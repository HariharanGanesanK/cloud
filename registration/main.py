from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import random
import psycopg2
import logging
import sys

# Local imports
from mail import send_mail
from config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
from role_manager import get_roles_for_otp

# ---------------- LOGGING ----------------
logging.basicConfig(
    level=logging.DEBUG,
    format="\033[1;36m[%(asctime)s]\033[0m \033[1;33m[%(levelname)s]\033[0m %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# ---------------- APP INIT ----------------
app = FastAPI(title="User Registration Backend", version="1.2.3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- MODELS ----------------
class RegisterRequest(BaseModel):
    name: str
    role: str
    device_unique_id: str
    company_name: str
    branch: str
    sub_branch: str
    password: str
    mail: Optional[str] = None


class OTPVerifyRequest(BaseModel):
    otp: str
    registration_data: RegisterRequest


# ---------------- DATABASE CONNECTION ----------------
def get_connection():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
            host=DB_HOST, port=DB_PORT
        )
        logger.debug(f"✅ Connected to PostgreSQL database '{DB_NAME}' as user '{DB_USER}'.")
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")


# ---------------- GLOBAL OTP STORE ----------------
otp_store = {}


# ---------------- UTILS ----------------
def generate_user_id(role, company_name, branch):
    prefix = company_name[:2].lower() + role[:2].lower() + branch[:2].lower()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM user_data WHERE user_id LIKE %s", (prefix + "%",))
    existing_ids = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()

    nums = []
    for uid in existing_ids:
        try:
            nums.append(int(uid[-3:]))
        except:
            pass
    next_num = (max(nums) + 1) if nums else 1
    return f"{prefix}{next_num:03d}"


# ---------------- ROUTES ----------------
@app.post("/register")
def register_user(data: RegisterRequest):
    logger.info(f"📩 Received registration request for: {data.name} ({data.role})")

    # 1️⃣ Generate OTP
    otp = str(random.randint(1000, 9999))
    otp_store[data.device_unique_id] = otp

    # 2️⃣ Get approvers
    conn = get_connection()
    cur = conn.cursor()
    role_sets = get_roles_for_otp(data.branch)

    business_roles = role_sets["business"]["roles"]
    business_placeholders = ','.join(['%s'] * len(business_roles))
    cur.execute(f"SELECT mail FROM user_data WHERE UPPER(role) IN ({business_placeholders})", business_roles)
    business_mails = [
        r[0] for r in cur.fetchall()
        if r[0] and str(r[0]).strip().lower() != "none"
    ]

    it_roles = role_sets["it"]["roles"]
    it_placeholders = ','.join(['%s'] * len(it_roles))
    if role_sets["it"]["branch_restricted"]:
        cur.execute(f"""
            SELECT mail FROM user_data
            WHERE UPPER(role) IN ({it_placeholders}) AND UPPER(branch) = UPPER(%s)
        """, (*it_roles, data.branch))
    else:
        cur.execute(f"SELECT mail FROM user_data WHERE UPPER(role) IN ({it_placeholders})", it_roles)

    it_mails = [
        r[0] for r in cur.fetchall()
        if r[0] and str(r[0]).strip().lower() != "none"
    ]

    cur.close()
    conn.close()

    all_recipients = list(set(business_mails + it_mails))
    logger.info(f"👔 Approver emails: {all_recipients}")

    if not all_recipients:
        logger.warning("⚠️ No valid approver emails found. Skipping mail send.")
        return {"message": "No approver emails found. Registration pending manual review."}

    # Mail content
    user_data = {
        "name": data.name,
        "role": data.role,
        "otp": otp
    }

    # 2️⃣ Send OTP to approvers
    for mail in all_recipients:
        send_mail(mail, "🔐 New User Registration OTP (Approval Required)", user_data)
    logger.info(f"✅ OTP sent to approvers: {all_recipients}")

    # 6️⃣ Send OTP to user if email exists
    if data.mail and str(data.mail).strip().lower() != "none":
        send_mail(data.mail, "🔐 Your Registration OTP", user_data)
        logger.info(f"📧 OTP also sent to user: {data.mail}")
    else:
        logger.info("ℹ️ No valid user email provided, skipping user OTP mail.")

    # 3️⃣ Respond to frontend (keep simple output)
    return {
        "message": "OTP sent to approvers",
        "status": "pending"
    }


# ---------------- VERIFY OTP ----------------
@app.post("/verify_otp")
def verify_otp(req: OTPVerifyRequest):
    device_id = req.registration_data.device_unique_id
    stored_otp = otp_store.get(device_id)

    if stored_otp != req.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    user_id = generate_user_id(
        req.registration_data.role,
        req.registration_data.company_name,
        req.registration_data.branch,
    )

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO user_data (user_id, name, role, device_unique_id, company_name, branch, sub_branch, password, mail)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        user_id,
        req.registration_data.name,
        req.registration_data.role,
        req.registration_data.device_unique_id,
        req.registration_data.company_name,
        req.registration_data.branch,
        req.registration_data.sub_branch,
        req.registration_data.password,
        req.registration_data.mail,
    ))
    conn.commit()
    cur.close()
    conn.close()

    otp_store.pop(device_id, None)
    return {"message": "User registered successfully", "user_id": user_id}


# ---------------- GET USERS ----------------
@app.get("/users")
def get_all_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM user_data ORDER BY user_id ASC")
    rows = cur.fetchall()
    col_names = [desc[0] for desc in cur.description]
    users = [dict(zip(col_names, row)) for row in rows]
    cur.close()
    conn.close()
    return {"total_users": len(users), "users": users}


# ---------------- STARTUP ----------------
@app.on_event("startup")
def startup_event():
    logger.info("🚀 FastAPI server started on uvicorn main:app --host 0.0.0.0 --port 9000")

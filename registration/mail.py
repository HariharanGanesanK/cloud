import smtplib
from email.mime.text import MIMEText
import logging
import os

logger = logging.getLogger(__name__)

# --- Gmail credentials (hardcoded version) ---
MAIL_USER = "hariharang103@gmail.com"       # 🔹 Replace with your Gmail
MAIL_PASS = "bzjv pfrg kpuc bbrl"     # 🔹 Replace with your 16-digit App Password


def send_mail(to_email, subject, user_data):
    """
    Sends a formal registration OTP mail to approvers.
    user_data should be a dict containing:
        - name
        - role
        - otp
    """
    name = user_data.get("name", "Unknown")
    role = user_data.get("role", "Unknown")
    otp = user_data.get("otp", "----")

    # --- Formal mail body ---
    body = f"""
    Dear Sir/Madam,

    A new user registration request has been submitted and requires your review.

    Applicant Details:
    • Name : {name}
    • Role : {role}

    Verification OTP:
    🔐 {otp}

    Please use the above OTP to authorize this registration request.

    Regards,
    """

    logger.info(f"📨 Sending mail to {to_email} | Subject: {subject}")
    logger.debug(f"Mail content:\n{body}")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = MAIL_USER
    msg["To"] = to_email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(MAIL_USER, MAIL_PASS)
            server.send_message(msg)
        logger.info(f"✅ Mail sent successfully to {to_email}")
    except Exception as e:
        logger.error(f"❌ Failed to send mail: {e}")

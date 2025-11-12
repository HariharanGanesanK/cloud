from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2 import sql
from datetime import datetime
import uvicorn

# -----------------------------------------
# Database configuration
# -----------------------------------------
DB_CONFIG = {
    "dbname": "jlmill",
    "user": "kaai",
    "password": "yourpassword",
    "host": "localhost",
    "port": "5432"
}

# -----------------------------------------
# Initialize FastAPI app
# -----------------------------------------
app = FastAPI(title="Transaction Database API", version="1.0")

# Allow CORS (optional)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------
# Helper: Get DB Connection
# -----------------------------------------
def get_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {e}")

# -----------------------------------------
# API Endpoint: Fetch by Date
# -----------------------------------------
@app.get("/transactions/by-date")
def get_transactions_by_date(date: str = Query(..., description="Date in YYYY-MM-DD format")):
    """
    Fetch transactions from transaction_db for the given date,
    ordered by start_time in descending order.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        query = """
            SELECT
                transaction_id,
                session_id,
                name,
                role,
                user_id,
                device_unique_id,
                cam,
                vehicle_number,
                date,
                start_time,
                end_time,
                box_count,
                bale_count,
                bag_count,
                trolley_count,
                image_path,
                updated_at
            FROM transaction_db
            WHERE date = %s
            ORDER BY start_time DESC;
        """

        cur.execute(query, (date,))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]

        cur.close()
        conn.close()

        results = [dict(zip(columns, row)) for row in rows]

        return {
            "count": len(results),
            "date": date,
            "data": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data: {e}")

# -----------------------------------------
# Root Endpoint
# -----------------------------------------
@app.get("/")
def root():
    return {"message": "Transaction Database API running on port 6000"}

# -----------------------------------------
# Run FastAPI app
# -----------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=6000)

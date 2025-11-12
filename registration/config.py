# Database credentials
DB_NAME = "jlmill"
DB_USER = "hari"
DB_PASSWORD = "yourpassword"
DB_HOST = "localhost"
DB_PORT = 5432

# Role-based notification configurations
OTP_NOTIFY_BUSINESS = {
    "roles": ["MD", "JMD", "GM", "AGM"]
}

OTP_NOTIFY_IT = {
    "roles": ["IT HEAD"],
    "branch_restricted": True  # Set False if IT gets OTPs from all branches
}

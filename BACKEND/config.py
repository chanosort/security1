import os
from dotenv import load_dotenv

# ── ADDED: load .env (Protection 11 — secrets never in code) ──
load_dotenv()

class Config:
    # Database configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'e_tracker_db')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_SCHEMA = os.getenv('DB_SCHEMA', '')

    # JWT configuration
    JWT_SECRET = os.getenv('JWT_SECRET', '')
    JWT_EXPIRY = 7  # days

    # CORS configuration
    CORS_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000',
                    'http://localhost:5500', 'http://localhost:5000',
                    'http://127.0.0.1:5000']

    # ── ADDED: seed values (Student ID ends 43 → D1=4, D2=3) ──
    MIN_USERNAME          = 7    # 6 + (D1 mod 3)
    MAX_USERNAME          = 19   # 16 + (D2 mod 5)
    MIN_PASSWORD          = 11   # 8 + (D2 mod 4)
    MAX_PASSWORD          = 64
    MAX_NAME_FIELD        = 23   # 20 + D2
    FAILED_BEFORE_FORGOT  = 2    # 2 + (D1 mod 2)
    LOCKOUT_TIER1_SECONDS = 19   # 15 + D1
    LOCKOUT_TIER2_SECONDS = 38   # 30 + 2*D1
    LOCKOUT_TIER3_SECONDS = 76   # 60 + 4*D1
    OTP_EXPIRY_MINUTES    = int(os.getenv('OTP_EXPIRY_MINUTES', '1'))
    IDLE_TIMEOUT_MINUTES  = 9    # 5 + (D1 mod 5)
    IP_BLOCK_THRESHOLD    = 11   # 8 + D2
    IP_BLOCK_SECONDS      = 600
    # Auth questions Q4, Q7, Q1
    AUTH_QUESTIONS = [
        ("Q4", "What is your mother's maiden first name?"),
        ("Q7", "What was the name of your elementary school?"),
        ("Q1", "What was the name of your first pet?"),
    ]

    # ── ADDED: secrets via env ──
    SMTP_HOST       = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT       = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USER       = os.getenv('SMTP_USER', '')
    SMTP_PASSWORD   = os.getenv('SMTP_PASSWORD', '')
    ENCRYPTION_KEY  = os.getenv('ENCRYPTION_KEY', '')
    CAPTCHA_SECRET  = os.getenv('CAPTCHA_SECRET', 'captcha_dev_secret')
    FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', JWT_SECRET)

    # Password history depth (Protection 7)
    PASSWORD_HISTORY_DEPTH = 3

    # Activity log retention not used (append-only)
    @property
    def DATABASE_URL(self):
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
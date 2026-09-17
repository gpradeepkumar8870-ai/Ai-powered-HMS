import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Central application configuration, loaded from environment variables."""

    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    DB_NAME = os.getenv("DB_NAME", "ai_hms")

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-me")
    JWT_ALGORITHM = "HS256"
    JWT_EXP_HOURS = int(os.getenv("JWT_EXP_HOURS", 12))

    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True") == "True"
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))

    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads", "lab_reports")
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}

    # Roles recognised by the system
    ROLES = ("admin", "doctor", "patient")

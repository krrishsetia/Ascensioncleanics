import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base configuration aligned with .env variables."""
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY") or os.getenv("SECRET_KEY", "dev-fallback-secret-key")
    DEBUG = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    TESTING = False

    HOST = os.getenv("HOST") or os.getenv("FLASK_HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT") or os.getenv("FLASK_PORT", 5000))
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", f"http://{HOST}:{PORT}")

    # SQLite & File Uploads Configuration
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "backend" / "cleanics.db"))
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "backend" / "uploads"))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

    # Session cookie settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Google OAuth 2.0 Credentials
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip().lstrip(":")
    GOOGLE_REDIRECT_URI = os.getenv(
        "GOOGLE_REDIRECT_URI", f"http://{HOST}:{PORT}/api/auth/callback"
    ).strip()
    POST_LOGIN_REDIRECT = os.getenv("POST_LOGIN_REDIRECT", "/")

    # Comma-separated list of admin emails (if empty in dev, all signed-in users can test admin features)
    ADMIN_EMAILS = [
        e.strip().lower()
        for e in os.getenv("ADMIN_EMAILS", "").split(",")
        if e.strip()
    ]


class DevelopmentConfig(Config):
    DEBUG = True
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
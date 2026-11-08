import os
from pathlib import Path
from dotenv import load_dotenv

# Explicitly load .env from the project root (one directory above backend/)
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

    # Session cookie settings required for OAuth state persistence
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Google OAuth 2.0 Credentials
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip().lstrip(":")
    GOOGLE_REDIRECT_URI = os.getenv(
        "GOOGLE_REDIRECT_URI", f"http://{HOST}:{PORT}/api/auth/callback"
    ).strip()
    POST_LOGIN_REDIRECT = os.getenv("POST_LOGIN_REDIRECT", "/")


class DevelopmentConfig(Config):
    """Development-specific configuration."""
    DEBUG = True
    # Allow oauthlib to operate over plain HTTP on 127.0.0.1
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


class ProductionConfig(Config):
    """Production-specific configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
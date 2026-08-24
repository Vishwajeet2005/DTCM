"""
config.py - Application configuration for Digital Twin CO2 Monitor (DTCM).

Loads environment variables from a .env file via python-dotenv and exposes
them as a hierarchy of Config classes.  A ``config_by_name`` mapping allows
the app factory to select the right config by string name.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from the project root (one directory up from this file if needed,
# or the same directory when run from project root).
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
load_dotenv(_HERE / ".env")


class Config:
    """Base configuration shared by all environments."""

    # ------------------------------------------------------------------
    # Flask core
    # ------------------------------------------------------------------
    SECRET_KEY: str = os.getenv("SECRET_KEY", "flask-secret-key-change-in-production")
    FLASK_ENV: str = os.getenv("FLASK_ENV", "production")
    DEBUG: bool = os.getenv("FLASK_DEBUG", "0") == "1"

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{_HERE.joinpath('dtcm.db').as_posix()}")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{_HERE.joinpath('dtcm.db').as_posix()}")

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "jwt-secret-change-in-production")
    # Token TTL in seconds (default 24 h)
    JWT_ACCESS_TOKEN_EXPIRES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "86400"))

    # ------------------------------------------------------------------
    # Weather API
    # ------------------------------------------------------------------
    OPENWEATHERMAP_API_KEY: str = os.getenv("OPENWEATHERMAP_API_KEY", "")
    OPENWEATHERMAP_BASE_URL: str = os.getenv(
        "OPENWEATHERMAP_BASE_URL", "https://api.openweathermap.org/data/2.5"
    )

    # ------------------------------------------------------------------
    # IoT / Sensor API
    # ------------------------------------------------------------------
    SENSOR_API_BASE_URL: str = os.getenv("SENSOR_API_BASE_URL", "")
    SENSOR_POLL_INTERVAL_SECONDS: int = int(
        os.getenv("SENSOR_POLL_INTERVAL_SECONDS", "60")
    )

    # ------------------------------------------------------------------
    # CO2 alert thresholds (ppm)
    # ------------------------------------------------------------------
    CO2_WARNING_THRESHOLD: float = float(os.getenv("CO2_WARNING_THRESHOLD", "450"))
    CO2_CRITICAL_THRESHOLD: float = float(os.getenv("CO2_CRITICAL_THRESHOLD", "500"))

    # ------------------------------------------------------------------
    # E-mail alerts
    # ------------------------------------------------------------------
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    ALERT_EMAIL_RECIPIENTS: str = os.getenv("ALERT_EMAIL_RECIPIENTS", "")

    # ------------------------------------------------------------------
    # ML model settings
    # ------------------------------------------------------------------
    MODEL_RETRAIN_INTERVAL_DAYS: int = int(
        os.getenv("MODEL_RETRAIN_INTERVAL_DAYS", "30")
    )
    MIN_ACCEPTABLE_R2: float = float(os.getenv("MIN_ACCEPTABLE_R2", "0.80"))

    # ------------------------------------------------------------------
    # Filesystem paths
    # ------------------------------------------------------------------
    BASE_DIR: Path = _HERE
    MODELS_DIR: Path = _HERE / "models"
    LOGS_DIR: Path = _HERE / "logs"

    @classmethod
    def get_db_url(cls) -> str:
        """Return the SQLAlchemy database URL.

        Convenience accessor so callers do not have to reach into the class
        attribute directly; also allows subclasses to override easily.
        """
        return cls.DATABASE_URL

    @classmethod
    def configure_logging(cls, level: int = logging.INFO) -> None:
        """Configure the root Python logger.

        Sets up two handlers:
        * **StreamHandler** - writes INFO+ messages to stdout/stderr.
        * **RotatingFileHandler** - writes INFO+ messages to
          ``logs/app.log`` (max 5 MB, 3 back-ups kept).

        Args:
            level: The minimum log level to capture (default: INFO).
        """
        # Ensure the logs directory exists before opening a file handler.
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_file = cls.LOGS_DIR / "app.log"

        fmt = logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(name)s : %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        # Avoid adding duplicate handlers on repeated calls (e.g. in tests).
        if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(fmt)
            console_handler.setLevel(level)
            root_logger.addHandler(console_handler)

        if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=5 * 1024 * 1024,  # 5 MB
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setFormatter(fmt)
            file_handler.setLevel(level)
            root_logger.addHandler(file_handler)


# ---------------------------------------------------------------------------
# Environment-specific subclasses
# ---------------------------------------------------------------------------


class DevelopmentConfig(Config):
    """Configuration for local development.

    Enables Flask debug mode and verbose SQL echo so developers can
    inspect generated queries in the console.
    """

    DEBUG: bool = True
    FLASK_ENV: str = "development"
    SQLALCHEMY_ECHO: bool = True  # Log every SQL statement to console


class ProductionConfig(Config):
    """Configuration for production deployments.

    Debug is explicitly disabled; SQL echo is off for performance.
    Expects all secrets to be supplied via real environment variables
    (not the .env.example defaults).
    """

    DEBUG: bool = False
    FLASK_ENV: str = "production"
    SQLALCHEMY_ECHO: bool = False


class TestingConfig(Config):
    """Configuration for the automated test suite.

    Uses an in-memory SQLite database so tests are fully isolated and
    require no external database server.  TESTING=True tells Flask-
    testing utilities to propagate exceptions rather than returning 500
    responses.
    """

    TESTING: bool = True
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///:memory:"
    SQLALCHEMY_ECHO: bool = False

    # Disable CSRF / JWT expiry checks during testing for convenience.
    JWT_ACCESS_TOKEN_EXPIRES: int = 0  # 0 = never expires in flask-jwt-extended tests

    @classmethod
    def get_db_url(cls) -> str:  # type: ignore[override]
        """Always return the in-memory SQLite URL regardless of env."""
        return "sqlite:///:memory:"


# ---------------------------------------------------------------------------
# Convenience mapping used by the app factory
# ---------------------------------------------------------------------------

config_by_name: dict[str, type[Config]] = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    # Alias so FLASK_ENV=default works during early bootstrap
    "default": DevelopmentConfig,
}


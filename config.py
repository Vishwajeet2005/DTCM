import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")
    TESTING = False
    
    # DB
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///dtcm.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret")
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 86400))
    
    # Thresholds
    CO2_WARNING_THRESHOLD = float(os.environ.get("CO2_WARNING_THRESHOLD", 450.0))
    CO2_CRITICAL_THRESHOLD = float(os.environ.get("CO2_CRITICAL_THRESHOLD", 500.0))
    
    # ML
    MIN_ACCEPTABLE_R2 = float(os.environ.get("MIN_ACCEPTABLE_R2", 0.80))

    # APIs & Collector
    OPENWEATHERMAP_API_KEY = os.environ.get("OPENWEATHERMAP_API_KEY", "")
    OPENWEATHERMAP_BASE_URL = os.environ.get("OPENWEATHERMAP_BASE_URL", "https://api.openweathermap.org/data/2.5")
    SENSOR_API_BASE_URL = os.environ.get("SENSOR_API_BASE_URL", "")
    SENSOR_POLL_INTERVAL_SECONDS = int(os.environ.get("SENSOR_POLL_INTERVAL_SECONDS", 60))

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    JWT_SECRET_KEY = "test-jwt-secret"
    SECRET_KEY = "test-secret"

config = Config()

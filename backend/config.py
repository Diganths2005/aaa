import os
from dotenv import load_dotenv

load_dotenv()

# Database Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://taxwise_user:taxwise_password@localhost:5432/taxwise_db"
)

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# CORS Configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

# API Configuration
API_V1_STR = "/api/v1"
PROJECT_NAME = "TaxWise"
PROJECT_VERSION = "0.1.0"

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

# AI provider configuration (server-side only)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GITHUB_MODELS_TOKENS = [token.strip() for token in os.getenv("GITHUB_MODELS_TOKENS", os.getenv("GITHUB_TOKEN", "")).split(",") if token.strip()]
GITHUB_MODELS_MODEL = os.getenv("GITHUB_MODELS_MODEL", "openai/gpt-4o-mini")
GITHUB_MODELS_URL = os.getenv("GITHUB_MODELS_URL", "https://models.github.ai/inference")

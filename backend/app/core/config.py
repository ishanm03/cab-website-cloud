# backend/app/core/config.py
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # API Configurations
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "SethCabs Backend"
    
    # CORS Origins (comma separated list in env, e.g. "http://localhost:5500,http://127.0.0.1:5500")
    CORS_ORIGINS: List[str] = ["*"]
    
    # HMAC Signing secret for booking quotes
    # NOTE: Set a strong secret in production environment
    HMAC_QUOTE_SECRET: str = Field(
        default="temporary_dev_hmac_quote_secret_key_12345",
        validation_alias="HMAC_QUOTE_SECRET"
    )
    
    # Path to Firebase Admin SDK service account key file (Optional if using default credentials)
    FIREBASE_SERVICE_ACCOUNT_PATH: Optional[str] = Field(
        default=None,
        validation_alias="FIREBASE_SERVICE_ACCOUNT_PATH"
    )

    # Super Admin emails authorized to promote/demote user roles
    SUPER_ADMIN_EMAILS: List[str] = Field(
        default=["admin@sethcabs.com", "admin@ishancabs.com"],
        validation_alias="SUPER_ADMIN_EMAILS"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()

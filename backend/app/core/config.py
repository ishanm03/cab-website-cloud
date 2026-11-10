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

    # Notification & Alert Configurations
    FRONTEND_BASE_URL: str = Field(
        default="https://sethcabs-poc.web.app",
        validation_alias="FRONTEND_BASE_URL"
    )
    DISPATCH_HELPLINE: str = Field(
        default="+91 89815 38038",
        validation_alias="DISPATCH_HELPLINE"
    )

    # Email Service Configuration (Resend API or SMTP)
    RESEND_API_KEY: Optional[str] = Field(
        default=None,
        validation_alias="RESEND_API_KEY"
    )
    SMTP_HOST: Optional[str] = Field(
        default=None,
        validation_alias="SMTP_HOST"
    )
    SMTP_PORT: int = Field(
        default=587,
        validation_alias="SMTP_PORT"
    )
    SMTP_USER: Optional[str] = Field(
        default=None,
        validation_alias="SMTP_USER"
    )
    SMTP_PASSWORD: Optional[str] = Field(
        default=None,
        validation_alias="SMTP_PASSWORD"
    )
    SMTP_FROM_EMAIL: str = Field(
        default="dispatch@sethcabs.com",
        validation_alias="SMTP_FROM_EMAIL"
    )
    SMTP_FROM_NAME: str = Field(
        default="SethCabs Dispatch",
        validation_alias="SMTP_FROM_NAME"
    )

    # Telegram Bot Alert Configuration
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(
        default=None,
        validation_alias="TELEGRAM_BOT_TOKEN"
    )
    TELEGRAM_CHAT_ID: Optional[str] = Field(
        default=None,
        validation_alias="TELEGRAM_CHAT_ID"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()

"""
Application configuration loaded from environment variables using Pydantic.
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "eCourts Services API Wrapper"
    PROJECT_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    LOG_LEVEL: str = Field(default="INFO", alias="LOG_LEVEL")

    # eCourts Portal Endpoints
    ECOURTS_SERVICES_BASE_URL: str = Field(
        default="https://ecourtsindia.com/",
        description="eCourts portal services base URL"
    )
    ECOURTS_HC_BASE_URL: str = Field(
        default="https://hcservices.ecourts.gov.in/hcservices",
        description="Official High Court services base URL"
    )
    ECOURTS_JUDGMENTS_BASE_URL: str = Field(
        default="https://judgments.ecourts.gov.in",
        description="Official eCourts Judgment Search portal"
    )

    # HTTP Client Configuration
    REQUEST_TIMEOUT: int = Field(default=30, description="HTTP request timeout in seconds")
    MAX_RETRIES: int = Field(default=3, description="Maximum HTTP retries on transient errors")
    USER_AGENT: str = Field(
        default=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        description="Browser User Agent for requests"
    )

    # CAPTCHA Session Store Configuration
    SESSION_TTL_SECONDS: int = Field(
        default=600,
        description="Session timeout in seconds (10 minutes) for user CAPTCHA solving"
    )
    MAX_ACTIVE_SESSIONS: int = Field(
        default=1000,
        description="Maximum concurrent active sessions in memory"
    )

    # Testing & Offline Mode
    ENABLE_MOCK_FALLBACK: bool = Field(
        default=False,
        description="Enable simulated mock responses for local testing when live servers are unavailable"
    )


settings = Settings()

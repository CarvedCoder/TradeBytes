"""
TradeBytes Core Configuration.

Centralized settings using pydantic-settings for type-safe environment variable parsing.
All configuration flows from environment → Settings singleton → dependency injection.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables."""

    # ── Core ──
    app_env: str = "development"
    app_name: str = "TradeBytes"
    app_version: str = "0.1.0"
    debug: bool = True
    secret_key: str = "change-me"
    api_prefix: str = "/api/v1"

    # ── Database ──
    database_url: str = "postgresql+asyncpg://tradebytes:tradebytes@localhost:5432/tradebytes"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # ── TimescaleDB ──
    timescale_url: str = "postgresql+asyncpg://tradebytes:tradebytes@localhost:5433/tradebytes_ts"

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 300

    # ── Auth ──
    jwt_secret_key: str = "change-me-jwt"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "TradeBytes"
    webauthn_origin: str = "https://localhost:3000"

    # ── ML ──
    model_registry_path: str = "./models"
    mlflow_tracking_uri: str = "http://localhost:5000"
    lstm_model_version: str = "latest"

    # ── Vector DB ──
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection_name: str = "tradebytes_knowledge"

    # ── External APIs ──
    news_api_key: str = ""
    alpha_vantage_key: str = ""
    finnhub_api_key: str = ""

    # ── Celery ──
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── Elasticsearch ──
    elasticsearch_url: str = "http://localhost:9200"

    # ── S3/MinIO ──
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_raw: str = "tradebytes-raw"
    s3_bucket_training: str = "tradebytes-training"

    # ── WebSocket ──
    ws_heartbeat_interval: int = 30
    ws_max_connections: int = 1000

    # ── CORS ──
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "https://localhost:3000"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False}


@lru_cache
def get_settings() -> Settings:
    """Singleton settings accessor for dependency injection."""
    return Settings()

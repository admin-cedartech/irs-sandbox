"""Application configuration loaded from environment / .env file."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # "bedrock" for real Amazon Bedrock, "mock" for a deterministic offline demo.
    llm_provider: str = "mock"

    aws_region: str = "us-east-1"
    # Cross-region inference profile for Claude Sonnet 4.5 (us-* region group).
    bedrock_model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

    # Optional Amazon Bedrock Guardrails (managed content safety).
    bedrock_guardrail_id: str = ""
    bedrock_guardrail_version: str = ""

    # Rules below this confidence get flagged for human review instead of auto-accepted.
    confidence_threshold: float = 0.6


settings = Settings()

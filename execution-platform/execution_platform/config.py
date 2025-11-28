from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Literal, Optional

class Settings(BaseSettings):
    provider: Literal["mock", "anthropic", "openai", "gemini", "claude_agent", "auto"] = "mock"
    app_name: str = "Execution Platform Gateway"
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    openai_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-pro"
    gemini_api_key: Optional[str] = None
    workspace_root: str = "./workspace"
    enable_tracing: bool = False
    rate_limit_per_persona: int = 0
    tokens_budget_per_minute: int = 0
    budget_per_minute_usd: float = 0.0
    persona_provider_map_path: str | None = None

    model_config = SettingsConfigDict(env_prefix="EP_", env_file=str(Path(__file__).resolve().parents[1] / ".env"), env_file_encoding="utf-8")

settings = Settings()
"""Application configuration via environment variables."""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str = "dev-secret"
    webhook_secret: str = ""

    database_url: str = "sqlite+aiosqlite:///./data/scalper.db"
    redis_url: str = ""
    use_redis: bool = False

    enable_ai_filter: bool = True
    enable_news_filter: bool = True
    enable_broker_execution: bool = False
    execution_mode: Literal["paper", "live"] = "paper"

    risk_preset: Literal["conservative", "standard", "aggressive"] = "standard"
    max_daily_loss: float = 500.0
    max_trades_per_day: int = 15
    max_consecutive_losses: int = 3
    cooldown_after_stop_seconds: int = 300
    duplicate_alert_window_seconds: int = 30
    stale_alert_seconds: int = 60
    kill_switch: bool = False

    skip_first_minutes_after_open: int = 5
    block_major_releases: bool = True

    default_dte: int = 0
    fallback_dte: int = 1
    target_delta_min: float = 0.35
    target_delta_max: float = 0.55
    min_open_interest: int = 100
    min_option_volume: int = 50
    max_spread_pct: float = 0.15
    max_hold_minutes: int = 15
    reject_late_day_minutes_before_close: int = 30

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    news_provider: Literal["mock", "finnhub", "newsapi"] = "mock"
    news_api_key: str = ""
    finnhub_api_key: str = ""

    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    tradier_access_token: str = ""
    tradier_account_id: str = ""
    ibkr_host: str = "127.0.0.1"
    ibkr_port: int = 7497
    ibkr_client_id: int = 1


RISK_PRESETS = {
    "conservative": {
        "max_daily_loss": 250.0,
        "max_trades_per_day": 8,
        "max_consecutive_losses": 2,
        "size_modifier_cap": 0.5,
        "min_confidence_approve": 0.65,
    },
    "standard": {
        "max_daily_loss": 500.0,
        "max_trades_per_day": 15,
        "max_consecutive_losses": 3,
        "size_modifier_cap": 1.0,
        "min_confidence_approve": 0.55,
    },
    "aggressive": {
        "max_daily_loss": 1000.0,
        "max_trades_per_day": 25,
        "max_consecutive_losses": 4,
        "size_modifier_cap": 1.5,
        "min_confidence_approve": 0.45,
    },
}


@lru_cache
def get_settings() -> Settings:
    return Settings()

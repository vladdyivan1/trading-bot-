from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "tv-0dte-ai-scalper"
    app_env: str = "dev"
    log_level: str = "INFO"

    database_url: str = "sqlite:///./data/scalper.db"
    redis_url: str | None = None

    webhook_secret: str | None = None
    webhook_stale_seconds: int = 45
    duplicate_window_seconds: int = 20

    risk_preset: str = "standard"
    max_daily_loss: float = -1_000.0
    max_trades_per_day: int = 12
    max_consecutive_losses: int = 3
    cooldown_minutes_after_loss: int = 10
    max_capital_per_trade: float = 1_500.0
    max_total_exposure: float = 8_000.0
    max_hold_minutes_default: int = 12
    no_trade_first_minutes: int = 5
    enforce_event_blackout: bool = True
    hard_kill_switch: bool = False

    session_morning_start: str = "09:35"
    session_morning_end: str = "11:30"
    session_afternoon_enabled: bool = True
    session_afternoon_start: str = "13:30"
    session_afternoon_end: str = "15:30"
    reject_lunch_period: bool = True

    ai_filtering_enabled: bool = True
    news_filtering_enabled: bool = True
    broker_execution_enabled: bool = False
    paper_trading_mode: bool = True
    broker_adapter: str = "paper"

    options_default_dte: int = 0
    options_fallback_dte: int = 1
    options_delta_min: float = 0.35
    options_delta_max: float = 0.60
    options_min_open_interest: int = 100
    options_min_volume: int = 100
    options_max_spread_pct: float = 0.12
    reject_after_time_et: str = "15:15"
    default_contract_qty: int = 1

    mock_news_provider: bool = True
    mock_ai_provider: bool = True
    news_api_url: str | None = None
    news_api_key: str | None = None

    dashboard_refresh_seconds: int = 5
    data_dir: Path = Field(default_factory=lambda: Path("./data"))


settings = Settings()

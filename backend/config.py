"""Explicit runtime configuration for the scalping backend."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Environment-driven settings with conservative paper-trading defaults."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SPY 0DTE AI Scalper"
    environment: Literal["local", "test", "paper", "live"] = "paper"
    log_level: str = "INFO"
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'spy_scalper.db'}"

    # Feature flags
    enable_ai_filter: bool = True
    enable_news_filter: bool = True
    enable_broker_execution: bool = False
    paper_trading: bool = True
    kill_switch: bool = False

    # Webhook/risk controls
    webhook_secret: str = ""
    allowed_symbols: list[str] = Field(default_factory=lambda: ["SPY"])
    stale_alert_seconds: int = 120
    duplicate_alert_window_seconds: int = 45
    market_timezone: str = "America/New_York"
    morning_start: str = "09:35"
    morning_end: str = "11:30"
    afternoon_start: str = "13:30"
    afternoon_end: str = "15:30"
    enable_afternoon_session: bool = True
    no_trade_first_minutes: int = 5
    no_trade_lunch_start: str = "11:30"
    no_trade_lunch_end: str = "13:30"

    # Risk presets and defaults
    risk_preset: Literal["conservative", "standard", "aggressive"] = "standard"
    starting_cash: float = 25000.0
    max_daily_loss: float = 500.0
    max_trades_per_day: int = 8
    max_consecutive_losses: int = 3
    cooldown_after_stop_minutes: int = 10
    max_capital_at_risk_per_trade: float = 350.0
    max_total_exposure: float = 1000.0
    max_hold_minutes: int = 20
    late_day_cutoff: str = "15:00"

    # Options contract selection
    default_dte: int = 0
    fallback_dte: int = 1
    min_option_open_interest: int = 500
    min_option_volume: int = 100
    target_delta_min: float = 0.45
    target_delta_max: float = 0.65
    max_option_spread_pct: float = 0.18

    # News/AI provider settings
    news_provider: Literal["mock", "rss"] = "mock"
    news_rss_urls: list[str] = Field(default_factory=list)
    llm_provider: Literal["mock"] = "mock"

    data_dir: Path = PROJECT_ROOT / "data"
    logs_dir: Path = PROJECT_ROOT / "logs"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings

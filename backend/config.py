"""Application configuration via environment variables."""

from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RiskPreset(str, Enum):
    CONSERVATIVE = "conservative"
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"


class ExecutionMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SPY 0DTE Scalping System"
    debug: bool = False
    database_url: str = "sqlite:///./data/scalper.db"
    redis_url: Optional[str] = None

    # Security
    webhook_secret: str = Field(default="change-me-in-production", alias="WEBHOOK_SECRET")
    api_key: Optional[str] = Field(default=None, alias="API_KEY")

    # Feature flags
    enable_ai_filter: bool = True
    enable_news_filter: bool = True
    enable_broker_execution: bool = False

    # Execution
    execution_mode: ExecutionMode = ExecutionMode.PAPER
    broker_adapter: str = "paper"

    # AI / LLM
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    ai_provider: str = "mock"  # mock | openai
    news_provider: str = "mock"  # mock | newsapi

    newsapi_key: Optional[str] = None

    # Risk presets
    risk_preset: RiskPreset = RiskPreset.STANDARD
    max_daily_loss: float = 500.0
    max_trades_per_day: int = 15
    max_consecutive_losses: int = 3
    cooldown_after_stop_seconds: int = 300
    max_capital_per_trade: float = 200.0
    max_total_exposure: float = 1000.0
    duplicate_alert_window_seconds: int = 60
    stale_alert_max_seconds: int = 120
    skip_first_minutes_after_open: int = 5
    kill_switch: bool = False

    # Options
    default_dte: int = 0
    allow_1dte_fallback: bool = True
    delta_min: float = 0.35
    delta_max: float = 0.55
    min_open_interest: int = 100
    min_option_volume: int = 50
    max_spread_pct: float = 0.15
    max_hold_minutes: int = 20
    reject_late_day_minutes: int = 30

    # Session (ET, minutes from midnight)
    session_am_start: int = 9 * 60 + 35
    session_am_end: int = 11 * 60 + 30
    session_pm_start: int = 13 * 60 + 30
    session_pm_end: int = 15 * 60 + 30
    enable_pm_session: bool = True
    lunch_start: int = 11 * 60 + 30
    lunch_end: int = 13 * 60 + 30

    @property
    def is_live(self) -> bool:
        return self.execution_mode == ExecutionMode.LIVE and self.enable_broker_execution


@lru_cache
def get_settings() -> Settings:
    return Settings()


RISK_PRESETS = {
    RiskPreset.CONSERVATIVE: {
        "max_daily_loss": 250.0,
        "max_trades_per_day": 8,
        "max_consecutive_losses": 2,
        "max_capital_per_trade": 100.0,
        "max_total_exposure": 400.0,
        "cooldown_after_stop_seconds": 600,
    },
    RiskPreset.STANDARD: {
        "max_daily_loss": 500.0,
        "max_trades_per_day": 15,
        "max_consecutive_losses": 3,
        "max_capital_per_trade": 200.0,
        "max_total_exposure": 1000.0,
        "cooldown_after_stop_seconds": 300,
    },
    RiskPreset.AGGRESSIVE: {
        "max_daily_loss": 1000.0,
        "max_trades_per_day": 25,
        "max_consecutive_losses": 4,
        "max_capital_per_trade": 400.0,
        "max_total_exposure": 2000.0,
        "cooldown_after_stop_seconds": 180,
    },
}


def apply_risk_preset(settings: Settings) -> Settings:
    preset = RISK_PRESETS.get(settings.risk_preset, RISK_PRESETS[RiskPreset.STANDARD])
    for key, value in preset.items():
        setattr(settings, key, value)
    return settings

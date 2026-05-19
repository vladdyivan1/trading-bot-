"""Application settings loaded from environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Central configuration for the trading assistant."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # IBKR
    ibkr_host: str = "127.0.0.1"
    ibkr_port: int = 4002
    ibkr_client_id: int = 1
    ibkr_account: str = ""
    paper_trading: bool = True

    # Safety
    live_trading_enabled: bool = False
    kill_switch: bool = False

    # LLM
    llm_provider: Literal["openai", "anthropic", "mock"] = "mock"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-latest"

    # Database
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'trading.db'}"

    # Logging
    log_level: str = "INFO"
    log_file: str = str(PROJECT_ROOT / "logs" / "trading.log")

    # Risk defaults
    max_risk_per_trade_pct: float = 0.5
    max_daily_loss_pct: float = 2.0
    max_weekly_loss_pct: float = 5.0
    max_account_drawdown_pct: float = 10.0
    max_open_positions: int = 3
    max_trades_per_day: int = 10
    max_contracts_per_trade: int = 1000
    max_forex_leverage: float = 20.0
    min_reward_to_risk: float = 1.5
    min_model_confidence: float = 0.65
    min_backtest_trades: int = 30
    max_spread_pct: float = 0.5

    # Paths
    models_dir: Path = Field(default=PROJECT_ROOT / "data" / "models")
    logs_dir: Path = Field(default=PROJECT_ROOT / "logs")

    def ensure_dirs(self) -> None:
        """Create required directories if missing."""
        (PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    """Return cached settings instance."""
    settings = Settings()
    settings.ensure_dirs()
    return settings

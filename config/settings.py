"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

load_dotenv()


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    return default if value in (None, "") else float(value)


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value in (None, "") else int(value)


@dataclass(frozen=True)
class Settings:
    """Runtime configuration with safe paper-trading defaults."""

    project_name: str = "ibkr-llm-trading-assistant"
    trading_mode: Literal["paper", "live"] = os.getenv("TRADING_MODE", "paper").lower()  # type: ignore[assignment]
    enable_live_trading: bool = _bool_env("ENABLE_LIVE_TRADING", False)

    ibkr_host: str = os.getenv("IBKR_HOST", "127.0.0.1")
    ibkr_port: int = _int_env("IBKR_PORT", 7497)
    ibkr_client_id: int = _int_env("IBKR_CLIENT_ID", 101)
    ibkr_account: str | None = os.getenv("IBKR_ACCOUNT") or None

    database_url: str = os.getenv("DATABASE_URL", "sqlite:///trading_assistant.db")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_dir: Path = Path(os.getenv("LOG_DIR", "logs"))

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY") or None
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")

    initial_capital: float = _float_env("INITIAL_CAPITAL", 100_000.0)
    max_risk_per_trade_pct: float = _float_env("MAX_RISK_PER_TRADE_PCT", 0.005)
    max_daily_loss_pct: float = _float_env("MAX_DAILY_LOSS_PCT", 0.02)
    max_weekly_loss_pct: float = _float_env("MAX_WEEKLY_LOSS_PCT", 0.05)
    max_account_drawdown_pct: float = _float_env("MAX_ACCOUNT_DRAWDOWN_PCT", 0.10)
    max_open_positions: int = _int_env("MAX_OPEN_POSITIONS", 3)
    max_trades_per_day: int = _int_env("MAX_TRADES_PER_DAY", 10)
    max_contracts_per_trade: int = _int_env("MAX_CONTRACTS_PER_TRADE", 1000)
    max_forex_leverage: float = _float_env("MAX_FOREX_LEVERAGE", 10.0)
    max_futures_exposure_pct: float = _float_env("MAX_FUTURES_EXPOSURE_PCT", 0.20)
    max_options_premium_risk_pct: float = _float_env("MAX_OPTIONS_PREMIUM_RISK_PCT", 0.01)
    min_reward_risk: float = _float_env("MIN_REWARD_RISK", 1.5)
    min_model_confidence: float = _float_env("MIN_MODEL_CONFIDENCE", 0.65)
    min_backtest_trades: int = _int_env("MIN_BACKTEST_TRADES", 30)
    max_allowed_spread_pct: float = _float_env("MAX_ALLOWED_SPREAD_PCT", 0.002)

    @property
    def live_trading_allowed(self) -> bool:
        """Return True only when both live flags are intentionally enabled."""

        return self.trading_mode == "live" and self.enable_live_trading


settings = Settings()
settings.log_dir.mkdir(parents=True, exist_ok=True)

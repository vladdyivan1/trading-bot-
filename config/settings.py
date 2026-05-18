"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseModel):
    """Global application configuration."""

    app_name: str = Field(default="ibkr-llm-trading-assistant")
    env: str = Field(default="dev")
    log_level: str = Field(default="INFO")
    database_url: str = Field(default="sqlite:///ibkr_trading.db")

    ib_host: str = Field(default="127.0.0.1")
    ib_port: int = Field(default=7497)
    ib_client_id: int = Field(default=101)
    ib_account: str | None = Field(default=None)

    paper_trading_only: bool = Field(default=True)
    live_trading_enabled: bool = Field(default=False)

    llm_provider: str = Field(default="none")
    openai_api_key: str | None = Field(default=None)
    openai_model: str = Field(default="gpt-4o-mini")
    anthropic_api_key: str | None = Field(default=None)
    anthropic_model: str = Field(default="claude-3-5-sonnet-latest")

    max_risk_per_trade_pct: float = Field(default=0.5)
    max_daily_loss_pct: float = Field(default=2.0)
    max_weekly_loss_pct: float = Field(default=5.0)
    max_account_drawdown_pct: float = Field(default=10.0)
    max_open_positions: int = Field(default=3)
    max_trades_per_day: int = Field(default=10)
    max_contracts_per_trade: int = Field(default=5)
    max_forex_leverage: float = Field(default=5.0)
    max_futures_exposure_pct: float = Field(default=20.0)
    max_options_premium_risk_pct: float = Field(default=1.0)
    min_reward_risk: float = Field(default=1.5)
    min_model_confidence: float = Field(default=0.65)
    min_backtest_sample_size: int = Field(default=50)
    max_allowed_spread_pct: float = Field(default=0.3)

    supported_timeframes: tuple[str, ...] = (
        "1 min",
        "5 mins",
        "15 mins",
        "1 hour",
        "1 day",
    )

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=os.getenv("APP_NAME", "ibkr-llm-trading-assistant"),
            env=os.getenv("ENV", "dev"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///ibkr_trading.db"),
            ib_host=os.getenv("IB_HOST", "127.0.0.1"),
            ib_port=int(os.getenv("IB_PORT", "7497")),
            ib_client_id=int(os.getenv("IB_CLIENT_ID", "101")),
            ib_account=os.getenv("IB_ACCOUNT") or None,
            paper_trading_only=_env_bool("PAPER_TRADING_ONLY", True),
            live_trading_enabled=_env_bool("LIVE_TRADING_ENABLED", False),
            llm_provider=os.getenv("LLM_PROVIDER", "none").lower(),
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
            max_risk_per_trade_pct=float(os.getenv("MAX_RISK_PER_TRADE_PCT", "0.5")),
            max_daily_loss_pct=float(os.getenv("MAX_DAILY_LOSS_PCT", "2.0")),
            max_weekly_loss_pct=float(os.getenv("MAX_WEEKLY_LOSS_PCT", "5.0")),
            max_account_drawdown_pct=float(os.getenv("MAX_ACCOUNT_DRAWDOWN_PCT", "10.0")),
            max_open_positions=int(os.getenv("MAX_OPEN_POSITIONS", "3")),
            max_trades_per_day=int(os.getenv("MAX_TRADES_PER_DAY", "10")),
            max_contracts_per_trade=int(os.getenv("MAX_CONTRACTS_PER_TRADE", "5")),
            max_forex_leverage=float(os.getenv("MAX_FOREX_LEVERAGE", "5.0")),
            max_futures_exposure_pct=float(os.getenv("MAX_FUTURES_EXPOSURE_PCT", "20")),
            max_options_premium_risk_pct=float(os.getenv("MAX_OPTIONS_PREMIUM_RISK_PCT", "1.0")),
            min_reward_risk=float(os.getenv("MIN_REWARD_RISK", "1.5")),
            min_model_confidence=float(os.getenv("MIN_MODEL_CONFIDENCE", "0.65")),
            min_backtest_sample_size=int(os.getenv("MIN_BACKTEST_SAMPLE_SIZE", "50")),
            max_allowed_spread_pct=float(os.getenv("MAX_ALLOWED_SPREAD_PCT", "0.3")),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get singleton settings object."""

    return Settings.from_env()

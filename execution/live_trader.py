"""Live trading path, disabled by default for safety."""

from __future__ import annotations

from config.settings import Settings, get_settings


class LiveTrader:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def assert_enabled(self) -> None:
        if self.settings.paper_trading_only or not self.settings.live_trading_enabled:
            raise RuntimeError(
                "Live trading is disabled by default. Set PAPER_TRADING_ONLY=false "
                "and LIVE_TRADING_ENABLED=true only after full validation."
            )

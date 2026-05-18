"""Global kill switch for halting all trading."""

from __future__ import annotations

from config.settings import Settings, get_settings


class KillSwitch:
    """In-memory and config-backed kill switch."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._active = self.settings.kill_switch

    @property
    def is_active(self) -> bool:
        return self._active or self.settings.kill_switch

    def activate(self) -> None:
        self._active = True
        self.settings.kill_switch = True

    def deactivate(self) -> None:
        self._active = False
        self.settings.kill_switch = False

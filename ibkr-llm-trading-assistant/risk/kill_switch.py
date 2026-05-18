"""Emergency kill switch — halts all trading."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from loguru import logger


class KillSwitch:
    """Global trading halt flag."""

    _instance: Optional["KillSwitch"] = None

    def __new__(cls) -> "KillSwitch":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._active = False
            cls._instance._reason = ""
            cls._instance._activated_at: Optional[datetime] = None
        return cls._instance

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def reason(self) -> str:
        return self._reason

    def activate(self, reason: str = "Manual kill switch") -> None:
        self._active = True
        self._reason = reason
        self._activated_at = datetime.utcnow()
        logger.critical("KILL SWITCH ACTIVATED: {}", reason)

    def deactivate(self) -> None:
        self._active = False
        self._reason = ""
        self._activated_at = None
        logger.info("Kill switch deactivated")

    def check(self) -> bool:
        """Return True if trading is allowed."""
        return not self._active

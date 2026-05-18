"""Hard kill switch for execution safety."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class KillSwitch:
    enabled: bool = False
    reason: str = ""

    def trigger(self, reason: str = "manual") -> None:
        self.enabled = True
        self.reason = reason

    def reset(self) -> None:
        self.enabled = False
        self.reason = ""

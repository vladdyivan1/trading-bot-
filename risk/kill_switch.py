"""Manual and programmatic kill switch."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class KillSwitch:
    """A simple file-backed kill switch suitable for dashboards and workers."""

    path: Path = Path("logs/kill_switch.enabled")

    def enable(self, reason: str = "manual") -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(reason, encoding="utf-8")

    def disable(self) -> None:
        if self.path.exists():
            self.path.unlink()

    def is_enabled(self) -> bool:
        return self.path.exists()

    def reason(self) -> str | None:
        if not self.path.exists():
            return None
        return self.path.read_text(encoding="utf-8").strip()

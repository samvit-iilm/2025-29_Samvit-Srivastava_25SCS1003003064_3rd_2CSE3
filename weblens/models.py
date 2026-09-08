"""Core data structures shared across the package."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True, slots=True)
class LogEntry:
    """A single parsed line of an access log."""

    ip: str
    timestamp: datetime
    method: str
    path: str
    protocol: str
    status: int
    size: int
    referrer: str = "-"
    user_agent: str = "-"

    @property
    def is_error(self) -> bool:
        return self.status >= 400

    @property
    def is_server_error(self) -> bool:
        return self.status >= 500

    @property
    def status_class(self) -> str:
        """'2xx', '3xx', ... - useful for grouping."""
        return f"{self.status // 100}xx"


@dataclass(slots=True)
class ParseStats:
    """Bookkeeping for how a file parsed."""

    total_lines: int = 0
    parsed: int = 0
    malformed: int = 0
    malformed_samples: list[str] = field(default_factory=list)

    def record_bad(self, line: str, keep: int = 5) -> None:
        self.malformed += 1
        if len(self.malformed_samples) < keep:
            self.malformed_samples.append(line.rstrip("\n")[:200])

    @property
    def success_rate(self) -> float:
        if self.total_lines == 0:
            return 0.0
        return self.parsed / self.total_lines * 100


@dataclass(frozen=True, slots=True)
class Anomaly:
    """Something worth a human's attention."""

    kind: str
    severity: str  # "low" | "medium" | "high"
    subject: str
    detail: str
    evidence: Optional[str] = None

    SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

    def sort_key(self) -> tuple[int, str]:
        return (self.SEVERITY_ORDER.get(self.severity, 9), self.subject)

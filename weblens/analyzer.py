"""Aggregation layer: turns a stream of LogEntry objects into statistics."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

from .models import LogEntry


@dataclass
class TrafficStats:
    """Everything the reports need, computed in a single pass."""

    total_requests: int = 0
    total_bytes: int = 0
    first_seen: datetime | None = None
    last_seen: datetime | None = None

    status_counts: Counter[int] = field(default_factory=Counter)
    status_classes: Counter[str] = field(default_factory=Counter)
    method_counts: Counter[str] = field(default_factory=Counter)
    path_counts: Counter[str] = field(default_factory=Counter)
    ip_counts: Counter[str] = field(default_factory=Counter)
    agent_counts: Counter[str] = field(default_factory=Counter)
    referrer_counts: Counter[str] = field(default_factory=Counter)

    hourly_hits: Counter[str] = field(default_factory=Counter)
    bytes_by_path: Counter[str] = field(default_factory=Counter)

    # per-IP detail used by the anomaly rules
    errors_by_ip: Counter[str] = field(default_factory=Counter)
    paths_by_ip: defaultdict[str, set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )

    # ---------- derived values ----------

    @property
    def error_count(self) -> int:
        return sum(c for s, c in self.status_counts.items() if s >= 400)

    @property
    def error_rate(self) -> float:
        if not self.total_requests:
            return 0.0
        return self.error_count / self.total_requests * 100

    @property
    def unique_visitors(self) -> int:
        return len(self.ip_counts)

    @property
    def avg_response_size(self) -> float:
        if not self.total_requests:
            return 0.0
        return self.total_bytes / self.total_requests

    @property
    def duration_hours(self) -> float:
        if not (self.first_seen and self.last_seen):
            return 0.0
        return (self.last_seen - self.first_seen).total_seconds() / 3600

    @property
    def requests_per_hour(self) -> float:
        hours = self.duration_hours
        return self.total_requests / hours if hours > 0 else float(self.total_requests)

    def top(self, counter: Counter, limit: int = 10) -> list[tuple[str, int]]:
        return counter.most_common(limit)

    def busiest_hour(self) -> tuple[str, int] | None:
        return self.hourly_hits.most_common(1)[0] if self.hourly_hits else None


def analyze(entries: Iterable[LogEntry]) -> TrafficStats:
    """Fold a stream of entries into a TrafficStats object.

    Single pass, O(1) memory per distinct key - safe on large files.
    """
    stats = TrafficStats()

    for entry in entries:
        stats.total_requests += 1
        stats.total_bytes += entry.size

        if stats.first_seen is None or entry.timestamp < stats.first_seen:
            stats.first_seen = entry.timestamp
        if stats.last_seen is None or entry.timestamp > stats.last_seen:
            stats.last_seen = entry.timestamp

        stats.status_counts[entry.status] += 1
        stats.status_classes[entry.status_class] += 1
        stats.method_counts[entry.method] += 1
        stats.path_counts[entry.path] += 1
        stats.ip_counts[entry.ip] += 1
        stats.agent_counts[entry.user_agent] += 1
        stats.referrer_counts[entry.referrer] += 1
        stats.bytes_by_path[entry.path] += entry.size
        stats.hourly_hits[entry.timestamp.strftime("%Y-%m-%d %H:00")] += 1
        stats.paths_by_ip[entry.ip].add(entry.path)

        if entry.is_error:
            stats.errors_by_ip[entry.ip] += 1

    return stats

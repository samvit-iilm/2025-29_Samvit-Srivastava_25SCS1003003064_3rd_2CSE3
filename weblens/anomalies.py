"""Heuristic rules that flag suspicious or unhealthy traffic.

Each rule is a small pure function taking TrafficStats and returning a
list of Anomaly objects, so new rules can be added without touching the
rest of the pipeline.
"""

from __future__ import annotations

import re
import statistics
from typing import Callable

from .analyzer import TrafficStats
from .models import Anomaly

Rule = Callable[[TrafficStats], list[Anomaly]]

SENSITIVE_PATH = re.compile(
    r"(\.env|\.git|wp-admin|wp-login|phpmyadmin|/admin|/etc/passwd|\.sql|\.bak)",
    re.IGNORECASE,
)
# URL-encoded payloads are the norm in real logs, so treat %20 / + as space.
_SP = r"(?:\s|\+|%20)+"
INJECTION_HINT = re.compile(
    rf"(union{_SP}select|select{_SP}.*{_SP}from|<script|%3cscript"
    r"|\.\./|%2e%2e|;\s*cat\s|/bin/sh|\bor\b\s*1\s*=\s*1)",
    re.IGNORECASE,
)
BOT_AGENT = re.compile(r"(bot|crawler|spider|curl|wget|python-requests)", re.IGNORECASE)

# thresholds kept together so they are easy to tune from one place
ERROR_RATE_WARN = 10.0          # percent of all requests
SERVER_ERROR_WARN = 1.0         # percent of all requests
IP_ERROR_MIN = 15               # errors from one IP before we care
IP_ERROR_SHARE = 0.5            # ...and what share of its traffic errored
SCAN_PATH_MIN = 25              # distinct paths hit by a single IP
SPIKE_SIGMA = 3.0               # std-devs above mean hourly traffic


def high_error_rate(stats: TrafficStats) -> list[Anomaly]:
    found: list[Anomaly] = []
    if stats.error_rate >= ERROR_RATE_WARN:
        found.append(
            Anomaly(
                kind="high_error_rate",
                severity="high" if stats.error_rate >= 25 else "medium",
                subject="site-wide",
                detail=f"{stats.error_rate:.1f}% of requests returned 4xx/5xx",
                evidence=f"{stats.error_count} of {stats.total_requests} requests",
            )
        )

    server_errors = sum(c for s, c in stats.status_counts.items() if s >= 500)
    if stats.total_requests:
        share = server_errors / stats.total_requests * 100
        if share >= SERVER_ERROR_WARN:
            found.append(
                Anomaly(
                    kind="server_errors",
                    severity="high",
                    subject="site-wide",
                    detail=f"{share:.1f}% of requests returned 5xx",
                    evidence=f"{server_errors} server errors",
                )
            )
    return found


def error_heavy_clients(stats: TrafficStats) -> list[Anomaly]:
    found: list[Anomaly] = []
    for ip, errors in stats.errors_by_ip.most_common(20):
        total = stats.ip_counts[ip]
        if errors >= IP_ERROR_MIN and errors / total >= IP_ERROR_SHARE:
            found.append(
                Anomaly(
                    kind="error_heavy_client",
                    severity="medium",
                    subject=ip,
                    detail=f"{errors}/{total} requests failed "
                    f"({errors / total * 100:.0f}%) - possible brute force or broken client",
                    evidence=f"{errors} errors",
                )
            )
    return found


def path_scanning(stats: TrafficStats) -> list[Anomaly]:
    found: list[Anomaly] = []
    for ip, paths in stats.paths_by_ip.items():
        if len(paths) >= SCAN_PATH_MIN:
            found.append(
                Anomaly(
                    kind="path_scanning",
                    severity="medium",
                    subject=ip,
                    detail=f"requested {len(paths)} distinct paths - looks like enumeration",
                    evidence=", ".join(sorted(paths)[:5]) + " ...",
                )
            )
    return found


def sensitive_path_probes(stats: TrafficStats) -> list[Anomaly]:
    hits = {p: c for p, c in stats.path_counts.items() if SENSITIVE_PATH.search(p)}
    if not hits:
        return []
    top = sorted(hits.items(), key=lambda kv: -kv[1])[:5]
    return [
        Anomaly(
            kind="sensitive_path_probe",
            severity="high",
            subject="site-wide",
            detail=f"{len(hits)} sensitive path(s) probed ({sum(hits.values())} requests)",
            evidence="; ".join(f"{p} x{c}" for p, c in top),
        )
    ]


def injection_attempts(stats: TrafficStats) -> list[Anomaly]:
    hits = {p: c for p, c in stats.path_counts.items() if INJECTION_HINT.search(p)}
    if not hits:
        return []
    top = sorted(hits.items(), key=lambda kv: -kv[1])[:5]
    return [
        Anomaly(
            kind="injection_attempt",
            severity="high",
            subject="site-wide",
            detail=f"{len(hits)} request path(s) contain injection/traversal patterns",
            evidence="; ".join(f"{p} x{c}" for p, c in top),
        )
    ]


def traffic_spikes(stats: TrafficStats) -> list[Anomaly]:
    """Flag hours more than SPIKE_SIGMA standard deviations above the mean."""
    counts = list(stats.hourly_hits.values())
    if len(counts) < 4:
        return []
    mean = statistics.fmean(counts)
    sigma = statistics.pstdev(counts)
    if sigma == 0:
        return []

    found: list[Anomaly] = []
    for hour, count in sorted(stats.hourly_hits.items()):
        z = (count - mean) / sigma
        if z >= SPIKE_SIGMA:
            found.append(
                Anomaly(
                    kind="traffic_spike",
                    severity="medium",
                    subject=hour,
                    detail=f"{count} requests vs {mean:.0f} hourly average (z={z:.1f})",
                    evidence=f"{count} requests",
                )
            )
    return found


def bot_dominance(stats: TrafficStats) -> list[Anomaly]:
    if not stats.total_requests:
        return []
    bot_hits = sum(c for a, c in stats.agent_counts.items() if BOT_AGENT.search(a))
    share = bot_hits / stats.total_requests * 100
    if share < 40:
        return []
    return [
        Anomaly(
            kind="bot_traffic",
            severity="low",
            subject="site-wide",
            detail=f"{share:.0f}% of traffic came from bots/automated agents",
            evidence=f"{bot_hits} requests",
        )
    ]


DEFAULT_RULES: tuple[Rule, ...] = (
    high_error_rate,
    error_heavy_clients,
    path_scanning,
    sensitive_path_probes,
    injection_attempts,
    traffic_spikes,
    bot_dominance,
)


def detect(stats: TrafficStats, rules: tuple[Rule, ...] = DEFAULT_RULES) -> list[Anomaly]:
    """Run every rule and return findings sorted by severity."""
    findings: list[Anomaly] = []
    for rule in rules:
        findings.extend(rule(stats))
    return sorted(findings, key=lambda a: a.sort_key())

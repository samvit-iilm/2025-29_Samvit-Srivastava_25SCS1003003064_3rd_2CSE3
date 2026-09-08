"""Streaming parser for Common / Combined Log Format access logs."""

from __future__ import annotations

import gzip
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Iterator, TextIO

from .models import LogEntry, ParseStats

# 127.0.0.1 - frank [10/Oct/2000:13:55:36 -0700] "GET /a HTTP/1.0" 200 2326 "ref" "ua"
LOG_PATTERN = re.compile(
    r"""^
    (?P<ip>\S+)\s+
    (?P<ident>\S+)\s+
    (?P<user>\S+)\s+
    \[(?P<time>[^\]]+)\]\s+
    "(?P<method>[A-Z]+)\s+(?P<path>\S+)(?:\s+(?P<protocol>[^"]*))?"\s+
    (?P<status>\d{3})\s+
    (?P<size>\d+|-)
    (?:\s+"(?P<referrer>[^"]*)"\s+"(?P<agent>[^"]*)")?
    \s*$""",
    re.VERBOSE,
)

TIME_FORMAT = "%d/%b/%Y:%H:%M:%S"


class LogParseError(ValueError):
    """Raised when a line cannot be understood as a log record."""


def parse_timestamp(raw: str) -> datetime:
    """Parse '10/Oct/2000:13:55:36 -0700' into an aware datetime."""
    stamp, _, offset = raw.partition(" ")
    moment = datetime.strptime(stamp, TIME_FORMAT)
    if offset and len(offset) == 5 and offset[0] in "+-":
        sign = 1 if offset[0] == "+" else -1
        delta = timedelta(hours=int(offset[1:3]), minutes=int(offset[3:5]))
        return moment.replace(tzinfo=timezone(sign * delta))
    return moment.replace(tzinfo=timezone.utc)


def parse_line(line: str) -> LogEntry:
    """Parse one log line. Raises LogParseError on anything unexpected."""
    match = LOG_PATTERN.match(line.strip())
    if match is None:
        raise LogParseError(f"unrecognised log line: {line.strip()[:120]!r}")

    groups = match.groupdict()
    try:
        timestamp = parse_timestamp(groups["time"])
    except ValueError as exc:  # bad month name, bad digits, ...
        raise LogParseError(f"bad timestamp {groups['time']!r}") from exc

    raw_size = groups["size"]
    return LogEntry(
        ip=groups["ip"],
        timestamp=timestamp,
        method=groups["method"],
        path=groups["path"],
        protocol=(groups.get("protocol") or "-").strip(),
        status=int(groups["status"]),
        size=0 if raw_size == "-" else int(raw_size),
        referrer=groups.get("referrer") or "-",
        user_agent=groups.get("agent") or "-",
    )


def parse_lines(lines: Iterable[str], stats: ParseStats | None = None) -> Iterator[LogEntry]:
    """Lazily parse an iterable of lines, skipping (and counting) bad ones."""
    stats = stats if stats is not None else ParseStats()
    for line in lines:
        if not line.strip():
            continue
        stats.total_lines += 1
        try:
            entry = parse_line(line)
        except LogParseError:
            stats.record_bad(line)
            continue
        stats.parsed += 1
        yield entry


def _open(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def parse_file(path: str | Path, stats: ParseStats | None = None) -> Iterator[LogEntry]:
    """Stream a (optionally gzipped) log file one entry at a time.

    Memory use stays flat regardless of file size, which is the whole
    point of using a generator here instead of readlines().
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"log file not found: {path}")
    with _open(path) as handle:
        yield from parse_lines(handle, stats)

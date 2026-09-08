"""Command line interface for weblens."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .analyzer import analyze
from .anomalies import detect
from .models import ParseStats
from .parser import parse_file
from .report import render_html, render_json, render_text, write_csv

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_ANOMALIES = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="weblens",
        description="Analyse a web server access log: traffic stats + anomaly detection.",
        epilog="Example: python -m weblens sample_data/access.log --format html -o report.html",
    )
    parser.add_argument("logfile", help="path to an access log (.log or .gz)")
    parser.add_argument(
        "-f", "--format", choices=("text", "html", "json"), default="text",
        help="output format (default: text)",
    )
    parser.add_argument("-o", "--output", help="write the report to this file instead of stdout")
    parser.add_argument("--csv", help="also write a per-path breakdown to this CSV file")
    parser.add_argument("-t", "--top", type=int, default=10, help="rows per ranking table (default: 10)")
    parser.add_argument("--no-anomalies", action="store_true", help="skip anomaly detection")
    parser.add_argument(
        "--fail-on-anomaly", action="store_true",
        help="exit with status 2 if anomalies were found (useful in CI)",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="suppress progress messages")
    parser.add_argument("--version", action="version", version=f"weblens {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    parse_stats = ParseStats()
    try:
        stats = analyze(parse_file(args.logfile, parse_stats))
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except PermissionError:
        print(f"error: cannot read {args.logfile} (permission denied)", file=sys.stderr)
        return EXIT_ERROR

    if stats.total_requests == 0:
        print(
            f"error: no valid log entries found in {args.logfile} "
            f"({parse_stats.malformed} malformed line(s))",
            file=sys.stderr,
        )
        return EXIT_ERROR

    anomalies = [] if args.no_anomalies else detect(stats)
    source = Path(args.logfile).name

    renderers = {
        "text": lambda: render_text(stats, anomalies, parse_stats, source, args.top),
        "html": lambda: render_html(stats, anomalies, parse_stats, source, args.top),
        "json": lambda: render_json(stats, anomalies, parse_stats, source),
    }
    report = renderers[args.format]()

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        if not args.quiet:
            print(f"report written to {args.output}")
    else:
        print(report)

    if args.csv:
        write_csv(stats, args.csv)
        if not args.quiet:
            print(f"per-path CSV written to {args.csv}")

    if args.fail_on_anomaly and anomalies:
        return EXIT_ANOMALIES
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

# weblens — Web Server Log Analyzer

A command-line tool that reads Apache/Nginx access logs, produces traffic
statistics, and flags suspicious activity — written in **pure Python 3.10+
with no third-party dependencies**.

Built as the capstone project for a **Python Developer Internship at
Codec Technologies India Pvt. Ltd.** (08/07/2026 – 08/08/2026).
Full write-up: [`docs/PROJECT_REPORT.md`](docs/PROJECT_REPORT.md).

---

## What it does

| | |
|---|---|
| **Parses** | Common Log Format and Combined Log Format, plain or `.gz` |
| **Aggregates** | requests, unique IPs, bandwidth, status codes, methods, top paths, hourly traffic |
| **Detects** | error spikes, brute-force/broken clients, path scanning, sensitive-file probes, injection attempts, traffic spikes, bot dominance |
| **Reports** | ASCII terminal report with bar charts, standalone HTML dashboard, JSON, per-path CSV |
| **Handles** | malformed lines (counted, never crashes), files larger than RAM (streaming generators) |

---

## Quick start

```bash
git clone https://github.com/samvit-iilm/python-Internship.git
cd python-Internship

# 1. terminal report on the bundled sample log
python -m weblens sample_data/access.log

# 2. HTML dashboard
python -m weblens sample_data/access.log --format html -o report.html

# 3. machine-readable output + CSV export
python -m weblens sample_data/access.log --format json -o report.json
python -m weblens sample_data/access.log --csv paths.csv -o report.txt
```

No `pip install` needed — the standard library is the only requirement.

## Command reference

```
usage: weblens [-h] [-f {text,html,json}] [-o OUTPUT] [--csv CSV] [-t TOP]
               [--no-anomalies] [--fail-on-anomaly] [-q] [--version]
               logfile

  logfile              path to an access log (.log or .gz)
  -f, --format         output format: text (default), html, json
  -o, --output         write the report to a file instead of stdout
  --csv CSV            also write a per-path breakdown to this CSV file
  -t, --top            rows per ranking table (default: 10)
  --no-anomalies       skip anomaly detection
  --fail-on-anomaly    exit with status 2 if anomalies were found (for CI)
  -q, --quiet          suppress progress messages
```

Exit codes: `0` clean, `1` error (missing/unreadable/empty file), `2` anomalies
found with `--fail-on-anomaly` — so it can be dropped straight into a cron job
or CI pipeline.

## Sample output

```
 OVERVIEW
------------------------------------------------------------------------------
  Requests parsed        : 1,500
  Unique client IPs      : 62
  Data transferred       : 98.9 MB
  Error rate (4xx/5xx)   : 12.60%
  Busiest hour           : 2026-08-04 14:00 (136 requests)
  Lines read / malformed : 1,502 / 2 (99.9% parsed)

 ANOMALIES
------------------------------------------------------------------------------
  [HIGH]   site-wide - 35 sensitive path(s) probed (94 requests)
            evidence: /wp-admin/setup-config.php x12; /wp-login.php x10; ...
  [MEDIUM] 185.220.101.44 - requested 36 distinct paths - looks like enumeration
  [MEDIUM] 2026-08-04 14:00 - 136 requests vs 94 hourly average (z=3.8)
```

Full examples: [`docs/sample_report.txt`](docs/sample_report.txt) and
[`docs/sample_report.html`](docs/sample_report.html).

## Project layout

```
weblens/
├── __init__.py      package metadata
├── __main__.py      enables `python -m weblens`
├── models.py        LogEntry, ParseStats, Anomaly dataclasses
├── parser.py        regex + streaming line parser
├── analyzer.py      single-pass aggregation into TrafficStats
├── anomalies.py     pluggable detection rules
├── report.py        text / HTML / JSON / CSV renderers
└── cli.py           argparse front-end
tests/               40 unit + end-to-end tests
scripts/             deterministic sample-log generator
sample_data/         1,500-line sample access log
docs/                project report and sample outputs
```

The pipeline is a straight line — **parse → analyze → detect → render** — and
each stage only knows about the one before it, so a new output format or a new
detection rule can be added without touching anything else.

## Design notes

- **Streaming, not slurping.** `parse_file()` is a generator, so a 5 GB log
  uses the same memory as a 5 KB one.
- **Bad data never crashes it.** Unparseable lines are counted and sampled,
  and the parse success rate appears in every report.
- **Rules are plain functions.** `anomalies.DEFAULT_RULES` is a tuple of
  `TrafficStats -> list[Anomaly]` functions; adding a rule is one function plus
  one tuple entry.
- **Spikes use a z-score** over hourly buckets (flagged above 3σ) rather than a
  fixed threshold, so it adapts to a quiet site and a busy one alike.
- **Thresholds live in one place** at the top of `anomalies.py`.

## Tests

```bash
python -m unittest discover -s tests -v
```

40 tests cover timestamp/offset parsing, malformed input, aggregation maths,
every detection rule (both firing and staying quiet), and all four output
formats end to end.

## Regenerating the sample log

```bash
python scripts/generate_sample_log.py sample_data/access.log 1500
```

The generator is seeded, so the output is identical every run — it deliberately
plants a path scanner, a broken client, a download burst, and two malformed
lines so every code path has something to find.

## Author

**Samvit Srivastava** — Python Developer Intern, Codec Technologies India Pvt. Ltd.

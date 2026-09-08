# Internship Project Report

## weblens — A Web Server Log Analyzer with Anomaly Detection

---

**Submitted by:** Samvit Srivastava
**Designation:** Python Developer Intern (Project Intern)
**Organisation:** Codec Technologies India Pvt. Ltd., Chandivali IT Hub, Mumbai
**Internship duration:** 08/07/2026 to 08/08/2026 (1 month)
**Mode:** Pan India, Hybrid
**Programme:** 1-Month AICTE & ICAC Approved Internship Programme, listed on the National Internship Portal
**AICTE ID:** CORPORATE6759d549ce59e1733940553
**NCS ID:** E19E86-0116588288923
**Reporting to:** Assigned Project Head(s)
**Programme Manager:** Dr. Anurag Shrivastava
**Repository:** https://github.com/samvit-iilm/python-Internship

---

## 1. Acknowledgement

I would like to thank Codec Technologies India Pvt. Ltd. for offering me the
opportunity to work as a Python Developer Intern, and Dr. Anurag Shrivastava
and my assigned project head for their guidance and weekly reviews through the
course of the programme. The internship was conducted under the AICTE and ICAC
approved programme listed on the National Internship Portal, and gave me the
chance to take a Python project from an idea to a tested, documented and
shippable tool.

---

## 2. Abstract

Every web server writes an access log, and almost nobody reads it. A busy site
produces tens of thousands of lines a day, and the useful signals — a failing
endpoint, a bot enumerating admin URLs, a sudden traffic spike — are buried in
noise that no one has time to scroll through.

**weblens** is a command-line tool that reads Apache/Nginx access logs and turns
them into something a human can act on in under a second: a summary of traffic,
a ranked breakdown of paths, clients, status codes and bandwidth, an hourly
histogram, and a prioritised list of anomalies with the evidence that triggered
each one. It emits a terminal report, a self-contained HTML dashboard, JSON for
downstream tooling, and a CSV export.

The whole tool is written in **pure Python 3.10+ using only the standard
library** — approximately 660 lines of application code covered by 40 unit and
end-to-end tests. It streams input through generators, so a log file larger than
available RAM analyses in constant memory.

---

## 3. Objectives

1. Build a complete, useful Python application rather than a set of exercises.
2. Practise clean package structure — separate parsing, analysis, detection and
   presentation instead of one long script.
3. Handle real-world messy input safely: malformed lines, missing fields,
   gzipped files, mixed timezone offsets.
4. Apply basic statistics (z-scores) and pattern matching to produce security
   and reliability insight, not just counts.
5. Write an automated test suite that proves each part behaves correctly.
6. Ship it with documentation, sample data and a reproducible demo.

---

## 4. Problem statement

Access-log analysis tools exist, but the common options are awkward for a small
team or a student project:

| Approach | Limitation |
|---|---|
| `grep` / `awk` one-liners | Ad-hoc, not repeatable, no anomaly logic |
| GoAccess and similar | Great dashboards, but a binary to install and no custom detection rules |
| ELK / Splunk stacks | Powerful, but heavy infrastructure for a single server |
| pandas notebooks | Requires third-party installs and loads the entire file into memory |

The gap: a **zero-install, single-command tool** that any machine with Python
can run, that reports both *what happened* and *what looks wrong*, and whose
detection rules can be edited by whoever owns the server.

---

## 5. Requirement analysis

**Functional requirements**

| ID | Requirement |
|---|---|
| F1 | Parse Common Log Format and Combined Log Format records |
| F2 | Accept plain-text and gzip-compressed log files |
| F3 | Skip and count malformed lines without terminating |
| F4 | Compute request, visitor, bandwidth, status, method and path statistics |
| F5 | Bucket traffic by hour and identify the busiest period |
| F6 | Detect and rank anomalies by severity, with supporting evidence |
| F7 | Render reports as text, HTML, JSON and CSV |
| F8 | Return meaningful exit codes for use in scripts and CI |

**Non-functional requirements**

| ID | Requirement |
|---|---|
| N1 | No third-party dependencies |
| N2 | Constant memory usage regardless of file size |
| N3 | Modular design — new rules or formats without changing existing modules |
| N4 | Automated tests for every module |
| N5 | Readable output in both light and dark environments |

---

## 6. Technology used

| Component | Choice | Why |
|---|---|---|
| Language | Python 3.10+ | Required by the internship; modern typing syntax (`X \| None`, `slots=True`) |
| Parsing | `re` with a verbose compiled pattern | One readable pattern for both log formats |
| Data model | `dataclasses` | Concise, typed, immutable records |
| Aggregation | `collections.Counter`, `defaultdict` | Idiomatic O(1) counting |
| Statistics | `statistics.fmean`, `pstdev` | Z-score spike detection, no NumPy needed |
| Time handling | `datetime`, `timezone` | Timezone-aware timestamps from log offsets |
| Compression | `gzip` | Rotated logs are usually `.gz` |
| CLI | `argparse` | Standard help text, validation and exit codes |
| Output | `json`, `csv`, `html.escape`, hand-written CSS | Self-contained reports |
| Testing | `unittest` | Bundled with Python — keeps the zero-dependency promise |

---

## 7. System design

### 7.1 Architecture

The application is a four-stage pipeline. Each stage depends only on the stage
before it, which is what keeps the modules independently testable.

```
   access.log (.gz)
          │
          ▼
   ┌──────────────┐   yields LogEntry objects lazily
   │  parser.py   │──────────────────────────────────┐
   └──────────────┘                                  │
          │ ParseStats (lines, malformed)            │
          ▼                                          ▼
   ┌──────────────┐   single pass          ┌──────────────────┐
   │ analyzer.py  │───────────────────────▶│   TrafficStats   │
   └──────────────┘                        └──────────────────┘
                                                     │
                              ┌──────────────────────┴───────────┐
                              ▼                                  ▼
                     ┌──────────────┐                    ┌──────────────┐
                     │ anomalies.py │  list[Anomaly]     │  report.py   │
                     └──────────────┘───────────────────▶└──────────────┘
                                                                 │
                                              text │ HTML │ JSON │ CSV
                                                                 ▼
                                                     ┌──────────────┐
                                                     │    cli.py    │
                                                     └──────────────┘
```

### 7.2 Module responsibilities

| Module | Lines | Responsibility |
|---|---:|---|
| `models.py` | 72 | `LogEntry`, `ParseStats`, `Anomaly` dataclasses and their derived properties |
| `parser.py` | 104 | Regex parsing, timestamp/offset handling, gzip support, generator streaming |
| `analyzer.py` | 109 | Single-pass fold of entries into a `TrafficStats` object |
| `anomalies.py` | 196 | Seven independent detection rules plus the tunable thresholds |
| `report.py` | 271 | Text, HTML, JSON and CSV renderers |
| `cli.py` | 94 | Argument parsing, error handling, exit codes |

### 7.3 Data structures

```python
@dataclass(frozen=True, slots=True)
class LogEntry:
    ip: str
    timestamp: datetime      # timezone-aware
    method: str
    path: str
    protocol: str
    status: int
    size: int
    referrer: str = "-"
    user_agent: str = "-"
```

`frozen=True` makes entries immutable — an entry can never be modified after
parsing — and `slots=True` removes the per-instance `__dict__`, which matters
when millions of records pass through the pipeline.

---

## 8. Implementation highlights

### 8.1 Streaming instead of loading

The single most important design decision. `parse_file()` is a generator, so
entries are produced and consumed one at a time and are garbage-collected
immediately:

```python
def parse_file(path, stats=None):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"log file not found: {path}")
    with _open(path) as handle:          # gzip.open() for .gz
        yield from parse_lines(handle, stats)
```

`analyze(parse_file(...))` therefore never holds more than one `LogEntry` in
memory. Peak memory depends on the number of *distinct* IPs and paths, not on
the size of the file.

### 8.2 One regex for two log formats

The referrer and user-agent group is optional, so the same pattern matches both
Common and Combined Log Format:

```python
LOG_PATTERN = re.compile(r"""^
    (?P<ip>\S+)\s+ (?P<ident>\S+)\s+ (?P<user>\S+)\s+
    \[(?P<time>[^\]]+)\]\s+
    "(?P<method>[A-Z]+)\s+(?P<path>\S+)(?:\s+(?P<protocol>[^"]*))?"\s+
    (?P<status>\d{3})\s+ (?P<size>\d+|-)
    (?:\s+"(?P<referrer>[^"]*)"\s+"(?P<agent>[^"]*)")?
    \s*$""", re.VERBOSE)
```

Timezone offsets such as `+0530` are converted into real `timezone` objects, so
logs from servers in different regions are comparable.

### 8.3 Fault tolerance

A single corrupt line must never abort a two-hour analysis. `parse_lines()`
catches the parse failure, records the line, and continues:

```python
try:
    entry = parse_line(line)
except LogParseError:
    stats.record_bad(line)     # counts it, keeps the first 5 as samples
    continue
stats.parsed += 1
yield entry
```

Every report prints the parse success rate, so a silently mis-configured log
format shows up as an obviously low percentage instead of wrong numbers.

### 8.4 Anomaly rules as plain functions

Each rule has the signature `TrafficStats -> list[Anomaly]`, and the active set
is a single tuple:

```python
DEFAULT_RULES = (
    high_error_rate, error_heavy_clients, path_scanning,
    sensitive_path_probes, injection_attempts, traffic_spikes, bot_dominance,
)

def detect(stats, rules=DEFAULT_RULES):
    findings = []
    for rule in rules:
        findings.extend(rule(stats))
    return sorted(findings, key=lambda a: a.sort_key())
```

Adding a rule is one function and one tuple entry — no other module changes.
Tests can also pass a custom `rules` tuple to isolate a single rule.

**Rules implemented**

| Rule | Severity | Trigger |
|---|---|---|
| `high_error_rate` | medium/high | ≥10% of requests are 4xx/5xx (high above 25%) |
| `server_errors` | high | ≥1% of requests are 5xx |
| `error_heavy_clients` | medium | One IP with ≥15 errors and ≥50% of its requests failing |
| `path_scanning` | medium | One IP requesting ≥25 distinct paths |
| `sensitive_path_probes` | high | Requests for `.env`, `.git`, `wp-admin`, `phpmyadmin`, `.sql`, `.bak` … |
| `injection_attempts` | high | SQL-injection, XSS or path-traversal patterns, including URL-encoded forms |
| `traffic_spikes` | medium | An hour more than 3σ above the mean hourly volume |
| `bot_dominance` | low | ≥40% of requests from bots, crawlers, `curl`, `python-requests` |

### 8.5 Statistical spike detection

A fixed "more than N requests per hour" threshold is wrong for every site except
the one it was tuned on. Instead, each hour is scored against the log's own
distribution:

```python
mean  = statistics.fmean(counts)
sigma = statistics.pstdev(counts)
z = (count - mean) / sigma
if z >= 3.0:
    ...flag it
```

The rule requires at least four hourly buckets and a non-zero standard
deviation, so it stays silent on short or perfectly flat logs rather than
producing noise.

### 8.6 Injection detection with encoded payloads

Real attack traffic is URL-encoded, so `union select` rarely appears literally.
The pattern treats `%20`, `+` and whitespace as equivalent:

```python
_SP = r"(?:\s|\+|%20)+"
INJECTION_HINT = re.compile(
    rf"(union{_SP}select|select{_SP}.*{_SP}from|<script|%3cscript"
    r"|\.\./|%2e%2e|;\s*cat\s|/bin/sh|\bor\b\s*1\s*=\s*1)", re.IGNORECASE)
```

This came directly out of testing: the first version of the rule matched only
literal whitespace, so the unit test using an encoded `%20UNION%20SELECT`
payload failed and exposed the gap before release.

### 8.7 HTML dashboard without a template engine

The HTML report is a single self-contained file — no CSS framework, no CDN, no
JavaScript — built with `str.format` and CSS custom properties. It adapts to the
reader's light or dark theme through `prefers-color-scheme`, and all
log-derived values pass through `html.escape()`, since a user-agent string is
attacker-controlled text and must never be injected raw into a page.

---

## 9. Testing

Testing used the `unittest` framework, run with:

```bash
python -m unittest discover -s tests -v
```

**Result: 40 tests, 40 passed, 0 failed (0.2 s).**

| Test module | Tests | Coverage focus |
|---|---:|---|
| `test_parser.py` | 12 | Both log formats, `+`/`-` timezone offsets, missing offsets, `-` byte sizes, query strings, garbage lines, malformed-line accounting, lazy iteration |
| `test_analyzer.py` | 8 | Totals, error rate, time window, every counter, hourly buckets, per-IP detail, empty input |
| `test_anomalies.py` | 13 | Each rule firing *and* staying quiet on clean traffic, severity ordering |
| `test_cli.py` | 7 | Text/HTML/JSON/CSV output end to end, exit codes 0/1/2, missing file, file with no valid entries |

Negative tests were treated as equally important as positive ones: a detector
that flags everything is as useless as one that flags nothing, so every rule has
a paired test proving it does *not* fire on healthy traffic.

**Two defects found and fixed by the suite**

1. `injection_attempts` missed URL-encoded payloads (Section 8.6).
2. `traffic_spikes` under-reported when a very large outlier inflated the
   standard deviation in a short log; the rule now requires a minimum number of
   buckets, and the test uses a realistic baseline length.

### Reproducible test data

`scripts/generate_sample_log.py` builds a 1,500-line sample log from a fixed
random seed, so it is byte-identical on every machine. It deliberately plants:

- a path scanner hitting `.env`, `wp-login.php`, `phpmyadmin` and 60 admin URLs
- a broken client looping on a dead endpoint with 100% failures
- a download burst concentrated in one hour
- two malformed lines

This guarantees every code path has something to find during a demo.

---

## 10. Results

Running the tool against the sample log:

```
 OVERVIEW
------------------------------------------------------------------------------
  Requests parsed        : 1,500
  Unique client IPs      : 62
  Data transferred       : 98.9 MB
  Average response size  : 67.5 KB
  Error rate (4xx/5xx)   : 12.60%
  Requests per hour      : 93.8
  Time window            : 2026-08-04 06:00 → 2026-08-04 21:59 (16.0 h)
  Busiest hour           : 2026-08-04 14:00 (136 requests)
  Lines read / malformed : 1,502 / 2 (99.9% parsed)

 ANOMALIES
------------------------------------------------------------------------------
  [HIGH]   site-wide - 35 sensitive path(s) probed (94 requests)
  [HIGH]   site-wide - 2 request path(s) contain injection/traversal patterns
  [MEDIUM] 103.21.58.9 - 46/46 requests failed (100%)
  [MEDIUM] 185.220.101.44 - 97/97 requests failed (100%)
  [MEDIUM] 185.220.101.44 - requested 36 distinct paths - looks like enumeration
  [MEDIUM] 2026-08-04 14:00 - 136 requests vs 94 hourly average (z=3.8)
  [MEDIUM] site-wide - 12.6% of requests returned 4xx/5xx
  [LOW]    site-wide - 47% of traffic came from bots/automated agents
```

All eight planted conditions were detected, ranked by severity, with the
evidence that triggered each one. The two malformed lines were counted rather
than crashing the run. Full outputs are saved in `docs/sample_report.txt` and
`docs/sample_report.html`.

---

## 11. Challenges faced

| Challenge | Resolution |
|---|---|
| One regex for two log formats | Made the referrer/user-agent group optional rather than maintaining two patterns |
| Timezone offsets in log timestamps | `strptime` ignores `+0530`; parsed the offset manually into a `timezone` object so entries are comparable |
| Memory on large files | Replaced `readlines()` with generators throughout; memory now scales with distinct keys, not file size |
| Spike threshold that suits any site | Replaced the fixed threshold with a z-score over the log's own hourly distribution |
| Encoded attack payloads slipping through | Rewrote the injection pattern to treat `%20`, `+` and whitespace as equivalent |
| Escaping in HTML output | Ran every log-derived value through `html.escape()` — user agents are attacker-controlled |
| Rules becoming tangled with rendering | Kept each rule a pure function returning `Anomaly` objects; renderers never re-compute anything |

---

## 12. Learning outcomes

- **Python packaging and structure** — modules, `__main__.py`, `pyproject.toml`,
  console entry points, and the discipline of one responsibility per module.
- **Generators and laziness** — where they matter, and the practical difference
  between `return [...]` and `yield`.
- **Dataclasses** — `frozen`, `slots`, derived properties, and why immutable
  records simplify reasoning.
- **Regular expressions** — verbose mode, named groups, optional groups, and the
  limits of regex on real-world input.
- **Applied statistics** — mean, population standard deviation and z-scores as a
  practical alternative to hand-tuned thresholds.
- **Testing discipline** — writing negative tests, and the experience of tests
  catching two genuine defects before release.
- **Defensive programming** — treating all input as hostile, meaningful exit
  codes, and escaping output.
- **Documentation** — a README someone else can follow without asking questions.

---

## 13. Future scope

1. **Live tailing** (`--follow`) with a rolling window for near-real-time alerts.
2. **GeoIP and ASN enrichment** to attribute traffic by country or hosting provider.
3. **Session reconstruction** — grouping requests by IP and user agent to derive
   visit paths and bounce rates.
4. **Baseline comparison** — storing yesterday's JSON report and flagging
   day-over-day deviations instead of only within-file anomalies.
5. **Additional log formats** — Nginx `error.log`, IIS W3C, JSON-structured logs.
6. **Notification hooks** — send high-severity findings to email or a webhook.
7. **Parallel parsing** with `multiprocessing` for multi-gigabyte archives.

---

## 14. Conclusion

The project set out to build a complete, useful Python application within a
one-month internship, and it delivers a tool that turns an unreadable access log
into an actionable report in under a second, detects eight classes of
operational and security problem, never crashes on bad input, and runs anywhere
Python is installed.

More valuable than the tool itself was the process: designing a pipeline before
writing code, keeping modules independent enough to test in isolation, letting a
test suite find real defects, and documenting the result so that someone else
can pick it up. Those habits are the part of this internship I expect to carry
into every project that follows.

---

## 15. References

1. Apache HTTP Server Documentation — *Log Files, Combined Log Format*.
   https://httpd.apache.org/docs/current/logs.html
2. Python Software Foundation — *Standard Library Reference* (`re`, `dataclasses`,
   `collections`, `statistics`, `argparse`, `gzip`, `csv`, `json`, `unittest`).
   https://docs.python.org/3/library/
3. Nginx Documentation — *ngx_http_log_module*.
   https://nginx.org/en/docs/http/ngx_http_log_module.html
4. OWASP Foundation — *SQL Injection* and *Path Traversal* attack references.
   https://owasp.org/www-community/attacks/
5. PEP 8 — *Style Guide for Python Code*; PEP 484 — *Type Hints*.
   https://peps.python.org/

---

## Annexure — Internship credentials

| Document | Reference |
|---|---|
| Internship Offer Letter | Issued 08/07/2026 by Dr. Anurag Shrivastava, Talent Acquisition Manager, Codec Technologies India |
| Internship Certificate | Awarded to Samvit Srivastava for completing the 1-Month AICTE & ICAC approved internship as Python Developer Intern, 08/07/2026 – 08/08/2026 |
| AICTE ID | CORPORATE6759d549ce59e1733940553 |
| NCS ID | E19E86-0116588288923 |
| Portal | National Internship Portal, Ministry of Education |

---

**Project repository:** https://github.com/samvit-iilm/python-Internship
**Submitted:** September 2026

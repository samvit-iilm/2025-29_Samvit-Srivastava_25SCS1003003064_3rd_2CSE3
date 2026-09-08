"""Rendering layer: terminal text, HTML and CSV output."""

from __future__ import annotations

import csv
import html
import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .analyzer import TrafficStats
from .models import Anomaly, ParseStats

BAR_CHARS = "█"  # full block


def human_bytes(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024 or unit == "TB":
            return f"{num:.1f} {unit}" if unit != "B" else f"{num:.0f} B"
        num /= 1024
    return f"{num:.1f} TB"


def _bar(value: int, peak: int, width: int = 28) -> str:
    if peak <= 0:
        return ""
    return BAR_CHARS * max(1, round(value / peak * width))


def _table(rows: Iterable[tuple[str, int]], label: str, width: int = 44) -> list[str]:
    rows = list(rows)
    if not rows:
        return [f"  (no {label.lower()})"]
    peak = max(c for _, c in rows)
    out = []
    for name, count in rows:
        shown = name if len(name) <= width else name[: width - 1] + "…"
        out.append(f"  {shown:<{width}} {count:>7}  {_bar(count, peak)}")
    return out


# --------------------------------------------------------------------- text


def render_text(
    stats: TrafficStats,
    anomalies: list[Anomaly],
    parse_stats: ParseStats,
    source: str,
    top: int = 10,
) -> str:
    line = "=" * 78
    thin = "-" * 78
    out: list[str] = [line, f" weblens report  -  {source}", line, ""]

    out += [
        " OVERVIEW",
        thin,
        f"  Requests parsed        : {stats.total_requests:,}",
        f"  Unique client IPs      : {stats.unique_visitors:,}",
        f"  Data transferred       : {human_bytes(stats.total_bytes)}",
        f"  Average response size  : {human_bytes(stats.avg_response_size)}",
        f"  Error rate (4xx/5xx)   : {stats.error_rate:.2f}%",
        f"  Requests per hour      : {stats.requests_per_hour:,.1f}",
    ]
    if stats.first_seen and stats.last_seen:
        out.append(
            f"  Time window            : {stats.first_seen:%Y-%m-%d %H:%M} "
            f"→ {stats.last_seen:%Y-%m-%d %H:%M} ({stats.duration_hours:.1f} h)"
        )
    busiest = stats.busiest_hour()
    if busiest:
        out.append(f"  Busiest hour           : {busiest[0]} ({busiest[1]:,} requests)")
    out.append(
        f"  Lines read / malformed : {parse_stats.total_lines:,} / "
        f"{parse_stats.malformed:,} ({parse_stats.success_rate:.1f}% parsed)"
    )
    out.append("")

    sections = [
        ("STATUS CODES", [(str(s), c) for s, c in sorted(stats.status_counts.items())]),
        ("TOP PATHS", stats.top(stats.path_counts, top)),
        ("TOP CLIENT IPs", stats.top(stats.ip_counts, top)),
        ("HTTP METHODS", sorted(stats.method_counts.items())),
        ("HEAVIEST PATHS (bytes)", stats.top(stats.bytes_by_path, 5)),
        ("TOP USER AGENTS", stats.top(stats.agent_counts, 5)),
    ]
    for title, rows in sections:
        out += [f" {title}", thin, *_table(rows, title), ""]

    out += [" HOURLY TRAFFIC", thin]
    if stats.hourly_hits:
        peak = max(stats.hourly_hits.values())
        for hour, count in sorted(stats.hourly_hits.items()):
            out.append(f"  {hour}  {count:>6}  {_bar(count, peak)}")
    else:
        out.append("  (no data)")
    out.append("")

    out += [" ANOMALIES", thin]
    if not anomalies:
        out.append("  None detected. ✓")
    else:
        marks = {"high": "[HIGH]  ", "medium": "[MEDIUM]", "low": "[LOW]   "}
        for item in anomalies:
            out.append(f"  {marks.get(item.severity, '[?]')} {item.subject} - {item.detail}")
            if item.evidence:
                out.append(f"            evidence: {item.evidence}")
    out += ["", line]
    return "\n".join(out)


# --------------------------------------------------------------------- html

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>weblens report - {source}</title>
<style>
 :root {{ color-scheme: light dark; --fg:#1b1f24; --bg:#f6f7f9; --card:#fff;
          --muted:#6b7280; --line:#e3e6ea; --accent:#2563eb; }}
 @media (prefers-color-scheme: dark) {{
   :root {{ --fg:#e6e8eb; --bg:#14171a; --card:#1c2024; --muted:#9aa3ad; --line:#2c3238; }} }}
 * {{ box-sizing:border-box; }}
 body {{ margin:0; padding:32px; background:var(--bg); color:var(--fg);
        font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
 h1 {{ font-size:24px; margin:0 0 4px; }}
 .sub {{ color:var(--muted); margin-bottom:28px; font-size:13px; }}
 .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:14px; margin-bottom:28px; }}
 .kpi {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px; }}
 .kpi .v {{ font-size:24px; font-weight:650; }}
 .kpi .l {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.05em; }}
 section {{ background:var(--card); border:1px solid var(--line); border-radius:10px;
            padding:18px 20px; margin-bottom:20px; }}
 h2 {{ font-size:15px; margin:0 0 12px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }}
 table {{ width:100%; border-collapse:collapse; font-size:14px; }}
 td, th {{ padding:6px 8px; text-align:left; border-bottom:1px solid var(--line); }}
 th {{ color:var(--muted); font-weight:600; font-size:12px; }}
 td.n {{ text-align:right; font-variant-numeric:tabular-nums; width:90px; }}
 .bar {{ background:var(--accent); height:8px; border-radius:4px; display:block; }}
 .barcell {{ width:38%; }}
 .a {{ border-left:4px solid var(--line); padding:8px 12px; margin-bottom:8px; border-radius:0 6px 6px 0; }}
 .a.high {{ border-color:#dc2626; }} .a.medium {{ border-color:#d97706; }} .a.low {{ border-color:#0891b2; }}
 .a b {{ display:block; }} .a span {{ color:var(--muted); font-size:13px; }}
 .ok {{ color:#059669; }}
 .scroll {{ overflow-x:auto; }}
 footer {{ color:var(--muted); font-size:12px; margin-top:24px; }}
</style></head><body>
<h1>weblens report</h1>
<div class="sub">{source} &middot; generated {generated}</div>
<div class="grid">{kpis}</div>
{sections}
<footer>Generated by weblens {version} - Python standard library only.</footer>
</body></html>
"""


def _kpi(label: str, value: str) -> str:
    return f'<div class="kpi"><div class="v">{html.escape(value)}</div>' \
           f'<div class="l">{html.escape(label)}</div></div>'


def _html_table(title: str, rows: list[tuple[str, int]]) -> str:
    if not rows:
        return f"<section><h2>{html.escape(title)}</h2><p>No data.</p></section>"
    peak = max(c for _, c in rows) or 1
    body = "".join(
        f"<tr><td>{html.escape(str(name))}</td><td class='n'>{count:,}</td>"
        f"<td class='barcell'><span class='bar' style='width:{count / peak * 100:.1f}%'></span></td></tr>"
        for name, count in rows
    )
    return (
        f"<section><h2>{html.escape(title)}</h2><div class='scroll'><table>"
        f"<tr><th>Item</th><th class='n'>Count</th><th></th></tr>{body}</table></div></section>"
    )


def render_html(
    stats: TrafficStats, anomalies: list[Anomaly], parse_stats: ParseStats, source: str, top: int = 10
) -> str:
    from . import __version__

    kpis = "".join(
        [
            _kpi("Requests", f"{stats.total_requests:,}"),
            _kpi("Unique IPs", f"{stats.unique_visitors:,}"),
            _kpi("Error rate", f"{stats.error_rate:.2f}%"),
            _kpi("Transferred", human_bytes(stats.total_bytes)),
            _kpi("Requests / hour", f"{stats.requests_per_hour:,.0f}"),
            _kpi("Anomalies", str(len(anomalies))),
        ]
    )

    if anomalies:
        items = "".join(
            f"<div class='a {a.severity}'><b>{html.escape(a.subject)} &mdash; {html.escape(a.detail)}</b>"
            + (f"<span>{html.escape(a.evidence)}</span>" if a.evidence else "")
            + "</div>"
            for a in anomalies
        )
    else:
        items = "<p class='ok'>No anomalies detected.</p>"

    sections = [f"<section><h2>Anomalies</h2>{items}</section>"]
    sections.append(_html_table("Status codes", [(str(s), c) for s, c in sorted(stats.status_counts.items())]))
    sections.append(_html_table("Top paths", stats.top(stats.path_counts, top)))
    sections.append(_html_table("Top client IPs", stats.top(stats.ip_counts, top)))
    sections.append(_html_table("Hourly traffic", sorted(stats.hourly_hits.items())))
    sections.append(_html_table("HTTP methods", sorted(stats.method_counts.items())))
    sections.append(_html_table("Top user agents", stats.top(stats.agent_counts, 5)))
    sections.append(
        "<section><h2>Parsing</h2><p>"
        f"{parse_stats.total_lines:,} lines read, {parse_stats.parsed:,} parsed, "
        f"{parse_stats.malformed:,} malformed ({parse_stats.success_rate:.1f}% success)."
        "</p></section>"
    )

    return HTML_TEMPLATE.format(
        source=html.escape(source),
        generated=datetime.now().strftime("%Y-%m-%d %H:%M"),
        kpis=kpis,
        sections="".join(sections),
        version=__version__,
    )


# ---------------------------------------------------------------- json / csv


def render_json(stats: TrafficStats, anomalies: list[Anomaly], parse_stats: ParseStats, source: str) -> str:
    payload = {
        "source": source,
        "generated": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total_requests": stats.total_requests,
            "unique_ips": stats.unique_visitors,
            "total_bytes": stats.total_bytes,
            "error_rate_pct": round(stats.error_rate, 2),
            "requests_per_hour": round(stats.requests_per_hour, 2),
            "first_seen": stats.first_seen.isoformat() if stats.first_seen else None,
            "last_seen": stats.last_seen.isoformat() if stats.last_seen else None,
        },
        "parsing": {
            "lines": parse_stats.total_lines,
            "parsed": parse_stats.parsed,
            "malformed": parse_stats.malformed,
        },
        "status_counts": {str(k): v for k, v in sorted(stats.status_counts.items())},
        "top_paths": stats.top(stats.path_counts, 20),
        "top_ips": stats.top(stats.ip_counts, 20),
        "hourly": dict(sorted(stats.hourly_hits.items())),
        "anomalies": [
            {"kind": a.kind, "severity": a.severity, "subject": a.subject,
             "detail": a.detail, "evidence": a.evidence}
            for a in anomalies
        ],
    }
    return json.dumps(payload, indent=2)


def write_csv(stats: TrafficStats, path: str | Path) -> Path:
    """Dump the per-path breakdown for use in Excel / pandas."""
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["path", "requests", "bytes"])
        for name, count in stats.path_counts.most_common():
            writer.writerow([name, count, stats.bytes_by_path[name]])
    return path

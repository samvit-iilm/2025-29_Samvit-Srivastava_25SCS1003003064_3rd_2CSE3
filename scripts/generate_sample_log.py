#!/usr/bin/env python3
"""Generate a realistic sample access log for testing weblens.

Usage: python scripts/generate_sample_log.py sample_data/access.log 1500
"""

from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta

NORMAL_PATHS = [
    "/", "/index.html", "/about", "/products", "/products/42", "/contact",
    "/static/css/main.css", "/static/js/app.js", "/static/img/hero.png",
    "/api/v1/items", "/api/v1/items/7", "/blog/python-tips", "/favicon.ico",
]
AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 13) Chrome/125.0 Mobile Safari/537.36",
    "Googlebot/2.1 (+http://www.google.com/bot.html)",
    "python-requests/2.31.0",
]
ATTACK_PATHS = [
    "/.env", "/wp-login.php", "/wp-admin/setup-config.php", "/phpmyadmin/index.php",
    "/admin/config.bak", "/../../etc/passwd", "/index.php?id=1%20UNION%20SELECT%201",
    "/backup.sql", "/.git/config",
]


def line(ip, when, method, path, status, size, agent, referrer="-"):
    stamp = when.strftime("%d/%b/%Y:%H:%M:%S +0530")
    return (
        f'{ip} - - [{stamp}] "{method} {path} HTTP/1.1" {status} {size} '
        f'"{referrer}" "{agent}"'
    )


def generate(count: int) -> list[str]:
    rng = random.Random(20260708)  # deterministic output
    start = datetime(2026, 8, 4, 6, 0, 0)
    rows: list[str] = []

    normal_ips = [f"49.36.{rng.randint(1, 250)}.{rng.randint(1, 250)}" for _ in range(60)]
    scanner_ip = "185.220.101.44"
    broken_client = "103.21.58.9"

    for i in range(count):
        when = start + timedelta(seconds=int(i * (16 * 3600 / count)) + rng.randint(0, 20))
        roll = rng.random()

        if roll < 0.80:  # ordinary traffic
            path = rng.choice(NORMAL_PATHS)
            status = rng.choices([200, 200, 200, 304, 404], [70, 10, 10, 7, 3])[0]
            rows.append(
                line(rng.choice(normal_ips), when, "GET", path, status,
                     rng.randint(180, 48000) if status == 200 else 0, rng.choice(AGENTS),
                     rng.choice(["-", "https://www.google.com/", "https://news.ycombinator.com/"]))
            )
        elif roll < 0.88:  # API writes
            status = rng.choices([201, 200, 400, 500], [60, 25, 10, 5])[0]
            rows.append(line(rng.choice(normal_ips), when, "POST", "/api/v1/items", status,
                             rng.randint(60, 900), rng.choice(AGENTS)))
        elif roll < 0.94:  # scanner enumerating many paths
            if rng.random() < 0.5:
                path = rng.choice(ATTACK_PATHS)
            else:
                path = f"/admin/panel{rng.randint(1, 60)}"
            rows.append(line(scanner_ip, when, "GET", path, 404, 0, "curl/8.4.0"))
        elif roll < 0.97:  # broken client hammering a dead endpoint
            rows.append(line(broken_client, when, "GET", "/api/v1/legacy", 404, 0,
                             "python-requests/2.31.0"))
        else:  # burst hour: heavy download traffic
            burst = datetime(2026, 8, 4, 14, rng.randint(0, 59), rng.randint(0, 59))
            rows.append(line(rng.choice(normal_ips), burst, "GET", "/downloads/report.pdf",
                             200, rng.randint(900000, 2500000), rng.choice(AGENTS)))

    rows.append("this line is not a valid log record at all")
    rows.append('10.0.0.1 - - [BAD/TIME:99:99:99 +0000] "GET / HTTP/1.1" 200 12 "-" "-"')
    rows.sort(key=lambda r: r.split("[")[-1][:20] if "[" in r else "")
    return rows


def main() -> int:
    target = sys.argv[1] if len(sys.argv) > 1 else "sample_data/access.log"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
    with open(target, "w", encoding="utf-8") as handle:
        handle.write("\n".join(generate(count)) + "\n")
    print(f"wrote {count} entries (+2 deliberately malformed) to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

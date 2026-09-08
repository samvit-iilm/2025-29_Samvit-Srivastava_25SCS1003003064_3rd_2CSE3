"""Tests for the aggregation layer."""

import unittest

from weblens.analyzer import analyze
from weblens.parser import parse_lines

LINES = [
    '1.1.1.1 - - [08/Sep/2026:10:00:00 +0000] "GET / HTTP/1.1" 200 1000 "-" "Chrome"',
    '1.1.1.1 - - [08/Sep/2026:10:30:00 +0000] "GET /a HTTP/1.1" 404 0 "-" "Chrome"',
    '2.2.2.2 - - [08/Sep/2026:11:00:00 +0000] "POST /api HTTP/1.1" 500 200 "-" "curl/8.4"',
    '2.2.2.2 - - [08/Sep/2026:12:00:00 +0000] "GET / HTTP/1.1" 200 3000 "-" "curl/8.4"',
]


class TestAnalyze(unittest.TestCase):
    def setUp(self):
        self.stats = analyze(parse_lines(LINES))

    def test_totals(self):
        self.assertEqual(self.stats.total_requests, 4)
        self.assertEqual(self.stats.total_bytes, 4200)
        self.assertEqual(self.stats.unique_visitors, 2)

    def test_error_rate(self):
        self.assertEqual(self.stats.error_count, 2)
        self.assertEqual(self.stats.error_rate, 50.0)

    def test_time_window(self):
        self.assertEqual(self.stats.duration_hours, 2.0)
        self.assertEqual(self.stats.requests_per_hour, 2.0)
        self.assertEqual(self.stats.first_seen.hour, 10)
        self.assertEqual(self.stats.last_seen.hour, 12)

    def test_counters(self):
        self.assertEqual(self.stats.method_counts["GET"], 3)
        self.assertEqual(self.stats.path_counts["/"], 2)
        self.assertEqual(self.stats.ip_counts["1.1.1.1"], 2)
        self.assertEqual(self.stats.status_classes["2xx"], 2)
        self.assertEqual(self.stats.bytes_by_path["/"], 4000)

    def test_hourly_buckets(self):
        self.assertEqual(len(self.stats.hourly_hits), 3)
        self.assertEqual(self.stats.busiest_hour()[1], 2)

    def test_per_ip_detail(self):
        self.assertEqual(self.stats.errors_by_ip["1.1.1.1"], 1)
        self.assertEqual(self.stats.paths_by_ip["2.2.2.2"], {"/api", "/"})

    def test_average_size(self):
        self.assertEqual(self.stats.avg_response_size, 1050.0)

    def test_empty_input_is_safe(self):
        empty = analyze([])
        self.assertEqual(empty.total_requests, 0)
        self.assertEqual(empty.error_rate, 0.0)
        self.assertEqual(empty.avg_response_size, 0.0)
        self.assertIsNone(empty.busiest_hour())


if __name__ == "__main__":
    unittest.main()

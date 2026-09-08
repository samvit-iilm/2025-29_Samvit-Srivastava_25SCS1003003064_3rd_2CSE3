"""Tests for the log line parser."""

import unittest
from datetime import timezone

from weblens.models import ParseStats
from weblens.parser import LogParseError, parse_line, parse_lines, parse_timestamp

COMBINED = (
    '66.249.66.1 - - [08/Sep/2026:10:15:32 +0530] "GET /index.html HTTP/1.1" '
    '200 5120 "https://google.com/" "Mozilla/5.0"'
)
COMMON = '10.0.0.7 - - [08/Sep/2026:10:15:32 +0000] "POST /api/items HTTP/1.1" 201 431'


class TestParseTimestamp(unittest.TestCase):
    def test_positive_offset(self):
        moment = parse_timestamp("08/Sep/2026:10:15:32 +0530")
        self.assertEqual(moment.utcoffset().total_seconds(), 5.5 * 3600)

    def test_negative_offset(self):
        moment = parse_timestamp("10/Oct/2000:13:55:36 -0700")
        self.assertEqual(moment.utcoffset().total_seconds(), -7 * 3600)

    def test_missing_offset_defaults_to_utc(self):
        self.assertEqual(parse_timestamp("08/Sep/2026:10:15:32").tzinfo, timezone.utc)


class TestParseLine(unittest.TestCase):
    def test_combined_format(self):
        entry = parse_line(COMBINED)
        self.assertEqual(entry.ip, "66.249.66.1")
        self.assertEqual(entry.method, "GET")
        self.assertEqual(entry.path, "/index.html")
        self.assertEqual(entry.status, 200)
        self.assertEqual(entry.size, 5120)
        self.assertEqual(entry.user_agent, "Mozilla/5.0")

    def test_common_format_without_referrer(self):
        entry = parse_line(COMMON)
        self.assertEqual(entry.status, 201)
        self.assertEqual(entry.referrer, "-")

    def test_dash_size_becomes_zero(self):
        raw = COMBINED.replace(" 200 5120 ", " 304 - ")
        self.assertEqual(parse_line(raw).size, 0)

    def test_status_helpers(self):
        self.assertTrue(parse_line(COMBINED.replace(" 200 ", " 404 ")).is_error)
        self.assertTrue(parse_line(COMBINED.replace(" 200 ", " 503 ")).is_server_error)
        self.assertFalse(parse_line(COMBINED).is_error)
        self.assertEqual(parse_line(COMBINED).status_class, "2xx")

    def test_query_string_is_preserved(self):
        raw = COMBINED.replace("/index.html", "/search?q=python&page=2")
        self.assertEqual(parse_line(raw).path, "/search?q=python&page=2")

    def test_garbage_raises(self):
        with self.assertRaises(LogParseError):
            parse_line("not a log line")

    def test_bad_timestamp_raises(self):
        with self.assertRaises(LogParseError):
            parse_line('1.1.1.1 - - [99/Xyz/2026:99:99:99 +0000] "GET / HTTP/1.1" 200 1')


class TestParseLines(unittest.TestCase):
    def test_skips_bad_lines_and_counts_them(self):
        stats = ParseStats()
        entries = list(parse_lines([COMBINED, "garbage", "", COMMON], stats))
        self.assertEqual(len(entries), 2)
        self.assertEqual(stats.total_lines, 3)   # blank lines are not counted
        self.assertEqual(stats.parsed, 2)
        self.assertEqual(stats.malformed, 1)
        self.assertAlmostEqual(stats.success_rate, 66.67, places=1)

    def test_returns_a_lazy_iterator(self):
        result = parse_lines([COMBINED])
        self.assertFalse(isinstance(result, list))
        self.assertEqual(next(result).ip, "66.249.66.1")


if __name__ == "__main__":
    unittest.main()

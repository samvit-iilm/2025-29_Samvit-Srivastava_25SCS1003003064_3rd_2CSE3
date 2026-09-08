"""Tests for the anomaly detection rules."""

import unittest

from weblens.analyzer import analyze
from weblens.anomalies import (
    bot_dominance,
    detect,
    error_heavy_clients,
    high_error_rate,
    injection_attempts,
    path_scanning,
    sensitive_path_probes,
    traffic_spikes,
)
from weblens.parser import parse_lines


def make(ip="1.1.1.1", path="/", status=200, hour=10, minute=0, agent="Chrome", size=100):
    return (
        f'{ip} - - [08/Sep/2026:{hour:02d}:{minute:02d}:00 +0000] '
        f'"GET {path} HTTP/1.1" {status} {size} "-" "{agent}"'
    )


def stats_for(lines):
    return analyze(parse_lines(lines))


class TestRules(unittest.TestCase):
    def test_high_error_rate_fires(self):
        lines = [make(status=500) for _ in range(5)] + [make() for _ in range(5)]
        found = high_error_rate(stats_for(lines))
        kinds = {a.kind for a in found}
        self.assertIn("high_error_rate", kinds)
        self.assertIn("server_errors", kinds)

    def test_healthy_traffic_is_quiet(self):
        lines = [make(minute=i % 60) for i in range(50)]
        self.assertEqual(high_error_rate(stats_for(lines)), [])

    def test_error_heavy_client(self):
        lines = [make(ip="9.9.9.9", status=401, minute=i) for i in range(20)]
        found = error_heavy_clients(stats_for(lines))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].subject, "9.9.9.9")

    def test_error_heavy_client_needs_enough_volume(self):
        lines = [make(ip="9.9.9.9", status=401) for _ in range(5)]
        self.assertEqual(error_heavy_clients(stats_for(lines)), [])

    def test_path_scanning(self):
        lines = [make(ip="8.8.8.8", path=f"/p{i}", status=404) for i in range(30)]
        found = path_scanning(stats_for(lines))
        self.assertEqual(len(found), 1)
        self.assertIn("30 distinct paths", found[0].detail)

    def test_sensitive_paths(self):
        found = sensitive_path_probes(stats_for([make(path="/.env"), make(path="/wp-login.php")]))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].severity, "high")

    def test_injection_patterns(self):
        found = injection_attempts(stats_for([make(path="/x?id=1%20UNION%20SELECT%201")]))
        self.assertEqual(len(found), 1)

    def test_clean_paths_do_not_trigger(self):
        clean = stats_for([make(path="/about"), make(path="/products/42")])
        self.assertEqual(sensitive_path_probes(clean), [])
        self.assertEqual(injection_attempts(clean), [])

    def test_traffic_spike(self):
        # sixteen quiet hours, then one hour with twenty times the traffic
        lines = [make(hour=h, minute=m) for h in range(0, 16) for m in range(3)]
        lines += [make(hour=16, minute=m) for m in range(60)]
        found = traffic_spikes(stats_for(lines))
        self.assertTrue(any(a.subject.endswith("16:00") for a in found))

    def test_flat_traffic_has_no_spike(self):
        lines = [make(hour=h, minute=m) for h in range(8, 16) for m in range(5)]
        self.assertEqual(traffic_spikes(stats_for(lines)), [])

    def test_bot_dominance(self):
        lines = [make(agent="Googlebot/2.1") for _ in range(8)] + [make() for _ in range(2)]
        found = bot_dominance(stats_for(lines))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].severity, "low")


class TestDetect(unittest.TestCase):
    def test_results_are_sorted_by_severity(self):
        lines = (
            [make(ip="8.8.8.8", path=f"/p{i}", status=404) for i in range(30)]
            + [make(path="/.env", agent="curl/8.4") for _ in range(5)]
        )
        found = detect(stats_for(lines))
        severities = [a.severity for a in found]
        self.assertEqual(severities, sorted(severities, key=lambda s: {"high": 0, "medium": 1, "low": 2}[s]))
        self.assertTrue(found and found[0].severity == "high")

    def test_no_findings_on_clean_log(self):
        lines = [make(path="/about", minute=i % 60) for i in range(40)]
        self.assertEqual(detect(stats_for(lines)), [])


if __name__ == "__main__":
    unittest.main()

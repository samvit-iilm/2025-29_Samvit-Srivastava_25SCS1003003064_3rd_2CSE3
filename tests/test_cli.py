"""End-to-end tests for the CLI."""

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from weblens.cli import main

SAMPLE = Path(__file__).resolve().parent.parent / "sample_data" / "access.log"


class TestCli(unittest.TestCase):
    def test_text_report_to_stdout(self):
        buffer = StringIO()
        with redirect_stdout(buffer):
            code = main([str(SAMPLE)])
        output = buffer.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("OVERVIEW", output)
        self.assertIn("ANOMALIES", output)

    def test_html_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "report.html"
            with redirect_stdout(StringIO()):
                code = main([str(SAMPLE), "--format", "html", "-o", str(target), "-q"])
            self.assertEqual(code, 0)
            body = target.read_text(encoding="utf-8")
            self.assertTrue(body.startswith("<!DOCTYPE html>"))
            self.assertIn("weblens report", body)

    def test_json_output_is_valid(self):
        buffer = StringIO()
        with redirect_stdout(buffer):
            main([str(SAMPLE), "--format", "json"])
        payload = json.loads(buffer.getvalue())
        self.assertIn("summary", payload)
        self.assertGreater(payload["summary"]["total_requests"], 0)

    def test_csv_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "paths.csv"
            with redirect_stdout(StringIO()):
                main([str(SAMPLE), "-o", str(Path(tmp) / "r.txt"), "--csv", str(csv_path), "-q"])
            rows = csv_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(rows[0], "path,requests,bytes")
            self.assertGreater(len(rows), 5)

    def test_fail_on_anomaly_exit_code(self):
        with redirect_stdout(StringIO()):
            code = main([str(SAMPLE), "--fail-on-anomaly", "-o", "/dev/null", "-q"])
        self.assertEqual(code, 2)

    def test_missing_file_is_reported(self):
        err = StringIO()
        with redirect_stderr(err):
            code = main(["does_not_exist.log"])
        self.assertEqual(code, 1)
        self.assertIn("not found", err.getvalue())

    def test_file_with_no_valid_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.log"
            bad.write_text("nonsense\nmore nonsense\n", encoding="utf-8")
            err = StringIO()
            with redirect_stderr(err):
                code = main([str(bad)])
            self.assertEqual(code, 1)
            self.assertIn("no valid log entries", err.getvalue())


if __name__ == "__main__":
    unittest.main()

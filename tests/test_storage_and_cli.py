"""Tests for the JSON storage layer and the command line interface."""

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from expense_tracker import storage
from expense_tracker.cli import main


class TestStorage(unittest.TestCase):
    def test_missing_file_gives_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(storage.load(Path(tmp) / "nope.json"), [])

    def test_save_then_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            rows = [{"id": 1, "amount": 10.0, "category": "food", "note": "", "date": "2026-08-01"}]
            storage.save(rows, path)
            self.assertEqual(storage.load(path), rows)

    def test_broken_json_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(ValueError):
                storage.load(path)

    def test_next_id_starts_at_one(self):
        self.assertEqual(storage.next_id([]), 1)


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / "expenses.json"

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args):
        out = StringIO()
        with redirect_stdout(out):
            code = main(["--file", str(self.data), *args])
        return code, out.getvalue()

    def test_add_then_list(self):
        code, _ = self.run_cli("add", "120", "food", "-n", "lunch", "-d", "2026-08-05")
        self.assertEqual(code, 0)
        code, output = self.run_cli("list")
        self.assertIn("food", output)
        self.assertIn("lunch", output)

    def test_add_writes_the_file(self):
        self.run_cli("add", "99.5", "travel")
        rows = json.loads(self.data.read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["amount"], 99.5)

    def test_delete(self):
        self.run_cli("add", "50", "food")
        code, output = self.run_cli("delete", "1")
        self.assertEqual(code, 0)
        self.assertIn("Deleted #1", output)
        self.assertEqual(json.loads(self.data.read_text(encoding="utf-8")), [])

    def test_delete_unknown_id_returns_error(self):
        err = StringIO()
        with redirect_stderr(err), redirect_stdout(StringIO()):
            code = main(["--file", str(self.data), "delete", "42"])
        self.assertEqual(code, 1)
        self.assertIn("no expense with id 42", err.getvalue())

    def test_negative_amount_returns_error(self):
        err = StringIO()
        with redirect_stderr(err), redirect_stdout(StringIO()):
            code = main(["--file", str(self.data), "add", "-5", "food"])
        self.assertEqual(code, 1)

    def test_summary_shows_totals(self):
        self.run_cli("add", "100", "food", "-d", "2026-08-01")
        self.run_cli("add", "300", "rent", "-d", "2026-08-02")
        _, output = self.run_cli("summary")
        self.assertIn("Total spent", output)
        self.assertIn("rent", output)
        self.assertIn("400.00", output)

    def test_list_on_empty_file(self):
        _, output = self.run_cli("list")
        self.assertIn("No expenses found", output)

    def test_export_csv(self):
        self.run_cli("add", "75", "books", "-n", "dsa book")
        target = Path(self.tmp.name) / "out.csv"
        code, _ = self.run_cli("export", str(target))
        self.assertEqual(code, 0)
        lines = target.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], "id,date,category,amount,note")
        self.assertIn("books", lines[1])


if __name__ == "__main__":
    unittest.main()

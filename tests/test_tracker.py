"""Tests for the core expense logic."""

import unittest
from datetime import date

from expense_tracker import tracker


def sample():
    return [
        {"id": 1, "amount": 100.0, "category": "food", "note": "lunch", "date": "2026-07-05"},
        {"id": 2, "amount": 250.0, "category": "books", "note": "notes", "date": "2026-07-20"},
        {"id": 3, "amount": 50.0, "category": "food", "note": "tea", "date": "2026-08-02"},
    ]


class TestAdd(unittest.TestCase):
    def test_add_returns_expense_and_appends(self):
        expenses = sample()
        new = tracker.add_expense(expenses, 75, "travel", "metro", "2026-08-10")
        self.assertEqual(len(expenses), 4)
        self.assertEqual(new["amount"], 75.0)
        self.assertEqual(new["category"], "travel")
        self.assertEqual(new["date"], "2026-08-10")

    def test_date_defaults_to_today(self):
        new = tracker.add_expense([], 10, "food")
        self.assertEqual(new["date"], date.today().strftime("%Y-%m-%d"))

    def test_category_is_lowercased_and_trimmed(self):
        new = tracker.add_expense([], 10, "  FOOD  ")
        self.assertEqual(new["category"], "food")

    def test_ids_reuse_gaps(self):
        expenses = [{"id": 1, "amount": 1, "category": "a", "note": "", "date": "2026-01-01"},
                    {"id": 3, "amount": 1, "category": "a", "note": "", "date": "2026-01-01"}]
        self.assertEqual(tracker.add_expense(expenses, 5, "food")["id"], 2)

    def test_zero_or_negative_amount_rejected(self):
        with self.assertRaises(ValueError):
            tracker.add_expense([], 0, "food")
        with self.assertRaises(ValueError):
            tracker.add_expense([], -20, "food")

    def test_empty_category_rejected(self):
        with self.assertRaises(ValueError):
            tracker.add_expense([], 20, "   ")

    def test_bad_date_rejected(self):
        with self.assertRaises(ValueError):
            tracker.add_expense([], 20, "food", on="08-09-2026")


class TestDelete(unittest.TestCase):
    def test_delete_removes_and_returns(self):
        expenses = sample()
        removed = tracker.delete_expense(expenses, 2)
        self.assertEqual(removed["category"], "books")
        self.assertEqual(len(expenses), 2)

    def test_missing_id_raises(self):
        with self.assertRaises(KeyError):
            tracker.delete_expense(sample(), 99)


class TestFilter(unittest.TestCase):
    def test_filter_by_category(self):
        self.assertEqual(len(tracker.filter_expenses(sample(), category="food")), 2)

    def test_filter_by_month(self):
        self.assertEqual(len(tracker.filter_expenses(sample(), month="2026-07")), 2)

    def test_filter_by_both(self):
        found = tracker.filter_expenses(sample(), category="food", month="2026-08")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["id"], 3)

    def test_results_are_sorted_by_date(self):
        dates = [e["date"] for e in tracker.filter_expenses(sample())]
        self.assertEqual(dates, sorted(dates))

    def test_no_filter_returns_everything(self):
        self.assertEqual(len(tracker.filter_expenses(sample())), 3)


class TestSummaries(unittest.TestCase):
    def test_total(self):
        self.assertEqual(tracker.total(sample()), 400.0)

    def test_total_of_empty_list(self):
        self.assertEqual(tracker.total([]), 0)

    def test_by_category_sorted_biggest_first(self):
        result = tracker.by_category(sample())
        self.assertEqual(list(result), ["books", "food"])
        self.assertEqual(result["food"], 150.0)

    def test_by_month_in_date_order(self):
        result = tracker.by_month(sample())
        self.assertEqual(list(result), ["2026-07", "2026-08"])
        self.assertEqual(result["2026-08"], 50.0)

    def test_biggest(self):
        self.assertEqual(tracker.biggest(sample())["id"], 2)

    def test_biggest_of_empty_list_is_none(self):
        self.assertIsNone(tracker.biggest([]))


if __name__ == "__main__":
    unittest.main()

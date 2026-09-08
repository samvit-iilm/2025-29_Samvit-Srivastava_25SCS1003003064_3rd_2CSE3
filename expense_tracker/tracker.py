"""The core logic: add, delete, filter and summarise expenses."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from .storage import next_id

DATE_FORMAT = "%Y-%m-%d"


def parse_date(text: str) -> str:
    """Validate a YYYY-MM-DD date and return it unchanged."""
    try:
        datetime.strptime(text, DATE_FORMAT)
    except ValueError:
        raise ValueError(f"date must look like 2026-09-08, got {text!r}")
    return text


def add_expense(
    expenses: list[dict],
    amount: float,
    category: str,
    note: str = "",
    on: str | None = None,
) -> dict:
    """Create a new expense and append it to the list."""
    if amount <= 0:
        raise ValueError("amount must be greater than zero")
    if not category.strip():
        raise ValueError("category cannot be empty")

    expense = {
        "id": next_id(expenses),
        "amount": round(float(amount), 2),
        "category": category.strip().lower(),
        "note": note.strip(),
        "date": parse_date(on) if on else date.today().strftime(DATE_FORMAT),
    }
    expenses.append(expense)
    return expense


def delete_expense(expenses: list[dict], expense_id: int) -> dict:
    """Remove an expense by id and return it. Raises KeyError if missing."""
    for index, expense in enumerate(expenses):
        if expense["id"] == expense_id:
            return expenses.pop(index)
    raise KeyError(f"no expense with id {expense_id}")


def filter_expenses(
    expenses: list[dict], category: str | None = None, month: str | None = None
) -> list[dict]:
    """Return the expenses matching a category and/or a YYYY-MM month."""
    result = expenses
    if category:
        wanted = category.strip().lower()
        result = [e for e in result if e["category"] == wanted]
    if month:
        result = [e for e in result if e["date"].startswith(month)]
    return sorted(result, key=lambda e: e["date"])


def total(expenses: list[dict]) -> float:
    """Sum of all the given expenses."""
    return round(sum(e["amount"] for e in expenses), 2)


def by_category(expenses: list[dict]) -> dict[str, float]:
    """Category totals, biggest spender first."""
    totals: dict[str, float] = defaultdict(float)
    for expense in expenses:
        totals[expense["category"]] += expense["amount"]
    ordered = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    return {name: round(value, 2) for name, value in ordered}


def by_month(expenses: list[dict]) -> dict[str, float]:
    """Month-wise totals in date order."""
    totals: dict[str, float] = defaultdict(float)
    for expense in expenses:
        totals[expense["date"][:7]] += expense["amount"]
    return {month: round(totals[month], 2) for month in sorted(totals)}


def biggest(expenses: list[dict]) -> dict | None:
    """The single largest expense, or None if the list is empty."""
    return max(expenses, key=lambda e: e["amount"]) if expenses else None

"""Reading and writing the expense data file (plain JSON)."""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_FILE = Path("expenses.json")


def load(path: Path = DEFAULT_FILE) -> list[dict]:
    """Return the list of saved expenses, or an empty list if none exist."""
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        raise ValueError(f"{path} is not a valid JSON file")
    if not isinstance(data, list):
        raise ValueError(f"{path} should contain a list of expenses")
    return data


def save(expenses: list[dict], path: Path = DEFAULT_FILE) -> None:
    """Write the expenses back to disk, nicely formatted."""
    with path.open("w", encoding="utf-8") as f:
        json.dump(expenses, f, indent=2)


def next_id(expenses: list[dict]) -> int:
    """Smallest unused id, so ids stay short even after deletions."""
    used = {e["id"] for e in expenses}
    candidate = 1
    while candidate in used:
        candidate += 1
    return candidate

"""Command-line interface for the expense tracker."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from . import __version__, storage, tracker

RUPEE = "Rs."


def money(value: float) -> str:
    return f"{RUPEE}{value:,.2f}"


def show_table(expenses: list[dict]) -> None:
    """Print expenses as a simple aligned table."""
    if not expenses:
        print("No expenses found.")
        return

    print(f"{'ID':<4} {'DATE':<12} {'CATEGORY':<14} {'AMOUNT':>12}  NOTE")
    print("-" * 62)
    for e in expenses:
        print(
            f"{e['id']:<4} {e['date']:<12} {e['category']:<14} "
            f"{money(e['amount']):>12}  {e['note']}"
        )
    print("-" * 62)
    print(f"{'TOTAL':<32}{money(tracker.total(expenses)):>18}")


def show_summary(expenses: list[dict]) -> None:
    """Print totals by category and by month, with simple bar charts."""
    if not expenses:
        print("No expenses to summarise.")
        return

    grand = tracker.total(expenses)
    print(f"\nTotal spent : {money(grand)}")
    print(f"Entries     : {len(expenses)}")

    top = tracker.biggest(expenses)
    if top:
        print(f"Biggest     : {money(top['amount'])} on {top['category']} ({top['date']})")

    print("\nBY CATEGORY")
    print("-" * 46)
    categories = tracker.by_category(expenses)
    peak = max(categories.values())
    for name, value in categories.items():
        bar = "#" * max(1, round(value / peak * 20))
        share = value / grand * 100
        print(f"  {name:<14} {money(value):>12}  {share:>5.1f}%  {bar}")

    print("\nBY MONTH")
    print("-" * 46)
    for month, value in tracker.by_month(expenses).items():
        print(f"  {month:<14} {money(value):>12}")


def export_csv(expenses: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "date", "category", "amount", "note"])
        writer.writeheader()
        for e in expenses:
            writer.writerow({k: e[k] for k in writer.fieldnames})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="expense-tracker",
        description="Track your daily expenses from the command line.",
    )
    parser.add_argument(
        "--file", type=Path, default=storage.DEFAULT_FILE,
        help="data file to use (default: expenses.json)",
    )
    parser.add_argument("--version", action="version", version=f"expense-tracker {__version__}")

    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="add a new expense")
    add.add_argument("amount", type=float, help="how much you spent")
    add.add_argument("category", help="e.g. food, travel, books")
    add.add_argument("-n", "--note", default="", help="optional description")
    add.add_argument("-d", "--date", help="date as YYYY-MM-DD (default: today)")

    listing = commands.add_parser("list", help="list expenses")
    listing.add_argument("-c", "--category", help="only this category")
    listing.add_argument("-m", "--month", help="only this month, as YYYY-MM")

    remove = commands.add_parser("delete", help="delete an expense by id")
    remove.add_argument("id", type=int)

    summary = commands.add_parser("summary", help="totals by category and month")
    summary.add_argument("-m", "--month", help="only this month, as YYYY-MM")

    export = commands.add_parser("export", help="export expenses to a CSV file")
    export.add_argument("output", type=Path)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        expenses = storage.load(args.file)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.command == "add":
        try:
            expense = tracker.add_expense(
                expenses, args.amount, args.category, args.note, args.date
            )
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        storage.save(expenses, args.file)
        print(f"Added #{expense['id']}: {money(expense['amount'])} on {expense['category']}")

    elif args.command == "list":
        show_table(tracker.filter_expenses(expenses, args.category, args.month))

    elif args.command == "delete":
        try:
            removed = tracker.delete_expense(expenses, args.id)
        except KeyError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        storage.save(expenses, args.file)
        print(f"Deleted #{removed['id']} ({money(removed['amount'])} on {removed['category']})")

    elif args.command == "summary":
        show_summary(tracker.filter_expenses(expenses, month=args.month))

    elif args.command == "export":
        export_csv(tracker.filter_expenses(expenses), args.output)
        print(f"Exported {len(expenses)} expense(s) to {args.output}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

# Expense Tracker CLI

A simple command-line tool to record daily expenses, see where the money went,
and export everything to CSV — written in **pure Python 3.10+ with no
third-party libraries**.

Built as the project for a **Python Developer Internship at Codec Technologies
India Pvt. Ltd.** (08/07/2026 – 08/08/2026).
Full write-up: [`docs/PROJECT_REPORT.md`](docs/PROJECT_REPORT.md).

---

## Features

- **Add** an expense with amount, category, note and date
- **List** everything, or filter by category and month
- **Delete** an entry by its id
- **Summary** — total spent, biggest expense, category-wise share with bar chart, month-wise totals
- **Export** to CSV for Excel or Google Sheets
- Data stored in a plain, human-readable **JSON** file
- Friendly errors: negative amounts, empty categories, bad dates and unknown ids are all rejected with a clear message

---

## Getting started

```bash
git clone https://github.com/samvit-iilm/python-Internship.git
cd python-Internship
```

Nothing to install — Python 3.10 or newer is all you need.

```bash
# add a few expenses
python -m expense_tracker add 120 food -n "canteen lunch"
python -m expense_tracker add 6000 rent -n "monthly room rent" -d 2026-08-03
python -m expense_tracker add 250 books -n "DSA book"

# see them
python -m expense_tracker list
python -m expense_tracker list -m 2026-08 -c food

# where did the money go?
python -m expense_tracker summary

# remove a wrong entry, export the rest
python -m expense_tracker delete 2
python -m expense_tracker export expenses.csv
```

Try it on the bundled sample data without touching your own file:

```bash
python -m expense_tracker --file sample_expenses.json summary
```

## Commands

| Command | What it does |
|---|---|
| `add AMOUNT CATEGORY [-n NOTE] [-d YYYY-MM-DD]` | Record a new expense (date defaults to today) |
| `list [-c CATEGORY] [-m YYYY-MM]` | Show expenses as a table with a total |
| `delete ID` | Remove one expense |
| `summary [-m YYYY-MM]` | Totals, biggest expense, category and month breakdown |
| `export FILE.csv` | Write all expenses to a CSV file |

Global options: `--file PATH` to use a different data file (default
`expenses.json`), `--version`, `-h/--help`.

## Sample output

```
$ python -m expense_tracker summary

Total spent : Rs.22,621.83
Entries     : 28
Biggest     : Rs.6,000.00 on rent (2026-07-03)

BY CATEGORY
----------------------------------------------
  rent           Rs.12,000.00   53.0%  ####################
  recharge        Rs.2,707.00   12.0%  #####
  food            Rs.2,470.28   10.9%  ####
  books           Rs.1,771.87    7.8%  ###
  movies          Rs.1,628.84    7.2%  ###
  travel          Rs.1,363.40    6.0%  ##
  stationery        Rs.680.44    3.0%  #

BY MONTH
----------------------------------------------
  2026-07        Rs.12,172.10
  2026-08        Rs.10,449.73
```

More in [`docs/sample_output.txt`](docs/sample_output.txt).

## Project structure

```
expense_tracker/
├── __init__.py     version
├── __main__.py     enables `python -m expense_tracker`
├── storage.py      load / save the JSON file, generate ids
├── tracker.py      add, delete, filter, totals  (all the logic)
└── cli.py          argparse commands and printing
tests/              32 tests
docs/               project report and sample output
sample_expenses.json
```

The logic in `tracker.py` never touches files and never prints — it only takes
lists and returns values. That is what makes it easy to test, and it keeps
`cli.py` free to deal with printing only.

## Data format

`expenses.json` is a plain list you can open and edit by hand:

```json
[
  {
    "id": 1,
    "amount": 6000.0,
    "category": "rent",
    "note": "monthly room rent",
    "date": "2026-07-03"
  }
]
```

## Tests

```bash
python -m unittest discover -s tests -v
```

32 tests covering the logic (adding, validation, id reuse, filtering, totals),
the storage layer (round trip, missing file, corrupt JSON) and every CLI
command end to end.

## Author

**Samvit Srivastava** — Python Developer Intern, Codec Technologies India Pvt. Ltd.

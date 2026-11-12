"""
Rewrite sample_tasks.csv with deadlines measured from today, so the OVERDUE,
DUE TODAY and "due tomorrow" flags always show up when you demo the project.

    python sample-data/generate_sample_tasks.py
"""

import os
from datetime import date, timedelta

# (id, name, priority, days from today or None, date format used in the file)
ROWS = [
    ("S1", "Prepare project presentation", 5, 2, "%d-%m-%Y"),
    ("S2", "Submit lab record", 4, 0, "%d-%m-%Y"),
    ("S3", "Revise data structures notes", 3, 8, "%d-%m-%Y"),
    ("S4", "Pay college fees", 5, -2, "%d-%m-%Y"),
    ("S5", "Clean up desktop files", 1, None, ""),
    ("S6", "Team meeting minutes", 2, 1, "%Y-%m-%d"),
    ("S7", "Write mini project report", 5, 2, "%d/%m/%Y"),
    ("S8", "Prepare for viva", 4, 6, "%d-%m-%Y"),
    ("S9", "Update GitHub README", 2, 13, "%d-%m-%Y"),
    ("S10", "Book train tickets", 3, 1, "%d-%m-%Y"),
]


def main():
    today = date.today()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_tasks.csv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("id,name,priority,deadline\n")
        for task_id, name, priority, offset, fmt in ROWS:
            deadline = "" if offset is None else (today + timedelta(days=offset)).strftime(fmt)
            f.write(f"{task_id},{name},{priority},{deadline}\n")
    print(f"Wrote {path} (deadlines relative to {today.isoformat()})")


if __name__ == "__main__":
    main()

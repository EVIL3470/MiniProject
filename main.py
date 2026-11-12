"""
Priority Based Task Manager
---------------------------
A console task manager built on a priority queue.

Tasks are ordered by:
    1. Priority          (5 = most urgent)
    2. Deadline          (earlier deadline first)
    3. Order of entry    (first added, first served)

This file contains only the menu and the input prompts.
All logic lives in manager.py, the data structures in dsa/.
"""

import csv
import json
import os

import lab
import report
from manager import (PRIORITY_LABELS, TaskManager, deadline_status, parse_date,
                     pretty_date, task_key)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "tasks.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# File used by menu option 8 when you just press Enter.
DEFAULT_IMPORT_FILE = os.path.join(BASE_DIR, "sample-data", "sample_tasks.csv")

mgr = TaskManager(DATA_FILE)


# ------------------------------------------------------------------ input helpers
def ask_text(prompt):
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("  This field cannot be empty.")


def ask_unique_id():
    while True:
        task_id = ask_text("Task ID: ")
        if mgr.get(task_id) is None:
            return task_id
        print("  That ID already exists. Please choose another.")


def ask_priority(current=None):
    """When `current` is given, pressing Enter keeps it and None is returned."""
    suffix = f" [{current}]" if current else ""
    while True:
        raw = input(f"Priority (1-5, 5 = most urgent){suffix}: ").strip()
        if not raw and current:
            return None
        if raw.isdigit() and 1 <= int(raw) <= 5:
            return int(raw)
        print("  Please enter a whole number from 1 to 5.")


def ask_deadline(editing=False, current=""):
    """Add: Enter = no deadline.  Edit: Enter = keep (None), 'none' = clear ('')."""
    if editing:
        hint = f" [{pretty_date(current)}] (type 'none' to remove)"
    else:
        hint = " (press Enter for none)"
    while True:
        raw = input(f"Deadline (DD-MM-YYYY){hint}: ").strip()
        if not raw:
            return None if editing else ""
        if editing and raw.lower() in ("none", "clear"):
            return ""
        parsed = parse_date(raw)
        if parsed:
            return parsed.isoformat()
        print("  Invalid date. Example: 25-12-2026")


def ask_yes_no(prompt):
    return input(prompt).strip().lower() in ("y", "yes")


def save():
    try:
        mgr.save()
    except OSError as err:
        print(f"Warning: could not save tasks ({err})\n")


def show_table(tasks):
    print("\n".join(report.table_lines(tasks, mgr.today())))
    print()


# ------------------------------------------------------------------ menu actions
def add_task():
    print("\n--- Add Task ---")
    task = mgr.add(ask_unique_id(), ask_text("Task Name: "), ask_priority(), ask_deadline())
    save()
    print(f"Task {task['id']} added successfully.\n")


def view_tasks():
    pending = mgr.pending()
    if not pending:
        print("\nNo pending tasks.\n")
        return
    print(f"\nPending Tasks ({len(pending)}) - in execution order:")
    show_table(pending)
    print(f"Next up: {pending[0]['id']} - {pending[0]['name']}\n")


def execute_task():
    task = mgr.execute()
    if task is None:
        print("\nNo tasks available.\n")
        return
    save()
    print("\nExecuting highest priority task:")
    print(f"  ID       : {task['id']}")
    print(f"  Task     : {task['name']}")
    print(f"  Priority : {task['priority']} ({PRIORITY_LABELS[task['priority']]})")
    print(f"  Deadline : {pretty_date(task['deadline'])}")
    status = deadline_status(task["deadline"], mgr.today())
    if status.startswith("OVERDUE"):
        print(f"  Note     : this task was {status}")
    print("Task marked as completed.\n")


def edit_task():
    if not len(mgr.heap):
        print("\nNo tasks to edit.\n")
        return
    task = mgr.get(ask_text("\nEnter ID of the task to edit: "))
    if task is None:
        print("No task found with that ID.\n")
        return
    print("Press Enter to keep the current value.")
    name = input(f"Task Name [{task['name']}]: ").strip()
    priority = ask_priority(current=task["priority"])
    deadline = ask_deadline(editing=True, current=task["deadline"])
    mgr.edit(task["id"], name=name, priority=priority, deadline=deadline)
    save()
    print("Task updated.\n")


def delete_task():
    if not len(mgr.heap):
        print("\nNo tasks to delete.\n")
        return
    task = mgr.get(ask_text("\nEnter ID of the task to delete: "))
    if task is None:
        print("No task found with that ID.\n")
        return
    if not ask_yes_no(f"Delete '{task['name']}'? (y/n): "):
        print("Cancelled.\n")
        return
    mgr.delete(task["id"])
    save()
    print("Task deleted. (You can bring it back with Undo.)\n")


def search_tasks():
    if not len(mgr.heap):
        print("\nNo tasks to search.\n")
        return
    term = ask_text("\nSearch text (word or start of a word in task ID or name): ")
    matches, mode = mgr.search(term)
    if not matches:
        print("No matching tasks.\n")
        return
    how = "found with the trie" if mode == "prefix" else "found by scanning (no word starts with that text)"
    print(f"\n{len(matches)} match(es), {how}:")
    show_table(matches)


def filter_tasks():
    if not len(mgr.heap):
        print("\nNo pending tasks.\n")
        return
    print("\nFilter by:  1. Priority   2. Overdue only   3. Due within N days")
    choice = input("Enter choice: ").strip()
    if choice == "1":
        matches = mgr.filter(priority=ask_priority())
    elif choice == "2":
        matches = mgr.filter(overdue=True)
    elif choice == "3":
        raw = input("Number of days: ").strip()
        if not raw.isdigit():
            print("Please enter a whole number.\n")
            return
        matches = mgr.filter(due_within=int(raw))
    else:
        print("Invalid choice.\n")
        return
    if not matches:
        print("No tasks match that filter.\n")
        return
    print(f"\n{len(matches)} task(s):")
    show_table(matches)


def view_completed():
    if not mgr.completed:
        print("\nNo completed tasks yet.\n")
        return
    print(f"\nCompleted Tasks ({len(mgr.completed)}):")
    print("\n".join(report.completed_lines(mgr.completed)) + "\n")


def undo_action():
    label = mgr.undo()
    if label is None:
        print("\nNothing to undo.\n")
        return
    save()
    print(f"\nUndone: {label}.  ({mgr.undo_available()} more action(s) can be undone)\n")


def show_reminder():
    s = mgr.stats()
    if s["overdue"] or s["due_today"]:
        print(f"Reminder: {len(s['overdue'])} overdue, {len(s['due_today'])} due today.\n")


# ------------------------------------------------------------------ upload file & perform
def read_import_file(path):
    """Return rows of (id, name, priority, deadline) from a CSV / TXT / JSON file."""
    rows = []
    if path.lower().endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = data.get("tasks", [])
        for item in data:
            rows.append((str(item.get("id", "")), str(item.get("name", "")),
                         str(item.get("priority", "")), str(item.get("deadline", ""))))
    else:
        with open(path, "r", newline="", encoding="utf-8-sig") as f:
            for row in csv.reader(f):
                row = [cell.strip() for cell in row]
                if not any(row):
                    continue
                row += [""] * (4 - len(row))
                rows.append(tuple(row[:4]))
        if rows and rows[0][0].lower() == "id" and not rows[0][2].isdigit():
            rows.pop(0)         # header line
    return rows


def upload_and_perform():
    print("\n--- Upload File & Perform Tasks ---")
    print("File format (CSV or TXT): one task per line ->  id,name,priority,deadline")
    print("JSON files are also supported.")
    print(f"Default file: {DEFAULT_IMPORT_FILE}")
    path = input("Path of the file to upload (press Enter to use the default): ").strip().strip("\"'")
    path = path or DEFAULT_IMPORT_FILE
    if not os.path.isfile(path) and os.path.isfile(os.path.join(BASE_DIR, path)):
        path = os.path.join(BASE_DIR, path)
    if not os.path.isfile(path):
        print("File not found. Please check the path and try again.\n")
        return
    try:
        rows = read_import_file(path)
    except (OSError, ValueError, AttributeError, TypeError):
        print("Could not read that file. Use CSV/TXT (id,name,priority,deadline) or JSON.\n")
        return

    added, skipped = mgr.import_rows(rows)
    save()
    print(f"\nImported {len(added)} task(s), skipped {len(skipped)}.")
    for reason in skipped[:10]:
        print(f"  Skipped - {reason}")
    if len(skipped) > 10:
        print(f"  ... and {len(skipped) - 10} more skipped row(s)")
    print()
    if not added:
        return

    ordered = sorted(added, key=task_key)
    print("Imported tasks in the order they will be performed:")
    show_table(ordered)
    if not ask_yes_no("Perform these tasks now? (y/n): "):
        print("Tasks kept as pending. Use option 3 to execute them one by one.\n")
        return

    print("\nPerforming tasks...")
    done = mgr.perform(added)
    for i, task in enumerate(done, 1):
        note = deadline_status(task["deadline"], mgr.today())
        note = f"  [{note}]" if note.startswith("OVERDUE") else ""
        print(f"  [{i}/{len(done)}] Done: {task['id']} - {task['name']} "
              f"(Priority {task['priority']}, {pretty_date(task['deadline'])}){note}")
    save()
    print(f"\nAll {len(done)} imported task(s) performed and marked as completed.\n")


# ------------------------------------------------------------------ report & export
def generate_report():
    if not len(mgr.heap) and not mgr.completed:
        print("\nNothing to report yet. Add some tasks first.\n")
        return
    lines = report.build_report(mgr)
    print()
    print("\n".join(lines) + "\n")
    try:
        print(f"Report saved to: {report.save_text(lines, OUTPUT_DIR)}\n")
    except OSError as err:
        print(f"Could not save the report file ({err}).\n")


def export_csv():
    if not len(mgr.heap) and not mgr.completed:
        print("\nNothing to export yet.\n")
        return
    try:
        print(f"\nExported to: {report.export_csv(mgr, OUTPUT_DIR)}\n")
    except OSError as err:
        print(f"\nCould not export ({err}).\n")


# ------------------------------------------------------------------ main loop
MENU = """===== Priority Based Task Manager =====
 1. Add Task
 2. View Tasks
 3. Execute Highest Priority Task
 4. Edit Task
 5. Delete Task
 6. Search Tasks
 7. View Completed Tasks
 8. Upload File & Perform Tasks
 9. Generate Report
10. Undo Last Action
11. Filter Tasks
12. Export to CSV
13. Algorithm Lab
14. Exit"""


def main():
    try:
        count = mgr.load()
        if count:
            print(f"Loaded {count} saved task(s).\n")
    except (OSError, ValueError):
        print("Warning: saved data was unreadable, starting with an empty list.\n")
    show_reminder()
    actions = {
        "1": add_task, "2": view_tasks, "3": execute_task, "4": edit_task,
        "5": delete_task, "6": search_tasks, "7": view_completed,
        "8": upload_and_perform, "9": generate_report, "10": undo_action,
        "11": filter_tasks, "12": export_csv, "13": lab.run,
    }
    try:
        while True:
            print(MENU)
            choice = input("Enter choice: ").strip()
            if choice == "14":
                break
            action = actions.get(choice)
            if action:
                action()
            else:
                print("Invalid choice. Please enter a number from 1 to 14.\n")
    except (KeyboardInterrupt, EOFError):
        print()
    save()
    print("Thank You")


if __name__ == "__main__":
    main()

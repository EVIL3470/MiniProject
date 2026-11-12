"""Text tables, the summary report and CSV export (no input, no TaskManager state changes)."""

import csv
import os
from datetime import datetime

from manager import PRIORITY_LABELS, deadline_status, pretty_date

WIDTH = 82


def table_lines(task_list, today):
    lines = [f"{'#':<3} {'ID':<8} {'Task':<26} {'Priority':<13} {'Deadline':<13} Status",
             "-" * WIDTH]
    for i, t in enumerate(task_list, 1):
        label = f"{t['priority']} ({PRIORITY_LABELS[t['priority']]})"
        name = t["name"] if len(t["name"]) <= 25 else t["name"][:22] + "..."
        lines.append(f"{i:<3} {t['id']:<8} {name:<26} {label:<13} "
                     f"{pretty_date(t['deadline']):<13} "
                     f"{deadline_status(t['deadline'], today)}".rstrip())
    return lines


def completed_lines(completed):
    lines = [f"{'ID':<8} {'Task':<28} {'Priority':<10} {'Completed On':<13} Result",
             "-" * WIDTH]
    for t in completed:
        done = t.get("completed_on", "")
        if not t.get("deadline"):
            result = "-"
        else:
            result = "on time" if done <= t["deadline"] else "LATE"
        lines.append(f"{t['id']:<8} {t['name'][:27]:<28} {t['priority']:<10} "
                     f"{pretty_date(done):<13} {result}")
    return lines


def build_report(manager):
    today = manager.today()
    s = manager.stats()
    pending = manager.pending()
    judged = s["on_time"] + s["late"]
    on_time_text = f"{s['on_time']} of {judged}" if judged else "n/a"

    lines = [
        "=" * WIDTH,
        "PRIORITY BASED TASK MANAGER - REPORT".center(WIDTH),
        f"Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')}".center(WIDTH),
        "=" * WIDTH,
        "",
        "SUMMARY",
        "-" * WIDTH,
        f"Total tasks                    : {s['total']}",
        f"Pending                        : {s['pending']}",
        f"Completed                      : {s['completed']}",
        f"Completion rate                : {s['rate']:.1f}%",
        f"Completed on time              : {on_time_text}",
        f"Overdue                        : {len(s['overdue'])}",
        f"Due today                      : {len(s['due_today'])}",
        f"Pending, no deadline           : {len(s['no_deadline'])}",
        "",
        "PENDING TASKS BY PRIORITY",
        "-" * WIDTH,
    ]
    for p, count in s["by_priority"].items():
        label = f"{p} ({PRIORITY_LABELS[p]})"
        lines.append(f"{label:<14}: {'#' * count} {count}")

    lines += ["", "PENDING TASKS (in execution order)", "-" * WIDTH]
    lines += table_lines(pending, today)[2:] if pending else ["None"]

    if s["overdue"]:
        lines += ["", "OVERDUE TASKS - NEEDS ATTENTION", "-" * WIDTH]
        lines += table_lines(s["overdue"], today)[2:]

    lines += ["", "COMPLETED TASKS", "-" * WIDTH]
    lines += completed_lines(manager.completed)[2:] if manager.completed else ["None"]
    lines += ["", "=" * WIDTH, "End of report".center(WIDTH), "=" * WIDTH]
    return lines


def save_text(lines, folder, prefix="report"):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def export_csv(manager, folder):
    """Write every task (pending in execution order, then completed) to a CSV file."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"tasks_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["status", "id", "name", "priority", "deadline", "completed_on"])
        for t in manager.pending():
            writer.writerow(["pending", t["id"], t["name"], t["priority"], t["deadline"], ""])
        for t in manager.completed:
            writer.writerow(["completed", t["id"], t["name"], t["priority"],
                             t["deadline"], t.get("completed_on", "")])
    return path

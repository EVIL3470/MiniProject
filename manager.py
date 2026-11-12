"""
TaskManager - all the logic of the project, with no input()/print().
Keeping logic separate from the menu makes it easy to unit-test.

Data structures used
    IndexedMinHeap  priority queue (pending tasks)            dsa/min_heap.py
    Hash map        task ID -> position inside the heap       (inside the heap)
    Trie            prefix search on task names and IDs       dsa/trie.py
    Stack (deque)   undo history, last action is undone first
    List            completed-task history (append only)
"""

import json
import os
import re
from collections import deque
from datetime import date, datetime

from dsa import IndexedMinHeap, Trie

NO_DEADLINE = "9999-12-31"          # sorts after every real date
DATE_INPUT_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y")
PRIORITY_LABELS = {1: "Very Low", 2: "Low", 3: "Medium", 4: "High", 5: "Critical"}
UNDO_LIMIT = 50


# ------------------------------------------------------------------ helpers
def parse_date(text):
    for fmt in DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


def pretty_date(iso):
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%d %b %Y") if iso else "No deadline"


def days_left(iso, today):
    return (datetime.strptime(iso, "%Y-%m-%d").date() - today).days


def deadline_status(iso, today):
    if not iso:
        return ""
    left = days_left(iso, today)
    if left < 0:
        return f"OVERDUE by {-left} day(s)"
    if left == 0:
        return "DUE TODAY"
    if left == 1:
        return "due tomorrow"
    return ""


def task_key(task):
    """Heap order: higher priority, then earlier deadline, then first added."""
    return (-task["priority"], task["deadline"] or NO_DEADLINE, task["order"])


def tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


# ------------------------------------------------------------------ manager
class TaskManager:
    def __init__(self, data_file=None, today=None):
        self.data_file = data_file
        self._today = today
        self.heap = IndexedMinHeap(task_key)
        self.trie = Trie()
        self.completed = []
        self.next_order = 0
        self._undo = deque(maxlen=UNDO_LIMIT)

    def today(self):
        return self._today or date.today()

    # -------------------------------------------------------- validation
    @staticmethod
    def _clean_priority(value):
        text = str(value).strip()
        if not (text.isdigit() and 1 <= int(text) <= 5):
            raise ValueError("priority must be a whole number from 1 to 5")
        return int(text)

    @staticmethod
    def _clean_deadline(value):
        text = (value or "").strip()
        if not text:
            return ""
        parsed = parse_date(text)
        if parsed is None:
            raise ValueError(f"invalid deadline '{text}'")
        return parsed.isoformat()

    def _build(self, task_id, name, priority, deadline):
        task_id, name = (task_id or "").strip(), (name or "").strip()
        if not task_id or not name:
            raise ValueError("ID and name are required")
        priority = self._clean_priority(priority)
        deadline = self._clean_deadline(deadline)
        if task_id.lower() in self.heap:
            raise ValueError("duplicate ID")
        task = {"id": task_id, "name": name, "priority": priority,
                "deadline": deadline, "order": self.next_order}
        self.next_order += 1
        return task

    # -------------------------------------------------------- heap + trie sync
    @staticmethod
    def _ref(task):
        return task["id"].lower()

    def _index(self, task):
        for word in set(tokens(task["name"])) | {self._ref(task)}:
            self.trie.insert(word, self._ref(task))

    def _unindex(self, task):
        for word in set(tokens(task["name"])) | {self._ref(task)}:
            self.trie.remove(word, self._ref(task))

    def _attach(self, task):
        self.heap.push(self._ref(task), task)
        self._index(task)

    def _detach(self, task):
        self.heap.remove(self._ref(task))
        self._unindex(task)

    def _complete(self, task):
        task["completed_on"] = self.today().isoformat()
        self.completed.append(task)

    def _uncomplete(self):
        task = self.completed.pop()
        task.pop("completed_on", None)
        return task

    def _apply_fields(self, task, name, priority, deadline):
        self._unindex(task)
        task["name"], task["priority"], task["deadline"] = name, priority, deadline
        self._index(task)
        self.heap.update(self._ref(task))

    # -------------------------------------------------------- undo stack
    def _push_undo(self, label, fn):
        self._undo.append((label, fn))

    def undo(self):
        """Undo the most recent action. Returns its label, or None."""
        if not self._undo:
            return None
        label, fn = self._undo.pop()
        fn()
        return label

    def undo_available(self):
        return len(self._undo)

    # -------------------------------------------------------- queries
    def get(self, task_id):
        ref = task_id.strip().lower()
        return self.heap.get(ref) if ref in self.heap else None

    def pending(self):
        return self.heap.ordered()

    def search(self, text):
        """Return (tasks, mode). mode is 'prefix' (trie) or 'substring' (fallback)."""
        words = tokens(text)
        if words:
            refs = None
            for word in words:
                found = self.trie.with_prefix(word)
                refs = found if refs is None else refs & found
                if not refs:
                    break
            if refs:
                return sorted((self.heap.get(r) for r in refs), key=task_key), "prefix"
        needle = text.strip().lower()
        found = [t for t in self.pending()
                 if needle in t["name"].lower() or needle in t["id"].lower()]
        return found, "substring"

    def filter(self, priority=None, overdue=False, due_within=None):
        """Pending tasks (in execution order) matching every given condition.
        due_within = N keeps tasks whose deadline is at most N days away
        (overdue tasks included)."""
        today = self.today()
        result = []
        for t in self.pending():
            if priority is not None and t["priority"] != priority:
                continue
            if overdue and not (t["deadline"] and days_left(t["deadline"], today) < 0):
                continue
            if due_within is not None and not (
                    t["deadline"] and days_left(t["deadline"], today) <= due_within):
                continue
            result.append(t)
        return result

    # -------------------------------------------------------- actions
    def add(self, task_id, name, priority, deadline=""):
        task = self._build(task_id, name, priority, deadline)
        self._attach(task)
        self._push_undo(f"Add task {task['id']}", lambda: self._detach(task))
        return task

    def execute(self):
        """Complete the highest-priority task. Returns it, or None if empty."""
        if not len(self.heap):
            return None
        task = self.heap.pop()
        self._unindex(task)
        self._complete(task)

        def undo():
            self._uncomplete()
            self._attach(task)
        self._push_undo(f"Execute task {task['id']}", undo)
        return task

    def edit(self, task_id, name=None, priority=None, deadline=None):
        """None keeps the old value; deadline '' clears the deadline."""
        task = self.get(task_id)
        if task is None:
            raise KeyError(task_id)
        old = (task["name"], task["priority"], task["deadline"])
        new_name = (name or "").strip() or task["name"]
        new_priority = task["priority"] if priority is None else self._clean_priority(priority)
        new_deadline = task["deadline"] if deadline is None else self._clean_deadline(deadline)
        self._apply_fields(task, new_name, new_priority, new_deadline)
        self._push_undo(f"Edit task {task['id']}", lambda: self._apply_fields(task, *old))
        return task

    def delete(self, task_id):
        task = self.get(task_id)
        if task is None:
            raise KeyError(task_id)
        self._detach(task)
        self._push_undo(f"Delete task {task['id']}", lambda: self._attach(task))
        return task

    def import_rows(self, rows):
        """rows: iterable of (id, name, priority, deadline) text values.
        Returns (added_tasks, skipped_reasons)."""
        added, skipped = [], []
        for line_no, (task_id, name, priority, deadline) in enumerate(rows, 1):
            try:
                task = self._build(task_id, name, priority, deadline)
            except ValueError as err:
                label = f"Row {line_no}" + (f" ({task_id})" if task_id else "")
                skipped.append(f"{label}: {err}")
                continue
            self._attach(task)
            added.append(task)
        if added:
            def undo():
                for task in added:
                    self._detach(task)
            self._push_undo(f"Import {len(added)} task(s)", undo)
        return added, skipped

    def perform(self, task_list):
        """Complete the given pending tasks, highest priority first.
        Returns them in the order they were performed."""
        ordered = sorted(task_list, key=task_key)
        for task in ordered:
            self._detach(task)
            self._complete(task)
        if ordered:
            def undo():
                for _ in ordered:
                    self._uncomplete()
                for task in ordered:
                    self._attach(task)
            self._push_undo(f"Perform {len(ordered)} task(s)", undo)
        return ordered

    # -------------------------------------------------------- statistics
    def stats(self):
        pending = self.pending()
        today = self.today()
        overdue = [t for t in pending if t["deadline"] and days_left(t["deadline"], today) < 0]
        due_today = [t for t in pending if t["deadline"] and days_left(t["deadline"], today) == 0]
        total = len(pending) + len(self.completed)
        with_deadline = [t for t in self.completed if t.get("deadline")]
        on_time = sum(1 for t in with_deadline if t["completed_on"] <= t["deadline"])
        return {
            "total": total,
            "pending": len(pending),
            "completed": len(self.completed),
            "rate": (len(self.completed) / total * 100) if total else 0.0,
            "overdue": overdue,
            "due_today": due_today,
            "no_deadline": [t for t in pending if not t["deadline"]],
            "by_priority": {p: sum(1 for t in pending if t["priority"] == p)
                            for p in range(5, 0, -1)},
            "on_time": on_time,
            "late": len(with_deadline) - on_time,
        }

    # -------------------------------------------------------- persistence
    def save(self):
        """Write tasks.json (temp file + rename, so a crash cannot corrupt it)."""
        if not self.data_file:
            return
        data = {"tasks": sorted(self.heap.items(), key=lambda t: t["order"]),
                "completed": self.completed}
        tmp = self.data_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, self.data_file)

    def load(self):
        """Load tasks.json. Returns the number of pending tasks loaded.
        Raises ValueError/OSError if the file is unreadable (state stays empty)."""
        if not self.data_file or not os.path.exists(self.data_file):
            return 0
        with open(self.data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        try:
            pending = [self._normalise(t) for t in data.get("tasks", [])]
            done = [self._normalise(t, completed=True) for t in data.get("completed", [])]
            if len({self._ref(t) for t in pending}) != len(pending):
                raise ValueError("duplicate IDs in saved data")
        except (KeyError, TypeError, AttributeError) as err:
            raise ValueError(f"bad saved data: {err}")
        for task in pending:
            self._attach(task)
        self.completed = done
        self.next_order = max([t["order"] for t in pending + done] + [-1]) + 1
        return len(pending)

    def _normalise(self, raw, completed=False):
        task = {"id": str(raw["id"]).strip(), "name": str(raw["name"]).strip(),
                "priority": self._clean_priority(raw["priority"]),
                "deadline": self._clean_deadline(raw.get("deadline", "")),
                "order": int(raw.get("order", 0))}
        if not task["id"] or not task["name"]:
            raise ValueError("task without id or name")
        if completed or raw.get("completed_on"):
            task["completed_on"] = raw.get("completed_on", "")
        return task

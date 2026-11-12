import json
import os
import tempfile
import unittest
from datetime import date

from manager import TaskManager

TODAY = date(2026, 11, 12)


def new_manager(path=None):
    return TaskManager(path, today=TODAY)


def order_of(mgr):
    return [t["id"] for t in mgr.pending()]


class OrderingTests(unittest.TestCase):
    def test_priority_then_deadline_then_insertion(self):
        m = new_manager()
        m.add("A", "low", 1, "2026-11-20")
        m.add("B", "high late", 5, "2026-12-01")
        m.add("C", "high early", 5, "2026-11-15")
        m.add("D", "high no deadline", 5, "")
        m.add("E", "high early too", 5, "2026-11-15")
        self.assertEqual(order_of(m), ["C", "E", "B", "D", "A"])

    def test_execute_takes_the_top_task_and_records_date(self):
        m = new_manager()
        m.add("A", "one", 2)
        m.add("B", "two", 4)
        task = m.execute()
        self.assertEqual(task["id"], "B")
        self.assertEqual(task["completed_on"], "2026-11-12")
        self.assertEqual(order_of(m), ["A"])
        self.assertEqual(len(m.completed), 1)

    def test_execute_on_empty_returns_none(self):
        self.assertIsNone(new_manager().execute())


class ValidationTests(unittest.TestCase):
    def test_bad_input_is_rejected(self):
        m = new_manager()
        for args in [("", "x", 3), ("A", "", 3), ("A", "x", 6), ("A", "x", 0),
                     ("A", "x", "abc"), ("A", "x", 3, "31-02-2026")]:
            with self.assertRaises(ValueError):
                m.add(*args)
        self.assertEqual(len(m.heap), 0)

    def test_duplicate_id_is_case_insensitive(self):
        m = new_manager()
        m.add("s1", "first", 3)
        with self.assertRaises(ValueError):
            m.add("S1", "second", 3)

    def test_date_formats(self):
        m = new_manager()
        for i, text in enumerate(["2026-11-20", "20-11-2026", "20/11/2026"]):
            self.assertEqual(m.add(f"T{i}", "x", 3, text)["deadline"], "2026-11-20")


class EditDeleteUndoTests(unittest.TestCase):
    def test_edit_reorders_the_heap(self):
        m = new_manager()
        m.add("A", "alpha", 2)
        m.add("B", "beta", 3)
        m.edit("A", priority=5)
        self.assertEqual(order_of(m), ["A", "B"])
        m.edit("A", deadline="")           # '' clears, None would keep
        m.edit("B", name="gamma")
        self.assertEqual(m.get("B")["name"], "gamma")

    def test_edit_keeps_values_when_none(self):
        m = new_manager()
        m.add("A", "alpha", 2, "2026-11-20")
        m.edit("A", name="", priority=None, deadline=None)
        t = m.get("A")
        self.assertEqual((t["name"], t["priority"], t["deadline"]), ("alpha", 2, "2026-11-20"))

    def test_delete(self):
        m = new_manager()
        m.add("A", "alpha", 2)
        m.delete("a")
        self.assertEqual(len(m.heap), 0)
        with self.assertRaises(KeyError):
            m.delete("A")

    def test_undo_each_action(self):
        m = new_manager()
        m.add("A", "alpha", 2)
        m.add("B", "beta", 4)
        m.edit("A", name="renamed", priority=5, deadline="2026-12-01")
        m.delete("B")
        m.execute()                         # completes A
        self.assertEqual(m.undo(), "Execute task A")
        self.assertEqual(m.undo(), "Delete task B")
        self.assertEqual(m.undo(), "Edit task A")
        a = m.get("A")
        self.assertEqual((a["name"], a["priority"], a["deadline"]), ("alpha", 2, ""))
        self.assertEqual(order_of(m), ["B", "A"])
        self.assertEqual(m.undo(), "Add task B")
        self.assertEqual(m.undo(), "Add task A")
        self.assertIsNone(m.undo())
        self.assertEqual(len(m.heap), 0)
        self.assertEqual(m.completed, [])

    def test_undo_restores_trie_index(self):
        m = new_manager()
        m.add("A", "write report", 3)
        m.edit("A", name="plan trip")
        self.assertEqual(m.search("rep")[0], [])
        m.undo()
        self.assertEqual([t["id"] for t in m.search("rep")[0]], ["A"])


class SearchFilterTests(unittest.TestCase):
    def setUp(self):
        self.m = new_manager()
        self.m.add("S1", "Prepare project presentation", 5, "2026-11-14")
        self.m.add("S2", "Submit lab record", 4, "2026-11-12")
        self.m.add("S3", "Pay college fees", 5, "2026-11-10")
        self.m.add("S4", "Clean desktop", 1)

    def ids(self, tasks):
        return [t["id"] for t in tasks]

    def test_prefix_search_uses_trie(self):
        tasks, mode = self.m.search("pre")
        self.assertEqual((self.ids(tasks), mode), (["S1"], "prefix"))

    def test_multi_word_search_is_and(self):
        tasks, _ = self.m.search("project pre")
        self.assertEqual(self.ids(tasks), ["S1"])
        tasks, _ = self.m.search("project lab")
        self.assertEqual(tasks, [])

    def test_search_by_id(self):
        self.assertEqual(self.ids(self.m.search("s2")[0]), ["S2"])

    def test_substring_fallback(self):
        tasks, mode = self.m.search("sentation")
        self.assertEqual((self.ids(tasks), mode), (["S1"], "substring"))

    def test_filters(self):
        self.assertEqual(self.ids(self.m.filter(priority=5)), ["S3", "S1"])
        self.assertEqual(self.ids(self.m.filter(overdue=True)), ["S3"])
        self.assertEqual(self.ids(self.m.filter(due_within=0)), ["S3", "S2"])
        self.assertEqual(self.ids(self.m.filter(due_within=3)), ["S3", "S1", "S2"])
        self.assertEqual(self.ids(self.m.filter(priority=5, due_within=3)), ["S3", "S1"])


class ImportTests(unittest.TestCase):
    ROWS = [("I1", "ok", "3", "20-11-2026"), ("I2", "bad priority", "9", ""),
            ("", "no id", "2", ""), ("I3", "bad date", "2", "99-99-2026"),
            ("I1", "duplicate", "2", ""), ("I4", "ok too", "5", "")]

    def test_import_skips_invalid_rows_with_reasons(self):
        m = new_manager()
        added, skipped = m.import_rows(self.ROWS)
        self.assertEqual([t["id"] for t in added], ["I1", "I4"])
        self.assertEqual(len(skipped), 4)
        self.assertIn("priority", skipped[0])
        self.assertIn("duplicate", skipped[3])

    def test_perform_completes_in_priority_order_and_undoes(self):
        m = new_manager()
        m.add("OLD", "already pending", 1)
        added, _ = m.import_rows(self.ROWS)
        done = m.perform(added)
        self.assertEqual([t["id"] for t in done], ["I4", "I1"])
        self.assertEqual(order_of(m), ["OLD"])
        self.assertEqual([t["id"] for t in m.completed], ["I4", "I1"])
        m.undo()                            # undo perform
        self.assertEqual(order_of(m), ["I4", "I1", "OLD"])
        self.assertEqual(m.completed, [])
        m.undo()                            # undo import
        self.assertEqual(order_of(m), ["OLD"])


class StatsTests(unittest.TestCase):
    def test_stats(self):
        m = new_manager()
        m.add("A", "late task", 5, "2026-11-01")
        m.add("B", "today", 4, "2026-11-12")
        m.add("C", "nothing", 1)
        s = m.stats()
        self.assertEqual((s["total"], s["pending"], s["completed"]), (3, 3, 0))
        self.assertEqual([t["id"] for t in s["overdue"]], ["A"])
        self.assertEqual([t["id"] for t in s["due_today"]], ["B"])
        m.execute()
        m.execute()
        s = m.stats()
        self.assertEqual(s["completed"], 2)
        self.assertEqual((s["on_time"], s["late"]), (1, 1))
        self.assertAlmostEqual(s["rate"], 200 / 3)


class PersistenceTests(unittest.TestCase):
    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "tasks.json")
            m = new_manager(path)
            m.add("A", "alpha", 2, "2026-11-20")
            m.add("B", "beta", 5)
            m.execute()
            m.save()
            m2 = new_manager(path)
            self.assertEqual(m2.load(), 1)
            self.assertEqual(order_of(m2), ["A"])
            self.assertEqual(m2.completed[0]["id"], "B")
            self.assertEqual(m2.add("C", "gamma", 1)["order"], 2)   # order keeps growing
            self.assertEqual([t["id"] for t in m2.search("alp")[0]], ["A"])

    def test_corrupt_file_raises_and_leaves_manager_empty(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "tasks.json")
            for content in ["not json", json.dumps({"tasks": [{"id": "A"}]}),
                            json.dumps({"tasks": [{"id": "A", "name": "x", "priority": 9}]})]:
                with open(path, "w") as f:
                    f.write(content)
                m = new_manager(path)
                with self.assertRaises((ValueError, OSError)):
                    m.load()
                self.assertEqual(len(m.heap), 0)

    def test_loads_original_project_format(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "tasks.json")
            with open(path, "w") as f:
                json.dump({"tasks": [], "completed": [
                    {"id": "S5", "name": "Clean up desktop files", "priority": 1,
                     "deadline": "", "order": 4, "completed_on": "2026-11-01"}]}, f)
            m = new_manager(path)
            self.assertEqual(m.load(), 0)
            self.assertEqual(len(m.completed), 1)
            self.assertEqual(m.next_order, 5)


if __name__ == "__main__":
    unittest.main()

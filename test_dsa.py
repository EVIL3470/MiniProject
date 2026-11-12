import random
import unittest

from dsa import IndexedMinHeap, Trie


def make_heap():
    return IndexedMinHeap(lambda x: x["k"])


class IndexedMinHeapTests(unittest.TestCase):
    def test_pop_returns_items_in_key_order(self):
        heap = make_heap()
        for i, k in enumerate([5, 3, 8, 1, 9, 2]):
            heap.push(f"i{i}", {"k": k})
        self.assertEqual([heap.pop()["k"] for _ in range(6)], [1, 2, 3, 5, 8, 9])

    def test_peek_does_not_remove(self):
        heap = make_heap()
        heap.push("a", {"k": 2})
        heap.push("b", {"k": 1})
        self.assertEqual(heap.peek()["k"], 1)
        self.assertEqual(len(heap), 2)

    def test_duplicate_id_rejected(self):
        heap = make_heap()
        heap.push("a", {"k": 1})
        with self.assertRaises(KeyError):
            heap.push("a", {"k": 2})

    def test_empty_heap_errors(self):
        heap = make_heap()
        with self.assertRaises(IndexError):
            heap.pop()
        with self.assertRaises(IndexError):
            heap.peek()

    def test_remove_from_middle(self):
        heap = make_heap()
        for k in range(10):
            heap.push(f"i{k}", {"k": k})
        heap.remove("i4")
        self.assertNotIn("i4", heap)
        self.assertTrue(heap.is_valid())
        self.assertEqual([t["k"] for t in heap.ordered()], [0, 1, 2, 3, 5, 6, 7, 8, 9])

    def test_update_moves_item_up_and_down(self):
        heap = make_heap()
        items = {f"i{k}": {"k": k} for k in range(1, 8)}
        for item_id, item in items.items():
            heap.push(item_id, item)
        items["i7"]["k"] = 0             # becomes the smallest
        heap.update("i7")
        self.assertEqual(heap.peek(), items["i7"])
        items["i7"]["k"] = 100           # becomes the largest
        heap.update("i7")
        self.assertEqual(heap.ordered()[-1], items["i7"])
        self.assertTrue(heap.is_valid())

    def test_ordered_leaves_heap_untouched(self):
        heap = make_heap()
        for k in (3, 1, 2):
            heap.push(f"i{k}", {"k": k})
        before = heap.ids_in_array_order()
        heap.ordered()
        self.assertEqual(heap.ids_in_array_order(), before)
        self.assertEqual(len(heap), 3)

    def test_random_operations_match_sorted_list(self):
        rng = random.Random(1)
        heap, model = make_heap(), {}
        next_id = 0
        for _ in range(3000):
            action = rng.choice(["push", "push", "pop", "remove", "update"])
            if action == "push" or not model:
                item_id = f"i{next_id}"
                next_id += 1
                item = {"k": rng.random()}
                heap.push(item_id, item)
                model[item_id] = item
            elif action == "pop":
                expected = min(model, key=lambda i: model[i]["k"])
                self.assertIs(heap.pop(), model.pop(expected))
            elif action == "remove":
                item_id = rng.choice(list(model))
                heap.remove(item_id)
                del model[item_id]
            else:
                item_id = rng.choice(list(model))
                model[item_id]["k"] = rng.random()
                heap.update(item_id)
            self.assertTrue(heap.is_valid())
            self.assertEqual(len(heap), len(model))


class TrieTests(unittest.TestCase):
    def test_prefix_lookup(self):
        trie = Trie()
        trie.insert("presentation", "t1")
        trie.insert("prepare", "t2")
        trie.insert("report", "t3")
        self.assertEqual(trie.with_prefix("pre"), {"t1", "t2"})
        self.assertEqual(trie.with_prefix("rep"), {"t3"})
        self.assertEqual(trie.with_prefix("xyz"), set())

    def test_remove_and_prune(self):
        trie = Trie()
        trie.insert("notes", "t1")
        trie.insert("note", "t2")
        trie.remove("notes", "t1")
        self.assertEqual(trie.with_prefix("note"), {"t2"})
        self.assertEqual(trie.with_prefix("notes"), set())
        trie.remove("note", "t2")
        self.assertEqual(trie.node_count(), 0)

    def test_remove_unknown_word_is_safe(self):
        trie = Trie()
        trie.insert("abc", "t1")
        trie.remove("abd", "t1")
        self.assertEqual(trie.with_prefix("abc"), {"t1"})


if __name__ == "__main__":
    unittest.main()

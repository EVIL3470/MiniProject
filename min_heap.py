"""
Indexed Min-Heap
----------------
A binary min-heap written from scratch (no heapq) with one extra feature:
a hash map (`_pos`) that remembers the array position of every item by ID.

Why the extra map?
    A plain heap can only remove the root quickly. Removing or re-prioritising
    an item in the middle needs O(n) to find it and O(n) to heapify again.
    With the position map the item is found in O(1), and fixing the heap takes
    only O(log n) (one sift-up or sift-down).

Complexity (n = number of items)
    push            O(log n)
    pop (min)       O(log n)
    peek (min)      O(1)
    get by id       O(1)
    remove by id    O(log n)
    update by id    O(log n)   (call after changing the item's key fields)
    ordered()       O(n log n) (heap-sort of a copy; the heap is not changed)
"""


class IndexedMinHeap:
    def __init__(self, key):
        """`key(item)` must return a comparable, strictly unique sort key."""
        self._key = key
        self._items = []        # array form of the binary tree: list of (id, item)
        self._pos = {}          # id -> index in self._items
        self.trace = None       # set to a list to record every swap (used by the lab)

    # ------------------------------------------------------------ basic info
    def __len__(self):
        return len(self._items)

    def __contains__(self, item_id):
        return item_id in self._pos

    def items(self):
        """All items in internal (array) order - NOT sorted."""
        return [item for _, item in self._items]

    def ids_in_array_order(self):
        return [item_id for item_id, _ in self._items]

    def get(self, item_id):
        return self._items[self._pos[item_id]][1]

    def peek(self):
        if not self._items:
            raise IndexError("peek from an empty heap")
        return self._items[0][1]

    # ------------------------------------------------------------ internals
    def _less(self, i, j):
        return self._key(self._items[i][1]) < self._key(self._items[j][1])

    def _swap(self, i, j):
        a = self._items
        a[i], a[j] = a[j], a[i]
        self._pos[a[i][0]] = i
        self._pos[a[j][0]] = j
        if self.trace is not None:
            self.trace.append(f"swap {a[i][0]} <-> {a[j][0]}")

    def _sift_up(self, i):
        while i > 0:
            parent = (i - 1) // 2
            if not self._less(i, parent):
                break
            self._swap(i, parent)
            i = parent
        return i

    def _sift_down(self, i):
        n = len(self._items)
        while True:
            left = 2 * i + 1
            right = left + 1
            smallest = i
            if left < n and self._less(left, smallest):
                smallest = left
            if right < n and self._less(right, smallest):
                smallest = right
            if smallest == i:
                return i
            self._swap(i, smallest)
            i = smallest

    def _remove_at(self, i):
        last = len(self._items) - 1
        if i != last:
            self._swap(i, last)          # move the victim to the end ...
        item_id, item = self._items.pop()  # ... and cut it off
        del self._pos[item_id]
        if i < last:                     # the item that took its place may be
            if self._sift_up(i) == i:    # too small (goes up) or too big (goes down)
                self._sift_down(i)
        return item

    # ------------------------------------------------------------ operations
    def push(self, item_id, item):
        if item_id in self._pos:
            raise KeyError(f"duplicate id: {item_id}")
        self._items.append((item_id, item))
        self._pos[item_id] = len(self._items) - 1
        self._sift_up(len(self._items) - 1)

    def pop(self):
        if not self._items:
            raise IndexError("pop from an empty heap")
        return self._remove_at(0)

    def remove(self, item_id):
        return self._remove_at(self._pos[item_id])

    def update(self, item_id):
        """Re-balance after the item's key fields were changed in place."""
        i = self._pos[item_id]
        if self._sift_up(i) == i:
            self._sift_down(i)

    def ordered(self):
        """Return every item in priority order without modifying this heap."""
        clone = IndexedMinHeap(self._key)
        clone._items = list(self._items)
        clone._pos = dict(self._pos)
        result = []
        while len(clone):
            result.append(clone.pop())
        return result

    def is_valid(self):
        """Self-check used by the tests: heap property and position map."""
        for i, (item_id, _) in enumerate(self._items):
            if self._pos.get(item_id) != i:
                return False
            if i > 0 and self._less(i, (i - 1) // 2):
                return False
        return len(self._pos) == len(self._items)

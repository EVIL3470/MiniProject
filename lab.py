"""
Algorithm Lab (menu option 13)
------------------------------
1. Heap visualiser  - watch the binary min-heap change after every push and pop.
2. Benchmark        - compare the heap against two simpler ways of keeping a
                      priority queue, to see the O(log n) advantage with real timings.
"""

import bisect
import heapq
import random
import time

from dsa import IndexedMinHeap
from manager import task_key

DEMO_TASKS = [          # (id, priority, deadline)
    ("A", 3, "2026-11-20"),
    ("B", 5, "2026-11-25"),
    ("C", 5, "2026-11-15"),
    ("D", 1, ""),
    ("E", 4, "2026-11-18"),
    ("F", 5, "2026-11-15"),
]


def _label(task):
    return f"{task['id']}(p{task['priority']})"


def _show(heap, swaps, width=66):
    labels = [_label(t) for t in heap.items()]
    print(f"  array : [{', '.join(labels)}]")
    start, size, level = 0, 1, []
    while start < len(labels):
        level.append("  ".join(labels[start:start + size]))
        start += size
        size *= 2
    print("  tree  :")
    for line in level:
        print("    " + line.center(width))
    if swaps:
        print(f"  swaps : {'; '.join(swaps)}")
    print()


def heap_demo():
    print("\n--- Heap visualiser ---")
    print("Key = (-priority, deadline, order).  The smallest key sits at the root.")
    print("A(p3) means task A with priority 3. Equal priorities are broken by deadline,")
    print("then by the order in which the tasks were added.")
    print("PUSH adds the task at the bottom and swaps it upwards while it beats its parent.")
    print("POP swaps the root with the last task, cuts it off, then swaps the new root")
    print("downwards until the heap order is restored.\n")
    heap = IndexedMinHeap(task_key)
    for order, (tid, priority, deadline) in enumerate(DEMO_TASKS):
        heap.trace = []
        task = {"id": tid, "name": tid, "priority": priority,
                "deadline": deadline, "order": order}
        print(f"PUSH {_label(task)}   deadline={deadline or 'none'}")
        heap.push(tid, task)
        _show(heap, heap.trace)
    while len(heap):
        heap.trace = []
        task = heap.pop()
        print(f"POP  -> {_label(task)}   (highest priority task leaves first)")
        _show(heap, heap.trace)


def _make_entries(n, rng):
    entries = []
    for order in range(n):
        priority = rng.randint(1, 5)
        deadline = "2026-%02d-%02d" % (rng.randint(1, 12), rng.randint(1, 28))
        task = {"id": f"T{order}", "name": "x", "priority": priority,
                "deadline": deadline, "order": order}
        entries.append(task)
    return entries


def _time(fn):
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


def benchmark():
    print("\n--- Benchmark: push n tasks, then execute all of them ---")
    print("Compared structures:")
    print("  Indexed heap (ours)   push O(log n), pop O(log n)")
    print("  Python heapq          same idea, written in C (shows the best case)")
    print("  Sorted list           bisect.insort: push O(n), pop O(n) (list shift, fast in C)")
    print("  Unsorted list         push O(1), pop O(n) (scan for the maximum)\n")
    rng = random.Random(42)
    header = f"{'n':>7} | {'Indexed heap':>13} | {'heapq':>9} | {'Sorted list':>12} | {'Unsorted list':>14}"
    print(header)
    print("-" * len(header))
    for n in (1000, 4000, 16000):
        tasks = _make_entries(n, rng)

        def run_indexed():
            heap = IndexedMinHeap(task_key)
            for t in tasks:
                heap.push(t["id"], t)
            while len(heap):
                heap.pop()

        def run_heapq():
            heap = []
            for t in tasks:
                heapq.heappush(heap, (task_key(t), t["id"]))
            while heap:
                heapq.heappop(heap)

        def run_sorted():
            data = []
            for t in tasks:
                bisect.insort(data, (task_key(t), t["id"]))
            while data:
                data.pop(0)

        def run_unsorted():
            data = [(task_key(t), t["id"]) for t in tasks]
            while data:
                data.remove(min(data))

        cells = [_time(run_indexed), _time(run_heapq), _time(run_sorted)]
        scan = _time(run_unsorted) if n <= 4000 else None
        print(f"{n:>7} | {cells[0]:>11.3f} s | {cells[1]:>7.3f} s | "
              f"{cells[2]:>10.3f} s | "
              f"{(format(scan, '.3f') + ' s') if scan is not None else 'skipped':>14}")
    print("\nHow to read this: when n grows 4x, the heap time grows a little over 4x")
    print("(n log n), while the unsorted list grows about 16x (n squared).")
    print("heapq is faster only because it is implemented in C, not because of a")
    print("better algorithm.\n")


def run():
    while True:
        print("\n===== Algorithm Lab =====")
        print("1. Heap visualiser (step by step)")
        print("2. Benchmark: heap vs simpler structures")
        print("3. Back")
        choice = input("Enter choice: ").strip()
        if choice == "1":
            heap_demo()
        elif choice == "2":
            benchmark()
        elif choice == "3":
            return
        else:
            print("Invalid choice.")

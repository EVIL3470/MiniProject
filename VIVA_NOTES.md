# Viva notes: questions you may be asked

Short answers in your own words are best. Each answer points to the file where the code lives.

## The big picture

**What is the project?**
A console task manager. Tasks sit in a priority queue, so the most urgent task is always the next one executed.

**Why a priority queue and not a sorted list?**
A sorted list needs O(n) to insert a task. A heap needs O(log n) to insert and O(log n) to take the top task. The Algorithm Lab benchmark (menu 13, then 2) shows the difference with real timings.

**How are tasks ordered?**
By the key `(-priority, deadline, order)`. Highest priority first, then earliest deadline, then the task that was added first. Priority is negative because a min-heap puts the smallest value on top. (`manager.py`, function `task_key`)

## The heap (`dsa/min_heap.py`)

**What is a binary min-heap?**
A binary tree stored in an array where every parent is smaller than its children. The smallest item is at index 0. For index `i`, the parent is `(i-1)//2` and the children are `2i+1` and `2i+2`.

**How does push work?**
Add the task at the end of the array, then swap it with its parent while it is smaller than the parent (`_sift_up`). At most log n swaps.

**How does pop work?**
Swap the root with the last item, cut the last item off, then swap the new root downwards with its smaller child until the order is correct (`_sift_down`). At most log n swaps.

**What is "indexed" about it?**
It keeps a dictionary `_pos` from task ID to array index. With it, a task in the middle is found in O(1) instead of scanning the array.

**Why is edit / delete O(log n) now?**
The dictionary finds the task at once. For delete, swap it with the last item, cut it off, and fix that one position with a sift-up or sift-down. For edit, change the fields and fix that one position. The first version rebuilt the whole heap with `heapify`, which is O(n).

**Why can't the heap hold two tasks with the same key?**
The `order` counter in the key never repeats, so every key is unique and Python never has to compare two dictionaries.

**How is the full table shown in order if a heap is not sorted?**
`ordered()` copies the heap and pops everything from the copy (heap sort), O(n log n). The real queue is not touched.

## Trie search (`dsa/trie.py`)

**What is a trie?**
A tree where each edge is one letter. Words with the same beginning share the same path.

**How does search use it?**
Each node stores the IDs of tasks whose words pass through it. Typing `pre` walks three nodes and returns the IDs stored there, so there is no scan over all tasks. Cost O(L + k).

**What if the text is from the middle of a word?**
A trie only finds word beginnings, so the program falls back to scanning all tasks, O(n), and says so on screen.

## Undo (`manager.py`)

**How does undo work?**
Every action (add, execute, edit, delete, import, perform) pushes a small reverse function on a stack. Undo pops the last one and runs it. Last action in, first action undone, which is why a stack fits.

**How many actions can be undone?**
The last 50. The stack is cleared when the program exits.

## Other design points

**Why is the logic in `manager.py` and not in `main.py`?**
`manager.py` has no `input()` or `print()`, so the unit tests can call it directly. `main.py` only talks to the user.

**How is the data saved?**
As JSON in `tasks.json`. The program writes a temporary file and then renames it, so a crash while saving cannot leave a half-written file.

**How are bad import rows handled?**
Each row is validated (ID and name present, priority 1-5, valid date, no duplicate ID). Bad rows are skipped and the reason is shown. Good rows are still imported.

**How did you test it?**
33 unit tests (`python -m unittest discover -s tests -t .`), including a random test that does 3,000 mixed operations on the heap and checks it against a simple model after every step.

## Complexity cheat sheet

| Operation                   | Cost         |
| --------------------------- | ------------ |
| Add task                    | O(log n)     |
| Execute (pop top)           | O(log n)     |
| See next task               | O(1)         |
| Find task by ID             | O(1)         |
| Edit / delete a task        | O(log n)     |
| View all in order           | O(n log n)   |
| Trie search                 | O(L + k)     |
| Undo one action             | O(log n)     |

`n` = pending tasks, `L` = length of the typed word, `k` = number of matches.

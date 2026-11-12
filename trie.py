"""
Trie (prefix tree) used for fast task search
--------------------------------------------
Every word of a task name (and the task ID) is stored letter by letter.
Each node remembers the IDs of all tasks whose words pass through it, so the
answer to "which tasks have a word starting with 'pre'?" is found by walking
3 nodes and reading one set - no scan over all tasks.

Complexity (L = length of the word, k = number of matching tasks)
    insert        O(L)
    remove        O(L)
    with_prefix   O(L + k)
"""


class _Node:
    __slots__ = ("children", "refs")

    def __init__(self):
        self.children = {}
        self.refs = set()      # references of every task passing through this node


class Trie:
    def __init__(self):
        self._root = _Node()

    def insert(self, word, ref):
        node = self._root
        for ch in word:
            node = node.children.setdefault(ch, _Node())
            node.refs.add(ref)

    def remove(self, word, ref):
        """Remove `ref` from the path of `word`; empty branches are pruned."""
        path = []
        node = self._root
        for ch in word:
            child = node.children.get(ch)
            if child is None:
                return
            path.append((node, ch, child))
            node = child
        for parent, ch, child in reversed(path):
            child.refs.discard(ref)
            if not child.refs and not child.children:
                del parent.children[ch]

    def with_prefix(self, prefix):
        """Set of refs having a stored word that starts with `prefix`."""
        node = self._root
        for ch in prefix:
            node = node.children.get(ch)
            if node is None:
                return set()
        return set(node.refs)

    def node_count(self):
        count, stack = 0, [self._root]
        while stack:
            node = stack.pop()
            count += len(node.children)
            stack.extend(node.children.values())
        return count

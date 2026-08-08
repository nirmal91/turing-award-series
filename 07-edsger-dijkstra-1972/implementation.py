"""
Dijkstra's shortest path algorithm, built the way Edsger Dijkstra described it in 1959.

Dijkstra's "A Note on Two Problems in Connexion with Graphs" (Numerische Mathematik,
1959) is three pages long and gives two algorithms. The second is the one everyone
means by "Dijkstra's algorithm": given a graph with non-negative edge weights and a
start node, find the shortest distance from the start to every other node.

The method is greedy, and the reason it is allowed to be greedy is the heart of it.
Keep a tentative distance to every node. Repeatedly pick the unsettled node with the
smallest tentative distance and settle it. Because no edge has negative weight, there
is no way to come back later with a shorter path to a node you have already settled:
any detour only adds length. So a settled distance is final. Then relax the settled
node's edges, lowering neighbours' tentative distances where going through this node
is cheaper. The settled set grows outward from the start like a wavefront.

This file mirrors the 1959 paper rather than optimising it. The original selected the
next node with a linear scan over the tentative distances (no binary heap; heaps came
later), so that is what this does: an explicit loop that finds the minimum. It is O(V^2),
exactly Dijkstra's original cost, and it is easy to read and to trace by hand.

BEFORE this algorithm: to find the shortest route you tried paths and compared, with
no guarantee you had found the best short of enumerating them all. The number of
paths grows combinatorially, so on any real map that was hopeless.

AFTER: a systematic method that settles one node at a time and provably returns the
shortest distance to every node, in time that grows with the square of the node count.

Pipeline:
    graph (nodes + weighted edges)
        -> initialise   (start distance 0, all others infinity)
        -> select       (scan for the closest unsettled node)
        -> settle       (its distance is now final)
        -> relax        (improve neighbours' tentative distances)
        -> repeat until every reachable node is settled
        -> distances + predecessor tree -> reconstruct any shortest path

Run:
    python3 implementation.py                 # interactive REPL (build a graph, query paths)
    python3 implementation.py demo.graph      # load and run a graph command file
    python3 implementation.py --test          # self-test suite (16 cases)
    python3 implementation.py --verbose       # REPL that traces every settle and relax
"""

import sys


VERBOSE = False

INFINITY = float("inf")


# ── Graph: nodes and non-negative weighted edges ────────────────────────────────
#
# The graph is an adjacency table: for each node, a list of (neighbour, weight).
# Edges are undirected here (a road runs both ways), which is the "cities and roads"
# setting Dijkstra used. add_edge stores both directions.

class Graph:
    def __init__(self):
        self.adjacency = {}

    def add_node(self, node):
        if node not in self.adjacency:
            self.adjacency[node] = []

    def add_edge(self, u, v, weight):
        if weight < 0:
            # Dijkstra's proof relies on non-negative weights. Reject negatives
            # loudly rather than return a wrong answer, which is what a negative
            # edge would silently cause.
            raise ValueError("edge weights must be non-negative (got %s)" % weight)
        self.add_node(u)
        self.add_node(v)
        self.adjacency[u].append((v, weight))
        self.adjacency[v].append((u, weight))

    def nodes(self):
        return list(self.adjacency)

    def neighbours(self, node):
        return self.adjacency.get(node, [])


# ── The algorithm: Dijkstra's second procedure from the 1959 paper ───────────────
#
# Returns two tables: distance[node] = shortest distance from start, and
# predecessor[node] = the node you arrive from on that shortest path. The
# predecessor table is the shortest-path tree; walking it backward rebuilds a path.

def dijkstra(graph, start):
    distance = {}
    predecessor = {}
    for node in graph.nodes():
        distance[node] = INFINITY
        predecessor[node] = None
    distance[start] = 0

    settled = set()

    while len(settled) < len(graph.nodes()):
        # Select: the unsettled node with the smallest tentative distance.
        current = _closest_unsettled(graph, distance, settled)

        # No reachable unsettled node remains: the rest of the graph is
        # disconnected from start. Their distance stays infinity.
        if current is None:
            break

        settled.add(current)
        if VERBOSE:
            print("settle %s (distance %s)" % (current, _show(distance[current])))

        # Relax: for each road out of current, see if it gives a shorter route.
        for (neighbour, weight) in graph.neighbours(current):
            if neighbour in settled:
                continue
            through_current = distance[current] + weight
            if through_current < distance[neighbour]:
                if VERBOSE:
                    print("   relax %s: %s -> %s (via %s)" % (
                        neighbour, _show(distance[neighbour]),
                        through_current, current))
                distance[neighbour] = through_current
                predecessor[neighbour] = current

    return distance, predecessor


def _closest_unsettled(graph, distance, settled):
    """Linear scan for the unsettled node of least tentative distance. This is
    Dijkstra's original selection step; a binary heap would speed it up but the
    scan is what the 1959 paper describes and it is the clearest to follow."""
    best = None
    for node in graph.nodes():
        if node in settled:
            continue
        if distance[node] == INFINITY:
            continue
        if best is None or distance[node] < distance[best]:
            best = node
    return best


def shortest_path(graph, start, goal):
    """Return (distance, path_as_list). path is [] and distance is infinity if the
    goal is unreachable. The path is rebuilt by walking predecessors from goal back
    to start and reversing."""
    distance, predecessor = dijkstra(graph, start)
    if distance.get(goal, INFINITY) == INFINITY:
        return INFINITY, []

    path = []
    node = goal
    while node is not None:
        path.append(node)
        node = predecessor[node]
    path.reverse()
    return distance[goal], path


# ── Printing helpers ─────────────────────────────────────────────────────────────

def _show(d):
    return "inf" if d == INFINITY else str(d)


def show_graph(graph):
    if len(graph.nodes()) == 0:
        print("(empty graph)")
        return
    seen = set()
    for u in sorted(graph.nodes()):
        for (v, w) in graph.neighbours(u):
            key = tuple(sorted([u, v]))
            if key in seen:
                continue
            seen.add(key)
            print("  %s -- %s  (%s)" % (u, v, w))


def show_distances(graph, start):
    distance, _ = dijkstra(graph, start)
    print("shortest distance from %s:" % start)
    for node in sorted(graph.nodes()):
        print("  %s -> %s = %s" % (start, node, _show(distance[node])))


def show_path(graph, start, goal):
    dist, path = shortest_path(graph, start, goal)
    if dist == INFINITY:
        print("no path from %s to %s" % (start, goal))
        return
    print("%s (distance %s)" % (" -> ".join(path), dist))


# ── The demo graph (also the Full Worked Example in the README) ──────────────────

def demo_graph():
    g = Graph()
    edges = [
        ("A", "B", 7), ("A", "C", 9), ("A", "F", 14),
        ("B", "C", 10), ("B", "D", 15),
        ("C", "D", 11), ("C", "F", 2),
        ("D", "E", 6), ("E", "F", 9),
    ]
    for u, v, w in edges:
        g.add_edge(u, v, w)
    return g


# ── Command interpreter: shared by the REPL and by graph files ───────────────────
#
# One tiny command language drives everything, so an interactive session and a
# saved .graph file are the same thing. Commands:
#     edge U V W     add an undirected edge U--V of weight W
#     path SRC DST   shortest path from SRC to DST
#     dist SRC       shortest distance from SRC to every node
#     show           print the current graph
#     demo           load the built-in demo graph
#     help           list commands

HELP = """commands:
  edge U V W     add an undirected edge U--V of weight W (W >= 0)
  path SRC DST   shortest path and distance from SRC to DST
  dist SRC       shortest distance from SRC to every reachable node
  show           print the current graph
  demo           load the built-in demo graph
  help           show this list
  (Ctrl-D quits)"""


def run_command(graph, line):
    """Execute one command against graph. Returns the (possibly new) graph."""
    parts = line.split()
    if len(parts) == 0:
        return graph
    command = parts[0]

    if command == "edge":
        if len(parts) != 4:
            print("usage: edge U V W")
            return graph
        u, v, w = parts[1], parts[2], parts[3]
        try:
            graph.add_edge(u, v, int(w))
        except ValueError as err:
            print("error: " + str(err))
        return graph

    if command == "path":
        if len(parts) != 3:
            print("usage: path SRC DST")
            return graph
        show_path(graph, parts[1], parts[2])
        return graph

    if command == "dist":
        if len(parts) != 2:
            print("usage: dist SRC")
            return graph
        show_distances(graph, parts[1])
        return graph

    if command == "show":
        show_graph(graph)
        return graph

    if command == "demo":
        print("(loaded the demo graph)")
        return demo_graph()

    if command == "help":
        print(HELP)
        return graph

    print("unknown command: %s (try 'help')" % command)
    return graph


def run_file(path):
    """Run a graph command file: one command per line, comments start with '#'."""
    with open(path) as source_file:
        source = source_file.read()
    graph = Graph()
    for raw in source.split("\n"):
        line = raw
        if "#" in line:
            line = line[:line.index("#")]
        line = line.strip()
        if line == "":
            continue
        print("> " + line)
        graph = run_command(graph, line)


# ── REPL ─────────────────────────────────────────────────────────────────────────

BANNER = """Dijkstra's shortest path (Edsger Dijkstra, 1959).
Build a graph, then ask for shortest paths. Try:
  demo
  show
  path A E
  dist A
Type 'help' for all commands, Ctrl-D to quit."""


def repl():
    graph = Graph()
    print(BANNER)
    while True:
        try:
            line = input("dijkstra> ")
        except EOFError:
            print()
            return
        graph = run_command(graph, line)


# ── Self-test suite ──────────────────────────────────────────────────────────────

def run_tests():
    passed = 0
    total = 0

    def check(description, got, expected):
        nonlocal passed, total
        total += 1
        ok = got == expected
        if ok:
            passed += 1
        mark = "PASS" if ok else "FAIL"
        print("[%s] %-48s -> %s" % (mark, description, got))
        if not ok:
            print("        expected %s" % (expected,))

    g = demo_graph()

    # Distances from A on the demo graph (matches the README worked example).
    dist, pred = dijkstra(g, "A")
    check("dist A->A", dist["A"], 0)
    check("dist A->B", dist["B"], 7)
    check("dist A->C", dist["C"], 9)
    check("dist A->D", dist["D"], 20)
    check("dist A->E", dist["E"], 20)
    check("dist A->F", dist["F"], 11)

    # Shortest path A->E goes A-C-F-E (9+2+9=20), not A-C-D-E (9+11+6=26).
    d, path = shortest_path(g, "A", "E")
    check("path A->E distance", d, 20)
    check("path A->E route", path, ["A", "C", "F", "E"])

    # Path to a direct neighbour uses the direct edge when it is cheapest.
    d, path = shortest_path(g, "A", "B")
    check("path A->B route", path, ["A", "B"])

    # Start to itself: distance 0, path is just the start.
    d, path = shortest_path(g, "A", "A")
    check("path A->A distance", d, 0)
    check("path A->A route", path, ["A"])

    # Symmetry on an undirected graph: distance A->E equals E->A.
    de, _ = shortest_path(g, "E", "A")
    check("undirected symmetry E->A == A->E", de, 20)

    # Edge case: an unreachable node. G is isolated, so its distance is infinity.
    g2 = demo_graph()
    g2.add_node("G")
    d, path = shortest_path(g2, "A", "G")
    check("unreachable node distance", d, INFINITY)
    check("unreachable node path", path, [])

    # Edge case: a tie. Two equal-length routes; the algorithm still returns 20.
    dtie, _ = shortest_path(g, "A", "D")
    check("tie handled (A->D = 20)", dtie, 20)

    # Edge case: negative weight is rejected.
    g3 = Graph()
    try:
        g3.add_edge("X", "Y", -1)
        rejected = False
    except ValueError:
        rejected = True
    check("negative weight rejected", rejected, True)

    print()
    print("%d/%d passed" % (passed, total))
    return passed == total


# ── Entry point ──────────────────────────────────────────────────────────────────

def main():
    global VERBOSE
    args = sys.argv[1:]
    if "--test" in args:
        ok = run_tests()
        sys.exit(0 if ok else 1)
    if "--verbose" in args:
        VERBOSE = True
        print("(verbose mode: every settle and relax is printed)\n")
    files = [a for a in args if not a.startswith("--")]
    if len(files) > 0:
        run_file(files[0])
        return
    repl()


if __name__ == "__main__":
    main()

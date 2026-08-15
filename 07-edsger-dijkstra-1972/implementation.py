"""
Dijkstra's shortest path, built the way Edsger Dijkstra described it in 1959.

Dijkstra's "A Note on Two Problems in Connexion with Graphs" (Numerische Mathematik,
1959) is three pages long and solves two problems at once. The famous one is the
shortest path between two nodes of a weighted graph. He designed it in about twenty
minutes at a cafe, with no paper, as a demonstration of the power of the new ARMAC
computer, and only wrote it down years later.

The method is a single disciplined rule. Give every node a tentative distance
(0 for the source, infinity for the rest). Repeatedly take the unfinished node with
the smallest tentative distance, mark it finished, and relax its outgoing edges: if
reaching a neighbour through this node is shorter than the neighbour's current best,
record the shorter distance and remember which node you came from. Because no edge
has a negative length, the closest unfinished node can never be improved later, so
the moment it is chosen its distance is final. That is the whole proof, and the whole
algorithm.

This file mirrors the 1959 paper rather than just simulating it. The primary routine
uses the linear scan for the minimum that Dijkstra actually described (O(V^2)); a
second routine uses a binary heap (O(E log V)), the standard descendant that arrived
once priority queues were understood. A self-test checks that the two always agree.

BEFORE Dijkstra: finding a shortest route meant hand tracing or a search that could
explore long detours before stumbling onto a short one, with no guarantee the first
answer found was actually the shortest.

AFTER Dijkstra: one pass that settles nodes in order of distance and stops with a
proven-optimal answer. Every GPS route, every internet routing table (OSPF, IS-IS),
and every game pathfinder descends from this rule.

Pipeline:
    graph description (edges with non-negative lengths)
        -> build adjacency table
        -> dijkstra   (settle the closest unfinished node, relax its edges, repeat)
        -> predecessors
        -> reconstruct the actual path from source to target
        -> distance + path

Run:
    python3 implementation.py            # interactive REPL (starts with the demo graph)
    python3 implementation.py cities.graph   # load a graph script and run its queries
    python3 implementation.py --test     # self-test suite (16 cases)
    python3 implementation.py --verbose  # REPL that prints every settle/relax step
"""

import sys

INFINITY = float("inf")

VERBOSE = False


# ── The graph: an adjacency table of node -> list of (neighbour, length) ─────────
#
# A weighted graph is just a table saying, for each node, which nodes it connects to
# and how long each connection is. An undirected road is stored as two directed
# edges, one each way, because that is what the algorithm walks.

class Graph:
    def __init__(self):
        self.edges = {}                 # node -> list of (neighbour, length)

    def add_node(self, node):
        if node not in self.edges:
            self.edges[node] = []

    def add_directed_edge(self, source, target, length):
        """A one-way connection from source to target with a given length."""
        if length < 0:
            raise ValueError("Dijkstra requires non-negative edge lengths; got " + str(length))
        self.add_node(source)
        self.add_node(target)
        self.edges[source].append((target, length))

    def add_edge(self, a, b, length):
        """A two-way road: stored as one directed edge in each direction."""
        self.add_directed_edge(a, b, length)
        self.add_directed_edge(b, a, length)

    def nodes(self):
        return list(self.edges.keys())

    def neighbours(self, node):
        return self.edges.get(node, [])


# ── Dijkstra's algorithm, the 1959 way: scan for the closest unfinished node ─────

def dijkstra(graph, source):
    """Return (distance, predecessor) dicts giving the shortest distance from source
    to every reachable node, and the node we arrived from on each shortest path.

    This is the original formulation: a linear scan to find the minimum tentative
    distance each round. Simple, and exactly what the paper describes."""
    if source not in graph.edges:
        raise KeyError("no such node: " + str(source))

    # Every node starts infinitely far away, except the source, which is 0 from
    # itself. predecessor[n] is the node we step back to when rebuilding the path.
    distance = {}
    predecessor = {}
    for node in graph.nodes():
        distance[node] = INFINITY
        predecessor[node] = None
    distance[source] = 0

    finished = set()

    while len(finished) < len(graph.nodes()):
        # Find the unfinished node with the smallest tentative distance.
        current = None
        for node in graph.nodes():
            if node in finished:
                continue
            if current is None or distance[node] < distance[current]:
                current = node

        # Everything still reachable has been found; the rest is unreachable.
        if current is None or distance[current] == INFINITY:
            break

        finished.add(current)
        if VERBOSE:
            print("  settle %s at distance %s" % (current, _fmt(distance[current])))

        # Relax each edge leaving current.
        for neighbour, length in graph.neighbours(current):
            if neighbour in finished:
                continue
            through_current = distance[current] + length
            if through_current < distance[neighbour]:
                if VERBOSE:
                    print("    relax %s: %s -> %s (via %s)"
                          % (neighbour, _fmt(distance[neighbour]), through_current, current))
                distance[neighbour] = through_current
                predecessor[neighbour] = current

    return distance, predecessor


# ── The modern descendant: the same rule with a binary heap as the priority queue ─

def dijkstra_heap(graph, source):
    """Same algorithm, but a binary heap supplies the closest unfinished node in
    O(log V) instead of an O(V) scan. This is the version in every textbook and
    library today. It is included so the test suite can confirm it agrees with the
    original on every graph."""
    import heapq

    if source not in graph.edges:
        raise KeyError("no such node: " + str(source))

    distance = {}
    predecessor = {}
    for node in graph.nodes():
        distance[node] = INFINITY
        predecessor[node] = None
    distance[source] = 0

    # The heap holds (tentative_distance, node). A node can appear more than once;
    # we skip an entry whose distance is stale (already improved on).
    heap = [(0, source)]
    finished = set()

    while len(heap) > 0:
        current_distance, current = heapq.heappop(heap)
        if current in finished:
            continue
        finished.add(current)

        for neighbour, length in graph.neighbours(current):
            if neighbour in finished:
                continue
            through_current = current_distance + length
            if through_current < distance[neighbour]:
                distance[neighbour] = through_current
                predecessor[neighbour] = current
                heapq.heappush(heap, (through_current, neighbour))

    return distance, predecessor


# ── Rebuilding the actual route from the predecessor trail ───────────────────────

def reconstruct_path(predecessor, source, target):
    """Walk the predecessor pointers backward from target to source, then reverse.
    Returns the list of nodes on the shortest path, or None if target is unreachable."""
    if source == target:
        return [source]

    path = []
    node = target
    while node is not None:
        path.append(node)
        if node == source:
            break
        node = predecessor[node]

    # If we walked off the end without reaching the source, there is no path.
    if path[-1] != source:
        return None

    path.reverse()
    return path


def shortest_path(graph, source, target):
    """Convenience wrapper: return (distance, path) from source to target."""
    distance, predecessor = dijkstra(graph, source)
    if distance[target] == INFINITY:
        return INFINITY, None
    return distance[target], reconstruct_path(predecessor, source, target)


# ── Printing helpers ─────────────────────────────────────────────────────────────

def _fmt(value):
    if value == INFINITY:
        return "inf"
    return str(value)


def print_graph(graph):
    print("graph:")
    for node in sorted(graph.nodes()):
        parts = []
        for neighbour, length in graph.neighbours(node):
            parts.append("%s(%s)" % (neighbour, length))
        print("  %s -> %s" % (node, ", ".join(parts) if parts else "(no edges)"))


# ── The classic six-node demo graph (undirected) ─────────────────────────────────

def demo_graph():
    g = Graph()
    g.add_edge("A", "B", 7)
    g.add_edge("A", "C", 9)
    g.add_edge("A", "F", 14)
    g.add_edge("B", "C", 10)
    g.add_edge("B", "D", 15)
    g.add_edge("C", "D", 11)
    g.add_edge("C", "F", 2)
    g.add_edge("D", "E", 6)
    g.add_edge("E", "F", 9)
    return g


# ── Graph script format: a tiny command language, also used by the REPL ──────────
#
# A graph file is a list of commands, one per line. Blank lines and text after '#'
# are ignored. This is what `python3 implementation.py cities.graph` runs.
#
#     edge A B 7      add an undirected edge of length 7
#     dedge A B 7     add a one-way (directed) edge
#     path A E        print the shortest distance and route from A to E
#     dist A          print the shortest distance from A to every node
#     show            print the whole graph

def run_command(graph, line):
    """Execute one command against the graph. Returns the (possibly new) graph."""
    parts = line.split()
    if len(parts) == 0:
        return graph
    command = parts[0]

    if command == "edge" and len(parts) == 4:
        graph.add_edge(parts[1], parts[2], int(parts[3]))
        return graph

    if command == "dedge" and len(parts) == 4:
        graph.add_directed_edge(parts[1], parts[2], int(parts[3]))
        return graph

    if command == "path" and len(parts) == 3:
        source, target = parts[1], parts[2]
        distance, path = shortest_path(graph, source, target)
        if path is None:
            print("no path from %s to %s" % (source, target))
        else:
            print("%s -> %s  distance %s  via %s" % (source, target, distance, " -> ".join(path)))
        return graph

    if command == "dist" and len(parts) == 2:
        source = parts[1]
        distance, _ = dijkstra(graph, source)
        for node in sorted(distance):
            print("  %s -> %s = %s" % (source, node, _fmt(distance[node])))
        return graph

    if command == "show":
        print_graph(graph)
        return graph

    if command == "demo":
        print("(loaded the classic six-node demo graph)")
        return demo_graph()

    if command == "reset":
        return Graph()

    if command in ("help", "?"):
        print(REPL_HELP)
        return graph

    print("?  unknown command: " + line + "   (type help)")
    return graph


def run_file(path):
    """Load and run a graph script: build the graph and answer its queries in order."""
    with open(path) as source_file:
        source = source_file.read()
    graph = Graph()
    for raw_line in source.split("\n"):
        line = raw_line
        if "#" in line:
            line = line[:line.index("#")]
        line = line.strip()
        if line == "":
            continue
        graph = run_command(graph, line)


# ── REPL ─────────────────────────────────────────────────────────────────────────

REPL_HELP = """commands:
  edge A B 7     add a two-way edge of length 7 between A and B
  dedge A B 7    add a one-way edge from A to B
  path A E       shortest distance and route from A to E
  dist A         shortest distance from A to every node
  show           print the graph
  demo           reload the classic six-node example graph
  reset          empty the graph
  help           this message
  Ctrl-D         quit"""

BANNER = """Dijkstra's shortest path (Edsger Dijkstra, 1959).
Started with the classic six-node demo graph. Try:
  show
  path A E
  dist A
  edge A E 3
  path A E
Type help for all commands, Ctrl-D to quit."""


def repl():
    graph = demo_graph()
    print(BANNER)
    while True:
        try:
            line = input("graph> ")
        except EOFError:
            print()
            return
        if line.strip() == "":
            continue
        try:
            graph = run_command(graph, line)
        except (ValueError, KeyError, IndexError) as err:
            print("error: " + str(err))


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
        print("[%s] %-52s -> %s" % (mark, description, got))
        if not ok:
            print("        expected %s" % (expected,))

    g = demo_graph()

    # Distances from A on the classic graph (worked out by hand in the README).
    distance, predecessor = dijkstra(g, "A")
    check("dist A->A", distance["A"], 0)
    check("dist A->B", distance["B"], 7)
    check("dist A->C", distance["C"], 9)
    check("dist A->D", distance["D"], 20)
    check("dist A->E", distance["E"], 20)
    check("dist A->F", distance["F"], 11)

    # The actual shortest route A -> E is A C F E, not the direct-looking A F E.
    check("path A->E", reconstruct_path(predecessor, "A", "E"), ["A", "C", "F", "E"])
    check("path A->D", reconstruct_path(predecessor, "A", "D"), ["A", "C", "D"])

    # Source to itself is distance 0 with a one-node path.
    check("path A->A", reconstruct_path(predecessor, "A", "A"), ["A"])

    # The heap version must agree with the original on every node.
    d_heap, _ = dijkstra_heap(g, "A")
    check("heap agrees with scan", d_heap, distance)

    # A directed graph: a one-way street can leave a node unreachable in reverse.
    d = Graph()
    d.add_directed_edge("X", "Y", 5)
    d.add_directed_edge("Y", "Z", 5)
    dd, _ = dijkstra(d, "X")
    check("directed X->Z", dd["Z"], 10)
    # From Z nothing points back to X, so X is unreachable and its path is None.
    z_dist, z_pred = dijkstra(d, "Z")
    check("directed Z->X unreachable", z_dist["X"], INFINITY)
    check("unreachable path is None", reconstruct_path(z_pred, "Z", "X"), None)

    # A tie: two equal-length routes both give the correct distance.
    t = Graph()
    t.add_edge("P", "Q", 1)
    t.add_edge("P", "R", 1)
    t.add_edge("Q", "S", 1)
    t.add_edge("R", "S", 1)
    td, _ = dijkstra(t, "P")
    check("tie distance P->S", td["S"], 2)

    # A greedy first step is not always on the shortest path: taking the cheap edge
    # A->F (14) first would be wrong; going through C is shorter overall.
    dist_af, path_af = shortest_path(g, "A", "F")
    check("A->F goes through C, not direct", path_af, ["A", "C", "F"])
    check("A->F distance is 11 not 14", dist_af, 11)

    # A negative edge is rejected: the algorithm's correctness depends on it.
    rejected = False
    try:
        g.add_edge("A", "Z", -3)
    except ValueError:
        rejected = True
    check("negative edge is rejected", rejected, True)

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
        print("(verbose mode: every settle and relax step is printed)\n")
    files = [a for a in args if not a.startswith("--")]
    if len(files) > 0:
        run_file(files[0])
        return
    repl()


if __name__ == "__main__":
    main()

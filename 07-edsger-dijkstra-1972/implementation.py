"""
Dijkstra's shortest path, built the way Edsger Dijkstra described it in 1959.

Dijkstra conceived this in 1956, in his head, in about twenty minutes, while
sitting at a cafe terrace in Amsterdam. He needed a demonstration problem simple
enough for a general audience to follow but real enough to show off the ARMAC
computer: the shortest way to travel between two Dutch cities. He published it in
1959 as "A Note on Two Problems in Connexion with Graphs" (Numerische Mathematik
1, pp. 269-271). It is three pages long and it is still the algorithm behind route
planners, network routing (OSPF, IS-IS), and countless graph problems.

This file is that algorithm, made runnable. It has a graph you can build edge by
edge, the core single-source shortest-path routine, path reconstruction (so you
get the actual route, not just its length), a REPL to explore graphs by hand, and
a verbose mode that narrates every settle and relaxation step.

It mirrors the 1959 paper rather than optimising it. The original used no heap: it
kept a set of tentative distances and, on each round, scanned that set for the
smallest one. That is exactly what settle_next() does here. The modern
heap-based version is a speed improvement layered on top; the idea underneath is
unchanged.

BEFORE this algorithm: to find the cheapest route you either enumerated paths
(which grows exponentially) or trusted brittle heuristics that a cleverly weighted
map could defeat.

AFTER: one pass that settles nodes in order of increasing distance, provably
correct as long as no edge is negative, gives you the shortest distance to every
node from a single start.

Pipeline:
    edges (u, v, weight)
        -> build adjacency  (node -> list of (neighbour, weight))
        -> initialise        (start = 0, everything else = infinity)
        -> settle + relax    (pick the closest unsettled node, update neighbours)
        -> distances + predecessors
        -> reconstruct        (walk predecessors backward to get the route)

Run:
    python3 implementation.py            # interactive REPL
    python3 implementation.py roads.txt  # load a graph file and run its queries
    python3 implementation.py --test     # self-test suite (18 cases)
    python3 implementation.py --verbose  # REPL that narrates every step
"""

import sys


INF = float("inf")
VERBOSE = False


# -- Graph: nodes and weighted edges ----------------------------------------------
#
# A graph here is an adjacency map: each node points to a list of (neighbour,
# weight) pairs. Edges are directed in the data structure. add_edge adds one
# direction; add_edge with both=True adds both, which is how a two-way street or an
# undirected road network is modelled.

class Graph:
    def __init__(self):
        self.adjacency = {}

    def add_node(self, node):
        if node not in self.adjacency:
            self.adjacency[node] = []

    def add_edge(self, u, v, weight, both=True):
        if weight < 0:
            # Dijkstra's correctness rests on non-negative edges. A negative edge
            # could make a longer detour cheaper, which breaks the greedy step.
            raise ValueError("Dijkstra requires non-negative weights; got %s" % weight)
        self.add_node(u)
        self.add_node(v)
        self.adjacency[u].append((v, weight))
        if both:
            self.adjacency[v].append((u, weight))

    def neighbours(self, node):
        return self.adjacency[node]

    def nodes(self):
        return list(self.adjacency.keys())


# -- The algorithm: settle the closest node, relax its neighbours -----------------

def settle_next(distance, unsettled):
    """Return the unsettled node with the smallest tentative distance.

    This linear scan over the tentative distances is the original 1959 selection
    step. Returns None if every remaining node is unreachable (all infinite).
    """
    current = None
    best = INF
    for node in unsettled:
        if distance[node] < best:
            best = distance[node]
            current = node
    return current


def dijkstra(graph, start):
    """Single-source shortest paths from start.

    Returns (distance, predecessor):
      distance[node]    = length of the shortest path start -> node
      predecessor[node] = the node just before `node` on that path (None at start)
    """
    distance = {}
    predecessor = {}
    for node in graph.nodes():
        distance[node] = INF
        predecessor[node] = None
    distance[start] = 0

    unsettled = set(graph.nodes())

    while len(unsettled) > 0:
        current = settle_next(distance, unsettled)

        # No reachable node remains. The rest of the graph is disconnected.
        if current is None:
            break

        unsettled.remove(current)

        if VERBOSE:
            print("settle %s (distance %s)" % (current, fmt(distance[current])))

        # Relax every edge leaving current.
        for neighbour, weight in graph.neighbours(current):
            if neighbour not in unsettled:
                # Already settled: its distance is final, skip it.
                continue
            through_current = distance[current] + weight
            if through_current < distance[neighbour]:
                if VERBOSE:
                    print("  relax %s: %s -> %s via %s"
                          % (neighbour, fmt(distance[neighbour]),
                             fmt(through_current), current))
                distance[neighbour] = through_current
                predecessor[neighbour] = current

    return distance, predecessor


def reconstruct_path(predecessor, start, target):
    """Walk the predecessor chain backward from target to start.

    Returns the list of nodes from start to target, or None if target was never
    reached (no path exists).
    """
    if target not in predecessor:
        return None
    # target is reachable only if it is the start or has a predecessor.
    if target != start and predecessor[target] is None:
        return None

    path = []
    node = target
    while node is not None:
        path.append(node)
        if node == start:
            break
        node = predecessor[node]
    path.reverse()

    # If the walk did not end at start, there was no connected path.
    if path[0] != start:
        return None
    return path


def shortest_path(graph, start, target):
    """Convenience: the shortest route and its total length as (path, distance)."""
    distance, predecessor = dijkstra(graph, start)
    path = reconstruct_path(predecessor, start, target)
    if path is None:
        return None, INF
    return path, distance[target]


# -- Formatting -------------------------------------------------------------------

def fmt(x):
    """Render infinity readably; leave finite numbers as-is."""
    if x == INF:
        return "inf"
    return str(x)


def show_graph(graph):
    """Print the adjacency structure, one node per line."""
    for node in sorted(graph.nodes(), key=str):
        edges = graph.neighbours(node)
        parts = []
        for neighbour, weight in edges:
            parts.append("%s(%s)" % (neighbour, weight))
        print("  %s -> %s" % (node, ", ".join(parts) if parts else "(no edges)"))


# -- File loader ------------------------------------------------------------------
#
# A graph file has one instruction per line:
#   u v w        add an (undirected) edge u--v with weight w
#   dedge u v w  add a directed edge u->v with weight w
#   path u v     print the shortest route from u to v
#   dist u       print the shortest distance from u to every node
# Blank lines and lines starting with # are ignored.

def run_file(path):
    graph = Graph()
    with open(path) as source_file:
        for raw in source_file:
            line = raw.strip()
            if line == "" or line.startswith("#"):
                continue
            handle_command(line, graph, echo=True)


def handle_command(line, graph, echo=False):
    """Run one REPL / file command against graph. Returns False to quit."""
    parts = line.split()
    verb = parts[0]

    if verb in ("quit", "exit"):
        return False

    if verb == "help":
        print(HELP)
        return True

    if verb == "show":
        show_graph(graph)
        return True

    if verb == "edge":
        # edge u v w  -> undirected edge
        u, v, w = parts[1], parts[2], number(parts[3])
        graph.add_edge(u, v, w, both=True)
        if echo:
            print("edge %s--%s (%s)" % (u, v, w))
        return True

    if verb == "dedge":
        # dedge u v w  -> directed edge u->v
        u, v, w = parts[1], parts[2], number(parts[3])
        graph.add_edge(u, v, w, both=False)
        if echo:
            print("edge %s->%s (%s)" % (u, v, w))
        return True

    if verb == "path":
        u, v = parts[1], parts[2]
        route, total = shortest_path(graph, u, v)
        if route is None:
            print("no path from %s to %s" % (u, v))
        else:
            print("%s   (distance %s)" % (" -> ".join(route), fmt(total)))
        return True

    if verb == "dist":
        start = parts[1]
        distance, _ = dijkstra(graph, start)
        for node in sorted(distance, key=str):
            print("  %s -> %s = %s" % (start, node, fmt(distance[node])))
        return True

    print("unknown command: %s (try 'help')" % verb)
    return True


def number(token):
    """Parse an edge weight as int if possible, else float."""
    try:
        return int(token)
    except ValueError:
        return float(token)


# -- REPL -------------------------------------------------------------------------

HELP = """Commands:
  edge u v w     add a two-way edge u--v of weight w      e.g.  edge A B 4
  dedge u v w    add a one-way edge u->v of weight w       e.g.  dedge A B 4
  path u v       shortest route from u to v                e.g.  path A D
  dist u         shortest distance from u to everywhere     e.g.  dist A
  show           print the graph
  help           this message
  quit           leave"""

BANNER = """Dijkstra's shortest path (1959).
Build a graph, then ask for routes. Try:
  edge A B 4
  edge A C 2
  edge C B 1
  edge B D 5
  path A D
Type 'help' for all commands, 'quit' to leave."""


def repl():
    graph = Graph()
    print(BANNER)
    while True:
        try:
            line = input("graph> ").strip()
        except EOFError:
            print()
            return
        if line == "":
            continue
        try:
            keep_going = handle_command(line, graph)
            if not keep_going:
                return
        except (ValueError, IndexError, KeyError) as err:
            print("error: " + str(err))


# -- Self-test suite --------------------------------------------------------------

def build_sample():
    """The road network used in the README's worked example.

        A --4-- B        A--C = 2   C--B = 1   B--D = 5
        |       |        A--B = 4   C--D = 8
        2       5
        |       |
        C --1-- B ...    (drawn out fully below)
    """
    g = Graph()
    g.add_edge("A", "B", 4)
    g.add_edge("A", "C", 2)
    g.add_edge("B", "C", 1)
    g.add_edge("B", "D", 5)
    g.add_edge("C", "D", 8)
    return g


def run_tests():
    passed = 0
    cases = []

    # Distances on the sample undirected graph, start = A.
    g = build_sample()
    dist, pred = dijkstra(g, "A")
    cases.append(("A->A distance", dist["A"], 0))
    cases.append(("A->C distance", dist["C"], 2))
    cases.append(("A->B distance (via C is shorter)", dist["B"], 3))
    cases.append(("A->D distance", dist["D"], 8))

    # The actual routes.
    route, total = shortest_path(g, "A", "D")
    cases.append(("A->D route", " ".join(route), "A C B D"))
    cases.append(("A->D total", total, 8))
    route, total = shortest_path(g, "A", "B")
    cases.append(("A->B route goes through C", " ".join(route), "A C B"))

    # Symmetry: on an undirected graph, d(A,D) == d(D,A).
    dist_from_d, _ = dijkstra(g, "D")
    cases.append(("undirected symmetry d(A,D)=d(D,A)", dist_from_d["A"], 8))

    # A single node with no edges.
    solo = Graph()
    solo.add_node("X")
    dist, _ = dijkstra(solo, "X")
    cases.append(("lone node distance to self", dist["X"], 0))

    # Disconnected graph: unreachable node stays at infinity.
    disc = Graph()
    disc.add_edge("A", "B", 1)
    disc.add_node("Z")
    dist, _ = dijkstra(disc, "A")
    cases.append(("unreachable node is infinite", dist["Z"], INF))
    route, total = shortest_path(disc, "A", "Z")
    cases.append(("no path returns None", route, None))

    # Directed graph: A->B exists but B->A does not.
    directed = Graph()
    directed.add_edge("A", "B", 5, both=False)
    dist, _ = dijkstra(directed, "A")
    cases.append(("directed A->B reachable", dist["B"], 5))
    dist_b, _ = dijkstra(directed, "B")
    cases.append(("directed B->A unreachable", dist_b["A"], INF))

    # Greedy trap: the direct edge is long, a two-hop detour is shorter.
    trap = Graph()
    trap.add_edge("S", "T", 10, both=False)
    trap.add_edge("S", "M", 3, both=False)
    trap.add_edge("M", "T", 4, both=False)
    route, total = shortest_path(trap, "S", "T")
    cases.append(("detour beats direct edge", total, 7))
    cases.append(("detour route is S M T", " ".join(route), "S M T"))

    # A longer line graph: distances accumulate.
    line = Graph()
    line.add_edge("1", "2", 2, both=False)
    line.add_edge("2", "3", 2, both=False)
    line.add_edge("3", "4", 2, both=False)
    dist, _ = dijkstra(line, "1")
    cases.append(("chain 1->4 sums to 6", dist["4"], 6))

    # Float weights work too.
    fg = Graph()
    fg.add_edge("A", "B", 1.5)
    fg.add_edge("B", "C", 2.5)
    dist, _ = dijkstra(fg, "A")
    cases.append(("float weights: A->C = 4.0", dist["C"], 4.0))

    # A negative edge is rejected up front.
    neg_rejected = False
    try:
        bad = Graph()
        bad.add_edge("A", "B", -1)
    except ValueError:
        neg_rejected = True
    cases.append(("negative edge rejected", neg_rejected, True))

    for description, got, expected in cases:
        ok = got == expected
        if ok:
            passed += 1
        mark = "PASS" if ok else "FAIL"
        print("[%s] %-40s -> %s" % (mark, description, fmt(got) if isinstance(got, float) else got))
        if not ok:
            print("        expected %s" % (expected,))

    total_cases = len(cases)
    print()
    print("%d/%d passed" % (passed, total_cases))
    return passed == total_cases


# -- Entry point ------------------------------------------------------------------

def main():
    global VERBOSE
    args = sys.argv[1:]
    if "--test" in args:
        ok = run_tests()
        sys.exit(0 if ok else 1)
    if "--verbose" in args:
        VERBOSE = True
        print("(verbose mode: every settle and relaxation is printed)\n")
    files = [a for a in args if not a.startswith("--")]
    if len(files) > 0:
        run_file(files[0])
        return
    repl()


if __name__ == "__main__":
    main()

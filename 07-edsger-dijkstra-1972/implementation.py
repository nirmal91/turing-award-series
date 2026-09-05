"""
Dijkstra's shortest path, built the way Edsger W. Dijkstra described it in 1959.

Dijkstra's "A Note on Two Problems in Connexion with Graphs" (Numerische
Mathematik, 1959) gave the first systematic, provably-correct method for the
shortest path between two nodes of a weighted graph. He came up with it in about
twenty minutes, without pencil and paper, while thinking about how to show off the
ARMAC computer with the shortest route between Rotterdam and Groningen.

This file is that method, made runnable. It mirrors the 1959 paper rather than
simulating it: the core loop keeps a set of tentative distances (Dijkstra's
"labels"), repeatedly settles the nearest unsettled node, and relaxes its
neighbors. It also records a predecessor for each node so the actual path, not
just its length, can be reconstructed. A verbose mode prints the label table after
every step, which is exactly the bookkeeping Dijkstra laid out.

BEFORE this algorithm: to find the shortest route you enumerated paths and
compared them. The number of paths through a graph grows exponentially, so this
was hopeless for anything but tiny maps, and there was no method guaranteed to
find the best route without checking almost all of them.

AFTER: give every node a tentative distance (0 for the start, infinity for the
rest), then repeat — take the closest unsettled node, freeze its distance, and see
if routing through it makes any neighbor cheaper. Because edge weights are never
negative, the closest unsettled node can never be improved by a detour, so its
distance is final the instant you pick it. Each node is settled once. An
exponential search becomes a single sweep.

Pipeline:
    graph (nodes + weighted edges)
        -> initialize labels  (start = 0, everyone else = infinity)
        -> settle nearest     (pick the smallest unsettled label; it is now final)
        -> relax neighbors    (lower a neighbor's label if this route is cheaper)
        -> repeat until every reachable node is settled
        -> reconstruct path   (follow predecessors back from the target)

Run:
    python3 implementation.py             # interactive shortest-path explorer
    python3 implementation.py routes.graph  # load a graph file and solve it
    python3 implementation.py --test      # self-test suite (16 cases)
    python3 implementation.py --verbose   # explorer that prints the label table
"""

import sys


INFINITY = float("inf")
VERBOSE = False


# ── The graph ────────────────────────────────────────────────────────────────────
#
# A graph is nodes joined by weighted, directed edges. We store it as a dict from
# each node to a dict of {neighbor: weight}. An undirected road is just two directed
# edges. Dijkstra's method needs one thing from the weights: none may be negative.

class Graph:
    def __init__(self):
        self.edges = {}                 # node -> {neighbor: weight}

    def add_node(self, node):
        if node not in self.edges:
            self.edges[node] = {}

    def add_edge(self, source, target, weight, undirected=False):
        if weight < 0:
            raise ValueError("negative weight %s on %s->%s; Dijkstra forbids it"
                             % (weight, source, target))
        self.add_node(source)
        self.add_node(target)
        self.edges[source][target] = weight
        if undirected:
            self.edges[target][source] = weight

    def nodes(self):
        return list(self.edges)

    def neighbors(self, node):
        return self.edges.get(node, {})


# ── The algorithm: Dijkstra's label-setting method ───────────────────────────────
#
# This is the heart of the 1959 paper. `distance` holds each node's tentative
# label; `predecessor` remembers which settled node we arrived from, so the path
# itself can be rebuilt afterward. We settle nodes one at a time, always the
# nearest unsettled one, and relax its outgoing edges.

def dijkstra(graph, start):
    """Compute shortest distances and predecessors from `start` to all nodes.

    Returns (distance, predecessor), each a dict keyed by node. A node left at
    INFINITY is unreachable from the start.
    """
    if start not in graph.edges:
        raise KeyError("start node %r is not in the graph" % (start,))

    distance = {}
    predecessor = {}
    for node in graph.nodes():
        distance[node] = INFINITY
        predecessor[node] = None
    distance[start] = 0

    unvisited = set(graph.nodes())
    step = 0

    while len(unvisited) > 0:
        # Find the unsettled node with the smallest tentative label. Dijkstra's
        # original does exactly this linear scan; modern versions use a priority
        # queue (a binary or Fibonacci heap) to find the minimum faster, but the
        # logic below is unchanged.
        current = None
        for node in unvisited:
            if distance[node] == INFINITY:
                continue
            if current is None or distance[node] < distance[current]:
                current = node

        # Every remaining node is unreachable — nothing left to settle.
        if current is None:
            break

        unvisited.remove(current)       # `current` is now final
        step += 1

        if VERBOSE:
            _print_step(step, current, distance, unvisited)

        # Relax every outgoing edge from `current`.
        for neighbor in graph.neighbors(current):
            if neighbor not in unvisited:
                continue                # already settled, cannot improve
            weight = graph.neighbors(current)[neighbor]
            candidate = distance[current] + weight
            if candidate < distance[neighbor]:
                distance[neighbor] = candidate
                predecessor[neighbor] = current

    return distance, predecessor


def shortest_path(graph, start, target):
    """Return (path_as_list, total_distance) for the cheapest start->target route.

    If the target is unreachable, returns ([], INFINITY).
    """
    distance, predecessor = dijkstra(graph, start)
    if distance.get(target, INFINITY) == INFINITY:
        return [], INFINITY

    # Walk predecessors backward from target to start, then reverse.
    path = []
    node = target
    while node is not None:
        path.append(node)
        node = predecessor[node]
    path.reverse()
    return path, distance[target]


# ── Verbose bookkeeping ──────────────────────────────────────────────────────────

def _print_step(step, current, distance, unvisited):
    """Print the label table at the moment `current` is settled."""
    print("step %d: settle %s (distance %s)" % (step, current, _fmt(distance[current])))
    labels = []
    for node in sorted(distance):
        mark = "*" if node not in unvisited else " "   # * = settled
        labels.append("%s%s=%s" % (mark, node, _fmt(distance[node])))
    print("        labels: " + "  ".join(labels))


def _fmt(value):
    return "inf" if value == INFINITY else str(value)


# ── Graph file reader ────────────────────────────────────────────────────────────
#
# A graph file is plain text, one instruction per line, so a route map can be
# written by hand and loaded with `python3 implementation.py routes.graph`:
#
#     # lines beginning with # are comments
#     A B 7            an edge A -> B of weight 7
#     A C 9 both       an UNDIRECTED edge (both A->C and C->A) of weight 9
#     from A           print shortest distances from A to everyone
#     path A E         print the shortest route from A to E
#
# Edge lines build the graph; `from` and `path` lines are queries run in order.

def load_graph_file(path):
    graph = Graph()
    queries = []
    with open(path) as source:
        for raw_line in source:
            line = raw_line.strip()
            if line == "" or line.startswith("#"):
                continue
            parts = line.split()
            head = parts[0]
            if head == "from":
                queries.append(("from", parts[1]))
            elif head == "path":
                queries.append(("path", parts[1], parts[2]))
            else:
                source_node = parts[0]
                target_node = parts[1]
                weight = _number(parts[2])
                undirected = len(parts) > 3 and parts[3] == "both"
                graph.add_edge(source_node, target_node, weight, undirected)
    return graph, queries


def _number(text):
    """Parse an edge weight as int when possible, else float."""
    try:
        return int(text)
    except ValueError:
        return float(text)


def run_file(path):
    """Load a graph file, run its queries (or, if it has none, all distances from
    the first node), and print the results."""
    graph, queries = load_graph_file(path)
    if len(queries) == 0 and len(graph.nodes()) > 0:
        queries = [("from", graph.nodes()[0])]

    for query in queries:
        if query[0] == "from":
            start = query[1]
            distance, _ = dijkstra(graph, start)
            print("shortest distance from %s:" % start)
            for node in sorted(distance):
                print("  %s -> %s : %s" % (start, node, _fmt(distance[node])))
        else:
            _, start, target = query
            path_nodes, total = shortest_path(graph, start, target)
            if total == INFINITY:
                print("no path from %s to %s" % (start, target))
            else:
                print("%s -> %s : %s   (%s)"
                      % (start, target, total, " -> ".join(path_nodes)))
        print()


# ── The example graph, used by the demo and the tests ────────────────────────────

def example_graph():
    """A small weighted, directed map. The shortest A->E is 20 (A C F E), even
    though the single edge A->F->E route looks direct at 23."""
    graph = Graph()
    for source, target, weight in [
        ("A", "B", 7), ("A", "C", 9), ("A", "F", 14),
        ("B", "C", 10), ("B", "D", 15),
        ("C", "D", 11), ("C", "F", 2),
        ("D", "E", 6),
        ("F", "E", 9),
    ]:
        graph.add_edge(source, target, weight)
    return graph


# ── Interactive explorer ─────────────────────────────────────────────────────────

BANNER = """Dijkstra's shortest path (1959). Build a graph, then ask for routes.
Commands:
  edge A B 7        add a directed edge A -> B of weight 7
  edge A B 7 both   add an undirected edge (both directions)
  path A E          shortest route and distance from A to E
  from A            shortest distance from A to every node
  show              list the graph's edges
  demo              load the built-in example map
  help              show this text
Type a command, or Ctrl-D to quit."""


def repl():
    graph = Graph()
    print(BANNER)
    while True:
        try:
            line = input("dijkstra> ").strip()
        except EOFError:
            print()
            return
        if line == "":
            continue
        parts = line.split()
        command = parts[0]
        try:
            if command == "help":
                print(BANNER)
            elif command == "demo":
                graph = example_graph()
                print("loaded the example map (nodes A..F)")
            elif command == "show":
                _show(graph)
            elif command == "edge":
                source, target = parts[1], parts[2]
                weight = _number(parts[3])
                undirected = len(parts) > 4 and parts[4] == "both"
                graph.add_edge(source, target, weight, undirected)
                print("added %s %s %s%s"
                      % (source, target, weight, " (both ways)" if undirected else ""))
            elif command == "from":
                start = parts[1]
                distance, _ = dijkstra(graph, start)
                for node in sorted(distance):
                    print("  %s -> %s : %s" % (start, node, _fmt(distance[node])))
            elif command == "path":
                start, target = parts[1], parts[2]
                path_nodes, total = shortest_path(graph, start, target)
                if total == INFINITY:
                    print("  no path from %s to %s" % (start, target))
                else:
                    print("  %s   (distance %s)" % (" -> ".join(path_nodes), total))
            else:
                print("unknown command: %s (try 'help')" % command)
        except (IndexError, ValueError, KeyError) as err:
            print("error: " + str(err))


def _show(graph):
    if len(graph.nodes()) == 0:
        print("  (empty graph — add edges with 'edge A B 7')")
        return
    for source in sorted(graph.nodes()):
        for target in sorted(graph.neighbors(source)):
            print("  %s -> %s : %s" % (source, target, graph.neighbors(source)[target]))


# ── Self-test suite ──────────────────────────────────────────────────────────────

def run_tests():
    graph = example_graph()

    cases = []

    # Distances from A across the example map (worked out by hand in the README).
    distance, _ = dijkstra(graph, "A")
    cases.append(("dist A->A", distance["A"], 0))
    cases.append(("dist A->B", distance["B"], 7))
    cases.append(("dist A->C", distance["C"], 9))
    cases.append(("dist A->D", distance["D"], 20))
    cases.append(("dist A->E", distance["E"], 20))
    cases.append(("dist A->F", distance["F"], 11))

    # The actual shortest route, not just its length.
    path_ae, total_ae = shortest_path(graph, "A", "E")
    cases.append(("path A->E nodes", path_ae, ["A", "C", "F", "E"]))
    cases.append(("path A->E total", total_ae, 20))

    # The greedy-looking direct edge is not the answer: A->F alone costs 14,
    # but routing A->C->F costs 11.
    cases.append(("dist A->F beats direct 14", distance["F"] < 14, True))

    # A node with no outgoing edges is still reachable.
    path_de, total_de = shortest_path(graph, "D", "E")
    cases.append(("path D->E", (path_de, total_de), (["D", "E"], 6)))

    # Unreachable target: nothing points back into A from E.
    path_ea, total_ea = shortest_path(graph, "E", "A")
    cases.append(("E->A unreachable path", path_ea, []))
    cases.append(("E->A unreachable dist", total_ea, INFINITY))

    # Start to itself is always 0.
    cases.append(("dist C->C", dijkstra(graph, "C")[0]["C"], 0))

    # A tie: two equally short routes give the same distance (the path may be either).
    tie = Graph()
    tie.add_edge("S", "X", 1)
    tie.add_edge("S", "Y", 1)
    tie.add_edge("X", "T", 1)
    tie.add_edge("Y", "T", 1)
    _, tie_total = shortest_path(tie, "S", "T")
    cases.append(("tie S->T distance", tie_total, 2))

    # Undirected edges work in both directions.
    ud = Graph()
    ud.add_edge("P", "Q", 5, undirected=True)
    cases.append(("undirected Q->P", shortest_path(ud, "Q", "P"), (["Q", "P"], 5)))

    # A negative weight must be rejected — Dijkstra's one precondition.
    negative_rejected = False
    try:
        Graph().add_edge("A", "B", -1)
    except ValueError:
        negative_rejected = True
    cases.append(("negative weight rejected", negative_rejected, True))

    passed = 0
    for name, got, expected in cases:
        ok = got == expected
        if ok:
            passed += 1
        mark = "PASS" if ok else "FAIL"
        print("[%s] %-32s -> %s" % (mark, name, got))
        if not ok:
            print("        expected %s" % (expected,))

    total = len(cases)
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
        print("(verbose mode: the label table is printed after every step)\n")
    files = [a for a in args if not a.startswith("--")]
    if len(files) > 0:
        run_file(files[0])
        return
    repl()


if __name__ == "__main__":
    main()

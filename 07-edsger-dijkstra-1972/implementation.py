"""
implementation.py — Dijkstra's shortest path algorithm (Edsger W. Dijkstra, 1959).

The full working version. Same idea as concept.py, but with the pieces the
1959 note and every textbook since actually use:

  - a priority queue (a min-heap) so we find the closest node in log time
    instead of scanning the whole frontier every step
  - predecessor tracking, so we can reconstruct the actual route, not just
    the length of it
  - a text graph format you can write in a file and run

Before Dijkstra: finding the shortest route through a network of any size was
a hand exercise, error-prone and slow. There was no agreed procedure a machine
could follow. After Dijkstra: one loop, provably correct, finds the shortest
path from a source to every other node. It powers routing on the internet
(OSPF, IS-IS), GPS navigation, and network analysis everywhere.

Pipeline:

  graph file/REPL  ->  parse edges  ->  build adjacency  ->  Dijkstra (min-heap)
                                                                     |
                                              distances + predecessors
                                                                     |
                                                          reconstruct path

Run it:

  python3 implementation.py                 # demo on a built-in 6-city map
  python3 implementation.py graph.txt       # run on a graph file
  python3 implementation.py --test          # self-test suite (16 cases)
  python3 implementation.py --verbose       # show the heap and distances each step
  python3 implementation.py graph.txt --verbose

Graph file format (see example.graph):

  # lines starting with # are comments
  directed              # optional; without it, every edge goes both ways
  source A              # optional; which node to start from (default: first seen)
  A B 7                 # an edge from A to B with weight 7
  A C 9
"""

import heapq
import sys


INFINITY = float("inf")


# --------------------------------------------------------------------------
# The graph. Stored as node -> list of (neighbor, weight).
# --------------------------------------------------------------------------

class Graph:
    def __init__(self, directed=False):
        self.directed = directed
        self.adjacency = {}

    def add_node(self, node):
        if node not in self.adjacency:
            self.adjacency[node] = []

    def add_edge(self, source, target, weight):
        if weight < 0:
            raise ValueError(
                "Dijkstra requires non-negative weights; got " + str(weight)
                + " on edge " + source + "->" + target
            )
        self.add_node(source)
        self.add_node(target)
        self.adjacency[source].append((target, weight))
        if not self.directed:
            self.adjacency[target].append((source, weight))

    def nodes(self):
        return list(self.adjacency.keys())

    def neighbors(self, node):
        return self.adjacency.get(node, [])


# --------------------------------------------------------------------------
# The algorithm.
# --------------------------------------------------------------------------

def dijkstra(graph, source, verbose=False):
    """Return (distance, predecessor) dicts for shortest paths from source.

    distance[n]     = length of the shortest path source -> n (inf if unreachable)
    predecessor[n]  = the node we arrived from on that shortest path (None at source)
    """
    if source not in graph.adjacency:
        raise ValueError("source node '" + str(source) + "' is not in the graph")

    distance = {}
    predecessor = {}
    for node in graph.nodes():
        distance[node] = INFINITY
        predecessor[node] = None
    distance[source] = 0

    # The frontier is a min-heap of (known_distance, node). We may push a node
    # more than once as we find better distances; the "finalized" set lets us
    # ignore the stale, larger entries when they pop out.
    frontier = [(0, source)]
    finalized = set()

    step = 0
    while len(frontier) > 0:
        current_distance, current = heapq.heappop(frontier)

        # Skip stale heap entries: if we already finalized this node, the copy
        # we just popped is an older, worse one.
        if current in finalized:
            continue
        finalized.add(current)

        if verbose:
            step = step + 1
            _print_step(step, current, current_distance, distance, finalized)

        # Relaxation: for each road out of current, see if going through current
        # gives a shorter route to the neighbor than anything found so far.
        for neighbor, weight in graph.neighbors(current):
            if neighbor in finalized:
                continue
            candidate = current_distance + weight
            if candidate < distance[neighbor]:
                distance[neighbor] = candidate
                predecessor[neighbor] = current
                heapq.heappush(frontier, (candidate, neighbor))

    return distance, predecessor


def reconstruct_path(predecessor, source, target):
    """Walk the predecessor chain backwards from target to source.

    Returns the list of nodes source..target, or None if target is unreachable.
    """
    if target != source and predecessor.get(target) is None:
        return None

    path = []
    node = target
    while node is not None:
        path.append(node)
        if node == source:
            break
        node = predecessor.get(node)

    path.reverse()
    if path[0] != source:
        return None
    return path


# --------------------------------------------------------------------------
# Parsing a graph file.
# --------------------------------------------------------------------------

def parse_graph(text):
    """Parse the text graph format. Returns (graph, source_or_None)."""
    directed = False
    declared_source = None
    edges = []
    first_node = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line == "":
            continue
        if line.startswith("#"):
            continue

        parts = line.split()
        keyword = parts[0].lower()

        if keyword == "directed":
            directed = True
            continue
        if keyword == "source":
            declared_source = parts[1]
            continue

        # Otherwise it is an edge: source target weight
        if len(parts) != 3:
            raise ValueError("bad edge line (expected 'A B weight'): " + line)
        source, target, weight_text = parts[0], parts[1], parts[2]
        weight = float(weight_text)
        # Store ints as ints so output reads cleanly.
        if weight == int(weight):
            weight = int(weight)
        edges.append((source, target, weight))
        if first_node is None:
            first_node = source

    graph = Graph(directed=directed)
    for source, target, weight in edges:
        graph.add_edge(source, target, weight)

    chosen_source = declared_source
    if chosen_source is None:
        chosen_source = first_node
    return graph, chosen_source


# --------------------------------------------------------------------------
# Output helpers.
# --------------------------------------------------------------------------

def _print_step(step, current, current_distance, distance, finalized):
    print("step " + str(step) + ": finalize " + str(current)
          + " at distance " + str(current_distance))
    row = []
    for node in sorted(distance.keys()):
        mark = "*" if node in finalized else " "
        value = distance[node]
        text = "inf" if value == INFINITY else str(value)
        row.append(mark + node + "=" + text)
    print("        distances: " + "  ".join(row) + "   (* = finalized)")


def report(graph, source, verbose=False):
    distance, predecessor = dijkstra(graph, source, verbose=verbose)
    if verbose:
        print("")
    print("Shortest paths from " + str(source) + ":")
    for node in sorted(distance.keys()):
        if distance[node] == INFINITY:
            print("  " + source + " -> " + node + " : unreachable")
            continue
        path = reconstruct_path(predecessor, source, node)
        print("  " + source + " -> " + node + " : distance " + str(distance[node])
              + "   path " + " -> ".join(path))


# --------------------------------------------------------------------------
# Built-in demo (the classic Wikipedia six-node map).
# --------------------------------------------------------------------------

def demo_graph():
    graph = Graph(directed=False)
    graph.add_edge("A", "B", 7)
    graph.add_edge("A", "C", 9)
    graph.add_edge("A", "F", 14)
    graph.add_edge("B", "C", 10)
    graph.add_edge("B", "D", 15)
    graph.add_edge("C", "D", 11)
    graph.add_edge("C", "F", 2)
    graph.add_edge("D", "E", 6)
    graph.add_edge("E", "F", 9)
    return graph


def run_demo(verbose=False):
    print("Demo: shortest routes across a six-city map, starting at A.")
    print("Before Dijkstra you traced this by hand and hoped. Now:")
    print("")
    graph = demo_graph()
    report(graph, "A", verbose=verbose)
    print("")
    print("Try your own: write a graph file and run  python3 implementation.py yourfile")


def repl():
    print("Dijkstra shortest-path REPL.")
    print("Enter edges as:  A B 7   (node node weight). Blank line runs it.")
    print("Commands:  source X   |   directed   |   run   |   quit")
    graph = Graph(directed=False)
    source = None
    while True:
        try:
            line = input("graph> ").strip()
        except EOFError:
            break
        if line == "":
            continue
        low = line.lower()
        if low in ("quit", "exit"):
            break
        if low == "directed":
            graph.directed = True
            print("(edges are now directed)")
            continue
        if low == "run":
            if len(graph.nodes()) == 0:
                print("no edges yet")
                continue
            use_source = source if source is not None else graph.nodes()[0]
            report(graph, use_source)
            continue
        parts = line.split()
        if parts[0].lower() == "source" and len(parts) == 2:
            source = parts[1]
            print("(source = " + source + ")")
            continue
        if len(parts) == 3:
            try:
                weight = float(parts[2])
                if weight == int(weight):
                    weight = int(weight)
                graph.add_edge(parts[0], parts[1], weight)
                if source is None:
                    source = parts[0]
                print("(added " + parts[0] + " <-> " + parts[1] + " : " + str(weight) + ")")
            except ValueError as error:
                print("error: " + str(error))
            continue
        print("did not understand: " + line)


# --------------------------------------------------------------------------
# Test suite.
# --------------------------------------------------------------------------

def run_tests():
    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            passed = passed + 1
            print("  PASS  " + name)
        else:
            failed = failed + 1
            print("  FAIL  " + name)

    # 1. Source distance to itself is 0.
    g = demo_graph()
    dist, pred = dijkstra(g, "A")
    check("source-to-self is 0", dist["A"] == 0)

    # 2-7. Known shortest distances on the classic six-node map from A.
    check("A->B = 7", dist["B"] == 7)
    check("A->C = 9", dist["C"] == 9)
    check("A->D = 20", dist["D"] == 20)
    check("A->E = 20", dist["E"] == 20)
    check("A->F = 11", dist["F"] == 11)
    # The shortest A->F is A-C-F (9+2=11), not the direct A-F edge (14).
    path_f = reconstruct_path(pred, "A", "F")
    check("A->F goes through C, not the direct edge", path_f == ["A", "C", "F"])

    # 8. Path reconstruction to D.
    path_d = reconstruct_path(pred, "A", "D")
    check("A->D path is A,C,D", path_d == ["A", "C", "D"])

    # 9. Single node graph.
    g1 = Graph()
    g1.add_node("X")
    d1, _ = dijkstra(g1, "X")
    check("single node distance 0", d1["X"] == 0)

    # 10. Disconnected node is unreachable.
    g2 = Graph()
    g2.add_edge("A", "B", 5)
    g2.add_node("Z")
    d2, _ = dijkstra(g2, "A")
    check("disconnected node is infinity", d2["Z"] == INFINITY)

    # 11. Straight line chain adds up.
    g3 = Graph()
    g3.add_edge("A", "B", 1)
    g3.add_edge("B", "C", 2)
    g3.add_edge("C", "D", 3)
    d3, _ = dijkstra(g3, "A")
    check("chain A->D = 6", d3["D"] == 6)

    # 12. A cheaper multi-hop beats a direct expensive edge.
    g4 = Graph()
    g4.add_edge("A", "B", 100)
    g4.add_edge("A", "C", 1)
    g4.add_edge("C", "B", 1)
    d4, p4 = dijkstra(g4, "A")
    check("prefers 2-hop (2) over direct (100)", d4["B"] == 2)
    check("path is A,C,B", reconstruct_path(p4, "A", "B") == ["A", "C", "B"])

    # 13. Directed edges do not go backwards.
    g5 = Graph(directed=True)
    g5.add_edge("A", "B", 3)
    d5, _ = dijkstra(g5, "B")
    check("directed: B cannot reach A", d5["A"] == INFINITY)

    # 14. Negative weight is rejected.
    negative_rejected = False
    try:
        gn = Graph()
        gn.add_edge("A", "B", -1)
    except ValueError:
        negative_rejected = True
    check("negative weight rejected", negative_rejected)

    # 15. Unknown source is rejected.
    bad_source_rejected = False
    try:
        dijkstra(demo_graph(), "Q")
    except ValueError:
        bad_source_rejected = True
    check("unknown source rejected", bad_source_rejected)

    # 16. Parsing a graph file gives the same answer as the built-in demo.
    text = (
        "source A\n"
        "A B 7\nA C 9\nA F 14\nB C 10\nB D 15\n"
        "C D 11\nC F 2\nD E 6\nE F 9\n"
    )
    parsed_graph, parsed_source = parse_graph(text)
    dp, _ = dijkstra(parsed_graph, parsed_source)
    check("parsed file matches demo (F=11)", dp["F"] == 11)

    print("")
    print(str(passed) + " passed, " + str(failed) + " failed")
    return failed == 0


# --------------------------------------------------------------------------
# Entry point.
# --------------------------------------------------------------------------

def main(argv):
    verbose = "--verbose" in argv
    args = []
    for item in argv:
        if item != "--verbose":
            args.append(item)

    if "--test" in args:
        ok = run_tests()
        sys.exit(0 if ok else 1)

    # A file path argument: run Dijkstra on that graph.
    file_args = []
    for item in args:
        if not item.startswith("--"):
            file_args.append(item)

    if len(file_args) > 0:
        path = file_args[0]
        handle = open(path, "r")
        text = handle.read()
        handle.close()
        graph, source = parse_graph(text)
        if source is None:
            print("graph file has no edges")
            sys.exit(1)
        report(graph, source, verbose=verbose)
        return

    # No file: if stdin is a terminal, run the REPL; otherwise the demo.
    if sys.stdin.isatty():
        run_demo(verbose=verbose)
        print("")
        repl()
    else:
        run_demo(verbose=verbose)


if __name__ == "__main__":
    main(sys.argv[1:])

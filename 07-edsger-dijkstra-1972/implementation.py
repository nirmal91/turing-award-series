"""
implementation.py — Dijkstra's shortest path algorithm, full working version.

Edsger W. Dijkstra, 1959, "A Note on Two Problems in Connexion with Graphs."
Given a weighted graph, find the shortest distance (and the actual route) from
one source node to every other node.

Before this algorithm, finding a shortest route meant either enumerating paths
(which explodes combinatorially) or ad hoc guessing. Dijkstra's insight was a
greedy rule that settles nodes one at a time in order of distance, and never has
to reconsider a settled node. Each node is finalized exactly once.

This file mirrors the historical algorithm: it keeps tentative distances and
repeatedly settles the closest unsettled node by a linear scan, the way the 1959
note describes it. A comment marks where a binary heap would speed the node
selection up (that is the modern O((V+E) log V) version).

Usage:
    python3 implementation.py                 # demo on a built-in map
    python3 implementation.py graph.txt       # run on a graph you wrote
    python3 implementation.py graph.txt A E   # shortest path from A to E
    python3 implementation.py --test          # test suite (14 cases)
    python3 implementation.py --verbose       # demo, printing every step
    python3 implementation.py graph.txt --verbose

Graph file format (one edge per line, whitespace separated):
    A B 7          # edge between A and B with length 7
    B C 10
    # lines starting with '#' are comments
    directed       # optional: a line with just 'directed' makes edges one-way
                   # (default is undirected: 'A B 7' also adds 'B A 7')
"""

import sys

INFINITY = float("inf")


def add_edge(graph, u, v, length, directed):
    """Add an edge to the adjacency map, creating nodes as needed."""
    if u not in graph:
        graph[u] = []
    if v not in graph:
        graph[v] = []
    graph[u].append((v, length))
    if not directed:
        graph[v].append((u, length))


def parse_graph(text):
    """Turn a graph description into an adjacency map.

    Returns (graph, directed). Each line is 'U V LENGTH', or the bare word
    'directed' to switch off the automatic reverse edge.
    """
    directed = False
    edges = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line == "":
            continue
        if line.startswith("#"):
            continue
        if line == "directed":
            directed = True
            continue
        parts = line.split()
        if len(parts) != 3:
            raise ValueError("bad edge line (need 'U V LENGTH'): " + raw_line)
        u, v, length_text = parts[0], parts[1], parts[2]
        length = float(length_text)
        if length == int(length):
            length = int(length)
        if length < 0:
            raise ValueError("Dijkstra needs non-negative edge lengths: " + raw_line)
        edges.append((u, v, length))

    graph = {}
    for u, v, length in edges:
        add_edge(graph, u, v, length, directed)
    return graph, directed


def dijkstra(graph, source, verbose=False):
    """Compute shortest distances and predecessors from source.

    Returns (distance, previous):
      distance[node]  -> length of the shortest path source..node (inf if none)
      previous[node]  -> the node just before `node` on that path (None if none)
    """
    if source not in graph:
        raise ValueError("source node not in graph: " + str(source))

    distance = {}
    previous = {}
    for node in graph:
        distance[node] = INFINITY
        previous[node] = None
    distance[source] = 0

    settled = set()

    step = 0
    while len(settled) < len(graph):
        # --- Select the unsettled node with the smallest tentative distance. ---
        # A linear scan, exactly as the 1959 note describes. Swapping this for a
        # binary heap (heapq) is what gives the textbook O((V+E) log V) version.
        current = None
        for node in graph:
            if node in settled:
                continue
            if current is None or distance[node] < distance[current]:
                current = node

        # Every remaining node is unreachable from the source. Stop.
        if current is None or distance[current] == INFINITY:
            if verbose:
                print("  remaining nodes are unreachable; stopping")
            break

        settled.add(current)
        step = step + 1

        if verbose:
            print("step " + str(step) + ": settle " + str(current) +
                  " (distance " + str(distance[current]) + ")")

        # --- Relax every edge out of current. ---
        for neighbor, length in graph[current]:
            if neighbor in settled:
                continue
            candidate = distance[current] + length
            if candidate < distance[neighbor]:
                if verbose:
                    old = distance[neighbor]
                    old_text = "inf" if old == INFINITY else str(old)
                    print("    relax " + str(current) + " -> " + str(neighbor) +
                          ": " + old_text + " -> " + str(candidate))
                distance[neighbor] = candidate
                previous[neighbor] = current

        if verbose:
            print("    tentative: " + format_distances(distance))

    return distance, previous


def reconstruct_path(previous, source, target):
    """Walk the predecessor chain backward from target to source."""
    path = []
    node = target
    while node is not None:
        path.append(node)
        if node == source:
            break
        node = previous[node]
    path.reverse()
    if path and path[0] == source:
        return path
    return []  # target unreachable from source


def format_distances(distance):
    """One-line readable dump of the tentative distance table."""
    parts = []
    for node in sorted(distance):
        value = distance[node]
        value_text = "inf" if value == INFINITY else str(value)
        parts.append(str(node) + "=" + value_text)
    return "{ " + ", ".join(parts) + " }"


# The built-in example graph. Distances from A worked out in the README.
DEMO_GRAPH = {
    "A": [("B", 7), ("C", 9), ("F", 14)],
    "B": [("A", 7), ("C", 10), ("D", 15)],
    "C": [("A", 9), ("B", 10), ("D", 11), ("F", 2)],
    "D": [("B", 15), ("C", 11), ("E", 6)],
    "E": [("D", 6), ("F", 9)],
    "F": [("A", 14), ("C", 2), ("E", 9)],
}


def run_demo(verbose=False):
    """The before/after: enumerate-every-route was hopeless; this settles in V steps."""
    print("Dijkstra's shortest path on a 6-city map, source = A")
    print("")
    distance, previous = dijkstra(DEMO_GRAPH, "A", verbose=verbose)
    if verbose:
        print("")
    print("Shortest distances from A:")
    for node in sorted(distance):
        path = reconstruct_path(previous, "A", node)
        route = " -> ".join(path) if path else "(unreachable)"
        print("  A .. " + node + " = " + str(distance[node]) + "   via " + route)


def run_file(path, source=None, target=None, verbose=False):
    """Load a graph from a file and report shortest paths."""
    with open(path) as handle:
        text = handle.read()
    graph, directed = parse_graph(text)
    kind = "directed" if directed else "undirected"
    print("Loaded " + kind + " graph with " + str(len(graph)) + " nodes from " + path)

    if source is None:
        source = sorted(graph)[0]
        print("No source given; using first node: " + source)
    print("")

    distance, previous = dijkstra(graph, source, verbose=verbose)
    if verbose:
        print("")

    if target is not None:
        path = reconstruct_path(previous, source, target)
        if path:
            route = " -> ".join(path)
            print("Shortest path " + source + " -> " + target + " = " +
                  str(distance[target]) + "   via " + route)
        else:
            print("No path from " + source + " to " + target)
        return

    print("Shortest distances from " + source + ":")
    for node in sorted(distance):
        path = reconstruct_path(previous, source, node)
        route = " -> ".join(path) if path else "(unreachable)"
        print("  " + source + " .. " + node + " = " + str(distance[node]) +
              "   via " + route)


# --------------------------------------------------------------------------- #
# Test suite
# --------------------------------------------------------------------------- #

def _graph_from_edges(edges, directed=False):
    graph = {}
    for u, v, length in edges:
        add_edge(graph, u, v, length, directed)
    return graph


def run_tests():
    passed = 0
    failed = 0

    def check(name, got, expected):
        nonlocal passed, failed
        if got == expected:
            passed = passed + 1
            print("  ok   " + name)
        else:
            failed = failed + 1
            print("  FAIL " + name + ": expected " + str(expected) + ", got " + str(got))

    # 1. Single node: distance to itself is zero.
    g = {"A": []}
    dist, _ = dijkstra(g, "A")
    check("single node self distance", dist["A"], 0)

    # 2. Two nodes, one edge.
    g = _graph_from_edges([("A", "B", 5)])
    dist, _ = dijkstra(g, "A")
    check("two nodes direct edge", dist["B"], 5)

    # 3. A shortcut through a middle node beats the direct edge.
    g = _graph_from_edges([("A", "B", 10), ("A", "C", 3), ("C", "B", 4)])
    dist, _ = dijkstra(g, "A")
    check("indirect route is shorter", dist["B"], 7)

    # 4. The classic 6-node demo graph, distance to E.
    dist, _ = dijkstra(DEMO_GRAPH, "A")
    check("demo graph A..E", dist["E"], 20)

    # 5. Same graph, distance to D.
    check("demo graph A..D", dist["D"], 20)

    # 6. Same graph, distance to F (via C).
    check("demo graph A..F", dist["F"], 11)

    # 7. Path reconstruction for A..E.
    _, prev = dijkstra(DEMO_GRAPH, "A")
    check("demo path A..E", reconstruct_path(prev, "A", "E"), ["A", "C", "F", "E"])

    # 8. Unreachable node stays at infinity.
    g = _graph_from_edges([("A", "B", 1), ("C", "D", 1)])
    dist, _ = dijkstra(g, "A")
    check("disconnected component unreachable", dist["D"], INFINITY)

    # 9. Unreachable node has empty reconstructed path.
    _, prev = dijkstra(g, "A")
    check("no path to disconnected node", reconstruct_path(prev, "A", "D"), [])

    # 10. Directed edge is one-way.
    g = _graph_from_edges([("A", "B", 2)], directed=True)
    dist, _ = dijkstra(g, "B")
    check("directed edge is one-way", dist["A"], INFINITY)

    # 11. A tie between two equal-length routes still gives the right distance.
    g = _graph_from_edges([("A", "B", 1), ("A", "C", 1), ("B", "D", 1), ("C", "D", 1)])
    dist, _ = dijkstra(g, "A")
    check("equal-length routes tie", dist["D"], 2)

    # 12. Zero-length edges are allowed.
    g = _graph_from_edges([("A", "B", 0), ("B", "C", 0)])
    dist, _ = dijkstra(g, "A")
    check("zero-length edges", dist["C"], 0)

    # 13. Parser builds a working undirected graph.
    graph, directed = parse_graph("A B 4\nB C 6\n")
    dist, _ = dijkstra(graph, "A")
    check("parsed graph A..C", dist["C"], 10)
    check("parsed graph is undirected", directed, False)

    # 14. Negative edge is rejected (Dijkstra's assumption).
    rejected = False
    try:
        parse_graph("A B -3\n")
    except ValueError:
        rejected = True
    check("negative edge rejected", rejected, True)

    print("")
    print(str(passed) + " passed, " + str(failed) + " failed")
    return failed == 0


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def main(argv):
    args = list(argv)
    verbose = False
    if "--verbose" in args:
        verbose = True
        args.remove("--verbose")

    if "--test" in args:
        ok = run_tests()
        sys.exit(0 if ok else 1)

    # Remaining positional args: [graph_file] [source] [target]
    positional = []
    for arg in args:
        positional.append(arg)

    if len(positional) == 0:
        run_demo(verbose=verbose)
        return

    path = positional[0]
    source = positional[1] if len(positional) > 1 else None
    target = positional[2] if len(positional) > 2 else None
    run_file(path, source=source, target=target, verbose=verbose)


if __name__ == "__main__":
    main(sys.argv[1:])

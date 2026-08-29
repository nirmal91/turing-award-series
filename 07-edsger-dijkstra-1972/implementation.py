"""
Dijkstra's shortest path algorithm — full working implementation.

Based on Edsger Dijkstra's "A Note on Two Problems in Connexion with
Graphs" (Numerische Mathematik, 1959). Dijkstra worked the algorithm out
in about twenty minutes in a cafe in Amsterdam in 1956, with no pencil or
paper, to demonstrate a new computer (the ARMAC) to a general audience:
find the shortest driving route between two Dutch cities. He deliberately
kept it simple so it stayed easy to explain and provably correct.

BEFORE Dijkstra: finding the shortest route between two points meant
checking every possible path between them, a number that grows
exponentially with the size of the map. Even a modest road network made
this hopeless to do by hand, and expensive to do on the machines of 1959.

AFTER Dijkstra: grow a set of nodes whose shortest distance from the
start is known for certain, one at a time. Always claim the closest
unclaimed node next, and use it to try to shorten its neighbors'
distances. Every node is visited once. With a priority queue this runs in
O((V + E) log V) instead of checking every path.

Pipeline:
    graph (adjacency list)
        -> priority queue seeded with the start node at distance 0
        -> pop the closest unvisited node          (it is now FINAL)
        -> relax its neighbors                     (maybe shorten them)
        -> repeat until the queue is empty
        -> distances{} and previous{} (previous[] lets you rebuild the path)

Run:
    python3 implementation.py                    # interactive REPL
    python3 implementation.py netherlands.graph   # load and run a graph file
    python3 implementation.py --test              # self-test suite (16 cases)
    python3 implementation.py --verbose            # REPL that prints every step
"""

import sys
import heapq


INF = float("inf")


# ── Graph ────────────────────────────────────────────────────────────────────
#
# A weighted graph as an adjacency list: node -> [(neighbor, weight), ...].
# Nodes can be any comparable, hashable value (strings, in every example
# here). Edges are undirected by default (a road you can drive both ways);
# pass directed=True for a one-way edge.

class Graph:
    def __init__(self):
        self.adjacency = {}

    def add_node(self, node):
        if node not in self.adjacency:
            self.adjacency[node] = []

    def add_edge(self, a, b, weight, directed=False):
        if weight < 0:
            # Dijkstra's algorithm assumes a settled node's distance can
            # never improve later. A negative edge breaks that assumption —
            # you'd need Bellman-Ford instead. See the README for why.
            raise ValueError("Dijkstra's algorithm requires non-negative edge weights")
        self.add_node(a)
        self.add_node(b)
        self.adjacency[a].append((b, weight))
        if not directed:
            self.adjacency[b].append((a, weight))

    def nodes(self):
        return list(self.adjacency)


# ── The algorithm ────────────────────────────────────────────────────────────

VERBOSE = False


def dijkstra(graph, start):
    """Return (distances, previous): the shortest distance from start to
    every reachable node, and the node you arrive from on that shortest
    path (so the path can be rebuilt by walking previous[] backwards)."""
    if start not in graph.adjacency:
        raise KeyError("unknown start node: " + repr(start))

    distances = {node: INF for node in graph.nodes()}
    previous = {node: None for node in graph.nodes()}
    distances[start] = 0

    # A node can be pushed onto the heap more than once, if we later find a
    # cheaper way to reach it. `settled` tracks which nodes are already
    # final, so we can ignore their stale, larger heap entries.
    heap = [(0, start)]
    settled = set()

    if VERBOSE:
        print("  start: %s" % start)

    while heap:
        dist, node = heapq.heappop(heap)

        if node in settled:
            if VERBOSE:
                print("  pop %-12s dist=%-6s already settled, skip" % (node, dist))
            continue

        settled.add(node)
        if VERBOSE:
            print("  pop %-12s dist=%-6s  <- FINAL" % (node, dist))

        for neighbor, weight in graph.adjacency[node]:
            if neighbor in settled:
                continue
            new_dist = dist + weight
            if new_dist < distances[neighbor]:
                if VERBOSE:
                    old = distances[neighbor]
                    old_str = "inf" if old == INF else str(old)
                    print("    relax %-10s via %-10s: %s -> %s" %
                          (neighbor, node, old_str, new_dist))
                distances[neighbor] = new_dist
                previous[neighbor] = node
                heapq.heappush(heap, (new_dist, neighbor))

    return distances, previous


def reconstruct_path(previous, start, end):
    """Walk the previous[] chain backwards from end to start. Returns None
    if end is unreachable from start."""
    if end not in previous:
        raise KeyError("unknown node: " + repr(end))
    if end != start and previous[end] is None:
        return None

    path = [end]
    while path[-1] != start:
        node = previous[path[-1]]
        if node is None:
            return None
        path.append(node)
    path.reverse()
    return path


def brute_force_shortest(graph, start, end):
    """Try every simple path (no revisited nodes) by hand and return the
    cheapest total. Only used to check dijkstra() against something
    independent — this brute-force search over every path is exactly what
    Dijkstra's insight lets you avoid."""
    best = [INF]

    def visit(node, visited, cost):
        if cost >= best[0]:
            return  # already worse than the best found; no point continuing
        if node == end:
            best[0] = cost
            return
        for neighbor, weight in graph.adjacency[node]:
            if neighbor not in visited:
                visit(neighbor, visited | {neighbor}, cost + weight)

    visit(start, {start}, 0)
    return best[0]


# ── The demo graph: Dijkstra's 1959 example, shrunk to six cities ───────────

def netherlands_demo():
    """The road network from Dijkstra's actual 1959 demo, shrunk from 64
    Dutch cities down to six. Distances are driving km, rounded."""
    graph = Graph()
    graph.add_edge("Rotterdam", "Utrecht", 60)
    graph.add_edge("Rotterdam", "Amsterdam", 85)
    graph.add_edge("Utrecht", "Amsterdam", 40)
    graph.add_edge("Utrecht", "Amersfoort", 25)
    graph.add_edge("Amsterdam", "Amersfoort", 45)
    graph.add_edge("Amersfoort", "Zwolle", 50)
    graph.add_edge("Amsterdam", "Zwolle", 110)
    graph.add_edge("Zwolle", "Groningen", 100)
    return graph


# ── Loading a graph from a file ──────────────────────────────────────────────
#
# File format (see netherlands.graph):
#   A B 10        undirected edge A-B, weight 10
#   A -> B 10     directed edge, A to B only, weight 10
#   START A       which node the report is computed from
#   END B         (optional) also print the specific path A -> B
#   # a comment, ignored, blank lines ignored

def parse_graph_file(path):
    graph = Graph()
    start = None
    end = None
    with open(path) as source_file:
        for raw_line in source_file:
            line = raw_line.split("#")[0].strip()
            if not line:
                continue
            parts = line.split()
            if parts[0] == "START":
                start = parts[1]
            elif parts[0] == "END":
                end = parts[1]
            elif "->" in parts:
                a, _arrow, b, weight = parts
                graph.add_edge(a, b, float(weight), directed=True)
            else:
                a, b, weight = parts
                graph.add_edge(a, b, float(weight))
    return graph, start, end


def run_file(path):
    graph, start, end = parse_graph_file(path)
    if start is None:
        start = graph.nodes()[0]

    distances, previous = dijkstra(graph, start)

    print("Shortest distances from %s:" % start)
    for node in sorted(graph.nodes()):
        dist = distances[node]
        dist_str = "unreachable" if dist == INF else str(dist)
        print("  %-12s %s" % (node, dist_str))

    if end is not None:
        path = reconstruct_path(previous, start, end)
        if path is None:
            print("\nNo path from %s to %s" % (start, end))
        else:
            print("\nShortest path %s -> %s: %s  (total %s)" %
                  (start, end, " -> ".join(path), distances[end]))


# ── REPL ─────────────────────────────────────────────────────────────────────

BANNER = """Dijkstra's shortest path algorithm (1959).
Build a graph, then ask it for shortest paths.

Commands:
  edge A B 10        add an undirected edge A-B with weight 10
  edge A -> B 10     add a directed edge A to B with weight 10
  dist A             shortest distance from A to every other node
  path A B           shortest path and total distance from A to B
  show               list every edge currently in the graph
  demo               load Dijkstra's own example: six Dutch cities
  quit               leave
"""


def repl():
    graph = Graph()
    print(BANNER)
    while True:
        try:
            line = input("dijkstra> ").strip()
        except EOFError:
            print()
            return
        if not line:
            continue
        if line in ("quit", "exit", "q"):
            return

        parts = line.split()
        try:
            if parts[0] == "edge" and "->" in parts:
                _, a, _arrow, b, weight = parts
                graph.add_edge(a, b, float(weight), directed=True)
                print("  added %s -> %s (%s)" % (a, b, weight))
            elif parts[0] == "edge":
                _, a, b, weight = parts
                graph.add_edge(a, b, float(weight))
                print("  added %s - %s (%s)" % (a, b, weight))
            elif parts[0] == "dist":
                _, a = parts
                distances, _ = dijkstra(graph, a)
                for node in sorted(distances):
                    dist = distances[node]
                    print("  %-12s %s" % (node, "unreachable" if dist == INF else dist))
            elif parts[0] == "path":
                _, a, b = parts
                distances, previous = dijkstra(graph, a)
                path = reconstruct_path(previous, a, b)
                if path is None:
                    print("  no path from %s to %s" % (a, b))
                else:
                    print("  %s  (total %s)" % (" -> ".join(path), distances[b]))
            elif parts[0] == "show":
                for node in sorted(graph.nodes()):
                    for neighbor, weight in graph.adjacency[node]:
                        print("  %s -> %s (%s)" % (node, neighbor, weight))
            elif parts[0] == "demo":
                graph = netherlands_demo()
                print("  loaded: Rotterdam, Utrecht, Amsterdam, Amersfoort, Zwolle, Groningen")
            else:
                print("  unknown command, see the banner above")
        except (ValueError, KeyError, IndexError) as err:
            print("  error: %s" % err)


# ── Self-test suite ──────────────────────────────────────────────────────────

def run_tests():
    passed = 0
    failed = 0

    def check(name, got, expected):
        nonlocal passed, failed
        if got == expected:
            print("  PASS  %s" % name)
            passed += 1
        else:
            print("  FAIL  %s: got %r, expected %r" % (name, got, expected))
            failed += 1

    # 1. Single edge: distance is just the weight.
    g = Graph()
    g.add_edge("A", "B", 10)
    distances, _ = dijkstra(g, "A")
    check("single edge A-B=10", distances["B"], 10)

    # 2. Three-node line: distances add up.
    g = Graph()
    g.add_edge("A", "B", 5)
    g.add_edge("B", "C", 7)
    distances, _ = dijkstra(g, "A")
    check("chain A-B-C adds up", distances["C"], 12)

    # 3. The core property: a cheaper multi-hop route beats a pricier direct edge.
    g = Graph()
    g.add_edge("A", "B", 10)   # direct, expensive
    g.add_edge("A", "C", 1)
    g.add_edge("C", "B", 2)    # A -> C -> B is cheaper
    distances, previous = dijkstra(g, "A")
    check("multi-hop beats direct edge", distances["B"], 3)
    check("path goes through C", reconstruct_path(previous, "A", "B"), ["A", "C", "B"])

    # 4. Unreachable node stays at infinity.
    g = Graph()
    g.add_edge("A", "B", 1)
    g.add_node("Z")   # isolated, no edges
    distances, previous = dijkstra(g, "A")
    check("unreachable node is INF", distances["Z"], INF)
    check("no path to unreachable node", reconstruct_path(previous, "A", "Z"), None)

    # 5. Disconnected graph: a whole other component is unreachable.
    g = Graph()
    g.add_edge("A", "B", 1)
    g.add_edge("X", "Y", 1)   # separate component
    distances, _ = dijkstra(g, "A")
    check("other component is unreachable", distances["X"], INF)

    # 6. A single-node graph: distance to yourself is 0.
    g = Graph()
    g.add_node("A")
    distances, previous = dijkstra(g, "A")
    check("distance to self is 0", distances["A"], 0)
    check("path to self is just [self]", reconstruct_path(previous, "A", "A"), ["A"])

    # 7. A self-loop doesn't break anything or shorten the distance to itself.
    g = Graph()
    g.add_edge("A", "A", 5)
    g.add_edge("A", "B", 3)
    distances, _ = dijkstra(g, "A")
    check("self-loop leaves self-distance at 0", distances["A"], 0)
    check("self-loop doesn't disturb other distances", distances["B"], 3)

    # 8. Directed edges only work one way.
    g = Graph()
    g.add_edge("A", "B", 1, directed=True)
    distances, _ = dijkstra(g, "B")
    check("directed edge is one-way", distances["A"], INF)
    distances, _ = dijkstra(g, "A")
    check("directed edge works forwards", distances["B"], 1)

    # 9. Negative weights are rejected outright.
    g = Graph()
    try:
        g.add_edge("A", "B", -5)
        check("negative weight raises", False, True)
    except ValueError:
        check("negative weight raises", True, True)

    # 10. A zero-weight edge is fine and free.
    g = Graph()
    g.add_edge("A", "B", 0)
    g.add_edge("B", "C", 4)
    distances, _ = dijkstra(g, "A")
    check("zero-weight edge costs nothing", distances["C"], 4)

    # 11. Querying an unknown start node fails loudly.
    g = Graph()
    g.add_edge("A", "B", 1)
    try:
        dijkstra(g, "Nowhere")
        check("unknown start raises KeyError", False, True)
    except KeyError:
        check("unknown start raises KeyError", True, True)

    # 12. reconstruct_path on an unknown node fails loudly too.
    g = Graph()
    g.add_edge("A", "B", 1)
    _, previous = dijkstra(g, "A")
    try:
        reconstruct_path(previous, "A", "Nowhere")
        check("unknown end raises KeyError", False, True)
    except KeyError:
        check("unknown end raises KeyError", True, True)

    # 13. The full six-city demo matches the hand-worked example in the README:
    #     Rotterdam -> Utrecht -> Amersfoort -> Zwolle -> Groningen, total 235.
    graph = netherlands_demo()
    distances, previous = dijkstra(graph, "Rotterdam")
    check("Netherlands demo: distance to Groningen", distances["Groningen"], 235)
    check("Netherlands demo: path to Groningen",
          reconstruct_path(previous, "Rotterdam", "Groningen"),
          ["Rotterdam", "Utrecht", "Amersfoort", "Zwolle", "Groningen"])

    # 14. Cross-check dijkstra() against an independent brute-force search
    #     over every simple path, on the same demo graph.
    check("brute-force agrees with dijkstra (Rotterdam -> Groningen)",
          brute_force_shortest(graph, "Rotterdam", "Groningen"), 235)
    check("brute-force agrees with dijkstra (Rotterdam -> Amersfoort)",
          brute_force_shortest(graph, "Rotterdam", "Amersfoort"), distances["Amersfoort"])

    total = passed + failed
    print()
    print("%d/%d passed" % (passed, total))
    return failed == 0


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    global VERBOSE
    args = sys.argv[1:]
    if "--test" in args:
        ok = run_tests()
        sys.exit(0 if ok else 1)
    if "--verbose" in args:
        VERBOSE = True
        print("(verbose mode: every pop and relax is printed)\n")
    files = [a for a in args if not a.startswith("--")]
    if len(files) > 0:
        run_file(files[0])
        return
    repl()


if __name__ == "__main__":
    main()

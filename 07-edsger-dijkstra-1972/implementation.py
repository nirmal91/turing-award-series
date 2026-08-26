"""
Dijkstra's shortest path algorithm (Edsger W. Dijkstra, 1959) — full version.

"A note on two problems in connexion with graphs," Numerische Mathematik, 1959.
Dijkstra said he designed it in about twenty minutes, without pencil or paper,
while having coffee with his fiancee in Amsterdam. He wanted to demonstrate
the new ARMAC computer with something that would impress a general audience,
so he picked a problem anyone could state: the 64 cities of the Netherlands,
what is the shortest road route between two of them?

Before this, the honest answer was to enumerate: list candidate routes, add
up their lengths, keep the shortest one you have seen. There was no way to
know when to stop looking, and no bound on how many routes there could be.

Dijkstra's algorithm never looks at a full route. It grows outward from the
start node one node at a time, always finishing the nearest unfinished node
next, and once a node is finished its distance is locked in for good. This
file is a working version of that idea: build a graph, load one from a file,
watch it run step by step, and see why "finished" really does mean finished.
"""

import sys

INF = float("inf")

VERBOSE = False


# ── The graph ─────────────────────────────────────────────────────────────────

class Graph:
    def __init__(self):
        self.adjacency = {}   # node -> {neighbor: weight, ...}

    def add_node(self, node):
        if node not in self.adjacency:
            self.adjacency[node] = {}

    def add_edge(self, a, b, weight, directed=False):
        self.add_node(a)
        self.add_node(b)
        self.adjacency[a][b] = weight
        if not directed:
            self.adjacency[b][a] = weight

    def nodes(self):
        return list(self.adjacency.keys())

    def neighbors(self, node):
        return self.adjacency.get(node, {})


# ── The algorithm ────────────────────────────────────────────────────────────

def dijkstra(graph, start, verbose=False):
    """
    Returns (distance, previous).
    distance[node]  = shortest known length from start to node
    previous[node]  = the node you step back to on the shortest path to node
    """
    if start not in graph.adjacency:
        raise ValueError("start node %r is not in the graph" % start)

    distance = {}
    for node in graph.nodes():
        distance[node] = INF
    distance[start] = 0

    previous = {}
    unfinished = set(graph.nodes())

    step = 0
    while unfinished:
        step += 1

        # Step 1: pick the unfinished node nearest to start.
        current = None
        current_distance = INF
        for node in unfinished:
            if distance[node] < current_distance:
                current = node
                current_distance = distance[node]

        if current is None:
            if verbose:
                print("  step %d: %d node(s) left, all unreachable — stopping" %
                      (step, len(unfinished)))
            break

        unfinished.remove(current)

        if verbose:
            print("  step %d: finish %s (distance %s)" % (step, current, current_distance))

        # Step 2: relax current's edges — see if going through current
        # beats the best known way to reach each neighbor.
        for neighbor, weight in graph.neighbors(current).items():
            if neighbor not in unfinished:
                continue  # already finished, and finished distances never improve
            candidate = distance[current] + weight
            if candidate < distance[neighbor]:
                old = distance[neighbor]
                distance[neighbor] = candidate
                previous[neighbor] = current
                if verbose:
                    old_str = "inf" if old == INF else str(old)
                    print("      relax %s -> %s: %s beats %s, via %s" %
                          (current, neighbor, candidate, old_str, current))

        if verbose:
            snapshot = ", ".join("%s=%s" % (n, "inf" if distance[n] == INF else distance[n])
                                  for n in sorted(distance))
            print("      distances now: %s" % snapshot)

    return distance, previous


def path_to(previous, start, target):
    if target == start:
        return [start]
    if target not in previous:
        return None
    path = [target]
    while path[-1] != start:
        if path[-1] not in previous:
            return None
        path.append(previous[path[-1]])
    path.reverse()
    return path


def format_distance(value):
    return "unreachable" if value == INF else str(value)


# ── Loading a graph from a file ─────────────────────────────────────────────
#
# File format, one directive per line:
#   A B 4        directed edge A -> B, weight 4
#   A B 4 both   edge A <-> B in both directions, weight 4
#   START A      which node to treat as the source (optional, default: first node seen)
#   # comment    ignored

def parse_graph_file(path):
    graph = Graph()
    start = None
    with open(path) as handle:
        for raw_line in handle:
            line = raw_line.split("#", 1)[0].strip()
            if line == "":
                continue
            parts = line.split()
            if parts[0] == "START":
                start = parts[1]
                continue
            a, b, weight = parts[0], parts[1], float(parts[2])
            if weight == int(weight):
                weight = int(weight)
            directed = not (len(parts) >= 4 and parts[3] == "both")
            graph.add_edge(a, b, weight, directed=directed)
    if start is None and graph.nodes():
        start = graph.nodes()[0]
    return graph, start


def run_file(path):
    graph, start = parse_graph_file(path)
    print("loaded %d nodes from %s" % (len(graph.nodes()), path))
    if start is None:
        print("graph is empty, nothing to do")
        return
    print("source node: %s\n" % start)
    distance, previous = dijkstra(graph, start, verbose=VERBOSE)
    print("shortest distance from %s to every node:" % start)
    for node in sorted(distance):
        print("  %s -> %s: %s" % (start, node, format_distance(distance[node])))
        if distance[node] != INF and node != start:
            route = path_to(previous, start, node)
            print("      route: %s" % " -> ".join(route))


# ── Interactive REPL ─────────────────────────────────────────────────────────

BANNER = """Dijkstra's shortest path algorithm (1959).
Build a graph, then ask for the shortest path.
  edge A B 4        add a directed edge A -> B with weight 4
  edge A B 4 both    add it in both directions
  path A B          shortest path from A to B
  table A           shortest distance from A to every node
  show              print the graph
  verbose           toggle step-by-step output
  load FILE         load a graph from a file
  help              show this message again
Type Ctrl-D to quit."""


def repl():
    global VERBOSE
    graph = Graph()
    print(BANNER)
    while True:
        try:
            line = input("graph> ")
        except EOFError:
            print()
            return
        line = line.strip()
        if line == "":
            continue
        parts = line.split()
        command = parts[0]

        try:
            if command == "help":
                print(BANNER)
            elif command == "edge":
                a, b, weight = parts[1], parts[2], float(parts[3])
                if weight == int(weight):
                    weight = int(weight)
                directed = not (len(parts) >= 5 and parts[4] == "both")
                graph.add_edge(a, b, weight, directed=directed)
                print("added %s -> %s (%s)%s" %
                      (a, b, weight, "" if directed else ", and back"))
            elif command == "show":
                if not graph.nodes():
                    print("(empty graph)")
                for node in sorted(graph.nodes()):
                    edges = graph.neighbors(node)
                    if edges:
                        edge_str = ", ".join("%s(%s)" % (n, w) for n, w in edges.items())
                        print("  %s -> %s" % (node, edge_str))
                    else:
                        print("  %s -> (no outgoing edges)" % node)
            elif command == "path":
                a, b = parts[1], parts[2]
                distance, previous = dijkstra(graph, a, verbose=VERBOSE)
                if distance.get(b, INF) == INF:
                    print("no path from %s to %s" % (a, b))
                else:
                    route = path_to(previous, a, b)
                    print("distance: %s" % format_distance(distance[b]))
                    print("route:    %s" % " -> ".join(route))
            elif command == "table":
                a = parts[1]
                distance, previous = dijkstra(graph, a, verbose=VERBOSE)
                for node in sorted(distance):
                    print("  %s -> %s: %s" % (a, node, format_distance(distance[node])))
            elif command == "load":
                graph, start = parse_graph_file(parts[1])
                print("loaded %d nodes; try: table %s" % (len(graph.nodes()), start))
            elif command == "verbose":
                VERBOSE = not VERBOSE
                print("verbose mode: %s" % ("on" if VERBOSE else "off"))
            else:
                print("unknown command: %s (try 'help')" % command)
        except (IndexError, ValueError, KeyError) as err:
            print("error: %s" % err)


# ── Self-test suite ──────────────────────────────────────────────────────────

def run_tests():
    passed = 0
    total = 0

    def check(description, actual, expected):
        nonlocal passed, total
        total += 1
        ok = actual == expected
        if ok:
            passed += 1
        mark = "PASS" if ok else "FAIL"
        print("[%s] %-55s -> %s" % (mark, description, actual))
        if not ok:
            print("        expected %s" % (expected,))

    # 1. The napkin example from concept.py, by hand: A-C-B-D-E is the cheap route.
    roads = Graph()
    roads.add_edge("A", "B", 4, directed=True)
    roads.add_edge("A", "C", 2, directed=True)
    roads.add_edge("B", "D", 5, directed=True)
    roads.add_edge("C", "B", 1, directed=True)
    roads.add_edge("C", "D", 8, directed=True)
    roads.add_edge("C", "E", 10, directed=True)
    roads.add_edge("D", "E", 2, directed=True)
    distance, previous = dijkstra(roads, "A")
    check("A to E total distance", distance["E"], 10)
    check("A to E route goes through C, B, D", path_to(previous, "A", "E"), ["A", "C", "B", "D", "E"])
    check("A to B is 3 via C, not 4 direct", distance["B"], 3)
    check("A to A is 0", distance["A"], 0)

    # 2. A single isolated node has distance 0 to itself and nowhere else to go.
    lonely = Graph()
    lonely.add_node("X")
    d, p = dijkstra(lonely, "X")
    check("single node distance to itself", d["X"], 0)
    check("single node has no other entries", list(d.keys()), ["X"])

    # 3. An unreachable node stays at infinity, and its path is None.
    split = Graph()
    split.add_edge("A", "B", 1, directed=True)
    split.add_node("Z")   # not connected to anything
    d, p = dijkstra(split, "A")
    check("unreachable node stays at infinity", d["Z"], INF)
    check("unreachable node has no path", path_to(p, "A", "Z"), None)

    # 4. Two routes tie in length; the algorithm still finds the correct value.
    tie = Graph()
    tie.add_edge("A", "B", 2, directed=True)
    tie.add_edge("A", "C", 2, directed=True)
    tie.add_edge("B", "D", 2, directed=True)
    tie.add_edge("C", "D", 2, directed=True)
    d, p = dijkstra(tie, "A")
    check("tied routes both give the same shortest distance", d["D"], 4)

    # 5. A direct edge is not always the shortest: a detour through C beats it.
    detour = Graph()
    detour.add_edge("A", "D", 100, directed=True)
    detour.add_edge("A", "C", 1, directed=True)
    detour.add_edge("C", "D", 1, directed=True)
    d, p = dijkstra(detour, "A")
    check("cheap detour beats an expensive direct edge", d["D"], 2)
    check("route uses the detour", path_to(p, "A", "D"), ["A", "C", "D"])

    # 6. Undirected edges (both directions) work the same from either end.
    both_ways = Graph()
    both_ways.add_edge("A", "B", 5, directed=False)
    d1, _ = dijkstra(both_ways, "A")
    d2, _ = dijkstra(both_ways, "B")
    check("undirected edge A->B distance", d1["B"], 5)
    check("undirected edge B->A distance", d2["A"], 5)

    # 7. A directed-only edge cannot be walked backwards.
    one_way = Graph()
    one_way.add_edge("A", "B", 1, directed=True)
    d, p = dijkstra(one_way, "B")
    check("directed edge cannot be walked backwards", d["A"], INF)

    # 8. The file loader parses edges, a START directive, and skips comments.
    import tempfile
    import os
    fd, path = tempfile.mkstemp(suffix=".graph")
    with os.fdopen(fd, "w") as handle:
        handle.write("# a tiny file graph\n")
        handle.write("A B 3\n")
        handle.write("B C 4 both\n")
        handle.write("START A\n")
    file_graph, start = parse_graph_file(path)
    os.remove(path)
    check("file loader reads the START directive", start, "A")
    d, p = dijkstra(file_graph, start)
    check("file loader builds working edges", d["C"], 7)

    print()
    print("%d/%d passed" % (passed, total))
    return passed == total


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    global VERBOSE
    args = sys.argv[1:]
    if "--test" in args:
        ok = run_tests()
        sys.exit(0 if ok else 1)
    if "--verbose" in args:
        VERBOSE = True
        print("(verbose mode: every step of the algorithm is printed)\n")
    files = [a for a in args if not a.startswith("--")]
    if len(files) > 0:
        run_file(files[0])
        return
    repl()


if __name__ == "__main__":
    main()

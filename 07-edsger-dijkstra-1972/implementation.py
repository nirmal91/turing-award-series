"""
Dijkstra's shortest-path algorithm, built the way E. W. Dijkstra described it
in his 1959 paper "A Note on Two Problems in Connexion with Graphs."

BEFORE this algorithm: finding the shortest route between two points meant
enumerating paths — walking every route through the network and comparing
their total lengths — and the number of simple paths through a graph explodes
combinatorially as the graph grows. brute_force_shortest_path() below does
exactly that, so you can watch it agree with Dijkstra on small graphs and
then imagine it on a real road network.

AFTER this algorithm: you never build or compare a single whole path. Every
node carries a running "label" (best distance found so far). You repeatedly
take the not-yet-finished node with the smallest label, make it permanent, and
use it to relax (try to shrink) its neighbors' labels. One pass over the
graph, and every label is the true shortest distance. This file mirrors that
two-pile (tentative / permanent) description exactly, including the linear
scan for the minimum label — Dijkstra did not use a priority queue; a min-heap
came decades later as a performance optimization, not a change to the idea.

Pipeline:
    graph edges (add A B 4)
        -> shortest_paths()   tentative labels -> permanent labels, one at a time
        -> path_to()          walk the parent pointers back into a route
        -> printed result

Run:
    python3 implementation.py               # interactive REPL
    python3 implementation.py practice.graph # load and run a graph script
    python3 implementation.py --test         # self-test suite
    python3 implementation.py --verbose      # REPL that prints every label update
"""

import sys

INFINITY = float("inf")
VERBOSE = False


# ── The graph ─────────────────────────────────────────────────────────────────
#
# A graph is just a dict: node -> list of (neighbor, weight) edges. Directed,
# because that is the general case; an undirected edge is two directed ones.

class Graph:
    def __init__(self):
        self.edges = {}

    def add_node(self, node):
        if node not in self.edges:
            self.edges[node] = []

    def add_edge(self, a, b, weight):
        self.add_node(a)
        self.add_node(b)
        self.edges[a].append((b, weight))

    def nodes(self):
        return list(self.edges.keys())


# ── Dijkstra's algorithm ─────────────────────────────────────────────────────

def shortest_paths(graph, source):
    """Compute the shortest distance from source to every other node.

    Every node gets a tentative label, starting at infinity except the
    source, which starts at 0. The algorithm repeatedly:
      1. picks the tentative node with the smallest label,
      2. moves it to the permanent pile (its label is now final), and
      3. relaxes its neighbors: if going through this node gives a shorter
         path to a neighbor than that neighbor's current label, update it.

    Because step 1 always picks the smallest remaining tentative label, and
    weights are assumed non-negative, no later relaxation can ever beat an
    already-permanent label. That is the entire correctness argument.

    Returns (dist, prev): dist[node] is the shortest distance from source,
    prev[node] is the node just before it on that shortest path (used to
    reconstruct the route in path_to()).
    """
    dist = {}
    prev = {}
    for node in graph.nodes():
        dist[node] = INFINITY
        prev[node] = None
    dist[source] = 0

    tentative = set(graph.nodes())
    permanent = set()

    step = 0
    while len(tentative) > 0:
        step += 1

        # The linear scan for the minimum. This is what makes the original
        # algorithm O(V^2): every step scans every remaining tentative node.
        # A min-heap (Fibonacci or binary) later turned this into O(E log V),
        # but that is a data-structure speedup, not a different algorithm.
        current = None
        for node in tentative:
            if current is None or dist[node] < dist[current]:
                current = node

        if dist[current] == INFINITY:
            if VERBOSE:
                print("  step %d: %s remaining node(s) unreachable from %s, stopping"
                      % (step, len(tentative), source))
            break

        tentative.remove(current)
        permanent.add(current)

        if VERBOSE:
            print("  step %d: finalize %s at distance %s" % (step, current, dist[current]))

        for neighbor, weight in graph.edges[current]:
            if neighbor in permanent:
                continue
            candidate = dist[current] + weight
            if candidate < dist[neighbor]:
                old = dist[neighbor]
                dist[neighbor] = candidate
                prev[neighbor] = current
                if VERBOSE:
                    old_str = "inf" if old == INFINITY else str(old)
                    print("      relax %s -> %s: %s -> %s (via %s)"
                          % (current, neighbor, old_str, candidate, current))

    return dist, prev


def path_to(prev, source, target):
    """Walk the parent pointers backward from target to source. Returns the
    route as a list of nodes, or None if target is unreachable."""
    if target not in prev:
        return None
    if prev[target] is None and target != source:
        return None
    path = [target]
    node = target
    while node != source:
        node = prev[node]
        if node is None:
            return None
        path.append(node)
    path.reverse()
    return path


# ── Before: brute-force enumeration ─────────────────────────────────────────

def brute_force_shortest_path(graph, source, target, visited=None):
    """What you had to do before Dijkstra: try every simple path from source
    to target and keep the shortest. Correct, but the number of simple paths
    grows combinatorially with the graph, so this is only here to check
    Dijkstra's answer on small graphs -- not to use on a real one."""
    if visited is None:
        visited = frozenset()
    if source == target:
        return [source], 0
    visited = visited | {source}
    best_path = None
    best_length = INFINITY
    for neighbor, weight in graph.edges.get(source, []):
        if neighbor in visited:
            continue
        sub = brute_force_shortest_path(graph, neighbor, target, visited)
        if sub is None:
            continue
        sub_path, sub_length = sub
        total = weight + sub_length
        if total < best_length:
            best_length = total
            best_path = [source] + sub_path
    if best_path is None:
        return None
    return best_path, best_length


# ── REPL / graph-script commands ────────────────────────────────────────────

BANNER = """Dijkstra's shortest-path algorithm (E. W. Dijkstra, 1959).
Commands:
  add A B 4        add a directed edge A -> B with weight 4
  show             print every edge in the graph
  run A            compute shortest distances from A to every node
  path A B         print the shortest route from A to B
  brute A B        compare against brute-force path enumeration (the "before")
  help             show this again
Ctrl-D to quit."""


def format_dist(d):
    return "inf" if d == INFINITY else str(d)


def format_weight(raw):
    w = float(raw)
    return int(w) if w == int(w) else w


def do_command(line, graph):
    parts = line.split()
    if len(parts) == 0:
        return
    cmd = parts[0]

    if cmd == "add" and len(parts) == 4:
        a, b = parts[1], parts[2]
        weight = format_weight(parts[3])
        graph.add_edge(a, b, weight)
        print("added %s -> %s (%s)" % (a, b, weight))

    elif cmd == "show":
        if len(graph.nodes()) == 0:
            print("  (empty graph)")
        for node in graph.nodes():
            for neighbor, weight in graph.edges[node]:
                print("  %s -> %s (%s)" % (node, neighbor, weight))

    elif cmd == "run" and len(parts) == 2:
        source = parts[1]
        if source not in graph.edges:
            print("unknown node: %s" % source)
            return
        dist, prev = shortest_paths(graph, source)
        for node in sorted(graph.nodes()):
            print("  %s: %s" % (node, format_dist(dist[node])))

    elif cmd == "path" and len(parts) == 3:
        source, target = parts[1], parts[2]
        if source not in graph.edges:
            print("unknown node: %s" % source)
            return
        dist, prev = shortest_paths(graph, source)
        route = path_to(prev, source, target)
        if route is None:
            print("no path from %s to %s" % (source, target))
        else:
            print("  " + " -> ".join(route) + "   (distance %s)" % format_dist(dist[target]))

    elif cmd == "brute" and len(parts) == 3:
        source, target = parts[1], parts[2]
        dist, prev = shortest_paths(graph, source)
        dijkstra_route = path_to(prev, source, target)
        result = brute_force_shortest_path(graph, source, target)
        if result is None:
            print("  brute force: no path")
        else:
            route, length = result
            print("  brute force: " + " -> ".join(route) + "   (distance %s)" % length)
        if dijkstra_route is None:
            print("  dijkstra:    no path")
        else:
            print("  dijkstra:    " + " -> ".join(dijkstra_route)
                  + "   (distance %s)" % format_dist(dist[target]))

    elif cmd == "help":
        print(BANNER)

    else:
        print("unknown command: %s (try 'help')" % line)


def repl():
    graph = Graph()
    print(BANNER)
    while True:
        try:
            line = input("dijkstra> ")
        except EOFError:
            print()
            return
        if line.strip() == "":
            continue
        try:
            do_command(line.strip(), graph)
        except (ValueError, KeyError) as err:
            print("error: %s" % err)


def run_file(path):
    """Load and run a graph script: one command per line, '#' starts a
    comment. Each command is echoed before it runs, the same as typing it
    into the REPL by hand."""
    graph = Graph()
    with open(path) as source_file:
        lines = source_file.readlines()
    for raw_line in lines:
        line = raw_line.split("#")[0].strip()
        if line == "":
            continue
        print("dijkstra> " + line)
        try:
            do_command(line, graph)
        except (ValueError, KeyError) as err:
            print("error: %s" % err)


# ── Self-test suite ──────────────────────────────────────────────────────────

def run_tests():
    passed = 0
    total = 0

    def check(description, condition):
        nonlocal passed, total
        total += 1
        mark = "PASS" if condition else "FAIL"
        if condition:
            passed += 1
        print("[%s] %s" % (mark, description))

    # 1. A straight line: A -> B -> C.
    g = Graph()
    g.add_edge("A", "B", 1)
    g.add_edge("B", "C", 2)
    dist, prev = shortest_paths(g, "A")
    check("line graph: A=0, B=1, C=3", dist == {"A": 0, "B": 1, "C": 3})

    # 2. A diamond where the two-hop route beats the direct-looking one.
    g = Graph()
    g.add_edge("A", "B", 4)
    g.add_edge("A", "C", 1)
    g.add_edge("C", "B", 2)
    g.add_edge("B", "D", 1)
    g.add_edge("C", "D", 5)
    dist, prev = shortest_paths(g, "A")
    check("diamond graph: shortest to D is 4 via A-C-B-D, not 5 via A-C-D",
          dist["D"] == 4)
    check("diamond graph: shortest to B is 3 via A-C-B, not 4 direct",
          dist["B"] == 3)

    # 3. A node with no path in from the source stays at infinity.
    g = Graph()
    g.add_edge("A", "B", 1)
    g.add_node("Z")   # isolated, unreachable
    dist, prev = shortest_paths(g, "A")
    check("unreachable node stays at infinity", dist["Z"] == INFINITY)
    check("unreachable node has no path", path_to(prev, "A", "Z") is None)

    # 4. A single node with no edges at all.
    g = Graph()
    g.add_node("A")
    dist, prev = shortest_paths(g, "A")
    check("single isolated node: distance to itself is 0", dist == {"A": 0})

    # 5. A self-loop should not change anything.
    g = Graph()
    g.add_edge("A", "A", 9)
    g.add_edge("A", "B", 3)
    dist, prev = shortest_paths(g, "A")
    check("self-loop does not affect distances", dist == {"A": 0, "B": 3})

    # 6. Two parallel edges between the same pair: the cheaper one wins.
    g = Graph()
    g.add_edge("A", "B", 5)
    g.add_edge("A", "B", 2)
    dist, prev = shortest_paths(g, "A")
    check("parallel edges: cheaper one wins", dist["B"] == 2)

    # 7. Path reconstruction follows the actual shortest route, not just
    #    reporting the right distance.
    g = Graph()
    g.add_edge("A", "B", 4)
    g.add_edge("A", "C", 1)
    g.add_edge("C", "B", 2)
    g.add_edge("B", "D", 1)
    dist, prev = shortest_paths(g, "A")
    route = path_to(prev, "A", "D")
    check("path reconstruction: A -> C -> B -> D", route == ["A", "C", "B", "D"])

    # 8. A zero-weight edge is a legal shortest hop.
    g = Graph()
    g.add_edge("A", "B", 0)
    g.add_edge("B", "C", 0)
    dist, prev = shortest_paths(g, "A")
    check("zero-weight edges work", dist == {"A": 0, "B": 0, "C": 0})

    # 9. A larger graph, worked out by hand.
    #    A -B(2)- C -B... let's use six nodes with a clear shortest tree.
    g = Graph()
    g.add_edge("A", "B", 7)
    g.add_edge("A", "C", 9)
    g.add_edge("A", "F", 14)
    g.add_edge("B", "C", 10)
    g.add_edge("B", "D", 15)
    g.add_edge("C", "D", 11)
    g.add_edge("C", "F", 2)
    g.add_edge("D", "E", 6)
    g.add_edge("F", "E", 9)
    dist, prev = shortest_paths(g, "A")
    # A->C = 9, A->C->F = 11, A->C->D = 20, A->C->D->E = 20 vs A->C->F->E = 20 (tie)
    check("larger graph: A=0", dist["A"] == 0)
    check("larger graph: C=9 (direct beats via B)", dist["C"] == 9)
    check("larger graph: F=11 (via C, not the direct 14-weight edge)", dist["F"] == 11)
    check("larger graph: D=20 (via C)", dist["D"] == 20)
    check("larger graph: E=20 (via C-D or C-F, both total 20)", dist["E"] == 20)

    # 10. Dijkstra agrees with brute-force enumeration on a handful of graphs
    #     with only non-negative weights -- the case Dijkstra guarantees.
    test_graphs = []

    g = Graph()
    g.add_edge("A", "B", 4)
    g.add_edge("A", "C", 1)
    g.add_edge("C", "B", 2)
    g.add_edge("B", "D", 1)
    g.add_edge("C", "D", 5)
    test_graphs.append((g, "A", "D"))

    g = Graph()
    g.add_edge("A", "B", 1)
    g.add_edge("A", "C", 5)
    g.add_edge("B", "C", 1)
    g.add_edge("B", "D", 6)
    g.add_edge("C", "D", 1)
    test_graphs.append((g, "A", "D"))

    for i, (tg, source, target) in enumerate(test_graphs, start=1):
        dist, prev = shortest_paths(tg, source)
        dijkstra_length = dist[target]
        brute_result = brute_force_shortest_path(tg, source, target)
        brute_length = brute_result[1] if brute_result is not None else INFINITY
        check("brute-force agreement, graph %d" % i, dijkstra_length == brute_length)

    # 11. The known limitation: with a negative edge, the "finalize smallest
    #     label first" argument breaks, and Dijkstra can give a WRONG answer
    #     while brute force still finds the true shortest path. This isn't a
    #     bug -- it's the reason Bellman-Ford exists. We assert the mismatch
    #     itself, to pin the limitation down as a fact about the algorithm.
    # C looks cheap and direct (1), so Dijkstra finalizes it immediately.
    # Only afterward does it discover the cheaper route through D, but C is
    # already permanent -- its label never gets to improve.
    g = Graph()
    g.add_edge("A", "C", 1)
    g.add_edge("A", "D", 2)
    g.add_edge("D", "C", -5)
    dist, prev = shortest_paths(g, "A")
    brute_result = brute_force_shortest_path(g, "A", "C")
    check("known limitation: negative weight makes Dijkstra disagree with brute force",
          dist["C"] != brute_result[1])

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
        print("(verbose mode: every label finalize and relax is printed)\n")
    files = [a for a in args if not a.startswith("--")]
    if len(files) > 0:
        run_file(files[0])
        return
    repl()


if __name__ == "__main__":
    main()

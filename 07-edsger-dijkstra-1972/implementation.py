"""
Dijkstra's shortest path algorithm — a full working version.

Edsger Dijkstra published this in 1959 in a three-page paper, "A note on
two problems in connexion with graphs." He had worked it out three years
earlier in about twenty minutes at a cafe in Amsterdam, to demonstrate
the ARMAC computer. It is still the algorithm your phone runs when it
plans a route.

Before this: to find the shortest route you would, in effect, try the
routes and compare them. The number of routes through a map grows
explosively, so that does not scale.

After this: you grow a frontier outward from the start, always settling
the nearest unsettled node next. Because road lengths are non-negative,
the first time you settle a node you already have its shortest distance.
You look at each edge only a small number of times.

This file adds the parts a real implementation needs on top of
concept.py:
  - a priority queue (binary heap) so picking the nearest node is fast
  - path reconstruction, not just distances
  - directed and undirected edges
  - a graph-file loader so you can run your own maps
  - an interactive REPL, a test suite, and a verbose trace

Run:
  python3 implementation.py                 # interactive REPL (starts with a demo map)
  python3 implementation.py roads.graph     # load a graph file and run its queries
  python3 implementation.py --test          # test suite
  python3 implementation.py --verbose       # REPL that traces every step

Graph file format (see the REPL 'help' for the same commands):
  # lines starting with # are comments
  start: A          # optional: default start node for 'from'
  edge A B 7        # undirected edge A<->B of length 7
  dedge A B 7       # directed edge A->B of length 7
  from A            # print shortest distance from A to every node
  path A E          # print the shortest path and distance from A to E
"""

import heapq
import sys

INF = float("inf")


# ---------------------------------------------------------------------------
# The graph: node -> {neighbour: length, ...}
# ---------------------------------------------------------------------------

def add_edge(graph, u, v, length, directed=False):
    """Add an edge. Undirected edges are stored in both directions."""
    if u not in graph:
        graph[u] = {}
    if v not in graph:
        graph[v] = {}
    graph[u][v] = length
    if not directed:
        graph[v][u] = length


# ---------------------------------------------------------------------------
# The algorithm
# ---------------------------------------------------------------------------

def dijkstra(graph, start, verbose=False):
    """
    Return (distance, previous):
      distance[node] = shortest distance from start to node (INF if unreachable)
      previous[node] = the node we arrived from on that shortest path
    Uses a binary heap as the priority queue so the nearest unsettled node
    is always cheap to find.
    """
    distance = {}
    for node in graph:
        distance[node] = INF
    distance[start] = 0

    previous = {}
    for node in graph:
        previous[node] = None

    settled = set()

    # The heap holds (distance_so_far, node). The smallest distance is on top.
    frontier = [(0, start)]

    step = 0
    while len(frontier) > 0:
        current_distance, current = heapq.heappop(frontier)

        # A node can appear on the heap more than once with different
        # distances. If we have already settled it, skip the stale copy.
        if current in settled:
            continue
        settled.add(current)

        if verbose:
            step = step + 1
            print("  step " + str(step) + ": settle " + str(current) +
                  " at distance " + fmt(current_distance))

        # Relax every edge out of current.
        for neighbour, road_length in graph[current].items():
            if neighbour in settled:
                continue
            new_distance = current_distance + road_length
            if new_distance < distance[neighbour]:
                distance[neighbour] = new_distance
                previous[neighbour] = current
                heapq.heappush(frontier, (new_distance, neighbour))
                if verbose:
                    print("      relax " + str(current) + "->" + str(neighbour) +
                          ": " + str(neighbour) + " now " + fmt(new_distance))

    return distance, previous


def reconstruct_path(previous, start, target):
    """Walk the previous-pointers backward from target to start."""
    if target not in previous:
        return None
    path = []
    node = target
    while node is not None:
        path.append(node)
        if node == start:
            break
        node = previous[node]
    path.reverse()
    # If we did not end up at start, target is unreachable.
    if len(path) == 0 or path[0] != start:
        return None
    return path


def shortest_path(graph, start, target, verbose=False):
    """Convenience: return (path_as_list, total_distance)."""
    if start not in graph or target not in graph:
        return None, INF
    distance, previous = dijkstra(graph, start, verbose=verbose)
    return reconstruct_path(previous, start, target), distance[target]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def fmt(d):
    if d == INF:
        return "unreachable"
    return str(d)


def demo_graph():
    """The sample road map used throughout the chapter."""
    graph = {}
    add_edge(graph, "A", "B", 7)
    add_edge(graph, "A", "C", 9)
    add_edge(graph, "A", "F", 14)
    add_edge(graph, "B", "C", 10)
    add_edge(graph, "B", "D", 15)
    add_edge(graph, "C", "D", 11)
    add_edge(graph, "C", "F", 2)
    add_edge(graph, "D", "E", 6)
    add_edge(graph, "E", "F", 9)
    return graph


def show_graph(graph):
    if len(graph) == 0:
        print("(empty graph)")
        return
    for node in sorted(graph):
        parts = []
        for neighbour in sorted(graph[node]):
            parts.append(neighbour + "(" + str(graph[node][neighbour]) + ")")
        print("  " + node + " -> " + ", ".join(parts))


def print_from(graph, start, verbose=False):
    if start not in graph:
        print("no such node: " + start)
        return
    distance, previous = dijkstra(graph, start, verbose=verbose)
    print("shortest distance from " + start + ":")
    for node in sorted(distance):
        print("  " + node + ": " + fmt(distance[node]))


def print_path(graph, start, target, verbose=False):
    path, total = shortest_path(graph, start, target, verbose=verbose)
    if path is None:
        print("no path from " + start + " to " + target)
        return
    print(" -> ".join(path) + "   (distance " + fmt(total) + ")")


# ---------------------------------------------------------------------------
# Graph-file loader / command runner
# ---------------------------------------------------------------------------

def run_line(graph, state, line, verbose=False):
    """
    Execute one command line against the graph. Shared by the REPL and the
    file loader. Returns False if the command was 'quit', True otherwise.
    """
    line = line.strip()
    if line == "" or line.startswith("#"):
        return True

    parts = line.split()
    command = parts[0].lower().rstrip(":")

    if command in ("quit", "exit"):
        return False

    if command == "help":
        print(HELP_TEXT)
        return True

    if command == "demo":
        graph.clear()
        graph.update(demo_graph())
        state["start"] = "A"
        print("loaded demo map (start A)")
        return True

    if command == "reset":
        graph.clear()
        state["start"] = None
        print("cleared")
        return True

    if command == "graph":
        show_graph(graph)
        return True

    if command == "start":
        if len(parts) < 2:
            print("usage: start: <node>")
            return True
        state["start"] = parts[1]
        return True

    if command in ("edge", "dedge"):
        if len(parts) < 4:
            print("usage: " + command + " <from> <to> <length>")
            return True
        u = parts[1]
        v = parts[2]
        length = int(parts[3])
        add_edge(graph, u, v, length, directed=(command == "dedge"))
        return True

    if command == "from":
        node = parts[1] if len(parts) > 1 else state["start"]
        if node is None:
            print("no start node; use 'from <node>' or 'start: <node>'")
            return True
        print_from(graph, node, verbose=verbose)
        return True

    if command == "path":
        if len(parts) < 3:
            print("usage: path <from> <to>")
            return True
        print_path(graph, parts[1], parts[2], verbose=verbose)
        return True

    print("unknown command: " + command + "   (try 'help')")
    return True


def load_file(path, verbose=False):
    graph = {}
    state = {"start": None}
    with open(path) as f:
        for line in f:
            run_line(graph, state, line, verbose=verbose)
    # If the file only built a graph and set a start but ran no query,
    # print all shortest distances from start as a sensible default.
    stripped = []
    with open(path) as f:
        for line in f:
            s = line.strip()
            if s != "" and not s.startswith("#"):
                stripped.append(s.split()[0].lower().rstrip(":"))
    if "from" not in stripped and "path" not in stripped and state["start"] is not None:
        print_from(graph, state["start"], verbose=verbose)


HELP_TEXT = """commands:
  edge A B 7      add undirected edge A<->B, length 7
  dedge A B 7     add directed edge A->B, length 7
  start: A        set the default start node
  from A          shortest distance from A to every node
  from            shortest distance from the default start
  path A E        shortest path and distance from A to E
  graph           show the current graph
  demo            load the sample road map
  reset           clear the graph
  help            this text
  quit            leave"""


def repl(verbose=False):
    graph = demo_graph()
    state = {"start": "A"}
    print("Dijkstra's shortest path. Loaded the demo map. Type 'help'.")
    print("Try:  path A E     or     from A     or     graph")
    while True:
        try:
            line = input("dijkstra> ")
        except EOFError:
            print()
            break
        keep_going = run_line(graph, state, line, verbose=verbose)
        if not keep_going:
            break


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def run_tests():
    graph = demo_graph()
    passed = 0
    failed = 0

    def check(name, got, want):
        nonlocal passed, failed
        if got == want:
            passed = passed + 1
            print("  ok   " + name)
        else:
            failed = failed + 1
            print("  FAIL " + name + ": got " + repr(got) + ", want " + repr(want))

    distance, previous = dijkstra(graph, "A")

    # 1-6: shortest distances from A on the demo map (worked by hand in README).
    check("dist A->A", distance["A"], 0)
    check("dist A->B", distance["B"], 7)
    check("dist A->C", distance["C"], 9)
    check("dist A->F", distance["F"], 11)   # A->C->F = 9+2, not the direct 14
    check("dist A->D", distance["D"], 20)   # A->C->D = 9+11
    check("dist A->E", distance["E"], 20)   # A->C->F->E = 9+2+9

    # 7: the cheapest path to F goes through C, not the direct road.
    check("path A->F", reconstruct_path(previous, "A", "F"), ["A", "C", "F"])

    # 8: path to E prefers the F route.
    check("path A->E", reconstruct_path(previous, "A", "E"), ["A", "C", "F", "E"])

    # 9: shortest_path convenience returns path and total.
    path, total = shortest_path(graph, "A", "E")
    check("shortest_path A->E total", total, 20)

    # 10: symmetric map, so distance is the same the other way.
    dist_e, _ = dijkstra(graph, "E")
    check("dist E->A == A->E", dist_e["A"], distance["E"])

    # 11: trivial path to itself.
    check("path A->A", reconstruct_path(previous, "A", "A"), ["A"])

    # 12: a directed edge is one-way.
    g2 = {}
    add_edge(g2, "X", "Y", 5, directed=True)
    dx, _ = dijkstra(g2, "X")
    dy, _ = dijkstra(g2, "Y")
    check("directed X->Y reachable", dx["Y"], 5)
    check("directed Y->X unreachable", dy["X"], INF)

    # 13: disconnected node stays at infinity.
    g3 = {}
    add_edge(g3, "P", "Q", 3)
    g3["Z"] = {}   # island
    d3, _ = dijkstra(g3, "P")
    check("disconnected node is INF", d3["Z"], INF)

    # 14: a longer single edge loses to a two-hop route.
    g4 = {}
    add_edge(g4, "S", "T", 100)
    add_edge(g4, "S", "M", 1)
    add_edge(g4, "M", "T", 1)
    check("two-hop beats direct", shortest_path(g4, "S", "T")[1], 2)

    # 15: choosing the nearest first still works when edges tie.
    g5 = {}
    add_edge(g5, "A", "B", 1)
    add_edge(g5, "A", "C", 1)
    add_edge(g5, "B", "D", 1)
    add_edge(g5, "C", "D", 1)
    check("tie resolves to distance 2", shortest_path(g5, "A", "D")[1], 2)

    # 16: unreachable target returns no path.
    check("no path to island", shortest_path(g3, "P", "Z")[0], None)

    print("")
    print(str(passed) + " passed, " + str(failed) + " failed")
    if failed > 0:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    verbose = False
    if "--verbose" in args:
        verbose = True
        args.remove("--verbose")

    if "--test" in args:
        run_tests()
        return

    # A bare filename argument means: load and run that graph file.
    file_args = []
    for a in args:
        if not a.startswith("--"):
            file_args.append(a)

    if len(file_args) > 0:
        load_file(file_args[0], verbose=verbose)
        return

    repl(verbose=verbose)


if __name__ == "__main__":
    main()

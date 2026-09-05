"""
Dijkstra's shortest path — the core idea (Edsger W. Dijkstra, 1959)

Before this algorithm, finding the shortest route through a network was a matter
of trial and error. You could enumerate paths and compare them, but the number of
paths explodes, and there was no systematic method that was guaranteed to find the
best one without looking at nearly everything. Dijkstra found one, reportedly in
about twenty minutes over coffee, while thinking about how to demo the ARMAC
computer with a route between two Dutch cities.

The trick is greedy and almost embarrassingly simple. Give every node a tentative
distance from the start: 0 for the start, infinity for everyone else. Then repeat:
pick the unvisited node with the SMALLEST tentative distance, mark it visited (its
distance is now final and can never improve), and "relax" its neighbors — if going
through this node reaches a neighbor more cheaply than its current tentative
distance, lower that neighbor's tentative distance.

Why does grabbing the smallest work? Because every edge has a non-negative weight,
the closest unvisited node can't be reached more cheaply by a longer detour. So the
moment you pick it, its distance is settled. That one observation turns an
exponential search into a method that touches each node once.

The version below is Dijkstra's original "scan for the minimum" form, not the
modern heap-based one. It is the whole idea in one function.
"""

INFINITY = float("inf")


def shortest_paths(graph, start):
    """Return the shortest distance from `start` to every node in `graph`.

    `graph` maps each node to a dict of {neighbor: edge_weight}. Weights must be
    non-negative — that is the one condition Dijkstra's method depends on.
    """
    # Every node begins infinitely far away, except the start, which is 0 away.
    distance = {}
    for node in graph:
        distance[node] = INFINITY
    distance[start] = 0

    # No node is settled yet. A settled node has its final, shortest distance.
    unvisited = set(graph)

    while len(unvisited) > 0:
        # Pick the unvisited node with the smallest tentative distance. This linear
        # scan is exactly what Dijkstra described in 1959.
        current = None
        for node in unvisited:
            if current is None or distance[node] < distance[current]:
                current = node

        # If even the closest unvisited node is unreachable, the rest are too.
        if distance[current] == INFINITY:
            break

        # `current` is now settled. Its tentative distance is final.
        unvisited.remove(current)

        # Relax each neighbor: is the path THROUGH current cheaper than what the
        # neighbor already has?
        for neighbor in graph[current]:
            step = distance[current] + graph[current][neighbor]
            if step < distance[neighbor]:
                distance[neighbor] = step

    return distance


# ── One small map, solved by hand-sized numbers ────────────────────────────────

# A weighted, directed graph. Read graph["A"] = {"B": 7} as "an edge A -> B of cost 7".
graph = {
    "A": {"B": 7, "C": 9, "F": 14},
    "B": {"C": 10, "D": 15},
    "C": {"D": 11, "F": 2},
    "D": {"E": 6},
    "E": {},
    "F": {"E": 9},
}

distance = shortest_paths(graph, "A")

print("shortest distance from A to every node:")
for node in sorted(distance):
    print("  A -> %s : %s" % (node, distance[node]))
print()
print("The shortest A -> E is 20, not the direct-looking A -> F -> E (23).")
print("Grabbing the closest unsettled node each step is all it takes.")

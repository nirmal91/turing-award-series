"""
Shortest path — the core idea (Edsger W. Dijkstra, 1959)

Before this, "find the shortest route between two points" meant trying paths
and comparing their total lengths, one at a time. There was no guarantee you
had checked the right ones, and no way to know you were done without trying
almost everything.

Dijkstra's insight: grow the answer outward from the start, one node at a
time, always finishing the *nearest unfinished* node next. Once a node is
finished its distance can never improve again, because every other way to
reach it would have to pass through a node that is farther away than it is
(and every edge length is non-negative). That single fact is the whole
algorithm. No backtracking, no trying combinations. Twenty minutes with a
napkin in a cafe in Amsterdam, according to Dijkstra himself.
"""

INF = float("inf")


def shortest_paths(graph, start):
    # graph: {node: {neighbor: edge_length, ...}, ...}
    # distance[node] = best known length from start to node, so far
    distance = {}
    for node in graph:
        distance[node] = INF
    distance[start] = 0

    previous = {}          # previous[node] = the node we arrived from
    unfinished = set(graph.keys())

    while unfinished:
        # Pick the unfinished node that is currently nearest to start.
        current = None
        current_distance = INF
        for node in unfinished:
            if distance[node] < current_distance:
                current = node
                current_distance = distance[node]

        if current is None:
            break  # everything left is unreachable from start

        unfinished.remove(current)

        # This node's distance is now final. Try to improve its neighbors
        # by going through it.
        for neighbor, length in graph[current].items():
            candidate = distance[current] + length
            if candidate < distance[neighbor]:
                distance[neighbor] = candidate
                previous[neighbor] = current

    return distance, previous


def path_to(previous, start, target):
    if target not in previous and target != start:
        return None
    path = [target]
    while path[-1] != start:
        path.append(previous[path[-1]])
    path.reverse()
    return path


# ── A tiny road map ──────────────────────────────────────────────────────────

roads = {
    "A": {"B": 4, "C": 2},
    "B": {"D": 5},
    "C": {"B": 1, "D": 8, "E": 10},
    "D": {"E": 2},
    "E": {},
}

distance, previous = shortest_paths(roads, "A")

print("shortest distance from A to every node:")
for node in sorted(distance):
    print(f"  A -> {node}: {distance[node]}")

print()
print("shortest route A -> E:", " -> ".join(path_to(previous, "A", "E")))
print()
print("Every node was finished exactly once, nearest first.")
print("No route was ever guessed and checked. It was grown.")

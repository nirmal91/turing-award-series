"""
concept.py — Dijkstra's shortest path, the pure idea (Edsger W. Dijkstra, 1959).

In 1956 there was no standard way to find the shortest route through a network.
People solved road-map and cable-length problems by hand or by guesswork.
Dijkstra, testing the new ARMAC computer, wanted a demo an audience could follow,
so he worked out the shortest route between two Dutch cities. He designed the
whole method in about twenty minutes, in his head, sitting at a cafe with his
fiancee. This is that method, stripped to its bones.

The one idea: always expand the closest unvisited node next. Once you pop a node
as the closest, its shortest distance is final and never changes. No backtracking.

This version uses no priority queue and no fancy data structures on purpose.
It scans for the minimum by hand, the way you would on paper, so the idea is naked.
"""

# A graph as: node -> list of (neighbor, edge_weight).
# These are the six nodes and the roads between them for our example.
GRAPH = {
    "A": [("B", 7), ("C", 9), ("F", 14)],
    "B": [("A", 7), ("C", 10), ("D", 15)],
    "C": [("A", 9), ("B", 10), ("D", 11), ("F", 2)],
    "D": [("B", 15), ("C", 11), ("E", 6)],
    "E": [("D", 6), ("F", 9)],
    "F": [("A", 14), ("C", 2), ("E", 9)],
}

INFINITY = float("inf")


def shortest_paths(graph, source):
    # Best known distance from source to every node. Start: source is 0, rest infinite.
    distance = {}
    for node in graph:
        distance[node] = INFINITY
    distance[source] = 0

    # Nodes we have not yet finalized.
    unvisited = set(graph.keys())

    while len(unvisited) > 0:
        # Pick the unvisited node with the smallest known distance. This is the
        # whole trick: the closest one is safe to finalize, so we take it next.
        current = None
        for node in unvisited:
            if current is None or distance[node] < distance[current]:
                current = node

        # If even the closest is unreachable, the rest are too. Stop.
        if distance[current] == INFINITY:
            break

        unvisited.remove(current)

        # Relaxation: try to improve each neighbor by going through current.
        for neighbor, weight in graph[current]:
            candidate = distance[current] + weight
            if candidate < distance[neighbor]:
                distance[neighbor] = candidate

    return distance


if __name__ == "__main__":
    result = shortest_paths(GRAPH, "A")
    print("Shortest distance from A to every city:")
    for node in sorted(result):
        print("  A -> " + node + " = " + str(result[node]))

"""
concept.py — Dijkstra's shortest path, the pure idea.

In 1956 Dijkstra worked out this algorithm in about twenty minutes, sitting in
a cafe with his fiancee, no pencil and no paper. He published it in 1959 in a
three-page note. The problem: given a map of cities and road lengths, find the
shortest route from one city to every other.

The whole idea is one greedy rule. Keep a running best-known distance to every
city. Always expand the closest city you have not settled yet. When you expand
it, its distance is final, because every other route to it would have to go
through a city that is already further away. That single observation is why the
algorithm works.

No priority queue here, no classes. Just the rule, the way the 1959 note
describes it: repeatedly pick the nearest unsettled node and relax its edges.
"""

# A graph is a dict of node -> list of (neighbor, edge_length).
GRAPH = {
    "A": [("B", 7), ("C", 9), ("F", 14)],
    "B": [("A", 7), ("C", 10), ("D", 15)],
    "C": [("A", 9), ("B", 10), ("D", 11), ("F", 2)],
    "D": [("B", 15), ("C", 11), ("E", 6)],
    "E": [("D", 6), ("F", 9)],
    "F": [("A", 14), ("C", 2), ("E", 9)],
}


def shortest_paths(graph, source):
    # Best-known distance to each node. Unknown starts as infinity.
    distance = {}
    for node in graph:
        distance[node] = float("inf")
    distance[source] = 0

    settled = set()  # nodes whose shortest distance is now final

    while len(settled) < len(graph):
        # Pick the unsettled node with the smallest known distance.
        current = None
        for node in graph:
            if node in settled:
                continue
            if current is None or distance[node] < distance[current]:
                current = node

        # If the closest remaining node is unreachable, we are done.
        if distance[current] == float("inf"):
            break

        settled.add(current)

        # Relax: can we reach a neighbor faster by going through current?
        for neighbor, length in graph[current]:
            new_distance = distance[current] + length
            if new_distance < distance[neighbor]:
                distance[neighbor] = new_distance

    return distance


if __name__ == "__main__":
    result = shortest_paths(GRAPH, "A")
    print("Shortest distance from A to every city:")
    for node in sorted(result):
        print("  A -> " + node + " = " + str(result[node]))

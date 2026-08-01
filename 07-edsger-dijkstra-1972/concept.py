"""
Dijkstra's shortest path — the core idea (Edsger Dijkstra, 1959)

Before this, finding the cheapest route through a network meant either checking
every possible path (which explodes) or fiddling with ad hoc rules that could be
fooled. In 1956 Dijkstra worked out a method to find the shortest route from one
point to all others, and he did it in about twenty minutes at a cafe, with no
paper. It was published in 1959 as "A Note on Two Problems in Connexion with
Graphs" and it is still the algorithm your phone runs to route you home.

The trick is greed that happens to be correct. Keep a tentative distance to every
node, all starting at infinity except the start at 0. Repeatedly pick the
unsettled node with the smallest tentative distance and declare it settled: its
number is now final. Then relax its neighbours, meaning check whether reaching
them through this node is cheaper than what you had. Because no edge has a
negative length, the smallest tentative distance can never be beaten by a longer
detour, so settling it is safe. That one observation is the whole proof.
"""

INF = float("inf")


def shortest_paths(graph, start):
    # graph is a dict: node -> list of (neighbour, weight) pairs.
    # Every node's best-known distance from start. Unknown means infinity.
    distance = {}
    for node in graph:
        distance[node] = INF
    distance[start] = 0

    # Nodes whose distance is not yet final. We settle them one at a time.
    unsettled = set(graph.keys())

    while len(unsettled) > 0:
        # Pick the unsettled node with the smallest tentative distance.
        # This linear scan is exactly what Dijkstra described in 1959.
        current = None
        best = INF
        for node in unsettled:
            if distance[node] <= best:
                best = distance[node]
                current = node

        # Every remaining node is unreachable from start. Nothing left to do.
        if best == INF:
            break

        # Settle it: distance[current] is now final and will never change.
        unsettled.remove(current)

        # Relax each neighbour: is the path through current cheaper than before?
        for neighbour, weight in graph[current]:
            through_current = distance[current] + weight
            if through_current < distance[neighbour]:
                distance[neighbour] = through_current

    return distance


# A small road network. Each edge is listed in both directions, the way a
# two-way street works. Weights are distances (or times, or costs).
graph = {
    "A": [("B", 4), ("C", 2)],
    "B": [("A", 4), ("C", 1), ("D", 5)],
    "C": [("A", 2), ("B", 1), ("D", 8)],
    "D": [("B", 5), ("C", 8)],
}

result = shortest_paths(graph, "A")

print("Shortest distance from A to every node:")
for node in sorted(result):
    print("  A ->", node, "=", result[node])

print()
print("The greedy pick is safe only because no edge is negative.")
print("Settle the closest unsettled node, relax its neighbours, repeat.")

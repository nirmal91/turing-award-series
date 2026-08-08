"""
Dijkstra's shortest path — the core idea (Edsger W. Dijkstra, 1959)

Before this algorithm, finding the shortest route through a network meant trying
paths and hoping. There was no method that promised the answer was truly the
shortest, short of checking every route, and the number of routes explodes as the
network grows. Dijkstra thought of the method in about twenty minutes in 1956,
sitting at a cafe in Amsterdam, as a way to show off the new ARMAC computer: the
shortest way to drive between two Dutch cities.

The trick is greed done carefully. Keep a tentative best distance to every node.
Repeatedly take the unvisited node with the smallest tentative distance and call
it settled: because every edge weight is zero or positive, no later path can ever
beat the one you already have to that node. Then "relax" its neighbours, lowering
their tentative distances if going through this node is cheaper. Settle nodes one
at a time and the distances grow outward from the start like a wavefront. When a
node is settled, its distance is final. That is the whole proof and the whole
program.

This runs one example graph. implementation.py turns the same idea into an
interactive tool with path reconstruction, tests, and a step-by-step trace.
"""

# An undirected road map: each edge is (city, city, distance). The same roads
# Dijkstra imagined between towns, with made-up mileage.
EDGES = [
    ("A", "B", 7), ("A", "C", 9), ("A", "F", 14),
    ("B", "C", 10), ("B", "D", 15),
    ("C", "D", 11), ("C", "F", 2),
    ("D", "E", 6), ("E", "F", 9),
]

# Build a neighbour table: for each city, the roads leaving it.
neighbours = {}
for u, v, w in EDGES:
    neighbours.setdefault(u, []).append((v, w))
    neighbours.setdefault(v, []).append((u, w))  # undirected: the road goes both ways


def shortest_paths(start):
    # The best distance we currently know to each city. Unknown means infinity.
    distance = {}
    for city in neighbours:
        distance[city] = float("inf")
    distance[start] = 0

    settled = set()  # cities whose distance is now final and will never change

    # Settle one city per pass: the closest one we have not settled yet.
    while len(settled) < len(neighbours):
        # Find the unsettled city with the smallest known distance.
        current = None
        for city in neighbours:
            if city in settled:
                continue
            if current is None or distance[city] < distance[current]:
                current = city

        # Everything left is unreachable from start; nothing more to do.
        if distance[current] == float("inf"):
            break

        settled.add(current)

        # Relax the roads out of current: is going through current cheaper?
        for (neighbour, road) in neighbours[current]:
            through_current = distance[current] + road
            if through_current < distance[neighbour]:
                distance[neighbour] = through_current

    return distance


result = shortest_paths("A")
print("Shortest distance from A to every city:")
for city in sorted(result):
    print("  A ->", city, "=", result[city])
print()
print("A settled city can never be improved, because every road is non-negative.")
print("That single fact is why greedy works and the answer is provably shortest.")

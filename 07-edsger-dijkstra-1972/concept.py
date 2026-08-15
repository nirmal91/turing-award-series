"""
Dijkstra's shortest path — the core idea (Edsger W. Dijkstra, 1959)

Before 1959 there was no clean, general answer to a plain question: given a map of
roads with distances, what is the shortest way from one city to another? People
solved instances by hand or by ad hoc search that could wander down long routes
before finding a short one. Dijkstra found the method while sitting at a cafe in
Amsterdam with his fiancee, and worked it out in about twenty minutes without pencil
or paper. He published it in 1959 in a three-page note.

The whole idea is one disciplined rule. Keep a tentative distance for every node,
starting at 0 for the source and infinity for everything else. Then repeat: pick the
unfinished node with the smallest tentative distance, declare it finished (its
distance can never get smaller), and use it to relax its neighbours — if going
through it is shorter than what they had, write down the shorter number.

Why picking the smallest is safe is the heart of it. Because every edge has a
non-negative length, no path through a farther node can loop back and beat a node
that is already the closest unfinished one. So the moment a node is the minimum, its
distance is final. That single observation turns an exponential search into a loop
that touches each node once. Every routing protocol, GPS, and network layout in use
today is a descendant of this rule.
"""

# A graph as an adjacency table: node -> list of (neighbour, edge_length).
# This is the classic six-node example. All edge lengths are non-negative, which
# is the one thing Dijkstra's rule requires to be correct.
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
    # Tentative distance to every node. The source is 0 away from itself; we have
    # not yet found any route to the others, so they start infinitely far.
    distance = {}
    for node in graph:
        distance[node] = INFINITY
    distance[source] = 0

    finished = set()        # nodes whose shortest distance is now settled for good

    while len(finished) < len(graph):
        # Pick the unfinished node with the smallest tentative distance. This linear
        # scan is exactly how Dijkstra described it in 1959 (the heap came later).
        current = None
        for node in graph:
            if node in finished:
                continue
            if current is None or distance[node] < distance[current]:
                current = node

        # If even the closest unfinished node is unreachable, the rest are too.
        if distance[current] == INFINITY:
            break

        finished.add(current)

        # Relax every edge out of current: is going through current an improvement?
        for neighbour, length in graph[current]:
            through_current = distance[current] + length
            if through_current < distance[neighbour]:
                distance[neighbour] = through_current

    return distance


# ── Run the rule from A and print every shortest distance ────────────────────────

result = shortest_paths(GRAPH, "A")
print("shortest distance from A to every node:")
for node in sorted(result):
    print("  A -> %s  =  %s" % (node, result[node]))
print()
print("The shortest A -> E is 20, along A -> C -> F -> E (9 + 2 + 9).")
print("A greedy-looking longer road A -> F costs 14 on its own, so the route")
print("through C wins. Always settling the closest unfinished node is what")
print("guarantees the answer is right, not just plausible.")

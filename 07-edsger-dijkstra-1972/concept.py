"""
Dijkstra's shortest-path algorithm — the core idea (E. W. Dijkstra, 1959).

Before this, finding the shortest route between two points in a network meant
checking paths — in the worst case, all of them — and comparing their total
lengths. The number of simple paths through a graph grows combinatorially, so
that approach falls apart as the graph grows.

Dijkstra's insight: you never need to compare whole paths. Give every node a
"label" — a running best-guess distance from the start. Repeatedly take the
not-yet-finished node with the smallest label, declare its label final, and
use it to try to shrink its neighbors' labels. Because you always finalize the
smallest remaining label first, and edge weights are never negative, that
label can never improve later. One pass, and every node ends up with its true
shortest distance. No path is ever explicitly compared to another.
"""

INFINITY = float("inf")

# A tiny directed, weighted graph: node -> list of (neighbor, weight).
graph = {
    "A": [("B", 4), ("C", 1)],
    "B": [("D", 1)],
    "C": [("B", 2), ("D", 5)],
    "D": [],
}


def shortest_paths(graph, source):
    # Every label starts at infinity — "we don't know yet" — except the
    # source, which is zero distance from itself.
    label = {node: INFINITY for node in graph}
    label[source] = 0

    # Two piles: nodes still tentative, and nodes whose label is now final.
    tentative = set(graph.keys())
    finished = set()

    while tentative:
        # Find the tentative node with the smallest label. This linear scan
        # is exactly what the 1959 paper does — no priority queue yet.
        current = min(tentative, key=lambda node: label[node])
        tentative.remove(current)
        finished.add(current)

        # That label is now permanent. Use it to relax (try to shrink) the
        # labels of every neighbor still tentative.
        for neighbor, weight in graph[current]:
            if neighbor in finished:
                continue
            candidate = label[current] + weight
            if candidate < label[neighbor]:
                label[neighbor] = candidate

    return label


if __name__ == "__main__":
    distances = shortest_paths(graph, "A")
    print("shortest distances from A:")
    for node in sorted(distances):
        print("  %s: %s" % (node, distances[node]))
    print()
    print("A -> C -> B -> D (1+2+1=4) beats the direct-looking A -> B -> D (4+1=5),")
    print("and no whole path was ever built and compared to find that out.")

"""
Dijkstra's shortest path algorithm, distilled to the core idea.

In 1956, Edsger Dijkstra was thinking about the shortest driving route
from Rotterdam to Groningen. He worked out this algorithm in about twenty
minutes, sitting in a cafe, with no pencil or paper. He needed something
simple enough to explain to a non-technical audience: it was a demo for
a new computer, the ARMAC, built to show people who had never seen a
computer solve anything that it actually could.

The idea: grow a set of nodes whose shortest distance from the start you
know FOR CERTAIN, one node at a time. Always take the closest unclaimed
node next, then use it to try to shorten the distance to its neighbors.
Once a node is claimed, its distance never changes again — everything
still unclaimed is at least as far away, so nothing left could beat it.
"""

INF = float("inf")


def shortest_paths(graph, start):
    distances = {node: INF for node in graph}
    distances[start] = 0
    unclaimed = set(graph)

    while unclaimed:
        # The closest unclaimed node is now final. Nothing left could turn
        # out to be closer, or it would already have a smaller distance.
        current = min(unclaimed, key=lambda node: distances[node])
        if distances[current] == INF:
            break  # everything left is unreachable from start

        unclaimed.remove(current)

        # Relax: does going through current make any neighbor cheaper?
        for neighbor, weight in graph[current]:
            through_current = distances[current] + weight
            if through_current < distances[neighbor]:
                distances[neighbor] = through_current

    return distances


if __name__ == "__main__":
    # Six Dutch cities, driving distance in km (rounded). Same shape as
    # Dijkstra's original demo: Rotterdam to Groningen.
    graph = {
        "Rotterdam":  [("Utrecht", 60), ("Amsterdam", 85)],
        "Utrecht":    [("Rotterdam", 60), ("Amsterdam", 40), ("Amersfoort", 25)],
        "Amsterdam":  [("Rotterdam", 85), ("Utrecht", 40), ("Amersfoort", 45), ("Zwolle", 110)],
        "Amersfoort": [("Utrecht", 25), ("Amsterdam", 45), ("Zwolle", 50)],
        "Zwolle":     [("Amersfoort", 50), ("Amsterdam", 110), ("Groningen", 100)],
        "Groningen":  [("Zwolle", 100)],
    }

    result = shortest_paths(graph, "Rotterdam")
    print("Shortest distance from Rotterdam (km):")
    for city, km in result.items():
        print(f"  {city:12s} {km}")

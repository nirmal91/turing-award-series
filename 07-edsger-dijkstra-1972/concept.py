"""
Dijkstra's shortest path, the pure idea (1959).

In 1956 Dijkstra worked out this algorithm in about twenty minutes at a
cafe terrace in Amsterdam, to show off what the ARMAC computer could do.
The question: what is the shortest route between two cities?

The naive answer is to try every possible route and keep the shortest.
The number of routes grows explosively, so that is hopeless on a real map.

Dijkstra's insight was that you never need to look at a whole route at
once. You grow outward from the start, and you always expand the nearest
place you have not settled yet. Because every road length is positive,
the nearest unsettled place can never be reached more cheaply by a longer
detour, so once you settle it, its distance is final. That one guarantee
is the whole algorithm.

No priority queue here, no path reconstruction, no classes. Just the
greedy loop, so you can see the idea with nothing in the way.
"""

# A tiny road map. Each city lists its neighbours and the road length.
GRAPH = {
    "A": {"B": 7, "C": 9, "F": 14},
    "B": {"A": 7, "C": 10, "D": 15},
    "C": {"A": 9, "B": 10, "D": 11, "F": 2},
    "D": {"B": 15, "C": 11, "E": 6},
    "E": {"D": 6, "F": 9},
    "F": {"A": 14, "C": 2, "E": 9},
}


def shortest_distances(graph, start):
    # Best distance known so far from start to each city. Unknown = infinity.
    distance = {}
    for city in graph:
        distance[city] = float("inf")
    distance[start] = 0

    # Cities whose distance is now final. We never touch them again.
    settled = set()

    while len(settled) < len(graph):
        # Pick the unsettled city with the smallest known distance.
        # This greedy choice is Dijkstra's whole trick.
        current = None
        for city in graph:
            if city in settled:
                continue
            if current is None or distance[city] < distance[current]:
                current = city

        # Nothing reachable is left. The rest is disconnected.
        if distance[current] == float("inf"):
            break

        settled.add(current)

        # Relax each road out of current: is going through current cheaper?
        for neighbour, road_length in graph[current].items():
            new_distance = distance[current] + road_length
            if new_distance < distance[neighbour]:
                distance[neighbour] = new_distance

    return distance


if __name__ == "__main__":
    start = "A"
    result = shortest_distances(GRAPH, start)
    print("shortest distance from " + start + " to each city:")
    for city in sorted(result):
        print("  " + city + ": " + str(result[city]))

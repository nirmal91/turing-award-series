# Week 07 — Edsger W. Dijkstra (1972)

**ACM Turing Award citation:** *"The working vocabulary of programmers everywhere is studded with words originated or forcefully promulgated by E. W. Dijkstra — display, deadly embrace, semaphore, go-to-less programming, structured programming. But his influence on programming is more pervasive than any glossary can possibly indicate. The precious gift that this Turing Award acknowledges is Dijkstra's style: his approach to programming as a high, intellectual challenge; his eloquent insistence and practical demonstration that programs should be composed correctly, not just debugged into correctness; and his illuminating perception of problems at the foundations of program design."*

## My Take
*[Placeholder — written by Nirmal, not AI]*

## The Code

Two files:

- [`concept.py`](./concept.py) — the pure idea: Dijkstra's shortest path with no priority queue and no path tracking, scanning for the closest node by hand the way you would on paper. The one rule, naked: always expand the closest unvisited node next, and once you do, its distance is final.
- [`implementation.py`](./implementation.py) — the full working version.

`implementation.py` pipeline:

```
graph file / REPL  ->  parse edges  ->  build adjacency  ->  Dijkstra (min-heap)
                                                                     |
                                                distances + predecessors
                                                                     |
                                                          reconstruct path
```

What it supports:

- A built-in demo on the classic six-city map
- An interactive REPL: type edges, then `run`
- A text graph format you can save in a file and run (`example.graph`)
- Directed or undirected graphs, non-negative weights only (it rejects negatives, because Dijkstra's core assumption breaks on them)
- Full path reconstruction, not just distances
- `--verbose` shows the frontier and every node's best-known distance at each step

How to run it:

```bash
python concept.py                       # the core idea, plain
python implementation.py                # demo + interactive REPL
python implementation.py example.graph  # run on a graph file
python implementation.py --test         # test suite (17 cases)
python implementation.py --verbose      # show the frontier at each step
```

Example session:

```
$ python implementation.py example.graph
Shortest paths from A:
  A -> A : distance 0   path A
  A -> B : distance 7   path A -> B
  A -> C : distance 9   path A -> C
  A -> D : distance 20   path A -> C -> D
  A -> E : distance 20   path A -> C -> F -> E
  A -> F : distance 11   path A -> C -> F
```

Note `A -> F`. There is a direct road A–F of length 14, but the algorithm finds the two-hop A–C–F of length 11 and takes it. That is the whole point: the shortest route is often not the direct one.

## Full Worked Example

The map has six cities. Undirected roads with lengths:

```
A–B 7    A–C 9    A–F 14
B–C 10   B–D 15
C–D 11   C–F 2
D–E 6
E–F 9
```

We want the shortest distance from **A** to every other city.

**Setup.** Give every city a "best known distance from A" tag. A starts at 0 (it is where we are). Every other city starts at infinity (we have not found any route yet). No city is finalized.

```
A=0   B=inf   C=inf   D=inf   E=inf   F=inf
```

**Step 1 — finalize A (distance 0).** A is the closest unfinalized city (it is 0; everything else is infinity). Finalize it. Now relax its neighbors: for each road out of A, check whether going through A beats the neighbor's current tag.

- A–B is 7. Is 0 + 7 < infinity? Yes. Set B = 7.
- A–C is 9. Is 0 + 9 < infinity? Yes. Set C = 9.
- A–F is 14. Is 0 + 14 < infinity? Yes. Set F = 14.

```
*A=0   B=7   C=9   D=inf   E=inf   F=14        (* = finalized)
```

**Step 2 — finalize B (distance 7).** Among the unfinalized (B=7, C=9, F=14, rest infinity), B is smallest. Finalize B at 7. Relax B's neighbors:

- B–C is 10. Is 7 + 10 = 17 < 9? No. C stays 9.
- B–D is 15. Is 7 + 15 = 22 < infinity? Yes. Set D = 22.

```
*A=0  *B=7   C=9   D=22   E=inf   F=14
```

**Step 3 — finalize C (distance 9).** Smallest unfinalized is C at 9. Finalize. Relax:

- C–D is 11. Is 9 + 11 = 20 < 22? Yes. Improve D to 20.
- C–F is 2. Is 9 + 2 = 11 < 14? Yes. Improve F to 11.
- (C–B is skipped; B is finalized.)

```
*A=0  *B=7  *C=9   D=20   E=inf   F=11
```

This is the heart of it. We *thought* F was 14 (the direct road). Going through C, it is 11. And D dropped from 22 to 20. This is called **relaxation**: every time we finalize a closer city, we get a chance to tighten the estimates for the cities beyond it.

**Step 4 — finalize F (distance 11).** Smallest unfinalized is F at 11. Finalize. Relax:

- F–E is 9. Is 11 + 9 = 20 < infinity? Yes. Set E = 20.
- (F–A, F–C skipped; finalized.)

```
*A=0  *B=7  *C=9   D=20   E=20   *F=11
```

**Step 5 — finalize D (distance 20).** D and E are tied at 20. Ties are fine; pick either. Finalize D. Relax:

- D–E is 6. Is 20 + 6 = 26 < 20? No. E stays 20.

```
*A=0  *B=7  *C=9  *D=20   E=20  *F=11
```

**Step 6 — finalize E (distance 20).** Last one. Finalize. It has no unfinalized neighbors left to improve. Done.

```
*A=0  *B=7  *C=9  *D=20  *E=20  *F=11
```

Final answer, and the routes (read backwards through the predecessors):

```
A -> B  =  7    (A–B)
A -> C  =  9    (A–C)
A -> D  = 20    (A–C–D)
A -> E  = 20    (A–C–F–E)
A -> F  = 11    (A–C–F)
```

**Why "finalize the closest" is safe.** When we pop the closest unfinalized city, could a shorter path to it still be waiting? No. Any other path to it would have to leave through some *other* unfinalized city first, and that city is already at least as far away (that is what "closest" means). Since all road lengths are non-negative, going further out and coming back can never be shorter. So the first time we reach the closest city, that distance is final. This is exactly why **negative weights break Dijkstra**: a negative road later on could make a "longer" detour actually shorter, and the safety argument collapses. `implementation.py` rejects negative weights for this reason.

**Edge case — unreachable node.** Add an island city Z with no roads. When the frontier empties, Z is still at infinity. The algorithm reports it unreachable rather than looping forever. (Test 10 checks this.)

## ELI5

Imagine your house is at the middle of a bunch of streets, and you want to know the shortest walk to every friend's house.

Before, you would trace routes with your finger and hope you found a short one. Easy to miss a shortcut.

Here is the trick. Start at your house. Find the friend you can reach in the fewest steps. Walk there. Now, standing at that friend's house, check: does going through here make any *other* friend closer than you thought? If yes, write down the shorter way.

Keep doing that, always going to the closest friend you have not visited yet. When you run out of friends, you have the shortest walk to every single one, and you never had to guess.

## ELI10

In the 1950s, if you wanted the shortest route through a network — roads between towns, wires between switchboards — you mostly did it by hand. There was no standard recipe a computer could follow, and for a big network, hand-tracing was slow and easy to get wrong.

In 1956, a 26-year-old programmer named Edsger Dijkstra was helping show off a new Dutch computer called the ARMAC. He needed a demo the audience could follow without knowing math, so he picked the shortest route between two cities in the Netherlands. Sitting at a cafe with his fiancee, with no pen and no paper, he worked out the whole method in about twenty minutes in his head.

The method is stubbornly simple. Tag your starting point with 0 and everything else with "unknown." Then repeat one move: go to the closest place you have not finalized yet, lock in its distance, and check whether reaching it opens up a shorter path to its neighbors. Because you always take the closest one next, the moment you arrive somewhere you already know it is the shortest way there. No backtracking, no guessing.

That little loop is now everywhere. When your phone finds a route, when internet routers decide where to send your data, when a game character walks around a wall, some descendant of Dijkstra's twenty-minute cafe idea is running. He later said he designed it without pencil and paper precisely because that forced him to avoid all avoidable complexity.

## CS Graduate Level

Dijkstra's Turing citation is deliberately broad. He did not win for a single theorem; he won for a *style* — the insistence that programs be constructed to be correct rather than debugged into working. Three concrete contributions anchor that style, and the code in this chapter implements the first.

### 1. The shortest path algorithm (1959)

**State of the art before.** Network optimization existed (the field of operations research was active), but there was no clean, provably correct, low-complexity procedure for single-source shortest paths that was simple enough to teach in a paragraph and run on the small machines of the era. Approaches were often ad hoc.

**What was new.** Dijkstra gave a greedy algorithm with an invariant strong enough to prove optimality. Maintain a set `S` of finalized vertices whose shortest distance from the source is known. Repeatedly select the vertex `u` outside `S` with the minimum tentative distance, add it to `S`, and *relax* its outgoing edges: for each edge `(u, v)` with weight `w`, if `dist[u] + w < dist[v]`, update `dist[v]`.

The correctness argument is the interesting part. **Claim:** when `u` is selected as the minimum-tentative-distance vertex outside `S`, `dist[u]` already equals the true shortest distance. **Proof sketch:** suppose not, and there is a shorter path `P` from source to `u`. `P` must at some point cross from `S` to outside `S`; let `y` be the first vertex on `P` outside `S`. Then `dist[y] <= (length of P's prefix up to y) <= length(P) < dist[u]`, using non-negativity of edge weights for the middle inequality. But then `y`, not `u`, would have been selected. Contradiction. The non-negativity assumption is load-bearing: with a negative edge, the prefix-shorter-than-whole step fails, and this is why Bellman–Ford (which relaxes all edges repeatedly) is needed when negative weights are present.

**Complexity.** With a linear scan for the minimum (as in `concept.py`), it is O(V²). With a binary min-heap (as in `implementation.py`, via `heapq`), each edge triggers at most one push, giving O((V + E) log V). With a Fibonacci heap (Fredman & Tarjan, 1984) it drops to O(E + V log V), which is asymptotically optimal for comparison-based approaches with a general priority queue.

**An implementation subtlety.** The `heapq` version uses "lazy deletion": rather than decreasing a key in place (which a binary heap does not support cheaply), it pushes a new `(distance, node)` entry and lets the stale, larger entry pop later, skipping it via a `finalized` set. This is the standard practical trick and is exactly what the code does.

**What descended from it.** Link-state internet routing protocols (OSPF, IS-IS) run Dijkstra on each router over the network topology. GPS and map routing use it (usually goal-directed variants like A*, which is Dijkstra plus an admissible heuristic). It is the backbone of countless graph libraries.

### 2. Structured programming and "Go To Statement Considered Harmful" (1968)

**State of the art before.** Control flow was built from `goto`. A program was a web of jumps, and reasoning about "what is true at this point in the code" meant reasoning about every path that could have jumped here.

**What was new.** Dijkstra's 1968 letter to the CACM argued that unrestricted `goto` makes the static program text and the dynamic execution diverge, so the human cannot map one to the other. The fix: build programs from a small set of composable control structures — sequence, selection (`if`/`else`), and iteration (`while`) — each with a single entry and single exit. This makes a program's dynamic state a simple function of its textual position plus a few loop counters. Böhm and Jacopini had already shown (1966) that these structures are sufficient to express any flowchart, giving the theory; Dijkstra supplied the engineering argument and the movement. It reshaped language design: the structured constructs we now take for granted in every mainstream language are this argument, won.

### 3. Concurrency: semaphores, mutual exclusion, and deadlock (1965–1968)

**State of the art before.** Coordinating concurrent processes sharing memory was a minefield of race conditions with no clean primitive.

**What was new.** In "Cooperating Sequential Processes" Dijkstra introduced the **semaphore**: an integer with two atomic operations, `P` (wait/decrement, block if it would go negative) and `V` (signal/increment). From this one primitive he built mutual exclusion and process synchronization. He posed and solved the **dining philosophers** problem as a teaching example of resource contention and deadlock (his "deadly embrace," named in the citation). The THE multiprogramming system (1968) demonstrated a fully layered OS design built on these ideas. Semaphores, mutexes, and the vocabulary of deadlock are direct descendants and are in every operating system today.

### The through-line

The citation's phrase "composed correctly, not just debugged into correctness" is the unifying idea. The shortest-path algorithm has an invariant you can prove. Structured programming exists so you *can* state invariants about a program at all. Semaphores give concurrency a primitive simple enough to reason about. In each case Dijkstra's move was to reduce something to a form where correctness is arguable rather than merely testable. His later work on weakest-preconditions and predicate transformers (the guarded command language, 1975; *A Discipline of Programming*, 1976) pushed this all the way to deriving programs from their specifications.

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [A Note on Two Problems in Connexion with Graphs](https://doi.org/10.1007/BF01386390) | Numerische Mathematik, 1(1) | 1959 |
| [Go To Statement Considered Harmful](https://doi.org/10.1145/362929.362947) | Communications of the ACM, 11(3) | 1968 |
| [Cooperating Sequential Processes (EWD123)](https://www.cs.utexas.edu/~EWD/transcriptions/EWD01xx/EWD123.html) | EWD manuscript / Academic Press | 1965/1968 |
| [The Structure of the "THE" Multiprogramming System](https://doi.org/10.1145/363095.363143) | Communications of the ACM, 11(5) | 1968 |
| [Guarded Commands, Nondeterminacy and Formal Derivation of Programs](https://doi.org/10.1145/360933.360975) | Communications of the ACM, 18(8) | 1975 |
| [The Humble Programmer (Turing Award Lecture)](https://doi.org/10.1145/355604.361591) | Communications of the ACM, 15(10) | 1972 |

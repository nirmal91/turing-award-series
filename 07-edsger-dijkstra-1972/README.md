# Week 07 — Edsger W. Dijkstra (1972)

**ACM Turing Award citation:** *"The working vocabulary of programmers everywhere is studded with words originated or forcefully promulgated by E. W. Dijkstra — display, deadly embrace, semaphore, go-to-less programming, structured programming. But his influence on programming is more pervasive than any glossary can possibly indicate. The precious gift that this Turing Award acknowledges is Dijkstra's style: his approach to programming as a high, intellectual challenge; his eloquent insistence and practical demonstration that programs should be composed correctly, not just debugged into correctness; and his illuminating perception of problems at the foundations of program design."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — Dijkstra's shortest path in about 60 lines: keep a best-known distance to every node, repeatedly expand the closest unsettled node, and relax its edges. The greedy rule and nothing else.

[`implementation.py`](./implementation.py) — a full working version: a graph-file parser, the algorithm with predecessor tracking so it returns the actual route (not just the distance), path reconstruction, a verbose mode that prints the tentative-distance table at every step, a demo, and a 15-case test suite.

```
graph text
    ↓ parse        one edge per line -> adjacency map
    ↓ dijkstra     settle the closest unsettled node, relax its edges, repeat
    ↓ distance[]   shortest length source..every node
    ↓ previous[]   predecessor chain
    ↓ reconstruct  walk predecessors backward
    ↓
  shortest route
```

What it supports:
- Undirected graphs by default; put the word `directed` on a line to make edges one-way
- Shortest distance from a source to every node, or a single source-to-target route
- Path reconstruction, not just the number
- Non-negative edge lengths (Dijkstra's core assumption — negative edges are rejected)
- A demo map, a `--verbose` trace of every settle-and-relax step, and a 15-case test suite

```bash
python3 concept.py                        # the core idea, plain
python3 implementation.py                 # demo on a built-in 6-city map
python3 implementation.py practice.txt    # run on a graph you wrote
python3 implementation.py practice.txt home work   # one source-to-target route
python3 implementation.py --test          # test suite (15 cases)
python3 implementation.py --verbose       # demo, printing every step
```

Example session:

```
$ python3 implementation.py
Dijkstra's shortest path on a 6-city map, source = A

Shortest distances from A:
  A .. A = 0    via A
  A .. B = 7    via A -> B
  A .. C = 9    via A -> C
  A .. D = 20   via A -> C -> D
  A .. E = 20   via A -> C -> F -> E
  A .. F = 11   via A -> C -> F
```

The route to E is `A -> C -> F -> E`, not the direct-looking `A -> F -> E`. The algorithm found that reaching F through C (9 + 2 = 11) beats the direct A–F edge (14), so the whole downstream route rides on that shortcut. You never told it to check; the greedy rule found it.

---

## Full Worked Example

The graph is the 6-city map in `implementation.py`. Edge lengths are symmetric (undirected):

```
A–B 7    A–C 9    A–F 14
B–C 10   B–D 15
C–D 11   C–F 2
D–E 6
E–F 9
```

We want the shortest distance from **A** to every city. The algorithm keeps two things:

- `distance` — the best length known so far to each node. Starts at 0 for A, infinity for everyone else.
- `settled` — the set of nodes whose distance is now final. Starts empty.

The rule each round: **pick the unsettled node with the smallest tentative distance, mark it settled, then relax every edge leaving it.** "Relax edge C→D" means: if going to D through C is shorter than D's current best, overwrite it.

### Start

```
distance = { A=0, B=inf, C=inf, D=inf, E=inf, F=inf }
settled  = { }
```

### Round 1 — settle A (distance 0)

A is the only node with a finite distance, so it is the closest unsettled node. Settle it and relax its edges:

```
relax A -> B : inf -> 0 + 7  = 7
relax A -> C : inf -> 0 + 9  = 9
relax A -> F : inf -> 0 + 14 = 14
distance = { A=0, B=7, C=9, D=inf, E=inf, F=14 }
settled  = { A }
```

### Round 2 — settle B (distance 7)

Among the unsettled nodes {B=7, C=9, F=14}, B is smallest. Settle B. Its only useful edge:

```
relax B -> D : inf -> 7 + 15 = 22
distance = { A=0, B=7, C=9, D=22, E=inf, F=14 }
settled  = { A, B }
```

B–C would give 7 + 10 = 17, which is worse than C's current 9, so C is not updated.

### Round 3 — settle C (distance 9)

Smallest unsettled is C=9. Settle it. This is the important round:

```
relax C -> D : 22 -> 9 + 11 = 20   (better route to D, through C)
relax C -> F : 14 -> 9 + 2  = 11   (better route to F, the C–F=2 shortcut)
distance = { A=0, B=7, C=9, D=20, E=inf, F=11 }
settled  = { A, B, C }
```

Notice both D and F just got cheaper. D dropped from 22 to 20; F dropped from 14 to 11. The direct A–F edge of 14 has now been beaten.

### Round 4 — settle F (distance 11)

Smallest unsettled is F=11 (not D=20). Settle F. Its edge to E:

```
relax F -> E : inf -> 11 + 9 = 20
distance = { A=0, B=7, C=9, D=20, E=20, F=11 }
settled  = { A, B, C, F }
```

### Round 5 — settle D (distance 20)

D and E are tied at 20. Ties are broken arbitrarily; say D goes first. Settle D. Its edge to E:

```
D -> E would give 20 + 6 = 26, worse than E's current 20. No update.
settled  = { A, B, C, D, F }
```

### Round 6 — settle E (distance 20)

E is the last node. Settle it. No unsettled neighbors left to relax. Done.

```
distance = { A=0, B=7, C=9, D=20, E=20, F=11 }
```

Final routes, read off the predecessor chain:

```
A .. B = 7    A -> B
A .. C = 9    A -> C
A .. D = 20   A -> C -> D
A .. E = 20   A -> C -> F -> E
A .. F = 11   A -> C -> F
```

### Why settling is safe (the key idea)

When a node is settled, its distance is **final** — the algorithm never revisits it. Why is that allowed? Because edge lengths are never negative. The node you are about to settle has the smallest tentative distance of anything unsettled. Any other route to it would have to leave through some other unsettled node, which is already at least as far away, and then add more non-negative length. So no cheaper route can exist. That single argument is the whole proof, and it is exactly why the algorithm breaks if you allow negative edges.

### Edge case — an unreachable node

Add an island: a node `Z` with no edges to the rest. Run from A:

```
Round after round, A's component gets settled. Eventually the only unsettled
node is Z, whose distance is still inf. The selection step picks Z, sees its
distance is infinity, and stops:

  remaining nodes are unreachable; stopping
  distance[Z] = inf   ->  path A .. Z = (unreachable)
```

Infinity is not a bug here. It is the honest answer: there is no path. The code checks for exactly this and stops instead of looping forever.

---

## ELI5

Imagine you want the shortest walk from your house to every other house on a big map of streets.

The slow way is to draw every possible path and measure them all. There are so many paths that you would never finish.

Dijkstra found a shortcut rule. Start at your house. Always walk to the nearest house you have not finished yet, and write down how far it is. Once you finish a house, you never have to check it again, because you always did the closest one first, so nothing could be shorter.

You do that one house at a time until every house has a number. That is the shortest distance to each one. No guessing, no going back.

---

## ELI10

In the 1950s, computers were new and there was no settled way to ask one for the shortest route between two points. You could try every possible path and compare them, but the number of paths blows up so fast that even a small map is hopeless. People needed a smarter rule.

Edsger Dijkstra, a Dutch programmer, worked one out in 1956. The story he told is that he came up with it in about twenty minutes while sitting at a cafe terrace in Amsterdam with his fiancee, no pencil and no paper. He published it three years later in a three-page note. The rule is greedy and simple: keep a best-known distance to every place, start at zero for where you are and infinity for everywhere else, then always expand the closest place you have not finished. When you finish a place its distance is locked in forever, because you always pick the closest one and the roads never have negative length, so nothing cheaper can turn up later. Do that until every place has a number.

That algorithm is why your phone can route you across a city in a fraction of a second. But shortest paths were only one of Dijkstra's ideas, and maybe not even his biggest. He also argued that the way people wrote programs was a mess, full of `goto` jumps that turned code into tangled spaghetti nobody could follow. In 1968 he wrote a famous short letter, "Go To Statement Considered Harmful," and helped start what became structured programming: build programs out of clean, nested pieces (if-then-else, loops) so you can actually reason about whether they are correct. He also invented the semaphore, a tiny counter that lets multiple programs share a computer without stepping on each other.

The thread running through all of it was an attitude, not just a trick. Dijkstra insisted that a program should be composed carefully so it is correct by design, not hacked together and then debugged until it stops crashing. His Turing Award citation calls out his style: treating programming as a high intellectual challenge. He liked to say that testing can show the presence of bugs but never their absence. The only way to trust a program is to be able to reason about it.

---

## CS Graduate Level — The Shortest Path, and Programming as Reasoning

Dijkstra's Turing Award is unusual in that it honors a body of work and a *style* rather than a single result. This writeup takes the algorithm the code implements as the anchor, then covers the two other pillars named in the citation: structured programming and concurrency.

### 1. The Shortest Path Algorithm (1959)

**State of the art before.** Graph problems were studied in operations research, but there was no clean, provably-correct, low-degree-polynomial method for single-source shortest paths that a programmer could just implement. Brute-force path enumeration is exponential. The alternatives were ad hoc.

**What was new.** Dijkstra's "A Note on Two Problems in Connexion with Graphs" (1959) gave a greedy algorithm that solves single-source shortest paths in polynomial time. It maintains a set of *settled* nodes (final distances) and *tentative* distances to the rest. The invariant is the whole thing:

> At every step, for each settled node the recorded distance is the true shortest-path distance; for each unsettled node it is the shortest distance using only settled nodes as intermediates.

**How it works.** Repeatedly pick the unsettled node `u` with minimum tentative distance, settle it, and relax each outgoing edge `(u, v)`:

```python
if distance[u] + length(u, v) < distance[v]:
    distance[v] = distance[u] + length(u, v)
    previous[v] = u
```

**Why it is correct** rests entirely on **non-negative edge weights**. When `u` is selected it has the minimum tentative distance among unsettled nodes. Any alternative path to `u` must exit the settled region through some other unsettled node `w`, where `distance[w] >= distance[u]`, and then accumulate more non-negative length. So no shorter path to `u` can exist, and settling `u` is safe. Introduce a negative edge and this argument collapses — that is why Bellman–Ford (which relaxes all edges V−1 times) exists for the negative-weight case.

**Complexity.** The cost is dominated by "find the minimum tentative distance." The version in `implementation.py` does a linear scan, faithful to the 1959 note, giving `O(V^2)` — optimal for dense graphs. Replace the scan with a binary heap (`heapq`) and you get `O((V + E) log V)`, the textbook form. A Fibonacci heap brings it to `O(E + V log V)` in theory. The code marks exactly where the heap would slot in.

**What descended from it.** Dijkstra's algorithm is the backbone of network routing (link-state protocols like OSPF and IS-IS run it), GPS and map routing (usually as A*, which is Dijkstra plus an admissible heuristic to steer the search), and countless graph problems reduced to shortest paths. It is one of the most-implemented algorithms in existence.

### 2. Structured Programming and "Go To Statement Considered Harmful" (1968)

**State of the art before.** Early code jumped around freely with `goto`. Control could leap anywhere, so the static text of a program told you little about its dynamic behavior. Reasoning about correctness was nearly impossible because you could not point at a line and say what was true when execution reached it.

**What was new.** In a one-page letter to *Communications of the ACM* (the title was supplied by editor Niklaus Wirth), Dijkstra argued that unrestricted `goto` should be abolished in favor of a small set of composable control structures: sequence, selection (`if/then/else`), and iteration (`while`). The technical argument is about the gap between a program's static text and its dynamic progress. With structured constructs, you can describe "where execution is" with a small, well-defined coordinate (a point in the text plus a few loop counters). With arbitrary `goto`, that coordinate can be anywhere, so you cannot attach a meaningful invariant to a point in the code.

**How it connects to correctness.** Structured control flow is what makes program proof tractable. Each construct has a clean rule: a loop is understood through its invariant, a conditional through its two branches. This line runs directly into Hoare logic (1969) and into Dijkstra's own later work on **guarded commands** and the **weakest precondition calculus** (1975), a formal system for deriving a program together with its proof of correctness, rather than writing code and testing afterward. His slogan: "Program testing can be used to show the presence of bugs, but never to show their absence."

**What descended from it.** Every mainstream language today is structured; raw `goto` is either absent or discouraged. The deeper legacy is the idea that a program should be *designed to be reasoned about* — the ancestor of static analysis, type systems as lightweight proofs, and formal verification.

### 3. Concurrency: Semaphores and Cooperating Sequential Processes (1965–1968)

**State of the art before.** When multiple processes share resources, naive interleaving corrupts data (race conditions) or freezes (deadlock). There was no clean primitive for coordination.

**What was new.** Dijkstra introduced the **semaphore**: an integer with two atomic operations, `P` (wait/decrement, block if it would go negative) and `V` (signal/increment). A semaphore initialized to 1 is a mutex enforcing mutual exclusion; initialized to N it caps concurrent access to N resources. He framed the general setting as **cooperating sequential processes** and posed the enduring teaching problems: the **dining philosophers** (deadlock and resource ordering) and, earlier, a solution to the mutual-exclusion problem (1965). He also coined "deadly embrace," now called deadlock.

**Where it ran.** The **THE multiprogramming system** (1968) put these ideas into a real OS, built as a strict hierarchy of layers, each providing a clean abstraction to the one above (level 0: processor allocation and semaphores; higher levels: memory, console, I/O, user programs). Layered OS design and the idea of a semaphore-synchronized process hierarchy both start here.

**What descended from it.** Semaphores are still in every operating systems textbook and every kernel. Mutexes, condition variables, and monitors are refinements of the same idea. The layered-abstraction approach to building systems is now simply how systems are built.

### 4. Lasting Impact

The through-line is Dijkstra's conviction that programming is a mathematical discipline and that elegance and correctness are the same pursuit. The shortest-path algorithm is the crowd-pleaser, but the citation is right to lead with style: composing programs to be correct by construction, distrusting testing as a proof of correctness, and insisting that we should be able to *reason* about what we build. That stance shaped how we teach programming, how we design languages and operating systems, and the entire modern project of formal methods and verified software.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [A Note on Two Problems in Connexion with Graphs](https://doi.org/10.1007/BF01386390) *(the shortest path algorithm)* | Numerische Mathematik 1, 269–271 | 1959 |
| [Solution of a Problem in Concurrent Programming Control](https://doi.org/10.1145/365559.365617) *(mutual exclusion)* | Communications of the ACM | 1965 |
| [Cooperating Sequential Processes](https://doi.org/10.1007/978-1-4757-3472-0_2) *(semaphores, dining philosophers)* | EWD123 (reprinted, orig. 1968) | 1968 |
| [Go To Statement Considered Harmful](https://doi.org/10.1145/362929.362947) | Communications of the ACM | 1968 |
| [The Structure of the "THE"-Multiprogramming System](https://doi.org/10.1145/363095.363143) | Communications of the ACM | 1968 |
| [The Humble Programmer](https://doi.org/10.1145/355604.361591) *(Turing Award lecture)* | Communications of the ACM | 1972 |
| [Guarded Commands, Nondeterminacy and Formal Derivation of Programs](https://doi.org/10.1145/360933.360975) | Communications of the ACM | 1975 |
| [Self-stabilizing Systems in Spite of Distributed Control](https://doi.org/10.1145/361179.361202) | Communications of the ACM | 1974 |

---

*Previous: [Week 06 — John McCarthy (1971)](../06-john-mccarthy-1971/)*

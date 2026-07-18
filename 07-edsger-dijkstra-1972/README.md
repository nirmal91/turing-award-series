# Week 07 — Edsger W. Dijkstra (1972)

**ACM Turing Award citation:** *"The working vocabulary of programmers everywhere is studded with words originated or forcefully promulgated by E. W. Dijkstra — display, deadly embrace, semaphore, go-to-less programming, structured programming. But his influence on programming is more pervasive than any glossary can possibly indicate. The precious gift that this Turing Award acknowledges is Dijkstra's style: his approach to programming as a high, intellectual challenge; his eloquent insistence and practical demonstration that programs should be composed correctly, not just debugged into correctness; and his illuminating perception of problems at the foundations of program design."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — Dijkstra's shortest path in about 60 lines: grow outward from the start, always settle the nearest unsettled node next, and its distance is final. No priority queue, no path reconstruction, just the greedy loop.

[`implementation.py`](./implementation.py) — the full algorithm: a binary-heap priority queue so finding the nearest node is fast, path reconstruction (not just distances), directed and undirected edges, a graph-file loader, a REPL, a 17-case test suite, and a verbose trace that prints every settle and every relax.

```
graph + start
    ↓ init          distance[start] = 0, everything else = infinity
    ↓ heap          push (0, start) onto a min-heap
    ↓ pop nearest   take the smallest-distance unsettled node
    ↓ settle        its distance is now final
    ↓ relax edges   for each neighbour, is going through here cheaper?
    ↓ repeat        until the heap is empty
    ↓
  distance[] and previous[]  →  reconstruct any shortest path
```

What it supports:
- Shortest distances from a start node to every other node
- Shortest path reconstruction between any two nodes
- Undirected edges (`edge A B 7`) and one-way directed edges (`dedge A B 7`)
- Loading a graph from a plain text file and running its queries
- A REPL to build a graph by hand and query it
- A verbose mode that shows the frontier growing one node at a time

```bash
python3 concept.py                  # the core idea, plain
python3 implementation.py           # interactive REPL (starts on the demo map)
python3 implementation.py roads.graph   # load a graph file and run its queries
python3 implementation.py --test    # test suite (17 cases)
python3 implementation.py --verbose # REPL that traces every step
```

Example session:

```
dijkstra> path A E
A -> C -> F -> E   (distance 20)
dijkstra> from A
shortest distance from A:
  A: 0
  B: 7
  C: 9
  D: 20
  E: 20
  F: 11
```

The path to F is the interesting one. There is a direct road A→F of length 14, but the algorithm never takes it. Going A→C→F is 9 + 2 = 11, which is shorter. Dijkstra's greedy rule finds that without ever comparing whole routes.

---

## Full Worked Example

The claim is that you can find the shortest distance to every node by only ever looking at one node at a time, the nearest one you have not finished with. Here is the algorithm running on the demo map by hand.

### Step 0 — The map and the setup

The map is undirected. Each edge has a length:

```
A—B 7    A—C 9    A—F 14
B—C 10   B—D 15
C—D 11   C—F 2
D—E 6    E—F 9
```

Set the distance to the start to 0 and every other distance to infinity, meaning "not reached yet." Keep a set of **settled** nodes (distance is final) which starts empty. Start from A.

```
distance = { A:0, B:∞, C:∞, D:∞, E:∞, F:∞ }
settled  = { }
```

### The one rule

Repeat: pick the unsettled node with the smallest distance, settle it, then **relax** each of its edges. Relaxing edge `current → neighbour` means: if `distance[current] + edge_length` is smaller than the neighbour's current distance, we found a shorter way in, so update it.

Why is the settled distance final? Because every edge length is non-negative. The nearest unsettled node cannot be reached more cheaply by first going somewhere farther and coming back, since coming back only adds length. So the first time you settle a node, you are done with it.

### Step 1 — Settle A (distance 0)

A is the only node with a finite distance, so it is the nearest. Settle it, relax its three edges:

```
A→B: 0 + 7  = 7   < ∞   update B = 7
A→C: 0 + 9  = 9   < ∞   update C = 9
A→F: 0 + 14 = 14  < ∞   update F = 14

distance = { A:0, B:7, C:9, D:∞, E:∞, F:14 }   settled = {A}
```

### Step 2 — Settle B (distance 7)

Among unsettled nodes {B:7, C:9, F:14}, B is nearest. Settle it, relax:

```
B→C: 7 + 10 = 17   not < 9    leave C = 9
B→D: 7 + 15 = 22   < ∞        update D = 22

distance = { A:0, B:7, C:9, D:22, E:∞, F:14 }   settled = {A,B}
```

### Step 3 — Settle C (distance 9)

Nearest unsettled is C:9. This is where the direct road to F gets beaten:

```
C→D: 9 + 11 = 20   < 22   update D = 20   (better than going through B)
C→F: 9 + 2  = 11   < 14   update F = 11   (better than the direct A→F of 14)

distance = { A:0, B:7, C:9, D:20, E:∞, F:11 }   settled = {A,B,C}
```

### Step 4 — Settle F (distance 11)

Now F:11 is the nearest unsettled node, not D:20. Settle F, relax:

```
F→E: 11 + 9 = 20   < ∞   update E = 20

distance = { A:0, B:7, C:9, D:20, E:20, F:11 }   settled = {A,B,C,F}
```

### Step 5 and 6 — Settle D (20), then E (20)

D and E are both at 20. Settle D first, relax `D→E: 20 + 6 = 26`, which is not less than 20, so E stays. Then settle E. Nothing left to update.

```
distance = { A:0, B:7, C:9, D:20, E:20, F:11 }   settled = {A,B,C,F,D,E}
```

Done. These are the final shortest distances. This matches `python3 implementation.py --verbose` exactly.

### Reconstructing a path

Distances alone do not tell you the route. So alongside `distance`, keep `previous[node]` = the node you arrived from when you last improved it. From the run above:

```
previous = { B:A, C:A, D:C, E:F, F:C }
```

To get the path to E, walk backward: E came from F, F came from C, C came from A. Reverse it: **A → C → F → E**, distance 20.

### Edge case — an unreachable node

Give the graph an island node Z with no edges, and ask for the distance from A:

```
distance[Z] = ∞    (never relaxed, never settled with a finite value)
```

The algorithm settles everything reachable, the heap empties, and Z is left at infinity. `path A Z` returns "no path." Same thing happens with a **directed** edge X→Y: you can reach Y from X, but asking `from Y` leaves X at infinity, because the one-way road does not go back. The tests cover both.

---

## ELI5

Imagine you are at your house and you want to know the shortest walk to every friend's house in the neighborhood.

The slow way is to draw every possible walk on paper and measure them all. There are way too many. You would be there all day.

Dijkstra found a faster way. Start at your house. Look at the closest place you can walk to and go there first. Now you know for sure that is the shortest way to that place, because everything else is farther away. Cross it off. Then look at the next closest place you have not crossed off, and do the same thing.

You keep grabbing the nearest place you have not finished with, one at a time. When you have crossed off everyone, you know the shortest walk to every friend, and you never had to draw a single whole route.

---

## ELI10

In the 1950s computers were new and expensive, and people wanted to show what they could do. In 1956 Edsger Dijkstra, a young Dutch programmer, needed a demo for a computer called the ARMAC. He picked a question anyone could understand: what is the shortest way to drive between two cities in the Netherlands? He worked out the answer in about twenty minutes, sitting at a cafe in Amsterdam with a cup of coffee and no pen or paper. He published it three years later in a paper that was only three pages long.

The obvious way to find the shortest route is to check all the routes and pick the smallest. The problem is that the number of routes explodes. Even a small map has more routes than a computer of that era could ever check. Dijkstra's trick was to never look at a whole route. Instead you grow outward from your start city. You always travel next to the nearest city you have not finished with, mark down its shortest distance as final, and update its neighbors. Because roads never have negative length, the nearest unfinished city can never be reached by some cleverer longer detour, so the first time you reach it, you are done with it.

That single idea is now everywhere. It is the algorithm inside every map app when it plans a route, inside the internet when it decides how to send your data, and inside games when a character finds its way around a wall. Your phone runs a descendant of a twenty-minute idea from a coffee shop in 1956.

Dijkstra spent the rest of his career on a bigger campaign. He believed programs should be built to be correct from the start, reasoned about like mathematics, not just poked at until the bugs stop showing up. In 1968 he wrote a famous short letter arguing that the `goto` jump, which let a program leap anywhere and made code impossible to follow, should mostly be abandoned. The editor gave it the title "Go To Statement Considered Harmful." It caused an uproar and it won. The clean, nested `if` and `while` blocks you write today are the world Dijkstra argued us into.

---

## CS Graduate Level — Greedy Shortest Paths, and Programs You Can Reason About

Dijkstra's Turing Award is unusual in that it is not for a single artifact. It is for a body of work and, more than that, for a stance: that programming is a rigorous intellectual discipline and that correctness should be established by reasoning, not discovered by testing. Three threads carry most of the weight.

### 1. The Shortest Path Algorithm (1959)

**Before.** Finding a shortest path was understood as a search over paths. The naive formulation is exponential: a graph with many routes between two nodes has exponentially many simple paths, and enumerating them is hopeless. There were dynamic-programming style ideas forming (Bellman–Ford came around the same period, 1958), but Dijkstra's was the clean greedy solution for the non-negative-weight case, and he arrived at it independently and early.

**What was new.** The key structural insight is an invariant. Maintain a set `S` of *settled* nodes whose shortest distance from the source is known to be final, and a tentative distance `d[v]` for everything else. The claim is:

> When you pick the unsettled node `u` with the smallest tentative distance and add it to `S`, `d[u]` is already the true shortest distance to `u`.

The proof is a one-line contradiction that leans entirely on non-negative edge weights. Suppose some shorter path to `u` existed. It must leave `S` at some point, crossing to a first unsettled node `w`. But `d[w] >= d[u]` (we chose `u` as the smallest), and the rest of the path from `w` to `u` only adds non-negative length. So that path is at least `d[u]` long, a contradiction. This is why Dijkstra's algorithm **fails on negative edges**: the "coming back is only more expensive" assumption breaks, and you need Bellman–Ford instead.

**How it works.** Two operations, repeated:

```python
u = the unsettled node with minimum d[u]     # "settle the nearest"
settle u
for (u, v) with weight w:                    # "relax its edges"
    if d[u] + w < d[v]:
        d[v] = d[u] + w
        previous[v] = u
```

Dijkstra's original description used a linear scan to find the minimum, giving `O(V^2)`, which is optimal for dense graphs. The version in `implementation.py` uses a binary heap as the priority queue, giving `O((V + E) log V)`, which is the standard choice for sparse graphs like road networks. A subtlety the code handles: when you relax `v` to a smaller distance you push a new `(distance, v)` onto the heap rather than decreasing a key in place, so a node can sit on the heap multiple times. The `if v in settled: continue` guard discards the stale copies. With a Fibonacci heap the bound improves to `O(E + V log V)` (Fredman and Tarjan, 1984), which matters in theory more than in practice.

**What descended from it.** Dijkstra is the backbone of shortest-path computation: OSPF and IS-IS routing protocols run it to build the internet's forwarding tables; A* search (Hart, Nilsson, Raphael, 1968) is Dijkstra plus an admissible heuristic and is the standard for game and robot pathfinding; contraction hierarchies and ALT preprocess road networks so that continent-scale queries return in microseconds, but the query engine underneath is still Dijkstra.

### 2. Structured Programming (1968)

**Before.** Programs were written with `goto`. Control could jump anywhere, so understanding a program meant tracing arbitrary tangles of jumps. Dijkstra's 1968 letter to *Communications of the ACM*, titled by editor Niklaus Wirth as "Go To Statement Considered Harmful," argued that unrestricted `goto` makes it impossibly hard to describe the *state* of a running program at a given point, and therefore hard to reason about. His constructive claim, developed in "Notes on Structured Programming" (1972), was that all algorithms can be composed from three control structures: **sequence, selection (`if`/`else`), and iteration (`while`)**.

**Why it holds up.** The Böhm–Jacopini theorem (1966) had already proven that these three suffice to express any computable function, giving the movement a formal footing. The deeper point was not expressiveness but *reasoning*: with only nested single-entry, single-exit blocks, you can attach an assertion to each point in the program and verify it locally, because control flows through the text in a way you can follow. This is the birth of the discipline that became Hoare logic and, eventually, everything from `assert` statements to modern static analyzers. The `goto`-free, block-structured code you write in every mainstream language is the settled outcome of this argument.

### 3. Concurrency: Semaphores, "THE," and Deadlock (1965–1968)

**Before.** When several processes share a computer, they interfere. Two processes updating the same variable can interleave and corrupt it (a race), and there was no clean primitive for coordinating them. Dijkstra's work on the **THE multiprogramming system** at Eindhoven forced the issue.

**What was new.** The **semaphore**: an integer with two atomic operations, `P` (from Dutch *proberen*, "to test": wait until positive, then decrement) and `V` (*verhogen*, "to increment": increment and possibly wake a waiter). A binary semaphore gives mutual exclusion; a counting semaphore controls access to N identical resources. This is the foundation every later synchronization primitive builds on — mutexes, condition variables, monitors. Dijkstra also framed **deadlock** (his "deadly embrace"): a set of processes each holding a resource and waiting for one another. His **Banker's algorithm** avoids it by only granting a request if the system can still reach a state where every process can finish. His **dining philosophers** problem (1965) is still the standard teaching example for resource contention. THE itself was one of the first systems designed as a hierarchy of layers, each providing a clean abstract machine to the layer above, an idea that runs straight through to how we structure operating systems today.

### 4. Correctness by Construction (1975–1976)

The thread tying it all together is Dijkstra's insistence that you should *derive* a correct program from its specification rather than write one and test it. In *A Discipline of Programming* (1976) he introduced **guarded commands** and the **weakest precondition** predicate transformer `wp(S, R)`: the weakest condition on the input state such that statement `S` is guaranteed to terminate in a state satisfying `R`. Programming becomes an exercise in calculating `wp` backward from the desired postcondition, so the proof and the program grow together. His famous line, "Program testing can be used to show the presence of bugs, but never to show their absence," is the compressed form of this whole philosophy, and it is the intellectual ancestor of formal verification, model checking, and the correctness proofs behind systems like the seL4 kernel and CompCert compiler.

### 5. Lasting Impact

Dijkstra changed both *what* we compute and *how* we think about computing. The shortest-path algorithm is a piece of working infrastructure you use dozens of times a day without knowing it. Structured programming is so thoroughly won that its central claim now sounds like a truism. Semaphores and deadlock are the vocabulary of every concurrent system. And the stance underneath all of it — that a program is a mathematical object you can and should reason about — is why software verification exists as a field. The Turing citation gets it exactly right: the gift is the *style*, the demand that programs be composed correctly rather than debugged into correctness.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [A Note on Two Problems in Connexion with Graphs](https://doi.org/10.1007/BF01386390) *(the shortest path algorithm)* | Numerische Mathematik | 1959 |
| [Solution of a Problem in Concurrent Programming Control](https://doi.org/10.1145/365559.365617) *(mutual exclusion)* | Communications of the ACM | 1965 |
| [Go To Statement Considered Harmful](https://doi.org/10.1145/362929.362947) | Communications of the ACM | 1968 |
| [The Structure of the "THE"-Multiprogramming System](https://doi.org/10.1145/363095.363143) *(semaphores, layered OS)* | Communications of the ACM | 1968 |
| [Notes on Structured Programming](https://www.cs.utexas.edu/~EWD/ewd02xx/EWD249.PDF) *(EWD249, later in the book Structured Programming)* | Academic Press (book) | 1972 |
| [Self-stabilizing Systems in Spite of Distributed Control](https://doi.org/10.1145/361179.361202) | Communications of the ACM | 1974 |
| [Guarded Commands, Nondeterminacy and Formal Derivation of Programs](https://doi.org/10.1145/360933.360975) | Communications of the ACM | 1975 |
| [A Discipline of Programming](https://www.pearson.com/en-us/subject-catalog/p/discipline-of-programming/P200000003348) *(book — weakest preconditions)* | Prentice Hall | 1976 |
| [The Humble Programmer](https://doi.org/10.1145/355604.361591) *(Turing Award lecture)* | Communications of the ACM | 1972 |

---

*Previous: [Week 06 — John McCarthy (1971)](../06-john-mccarthy-1971/)*

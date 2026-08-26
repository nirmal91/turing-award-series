# Week 07 — Edsger W. Dijkstra (1972)

**ACM Turing Award citation:** *"The working vocabulary of programmers everywhere is studded with words originated or forcefully promulgated by E. W. Dijkstra — display, deadly embrace, semaphore, go-to-less programming, structured programming. But his influence on programming is more pervasive than any glossary can possibly indicate. The precious gift that this Turing Award acknowledges is Dijkstra's style: his approach to programming as a high, intellectual challenge; his eloquent insistence and practical demonstration that programs should be composed correctly, not just debugged into correctness; and his illuminating perception of problems at the foundations of program design."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — Dijkstra's shortest path algorithm in about 60 lines: grow a set of "finished" nodes outward from the start, always finishing the nearest unfinished one next, and every other node's distance only ever gets cheaper as its neighbors finish.

[`implementation.py`](./implementation.py) — a full working version: a `Graph` you build by hand or load from a file, the algorithm with a step-by-step verbose mode, shortest-path reconstruction, and a REPL.

```
graph (nodes + weighted edges)
    ↓ pick               the unfinished node nearest to start
    ↓ finish it           its distance is now locked in, forever
    ↓ relax its edges     does going through it shorten any neighbor's distance?
    ↓ repeat              until every reachable node is finished
    ↓
distance table + shortest-path tree
```

What it supports:
- Directed or undirected weighted edges, built one at a time or loaded from a `.graph` file
- Step-by-step `verbose` mode that prints which node was finished, which edges relaxed, and why
- Shortest-path reconstruction (not just the distance — the actual route)
- A REPL, a 16-case test suite, and a scratch file (`practice.graph`) to build your own graph

```bash
python3 concept.py                          # the core idea, plain
python3 implementation.py                   # interactive REPL
python3 implementation.py practice.graph    # load and run a graph file
python3 implementation.py --test            # test suite (16 cases)
python3 implementation.py --verbose network.graph  # step-by-step run
```

Example session:

```
graph> edge A B 4
added A -> B (4)
graph> edge A C 2
added A -> C (2)
graph> edge C B 1
added C -> B (1)
graph> edge B D 5
added B -> D (5)
graph> edge C D 8
added C -> D (8)
graph> edge C E 10
added C -> E (10)
graph> edge D E 2
added D -> E (2)
graph> path A E
distance: 10
route:    A -> C -> B -> D -> E
```

The direct edge `A -> B` costs 4. But going `A -> C -> B` costs `2 + 1 = 3`. The algorithm never guesses at routes — it never even looks at "A to E" as a route at all. It finishes A, then C, then B, then D, then E, one at a time, nearest first, and the shortest distance to E falls out at the end because every node it passed through on the way had already been locked in as optimal.

---

## Full Worked Example

Same graph as above, walked by hand. Distances start at `0` for the source and `∞` (infinite, unknown) everywhere else. A node is **unfinished** until the algorithm locks in its distance for good.

```
A --4--> B          A --2--> C
B --5--> D          C --1--> B
C --8--> D          C --10-> E
D --2--> E
```

### Step 0 — Setup

```
distance = { A: 0, B: ∞, C: ∞, D: ∞, E: ∞ }
unfinished = { A, B, C, D, E }
```

### Step 1 — Finish A (distance 0)

A is the only node with a known distance, so it's nearest. Finish it, remove it from `unfinished`, then **relax** its outgoing edges — check whether going through A beats what's currently known for each neighbor:

```
A -> B: 0 + 4 = 4    beats ∞     -> distance[B] = 4, previous[B] = A
A -> C: 0 + 2 = 2    beats ∞     -> distance[C] = 2, previous[C] = A

distance = { A: 0, B: 4, C: 2, D: ∞, E: ∞ }
```

### Step 2 — Finish C (distance 2)

Of the unfinished nodes `{B: 4, C: 2, D: ∞, E: ∞}`, C is nearest. Finish it, relax its edges:

```
C -> B: 2 + 1 = 3    beats 4     -> distance[B] = 3, previous[B] = C
C -> D: 2 + 8 = 10   beats ∞     -> distance[D] = 10, previous[D] = C
C -> E: 2 + 10 = 12  beats ∞     -> distance[E] = 12, previous[E] = C

distance = { A: 0, B: 3, C: 2, D: 10, E: 12 }
```

B's distance just dropped from 4 to 3. This is the whole point: B looked settled after step 1, but it wasn't finished, so it stayed open to correction.

### Step 3 — Finish B (distance 3)

Nearest unfinished node is now B (3), beating D (10) and E (12). Finish it, relax:

```
B -> D: 3 + 5 = 8    beats 10    -> distance[D] = 8, previous[D] = B

distance = { A: 0, B: 3, C: 2, D: 8, E: 12 }
```

### Step 4 — Finish D (distance 8)

```
D -> E: 8 + 2 = 10   beats 12    -> distance[E] = 10, previous[E] = D

distance = { A: 0, B: 3, C: 2, D: 8, E: 10 }
```

### Step 5 — Finish E (distance 10)

E has no outgoing edges. Nothing to relax. `unfinished` is now empty. Done.

### Reading off the route

`previous` traces backward from E: `E ← D ← B ← C ← A`. Reversed: **A → C → B → D → E**, total distance **10**. Notice B's edge is never used directly — B was reached cheaper through C than through A, and that only became visible once C finished.

### Why "finish nearest first" is actually safe

Every edge weight here is non-negative. That means once a node is finished, no path through a still-unfinished node could ever beat it — every unfinished node already has a distance *at least* as large as the one just finished, and adding more edges (which only add non-negative length) can't shrink a path. That single guarantee is what lets the algorithm skip ever comparing full routes.

### Edge case 1 — an unreachable node

Add a node `Z` with no edges to or from anything else. `unfinished` still contains `Z` after every reachable node is finished. The loop's "pick nearest unfinished" step finds `distance[Z] = ∞` and every other candidate already removed, so it just stops:

```
distance[Z] = ∞  →  format_distance prints "unreachable"
path_to(previous, A, Z) → None   (Z is not a key in previous at all)
```

### Edge case 2 — why negative weights break it

Suppose `A -> B` costs `5` directly, but `A -> C` costs `2` and `C -> B` costs `-10` (Dijkstra's algorithm is not built for negative weights, and here's the failure in numbers):

```
Step 1: finish A.       relax: distance[B] = 5, distance[C] = 2
Step 2: nearest unfinished is C (2). finish C.  relax: A->C->B = 2 + (-10) = -8, beats 5
                                                  distance[B] = -8
```

That happens to work out here only because C finished *before* B. Flip the edge weights slightly (say `A -> C` costs `20` instead of `2`) and C would still be unfinished when B gets finished at distance `5` — and once B is finished, the algorithm never revisits it, so it would report `5` and miss the true shortest distance of `-8`. "Finish nearest first, never revisit" is only a valid strategy when every edge is non-negative. This repo's `implementation.py` does not check for negative weights — feeding it one will silently produce a wrong answer, which is the historically accurate behavior: the fix (Bellman-Ford, which allows negative weights but is slower) is a different algorithm entirely, not a patch on this one.

---

## ELI5

Say there are 5 towns: A, B, C, D, E. Some roads connect them, and each road has a number on it for how long it takes. You start in town A and want to know the fastest way to every other town.

The old way: you'd walk down every possible chain of roads from A to E, add up the numbers on each chain, and keep the smallest total. One chain is A then B then D then E. Another is A then C then D then E. Another is A then C then B then D then E. You have to try all of them and you're never sure you found every chain there is.

Dijkstra's way: from A, you look at the two roads out of it, to B (takes 4) and to C (takes 2). C is closer, so you go there first and you're done thinking about C forever, its fastest time from A is locked in at 2. Now from C you see a road to B that only takes 1 more, so the fastest way to B turns out to be through C (2 + 1 = 3), not the direct road (4). You keep doing that, always finishing whichever town is currently closest, and every town's fastest time locks in one at a time until you've done all five. You never had to list a single whole chain of roads. You just kept finishing the nearest unfinished town, and the fastest way everywhere fell out on its own.

---

## ELI10

In 1959, Edsger Dijkstra was a 29-year-old programmer in Amsterdam trying to think of something impressive to demonstrate on a brand new computer called the ARMAC. He wanted a problem anyone in the audience could understand, not just programmers. So he picked: given a map of 64 cities in the Netherlands, what's the shortest route between any two of them?

At the time, "find the shortest path" meant something close to trial and error. You'd list out candidate routes, add up their distances, and keep the best one you'd found so far. There was no rule for knowing when to stop, and no bound on how many routes there might be to check. Dijkstra worked out a completely different approach in about twenty minutes, without pencil or paper, sitting at a cafe with his fiancee. Instead of building and comparing whole routes, his algorithm grows a "finished" region outward from the starting city one city at a time, always finishing whichever unfinished city is currently nearest. Once a city is finished, its distance can never get better, so the algorithm never has to look at it again.

That one rule, finish the nearest unfinished node next, turns an exponential search problem into something you can compute in well under a second, even for a real road network. It's why "A note on two problems in connexion with graphs," a paper barely three pages long, became one of the most cited papers in computer science.

Dijkstra spent the rest of his career on a related worry: if a simple idea like this could get so many programs written wrong, sloppy, unreadable spaghetti of jumps and detours, what would it take to write programs you could actually trust? That question is what the 1972 Turing Award was really for, and it's the reason "structured programming" and "go-to statement considered harmful" are on the same trophy as the shortest path algorithm this chapter's code demonstrates.

---

## CS Graduate Level

### 1. The State of the Art Before

By the late 1950s, graph search for shortest paths generally meant enumeration: generate candidate paths (often via brute-force or basic branch-and-bound), sum their edge weights, and retain the minimum. Nothing bounded how much work this took relative to the size of the graph, and there was no proof that a given "current best" route was actually optimal until every alternative had been ruled out.

Separately, and more consequentially for his Turing Award, mainstream programming in FORTRAN and assembly relied heavily on unrestricted `goto` to express loops, conditionals, and error handling. A program's control flow could jump anywhere, which meant the "state" of a running program (which statement is executing, and how you got there) could not be reasoned about locally. Understanding what a program did required tracing jumps by hand across the whole listing. Debugging was largely empirical: run it, see what broke, patch it.

### 2. The Shortest Path Algorithm

Given a graph with non-negative edge weights and a source node, Dijkstra's algorithm maintains a `distance` estimate for every node (initialized to `0` for the source, `∞` elsewhere) and repeatedly:

1. Selects the unfinished node with the smallest `distance`.
2. Marks it finished — its `distance` is now provably optimal.
3. **Relaxes** its outgoing edges: for each neighbor, checks whether `distance[current] + weight` improves `distance[neighbor]`.

The correctness argument is an induction on the order nodes are finished: when a node `u` is selected, every unfinished node already has `distance ≥ distance[u]` (that's why `u` was selected), and every edge weight is `≥ 0`, so no path through a still-unfinished node could possibly produce a shorter path to `u` than the one already found. This is precisely the property that fails under negative weights, worked through by hand in the Full Worked Example above.

The naive implementation here (linear scan for the minimum each step) is `O(V²)`. A binary heap for the "pick nearest unfinished" step brings it to `O((V + E) log V)`, and a Fibonacci heap to `O(E + V log V)` — the improvement Dijkstra's algorithm has received over sixty-plus years without changing its core idea.

### 3. Structured Programming and `goto`

Dijkstra's 1968 letter "Go To Statement Considered Harmful" (his own title was rejected by the CACM editor, who substituted this one) argued that the quality of a programmer's ability to reason about a program correlates inversely with the density of `goto` statements in it: with unrestricted jumps, the set of program states reachable at any point in the code is unbounded, so no local reasoning about a program's behavior is possible.

The Böhm–Jacopini theorem (1966) had already shown that any program built from arbitrary jumps can be rewritten using only three control structures: **sequence** (do this, then that), **selection** (if/else), and **iteration** (while/for) — each with a single entry and a single exit. **Structured programming**, formalized by Dijkstra with Ole-Johan Dahl and Tony Hoare in their 1972 book of that name, is the discipline of building programs exclusively out of those composable blocks, so that a program's correctness can be argued piece by piece rather than by tracing every possible jump.

### 4. Semaphores and Cooperating Sequential Processes

Dijkstra's other major line of work was concurrency, developed while building the THE multiprogramming system (1965–68), one of the earliest operating systems structured in explicit layers. Multiple processes sharing resources (memory, devices, data structures) can interleave in ways that corrupt shared state if two processes modify it at the same time — a **race condition**.

Dijkstra's solution was the **semaphore**: an integer with exactly two atomic operations, `P` (or `wait`, decrement, block if it would go negative) and `V` (or `signal`, increment, wake a blocked process). A semaphore initialized to 1 used to guard a critical section — `P` before entering, `V` after leaving — enforces **mutual exclusion**: only one process can be inside at a time. He also named a specific concurrency failure the **deadly embrace**: two or more processes each holding a resource the other needs, so both wait forever. It's now universally called deadlock.

### 5. What Descended From It

- **Routing.** Dijkstra's algorithm (or a variant) underlies OSPF and IS-IS, the link-state routing protocols that decide how packets move across the internet, and it's the backbone of every "shortest route" feature in mapping software.
- **Priority-queue algorithm design.** The "always process the globally cheapest unfinished option next" pattern generalizes to Prim's minimum spanning tree, A* search (Dijkstra plus a heuristic), and more broadly to greedy algorithms with an exchange-argument correctness proof.
- **Control flow in every modern language.** No mainstream language designed after the 1970s exposes unrestricted `goto` as its primary control construct. `if`/`while`/`for`/functions with single entry points are structured programming, so thoroughly won that most programmers have never had to think about the alternative.
- **Concurrency primitives.** Mutexes, condition variables, and the lock/unlock pattern in every threading library (POSIX threads, Java's `synchronized`, Python's `threading.Lock`) are semaphores with the count fixed at 1. Deadlock detection and avoidance in databases and operating systems is directly downstream of naming the "deadly embrace" as a problem worth solving formally.

### 6. Lasting Impact

Two very different threads run through Dijkstra's career, and both won on the same principle: prove things are correct instead of debugging until they look right. The shortest path algorithm proves optimality through an invariant, not exhaustive search. Structured programming makes a program's correctness arguable in pieces instead of by tracing arbitrary jumps. Semaphores make concurrent correctness provable via an invariant on a counter rather than by hoping interleavings behave. He rarely wrote a program to test whether it worked; he wrote it to be provably correct on paper first. That habit of demanding you be able to explain *why* code is right, not just that it happened to pass, is his real legacy, and it shows up every time a modern engineer reaches for a loop invariant, a type system, or a formal proof instead of a debugger.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [A Note on Two Problems in Connexion with Graphs](https://doi.org/10.1007/BF01386390) | Numerische Mathematik | 1959 |
| [Go To Statement Considered Harmful](https://doi.org/10.1145/362929.362947) | Communications of the ACM | 1968 |
| [The Structure of the "THE"-Multiprogramming System](https://doi.org/10.1145/363095.363143) | Communications of the ACM | 1968 |
| Cooperating Sequential Processes (EWD123) — in *Programming Languages*, F. Genuys (ed.) | Academic Press | 1968 |
| *Structured Programming* (with O-J. Dahl and C.A.R. Hoare) | Academic Press | 1972 |
| [The Humble Programmer](https://doi.org/10.1145/1283920.1283927) *(Turing Award lecture)* | Communications of the ACM | 1972 |

---

*Previous: [Week 06 — John McCarthy (1971)](../06-john-mccarthy-1971/)*

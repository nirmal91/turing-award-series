# Week 07 — Edsger W. Dijkstra (1972)

**ACM Turing Award citation:** *"Edsger Dijkstra was a principal contributor in the late 1950's to the development of the ALGOL, a high level programming language which has become a model of clarity and mathematical rigor. He is one of the principal exponents of the science and art of programming languages in general, and has greatly contributed to our understanding of their structure, representation, and implementation. His fifteen years of publications extend from theoretical articles on graph theory to basic manuals, expository texts, and philosophical contemplations in the field of programming languages."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — Dijkstra's shortest path in about 60 lines: start every node at infinity, settle the closest unsettled node, relax its neighbours, repeat. The whole algorithm and the one fact that makes it correct.

[`implementation.py`](./implementation.py) — a full working version: a graph you build edge by edge, single-source shortest paths, path reconstruction (the actual route, not just its length), a REPL to explore graphs by hand, a file loader, and a verbose mode that narrates every settle and relaxation.

```
edges (u, v, weight)
    ↓ build adjacency   node -> list of (neighbour, weight)
    ↓ initialise        start = 0, everything else = infinity
    ↓ settle + relax    pick the closest unsettled node, update its neighbours
    ↓ distances + predecessors
    ↓ reconstruct       walk predecessors backward to get the route
  shortest path
```

What it supports:
- Single-source shortest paths from any start node to every other node
- The actual route between two nodes, rebuilt from a predecessor chain
- Undirected edges (`edge`) and directed edges (`dedge`) in the same graph
- Non-negative integer and float weights; negative weights are rejected up front, because they break the algorithm
- A REPL, an 18-case test suite, and a verbose mode that prints every step

```bash
python3 concept.py                      # the core idea, plain
python3 implementation.py               # interactive REPL
python3 implementation.py roads.txt     # load a graph file and run its queries
python3 implementation.py --test        # test suite (18 cases)
python3 implementation.py --verbose      # REPL that narrates every step
```

Example session:

```
graph> edge A B 4
edge A--B (4)
graph> edge A C 2
graph> edge B C 1
graph> edge B D 5
graph> edge C D 8
graph> path A D
A -> C -> B -> D   (distance 8)
graph> dist A
  A -> A = 0
  A -> B = 3
  A -> C = 2
  A -> D = 8
```

The direct road from A to B is 4. But the route A → C → B is 2 + 1 = 3, so the shortest path to B does not use the A–B road at all. Dijkstra's algorithm finds that without ever enumerating routes.

---

## Full Worked Example

Here is `dijkstra` running on the road network above, by hand, step by step. Nothing is skipped.

### Step 0 — The network

Five two-way roads between four places:

```
        A
      /   \
   2 /     \ 4
    /       \
   C ---1--- B
    \       / \
   8 \     / 5  \
      \   /      (D reached from B at 5, from C at 8)
       \ /
        D
```

Written as weighted edges:

```
A–C = 2    C–B = 1    B–D = 5
A–B = 4    C–D = 8
```

We want the shortest distance from **A** to everywhere.

### Step 1 — Initialise

Every node starts at infinity except the start, which is 0. Nothing is settled yet.

```
distance:  A=0   B=inf   C=inf   D=inf
unsettled: {A, B, C, D}
```

### Step 2 — Settle A

The smallest tentative distance among unsettled nodes is A at 0. Settle it. A's distance is now final. Relax A's neighbours:

```
via A:  B = 0 + 4 = 4   (better than inf)  -> B = 4, came from A
        C = 0 + 2 = 2   (better than inf)  -> C = 2, came from A

distance:  A=0   B=4   C=2   D=inf
unsettled: {B, C, D}
```

### Step 3 — Settle C

Among {B, C, D} the smallest is C at 2. Settle it. Relax C's neighbours (A is already settled, so skip it):

```
via C:  B = 2 + 1 = 3   (better than 4)    -> B = 3, came from C
        D = 2 + 8 = 10  (better than inf)  -> D = 10, came from C

distance:  A=0   B=3   C=2   D=10
unsettled: {B, D}
```

This is the interesting step. B was 4 (straight from A). Going A → C → B is only 3, so B improves and now remembers it came from C, not A.

### Step 4 — Settle B

Between B=3 and D=10, the smallest is B at 3. Settle it. Relax B's neighbours (A and C are settled, skip them):

```
via B:  D = 3 + 5 = 8   (better than 10)   -> D = 8, came from B

distance:  A=0   B=3   C=2   D=8
unsettled: {D}
```

D improves from 10 (the direct C–D road) to 8 (the route through B).

### Step 5 — Settle D

Only D is left, at 8. Settle it. It has no unsettled neighbours. Done.

```
distance:  A=0   B=3   C=2   D=8   (all final)
```

### Step 6 — Reconstruct the route to D

Each node remembered who it came from. Walk that chain backward from D:

```
D came from B
B came from C
C came from A
A is the start
```

Reverse it: **A → C → B → D**, total distance **8**. The algorithm never listed all the paths from A to D. It settled four nodes in order of increasing distance and read the answer off the predecessor chain.

### Why the greedy step is safe

When we settled C at distance 2, we declared that number final without checking any other route to C. How can that be safe? Because every edge is non-negative. Any other path to C would have to leave A, reach some other unsettled node first (all of which are already at distance ≥ 2), and then travel further. It can only get longer. The closest unsettled node can never be improved by a detour through a farther one. That single observation is the whole correctness proof.

### Edge case — a negative edge would break it

Suppose there were a road C → B of weight −2. Once C is settled at 2, Dijkstra never revisits it. But A → C → B → (back toward C) could now form a cheaper route that the algorithm has already closed the door on. The greedy "settle and never look back" step depends on distances only ever growing. That is why `add_edge` raises an error on a negative weight instead of returning a wrong answer. (Graphs with negative edges need Bellman–Ford instead.)

### Edge case — an unreachable node

Add a node Z with no roads to it. It starts at infinity, and since nothing ever relaxes it, it stays at infinity. `path A Z` returns "no path". Infinity is not a bug here; it is the correct answer for "you cannot get there".

---

## ELI5

Imagine a treasure map with towns joined by roads, and each road has a number for how long it takes to walk.

Before, to find the fastest way from your town to the treasure, you would have to try every path, one by one. With lots of towns that is way too many to try.

Dijkstra found a smarter way. Stand in your town. Look at the towns you can reach and always walk to the closest one you have not visited yet. When you get there, write down how far it was. That number is now locked in and will never change. Then look at its neighbours and see if going through this new town is a shortcut to them.

Keep always stepping to the closest unvisited town. Because you never take a longer road when a shorter one exists, the first time you lock in a town's number, it is already the best. When you have visited every town, you know the fastest way to all of them.

---

## ELI10

In 1956 there were almost no algorithms with names. Computers were rare, slow, and mostly did arithmetic. Edsger Dijkstra, a young Dutch programmer, was asked to come up with a demonstration for a new computer called the ARMAC, something an ordinary audience could follow. He picked a question everyone understands: what is the shortest way to drive from one city to another? One morning, sitting at a cafe terrace in Amsterdam with a cup of coffee and no paper, he worked out the answer in about twenty minutes. He later said that because he had no pencil, he was forced to make it simple.

The idea is this. Give every city a running "best distance from home", starting at zero for home and infinity for everywhere else. Now repeat one move: among the cities you have not finalised, pick the one with the smallest running distance and finalise it. Then look at its road neighbours and check whether going through this city is a shortcut to them. If it is, lower their running distance. Keep going until every city is finalised. The trick that makes it work is that no road has a negative length, so the closest unfinished city can never be reached faster by a detour. The moment you finalise a city, its number is already the best it will ever be.

Dijkstra published this in 1959 in a three-page paper. It is now one of the most used algorithms in the world. Every time your phone maps a route, every time an internet packet finds its way across the network (protocols like OSPF run it), something very close to that cafe-terrace idea is running underneath. Not bad for twenty minutes without a pencil.

And shortest paths were only a corner of what he did. He spent the rest of his career arguing that programming is a serious intellectual craft, that you should reason your programs correct rather than debug them into working, and that simplicity is a hard-won achievement rather than a lack of ambition. A lot of how we are taught to write clean code traces back to him.

---

## CS Graduate Level — Shortest Paths, Structured Programming, and Programming as a Discipline

Dijkstra's Turing Award is unusual in how broad the underlying body of work is. The citation points at ALGOL and "the science and art of programming languages", but that undersells it. He produced a famous algorithm, a famous polemic, the core primitives of concurrency, a layered operating system, and a formal method for deriving correct programs. This section takes them in turn, with the shortest-path algorithm (the code in this chapter) first and in the most depth.

### 1. Shortest Paths (1959): the state of the art before

Before 1959 there was no clean, provably correct, efficient single-source shortest-path algorithm in wide circulation. Graph problems were solved by enumeration or by heuristics that could be defeated by adversarial weightings. Dijkstra's contribution was not just *an* algorithm but a *provably optimal greedy* one, with an argument for why the greed is safe.

**What was technically new.** The method maintains a set of *settled* nodes (final distances) and *unsettled* nodes (tentative distances). The invariant is: at every step, `distance[v]` for a settled `v` equals the true shortest-path distance, and for an unsettled `v` it equals the shortest distance using only settled intermediate nodes. Each iteration:

1. **Select** the unsettled node `u` with minimum tentative distance.
2. **Settle** it. The invariant plus non-negative edges guarantees `distance[u]` is now final.
3. **Relax** each edge `(u, w)`: if `distance[u] + weight(u, w) < distance[w]`, lower `distance[w]` and record `u` as `w`'s predecessor.

The correctness hinges on step 2, and the proof is short. Suppose we settle `u` with tentative distance `d`, but the true shortest distance is some `d' < d`. That shorter path must at some point leave the settled set for the first time, crossing to an unsettled node `x`. Because all edges are non-negative, the distance to `x` along that path is ≤ `d' < d`. But then `x`, not `u`, would have had the minimum tentative distance, contradicting our selection of `u`. Non-negativity is doing all the work; remove it and the argument collapses, which is exactly why the algorithm is wrong on graphs with negative edges (use Bellman–Ford there).

**How it worked, concretely.** In the code here, `dijkstra()` maintains `distance` and `predecessor` dicts and an `unsettled` set. `settle_next()` is the selection step, and in the original 1959 formulation it is a *linear scan* over the tentative distances:

```python
def settle_next(distance, unsettled):
    current = None
    best = INF
    for node in unsettled:
        if distance[node] < best:
            best = distance[node]
            current = node
    return current
```

That linear scan gives the classic **O(V²)** complexity — V selections, each scanning up to V nodes, plus O(E) relaxations. This chapter keeps that form on purpose, because it is what Dijkstra actually described. The modern **O((V + E) log V)** version replaces the scan with a binary heap (a priority queue), and with a Fibonacci heap you reach O(E + V log V) (Fredman & Tarjan, 1984). None of that changes the idea; it changes the data structure used for "find the smallest tentative distance".

**What descended from it.** Route planners (Google Maps, car navigation) run Dijkstra and its goal-directed refinement A\* (Hart, Nilsson, Raphael, 1968), which adds an admissible heuristic to steer the search toward the destination. Internet link-state routing protocols — **OSPF** and **IS-IS** — have every router run Dijkstra over the network's link map to build its forwarding table. It is a workhorse inside countless other algorithms (network flow, k-shortest-paths, many operations-research pipelines).

### 2. "Go To Statement Considered Harmful" (1968) and Structured Programming

In a March 1968 letter to the *Communications of the ACM* — the provocative title was supplied by the editor, Niklaus Wirth — Dijkstra argued that unrestricted `goto` makes programs hard to reason about. His concern was not aesthetic. He wanted the *static* program text to correspond closely to the *dynamic* process it describes, so that you can reason about a running program from its source. Arbitrary jumps destroy that correspondence: at a given point in execution you cannot describe "where you are" with a small amount of information.

The constructive side, developed in his 1972 monograph *Notes on Structured Programming* and the book *Structured Programming* (with Ole-Johan Dahl and C.A.R. Hoare), was that programs should be built from a few well-behaved control structures — sequence, selection (`if`/`else`), and iteration (`while`) — each with a single entry and a single exit. The Böhm–Jacopini theorem (1966) had already shown these suffice to express any computation. The lasting result: the `goto`-free style is now simply how we write code, and "structured programming" stopped being a movement and became the default.

### 3. Concurrency: Semaphores, the THE System, and the Deadly Embrace

Dijkstra essentially founded the systematic study of concurrent programming.

- **The mutual exclusion problem** and a software solution (Dekker's algorithm, which Dijkstra published and analysed) — how do two processes coordinate so that only one is in a critical section at a time?
- **Semaphores** (from *Cooperating Sequential Processes*, circa 1965–68): an integer with two atomic operations, **P** (proberen, "to test" — wait/decrement) and **V** (verhogen, "to increment" — signal). Semaphores are the primitive from which mutexes, condition variables, and higher-level synchronisation are built. Every operating systems course still teaches them.
- **The THE multiprogramming system** (1968), built at the Technische Hogeschool Eindhoven, was organised as a strict hierarchy of *layers*, each providing an abstract machine to the one above and depending only on the ones below. Layer 0 handled processor allocation, layer 1 memory/segments, and so on. This layered structuring of an OS — proving properties layer by layer — is an ancestor of every modularly designed system since.
- **The Dining Philosophers problem** and the term **"deadly embrace"** (what we now call deadlock): his teaching examples for the ways concurrent processes can wedge each other, and the conditions under which they do. His **Banker's algorithm** is a classic deadlock-*avoidance* strategy: grant a resource request only if the system can still reach a state where every process can finish.

### 4. Program Correctness: Guarded Commands and Weakest Preconditions

Dijkstra's later work aimed at *deriving* programs together with their proofs of correctness, rather than writing code and testing it afterward. In *A Discipline of Programming* (1976) he introduced:

- **Guarded commands**: a minimalist nondeterministic language where a statement can execute only when its boolean *guard* holds, e.g. `if x >= y -> m := x [] y >= x -> m := y fi`. If several guards hold, one is chosen arbitrarily; nondeterminism is made explicit and first-class.
- **Predicate transformers** and the **weakest precondition** `wp(S, R)`: the weakest condition on the input state that guarantees statement `S` terminates in a state satisfying postcondition `R`. This gives a calculational semantics — you compute `wp` backward from what you want to be true at the end, and the program falls out of the derivation. It is a sharpening of Hoare logic into something you can mechanically drive.

This is the formal core of "prove it correct, don't debug it correct" that the Turing citation gestures at, and it feeds directly into modern program verification, static analysis, and tools like model checkers and SMT-backed verifiers.

### 5. Lasting Impact

The shortest-path algorithm alone would earn a place in the canon; it runs, unmodified in spirit, in your pocket. But the larger legacy is a stance: that programming is a rigorous intellectual discipline, that elegance and simplicity are the point rather than a luxury, and that a program's correctness should be something you can argue rather than something you hope for. His 1972 Turing lecture, *The Humble Programmer*, made the case that the limiting factor in software is the human mind's capacity to manage complexity, and that our job is to keep programs small and clear enough to reason about. Half a century of software engineering — structured control flow, layered systems, synchronisation primitives, formal verification, and the humble idea that you should be able to explain why your code works — is the field growing into that argument.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [A Note on Two Problems in Connexion with Graphs](https://doi.org/10.1007/BF01386390) *(the shortest-path algorithm)* | Numerische Mathematik 1 | 1959 |
| [Go To Statement Considered Harmful](https://doi.org/10.1145/362929.362947) *(letter to the editor)* | Communications of the ACM | 1968 |
| [The Structure of the "THE"-Multiprogramming System](https://doi.org/10.1145/363095.363143) | Communications of the ACM | 1968 |
| [Cooperating Sequential Processes](https://doi.org/10.1007/978-1-4757-3472-0_2) *(semaphores, P and V)* | (EWD123; repr. in *The Origin of Concurrent Programming*) | 1968 |
| [The Humble Programmer](https://doi.org/10.1145/355604.361591) *(Turing Award lecture)* | Communications of the ACM | 1972 |
| [Notes on Structured Programming](https://www.cs.utexas.edu/~EWD/ewd02xx/EWD249.PDF) *(EWD249)* | in *Structured Programming*, Academic Press | 1972 |
| [Guarded Commands, Nondeterminacy and Formal Derivation of Programs](https://doi.org/10.1145/360933.360975) | Communications of the ACM | 1975 |
| [A Discipline of Programming](https://www.worldcat.org/title/discipline-of-programming/oclc/1958445) *(book — weakest preconditions)* | Prentice-Hall | 1976 |

---

*Previous: [Week 06 — John McCarthy (1971)](../06-john-mccarthy-1971/)*

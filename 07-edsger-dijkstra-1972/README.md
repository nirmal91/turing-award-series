# Week 07 — Edsger W. Dijkstra (1972)

**ACM Turing Award citation:** *"Edsger Dijkstra was a principal contributor in the late 1950's to the development of the ALGOL, a high level programming language which has become a model of clarity and mathematical rigor. He is one of the principal proponents of the science and art of programming languages in general, and has greatly contributed to our understanding of their structure, representation, and implementation. His fifteen years of publications extend from theoretical articles on graph theory to basic manuals, expository texts, and philosophical contemplations in the field of programming languages."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — Dijkstra's shortest path in about 60 lines: keep a tentative distance to every node, repeatedly settle the closest unsettled one, and relax its edges. One example graph, no flags.

[`implementation.py`](./implementation.py) — a full working version: a small graph type, the algorithm with a predecessor tree so you can rebuild any shortest path, an interactive REPL, a graph-file loader, a 16-case test suite, and a verbose mode that prints every settle and relax.

```
graph (nodes + weighted edges)
    ↓ initialise    start distance 0, all others infinity
    ↓ select        scan for the closest unsettled node
    ↓ settle        its distance is now final (nothing can beat it)
    ↓ relax         improve neighbours' tentative distances
    ↓ repeat        until every reachable node is settled
    ↓
distances + predecessor tree → reconstruct any shortest path
```

What it supports:
- Undirected weighted graphs, built in code or from a `.graph` command file
- Shortest distance from a start node to every node, and the actual path to any goal
- A predecessor tree, so a path is rebuilt by walking backward from the goal
- Non-negative weights enforced (a negative edge is rejected, because the proof depends on it)
- A REPL, a 16-case test suite, and a verbose trace of every step

```bash
python3 concept.py                    # the core idea, plain
python3 implementation.py             # interactive REPL (build a graph, query paths)
python3 implementation.py demo.graph  # load and run a graph command file
python3 implementation.py --test      # test suite (16 cases)
python3 implementation.py --verbose   # REPL that traces every settle and relax
```

Example session:

```
dijkstra> demo
(loaded the demo graph)
dijkstra> path A E
A -> C -> F -> E (distance 20)
dijkstra> dist A
shortest distance from A:
  A -> A = 0
  A -> B = 7
  A -> C = 9
  A -> D = 20
  A -> E = 20
  A -> F = 11
```

The shortest way from A to E is not the road with the fewest hops. It is `A → C → F → E`, length 20, beating the more direct-looking `A → C → D → E` (length 26). The algorithm finds that without ever enumerating the routes.

---

## Full Worked Example

The claim is that a greedy method, settling one node at a time, provably finds the shortest distance to every node. Here is the algorithm run by hand on the demo graph.

### Step 0 — The map

An undirected road map. Each edge is a road with a length; roads run both ways.

```
        7        10
   A -------- B -------- +
   | \                   |
  9|  \14                |15
   |   \                 |
   C --- F        D ------+
   | \    \      /|
   |  \11  \9   /6|
   |   \    \  /  |
   +----+    E ---+
        \   /
      (C-F=2, E-F=9, C-D=11, D-E=6)
```

Cleaner as an adjacency list:

```
A: B(7)  C(9)  F(14)
B: A(7)  C(10) D(15)
C: A(9)  B(10) D(11) F(2)
D: B(15) C(11) E(6)
E: D(6)  F(9)
F: A(14) C(2)  E(9)
```

We want the shortest distance from **A** to every node.

### Step 1 — Initialise

Tentative distance to the start is 0, everything else is infinity. Nothing is settled yet.

```
distance:  A=0   B=inf  C=inf  D=inf  E=inf  F=inf
settled:   { }
```

### Step 2 — Settle A (distance 0)

A is the only node with a known distance, so it is the closest unsettled node. Settle it, then relax its roads. Going through A, each neighbour's tentative distance becomes `0 + road`:

```
relax B: inf -> 7   (via A)
relax C: inf -> 9   (via A)
relax F: inf -> 14  (via A)

distance:  A=0  B=7  C=9  D=inf  E=inf  F=14
settled:   {A}
```

### Step 3 — Settle B (distance 7)

The smallest unsettled distance is B at 7. Settle it. Relax B's unsettled roads:

```
relax C: 9 vs 7+10=17   -> no change (9 is already better)
relax D: inf -> 7+15=22 (via B)

distance:  A=0  B=7  C=9  D=22  E=inf  F=14
settled:   {A, B}
```

Notice C stays 9. B offered a route to C of length 17, but we already had 9 through A. Greedy keeps the better one.

### Step 4 — Settle C (distance 9)

Smallest unsettled is C at 9. Settle it. Relax:

```
relax D: 22 vs 9+11=20  -> 20 (via C, better than via B)
relax F: 14 vs 9+2=11   -> 11 (via C, better than direct A-F)

distance:  A=0  B=7  C=9  D=20  E=inf  F=11
settled:   {A, B, C}
```

C improved two distances. The direct road A–F was 14, but A→C→F is only 11. This is the moment the algorithm beats the obvious guess.

### Step 5 — Settle F (distance 11)

Smallest unsettled is F at 11. Settle it. Relax:

```
relax E: inf -> 11+9=20 (via F)

distance:  A=0  B=7  C=9  D=20  E=20  F=11
settled:   {A, B, C, F}
```

### Step 6 — The tie: settle D and E (both 20)

Two nodes are tied at 20. The order does not matter, because both are already final. Settle D first:

```
relax E: 20 vs 20+6=26  -> no change

distance:  A=0  B=7  C=9  D=20  E=20  F=11
settled:   {A, B, C, F, D}
```

D offered E a route of 26, worse than the 20 E already has. Settle E last. Nothing left to relax.

```
settled:   {A, B, C, F, D, E}   -- done
```

### Result

```
A -> A = 0
A -> B = 7
A -> C = 9
A -> D = 20
A -> E = 20
A -> F = 11
```

To rebuild the path to E, walk the predecessor tree backward: E came from F, F came from C, C came from A. Reverse it: **A → C → F → E, length 20.** The tempting `A → C → D → E` is 9 + 11 + 6 = 26. The algorithm never had to compare whole routes; it only ever compared one edge at a time.

### Edge case — an unreachable node

Add a node G with no roads. When the settled set has absorbed every reachable node, the closest-unsettled scan finds nothing with a finite distance and stops. G keeps distance infinity, and `path A G` reports no path. The algorithm terminates cleanly instead of looping.

### Why greedy is allowed to be greedy

The whole method rests on one fact: **every edge weight is non-negative.** When you settle a node, its tentative distance is the smallest among all unsettled nodes. Any other route to it would have to pass through some node that is still unsettled, and therefore farther away, and then travel a non-negative extra distance. So no later path can be shorter. That is why a settled distance is final, and why the `Graph` refuses a negative edge: one negative road breaks the proof and the answer.

---

## ELI5

Imagine you want the shortest walk from your house to every house on the block, but the streets are all different lengths.

Before, you would try one whole path, then another, then another, and hope you found the shortest. On a big neighbourhood you could never try them all.

A man named Edsger Dijkstra found a better way. Stand at your house. Look at the closest house you can reach and walk there first. Now you know that is the shortest way to that house, for sure, and you never have to check it again. From there, look at the next closest house you have not visited, and go. Keep taking the closest new house each time.

Because you always grab the nearest one first, and streets can only add distance, you never make a mistake. Little by little the shortest walk spreads out from your house to the whole block.

---

## ELI10

In the 1950s, computers were new and slow, and one of the honest questions was: what can this thing actually do that is useful? In 1956 Edsger Dijkstra, a young Dutch programmer, needed a demo to show off a new machine called the ARMAC. He picked a problem everyone understands: what is the shortest way to drive from one city to another? He worked out the method in about twenty minutes, sitting at a cafe with his fiancee, with no pen and paper. He published it three years later in a three-page paper.

Here is the idea. You want the shortest distance from your start city to every other city. Keep a running best guess for each city, starting at zero for your start and "unknown" for the rest. Now repeat one move: take the city with the smallest guess that you have not locked in yet, and lock it in. Once it is locked in, that number is final and never changes. Then look at every road leaving that city and check whether going through it gives a shorter route to its neighbours. If it does, lower their guesses. Lock in cities one at a time and the correct distances spread outward from the start.

The clever part is why locking in is safe. Every road has a length of zero or more, never negative. So the moment a city has the smallest guess left, there is no sneaky longer detour that somehow comes out shorter. Any other route would have to go through a city that is even farther away and then add more road on top. That single fact, non-negative roads, is what turns a simple greedy habit into a method that is provably correct.

Dijkstra is famous for more than this. He also argued, in a blunt 1968 letter titled "Go To Statement Considered Harmful," that programs should be built out of clean nested blocks instead of jumping around with `goto`, which is why your code today has `if`, `while`, and functions instead of a tangle of jumps. And he invented the semaphore, a little counter that lets two programs share one resource without stepping on each other. But the shortest path algorithm is the one that quietly runs every time your phone finds you a route.

---

## CS Graduate Level — Greedy Correctness, Structured Programming, and Semaphores

Dijkstra's Turing Award is unusual in that it honours a body of work, not a single result. Three strands matter most: the shortest path algorithm, the argument for structured programming, and the invention of the semaphore. They share a temperament: reduce a messy problem to a small invariant you can actually reason about.

### 1. The Shortest Path Algorithm (1959)

**State of the art before.** Finding a shortest route in a weighted graph had no efficient, provably correct method in wide use. The naive approach, enumerate paths and compare, is exponential: the number of simple paths in a graph grows combinatorially, so it is hopeless on any real network. There were ad hoc relaxation ideas floating around, but no clean argument for why one would terminate with the right answer.

**What was new.** Dijkstra's "A Note on Two Problems in Connexion with Graphs" (1959) gave a greedy algorithm with a correctness proof, in three pages. Maintain a tentative distance `d[v]` to every node and a set `S` of *settled* nodes whose distance is known to be final. Initialise `d[start] = 0`, everything else infinity, `S` empty. Then repeat: pick the unsettled node `u` with minimum `d[u]`, add it to `S`, and relax every edge `(u, v)`:

```
if d[u] + weight(u, v) < d[v]:
    d[v] = d[u] + weight(u, v)
    predecessor[v] = u
```

**How it works, and the invariant.** The loop invariant is: for every node in `S`, `d[v]` equals the true shortest distance. The proof that settling `u` preserves this rests entirely on non-negative weights. When `u` is chosen, `d[u]` is the minimum over all unsettled nodes. Any other path to `u` must leave `S` at some point through an unsettled node `x`, and by choice `d[x] ≥ d[u]`; the remainder of that path adds only non-negative length, so it cannot beat `d[u]`. Therefore `d[u]` is already optimal and can be settled. A single negative edge destroys this argument, which is why the algorithm is specifically for non-negative weights (Bellman–Ford, 1958, handles negatives at higher cost).

**Complexity and what descended.** Dijkstra's original selection step was a linear scan over the tentative distances, giving O(V²), which is what [`implementation.py`](./implementation.py) does, faithfully. Replacing the scan with a binary heap gives O((V + E) log V); a Fibonacci heap (Fredman and Tarjan, 1984) gives O(E + V log V). The algorithm is the backbone of internet routing (OSPF and IS-IS run a Dijkstra shortest-path-first computation over the link-state graph), of GPS and map routing (usually as A*, which is Dijkstra plus an admissible heuristic that steers the search toward the goal), and of countless graph problems that reduce to shortest paths.

### 2. Structured Programming (1968)

**State of the art before.** Programs were built with `goto`. Control flow was a web of jumps, and understanding a program meant tracing every possible path into a block of code. There was no reliable way to reason about what was true at a given line, because control could arrive there from anywhere.

**What was new.** Dijkstra's 1968 letter to the editor of the *Communications of the ACM*, given the title "Go To Statement Considered Harmful," argued that unrestricted `goto` makes programs impossible to reason about, and that all algorithms can be expressed with three composable control structures: sequence, selection (`if/then/else`), and iteration (`while`). The deep point was not stylistic. His argument was about the gap between the *static* program text you read and the *dynamic* process it describes. With only structured constructs, you can describe where a running program is with a small, readable coordinate (which line, plus how many times each enclosing loop has run). With arbitrary `goto`, that coordinate becomes an unbounded tangle.

**What it enabled.** This line of thinking, developed further in the 1972 book *Structured Programming* with Hoare and Dahl, is why modern languages are built from blocks, functions, and loops rather than labels and jumps. It is the foundation under Hoare logic and every static analysis that reasons about program state, because those tools need control flow to be structured to work at all. The `if`/`while`/function structure of the very code in this chapter is the direct inheritance.

### 3. Semaphores and Concurrency (1965–1968)

**State of the art before.** When several programs share one resource (a printer, a block of memory, a CPU), they can interfere: two processes reading and writing the same variable can interleave into a corrupt result, the *race condition*. Early attempts at mutual exclusion in software (Dekker's algorithm) were correct but intricate and did not generalise.

**What was new.** Dijkstra introduced the **semaphore**: an integer with two atomic operations, historically `P` (from Dutch *proberen*, to test; decrement and block if the result is negative) and `V` (*verhogen*, to increment; wake a waiter if any). A binary semaphore enforces mutual exclusion: `P` before a critical section, `V` after, and at most one process is inside at a time. A counting semaphore manages a pool of N identical resources. He built these into the THE multiprogramming system (1968), one of the first systems designed as a hierarchy of layers each of which could be reasoned about independently. He also posed the dining philosophers problem as a teaching example of deadlock and resource contention.

**What descended.** Semaphores are still primitive operations in operating systems (POSIX semaphores, the Linux kernel). Mutexes, condition variables, and monitors are all built on the same idea of atomic guarded state. Every time a program takes a lock before touching shared data, it is using Dijkstra's abstraction.

### 4. Lasting Impact

The through-line is Dijkstra's insistence that programming is a mathematical discipline, that a program should be something you can prove correct rather than test until it seems to work. His later work on predicate transformers and the weakest-precondition calculus (*A Discipline of Programming*, 1976) and on self-stabilising systems (1974) pushed that conviction further. The shortest path algorithm is the piece of it that ended up in every router and every phone, but the larger legacy is the idea that a small, well-chosen invariant is worth more than any amount of cleverness. That is why his greedy proof still reads cleanly sixty years later: it rests on one fact about non-negative edges, and everything else follows.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [A Note on Two Problems in Connexion with Graphs](https://doi.org/10.1007/BF01386390) | Numerische Mathematik | 1959 |
| [Go To Statement Considered Harmful](https://doi.org/10.1145/362929.362947) | Communications of the ACM | 1968 |
| [The Structure of the "THE"-Multiprogramming System](https://doi.org/10.1145/363095.363143) | Communications of the ACM | 1968 |
| [Cooperating Sequential Processes](https://doi.org/10.1007/978-1-4757-3472-0_2) *(semaphores, dining philosophers; circulated 1965)* | EWD123 / reprinted | 1968 |
| [Structured Programming](https://dl.acm.org/doi/book/10.5555/1243380) *(with Dahl and Hoare)* | Academic Press | 1972 |
| [Self-stabilizing Systems in Spite of Distributed Control](https://doi.org/10.1145/361179.361202) | Communications of the ACM | 1974 |
| [The Humble Programmer](https://doi.org/10.1145/355604.361591) *(Turing Award lecture)* | Communications of the ACM | 1972 |

---

*Previous: [Week 06 — John McCarthy (1971)](../06-john-mccarthy-1971/)*

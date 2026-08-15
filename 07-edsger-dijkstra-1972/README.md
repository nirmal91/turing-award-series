# Week 07 — Edsger W. Dijkstra (1972)

**ACM Turing Award citation:** *"Edsger Dijkstra was a principal contributor in the late 1950's to the development of the ALGOL, a high level programming language which has become a model of clarity and mathematical rigor. He is one of the principal exponents of the science and art of programming languages in general, and has greatly contributed to our understanding of their structure, representation, and implementation. His fifteen years of publications extend from theoretical articles on graph theory to basic manuals, expository texts, and philosophical contemplations in the field of programming languages."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — Dijkstra's shortest path in about 60 lines: keep a tentative distance for every node, repeatedly settle the closest unfinished one, and relax its neighbours. The linear scan for the minimum is exactly how the 1959 paper described it.

[`implementation.py`](./implementation.py) — a full working shortest-path engine: a weighted graph you can build up edge by edge, Dijkstra's algorithm with path reconstruction, a binary-heap version (the modern descendant) that the test suite checks against the original, a small graph-script language, a REPL, and a verbose mode that prints every settle and relax step.

```
graph description (edges with non-negative lengths)
    ↓ build      adjacency table: node -> [(neighbour, length), ...]
    ↓ dijkstra   settle the closest unfinished node, relax its edges, repeat
    ↓ predecessors
    ↓ reconstruct   walk the predecessor trail backward from the target
    ↓
  distance + path
```

What it supports:
- Undirected and directed weighted graphs, built in code or from a `.graph` script
- Shortest distance from a source to every node, and the actual route to any target
- Two implementations of the same rule: the 1959 linear scan (O(V²)) and a binary heap (O(E log V))
- Non-negative edge lengths enforced, because the algorithm's correctness depends on it
- A REPL, a 17-case test suite, and a verbose mode that prints the settle/relax trace

```bash
python3 concept.py                      # the core idea, plain
python3 implementation.py               # interactive REPL (starts on the demo graph)
python3 implementation.py cities.graph  # load a graph script and run its queries
python3 implementation.py --test        # test suite (17 cases)
python3 implementation.py --verbose      # REPL that prints every settle/relax step
```

Example session:

```
graph> show
graph:
  A -> B(7), C(9), F(14)
  B -> A(7), C(10), D(15)
  C -> A(9), B(10), D(11), F(2)
  D -> B(15), C(11), E(6)
  E -> D(6), F(9)
  F -> A(14), C(2), E(9)
graph> path A E
A -> E  distance 20  via A -> C -> F -> E
graph> edge A E 3
graph> path A E
A -> E  distance 3  via A -> E
```

The route from A to E is `A -> C -> F -> E` at distance 20, not the direct-looking `A -> F -> E` (which is 14 + 9 = 23). The cheap first step is not the shortest path. Settling the closest unfinished node every time is what guarantees the answer is right and not merely plausible.

---

## Full Worked Example

Here is Dijkstra's algorithm run by hand on the six-node graph above, from source `A`. The undirected edges are:

```
A-B 7   A-C 9   A-F 14   B-C 10   B-D 15   C-D 11   C-F 2   D-E 6   E-F 9
```

### Step 0 — Set the starting distances

Every node begins infinitely far away. The source is 0 away from itself. `pred` records the node we arrived from, so we can rebuild the route later.

```
dist:  A=0   B=∞   C=∞   D=∞   E=∞   F=∞
pred:  (all none)
finished: { }
```

### Step 1 — Settle A (the closest unfinished node, distance 0)

A is the smallest tentative distance, so it is settled: 0 is final. Relax every edge out of A. Each neighbour had ∞, so every route through A is an improvement.

```
relax B: ∞ -> 7   (via A)
relax C: ∞ -> 9   (via A)
relax F: ∞ -> 14  (via A)

dist:  A=0   B=7   C=9   D=∞   E=∞   F=14
finished: { A }
```

### Step 2 — Settle B (distance 7)

The smallest unfinished distance is B at 7. Settle it. B's neighbours are A (finished), C, and D.

```
through B to C = 7 + 10 = 17   not better than 9,  skip
through B to D = 7 + 15 = 22   better than ∞,  relax D -> 22 (via B)

dist:  A=0   B=7   C=9   D=22   E=∞   F=14
finished: { A, B }
```

### Step 3 — Settle C (distance 9)

Smallest unfinished is C at 9. This is the important round. C's neighbours are A, B (finished), D, and F.

```
through C to D = 9 + 11 = 20   better than 22,  relax D -> 20 (via C)
through C to F = 9 + 2  = 11   better than 14,  relax F -> 11 (via C)

dist:  A=0   B=7   C=9   D=20   E=∞   F=11
finished: { A, B, C }
```

Notice F just dropped from 14 to 11. The direct edge `A-F` of length 14 has been beaten by the two-hop route `A -> C -> F` = 9 + 2. This is the moment the greedy-looking answer loses.

### Step 4 — Settle F (distance 11)

Smallest unfinished is F at 11. F's neighbours are A, C (finished) and E.

```
through F to E = 11 + 9 = 20   better than ∞,  relax E -> 20 (via F)

dist:  A=0   B=7   C=9   D=20   E=20   F=11
finished: { A, B, C, F }
```

### Step 5 — Settle D and E (both at distance 20)

D and E are tied at 20. Settle D first. Its only unfinished neighbour is E:

```
through D to E = 20 + 6 = 26   not better than 20,  skip
```

Then settle E. Every node is now finished.

```
dist:  A=0   B=7   C=9   D=20   E=20   F=11
pred:  B<-A  C<-A  D<-C  F<-C  E<-F
```

### Reconstruct the path A -> E

Walk the `pred` pointers backward from E, then reverse:

```
E  <- F  <- C  <- A
reversed: A -> C -> F -> E
check:    9  + 2  + 9   = 20  ✓
```

### Why this is provably correct, not just lucky

Each time we settle a node, we claim its distance can never get smaller. Why is that safe? Because every edge length is non-negative. Any not-yet-settled path to that node would have to leave through some other unfinished node, which already has an equal-or-larger tentative distance, and adding a non-negative edge to it can only make things longer. So the closest unfinished node is already at its final distance. That single invariant is the whole proof, and it is also why the algorithm breaks the moment you allow a negative edge:

```
X -> Y  length 5
X -> Z  length 2
Z -> Y  length -4
```

Dijkstra settles Y at 5 (through X), then later finds `X -> Z -> Y` = 2 + (-4) = -2, which is shorter, but Y is already finished and never revisited. The answer comes out wrong. This is exactly why `implementation.py` rejects a negative edge instead of quietly returning a bad path. (When negative edges are genuinely needed, the Bellman-Ford algorithm handles them, at a higher cost.)

---

## ELI5

Say you want the shortest walk from your house to the park, and there is a tangle of little streets in between.

Before, you might pick a way, then try another, then a third, and still never be sure you found the shortest one.

Dijkstra found a rule that always works. Write a 0 on your house. Look at the places you can reach and write down how far each one is. Now walk to the closest place you have not visited yet, cross it off for good, and update the numbers on its neighbours if you found a shorter way to them.

Keep picking the closest place you have left. The moment you cross off the park, the number on it is the shortest walk. You never have to go back and check, because you always finished the closest one first.

---

## ELI10

In the 1950s, computers were brand new and expensive, and there was no tidy method for a plain question: given a map of roads with distances, what is the shortest route between two towns? You could search, but a careless search might wander far down a long road before noticing a short one, and you had no guarantee the first route you found was actually the best.

In 1956, a 26-year-old Dutch programmer named Edsger Dijkstra was sitting at a cafe in Amsterdam with his fiancee. He was trying to think of a problem that would show off a new computer called the ARMAC in a way ordinary people could follow. Shortest route between two cities was easy to explain. In about twenty minutes, with no pencil and no paper, he worked out the method that now carries his name. He did not publish it until 1959, in a note only three pages long.

The trick is a rule you repeat. Give every town a running "best distance so far," starting at 0 for the town you are in and infinity for the rest. Then always visit the closest town you have not finished yet, mark it done, and check whether going through it gives its neighbours a shorter distance. Because no road has a negative length, once a town is the closest unfinished one, its distance can never improve, so you can lock it in and never look back. That is what makes it fast: you touch each town about once instead of trying every possible route.

That little rule is everywhere now. When your phone finds the fastest way home, when the internet decides which cables your data hops across, when a game character walks around a wall, some descendant of Dijkstra's 1959 cafe idea is running underneath. He went on to shape how we think about programming itself, arguing that programs should be built to be correct rather than debugged into working, but this three-page note is the piece of him almost every one of us uses every day.

---

## CS Graduate Level — One Rule for Shortest Paths, and a Career Spent Making Programs Provable

Dijkstra's Turing citation points at ALGOL, but his influence is a fan of contributions that are still load-bearing: the shortest-path algorithm, structured programming, the semaphore and the theory of cooperating processes, and a formal discipline for deriving correct programs. The through-line is a single conviction, stated in his 1972 Turing lecture *The Humble Programmer*: programming is hard enough that our only hope is to keep it simple enough to reason about, and to prove programs correct rather than test them into apparent submission. "Program testing can be used to show the presence of bugs, but never to show their absence."

### 1. The State of the Art Before (mid-1950s)

Graph problems were studied in operations research, but there was no efficient, general, provably-correct shortest-path method in wide circulation. Ford's label-correcting ideas and the dynamic-programming formulations that became Bellman-Ford were emerging around the same time and handle negative edges, but at higher cost. On the language side, machine and assembly code dominated; control flow was a tangle of jumps, and there was no accepted way to argue that a program did what it claimed. Dijkstra worked on both fronts.

### 2. The Shortest-Path Algorithm (1959)

The 1959 note *A Note on Two Problems in Connexion with Graphs* solves two problems in three pages; the shortest-path one is the famous half (the other is the minimum spanning tree). The algorithm maintains a tentative distance `d[v]` for every node and a set of *settled* nodes whose distance is final. It repeats one step:

1. Among unsettled nodes, pick `u` with the smallest `d[u]`.
2. Settle `u`.
3. For each edge `u -> v` of length `w`, **relax**: if `d[u] + w < d[v]`, set `d[v] = d[u] + w` and record `pred[v] = u`.

The correctness rests on a single invariant, provable by induction: **when a node is settled, `d[u]` is its true shortest distance.** The argument needs one hypothesis — all edge lengths are non-negative. Suppose `u` is the closest unsettled node but some shorter path `P` to `u` exists. `P` must cross from the settled set to the unsettled set at some node `x`; `x` is unsettled, so `d[x] >= d[u]`, and the remainder of `P` from `x` to `u` has non-negative length, so `P`'s length is `>= d[u]`. Contradiction. That is the whole proof, and the worked example above shows the one place it bites: node F drops from 14 to 11 because a two-hop route beats the direct edge, and the negative-edge counterexample shows the algorithm silently failing the moment the hypothesis is dropped.

Complexity depends entirely on how you find "the smallest `d[u]`." Dijkstra's original linear scan is `O(V²)`, ideal for dense graphs. Replace the scan with a binary heap and it becomes `O((V + E) log V)`; with a Fibonacci heap, `O(E + V log V)`. `implementation.py` ships both the linear scan (faithful to 1959) and a `heapq` version, and the test suite asserts they agree on every graph — a small demonstration that the priority-queue optimization changes the running time, not the answer.

### 3. Structured Programming and "Go To Statement Considered Harmful" (1968)

Dijkstra's 1968 letter to *Communications of the ACM* (the title was supplied by editor Niklaus Wirth) argued that unrestricted `goto` makes a program's dynamic behaviour impossible to map onto its static text. His point was about human reasoning: with `goto`, knowing *where* control is tells you little about *how* it got there. Restrict yourself to sequencing, selection (`if`/`case`), and iteration (`while`), and at every point in the text you can name a small, meaningful description of the program's state — an invariant. The 1972 monograph *Structured Programming* (with Dahl and Hoare) generalized this into program construction by stepwise refinement. This is why essentially every language since is built from block-structured control flow, and why "spaghetti code" is a pejorative rather than a neutral description.

### 4. Cooperating Sequential Processes: Semaphores, THE, and Deadlock (1965–1968)

Dijkstra effectively founded concurrent programming as a discipline. In *Solution of a Problem in Concurrent Programming Control* (1965) he posed and solved mutual exclusion for `n` processes. He then introduced the **semaphore**: an integer with two indivisible operations, `P` (wait/down) and `V`(signal/up), that together are enough to coordinate any number of processes safely. The `THE` multiprogramming system (1968) demonstrated the payoff of layering: the system is built as a hierarchy of levels, each providing a clean abstract machine to the level above (processor allocation, then memory, then I/O), so each layer can be understood and verified against the one below. He gave us the vocabulary the field still uses — the "deadly embrace" (deadlock), the dining philosophers problem as the canonical illustration, and the banker's algorithm for deadlock avoidance. Semaphores are still the primitive under mutexes, condition variables, and the synchronization in every operating-system kernel.

### 5. A Discipline of Programming: Guarded Commands and Weakest Preconditions (1975–1976)

Dijkstra's late work tried to make "correct by construction" literal. *Guarded Commands, Nondeterminacy and Formal Derivation of Programs* (1975) introduced a tiny language whose conditionals and loops are sets of *guarded commands* `guard -> statement`; when several guards are true, the choice is nondeterministic, which forces the programmer to make correctness independent of the choice. On top of this he built the **weakest precondition** calculus: `wp(S, R)` is the weakest condition on the initial state guaranteeing that statement `S` terminates in a state satisfying `R`. Program construction becomes an algebraic activity — you derive the program from the specification `R` by manipulating `wp`, rather than writing code and hoping. *A Discipline of Programming* (1976) is the book-length treatment. This line runs directly into Hoare logic, modern verification tools, model checkers, and the loop-invariant reasoning taught in every algorithms course.

### 6. Lasting Impact

Two legacies, one practical and one cultural. The practical one is concrete and ubiquitous: Dijkstra's shortest path is the core of link-state internet routing (OSPF and IS-IS build a map of the network and run Dijkstra to fill their forwarding tables), of turn-by-turn navigation (usually as the A* generalization, which is Dijkstra plus an admissible heuristic), and of pathfinding in robotics and games. The cultural one is the insistence that programming is a mathematical activity where simplicity and provability are the point, not luxuries — the source of structured control flow, of treating concurrency as something to reason about rather than debug, and of the whole field of formal verification. The modern echo is sharp: as we hand more code generation to systems that produce plausible-looking programs quickly, Dijkstra's central question — how do you *know* it is correct, rather than that it seems to work — is more pressing, not less.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [A Note on Two Problems in Connexion with Graphs](https://doi.org/10.1007/BF01386390) *(the shortest-path algorithm)* | Numerische Mathematik | 1959 |
| [Solution of a Problem in Concurrent Programming Control](https://doi.org/10.1145/365559.365617) | Communications of the ACM | 1965 |
| [Go To Statement Considered Harmful](https://doi.org/10.1145/362929.362947) | Communications of the ACM | 1968 |
| [The Structure of the "THE"-Multiprogramming System](https://doi.org/10.1145/363095.363143) | Communications of the ACM | 1968 |
| [The Humble Programmer](https://doi.org/10.1145/355604.361591) *(Turing Award lecture)* | Communications of the ACM | 1972 |
| [Self-stabilizing Systems in Spite of Distributed Control](https://doi.org/10.1145/361179.361202) | Communications of the ACM | 1974 |
| [Guarded Commands, Nondeterminacy and Formal Derivation of Programs](https://doi.org/10.1145/360933.360975) | Communications of the ACM | 1975 |
| [A Discipline of Programming](https://www.pearson.com/en-us/subject-catalog/p/discipline-of-programming/P200000003524) *(book)* | Prentice-Hall | 1976 |

---

*Previous: [Week 06 — John McCarthy (1971)](../06-john-mccarthy-1971/)*

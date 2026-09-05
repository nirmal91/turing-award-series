# Week 07 — Edsger W. Dijkstra (1972)

**ACM Turing Award citation:** *"The working vocabulary of programmers everywhere is studded with words originated or forcefully promulgated by E. W. Dijkstra — display, deadly embrace, semaphore, go-to-less programming, structured programming. But his influence on programming is more pervasive than any glossary can possibly indicate. The precious gift that this Turing Award acknowledges is Dijkstra's style: his approach to programming as a high, intellectual challenge; his eloquent insistence and practical demonstration that programs should be composed correctly, not just debugged into correctness; and his illuminating perception of problems at the foundations of program design."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — Dijkstra's shortest-path idea in about 60 lines: every node gets a distance label, you repeatedly finalize the smallest tentative one and use it to shrink its neighbors' labels, and no whole path is ever built or compared.

[`implementation.py`](./implementation.py) — a full working version: a directed weighted graph, the algorithm exactly as the 1959 paper describes it (tentative/permanent labels, linear scan for the minimum — no priority queue, because Dijkstra didn't use one), path reconstruction, and a brute-force path enumerator to check it against.

```
graph edges (add A B 4)
    -> shortest_paths()   tentative labels -> permanent labels, one node at a time
    -> path_to()          walk the parent pointers back into a route
    -> printed result
```

What it supports:
- A directed, weighted graph built one edge at a time (`add A B 4`)
- `shortest_paths()`: Dijkstra's algorithm, mirroring the original two-pile (tentative/permanent) description
- `path_to()`: reconstructs the actual route, not just the distance
- `brute_force_shortest_path()`: the "before" — enumerate every simple path and keep the shortest, so you can watch it agree with Dijkstra and see why nobody wants to run it on a real graph
- A REPL, a graph-script loader, an 18-case test suite, and a verbose mode that prints every label finalize and relax

```bash
python3 concept.py                       # the core idea, plain
python3 implementation.py                # interactive REPL
python3 implementation.py practice.graph # load and run a graph script
python3 implementation.py --test         # test suite (18 cases)
python3 implementation.py --verbose      # REPL that prints every label update
```

Example session:

```
dijkstra> add A B 4
added A -> B (4)
dijkstra> add A C 1
added A -> C (1)
dijkstra> add C B 2
added C -> B (2)
dijkstra> add B D 1
added B -> D (1)
dijkstra> add C D 5
added C -> D (5)
dijkstra> run A
  A: 0
  B: 3
  C: 1
  D: 4
dijkstra> path A D
  A -> C -> B -> D   (distance 4)
```

The route to `D` is not the direct-looking `A -> B -> D` (4 + 1 = 5). It's `A -> C -> B -> D` (1 + 2 + 1 = 4), a path that only becomes visible once you've already found the cheaper way to `B`. Dijkstra's algorithm finds that without ever building or comparing a whole path — it only ever shrinks labels.

---

## Full Worked Example

### Happy path: the diamond graph

Graph: `A -> B (4)`, `A -> C (1)`, `C -> B (2)`, `B -> D (1)`, `C -> D (5)`. Find the shortest distance from `A` to everything.

**Step 0 — initialize.** Every node gets a label. The source is `0`; everyone else starts at infinity because we haven't found any path to them yet.

```
label: A=0  B=inf  C=inf  D=inf
tentative: {A, B, C, D}
permanent: {}
```

**Step 1 — finalize A.** Scan the tentative pile for the smallest label. Only `A` has a finite one (`0`), so it wins by default. Move it to permanent — its label can never change again. Then relax every edge out of `A`: for each neighbor, check whether going through `A` beats the neighbor's current label.

```
finalize A (label 0)
  relax A->B: 0 + 4 = 4 < inf   -> label[B] = 4
  relax A->C: 0 + 1 = 1 < inf   -> label[C] = 1

label: A=0  B=4  C=1  D=inf
tentative: {B, C, D}
permanent: {A}
```

**Step 2 — finalize C.** Scan the tentative pile again: `B=4`, `C=1`, `D=inf`. `C` is smallest, so it's next. Once a node is chosen here, its label is final — nothing discovered later can ever beat it, because everything still tentative already has a label `>= label[C]`, and edge weights are never negative, so no future relaxation through them can produce something smaller than `label[C]`.

```
finalize C (label 1)
  relax C->B: 1 + 2 = 3 < 4    -> label[B] = 3   (found a cheaper way to B!)
  relax C->D: 1 + 5 = 6 < inf  -> label[D] = 6

label: A=0  B=3  C=1  D=6
tentative: {B, D}
permanent: {A, C}
```

This is the step that matters. `B`'s label was `4` after step 1 (the direct edge `A -> B`). Going through `C` first drops it to `3`. That's the whole algorithm in one line: a node's provisional label is a ceiling, not an answer, until it's finalized.

**Step 3 — finalize B.** Smallest tentative label is now `B=3`.

```
finalize B (label 3)
  relax B->D: 3 + 1 = 4 < 6    -> label[D] = 4

label: A=0  B=3  C=1  D=4
tentative: {D}
permanent: {A, C, B}
```

**Step 4 — finalize D.** Only `D` is left, label `4`. Finalize it. No outgoing edges to relax.

```
finalize D (label 4)
label: A=0  B=3  C=1  D=4
tentative: {}
permanent: {A, C, B, D}
```

Done. Every label is now a true shortest distance: `A=0, C=1, B=3, D=4`. Walking the parent pointers backward from `D` gives the route: `D <- B <- C <- A`, reversed to `A -> C -> B -> D`. Total: `1 + 2 + 1 = 4`. That beats the direct-looking `A -> B -> D` (`4 + 1 = 5`) — and to find that out, the algorithm never built either path and compared their totals. It just kept shrinking labels.

### Edge case: a negative edge breaks the guarantee

Dijkstra's correctness argument leans on one fact: once a node is finalized, nothing later can produce a shorter path to it, because everything still tentative already has a label at least as large, and edges never subtract. Negative weights void that argument. Graph: `A -> C (1)`, `A -> D (2)`, `D -> C (-5)`.

```
label: A=0  C=inf  D=inf
finalize A (label 0)
  relax A->C: 0 + 1 = 1 < inf   -> label[C] = 1
  relax A->D: 0 + 2 = 2 < inf   -> label[D] = 2

tentative: {C, D}   label: C=1  D=2
```

`C` looks cheapest (`1 < 2`), so it's finalized next — permanently.

```
finalize C (label 1)     <- WRONG, but the algorithm doesn't know that yet
  (C has no outgoing edges to relax)

tentative: {D}
finalize D (label 2)
  relax D->C: 2 + (-5) = -3 < 1   -> would update label[C] to -3...
                                      ...but C is already permanent. Too late.
```

The true shortest path is `A -> D -> C` (`2 + -5 = -3`), and `brute A C` in the REPL finds it. But Dijkstra's algorithm reports `1`, the distance of the path it locked in before it had seen the shortcut. This isn't a bug in this implementation — it's a real, well-known limitation of the algorithm, and it's exactly why Bellman-Ford (which tolerates negative weights, at the cost of being slower) exists as a separate algorithm. `implementation.py --test` asserts this mismatch directly, as a documented fact about what Dijkstra's algorithm guarantees and what it doesn't.

---

## ELI5

Before, if you wanted the shortest way to a friend's house, you had to imagine every possible route and add up the steps for each one, then pick the smallest total. If there were a lot of streets, that's a lot of routes to imagine.

Dijkstra found a shortcut. Start at your house with a sticky note that says "0 steps." Put a blank sticky note on every other house. Look at all your neighbors' houses and write a guess on their sticky notes: "steps to get here from my house." Now go to whichever house has the smallest number on its sticky note, and treat that number as final — done, no more changing it. From that house, look at its neighbors and see if going through it makes their guess smaller. Keep doing that, always picking the smallest unfinished sticky note next.

By the time every house has a final number, every single one is the true shortest distance from your house. And you never once had to imagine a whole route and add it up. You just kept fixing sticky notes, one at a time.

---

## ELI10

In 1956, Edsger Dijkstra was a 26-year-old programmer in the Netherlands, working on a new computer called the ARMAC. He wanted a demo problem that would be easy for a non-programmer to understand and impressive for the machine to solve: the shortest route between two Dutch cities, Rotterdam and Groningen, on a simplified map of 64 cities.

The story goes that he worked out the algorithm without a computer, without even pen and paper, in about twenty minutes, while sitting on a café terrace in Amsterdam with his fiancée. The trick was to stop thinking about routes and start thinking about running totals. Instead of asking "what is the shortest path?", ask "what is the smallest distance I can currently prove to each city, and can I lock one of those in?" Every time you lock in the cheapest unproven distance, it turns out to be correct forever, and you use it to improve your guesses about its neighbors. Repeat until every city is locked in. He published the method in 1959, in a paper just three pages long.

That's the algorithm most people mean when they say "Dijkstra." But the 1972 Turing Award citation is really about something bigger than one algorithm: it's about a style. In 1968 Dijkstra wrote a short, sharp letter to a computing magazine called "Go To Statement Considered Harmful," arguing that jumping around a program with `goto` statements — which is how almost everyone wrote code at the time — made programs nearly impossible to reason about. He pushed instead for what he called structured programming: build programs out of sequence, choice, and repetition, nothing else, so you can understand what a program does by reading it top to bottom instead of tracing jumps all over the page. Around the same time, working on early multitasking operating systems, he invented the semaphore, a simple counter that lets multiple running programs take turns using a shared resource without stepping on each other. Three different problems, one habit underneath all of them: don't just make the code work, make it possible to prove that it works.

Those two ideas, structured programming and semaphores, shaped how essentially every programming language and operating system since has been built. Every `if`, `while`, and function call you write without a `goto` anywhere in sight is a small, permanent win for Dijkstra's argument. Every time an operating system lets two programs share a printer, a database row, or a slot in memory without corrupting each other, there's a semaphore or one of its descendants doing the coordinating underneath.

---

## CS Graduate Level — Shortest Paths, No Jumps, and Taking Turns

### 1. Shortest paths: from brute-force enumeration to one-pass labeling

**Before.** Finding the shortest path in a weighted graph, absent a better idea, means enumerating candidate routes and comparing their totals. The number of simple paths between two nodes in a dense graph grows combinatorially with the node count — there is no polynomial bound on how many you might have to check. `brute_force_shortest_path()` in `implementation.py` is exactly this: recursively try every unvisited neighbor, keep the cheapest complete route. It's correct and it's exponential.

**What was new.** Dijkstra's 1959 paper, "A Note on Two Problems in Connexion with Graphs," reframes the problem entirely. Rather than build and compare whole paths, maintain a single number per node — a *label* — that is always either a proven-correct shortest distance ("permanently labelled" in the paper's terms) or a provisional upper bound ("tentatively labelled"). The algorithm:

```python
def shortest_paths(graph, source):
    dist = {node: INFINITY for node in graph.nodes()}
    dist[source] = 0
    tentative, permanent = set(graph.nodes()), set()

    while tentative:
        current = min(tentative, key=lambda n: dist[n])   # smallest tentative label
        tentative.remove(current)
        permanent.add(current)
        for neighbor, weight in graph.edges[current]:
            if neighbor not in permanent:
                dist[neighbor] = min(dist[neighbor], dist[current] + weight)
    return dist
```

The correctness argument is short and depends critically on non-negative weights: when `current` is chosen as the smallest remaining tentative label, every other tentative node already has a label `>= dist[current]`, and since no edge can subtract distance, no path discovered later through a still-tentative node can produce something smaller than `dist[current]`. So `current`'s label is safe to finalize immediately — no path through the unexplored part of the graph can ever beat it. That single invariant is why the algorithm needs only one pass: each node is finalized exactly once, and once finalized, never revisited.

**The linear scan, and why it's there on purpose.** `implementation.py` picks the minimum tentative label with a plain scan over the tentative set, exactly as the 1959 paper describes it — Dijkstra had no priority queue in mind; that's a `V` nodes times `V` scan, or `O(V^2)`. Replacing that scan with a binary or Fibonacci heap (invented later, independently) turns the same algorithm into `O(E log V)`, which is what every production shortest-path library actually runs. That's a data-structure optimization layered on top of an unchanged algorithm, not a different algorithm — which is why this chapter's code keeps the original O(V^2) scan: the point here is the labeling idea, not the engineering that came after it.

**The edge case that defines the boundary.** The Full Worked Example above shows a negative edge breaking the finalize-and-never-revisit guarantee: a node gets finalized on an artificially cheap label, and a genuinely shorter route through a not-yet-finalized node is discovered too late to matter. `implementation.py --test` pins this down as an assertion, not just a warning in the README. This is precisely the gap that Bellman-Ford (1958, independently) fills: it tolerates negative weights by relaxing every edge `V-1` times instead of finalizing nodes one at a time, trading Dijkstra's speed for that tolerance.

**What descended from it.** Dijkstra's algorithm (with a heap) is the shortest-path core inside routing protocols (OSPF, IS-IS use link-state routing built on it), road navigation and mapping software, and network packet routing. A* (Hart, Nilsson, Raphael, 1968) is Dijkstra's algorithm plus a heuristic that steers the search toward the target instead of expanding outward uniformly — still finalize-and-never-revisit underneath.

### 2. Structured programming: `goto` and the shape of provably correct control flow

**Before.** Early high-level languages inherited `goto` directly from assembly's unconditional jump. A program's control flow was, in general, an arbitrary directed graph over labeled statements — any line could jump to any other. That flexibility came at a real cost: to know the state of a program at a given line, you had to trace every possible jump into it from anywhere else in the source, and that set of possible histories didn't compose. Understanding one part of a large `goto`-laden program required understanding, in principle, all of it.

**What was new.** Dijkstra's 1968 letter to *Communications of the ACM*, "Go To Statement Considered Harmful," argued for restricting control flow to three composable constructs: sequence (do this, then that), selection (`if`/`then`/`else`), and iteration (`while`/`for`). Each of these has a single entry and a single exit, so they nest cleanly — the "shape" of the program's control flow at any point is determined by the static structure of the enclosing blocks, not by a dynamic history of jumps you'd have to reconstruct. He formalized this further in "Notes on Structured Programming" (in *Structured Programming*, with Ole-Johan Dahl and C.A.R. Hoare, 1972), connecting it to program correctness proofs: if control flow is built from a small, closed set of composable constructs, you can reason about correctness compositionally — prove each block correct in isolation, then compose the proofs the same way you composed the blocks.

**How it worked, concretely.** Compare finding the first negative number in a list:

```
goto style (control flow is a graph you have to trace):        structured style (control flow is nested blocks):
  i = 0                                                           i = 0
loop:                                                              found = -1
  if i >= n goto done                                              while i < n and found == -1:
  if a[i] < 0 goto found                                               if a[i] < 0:
  i = i + 1                                                                found = i
  goto loop                                                            i = i + 1
found:
  result = i
  goto end
done:
  result = -1
end:
```

The left version requires tracing five labels and their jump targets to know what "the state at `found:`" even means. The right version's meaning at any line is fixed by which `while`/`if` blocks textually enclose it — no jump table to hold in your head.

**What descended from it.** Every mainstream language designed after the early 1970s (C, Pascal, and everything downstream) either omits `goto` entirely or discourages it hard enough that idiomatic code almost never uses it. Structured exception handling, structured concurrency, and even modern "no early return" style guides are the same underlying argument — restrict control flow to shapes you can reason about compositionally — applied to newer kinds of jumps.

### 3. Semaphores: taking turns without a referee

**Before.** As operating systems moved from running one program at a time to interleaving several ("cooperating sequential processes," in Dijkstra's phrase), a new failure mode appeared that single-threaded programs never had: two processes reading and writing the same shared variable or resource in an interleaved, unpredictable order, corrupting it. Ad hoc fixes (disable interrupts, busy-wait on a flag) were fragile and didn't generalize.

**What was new.** In his 1965 technical report "Cooperating Sequential Processes" (EWD123), Dijkstra introduced the **semaphore**: an integer variable that can only be touched through two atomic operations, conventionally called P (from the Dutch *proberen*, "to try") and V (*verhogen*, "to increase"). `P(s)` waits until `s > 0`, then decrements it; `V(s)` increments it. Both are indivisible — no other process can observe or act on `s` in the middle of either operation. A semaphore initialized to `1` becomes a mutual-exclusion lock: whichever process calls `P` first gets in, decrementing `s` to `0`; any other process calling `P` blocks until the first calls `V`.

```
shared_counter = 0
mutex = Semaphore(1)          # a "binary" semaphore guarding one resource

def increment():
    P(mutex)                  # wait your turn, then take it
    shared_counter += 1
    V(mutex)                  # release it for the next process
```

Semaphores with an initial value greater than `1` generalize this to counting: `n` interchangeable copies of a resource (say, `n` open connections in a pool), where `P` blocks once all `n` are checked out and `V` releases one back. Dijkstra also posed the **dining philosophers problem** in this same body of work as a teaching example for the deadlock and starvation failure modes concurrent code can fall into if synchronization primitives are used carelessly.

**What descended from it.** Semaphores are the direct ancestor of essentially every synchronization primitive in use today: mutexes, condition variables, monitors (Hoare's later refinement), and the lock objects in every mainstream language's standard library (`threading.Lock` in Python, `sync.Mutex` in Go, `synchronized` in Java). Database transaction locking and the reader-writer locks inside operating system kernels trace back to the same P/V discipline.

### 4. The thread connecting all three

Shortest paths, structured programming, and semaphores look like three unrelated contributions, and the ACM's citation is careful to name that breadth rather than credit one paper. But they share a habit: in each case, Dijkstra found a small, closed set of primitives — labels finalized once each; sequence, selection, iteration; P and V — from which a correctness argument could be built and composed, instead of debugged after the fact. "Programs should be composed correctly, not just debugged into correctness," as the citation puts it. That habit is why his name survives as an adjective (a "Dijkstra-style" proof) as much as it survives as an algorithm.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [A Note on Two Problems in Connexion with Graphs](https://doi.org/10.1007/BF01386390) | Numerische Mathematik | 1959 |
| [Go To Statement Considered Harmful](https://doi.org/10.1145/362929.362947) | Communications of the ACM | 1968 |
| [Cooperating Sequential Processes](https://www.cs.utexas.edu/~EWD/transcriptions/EWD01xx/EWD123.html) *(EWD123, technical report)* | Technological University Eindhoven | 1965 |
| [Notes on Structured Programming](https://research.tue.nl/en/publications/notes-on-structured-programming) *(in* Structured Programming*, with Dahl and Hoare)* | Academic Press | 1972 |
| [The Humble Programmer](https://doi.org/10.1145/1283920.1283927) *(Turing Award lecture)* | Communications of the ACM | 1972 |

---

*Previous: [Week 06 — John McCarthy (1971)](../06-john-mccarthy-1971/)*

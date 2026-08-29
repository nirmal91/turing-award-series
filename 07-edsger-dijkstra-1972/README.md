# Week 07 — Edsger W. Dijkstra (1972)

**ACM Turing Award citation:** *"The working vocabulary of programmers everywhere is studded with words originated or forcefully promulgated by E. W. Dijkstra — display, deadly embrace, semaphore, go-to-less programming, structured programming. But his influence on programming is more pervasive than any glossary can possibly indicate. The precious gift that this Turing Award acknowledges is Dijkstra's style: his approach to programming as a high, intellectual challenge; his eloquent insistence and practical demonstration that programs should be composed correctly, not just debugged into correctness; and his illuminating perception of problems at the foundations of program design."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — Dijkstra's shortest path algorithm in about 50 lines: grow a set of nodes whose distance from the start you know for certain, one at a time, always claiming the closest unclaimed node next.

[`implementation.py`](./implementation.py) — a full working version: a `Graph` class, a priority-queue `dijkstra()`, path reconstruction, a graph file loader, a brute-force checker to verify the algorithm against, and a REPL.

```
graph (adjacency list)
    ↓ seed          priority queue starts with (start, distance=0)
    ↓ pop            take the closest unvisited node — it is now FINAL
    ↓ relax          try to shorten every neighbor's distance through it
    ↓ repeat         until the queue is empty
    ↓
  distances{}, previous{}   (previous{} rebuilds the actual path)
```

What it supports:
- Undirected roads (`edge A B 10`) and one-way roads (`edge A -> B 10`)
- Shortest distance from a node to everywhere (`dist`), or the exact path between two nodes (`path`)
- Loading a graph from a text file, the same way `implementation.py` in Week 06 loaded a `.lisp` file
- A `demo` command that loads Dijkstra's own example, shrunk from 64 Dutch cities to six
- Negative edge weights are rejected outright — the algorithm doesn't just give a wrong answer, it refuses to run (see the CS Graduate section for why)
- A REPL, a 21-case test suite (including a brute-force cross-check), and a verbose mode that prints every pop and every relaxation

```bash
python3 concept.py                        # the core idea, plain
python3 implementation.py                 # interactive REPL
python3 implementation.py netherlands.graph  # load and run a graph file
python3 implementation.py --test          # test suite (21 cases)
python3 implementation.py --verbose       # REPL that prints every step
```

Example session:

```
dijkstra> demo
  loaded: Rotterdam, Utrecht, Amsterdam, Amersfoort, Zwolle, Groningen
dijkstra> path Rotterdam Groningen
  Rotterdam -> Utrecht -> Amersfoort -> Zwolle -> Groningen  (total 235)
```

With `--verbose`, the same query prints the whole run:

```
  start: Rotterdam
  pop Rotterdam    dist=0       <- FINAL
    relax Utrecht    via Rotterdam : inf -> 60
    relax Amsterdam  via Rotterdam : inf -> 85
  pop Utrecht      dist=60      <- FINAL
    relax Amersfoort via Utrecht   : inf -> 85
  pop Amersfoort   dist=85      <- FINAL
    relax Zwolle     via Amersfoort: inf -> 135
  pop Amsterdam    dist=85      <- FINAL
  pop Zwolle       dist=135     <- FINAL
    relax Groningen  via Zwolle    : inf -> 235
  pop Groningen    dist=235     <- FINAL
```

Notice the road straight from Rotterdam to Amsterdam (85 km) never gets used. The route through Utrecht and Amersfoort is what actually gets you to Groningen fastest, and the algorithm finds that without ever comparing the two full routes to each other.

There's also a scratch file, [`scratch.graph`](./scratch.graph), for adding your own cities and roads and running `python3 implementation.py scratch.graph` yourself.

---

## Full Worked Example

Graph: six Dutch cities, driving distance in km (see `netherlands.graph`).

```
Rotterdam - Utrecht     60
Rotterdam - Amsterdam   85
Utrecht   - Amsterdam   40
Utrecht   - Amersfoort  25
Amsterdam - Amersfoort  45
Amersfoort - Zwolle     50
Amsterdam - Zwolle      110
Zwolle    - Groningen   100
```

Start: Rotterdam. Goal: shortest route to Groningen.

### Step 0 — Setup

Every node starts at distance infinity except the start, which is 0. Nothing is claimed ("settled") yet.

```
distances = { Rotterdam: 0, Utrecht: inf, Amsterdam: inf, Amersfoort: inf, Zwolle: inf, Groningen: inf }
settled   = { }
queue     = [ (0, Rotterdam) ]
```

### Step 1 — Pop Rotterdam (distance 0)

Rotterdam is the closest unclaimed node (trivially — it's the only one in the queue), so it's now **final**: nothing can ever beat a distance of 0. Relax its two roads:

```
Utrecht:   0 + 60 = 60   <  inf   → update to 60, arrived via Rotterdam
Amsterdam: 0 + 85 = 85   <  inf   → update to 85, arrived via Rotterdam
```

```
settled = { Rotterdam }
queue   = [ (60, Utrecht), (85, Amsterdam) ]
```

### Step 2 — Pop Utrecht (distance 60)

60 is the smallest value in the queue, so Utrecht is final. Relax its roads to Amsterdam and Amersfoort:

```
Amsterdam:  60 + 40 = 100   is NOT < 85   → no update, Amsterdam stays at 85
Amersfoort: 60 + 25 = 85    <  inf        → update to 85, arrived via Utrecht
```

The road from Utrecht to Amsterdam exists, but going that way (100) is worse than the direct Rotterdam-Amsterdam road (85) already found. Relaxation just means "try — and only keep it if it's actually better."

```
settled = { Rotterdam, Utrecht }
queue   = [ (85, Amsterdam), (85, Amersfoort) ]
```

### Step 3 — A tie: pop Amersfoort (distance 85)

Amsterdam and Amersfoort are now tied at 85. It genuinely does not matter which one comes out of the queue first — neither can possibly get cheaper later, because every remaining road has a positive weight, so anything still unclaimed is at least 85 away. (This implementation breaks the tie alphabetically, so Amersfoort goes first — "Amersfoort" sorts before "Amsterdam.")

Amersfoort is final at 85. Relax its road to Zwolle:

```
Zwolle: 85 + 50 = 135   <  inf   → update to 135, arrived via Amersfoort
```

```
settled = { Rotterdam, Utrecht, Amersfoort }
queue   = [ (85, Amsterdam), (135, Zwolle) ]
```

### Step 4 — Pop Amsterdam (distance 85)

Amsterdam is final at 85. Relax its road to Zwolle:

```
Zwolle: 85 + 110 = 195   is NOT < 135   → no update, Zwolle stays at 135
```

The long way to Zwolle through Amsterdam (195) loses to the way through Amersfoort (135) that Step 3 already locked in.

```
settled = { Rotterdam, Utrecht, Amersfoort, Amsterdam }
queue   = [ (135, Zwolle) ]
```

### Step 5 — Pop Zwolle (distance 135)

Zwolle is final at 135. Relax its road to Groningen:

```
Groningen: 135 + 100 = 235   <  inf   → update to 235, arrived via Zwolle
```

```
settled = { Rotterdam, Utrecht, Amersfoort, Amsterdam, Zwolle }
queue   = [ (235, Groningen) ]
```

### Step 6 — Pop Groningen (distance 235)

Groningen is final at 235. It has no unclaimed neighbors left to relax. The queue is empty. Done.

**Final distances from Rotterdam:** Utrecht 60, Amersfoort 85, Amsterdam 85, Zwolle 135, Groningen 235.

**Path to Groningen**, read backwards from `previous[]`: Groningen ← Zwolle ← Amersfoort ← Utrecht ← Rotterdam. Reversed: **Rotterdam → Utrecht → Amersfoort → Zwolle → Groningen**, total 235 km.

### Edge case — negative weight

Try to add a road with weight `-5`:

```
graph.add_edge("A", "B", -5)
ValueError: Dijkstra's algorithm requires non-negative edge weights
```

The algorithm doesn't attempt to run and get it wrong. It refuses outright, because its whole correctness argument depends on distances only ever growing as you take more roads — see "Why Negative Weights Break It" below.

### Edge case — unreachable node

Add an isolated city with no roads to it at all:

```
graph.add_node("Leeuwarden")
dijkstra(graph, "Rotterdam")["Leeuwarden"]   # inf
reconstruct_path(previous, "Rotterdam", "Leeuwarden")   # None
```

`Leeuwarden` never gets pulled out of the queue, because it's never pushed onto it in the first place — nothing relaxes an edge that doesn't exist. Its distance stays at infinity, and there is no `previous[]` entry to walk back through, so `reconstruct_path` correctly reports "no path" instead of guessing.

---

## ELI5

Imagine you want to find the fastest way to Grandma's house, and there are lots of roads that connect lots of towns.

Before, the only way to be sure you'd found the fastest way was to try every single route all the way to the end, add up the minutes for each one, and compare them all. If there are a lot of towns, that's an enormous number of routes. Way too many to check by lunchtime.

Dijkstra found a shortcut. Start at home. Look at the towns you can reach directly, and write down how far each one is. Always go next to whichever town is currently closest — you can be sure that town's number is now the real answer for it, because nothing else could possibly be closer. Then use that town to check if it makes any of its neighbor towns closer than what you'd written down before. Keep doing that, one town at a time, and by the time you run out of towns you know the fastest way to every single one, not just Grandma's.

You never had to imagine the whole trip in your head first. You just took it one closest step at a time.

---

## ELI10

In 1956, Edsger Dijkstra was a young programmer in Amsterdam, and he was thinking about something ordinary: what's the shortest driving route between two Dutch cities, Rotterdam and Groningen? He worked out an algorithm for it in about twenty minutes, sitting in a café, with no pencil or paper. He wasn't allowed to use notation that hadn't been invented yet either — this was for a demo of a brand-new computer called the ARMAC, and the whole point was to show ordinary people, not just other programmers, that the machine could do something useful and understandable. He built a simplified map of 64 Dutch cities (64, because that's exactly what fits in 6 bits — 2⁶ — which mattered when memory was measured in the hundreds of words, not gigabytes) and had the ARMAC compute the shortest route between two of them live, in front of an audience. It worked. That algorithm is still called Dijkstra's algorithm today, and it's what runs, in spirit, every time your phone's map app picks a route.

But the Turing Award citation above barely mentions shortest paths. What Dijkstra actually won for was bigger: he spent the 1960s and early 1970s arguing, loudly and rigorously, that programs should be built so a human being can actually reason about whether they're correct — not just run them and see what happens. His 1968 letter to the editor of Communications of the ACM, titled by the editor "Go To Statement Considered Harmful," argued that jumping around a program with `goto` statements makes it nearly impossible to know what state the program is in at any given line. His fix, "structured programming," said: build programs out of a small number of predictable shapes — sequence, choice, repetition — nested inside each other, and you can reason about correctness piece by piece, the same way you'd prove a math theorem step by step.

He did something similar for a second hard problem: what happens when multiple programs run on one machine at the same time and need to share things safely? Before Dijkstra, there was no standard way to stop two programs from stepping on each other's data. He invented the semaphore — a simple counter with two operations, one that waits for permission and one that grants it — as the basic building block for keeping concurrent programs from colliding. He also gave us the word for what happens when two programs each wait forever for a resource the other one is holding: "deadly embrace," what we now just call deadlock. Nearly every operating system, database, and multi-threaded program written since traces its synchronization primitives back to that idea.

---

## CS Graduate Level — Three Ideas, One Style

### 1. The State of the Art Before

By the mid-1950s, programs were written as long, flat sequences of instructions, and control flow moved around with unconditional jumps (`goto`). This was a direct reflection of how the hardware worked — a program counter jumping to an address — and early high-level languages like Fortran inherited it uncritically. The problem: as a program's use of `goto` grows, the number of possible paths a reader has to hold in their head to understand "what state could we be in at line N?" grows combinatorially. Debugging meant running the program and inspecting what actually happened; there was no discipline for reasoning about what *must* happen from the code alone.

On the graph side, the shortest-path problem had a correct but impractical answer: enumerate every path between two nodes and take the minimum. The number of simple paths in a graph grows combinatorially with its size (see `brute_force_shortest()` in `implementation.py`, which does exactly this — kept around only so the fast algorithm has something honest to check itself against). For a real road network, brute force was hopeless by hand and expensive even on a computer.

On the concurrency side, machines were starting to run multiple processes that shared memory and devices, but there was no primitive for controlling access to a shared resource beyond ad hoc, error-prone tricks. Two processes could read-modify-write the same variable in an interleaved way and silently corrupt it — a race condition with no name and no standard fix.

### 2. Shortest Paths: Greedy Relaxation, Proven Correct

Dijkstra's algorithm partitions nodes into two sets at every point in time: **settled** (their shortest distance from the start is known for certain) and **unsettled**. It repeatedly moves the closest unsettled node into the settled set, then **relaxes** every edge out of it — checks whether reaching a neighbor through this node beats the best distance found so far:

```python
while heap:
    dist, node = heapq.heappop(heap)
    if node in settled:
        continue
    settled.add(node)
    for neighbor, weight in graph.adjacency[node]:
        new_dist = dist + weight
        if new_dist < distances[neighbor]:
            distances[neighbor] = new_dist
            previous[neighbor] = node
            heapq.heappush(heap, (new_dist, neighbor))
```

The correctness argument is an induction on the order nodes get settled. **Claim:** when a node is popped from the queue, its distance is final. **Proof sketch:** suppose not — suppose the true shortest path to node `X` is shorter than what we popped. That true path must, at some point, leave the settled set through some edge into an unsettled node `Y`. Because all edge weights are non-negative, the distance to `Y` along that true path is already ≥ the distance we'd have computed for `Y` — and `Y`'s distance was already in the queue, ahead of `X`'s, contradicting that we popped `X` first. This is exactly where the non-negative weight assumption gets used, and exactly why the code raises `ValueError` on a negative edge rather than silently computing a wrong answer: the proof simply does not hold otherwise.

With a binary heap, each node is popped once (O(V log V) total) and each edge is relaxed once (O(E log V) total, since each relaxation may push onto the heap), giving O((V + E) log V) — a world away from checking every path.

### 3. Why Negative Weights Break It

If an edge can be negative, a node already marked settled might later be reachable more cheaply through a node that hasn't been discovered yet — the induction step above fails, because "distance only grows as you add edges" is no longer true. Dijkstra's algorithm doesn't detect this failure; it just returns a wrong, too-large answer, silently. `Graph.add_edge()` in `implementation.py` refuses negative weights up front rather than let that happen. The general problem (shortest paths with negative edges, but no negative cycles) is solved by **Bellman-Ford** (1958), which relaxes every edge V-1 times instead of using a priority queue — slower (O(VE)) but correct under weaker assumptions. **A\*** (1968) goes the other direction: it adds a heuristic estimate of remaining distance to prioritize the search, which is what makes GPS route-finding fast enough to feel instant on continent-sized road networks.

### 4. Structured Programming: Programs You Can Prove

The claim in "Go To Statement Considered Harmful" (1968) is precise, not just a style preference: understanding a running program requires being able to describe "where you are" with a small set of coordinates. In a program built only from sequence, selection (`if`), and repetition (`while`/`for`), your position is fully described by your position in the (statically nested) program text plus the values of the loop counters — a small, structured coordinate. An unrestricted `goto` breaks this: the set of places you might have jumped from is unbounded, so "where you are" stops correlating with "where you are in the text."

This is the same idea Dijkstra pushed further with **Hoare logic**-style reasoning (developed alongside Tony Hoare): a structured statement can be verified with a precondition and postcondition, and structured statements compose — the postcondition of one becomes the precondition of the next, and a `while` loop can be verified with a **loop invariant**, a condition that's true before and after every iteration. None of this composes cleanly with arbitrary jumps. The 1972 book *Structured Programming*, co-authored with Dahl and Hoare, turned this into a discipline: programs developed by **stepwise refinement**, starting from an abstract, obviously-correct sketch and mechanically refining it into working code, each refinement preserving correctness.

### 5. Semaphores and the "THE" System: Concurrency You Can Reason About

In "Cooperating Sequential Processes" (1965/1968) Dijkstra introduced the **semaphore**: an integer with exactly two atomic operations, conventionally named `P` (from the Dutch *proberen*, "to try," — wait/decrement, blocking if the value would go negative) and `V` (*verhogen*, "to increase" — signal/increment, waking a waiter if one exists). A semaphore initialized to 1 becomes a **mutex**: `P` before a critical section, `V` after, and only one process can be inside at a time. A semaphore initialized to `N` limits N concurrent holders — a counting semaphore, useful for a fixed pool of resources.

He then used exactly this primitive to build "THE" Multiprogramming System (1968), one of the first operating systems organized as **explicit layers**, each one providing a clean abstraction to the layer above and depending only on the layer below (processor allocation at the bottom, up through memory, drivers, the operator's console at the top). This separation — reasoning about one layer at a time, each built only from guarantees the layer below already proved — is the same discipline as structured programming, applied to system architecture instead of a single function. It's also where "deadly embrace" (deadlock: two or more processes each holding a resource the other needs, and each waiting forever) gets named and analyzed as a formal hazard to design around, not just a bug you hit and patch.

### 6. What Descended From It

- **Routing.** Link-state routing protocols (OSPF, IS-IS) run Dijkstra's algorithm on every router to compute shortest paths through the network. Every GPS and mapping app runs a close variant (usually A\*) on a road graph.
- **Structured control flow.** Every mainstream language designed after the mid-1970s (C, Pascal, and everything downstream) makes `goto` awkward or unavailable by default and makes `if`/`while`/`for` the normal way to write control flow. Structured exception handling (`try`/`catch`) is a direct descendant of the same "bounded, nameable program state" argument.
- **Formal verification.** Hoare logic, loop invariants, and precondition/postcondition reasoning are still exactly how introductory formal-methods courses teach program correctness, and the same ideas underpin modern tools like model checkers and verified compilers.
- **Concurrency primitives.** Mutexes, condition variables, and monitors (Hoare, 1974) are all direct descendants of the semaphore. `threading.Semaphore` in Python, `sync.Mutex` in Go, and every lock in every language's standard library trace back to `P` and `V`.
- **Layered systems.** The "THE" system's layered abstraction is the same idea behind the OSI/TCP-IP networking stack, modern kernel/driver separation, and virtual memory as a clean abstraction the layers above don't have to think about.

### 7. Lasting Impact

Dijkstra's throughline across all three contributions is the same conviction: a program is a mathematical object, and you should be able to reason about it with the same rigor you'd bring to a proof, rather than trust it because it happened to run correctly on your test cases. Shortest-path relaxation is provably correct because non-negative weights make "settled" mean "settled." Structured programming is arguable-about because a small, bounded set of control shapes gives you a small, bounded description of program state. Semaphores are safe to reason about because `P` and `V` are atomic, so a proof about one process's behavior doesn't get invalidated by what another process might be doing in between. Every one of those is the same move: constrain the shape of the thing, so a human being — not just a machine — can actually think about it correctly.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [A Note on Two Problems in Connexion with Graphs](https://doi.org/10.1007/BF01386390) | Numerische Mathematik | 1959 |
| [Go To Statement Considered Harmful](https://doi.org/10.1145/362929.362947) | Communications of the ACM | 1968 |
| [The Structure of the "THE"-Multiprogramming System](https://doi.org/10.1145/363095.363143) | Communications of the ACM | 1968 |
| [Cooperating Sequential Processes](https://www.cs.utexas.edu/~EWD/transcriptions/EWD01xx/EWD123.html) *(EWD 123, later reprinted in F. Genuys, ed., *Programming Languages*)* | Technical report, Technological University Eindhoven | 1965 |
| *Structured Programming* *(book, with O.-J. Dahl and C.A.R. Hoare)* | Academic Press | 1972 |
| [The Humble Programmer](https://doi.org/10.1145/1283920.1283927) *(Turing Award lecture)* | Communications of the ACM | 1972 |

---

*Previous: [Week 06 — John McCarthy (1971)](../06-john-mccarthy-1971/)*

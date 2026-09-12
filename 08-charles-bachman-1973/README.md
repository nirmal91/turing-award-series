# Week 08 — Charles W. Bachman (1973)

**ACM Turing Award citation:** *"for his outstanding contributions to database technology"*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — Bachman's idea in about 55 lines: a SET is one owner record ring-linked to a chain of member records, the last one pointing back to the owner. Walking the ring is one pointer-follow; so is jumping from a member straight back to its owner.

[`implementation.py`](./implementation.py) — a full working navigational database: a schema of record types and named set types, STORE/CONNECT/DISCONNECT to build the pointer structure, FIND FIRST/NEXT/PRIOR/OWNER to navigate it, currency indicators to track "where the program is standing right now," and a linear scan to show what you had to do before any of this existed.

```
record / set              (schema: record types, and named owner->member rings)
    -> store                   create a record instance
    -> connect                 splice a record into a set occurrence's ring
    -> find first/next/prior/owner   move the currency indicator
    -> printed result
```

What it supports:
- Record types (`record EMPLOYEE name`) and set types (`set DEPT-EMP owner DEPARTMENT member EMPLOYEE`) — the schema
- `store`, `connect`, `disconnect` — build the pointer rings
- `find first / next / prior / owner` — navigate them, one pointer at a time, tracked by currency indicators (`current of run-unit`, `current of record type`, `current of set`)
- `scan` — the "before": a linear scan through every record of a type, with no stored relationship to follow
- One record type can be a member of more than one independent set at once — the actual network, not a tree
- A REPL, a schema-and-data script loader, a 17-case test suite, and a verbose mode that prints every pointer update

```bash
python3 concept.py                       # the core idea, plain
python3 implementation.py                # interactive REPL
python3 implementation.py company.ids    # load and run a schema+data script
python3 implementation.py --test         # test suite (17 cases)
python3 implementation.py --verbose      # REPL that prints every pointer update
```

Example session:

```
navigator> record DEPARTMENT name
defined record type DEPARTMENT(name)
navigator> record EMPLOYEE name
defined record type EMPLOYEE(name)
navigator> set DEPT-EMP owner DEPARTMENT member EMPLOYEE
defined set type DEPT-EMP: DEPARTMENT owns EMPLOYEE
navigator> store DEPARTMENT name=Sales
stored DEPARTMENT-1 DEPARTMENT(name=Sales)
navigator> store EMPLOYEE name=Alice
stored EMPLOYEE-1 EMPLOYEE(name=Alice)
navigator> store EMPLOYEE name=Bob
stored EMPLOYEE-2 EMPLOYEE(name=Bob)
navigator> connect DEPT-EMP DEPARTMENT-1 EMPLOYEE-1
connected EMPLOYEE-1 into DEPT-EMP owned by DEPARTMENT-1
navigator> connect DEPT-EMP DEPARTMENT-1 EMPLOYEE-2
connected EMPLOYEE-2 into DEPT-EMP owned by DEPARTMENT-1
navigator> find first DEPT-EMP DEPARTMENT-1
  EMPLOYEE-1 EMPLOYEE(name=Alice)
navigator> find next DEPT-EMP
  EMPLOYEE-2 EMPLOYEE(name=Bob)
navigator> find owner DEPT-EMP
  DEPARTMENT-1 DEPARTMENT(name=Sales)
```

`find owner` from Bob doesn't walk back through Alice to reach Sales. It follows one direct pointer that IDS stored on every member record for exactly this reason.

---

## Full Worked Example

### Setup

Two record types, one set type: `DEPARTMENT` owns `EMPLOYEE`, set name `DEPT-EMP`. We store one department, `Sales` (`DEPARTMENT-1`), and three employees: `Alice` (`EMPLOYEE-1`), `Bob` (`EMPLOYEE-2`), `Carol` (`EMPLOYEE-3`).

**Step 0 — a new owner's ring is a self-loop.** The moment `DEPARTMENT-1` is stored, its `DEPT-EMP` ring is initialized to point at itself in both directions — an owner with no members is a ring of one, closed on itself. This is what "the set exists but is empty" looks like as pointers.

```
DEPARTMENT-1.ring_next[DEPT-EMP]  = DEPARTMENT-1
DEPARTMENT-1.ring_prior[DEPT-EMP] = DEPARTMENT-1
```

**Step 1 — connect Alice.** `connect DEPT-EMP DEPARTMENT-1 EMPLOYEE-1`. The rule: splice the new member in between the current "last" record in the ring and the owner. Right now "last" is the owner itself (the ring has nothing else in it), so Alice gets inserted right after the owner and right before it too — the ring now has two nodes.

```
before:  DEPARTMENT-1 -> DEPARTMENT-1                (self-loop)
after:   DEPARTMENT-1 -> EMPLOYEE-1 -> DEPARTMENT-1   (ring of two)

EMPLOYEE-1.owner_of[DEPT-EMP] = DEPARTMENT-1   (direct pointer, set once, here)
```

**Step 2 — connect Bob.** `connect DEPT-EMP DEPARTMENT-1 EMPLOYEE-2`. "Last" is now `owner.ring_prior[DEPT-EMP]`, which is `EMPLOYEE-1` (the only member so far). Bob is spliced in between Alice and the owner.

```
before:  DEPARTMENT-1 -> EMPLOYEE-1 -> DEPARTMENT-1
after:   DEPARTMENT-1 -> EMPLOYEE-1 -> EMPLOYEE-2 -> DEPARTMENT-1
```

**Step 3 — connect Carol.** Same rule, "last" is now Bob. Carol lands after Bob, before the owner.

```
after:   DEPARTMENT-1 -> EMPLOYEE-1 -> EMPLOYEE-2 -> EMPLOYEE-3 -> DEPARTMENT-1
```

That's the whole ring: `Sales -> Alice -> Bob -> Carol -> Sales`. Every `connect` was a handful of pointer reassignments, nothing else touched — not Alice's data, not Bob's, not a file scan of any kind.

### Navigating it: FIND FIRST, then FIND NEXT

**`find first DEPT-EMP DEPARTMENT-1`.** Look at `DEPARTMENT-1.ring_next[DEPT-EMP]`. It's `EMPLOYEE-1` — not the owner itself, so the set isn't empty. Currency of set `DEPT-EMP` becomes `EMPLOYEE-1`; currency of record type `EMPLOYEE` and of the whole run-unit also become `EMPLOYEE-1`. Print Alice.

**`find next DEPT-EMP`.** Read the currency of set `DEPT-EMP`: it's `EMPLOYEE-1`. Follow `EMPLOYEE-1.ring_next[DEPT-EMP]`: that's `EMPLOYEE-2`, and its kind is `EMPLOYEE`, not the owner type `DEPARTMENT` — so it's a real member, not a wraparound. Currency of set moves to `EMPLOYEE-2`. Print Bob.

**`find next DEPT-EMP`** again. Currency is `EMPLOYEE-2`. Follow its `ring_next`: `EMPLOYEE-3`. Print Carol.

**`find next DEPT-EMP`** once more. Currency is `EMPLOYEE-3`. Follow its `ring_next`: that lands back on `DEPARTMENT-1` — whose kind *is* the set's owner type. That's the ring closing, not a fourth member. The command reports "end of set" and leaves currency exactly where it was, on Carol, instead of silently treating the owner as if it were a fourth employee.

### FIND OWNER: the payoff for storing a direct pointer

Suppose the program's current record (currency of run-unit) is Carol, from the walk above. `find owner DEPT-EMP` does **not** walk the ring back through Bob and Alice to find Sales. It reads `EMPLOYEE-3.owner_of[DEPT-EMP]` directly — a single pointer, stored on Carol's own record the moment she was connected — and gets `DEPARTMENT-1` in one step. That's the second half of Bachman's design: not just "members chained together," but "every member also knows its owner without asking anyone."

### Edge case: FIND NEXT with nothing connected yet

Given `DEPARTMENT-2`, `Engineering`, freshly stored, with zero employees connected: `find first DEPT-EMP DEPARTMENT-2` reads `DEPARTMENT-2.ring_next[DEPT-EMP]`, which is still the self-loop pointer — `DEPARTMENT-2` itself. Since the candidate's kind matches the set's owner type, this is recognized as "empty," and `find first` returns nothing rather than a nonsense employee. There's no error, and no employee record is fabricated — the ring, correctly, says there's nobody there.

### Edge case: reconnecting after DISCONNECT

`disconnect DEPT-EMP EMPLOYEE-2` (Bob) repairs the ring around him: Alice's `ring_next` is pointed straight at Carol, and Carol's `ring_prior` is pointed straight at Alice, skipping over Bob entirely. Bob's own `owner_of[DEPT-EMP]` is cleared to nothing. Bob still exists as a record — his name, his key — but he is no longer part of that ring. He can now be `connect`ed into a *different* department's `DEPT-EMP` occurrence (say, `DEPARTMENT-2`), because the one-owner-at-a-time rule only blocks reconnecting to the *same* set type while an owner pointer is still set; disconnecting clears exactly that pointer and nothing else.

---

## ELI5

Imagine a big box of index cards, one card per employee, and you want to find everyone in the Sales department. Before this invention, you had to pick up every single card in the box and check if it said "Sales" on it. If the box has thousands of cards, that takes forever, and you have to do it again every time you ask.

Charles Bachman had an idea: what if the Sales card had a little string tied to the first Sales employee's card, and that card had a string tied to the next one, and so on, until the last string ties back to the Sales card? Now finding everyone in Sales means following strings, not checking every card in the box. And if you're holding an employee's card, there's also a short string straight back to their department card, so you always know whose team you're on without following the long way around.

---

## ELI10

Charles Bachman didn't have a PhD, and he wasn't a scientist by training — he was an engineer, and he spent his whole career at companies, not universities. That alone made him unusual among Turing Award winners when he received it in 1973: he was the first winner without a doctorate, and the first to win for a specific piece of software rather than a theory.

The software was called IDS, the Integrated Data Store, and he built it starting in 1960 at General Electric, where one factory department's paperwork problem — tracking parts, orders, and billing without every department inventing its own filing system — turned into a genuine breakthrough. By 1963, running on one of the very first commercial disk drives (a huge deal at the time — before disks, computers mostly read data in the fixed order it was written on tape, one record after another, with no way to jump around), Bachman's team had a system that stored not just the records but the *connections between them*, as chains of pointers on the disk. A department's card pointed at its first employee's card, which pointed at the next, and so on. Looking something up meant following a pointer, not re-reading a whole file.

The idea was powerful enough that an industry standards group, CODASYL — the same group behind the COBOL programming language — turned it into an official specification between 1969 and 1971, called the network data model. "Network" because a single record, like an employee, could be linked into more than one of these chains at once: their department's chain and their project's chain, at the same time, without duplicating anything. That was a real advantage over the other big database style of the era, IBM's hierarchical model, which only let a record have one parent.

Bachman's 1973 Turing Award lecture was called "The Programmer as Navigator." That title says exactly how this style of programming felt: the program didn't ask a question and wait for an answer, it moved a position through the stored structure step by step, deciding at each pointer where to go next. A few years earlier, in 1970, a mathematician at IBM named E. F. Codd had proposed something quite different — the relational model, where you describe *what* you want in a table and a query language figures out how to get it, instead of you navigating there yourself. That disagreement between navigating and querying became one of the defining arguments in the history of databases, and for a long time it wasn't obvious which side would win.

---

## CS Graduate Level — Records, Sets, and the Navigational Style

### 1. Before IDS: sequential files, and no stored relationships

Through the 1950s and into the early 1960s, the dominant storage medium was magnetic tape: a sequence of records read in order, front to back. There was no efficient way to jump to an arbitrary record, and there was certainly no way to store "this record relates to that one" as anything but a shared field value you had to search for. Finding every `EMPLOYEE` record belonging to a given `DEPARTMENT` meant a full pass over the employee file, testing a department field on every record — exactly what `scan_linear()` in this chapter's `implementation.py` does, and exactly the cost this chapter's whole design exists to avoid. That cost is not incidental: it is `O(n)` in the number of records of that type, and it is paid again, in full, on every single query — nothing learned from the first scan survives to make the second one cheaper.

### 2. What was new: records, sets, and stored pointers

Bachman's IDS, running on one of the first magnetic disk drives (which, unlike tape, could seek directly to an arbitrary location), stored the relationship itself, physically, as a chain of pointers threaded through the records on disk. He called a named 1:N relationship a **set**: one **owner** record type, one or more **member** record types, and, per occurrence, a ring of pointers connecting one specific owner to its specific members — closing back on itself so the last member's pointer leads back to the owner, not off into nothing.

`implementation.py`'s `Record` class mirrors this directly: `ring_next` and `ring_prior`, keyed by set name, form the chain; `owner_of`, also keyed by set name, is a second, direct pointer from member straight back to owner — an optimization IDS made so that "who owns this?" never requires walking the ring at all:

```python
class Record:
    def __init__(self, kind, key, fields):
        self.kind = kind
        self.key = key
        self.fields = fields
        self.ring_next = {}     # set_name -> next Record in that ring
        self.ring_prior = {}    # set_name -> prior Record in that ring
        self.owner_of = {}      # set_name -> the Record that owns this one
```

Two operations follow directly from this shape. `connect()` splices a member in between the ring's current last node and the owner — always an `O(1)` pointer rewrite, regardless of how many members already exist:

```python
last = owner.ring_prior[set_name]
last.ring_next[set_name] = member
member.ring_prior[set_name] = last
member.ring_next[set_name] = owner
owner.ring_prior[set_name] = member
member.owner_of[set_name] = owner
```

And `find_owner()` is a single dictionary lookup, not a traversal:

```python
owner = current.owner_of.get(set_name)
```

### 3. Currency indicators: the state a navigational program carries

A relational query is stateless: you send a declarative statement, you get a result set back, and the system's internal position (if it had one) is invisible and irrelevant to you. A CODASYL / DBTG program is the opposite. It carries an explicit position, called a **currency indicator**, and every DML statement both reads and updates it. The standard defines several: current of the run-unit (the very last record touched by anything), current of each record type, and current of each set type. `Database` in `implementation.py` keeps exactly these three:

```python
self.current_run_unit = None          # key of the last record touched
self.current_of_type = {}             # record type name -> key
self.current_of_set = {}              # set type name -> key
```

`FIND FIRST <set> OWNER <key>` and `FIND NEXT <set>` don't take a record as an argument the way a function call normally would — `find_next(set_name)` takes only the set's name, because the record it operates on is implicit: whatever the currency indicator for that set says right now. This is precisely Bachman's "navigator" metaphor made literal in code: the program's state includes *where it is standing*, and each command moves that position rather than asking a fresh question from scratch.

### 4. The network property, and why it beat a strict hierarchy

IBM's contemporaneous hierarchical model (as implemented in IMS, released 1968) restricted every record to exactly one parent — a tree. That is a real constraint: an employee who belongs to both a department and a project cannot honestly have two parents in a tree, so a hierarchical design has to pick one as the "real" parent and either duplicate the employee's data under the other, or drop the relationship entirely.

`implementation.py`'s test suite (`run_tests()`, case 9) pins this down directly: one `EMPLOYEE` record, `Alice`, is connected into *two* independent set types at once — `DEPT-EMP` (owned by her department) and `PROJ-EMP` (owned by her project) — and both `owner_of` pointers resolve correctly, on the same underlying record, with no duplication:

```python
db.connect("DEPT-EMP", sales.key, alice.key)
db.connect("PROJ-EMP", launch.key, alice.key)
check("Alice's department owner is Sales", alice.owner_of["DEPT-EMP"].key == sales.key)
check("the SAME Alice record's project owner is Launch", alice.owner_of["PROJ-EMP"].key == launch.key)
```

That's the "network" in network data model: a general graph of owner/member relationships, not a tree. It's also exactly why Bachman's model needed currency indicators *per set type*, not one global position — a program navigating Alice's department membership and her project membership at the same time needs to track both positions independently.

### 5. What replaced it, and what survived

E. F. Codd's 1970 paper, "A Relational Model of Data for Large Shared Data Banks," argued for the opposite trade: give up the programmer's explicit control over the physical access path, and in exchange, let the system figure out how to answer a declarative query — expressed against tables, with no pointers exposed to the application at all. Codd's own stated motivation was largely about this chapter's technology directly: application programs written against CODASYL-style navigational structures broke whenever the physical storage layout changed, because the navigation path *was* the physical layout. The relational model decoupled the two.

Through the 1970s and into the 1980s, this became a real industry argument, not an obvious call — CODASYL-derived systems (Cullinet's IDMS chief among them, itself a direct descendant of Bachman's IDS) remained commercially dominant for years after Codd's paper, in part because early relational systems were genuinely slower before query optimizers matured. Relational systems eventually won the argument for general-purpose transactional databases, and SQL is the language every working engineer meets first today.

But the navigational style didn't vanish — it resurfaced wherever an application legitimately wants explicit control over traversal rather than a query planner's guess. Graph databases (Neo4j's property graph model, for one) are, at the level of stored representation, a direct descendant: nodes and typed relationships, walked one pointer-follow at a time, is Bachman's set occurrence with a friendlier name. Pointer-chasing through an in-memory object graph — the everyday act of writing `department.employees[i].project.owner` in any object-oriented language — is the same idea again, minus the disk. Bachman himself is also credited, separately, with the **Bachman diagram**, a box-and-arrow notation for drawing a schema's record types and set types, which is a direct ancestor of the entity-relationship diagrams every database course still teaches, on both sides of the navigational/relational divide.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [Integrated Data Store: A General-Purpose Programming System for Random-Access Memories](https://www.semanticscholar.org/paper/A-general-purpose-programming-system-for-random-Bachman-Williams/796b7cd42f3d6f0fcfaadf569e6c7b7ffc127664) *(Bachman & Williams, pp. 411-422)* | AFIPS Fall Joint Computer Conference | 1964 |
| [Data Base Task Group Report to the CODASYL Programming Language Committee](https://dl.acm.org/doi/book/10.1145/1387145) *(network model DDL/DML specification; revised April 1971)* | CODASYL | 1969 |
| [The Programmer as Navigator](https://doi.org/10.1145/355611.362534) *(1973 Turing Award lecture)* | Communications of the ACM | 1973 |
| [A Relational Model of Data for Large Shared Data Banks](https://doi.org/10.1145/362384.362685) *(E. F. Codd — the model proposed to replace this one)* | Communications of the ACM | 1970 |

---

*Previous: [Week 07 — Edsger W. Dijkstra (1972)](../07-edsger-dijkstra-1972/)*

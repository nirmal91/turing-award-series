# Week 08 — Charles W. Bachman (1973)

**ACM Turing Award citation:** *"For his outstanding contributions to database technology."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — the whole idea in ~55 lines: a `Record`, a `connect()` that splices a member onto a ring, and a `members_of()` that walks the ring. No schema, no query language, no currency indicators — just the ring.

[`implementation.py`](./implementation.py) — a full navigational DML interpreter that mirrors CODASYL's 1969 Data Base Task Group (DBTG) language: typed records, named `SET` relationships between an owner record type and a member record type, and the three moves a 1960s programmer had — `FIND FIRST`, `FIND NEXT`, `FIND OWNER` — plus `STORE`, `CONNECT`, and `DISCONNECT`. It also tracks *currency indicators*: "what record am I positioned at right now," which is what let DBTG commands stay short (`CONNECT DEPT-EMP` with no arguments works because the database already knows your current department and your current employee).

```
DEFINE SET (declare an owner/member relationship)
    -> STORE (create records)
    -> CONNECT (splice a record into a set's ring)
    -> FIND FIRST / FIND NEXT / FIND OWNER (navigate the ring)
    -> currency indicators track "where you are" between commands
```

What it supports:
- `DEFINE SET name OWNER kind MEMBER kind` — declare a set type (a 1-to-many relationship)
- `STORE kind field=value ...` — create a record; it becomes "current"
- `CONNECT name` / `CONNECT name OWNER id MEMBER id` — splice a record into a set's ring, implicitly (using currency) or explicitly
- `FIND FIRST name [OWNER id]`, `FIND NEXT name`, `FIND OWNER name` — the only ways to navigate; there is no scan and no join
- `DISCONNECT name [MEMBER id]` — remove a member and re-link the ring around it
- `PRINT CURRENT | PRINT id | PRINT ALL kind`, `DUMP` — inspect state (not part of the historical DML, added for visibility)
- A record can be a member of **two different sets at once** (an employee in a department set *and* a project set) — the network property a strict tree cannot express

How to run it:
```bash
python3 concept.py                       # the core idea, plain
python3 implementation.py                # full interactive REPL
python3 implementation.py scratch.ids    # run a DML script (try this one first)
python3 implementation.py --test         # 18 test cases
python3 implementation.py --verbose      # REPL that narrates currency changes
```

Example session:
```
$ python3 implementation.py
ids> DEFINE SET DEPT-EMP OWNER DEPARTMENT MEMBER EMPLOYEE
defined set DEPT-EMP: DEPARTMENT owns EMPLOYEE
ids> STORE DEPARTMENT name=Engineering
stored DEPARTMENT#1 {'name': 'Engineering'}
ids> STORE EMPLOYEE name=Alice
stored EMPLOYEE#1 {'name': 'Alice'}
ids> CONNECT DEPT-EMP
connected DEPARTMENT#1 -> EMPLOYEE#1 into set DEPT-EMP
ids> FIND FIRST DEPT-EMP
EMPLOYEE#1 {'name': 'Alice'}
ids> FIND OWNER DEPT-EMP
DEPARTMENT#1 {'name': 'Engineering'}
```

---

## Full Worked Example

This walks through exactly what `implementation.py` does, one pointer at a time, using the numbers from [`scratch.ids`](./scratch.ids).

### Setup: declaring the schema

```
DEFINE SET DEPT-EMP OWNER DEPARTMENT MEMBER EMPLOYEE
```

This does not create anything yet. It registers one fact: `db.set_types["DEPT-EMP"] = ("DEPARTMENT", "EMPLOYEE")`. Every future `CONNECT DEPT-EMP` will be checked against this — you cannot connect a `PROJECT` as if it were a `DEPARTMENT`.

### Step 1: STORE the owner

```
STORE DEPARTMENT name=Engineering
```

Internally: `db.counters["DEPARTMENT"]` goes from nothing to `1`, and `db.records["DEPARTMENT#1"] = {"kind": "DEPARTMENT", "fields": {"name": "Engineering"}}`. Two currency indicators update: `current_run_unit = "DEPARTMENT#1"` and `current_of_record_type["DEPARTMENT"] = "DEPARTMENT#1"`.

At this point `DEPARTMENT#1` exists but owns nothing. There is no ring for it yet — `db.ring_next` has no entry for `("DEPT-EMP", "DEPARTMENT#1")`.

### Step 2: STORE a member and CONNECT it

```
STORE EMPLOYEE name=Alice
CONNECT DEPT-EMP
```

`STORE` creates `EMPLOYEE#1` and makes it current (`current_of_record_type["EMPLOYEE"] = "EMPLOYEE#1"`).

`CONNECT DEPT-EMP` with no explicit ids looks up the set type (`DEPARTMENT` owns `EMPLOYEE`), then reads the *current* department (`DEPARTMENT#1`) and the *current* employee (`EMPLOYEE#1`) — this is the currency mechanism doing its job: you never had to type either id.

Inside `connect()`, since `("DEPT-EMP", "DEPARTMENT#1")` has no ring yet, this is the first-member case:
```
ring_next[("DEPT-EMP", "DEPARTMENT#1")] = "EMPLOYEE#1"
ring_next[("DEPT-EMP", "EMPLOYEE#1")]   = "DEPARTMENT#1"
```
That second line is the ring closing — `EMPLOYEE#1`'s "next" pointer is the owner itself. One member, one ring, pointing back to where it started:

```
DEPARTMENT#1 ──next──▶ EMPLOYEE#1 ──next──▶ DEPARTMENT#1   (closed ring)
```

### Step 3: add two more members

```
STORE EMPLOYEE name=Bob
CONNECT DEPT-EMP
STORE EMPLOYEE name=Carol
CONNECT DEPT-EMP
```

Each `CONNECT` now hits the "ring already exists" branch: walk from the owner, following `ring_next`, until you find the node whose `next` currently points back to the owner (the *tail*), then splice the new member in before that closing link.

Before adding Bob, the tail is `EMPLOYEE#1` (its next is `DEPARTMENT#1`). So:
```
ring_next[("DEPT-EMP", "EMPLOYEE#1")] = "EMPLOYEE#2"   # was DEPARTMENT#1, now points to Bob
ring_next[("DEPT-EMP", "EMPLOYEE#2")] = "DEPARTMENT#1" # Bob closes the ring instead
```
Same again for Carol, walking `DEPARTMENT#1 -> EMPLOYEE#1 -> EMPLOYEE#2` to find the new tail (`EMPLOYEE#2`) and splicing Carol in after it:
```
ring_next[("DEPT-EMP", "EMPLOYEE#2")] = "EMPLOYEE#3"
ring_next[("DEPT-EMP", "EMPLOYEE#3")] = "DEPARTMENT#1"
```

The full ring is now:
```
DEPARTMENT#1 ─▶ EMPLOYEE#1(Alice) ─▶ EMPLOYEE#2(Bob) ─▶ EMPLOYEE#3(Carol) ─▶ DEPARTMENT#1
```
Read the pointer table left to right and you can see it's one long chain closing on itself — this is the literal "ring" IDS wrote to disk in 1963: no index, no separate list of members, just each record carrying the address of the next one.

### Step 4: navigate — FIND FIRST, then FIND NEXT

```
FIND FIRST DEPT-EMP OWNER DEPARTMENT#1
```
`find_first` looks at `ring_next[("DEPT-EMP", "DEPARTMENT#1")]`, which is `"EMPLOYEE#1"`. Since that's not the owner itself, it's not an empty set — so `EMPLOYEE#1` becomes current, and it's returned: **Alice**.

```
FIND NEXT DEPT-EMP
```
`find_next` looks at `current_of_set["DEPT-EMP"]` (`EMPLOYEE#1`), follows `ring_next` to `EMPLOYEE#2`. Is `EMPLOYEE#2` the owner? No (`owner_of[("DEPT-EMP", "EMPLOYEE#1")] == "DEPARTMENT#1"`, and `EMPLOYEE#2 != DEPARTMENT#1`), so no wrap: **Bob**.

```
FIND NEXT DEPT-EMP
```
Same logic from `EMPLOYEE#2`: next is `EMPLOYEE#3`, not the owner: **Carol**.

### Edge case: FIND NEXT past the last member

If you call `FIND NEXT DEPT-EMP` one more time, `ring_next[("DEPT-EMP", "EMPLOYEE#3")]` is `"DEPARTMENT#1"` — and `owner_of[("DEPT-EMP", "EMPLOYEE#3")]` is *also* `"DEPARTMENT#1"`. Next equals owner, so `wrapped = True`. The program reports `(end of set DEPT-EMP -- back at owner DEPARTMENT#1)` instead of silently looping forever or crashing. Currency is left positioned *at the owner* — so the very next `FIND NEXT` would walk you straight back to Alice. That's not an accident: positioned-at-owner is exactly the state `FIND FIRST` starts from, so "wrap and go again" falls out of the same code path for free.

### The network part: one record, two owners

```
STORE PROJECT name=Compiler
CONNECT PROJ-EMP OWNER PROJECT#1 MEMBER EMPLOYEE#1
FIND OWNER PROJ-EMP
```
`EMPLOYEE#1` (Alice) is *already* a member of `DEPT-EMP`, owned by `DEPARTMENT#1`. This second `CONNECT` makes her a member of a completely different set, `PROJ-EMP`, owned by `PROJECT#1`. Now `owner_of` holds two separate entries for Alice:
```
owner_of[("DEPT-EMP", "EMPLOYEE#1")] = "DEPARTMENT#1"
owner_of[("PROJ-EMP", "EMPLOYEE#1")] = "PROJECT#1"
```
`FIND OWNER PROJ-EMP` correctly returns `PROJECT#1`, not `DEPARTMENT#1` — because "owner" is always relative to *which set* you're asking about. A hierarchical database (IBM's IMS, the dominant alternative at the time) forces every record into exactly one parent. Bachman's model lets the same record sit in as many rings as the application needs. That's the "network" in network data model.

### Failure case: acting without currency

If you call `FIND NEXT DEPT-EMP` before ever calling `FIND FIRST` or `CONNECT`, `current_of_set.get("DEPT-EMP")` is `None`, and the code raises `ValueError("not currently positioned in set 'DEPT-EMP' (FIND FIRST first)")` rather than guessing. This mirrors a real DBTG failure mode: navigational access means the *program* is responsible for knowing where it is, and asking to move before you've arrived anywhere is a program bug, not a database question.

---

## ELI5

Imagine you keep every kid's homework in one pile, and every teacher's grade book in a totally different pile, and nothing connects them. If you want to know which homework belongs to which kid, you have to go looking, page by page, hoping the names match.

Charles Bachman's idea was: what if every kid's paper had a little arrow drawn on it pointing to the *next* kid in their class, and the *last* kid's arrow pointed back to the teacher? Now finding "everyone in Ms. Alice's class" isn't searching — you just follow the arrows, one at a time, until you're back at Ms. Alice. And a kid can have TWO sets of arrows: one for their class, one for their soccer team. Same kid, two rings of arrows, no copying their name onto two different piles.

That's what Bachman built in 1963, for a computer instead of paper: records connected by pointers instead of piles you have to search.

---

## ELI10

Before 1963, if a company wanted software to track "which employees work in which department," a programmer usually wrote a custom file format just for that one program — a flat list of employee records, maybe with the department name copied into every single one. If Payroll needed the same information, Payroll wrote its *own* file, often duplicating the same facts. There was no shared, general-purpose way to store "this record belongs to that record" that multiple programs could use.

Charles Bachman, working at General Electric, built the Integrated Data Store (IDS), running by 1963. His idea was to store relationships as physical rings of pointers: a department record points to its first employee, that employee points to the next, and the last one points back to the department, closing the loop. To answer "who works in Engineering," a program didn't search anything — it started at the Engineering record and followed pointers until it arrived back where it started. This was fast, on 1960s hardware where scanning a whole file was expensive, and it let multiple applications share one "integrated" store instead of each keeping a private copy.

In 1969, an industry group called CODASYL (the same COBOL standards committee) turned Bachman's design into a formal standard: the network data model. "Network" meant a record could be a member of *several* different rings at once — an employee could belong to a department ring and a project ring simultaneously — something the era's other popular design, IBM's strictly tree-shaped hierarchical model (IMS), could not express without duplicating data. Bachman won the 1973 Turing Award for this work, and titled his acceptance lecture "The Programmer as Navigator" — because using his database meant writing code that walked, step by step, from record to record, rather than describing what you wanted and letting the system figure out how to get it.

---

## CS Graduate Level

### State of the art before IDS

In the early 1960s, "database" was not yet a category of software. Applications used sequential or indexed-sequential files (ISAM) tailored to one program's access pattern. Cross-referencing data required either duplicating fields across files or writing bespoke merge/match logic per pair of programs. There was no general notion of a *relationship* between record types that the system itself understood and maintained.

### What was technically new

Bachman's IDS (design work 1961–1963, operational 1963 at GE) introduced three ideas that became the vocabulary of the field for the next two decades:

1. **Records and record types.** A typed, named bundle of fields — the unit of storage.
2. **Sets** as first-class named relationships. A set type declares an owner record type and a member record type (`DEPARTMENT` owns `EMPLOYEE`). A set *occurrence* is one specific instance: one department and its actual employees.
3. **Physical implementation as a ring** (a singly linked list closing back on the owner). This made two operations O(1) or O(k) in the number of related records, with zero search: "find the owner of this record" (one pointer hop) and "find the next member" (one pointer hop). Listing *all* members of an occurrence is O(k) where k is the number of members — proportional to the answer size, not the size of the whole database.

CODASYL's Data Base Task Group formalized this in a 1969 report (revised 1971) as the **network data model**, with a standard Data Manipulation Language (DML) embedded in COBOL: `STORE`, `FIND`, `GET`, `MODIFY`, `ERASE`, `CONNECT`, `DISCONNECT`, plus **currency indicators** — the runtime's memory of "current record," "current record of each type," and "current record of each set" — which let DML statements stay terse by defaulting to whatever the program was last positioned at. `implementation.py` in this chapter implements exactly this subset: `STORE`, `CONNECT`, `DISCONNECT`, `FIND FIRST/NEXT/OWNER`, and the three currency indicators (run unit, of-record-type, of-set).

The crucial structural difference from IBM's competing hierarchical model (used in IMS, 1966) is that a network-model record can be a member of **multiple, independent set occurrences**, including set types with different owners. A hierarchy forces a strict tree: every record has exactly one parent. Bachman's model is a directed graph of rings — hence "network." This chapter's test #10 (`Alice is ALSO a member of the project set`) demonstrates exactly this: `EMPLOYEE#1` sits in both a `DEPARTMENT` ring and a `PROJECT` ring simultaneously, something a pure hierarchy cannot represent without either duplicating the employee record or picking one parent arbitrarily.

### How it worked, concretely

See the Full Worked Example above for the exact pointer values. The essential mechanism: `ring_next[(set_name, node_id)]` is a single dictionary that plays the role of the on-disk "next" pointer field IDS physically stored inside each record. Traversal is always relative — `FIND NEXT` only makes sense given a currency indicator telling you where you currently are — which is the origin of the term **navigational database**: the program's logic *is* a walk through the graph, statement by statement, rather than a declarative description of a result set.

### What it enabled, and its lasting impact

- CODASYL/network-model and IBM's hierarchical IMS were the two dominant commercial database paradigms through the 1970s (Cullinet's IDMS, a direct commercial descendant of Bachman's IDS, was one of the most widely deployed systems of the era).
- Edgar F. Codd's 1970 relational model was explicitly framed as a response to the navigational approach: replace "the programmer must know the physical/logical path to the data" with a declarative algebra over tables, letting a query optimizer choose the access path. Codd's paper directly cites the pointer-chasing complexity of CODASYL-style systems as the problem relational algebra solves.
- The **Bachman diagram** (boxes for record types, arrows for set types) remains a recognizable ancestor of modern entity-relationship diagrams.
- The underlying idea — a graph of typed nodes connected by named, directed relationships, traversed by following edges rather than by joining tables — reappears directly in modern **graph databases** (Neo4j, Amazon Neptune) and in **linked-list / pointer-chasing data structures** used throughout systems programming. "Set occurrence as a ring with an owner" is, structurally, a circular linked list with a sentinel — a data structure every CS curriculum still teaches, for exactly the reasons Bachman needed it: O(1) insertion at a known position and O(1) traversal to the next element.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [The Programmer as Navigator (1973 ACM Turing Award Lecture)](https://dl.acm.org/doi/10.1145/362534.362560) | Communications of the ACM | 1973 |
| [Integrated Data Store: A General-Purpose Programming System for Random Access Memories](https://ieeexplore.ieee.org/document/1487621) | AFIPS Fall Joint Computer Conference | 1964 |
| CODASYL Data Base Task Group October 1969 Report | CODASYL Systems Committee | 1969 |
| [A Relational Model of Data for Large Shared Data Banks](https://dl.acm.org/doi/10.1145/362384.362685) (E. F. Codd — the relational response to the navigational model) | Communications of the ACM | 1970 |

# Week 08 — Charles W. Bachman (1973)

**ACM Turing Award citation:** *"For his outstanding contributions to database technology."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — the core idea in about 65 lines: a named SET links an owner record (a CUSTOMER) directly to its member records (that customer's ORDERs), so finding them is a few navigation steps instead of a scan of every order in the file.

[`implementation.py`](./implementation.py) — a full working version: a fixed two-level schema (CUSTOMER-ORDER, ORDER-ITEM), the CODASYL set rules (a member can only be owned by one owner occurrence of a given set type at a time), currency indicators that remember where you last navigated to, and a brute-force `scan()` to measure the "before" against the "after."

```
schema (set types, fixed up front like a real CODASYL DBA would define it)
    -> STORE records
    -> CONNECT members into owners' sets
    -> FIND FIRST/NEXT WITHIN SET, FIND OWNER   (navigate the links)
    -> printed result
```

What it supports:
- A fixed schema: `CUSTOMER-ORDER` (owner `CUSTOMER`, member `ORDER`) and `ORDER-ITEM` (owner `ORDER`, member `ITEM`) — two levels, so you can navigate `CUSTOMER -> ORDER -> ITEM`
- `store()`, `connect()`, `disconnect()`: build the database and wire records into sets
- `find_first_within_set()` / `find_next_within_set()` / `find_owner()`: the actual CODASYL navigation verbs, built on currency indicators
- `scan()`: the "before" — a brute-force table scan, counting every record it has to examine
- A REPL, a network-script loader, a 14-case test suite, and a verbose mode that prints every currency update

```bash
python3 concept.py                        # the core idea, plain
python3 implementation.py                 # interactive REPL
python3 implementation.py practice.network # load and run a network script
python3 implementation.py --test          # test suite (14 cases)
python3 implementation.py --verbose       # REPL that prints every currency update
```

Example session:

```
bachman> store CUSTOMER name=Acme
stored CUSTOMER:1 {'name': 'Acme'}
bachman> store ORDER total=250
stored ORDER:1 {'total': '250'}
bachman> store ORDER total=80
stored ORDER:2 {'total': '80'}
bachman> store ORDER total=500
stored ORDER:3 {'total': '500'}
bachman> connect CUSTOMER-ORDER CUSTOMER:1 ORDER:1
connected ORDER:1 into CUSTOMER-ORDER owned by CUSTOMER:1
bachman> connect CUSTOMER-ORDER CUSTOMER:1 ORDER:2
connected ORDER:2 into CUSTOMER-ORDER owned by CUSTOMER:1
bachman> find first within CUSTOMER-ORDER owner CUSTOMER:1
  current: ORDER:1 {'total': '250'}
bachman> find next within CUSTOMER-ORDER
  current: ORDER:2 {'total': '80'}
bachman> find next within CUSTOMER-ORDER
  (end of set)
bachman> scan ORDER total=250
  found ['ORDER:1'] after examining 3 ORDER record(s)
```

Order 3 (Globex's order) is never looked at while walking Acme's set — two navigation steps find both of Acme's orders. `scan`, the brute-force stand-in for a flat tape file, has to examine all three orders to answer the same question, because it has no link to follow — it can only check every record and see which ones match.

---

## Full Worked Example

### Setup

Two customers, three orders, none connected yet:

```
CUSTOMER:1 {name: Acme}
CUSTOMER:2 {name: Globex}
ORDER:1 {total: 250}
ORDER:2 {total: 80}
ORDER:3 {total: 500}
```

The question we want to answer: **"give me all of Acme's orders."**

### Step 1 — the before: a flat file, no links

If `ORDER:1`, `ORDER:2`, and `ORDER:3` only exist as rows in a sequential file, with a `customer` field on each one, answering the question means reading every row and checking the field:

```
examine ORDER:1 -> total=250, customer=Acme   -> match, keep it
examine ORDER:2 -> total=80,  customer=Acme   -> match, keep it
examine ORDER:3 -> total=500, customer=Globex -> no match, discard
```

Three records examined to find two matches. With three orders that's nothing. With three million orders on tape, it's a full pass over three million records, every single time any program asks this question — and if ten different programs ask ten different questions about the same file, each one pays its own full pass.

### Step 2 — the after: wire the link once

Instead of a bare `customer` field, Bachman's model stores a named **set**, `CUSTOMER-ORDER`, connecting the owner (`CUSTOMER:1`) directly to its members (`ORDER:1`, `ORDER:2`). This happens once, at the moment each order is created — not every time someone asks a question about it.

```
connect CUSTOMER-ORDER CUSTOMER:1 ORDER:1
  set_members["CUSTOMER-ORDER"][CUSTOMER:1] = [ORDER:1]
  member_owner["CUSTOMER-ORDER"][ORDER:1]   = CUSTOMER:1

connect CUSTOMER-ORDER CUSTOMER:1 ORDER:2
  set_members["CUSTOMER-ORDER"][CUSTOMER:1] = [ORDER:1, ORDER:2]
  member_owner["CUSTOMER-ORDER"][ORDER:2]   = CUSTOMER:1

connect CUSTOMER-ORDER CUSTOMER:2 ORDER:3
  set_members["CUSTOMER-ORDER"][CUSTOMER:2] = [ORDER:3]
  member_owner["CUSTOMER-ORDER"][ORDER:3]   = CUSTOMER:2
```

Two in-memory structures now exist: for any owner, the ordered list of its members (so you can walk forward through them), and for any member, which single owner holds it (so you can walk backward). Both directions of the link exist from the moment of `connect` — nothing about the question "give me Acme's orders" has been answered yet, but the answer is now one step away instead of a whole-file scan away.

### Step 3 — navigate instead of scan

`find first within CUSTOMER-ORDER owner CUSTOMER:1` looks up `set_members["CUSTOMER-ORDER"][CUSTOMER:1]`, takes the first entry (`ORDER:1`), and remembers it as the **currency** of the set `CUSTOMER-ORDER` — a pointer saying "this is where you are, in this set, right now."

```
current_of_set["CUSTOMER-ORDER"] = (CUSTOMER:1, ORDER:1)
returns ORDER:1
```

`find next within CUSTOMER-ORDER` reads that currency, finds `ORDER:1`'s position in `CUSTOMER:1`'s member list (index 0), and returns the next one:

```
current_of_set["CUSTOMER-ORDER"] = (CUSTOMER:1, ORDER:2)
returns ORDER:2
```

A third `find next within CUSTOMER-ORDER` walks off the end of the list — there is no third member for `CUSTOMER:1` — and returns nothing:

```
current_of_set["CUSTOMER-ORDER"] = (CUSTOMER:1, None)
returns None
```

Two steps, two matches, zero wasted looks at `ORDER:3`. That is the entire point of a navigational database: the cost of the answer is proportional to the size of the answer, not to the size of the file.

### Edge case: a member can only have one owner at a time

Suppose, by mistake, you try to connect `ORDER:1` into `Globex`'s set as well, without disconnecting it from Acme first:

```
connect CUSTOMER-ORDER CUSTOMER:1 ORDER:1   -- already done above
connect CUSTOMER-ORDER CUSTOMER:2 ORDER:1   -- ORDER:1 is already owned by CUSTOMER:1

error: ORDER:1 is already connected into CUSTOMER-ORDER under owner CUSTOMER:1; disconnect first
```

This isn't an implementation quirk — it's a real CODASYL rule. In the standard, a member record occurrence belongs to **at most one owner occurrence of a given set type at a time**. An order can't silently belong to two customers; if it needs to move, the program has to explicitly `disconnect` it first, then `connect` it to the new owner. `implementation.py --test` pins this down directly (test 6), along with the recovery path — disconnect, then reconnect to a different owner (test 7) — so the rule is a documented, checked fact about the model, not just a line in this README.

---

## ELI5

Imagine your toy box has a hundred toys all mixed together in one big pile. Every time you want "all my red cars," you have to pick up every single toy, look at it, and put it back if it's not a red car. That takes forever.

Now imagine instead you had a little string tied from a tag that says "red cars" to each red car, all tied together in a loop. To find your red cars, you just follow the string. You never touch the blue trucks or the stuffed animals at all.

Charles Bachman built the string. Before him, computers kept everything in one big pile on tape and had to check every single thing to answer any question. He built a way to tie direct strings between things that belong together — a customer and their orders, an order and its items — so a computer could just follow the string to the answer, instead of checking the whole pile every time.

---

## ELI10

Charles William Bachman was born in Manhattan, Kansas, in 1924, where his father was the head football coach at Kansas State College. He trained as a mechanical engineer, spent about ten years at Dow Chemical working in finance and production, and then moved to General Electric in 1960 — a background in factories and supply chains, not computer science, which turns out to matter: the problem he solved first was a factory's, not a researcher's.

GE needed to track parts, orders, and manufacturing schedules on a computer, and the sequential tape files everyone used at the time were a terrible fit. A tape file makes you read record 1, then 2, then 3, in order — there's no way to jump straight to "this customer's orders" without reading everything before it. By 1963, Bachman and his team had built the Integrated Data Store (IDS): data lived on disk instead of tape, which meant a program could jump straight to any record, and records could be wired together with direct links Bachman called "sets" — one customer record linked to all of that customer's order records, one order linked to all of its line items. A program didn't read a file top to bottom anymore; it **navigated**, moving from record to record along these links. A GE prototype using IDS reportedly ran twice as fast as the custom-built system it replaced.

IDS worked well enough that other companies wanted the same design, and in 1969 an industry group called CODASYL (the same consortium behind COBOL) standardized Bachman's approach as the "network data model." For most of the 1970s, if a large company ran a database, there was a good chance it looked like Bachman's: record types connected by named sets, programs written to FIND the next record along a chain. He also invented a way to draw these structures on paper — boxes for record types, arrows for the links between them — now called Bachman diagrams, published in 1969, seven years before Peter Chen's more famous entity-relationship diagrams.

His 1973 Turing Award lecture, "The Programmer as Navigator," opened by comparing the shift to Copernicus moving the Earth out of the center of the universe: the programmer, Bachman said, was no longer a stationary observer watching records pass by on a tape, but a mobile navigator free to move anywhere in a web of linked data. It's a good description of what he built — and also, within a year, the opening move in a public debate with Ted Codd, who argued that Bachman's links tied every program too tightly to the database's exact physical shape. That debate took most of a decade to settle, and the side that won wasn't Bachman's.

---

## CS Graduate Level

### 1. The network data model: records connected by named sets

**Before.** A sequential file is a flat list of records with no structural links between them. If an `ORDER` record needs to be associated with a `CUSTOMER`, the usual trick is a foreign key-like field (`customer_id`) that a program checks by reading the whole file and filtering — there is no way to retrieve "this customer's orders" except by scanning every order and testing the field. `implementation.py`'s `scan()` method is exactly this: a linear pass over every record of a type, counting how many it had to look at to find the ones that matched.

**What was new.** Bachman's Integrated Data Store (1963) introduced the **set**: a named, direct, bidirectional link between one **owner** record type and one **member** record type. Unlike a field you have to search, a set is a structure you walk. In `implementation.py`, this is two dictionaries kept in sync on every `connect()`:

```python
self.set_members[set_name][owner_key].append(member_key)   # owner -> ordered list of members
self.member_owner[set_name][member_key] = owner_key        # member -> its one owner
```

`find_first_within_set()` / `find_next_within_set()` walk the first dictionary forward; `find_owner()` walks the second one backward. Both directions exist the moment the link is made — the cost of connecting a record is paid once, up front, and every later query against that link is just a pointer dereference, not a search.

**The constraint that makes it a *model*, not just a convenience.** A member record occurrence can be owned by **at most one owner occurrence of a given set type at a time.** `connect()` enforces this directly — reconnecting an already-connected member raises `BachmanError` until it's explicitly `disconnect()`-ed first. This single rule is why a true many-to-many relationship (an order with items that themselves belong to many orders, say) can't be expressed as one set type between two record types; the real CODASYL answer was to introduce an intermediate "junction" record type with two owning sets, the same workaround relational databases use today with a join table.

**What descended from it.** The 1969 CODASYL Data Base Task Group (DBTG) report formalized Bachman's design into an industry specification — the **network model** — with a **schema** (the full database structure, fixed by a database administrator) and **subschemas** (a restricted view of it that a given program is allowed to see, an early, if partial, form of data independence). `implementation.py`'s `build_schema()`, defining the set types once before any `store`/`connect`/`find` runs, mirrors that same split between "the DBA defines the structure" and "the program operates within it."

### 2. Navigation: currency indicators and the programmer-as-navigator

**Before.** On tape, "where you are" in the data is a single number: the position of the read head. There's exactly one notion of "current."

**What was new.** A network database gives a program many simultaneous notions of "current" — Bachman called them **currency indicators**: the current record of each record type, the current record of each set type, the current record overall. `FIND FIRST WITHIN SET` and `FIND NEXT WITHIN SET` are stateful: they read and update currency rather than taking a position as an argument. `implementation.py`'s `current_of_set` dict is this exact mechanism, scoped to one indicator per set type for clarity:

```python
self.current_of_set[set_name] = (owner_key, member_key)
```

`find_next_within_set()` doesn't take a "which record" argument at all — it reads `current_of_set[set_name]`, finds that member's position in the owner's list, and returns the next one. This is why there's a 13th test case asserting that calling `find_next_within_set()` with no prior `find_first_within_set()` is an error: there is no "next" without an established "current." The entire CODASYL Data Manipulation Language (DML) was built this way — no `SELECT`, only `FIND`, and every `FIND` moved a pointer that the next statement could depend on. Bachman's 1973 Turing lecture, "The Programmer as Navigator," framed this explicitly: the programmer was no longer a passive viewer of records streaming past (the tape model) but an active navigator choosing a path through a graph of linked data.

### 3. Bachman diagrams: drawing the schema before building it

**Before.** A database's structure lived in code and documentation prose — there was no standard visual notation for "here are the record types, and here is how they connect."

**What was new.** Bachman's 1969 paper "Data Structure Diagrams" (Data Base, the SIGBDP newsletter, vol. 1 no. 2) introduced a simple notation: a box per record type, an arrow per set type, pointing from owner to member. This chapter's schema would be drawn as `CUSTOMER -> ORDER -> ITEM`, two boxes and two arrows — exactly the shape `build_schema()` encodes in `define_set()` calls. These diagrams predate Peter Chen's entity-relationship (ER) diagrams by seven years (Chen, 1976) and are a direct ancestor of them, though Chen's notation is value-based (relationships can be many-to-many directly) where Bachman's is navigational (every arrow is a set you can walk).

### 4. The Bachman-Codd debate: navigation versus the relational model

**Before — or rather, alongside.** While CODASYL's network model was becoming the commercial standard, Ted Codd published "A Relational Model of Data for Large Shared Data Banks" (1970), arguing for a fundamentally different approach: data as simple tables, queried by describing *what* you want (a join on matching values) rather than *how* to get it (a sequence of FIND statements along pre-built links).

**The actual disagreement.** The two models trade the same tradeoff in opposite directions. A network set is fast specifically because the link is pre-built — `find_first_within_set()` is an `O(1)` dictionary lookup — but the program that calls it has to know the exact shape of the schema: the set's name, which record type owns it, which type is a member. Change the schema (split a set, add an intermediate record type) and every program using `FIND ... WITHIN SET` for that relationship has to change too. A relational join reconstructs the same relationship at query time from matching column values, paying a real runtime cost (the join), but the program issuing the query never needed to know how the join was physically carried out — the system is free to change indexes, storage layout, even the join algorithm, without touching a single application. Bachman and Codd debated this directly at a 1974 SIGMOD conference; Bachman defended navigation's performance, Codd defended the relational model's independence from physical structure. Codd's side won the market through the 1980s as SQL matured — not because navigation was slow (it wasn't), but because the cost of recoding every program every time the schema changed eventually outweighed the speed advantage, especially as businesses' data needs kept shifting.

### 5. What outlived the debate

Pure CODASYL network databases are now a historical footnote in new development, but the ideas didn't disappear:

- **Foreign keys in SQL databases** are a value-based descendant of Bachman's sets — a simplified version that trades the direct pointer for a value lookup, in exchange for Codd's data independence.
- **Graph databases** (Neo4j and similar) are, structurally, Bachman's network model with the owner/member restriction lifted: any node can link to any other node, and queries are written as explicit traversals — `FIND FIRST WITHIN SET` under a new name, for the exact use cases (social graphs, recommendation chains, fraud rings) where "follow the links fast" beats "join tables."
- **Object databases and ORMs** that let you write `customer.orders[0]` instead of a SQL join are, under the hood, re-implementing navigational access on top of a relational store, because for a programmer thinking in terms of one object's related objects, navigation is still the more natural shape — Bachman's argument, forty-plus years later, still shows up in how application code is written, even where the storage underneath it is relational.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [Integrated Data Store (A General Purpose Programming System for Random Access Memories)](https://www.mirrorservice.org/sites/www.bitsavers.org/pdf/afips/1964-04_%2325.pdf) *(Bachman & Williams)* | AFIPS Fall Joint Computer Conference | 1964 |
| [Data Structure Diagrams](https://en.wikipedia.org/wiki/Data_structure_diagram) | Data Base (ACM SIGBDP newsletter), vol. 1, no. 2 | 1969 |
| CODASYL Data Base Task Group Report | Conference on Data Systems Languages (CODASYL) | 1969/1971 |
| [The Programmer as Navigator](https://doi.org/10.1145/355611.362534) *(1973 Turing Award lecture)* | Communications of the ACM, 16(11) | 1973 |
| [A Relational Model of Data for Large Shared Data Banks](https://doi.org/10.1145/362384.362685) *(E. F. Codd — the model that eventually displaced it)* | Communications of the ACM, 13(6) | 1970 |

---

*Previous: [Week 07 — Edsger W. Dijkstra (1972)](../07-edsger-dijkstra-1972/)*

# Week 08 — Charles W. Bachman (1973)

**ACM Turing Award citation:** *"For his outstanding contributions to database technology."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## What He Actually Invented

Before Bachman, "database" mostly meant a stack of magnetic tape files, one per record type, read start to finish, in order, nothing else. If a program needed to relate two files — say, which orders belong to which customer — there were two options, both crude: sort both files by the same key and merge them in one matched pass, or rescan one file over and over, once for every record in the other. Every program had to know, baked into its own source code, exactly how the files were laid out. There was no "database" as a thing multiple programs shared — just a private file format, reinvented per program, that broke the moment you changed it.

Bachman's Integrated Data Store, running at General Electric by 1963, replaced "recompute the relationship every time you need it" with "store the relationship as data." Instead of matching a customer to its orders by scanning, the customer record got an actual pointer to its first order. That order pointed to the next one. The last order pointed back to the customer, closing a ring. A program no longer searched for a customer's orders — it started at the customer and walked pointers, touching only the records that were actually related.

That's also what makes IDS the first real database management *system*, and not just a faster file format: the record types and the relationships between them — Bachman called a relationship a "set type" — were described once, as a schema shared by every program that used the database, instead of each program carrying its own private, hand-coded understanding of the file layout. Change the schema in one place, and every program navigating it saw the change. Nobody had to hunt down and rewrite every program that happened to touch that data.

It didn't stay a one-company system. Bachman helped lead the CODASYL Data Base Task Group, an industry committee, whose 1969 and 1971 reports turned IDS's approach into a standard — the **network data model** (called "network" because a record type could belong to more than one owner, unlike a strict parent-child hierarchy). Multiple vendors built database systems to that standard, and for most of the 1970s — years before SQL existed — this was simply how you built a serious database.

So, before any code: no shared, storable relationships before this. Pointer-linked, schema-shared relationships after. Standardized industry-wide within a decade. The code below is what that actually looks like underneath.

---

## The Code

[`concept.py`](./concept.py) — the core idea in about 60 lines: a "set" is a ring of pointers. An owner record points to its first member, each member points to the next, and the last member points back to the owner. Finding everything that belongs to an owner means starting at the owner and following pointers, not scanning a whole file.

[`implementation.py`](./implementation.py) — a full working network database: four record types, three set types, one record type (`LINE`) that is a member of two different rings at once, and a DML command set (`STORE`, `FIND`, `CONNECT`, `FIND FIRST/NEXT/OWNER WITHIN`) modeled on real IDS/CODASYL commands, including "currency" — the database's memory of the last record you touched of each type and each set, which every navigation command moves relative to.

```
schema (record types, set types)
    -> STORE     create a record, becomes current, auto-connects
                 into any set it's an automatic member of
    -> CONNECT   manually link a record into a set's ring
    -> FIND      the "before": scan a whole record type by field value
    -> FIND FIRST/NEXT/OWNER WITHIN   the "after": walk a ring
```

What it supports:
- A schema of record types and set types (`CUSTOMER` owns `CUSTOMER-ORDERS`, `ORDER` owns `ORDER-LINES`, `PART` owns `PART-LINES`, and `LINE` is a member of both `ORDER-LINES` and `PART-LINES` at once — the detail that makes this a *network*, not a tree)
- `store()`: create a record; if its type is an automatic member of some set, and a current owner is already established for that set, it auto-connects on the spot
- `connect()`: manually wire a record into a set's ring, for when automatic membership isn't enough
- `find()`: the "before" — scan every record of a type checking field values, reporting how many records it had to touch
- `find_first_within()` / `find_next_within()` / `find_owner_within()`: the "after" — walk a ring using pointers only, touching exactly the records that belong to it
- "Currency": the database always remembers the record you last touched, of each type and of each set — every `WITHIN` command moves relative to that, never by name or address you supply
- A REPL, a DML-script loader, a 22-case test suite, and a verbose mode that prints every pointer update as it happens

```bash
python3 concept.py                       # the core idea, plain
python3 implementation.py                # interactive REPL
python3 implementation.py practice.dml   # load and run a DML script
python3 implementation.py --test         # test suite (22 cases)
python3 implementation.py --verbose      # REPL that prints every pointer update
```

Example session (this is [`practice.dml`](./practice.dml) — run it yourself with `python3 implementation.py practice.dml`):

```
ids> store CUSTOMER name=Alice city=Boston
stored CUSTOMER#1 (name=Alice, city=Boston)
ids> store ORDER order_no=1001 amount=50
stored ORDER#2 (order_no=1001, amount=50)
ids> store ORDER order_no=1002 amount=75
stored ORDER#3 (order_no=1002, amount=75)
ids> store CUSTOMER name=Bob city=Chicago
stored CUSTOMER#4 (name=Bob, city=Chicago)
ids> store ORDER order_no=2001 amount=20
stored ORDER#5 (order_no=2001, amount=20)
ids> find CUSTOMER name=Alice
found CUSTOMER#1 (name=Alice, city=Boston) (scanned 1 record(s))
ids> walk CUSTOMER-ORDERS
  ORDER#2 (order_no=1001, amount=50)
  ORDER#3 (order_no=1002, amount=75)
  touched 2 record(s)
ids> store PART part_no=P1 description=bolt
stored PART#6 (part_no=P1, description=bolt)
ids> find ORDER order_no=1001
found ORDER#2 (order_no=1001, amount=50) (scanned 1 record(s))
ids> store LINE qty=12
stored LINE#7 (qty=12)
ids> find ORDER order_no=1001
found ORDER#2 (order_no=1001, amount=50) (scanned 1 record(s))
ids> walk ORDER-LINES
  LINE#7 (qty=12)
  touched 1 record(s)
ids> find PART part_no=P1
found PART#6 (part_no=P1, description=bolt) (scanned 1 record(s))
ids> walk PART-LINES
  LINE#7 (qty=12)
  touched 1 record(s)
```

`LINE#7` shows up in both walks. One record, reached two different ways, no copy made for either. That's the whole invention in one trace.

There's also [`scratch.dml`](./scratch.dml) — a smaller script for trying your own commands against, and a place to hand-write DML by hand and run it (`python3 implementation.py scratch.dml`).

---

## Full Worked Example

### Happy path: building and walking a ring

Start empty. `next_id = 1`.

**Step 1 — `store CUSTOMER name=Alice city=Boston`.** A new record, `CUSTOMER#1`. It owns the `CUSTOMER-ORDERS` set type, so it gets an empty ring: `first=None, last=None`. It has no member-of sets (customers aren't members of anything here), so nothing else happens. It becomes current: current-of-run-unit `#1`, current-of-`CUSTOMER` `#1`, and — because it owns `CUSTOMER-ORDERS` — current owner of `CUSTOMER-ORDERS` is now `#1`.

```
CUSTOMER#1 owns CUSTOMER-ORDERS: first=None last=None
current owner of CUSTOMER-ORDERS: #1
```

**Step 2 — `store ORDER order_no=1001 amount=50`.** A new record, `ORDER#2`. `ORDER` is a member of `CUSTOMER-ORDERS`, so `store()` checks: is there a current owner of that set right now? Yes — `#1`, from step 1. So it auto-connects. `#1`'s ring is empty (`first=None`), so this is the first-ever member: `#1.first = #2`, `#1.last = #2`, and `#2`'s own next-pointer closes the ring straight back to the owner: `#2.next = #1`.

```
ring:  #1 -> #2 -> #1
CUSTOMER#1 owns CUSTOMER-ORDERS: first=#2 last=#2
ORDER#2 member of CUSTOMER-ORDERS: owner=#1 next=#1
```

**Step 3 — `store ORDER order_no=1002 amount=75`.** `ORDER#3`, same auto-connect logic. This time `#1`'s ring is *not* empty — `last=#2`. So the old last member gets re-pointed at the new one, the new one closes the ring back to the owner, and the owner's `last` moves up:

```
#2.next:  #1  ->  #3        (was pointing straight at the owner, now points at #3)
#3.next:  #1                (the new member closes the ring)
#1.last:  #2  ->  #3

ring:  #1 -> #2 -> #3 -> #1
```

**Step 4 — `store CUSTOMER name=Bob city=Chicago`.** `CUSTOMER#4`. Same as step 1: empty ring, and it becomes the new current owner of `CUSTOMER-ORDERS` — not `#1` anymore. This one line is why the next `store ORDER` attaches to Bob, not Alice: "current owner" changed.

**Step 5 — `store ORDER order_no=2001 amount=20`.** `ORDER#5` auto-connects to whichever `CUSTOMER-ORDERS` owner is current *right now* — `#4` (Bob), not `#1` (Alice). Bob's ring: `#4 -> #5 -> #4`. Alice's ring is untouched.

**Step 6 — `find CUSTOMER name=Alice`.** This is the deliberately expensive command: scan every `CUSTOMER` record in dbkey order, checking `name`. `#1` is the very first `CUSTOMER` in the database, so it matches immediately — 1 record touched. `find()` makes `#1` current again, which also resets "current owner of `CUSTOMER-ORDERS`" back to `#1`.

**Step 7 — `walk CUSTOMER-ORDERS`.** Now the pointer-only path: `find_first_within` reads `#1.first = #2`, then `find_next_within` reads `#2.next = #3`, then `find_next_within` again reads `#3.next = #1` — that's the owner's own key, so the ring has closed and the walk stops. Result: `[#2, #3]`, 2 records touched. Bob's `#5` was never looked at. It didn't need to be.

### The case that makes it a network, not a tree

Everything so far is really just a tree: each `ORDER` belongs to exactly one `CUSTOMER`. A hierarchical database (IBM's IMS, which came a few years after IDS) can do that much. Here's the case that can't be modeled as a tree.

**Step 8 — `store PART part_no=P1 description=bolt`.** `PART#6`. It owns `PART-LINES`, so current owner of `PART-LINES` becomes `#6`. Nothing connects yet — no `LINE` has been stored.

**Step 9 — `find ORDER order_no=1001`.** Scans `ORDER` records, matches `#2` immediately (it's the first `ORDER` in dbkey order). This makes `#2` current, and — because `ORDER` owns `ORDER-LINES` — current owner of `ORDER-LINES` becomes `#2`.

At this exact moment, the database has **two live "current owner" pointers at once**: `ORDER-LINES -> #2` and `PART-LINES -> #6`, left over from step 8.

**Step 10 — `store LINE qty=12`.** `LINE#7` is a member of *both* `ORDER-LINES` and `PART-LINES`. `store()` loops over every set type `LINE` is a member of, and for each one it finds a current owner already sitting there:

```
connect #7 into ORDER-LINES: first member, ring is #2 -> #7 -> #2
connect #7 into PART-LINES:  first member, ring is #6 -> #7 -> #6
```

One `store` call, two rings updated. `LINE#7` now has two independent next-pointers — one for each set it belongs to — and neither ring knows the other exists.

**Step 11 — verify from both directions.** `find ORDER order_no=1001` then `walk ORDER-LINES` gives `[#7]`. Separately, `find PART part_no=P1` then `walk PART-LINES` also gives `[#7]`. Same record, reached by two unrelated starting points, with zero duplication. That's the property CODASYL called a "network data model": a member record type isn't owned by one thing, the way a file folder holds one thing — it can sit at the intersection of two rings at once, the same way `order_no=1001` and `part_no=P1` intersect at exactly one line item in the real world.

### What the scan actually costs, in numbers

One more concrete case, run as its own script ([`scratch.dml`](./scratch.dml) has a version of this):

```
ids> store CUSTOMER name=Carol city=Denver
ids> store ORDER order_no=1 amount=1
ids> store ORDER order_no=2 amount=2
ids> store CUSTOMER name=Dave city=Miami
ids> store ORDER order_no=3 amount=3
ids> store ORDER order_no=4 amount=4
ids> store ORDER order_no=5 amount=5
ids> find ORDER order_no=5
found ORDER#7 (order_no=5, amount=5) (scanned 5 record(s))
ids> find CUSTOMER name=Carol
found CUSTOMER#1 (name=Carol, city=Denver) (scanned 1 record(s))
ids> walk CUSTOMER-ORDERS
  ORDER#2 (order_no=1, amount=1)
  ORDER#3 (order_no=2, amount=2)
  touched 2 record(s)
```

Finding the last order by scanning touches every order that came before it — 5 records, in a database with only 7 orders total. Walking Carol's own ring touches exactly her 2 orders, no matter how many other customers' orders sit in the same database. The gap between those two numbers is the entire reason Bachman built this. It's a constant-size database here, so the difference looks small. General Electric was running this against files with hundreds of thousands of records in 1963 — the gap doesn't stay small.

---

## ELI5

Before, if you wanted to find all of a kid's toys in a giant toy warehouse, you had to walk down every aisle and check every single box: "is this yours? is this yours?" until you'd checked the whole warehouse.

Charles Bachman had a better idea. What if every kid's first toy box had a little string tied to it, going to their next toy box, and that one had a string to the next, all the way around back to the kid? Now you just grab the kid's hand, follow the string to the first box, follow the next string, and the next — and you stop the moment the string leads back to the kid. You never even walk past another kid's toys.

And here's the clever part: one toy box could have a string from the kid who owns it AND a string from the store it was bought at, so you could find it starting from either end.

---

## ELI10

Charles Bachman was born in 1924 in Manhattan, Kansas. He trained as a mechanical engineer, not a computer scientist — computer science barely existed as a subject yet — and spent his whole career inside companies, not universities: first Dow Chemical, then General Electric starting in 1960. That matters, because the problem he solved wasn't an academic one. It was General Electric's actual manufacturing and inventory data, and the actual pain of writing programs against it.

In the early 1960s, "database" mostly meant a stack of magnetic tapes, one file per kind of record, each one read start to finish in order. If a program needed to relate two files — say, which orders belong to which customer — it had to sort both files by the same key and merge them, or scan one file over and over for every record in the other. Every program that touched the data had to know exactly how the files were laid out on tape, because the layout *was* the only structure there was. Bachman's Integrated Data Store, running at GE by 1963, replaced that with something new: records that pointed directly at the other records they were related to. A customer record pointed to its first order; that order pointed to the next; the last one pointed back to the customer, closing a ring. Programs stopped scanning and started *navigating* — following a specific path through specific pointers to get exactly the records they needed, and nothing else. He called the visual notation for this — boxes for record types, arrows for the ownership relationships between them — a "data structure diagram," now usually called a Bachman diagram.

IDS worked well enough that GE's approach became the seed for an industry standard: the CODASYL Data Base Task Group, which Bachman helped lead, published reports in 1969 and 1971 formalizing what came to be called the network data model — "network" because, unlike a strict company-org-chart hierarchy, one record could belong to more than one owner at once. Multiple vendors built database systems on that standard through the 1970s, and it was the dominant way to build a database for most of that decade, years before SQL existed. Bachman's 1973 Turing Award lecture, "The Programmer as Navigator," made the case explicit in its title: with this model, programming a database query meant literally programming a route through the data, one pointer at a time.

That title also marks the edge of what the network model got right and what it got stuck on. Two years earlier, in 1970, an IBM researcher named E. F. Codd had published a very different idea — the relational model — built on the argument that a programmer shouldn't have to navigate anything at all; you should be able to ask for what you want and let the system figure out how to get it. That argument eventually won, and it's why almost nobody writes CONNECT and FIND-NEXT-WITHIN statements today. But the network model didn't disappear so much as go underground: Bachman's own commercial descendant, IDMS, still processes real transactions today inside mainframes that insurance and banking companies never got around to replacing, and the pointer-chasing idea itself came back decades later, openly, as the graph database.

---

## CS Graduate Level

### 1. From sequential files to a shared, pointer-linked database

**Before.** Pre-IDS data processing worked file by file. Each record type — customers, orders, inventory — lived in its own sequential file, typically on magnetic tape, and every program that needed related data from two files had to either sort both by a common key and merge them in lockstep, or repeatedly rescan one file for each record of the other. There was no notion of "the database" as a shared object distinct from any one program: the physical file layout *was* the data model, privately understood by whichever program's source code encoded it. Changing that layout meant finding and fixing every program that depended on it.

**What was new.** Bachman's Integrated Data Store, operational at General Electric by 1963, introduced two things at once. First, a schema — a description of record types and the relationships between them — that existed independently of any single application program, so multiple programs could share one database instead of each owning a private file. Second, a physical mechanism for representing a relationship: the **chained set**, a ring of pointers where one occurrence (the owner) links to a series of others (the members), each pointing to the next, the last pointing back to the owner. `implementation.py`'s `_connect()` is this exact mechanism: `owner.owner_of[set_name]["first"]`/`["last"]` track the ends of the ring, and each member's `member_of[set_name]["next"]` is the link to the next member or, for the last one, back to the owner.

**How it worked, concretely.** Finding "every order for customer 7" went from an O(total orders) scan to an O(orders customer 7 actually has) walk. The Full Worked Example above shows this directly: scanning for the fifth order touched 5 records; walking a specific customer's own ring touched exactly 2, regardless of how many other customers' orders sat in the same database. This is the same complexity shift as an index versus a table scan in a modern database — except here it isn't an optimization layered under a query planner, it's the *only* way the data is organized. There is no other path to the data than the ones the schema wired in advance.

**What it enabled.** Bachman's own 1969 paper, "Data Structure Diagrams," gave the field its first standard visual notation for this: rectangles for record types, labeled arrows for set types. That notation is the direct ancestor of Peter Chen's 1976 Entity-Relationship diagram — the notation still used today to design a SQL schema on a whiteboard before a single `CREATE TABLE` is written, even though the database it's designed for works nothing like IDS internally anymore.

### 2. CODASYL and the network data model

**Before.** IDS itself was General Electric's proprietary system — powerful, but a one-vendor solution.

**What was new.** Bachman brought this design to the Conference on Data Systems Languages (CODASYL) — the same industry/government committee that had earlier standardized COBOL — where the Data Base Task Group he helped lead published reports in 1969 and 1971 formalizing IDS's approach into a vendor-neutral standard: the **network data model**. The standard split cleanly into a *schema* (the full database structure, owned by a database administrator) and *subschemas* (a restricted view of just the record and set types one particular program needed), plus a Data Manipulation Language embedded in COBOL, with verbs almost identical to this chapter's: `STORE`, `FIND`, `GET`, `CONNECT`, and the set-relative `FIND NEXT/PRIOR/OWNER WITHIN <set-name>`.

**Why "network."** In a strict hierarchy (the model IBM's IMS took, built around the same time as CODASYL's standardization effort), each record type has exactly one parent type, so the whole database is shaped like an org chart. CODASYL's model dropped that restriction: a record type could be a member of several different set types simultaneously, owned by several different parents, so the overall shape of the data was a general graph, not a tree. `implementation.py`'s `LINE` record type is a direct, minimal instance of this: it's a member of both `ORDER-LINES` and `PART-LINES` at once, reachable by walking from either an `ORDER` or a `PART`, with the two rings maintained completely independently (`connect()` is called twice, once per set, and neither call knows about the other).

**What it enabled.** Multiple commercial DBMSs (Cullinet's IDMS chief among them, still Bachman's own design) implemented the CODASYL standard through the 1970s, making it — years before SQL shipped commercially — the dominant way large organizations actually built a database.

### 3. Currency: the navigational state a program carries

**Before / what was new, together.** The mechanism that makes navigational DML terse is a piece of state CODASYL called **currency**: the database continuously tracks the record you most recently touched, both overall ("current of run-unit") and per record type and per set type. Every relative command — `FIND NEXT WITHIN`, `FIND OWNER WITHIN` — moves *from* that remembered position, so a program never has to pass around an explicit address or key; it just says "the next one" or "my owner" and the database knows what that means because of where you already are. `implementation.py`'s `Database` class carries this directly: `current_run_unit`, `current_of_type`, `current_owner_of_set`, `current_member_of_set` are all currency indicators, and `_make_current()` (called by every `store()` and `find()`) is the exact mechanism that updates them.

**The cost of this design.** Currency is also the design's biggest liability: it's implicit, mutable, global state that every DML command reads and silently rewrites. `store()`'s auto-connect logic in this chapter is a direct illustration — a `LINE` stored after a `PART` and an `ORDER` were both separately made current attaches to *both* of them, correctly, but only because of ambient state the `STORE` command itself never mentions. Get the order of operations wrong in a real IDS/CODASYL program — issue one `FIND` you didn't mean to, and currency shifts under you — and the next `CONNECT` silently attaches to the wrong owner. This is precisely the "the programmer as navigator" Bachman's Turing lecture title describes: correctness depended on the programmer holding the database's entire current position in their head, one relative move at a time.

### 4. What replaced it, and why

**Before (i.e., this whole model).** By the model described above, relationships are physical pointers, baked into the stored data itself. Querying means writing a program that walks those specific pointers in a specific order.

**What was new.** E. F. Codd's 1970 paper, "A Relational Model of Data for Large Shared Data Banks," argued for removing the pointers entirely. Represent every relationship as matching **values** across tables (what became foreign keys) instead of physical links, and let a query express *what* data is wanted, declaratively, leaving *how* to find it to the system. Codd's central objection to the network model was exactly its strength here: because relationships were physical pointers baked into the data, restructuring the database — adding a new set type, re-chaining existing data — could force a rewrite of every program that navigated the old structure. The relational model decoupled the logical view of the data from its physical storage, so the storage could change without breaking the programs querying it.

**What descended from it, both ways.** SQL and the relational model won the market by the 1980s, and "the programmer as navigator" the way Bachman meant it — hand-written pointer traversal — mostly disappeared from application code. But it didn't disappear from database engines: a modern relational database's B-tree indexes and foreign-key constraints are, underneath the declarative SQL surface, still doing pointer-following very similar in spirit to a CODASYL chain — the navigation just moved from the application programmer into the query optimizer. And the explicit, application-visible version of navigation came back on its own terms, decades later, as the **graph database** (Neo4j and similar systems): nodes and typed, directed edges you traverse directly, which is structurally close to a CODASYL set type, just without Bachman's schema-level rigidity or his currency indicators. Bachman's own commercial system, IDMS, is still in production today, processing real transactions inside insurance and banking mainframes that were never worth the cost of migrating off a working network database.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [A General Purpose Programming System for Random Access Memories](https://doi.org/10.1145/1464052.1464088) *(Bachman & Williams — the original IDS paper)* | AFIPS Fall Joint Computer Conference | 1964 |
| [Data Structure Diagrams](https://doi.org/10.1145/1017466.1017467) *(the "Bachman diagram" notation)* | ACM SIGMIS Database | 1969 |
| CODASYL Data Base Task Group October 1969 Report | ACM | 1971 |
| [The Programmer as Navigator](https://doi.org/10.1145/355611.362534) *(1973 Turing Award lecture)* | Communications of the ACM | 1973 |
| [A Relational Model of Data for Large Shared Data Banks](https://doi.org/10.1145/362384.362685) *(Codd — the model that displaced it)* | Communications of the ACM | 1970 |

---

*Previous: [Week 07 — Edsger W. Dijkstra (1972)](../07-edsger-dijkstra-1972/)*

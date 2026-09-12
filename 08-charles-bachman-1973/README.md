# Week 08 — Charles W. Bachman (1973)

**ACM Turing Award citation:** *"For his outstanding contributions to database technology."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — the network model in about 60 lines: two flat dicts (customers, orders) plus one extra dict that didn't exist before 1963 — a "set" mapping each customer to the ring of order ids connected to it. `scan_orders_before()` re-derives that relationship by reading every order; `walk_set_after()` just walks the ring.

[`implementation.py`](./implementation.py) — a full working simulation of Integrated Data Store / CODASYL DML: typed records with real NEXT/PRIOR/OWNER pointer slots, `SetType` (owner type, member type, FIFO or LIFO insertion), a `Database` with the three currency indicators DBTG defines (current of run unit, current of record type, current of set type), and the core DML verbs: `STORE`, `FIND ANY`, `FIND FIRST/NEXT/OWNER WITHIN <set>`, `GET`, `MODIFY`.

```
STORE CUSTOMER / STORE ORDER
    -> AUTOMATIC set membership: new ORDER wired into current CUSTOMER's ring
FIND ANY CUSTOMER id=1
    -> the one operation that has to scan: the entry point into the database
FIND FIRST / FIND NEXT WITHIN CUSTOMER-ORDERS
    -> navigate the ring, one pointer at a time, no scanning
GET
    -> read the fields of whatever is current
```

What it supports:
- A schema of record types wired together by named `SetType`s (owner -> member, FIFO or LIFO)
- `STORE`: writes a record and, if it's a member type, automatically connects it into the ring owned by whatever is currently "current" of the owner type
- `FIND FIRST` / `FIND NEXT` / `FIND OWNER WITHIN <set>`: pointer-chasing navigation, each step touching exactly one record
- `FIND ANY`: the pre-1963 style full scan — kept in, on purpose, because it's the one place the network model still has to search instead of navigate
- `scan_for_members()`: the "before" comparison — what a program had to do with no set at all
- A REPL, a DML-script loader, an 14-case test suite, and a verbose mode that prints all three currency indicators after every command

```bash
python3 concept.py                       # the core idea, plain
python3 implementation.py                # interactive REPL
python3 implementation.py demo.ids       # run a DML script
python3 implementation.py --test         # test suite (14 cases)
python3 implementation.py --verbose      # REPL/script run that prints currency indicators
```

Example session (`python3 implementation.py demo.ids`):

```
ids> store CUSTOMER name=Ada id=1
stored CUSTOMER#1{'name': 'Ada', 'id': 1}
ids> store ORDER item=Punched-cards customer=1
stored ORDER#2{'item': 'Punched-cards', 'customer': 1}
ids> store ORDER item=Vacuum-tube customer=1
stored ORDER#3{'item': 'Vacuum-tube', 'customer': 1}
ids> store CUSTOMER name=Grace id=2
stored CUSTOMER#4{'name': 'Grace', 'id': 2}
ids> store ORDER item=Teletype customer=2
stored ORDER#5{'item': 'Teletype', 'customer': 2}
ids> find any CUSTOMER id=1
found CUSTOMER#1{'name': 'Ada', 'id': 1}
ids> find first CUSTOMER-ORDERS
found ORDER#2{'item': 'Punched-cards', 'customer': 1}
ids> find next CUSTOMER-ORDERS
found ORDER#3{'item': 'Vacuum-tube', 'customer': 1}
ids> scan ORDER customer 1
scanned 3 ORDER records, matched 2: [ORDER#2..., ORDER#3...]
```

`find first` / `find next` touched exactly the two orders they returned. `scan` — the pre-1963 way of answering the same question — read all three orders in the file to find them, and that cost grows with every order anyone ever places, for every customer, forever. That gap is the entire chapter.

---

## Full Worked Example

### Happy path: building and walking a ring

Schema: one set type, `CUSTOMER-ORDERS`, owner `CUSTOMER`, member `ORDER`, insertion order `FIFO`.

**Step 0 — store the owner.** `STORE CUSTOMER name=Ada id=1`. A brand new record, no ring yet. Because no `ORDER` has been connected to it, `Ada.next["CUSTOMER-ORDERS"]` and `Ada.prior["CUSTOMER-ORDERS"]` don't exist yet — that absence *is* "empty set."

```
CUSTOMER#1 (Ada)
  next["CUSTOMER-ORDERS"]:  (none yet)
  prior["CUSTOMER-ORDERS"]: (none yet)
```

**Step 1 — store the first member.** `STORE ORDER item=Punched-cards customer=1`. `STORE` sees that `ORDER` is a member type of `CUSTOMER-ORDERS`, looks up "current of `CUSTOMER`" (that's Ada, from step 0), and connects the new order into her ring. Since the ring is empty, the new member becomes both first and last, and the ring closes directly back to the owner in both directions:

```
CUSTOMER#1 (Ada)
  next["CUSTOMER-ORDERS"]  -> ORDER#2   (first member)
  prior["CUSTOMER-ORDERS"] -> ORDER#2   (last member)
ORDER#2 (Punched-cards)
  next["CUSTOMER-ORDERS"]  -> CUSTOMER#1   (ring closes back to owner)
  prior["CUSTOMER-ORDERS"] -> CUSTOMER#1
  owner["CUSTOMER-ORDERS"] -> CUSTOMER#1   (direct backpointer, O(1) FIND OWNER)
```

**Step 2 — store a second member (FIFO).** `STORE ORDER item=Vacuum-tube customer=1`. FIFO means "insert before the owner, after the current last member" — append at the end of the ring:

```
CUSTOMER#1 (Ada)
  next  -> ORDER#2          (first member, unchanged)
  prior -> ORDER#3          (last member, updated)
ORDER#2 (Punched-cards)
  next  -> ORDER#3          (used to point to Ada, now points to the new order)
  prior -> CUSTOMER#1
ORDER#3 (Vacuum-tube)
  next  -> CUSTOMER#1        (ring closes back to owner)
  prior -> ORDER#2
  owner -> CUSTOMER#1
```

The ring, read as a loop: `Ada -> Punched-cards -> Vacuum-tube -> Ada -> ...`

**Step 3 — navigate it.** `FIND ANY CUSTOMER id=1` scans the customer file (there's no shortcut for the very first lookup — you have to land somewhere) and sets currency to Ada. `FIND FIRST WITHIN CUSTOMER-ORDERS` reads `Ada.next["CUSTOMER-ORDERS"]` directly — one pointer, no scan — and lands on `ORDER#2`. `FIND NEXT WITHIN CUSTOMER-ORDERS` reads `ORDER#2.next["CUSTOMER-ORDERS"]` — one more pointer — and lands on `ORDER#3`. Two navigational steps, two records touched, and neither one looked at Grace's data at all, even though it's sitting in the very same database.

### Edge case: walking off the end of the ring

Continue from `ORDER#3` (Vacuum-tube), current. Call `FIND NEXT WITHIN CUSTOMER-ORDERS` again. The code reads `ORDER#3.next["CUSTOMER-ORDERS"]`, which is `CUSTOMER#1` — the owner, not another order. `find_next()` checks the type of what it found: if it's the set's *owner type*, that's the ring closing, not a real next member, so it raises `end of set` instead of silently handing back the customer record disguised as an order. This is exactly the DBTG language's "no record found" condition: navigating a set is bounded, and the boundary is the owner itself, because the ring always closes there.

### Edge case: storing a member before any owner exists

`db4.store("ITEM", label="x")` with no `CUSTOMER`-equivalent ever stored or found first. `STORE` looks up "current of the owner type" to decide where to connect the new member, and there isn't one — `current_of_type` has no entry for that type yet. This raises immediately, rather than connecting the member to nothing (or worse, to whatever was current for an unrelated reason). It's the same discipline as the ring boundary above: the model refuses to leave a member half-wired into a set. `implementation.py --test` case 8 pins this down as an assertion.

---

## ELI5

Before, if you wanted to know what your friend ordered from the toy catalog, someone had to read through the entire pile of every order from every kid in the whole school, checking each one's name, until they'd checked all of them.

Charles Bachman's idea: instead of one big pile, tie a string from each kid straight to their own orders, one after another, like a chain of paper dolls holding hands. Now if you want your friend's orders, you don't touch anyone else's chain at all. You just follow the string from your friend to their first doll, then the next, then the next, until the string loops back to your friend — done. You never touched the other kids' piles.

---

## ELI10

Charles Bachman never finished a PhD. He trained as a mechanical engineer, worked at Dow Chemical and then General Electric, and in 1973 became the first person ever to win the Turing Award without an advanced degree, the first to win it for a specific piece of software, and the first to spend his entire career in industry rather than a university. He built the thing he's remembered for because his employer needed it, not because he was chasing a research question.

The problem, around 1960, was concrete: General Electric was trying to computerize manufacturing across roughly a hundred departments, and every one of them was on the verge of inventing its own file format and its own programs to read it. Data lived in flat, sequential files — one file per kind of record, processed top to bottom on tape or punched cards. If a program needed to relate two files (which orders belong to which customer, say), the programmer wrote a loop that read every record of one file and checked a field against the other. There was no way to say "this record belongs to that one" except by re-deriving it, in code, every single time, in every single program that needed the answer.

Bachman's team built the Integrated Data Store (IDS), running by 1963 on one of GE's first disk drives, on a Manufacturing Information and Control System project in Philadelphia. Disks mattered because, unlike tape, you could jump straight to any block on the disk instead of reading past everything before it — that's what made "chase a pointer" a fast operation instead of a fantasy. IDS introduced the **set**: a named, stored relationship between one owner record and its member records, wired together as a ring of pointers the moment a member record was written. A program no longer scanned to find related data. It navigated — start on a record, follow a named set to the next one, one pointer at a time. IDS became the seed of a much bigger standard: the CODASYL committee's Data Base Task Group (DBTG) published a report in 1971 formalizing this network model as a data definition language and data manipulation language, and it became the dominant way large companies ran their data through the 1970s and into the 1980s, under products like IDMS.

Bachman's 1973 Turing Award lecture was titled "The Programmer as Navigator" — an apt description of what writing one of these programs actually felt like: you were always somewhere in the data, and your job was to steer. That same lecture is also where the story gets a second act. A researcher at IBM named Edgar Codd had, a few years earlier, proposed a completely different idea — the relational model — where you declare *what* you want and the system figures out *how* to get it, instead of you writing the navigation yourself. Bachman defended navigation as the more honest, more efficient way to work with data at scale. History mostly sided with Codd: the relational model, and SQL built on top of it, is what runs underneath almost everything today. But the thing both men were arguing about — that data should be a shared, managed structure instead of a pile of per-program files — is the idea Bachman actually won his award for, and it's the ground both models stand on.

---

## CS Graduate Level

### 1. Before IDS: the flat file was the database

Through the late 1950s, "the database" for a business application was whatever sequential files that application's programs happened to read. A COBOL program's `DATA DIVISION` hard-coded the exact layout of the records it processed — field names, sizes, order — directly into the source. If two programs needed to relate two files (orders to customers, employees to departments), each one independently wrote code to read one file, extract a key field, and match it against the other, usually via a sort-merge pass because tape only supports sequential access. Three consequences followed directly from this: (1) relationships between records existed only as *logic*, re-implemented in every program that needed them, never as *data* the system itself understood; (2) changing a file's layout meant finding and fixing every program that touched it; (3) answering a genuinely new question about the data meant writing a genuinely new program, because there was no way to ask the file system anything except "give me the next record."

### 2. What IDS introduced: the set as a stored, navigable relationship

Bachman's Integrated Data Store, operational at General Electric by 1963, introduced the **set** as a first-class schema object: a named 1-to-many relationship between one *owner* record type and one *member* record type. Crucially, a set instance wasn't computed at query time — it was *materialized* as a physical structure the moment data was written, typically a ring of pointers: owner → first member → second member → ... → last member → owner (closing the loop), often with a third pointer from each member directly back to its owner for O(1) upward navigation. `implementation.py`'s `Record.next` / `.prior` / `.owner` dicts are exactly this three-pointer scheme, one instance per set type a given record participates in.

```python
def _connect(self, set_name, owner, member):
    member.owner[set_name] = owner
    if owner.next.get(set_name) is None:        # empty ring: owner points to itself
        owner.next[set_name] = owner
        owner.prior[set_name] = owner
    last = owner.prior[set_name]                  # FIFO: insert after the current last member
    member.prior[set_name] = last
    member.next[set_name] = owner
    last.next[set_name] = member
    owner.prior[set_name] = member
```

This is a genuine change in what "the database" *is*: not a collection of independent files, but one shared structure where relationships are stored data, maintained automatically as records are added, and available to every program that opens the database — not re-derived per program.

### 3. Navigation: what a DML program actually did

CODASYL's DBTG standardized the language around this structure in its 1971 report. The verbs `implementation.py` implements are a direct, if simplified, subset: `STORE` (write a record, auto-connecting it into any set it's an AUTOMATIC member of), `FIND ANY <type> ...` (the one true search — locate an entry point by scanning or, in a real system, an index), and the navigational trio `FIND FIRST` / `FIND NEXT` / `FIND OWNER WITHIN <set>`, each of which reads a single stored pointer rather than searching anything.

The system tracked **currency indicators** throughout: current of run unit (the single most recently touched record, database-wide), current of each record type, and current of each set type. Every DML verb both *reads* currency (to know where to navigate from or where to connect a new member) and *updates* it (to establish where the program is now). This is the literal mechanism behind "the programmer as navigator" — you never pass a record's address around explicitly; you say "the current one," and the runtime remembers where you left off, the same way a subway system tracks "current station" instead of making you carry a map reference on a piece of paper.

```python
def _touch(self, record):
    self.current_of_run_unit = record
    self.current_of_type[record.record_type] = record
    for set_name, set_type in self.schema_sets.items():
        if record.record_type in (set_type.owner_type, set_type.member_type):
            self.current_of_set[set_name] = record
```

### 4. What this bought, and what it cost

The gain was real: once positioned, every navigational step touches exactly the records involved in the answer, never the rest of the file. `scan_for_members()` in `implementation.py` — read every record, check a field — versus `find_first`/`find_next` — follow a pointer — is the entire before/after of this chapter made concrete: same answer, different amount of the database touched to get it.

The cost, which is exactly what the relational model would later attack, was that the navigation *was the program*. A query wasn't a description of what you wanted; it was a specific sequence of FIND verbs walking specific sets in a specific order, chosen by the programmer at the time the program was written, against the schema as it existed then. If the schema changed — a new set added, a record's set membership altered — every program whose navigation assumed the old shape could silently need rewriting. Data and access path were coupled at the program level, not just the storage level.

### 5. What descended from it, and where it lost

IDS's set concept, generalized and standardized by CODASYL's DBTG, powered network-model DBMSs that ran enterprise computing through the 1970s and into the 1980s — IDMS (built directly on Bachman's ideas) being the best-known. The competing idea — E. F. Codd's 1970 relational model, where a program *declares* what it wants via set-at-a-time operations and a query optimizer decides how to navigate — eventually displaced it almost entirely, because it decoupled programs from physical structure: change the schema, and only the optimizer's plans need to adapt, not every application. SQL is Codd's declarative idea made concrete and standardized. Bachman's Turing lecture, "The Programmer as Navigator," is in large part a direct defense of navigation against exactly this criticism, delivered the same year IBM began the System R project that would prove the relational model could actually perform.

But the deeper idea Bachman is credited for outlived the specific navigational syntax: that an organization's data should live in one shared, managed structure with relationships as real as the records themselves — a *database*, administered as its own thing, distinct from any single application — rather than a pile of per-program files. Every relational database, every graph database, and every modern application built on a shared schema is still standing on that premise, whatever query language sits on top of it. Even the physical trick underneath IDS's rings — following an explicit pointer instead of searching — reappears today wherever an index or a foreign-key-backed join path is used to avoid a full table scan; the interface changed from "you write the pointer-chase" to "the query planner writes it for you," but the underlying move, replace search with a stored path, is the same one Bachman made in 1963.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [The Programmer as Navigator](https://doi.org/10.1145/362534.362560) *(1973 Turing Award Lecture)* | Communications of the ACM | 1973 |
| Integrated Data Store — internal General Electric documentation and the MIACS project | General Electric, Phoenix/Philadelphia | 1963 |
| [CODASYL Data Base Task Group Report](https://dl.acm.org/doi/10.1145/1247610.1247611) | ACM (DBTG of CODASYL) | 1971 |
| [A Relational Model of Data for Large Shared Data Banks](https://doi.org/10.1145/362384.362685) *(E. F. Codd — the competing model referenced in the lecture)* | Communications of the ACM | 1970 |

---

*Previous: [Week 07 — Edsger W. Dijkstra (1972)](../07-edsger-dijkstra-1972/)*

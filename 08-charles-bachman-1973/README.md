# Week 08 — Charles W. Bachman (1973)

**ACM Turing Award citation:** *"For his outstanding contributions to database technology."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — Bachman's core idea in about 50 lines: records hold the addresses of other records, a "set" is a ring of pointers from an owner through its members and back, and you answer a question by walking the ring instead of searching the file.

[`implementation.py`](./implementation.py) — a miniature Integrated Data Store: records with database keys, owner/member sets as circular doubly linked rings, a CALC key for the first lookup, the CODASYL style verbs (`STORE`, `FIND ANY`, `FIND FIRST/NEXT/PRIOR/LAST/OWNER WITHIN`, `GET`, `MODIFY`, `ERASE`), and currency indicators that remember where you are. It also builds the "before": a flat file you scan from the top, with a counter so you can compare the cost.

```
DML text (STORE / FIND / GET ...)
    -> parse()          split a line into a verb and arguments
    -> Database.*       follow or build pointers, update currency
    -> printed result   plus a status (OK, END-OF-SET, NOT-FOUND ...)
```

What it supports:
- A network schema where `LINE` belongs to two sets at once (`ORDER_LINE` and `PROD_LINE`)
- Automatic set membership on `STORE`, where the owner is chosen by currency, as in CODASYL
- Currency indicators: current of run unit, of record type, and of each set
- `compare <product>`: the same question answered by a tape scan and by navigation, with the cost of each
- `filler <n>`: pile on unrelated customers and watch the scan get slower while navigation does not
- A REPL, a script loader (`.dml` files), a 24-case test suite, and a verbose mode that prints every pointer hop and every currency change

```bash
python3 concept.py                       # the core idea, plain
python3 implementation.py                # interactive REPL
python3 implementation.py scratch.dml    # run a DML script file
python3 implementation.py --test         # test suite (24 cases)
python3 implementation.py --verbose      # REPL that prints every hop and currency change
```

Example session:

```
ids> demo
demo database loaded (14 records)
ids> FIND ANY PRODUCT name=Widget
OK: PRODUCT #1  name=Widget price=10
ids> FIND FIRST LINE WITHIN PROD_LINE
OK: LINE #5  qty=2
ids> FIND OWNER WITHIN ORDER_LINE
OK: ORDER #4  no=O1
ids> FIND OWNER WITHIN CUST_ORDER
OK: CUSTOMER #3  name=Acme city=Boston
ids> compare Widget
tape scan : ['Acme', 'Birch']  records read: 5
navigation: ['Acme', 'Birch']  pointer hops: 8
ids> filler 100
added filler customers (314 records)
ids> compare Widget
tape scan : ['Acme', 'Birch']  records read: 105
navigation: ['Acme', 'Birch']  pointer hops: 8
```

The tape scan reads more rows every time the file grows. Navigation stays at 8 hops because the 100 new customers never bought a Widget, so they are not in the Widget ring.

---

## Full Worked Example

### The data

Two products, three customers, four orders, five line items. These are the records `demo` creates. Each gets a database key (its address) in the order it is stored.

| dbkey | Record |
|---|---|
| #1 | PRODUCT Widget |
| #2 | PRODUCT Gadget |
| #3 | CUSTOMER Acme |
| #4 | ORDER O1 (Acme) |
| #5 | LINE qty=2, in O1, product Widget |
| #6 | LINE qty=1, in O1, product Gadget |
| #7 | ORDER O3 (Acme) |
| #8 | LINE qty=3, in O3, product Gadget |
| #9 | CUSTOMER Birch |
| #10 | ORDER O2 (Birch) |
| #11 | LINE qty=5, in O2, product Widget |
| #12 | CUSTOMER Cedar |
| #13 | ORDER O4 (Cedar) |
| #14 | LINE qty=1, in O4, product Gadget |

The Bachman diagram. An arrow runs from owner to member. `LINE` has two arrows pointing at it, so it has two owners:

```
CUSTOMER --CUST_ORDER--> ORDER --ORDER_LINE--> LINE <--PROD_LINE-- PRODUCT
```

### What a set looks like in memory

A set is a ring. The owner is the head. Take `PROD_LINE` for Widget (#1). Its members are the lines that mention Widget, #5 and #11:

```
owner #1 --next--> #5 --next--> #11 --next--> back to #1
owner #1 <--prior-- #5 <--prior-- #11 <--prior-- ...
```

Every member also stores its owner, so from #11 you can jump straight to #1. An empty set is the owner pointing at itself. "Reached the end" always means "the next pointer led back to the owner." The `show` command prints this:

```
LINE #5  qty=2
      member ORDER_LINE  next=#6 prior=#4 owner=#4
      member PROD_LINE   next=#11 prior=#1 owner=#1
```

Line #5 is in two rings at once. In `ORDER_LINE` its owner is order #4. In `PROD_LINE` its owner is product #1.

### Before: the tape scan

Question: which customers bought a Widget?

Before IDS you have a flat file, one row per line item, and you read it from the top:

| Row read | Product | Widget? | Customers so far |
|---|---|---|---|
| 1 | Widget (Acme) | yes | Acme |
| 2 | Gadget (Acme) | no | Acme |
| 3 | Gadget (Acme) | no | Acme |
| 4 | Widget (Birch) | yes | Acme, Birch |
| 5 | Gadget (Cedar) | no | Acme, Birch |

Five rows read for a five row file. With a million rows it is a million reads, every time you ask.

### After: navigation, hop by hop

Same question, same data. Each step is one pointer follow. The last column is the currency we hold afterwards.

| Hop | Command | From | To | Result |
|---|---|---|---|---|
| 1 | `FIND ANY PRODUCT name=Widget` | CALC | #1 | Widget. Current of `PROD_LINE` = #1 |
| 2 | `FIND FIRST LINE WITHIN PROD_LINE` | #1 | #5 | LINE qty=2. Current of `PROD_LINE` and `ORDER_LINE` = #5 |
| 3 | `FIND OWNER WITHIN ORDER_LINE` | #5 | #4 | ORDER O1. Current of `CUST_ORDER` = #4 |
| 4 | `FIND OWNER WITHIN CUST_ORDER` | #4 | #3 | CUSTOMER Acme. Record it. |
| 5 | `FIND NEXT LINE WITHIN PROD_LINE` | #5 | #11 | LINE qty=5 |
| 6 | `FIND OWNER WITHIN ORDER_LINE` | #11 | #10 | ORDER O2 |
| 7 | `FIND OWNER WITHIN CUST_ORDER` | #10 | #9 | CUSTOMER Birch. Record it. |
| 8 | `FIND NEXT LINE WITHIN PROD_LINE` | #11 | #1 | Back at the owner, so status `END-OF-SET`. Done. |

Eight hops. Gadget lines, Cedar and every filler customer were never touched.

### Why step 5 works: currency

At hop 4 we moved to a CUSTOMER. That record is not in `PROD_LINE`, so the current of `PROD_LINE` was not changed. It is still line #5. That is why `FIND NEXT LINE WITHIN PROD_LINE` at hop 5 continues from #5 and lands on #11. Currency is the program's finger on the data. Each set keeps its own finger.

### Edge case 1: the end of a set

Hop 8 above. `FIND NEXT` follows the next pointer from #11 and arrives at #1, the owner. The system does not return the owner as a result. It returns `END-OF-SET`. Your loop is `while status is OK`.

### Edge case 2: STORE with no current owner

```
ids> STORE ORDER no=X
NO-CURRENT: no current CUSTOMER to own it in CUST_ORDER
```

An `ORDER` must be inserted into a `CUST_ORDER` ring, and the ring is chosen by the current customer. No current customer, no insert. This is why the demo script runs `FIND ANY PRODUCT name=Widget` before `STORE LINE qty=2`: the new line goes into the ring owned by the current order (#4) and the ring owned by the current product (#1).

### Edge case 3: you cannot erase an owner that still has members

```
ids> FIND ANY CUSTOMER name=Acme
ids> ERASE
ERROR: still owns members in CUST_ORDER
```

If it allowed that, #4 and #7 would hold an owner pointer to a record that no longer exists.

---

## ELI5

Imagine a giant toy box with a thousand toys thrown in. You want every red car. You dump the box out and look at each toy, one by one.

Now imagine each red car has a string tied to it, and the strings link all the red cars in a circle. You grab one red car and follow the string to the next. When the string brings you back to where you started, you have them all.

Charles Bachman invented the strings. He did it for computers.

---

## ELI10

In the 1950s a company kept its records on reels of magnetic tape, or on punched cards. To find every customer who bought a Widget, the computer ran the tape from the beginning and looked at every single record. Ask a second question and it ran the whole tape again. A bigger company meant a longer wait.

Charles Bachman worked at General Electric. Around 1963 his team built the Integrated Data Store, one of the first database systems. The records now lived on disks, where the computer could jump straight to any spot. Every record got an address, called a database key, and records could store the addresses of other records. A customer record pointed at its first order. That order pointed at the next order. The last one pointed back to the customer, so the orders formed a circle. To find a customer's orders, you stepped around the circle.

The clever part was that one record could sit in two circles at once. An order line belonged to the circle of its order and also to the circle of its product. So you could start at a Widget, step around everything that mentions Widgets, and climb from each line to the order and the customer who bought it. When he got his Turing Award in 1973, Bachman called the programmer a navigator. You do not search for the data. You travel to it.

---

## CS Graduate Level

### 1. What came before

Business data processing in the 1950s was file based. Records lived in sequential files on magnetic tape or cards, sorted by a key. A program was a pass over one or more files: read, test, write. Answering a new question usually meant a new program and often a sort followed by a merge. The data layout was welded into every program that touched it. Random access disks (the IBM 305 RAMAC, 1956) made it possible to jump to a record, but there was no general way to organize data on them. Each application invented its own scheme.

### 2. Integrated Data Store (GE, early 1960s)

Bachman started IDS at General Electric around 1960 and it ran on the GE 225 by 1963. It is usually named as the first direct access database management system. Three ideas:

- **Database keys.** Each record has a unique address, so a pointer is just a stored database key.
- **Chains (sets).** A record type can own a chain. Records are linked by NEXT pointers, with optional PRIOR and OWNER pointers. The last record points back to the owner, so the chain is a ring. An owner with no members points at itself.
- **Integration.** Many record types, many chains, one shared database used by many programs. Hence "integrated".

A record can be a member of more than one chain, for example an order line that is in the order's chain and the product's chain. That makes the structure a graph, a network, not a tree. The same year IBM built IMS (for the Apollo program, mid 1960s), which was hierarchical: every record has one parent. A many to many relationship in IMS needs duplicated data or awkward workarounds. In a network it is two sets with a shared member.

### 3. The Bachman diagram

Bachman drew the schema as boxes (record types) and arrows from owner to member, one arrow per set type. This data structure diagram was published in 1969 and is the ancestor of the entity relationship diagrams that came later. It is the picture in `implementation.py`:

```
CUSTOMER --CUST_ORDER--> ORDER --ORDER_LINE--> LINE <--PROD_LINE-- PRODUCT
```

### 4. CODASYL and the network model

IDS was proprietary. In 1965 the CODASYL committee (the same group behind COBOL) formed a Data Base Task Group. Its 1969 report and 1971 revision turned IDS ideas into a standard: a schema data definition language, a subschema for each application, and a data manipulation language embedded in COBOL. The vocabulary in this chapter's code comes from there:

| Concept | What it is |
|---|---|
| Set type | A named owner to member relationship |
| CALC key | A field hashed to place a record, so `FIND ANY` finds it in about one access |
| Currency indicators | Per run unit, per record type, per set: the "current" record |
| `FIND NEXT/PRIOR/FIRST/LAST WITHIN set` | Move along a ring from the current position |
| `FIND OWNER WITHIN set` | Jump from a member to its owner |
| Insertion class | `AUTOMATIC` or `MANUAL` set membership on `STORE` |
| Status codes | End of set, record not found, and so on |

Currency is the important subtlety. A program has no variable holding "the record". The system holds a table of currents, and every FIND rewrites part of it. The same call, `FIND NEXT ORDER WITHIN CUST_ORDER`, means different things depending on where the last FIND left you. `STORE` also uses currency to pick the owner of each set the new record joins.

### 5. The Turing lecture: the programmer as navigator

Bachman's 1973 lecture used a Copernican analogy. Before Copernicus, everything was described relative to the Earth. Before the database idea, data was described relative to the machine and the program that ran on it. Bachman argued for putting the data at the center and letting programs orbit it. He described the programmer as a navigator moving through an n dimensional data space, following access paths, with the access path being a first class concept. He also named the cost: a navigator has to know the map. If the structure changes, the programs that walk it break.

### 6. What descended from it and what replaced it

- **IDMS** (Cullinane, later Computer Associates) was a commercial CODASYL database and ran for decades in banks and insurers.
- **Relational model.** Edgar Codd's 1970 paper argued that programs should say what they want and let the system decide how to get it, so data independence replaces navigation. The Bachman versus Codd argument ran through the 1970s (they debated at ACM SIGMOD in 1974). SQL and the relational systems won the mainstream by the 1980s.
- **Navigation did not die.** Graph databases (Neo4j and similar) store relationships as direct pointers between nodes and traverse them. Document stores embed related data. Object databases and ORMs with lazy loading follow references from object to object. Linked data structures inside every program are the same idea in memory.
- **Index free adjacency** in a graph database is IDS pointers by another name.
- Late in his career Bachman also chaired the work that produced the ISO seven layer OSI reference model for networking.

### 7. Lasting impact

Two lessons carry forward. First, a shared, structured, durable store of data that many programs use is a different thing from a file, and it deserves its own system. Second, there is a real tradeoff between navigation (fast and predictable for the access paths you planned, brittle for the ones you did not) and declarative queries (flexible, but you rely on an optimizer). Every modern data system picks a point on that line, and Bachman drew one end of it.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [The Programmer as Navigator](https://doi.org/10.1145/355611.362534) (Turing Award lecture) | Communications of the ACM 16(11) | 1973 |
| [A Relational Model of Data for Large Shared Data Banks](https://doi.org/10.1145/362384.362685) (E. F. Codd, the counterpoint) | Communications of the ACM 13(6) | 1970 |
| Data Structure Diagrams | Data Base (ACM SIGBDP) 1(2) | 1969 |
| CODASYL Data Base Task Group Report | CODASYL | 1969, 1971 |
| A General Purpose Programming System for Random Access Memories (Bachman and Williams) | AFIPS Fall Joint Computer Conference | 1964 |

Note: I am confident of the two linked DOIs. The other three are cited from memory, so check titles and venues before quoting them.

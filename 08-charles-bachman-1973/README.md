# Week 08 — Charles W. Bachman (1973)

**ACM Turing Award citation:** *"For his outstanding contributions to database technology."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — Bachman's idea in about 60 lines: records that point at each other, a "set" as a ring of pointers from one owner through its members, and a query answered by following pointers instead of scanning files.

[`implementation.py`](./implementation.py) — a miniature Integrated Data Store: records under database keys, sets as circular next/prior rings, CALC records found by hashing, currency indicators, and the CODASYL verbs `FIND`, `GET`, `STORE`, `MODIFY`, `CONNECT`, `DISCONNECT`, `ERASE`. Every record fetch is counted so you can see what navigation costs.

[`practice.ids`](./practice.ids) — a scratch file for you to write navigation programs in.

```
schema (record / set lines)
    -> Database       records, rings, hash table, currency indicators
    -> Interpreter    one DML verb per line, loop ... end blocks
    -> printed result
```

What it supports:
- A schema of record types and set types (`record`, `set`). A set has one owner type and one member type. Owner `SYSTEM` makes a set that holds every record of a type, which is how you walk "all suppliers".
- `find calc` (hash straight to a record), `find key` (go to a database key), `find first|last|next|prior within SET`, `find owner within SET`
- `store`, `get`, `modify`, `connect`, `disconnect`, `erase`, `erase all`
- Currency indicators you can inspect (`currency`) and the rings you can inspect (`sets`)
- `loop ... end`, which repeats until a command fails, the way a COBOL program looped until `DB-STATUS` said end of set
- `export_flat_files()` and `flat_file_query()`: the "before", answering the same question with sequential files
- A 25-case test suite, including a pointer-integrity checker run after inserts and deletes

```bash
python3 concept.py                        # the core idea, plain
python3 implementation.py                 # interactive REPL (type 'demo' first)
python3 implementation.py practice.ids    # run a script file
python3 implementation.py --test          # test suite (25 cases)
python3 implementation.py --verbose       # REPL that prints every record fetch
```

Example session:

```
ids> demo
  ...
  demo loaded: 3 suppliers, 3 parts, 6 supplies
ids> find calc PART P2
  found PART #1005  pno=P2  name=Bolt
ids> find next within PART-SUPPLY
  found SUPPLY #1008  qty=200
ids> find owner within SUPPLIER-SUPPLY
  found SUPPLIER #1001  sno=S1  name=Smith  city=London
ids> find next within PART-SUPPLY
  found SUPPLY #1011  qty=400
ids> find owner within SUPPLIER-SUPPLY
  found SUPPLIER #1002  sno=S2  name=Jones  city=Paris
```

Notice the second `find next` still works after you jumped to a supplier. The program remembered where it was in the part's ring. That memory is the currency indicator, and it is the whole trick.

---

## Full Worked Example

The demo database: three suppliers, three parts, and six supply records saying who supplies what.

| Supplier | Part | Qty |
|---|---|---|
| S1 Smith | P1 Nut | 300 |
| S1 Smith | P2 Bolt | 200 |
| S1 Smith | P3 Screw | 400 |
| S2 Jones | P1 Nut | 300 |
| S2 Jones | P2 Bolt | 400 |
| S3 Blake | P2 Bolt | 200 |

The question: **which suppliers supply part P2?**

### Step 0 — what is actually stored

Every record gets a database key (its address). `demo` stores suppliers as `#1001` to `#1003`, parts as `#1004` to `#1006`, and supplies as `#1007` to `#1012`.

A supply record is not a row with two foreign key columns. It is a record that is a **member of two sets at once**: one ring hanging off its supplier, one hanging off its part. Here are both set types, exactly as `sets` prints them:

```
set SUPPLIER-SUPPLY  (SUPPLIER owns SUPPLY)
  [SUPPLIER #1001] -> #1007 -> #1008 -> #1009 -> [SUPPLIER #1001]
  [SUPPLIER #1002] -> #1010 -> #1011 -> [SUPPLIER #1002]
  [SUPPLIER #1003] -> #1012 -> [SUPPLIER #1003]
set PART-SUPPLY  (PART owns SUPPLY)
  [PART #1004] -> #1007 -> #1010 -> [PART #1004]
  [PART #1005] -> #1008 -> #1011 -> #1012 -> [PART #1005]
  [PART #1006] -> #1009 -> [PART #1006]
```

Read the first line: supplier `#1001` (Smith) points to supply `#1007`, which points to `#1008`, which points to `#1009`, which points back to Smith. A ring. The second block shows the same supply records again, this time in the rings that hang off parts. `#1008` appears in Smith's ring and in the Bolt ring. Each supply also stores a pointer to its owner in each set, so from a supply you can jump straight to either supplier or part.

### Step 1 — find the starting record (hashing, no search)

`find calc PART P2` must land on the Bolt record without scanning. CALC hashes the record type and key into one of 7 buckets (the toy hash in the code). All three parts happen to hash to bucket 1, which is a collision on purpose:

```
bucket 1 holds: #1004 (P1), #1005 (P2), #1006 (P3)
```

The lookup reads `#1004`, sees P1, reads `#1005`, sees P2. **2 record reads.** It did not matter how many suppliers or supplies existed. Currency now says: current of run unit = `#1005`, current of set PART-SUPPLY = `#1005` (the owner).

### Step 2 — walk the ring (each `find next`)

`find next within PART-SUPPLY`. Current of the set is the owner `#1005`, so "next" means the owner's next pointer, `#1008`. Two reads: the code reads the current record `#1005` to get its pointer, then reads the target `#1008`. Currency: run unit = `#1008`, and also current of both PART-SUPPLY and SUPPLIER-SUPPLY, because this supply record is a member of both.

### Step 3 — hop to the other owner (`find owner`)

`find owner within SUPPLIER-SUPPLY`. The current of that set is `#1008` (set in step 2), and its stored owner pointer says `#1001`. One read: Smith. (The code reads the owner directly from the pointer, no scan.) Notice that the current of PART-SUPPLY is still `#1008`. Finding a supplier did not move it.

### Step 4 — repeat until the ring closes

```
find next within PART-SUPPLY      -> #1011 (qty 400)
find owner within SUPPLIER-SUPPLY -> #1002 Jones
find next within PART-SUPPLY      -> #1012 (qty 200)
find owner within SUPPLIER-SUPPLY -> #1003 Blake
find next within PART-SUPPLY      -> next pointer of #1012 is #1005, the owner
```

When the next pointer leads back to the owner, the ring is finished and the status is `END-OF-SET`. The `loop ... end` block stops on exactly that:

```
  status: END-OF-SET  (no next member in set PART-SUPPLY)
  (loop ends: END-OF-SET)
```

Total: 2 reads for the CALC, then 3 members x (2 reads for `find next` + 1 read for `find owner`) = 9, plus 1 read for the final `find next` that discovers the ring is closed = **12 reads for the whole answer**: Smith, Jones, Blake.

### The "before": sequential files

`flat_file_query` flattens the same data into the three files a shop would have had, with plain `sno` and `pno` columns instead of pointers. To answer the question it reads every supply record, and for each one that matches P2 it scans the supplier file from the top until the supplier turns up:

```
read supply S1/P1  -> no
read supply S1/P2  -> match: read S1                      (2 reads)
read supply S1/P3  -> no
read supply S2/P1  -> no
read supply S2/P2  -> match: read S1, S2                  (3 reads)
read supply S3/P2  -> match: read S1, S2, S3              (4 reads)
```

Also **12 reads** on 6 supply records. At this size, navigation does not win. That is honest, and the point of the next part.

### Why it still wins: scale

The test suite builds bigger databases (every supplier supplies 9 parts, and every supplier supplies P3), and compares reads for "who supplies P3":

| Suppliers | Supply records | Flat files (reads) | Navigation (reads) |
|---|---|---|---|
| 3 | 27 | 33 | 14 |
| 60 | 540 | 2,370 | 185 |
| 200 | 1,800 | 21,900 | 605 |

Flat files grow with supplies x suppliers. Navigation grows with the number of answers. That is the entire argument Bachman was making in 1973: once data is on a disk you can jump around in, a program should follow links to what it needs, not read everything.

### Edge cases and failures

**Walking off the end.** `find next` when the next pointer is the owner gives `END-OF-SET`. Not an exception that crashes the program: a status the program is expected to check.

**Storing with no owner in view.** `store SUPPLY qty=1` connects the new supply to the *current* supplier and the *current* part. If the program never found them, there is no currency, and the store is refused with `NO-CURRENCY` before anything is changed.

**Erasing an owner that still has members.** With S2 current:

```
ids> erase
  status: HAS-MEMBERS  (SUPPLIER #1002 still owns members in SUPPLIER-SUPPLY (use erase all))
```

`erase all` deletes Jones and his supplies, and unlinks those supplies from the part rings they were also in. The test suite runs the pointer-integrity checker after this: every ring closes, every prior pointer matches, every owner pointer is right.

**Duplicate CALC key.** Storing a second supplier `S1` is refused with `DUPLICATE-KEY`. CALC records are found by hashing, so the key has to be unique.

---

## ELI5

Imagine a toy box where every toy has a string tied to it. Before, all your toys were in one big pile and to find "the red cars" you had to dig through the whole pile every time. Bachman tied strings between toys that belong together. The red car has a string to the other red cars, and a string to the garage it lives in. Now you pick up one red car, follow the string to the next red car, and the next, and you stop when the string comes back to where you started. You never dig through the pile again.

---

## ELI10

In the 1950s, companies kept their records on stacks of punched cards and reels of magnetic tape. Tape is like a cassette: to get to a record in the middle you have to wind past everything before it. So almost every question meant reading the whole tape. "Which suppliers sell us part number 2?" meant reading every order, and for each match, reading through the list of suppliers to find the name.

Then disks arrived, which you can jump around on. Charles Bachman, working at General Electric around 1961, built a system called the Integrated Data Store, or IDS, that used this. Instead of keeping records in a line, he made records point at each other. A supplier record pointed at the first order it was part of, that order pointed to the next, and the last one pointed back to the supplier, forming a loop. An order could sit in two loops at once, one for its supplier and one for its part, so you could start at a part, follow its loop, and hop across to each supplier.

Bachman called the programmer who works this way a navigator, because they move through the data by following links, like a ship following a route. Other computer companies liked the idea so much that a committee called CODASYL wrote it down as a standard in 1969, and for about a decade this was how most big companies stored their data. In 1973 he got the Turing Award for it.

---

## CS Graduate Level — Records That Point At Each Other

### 1. The state of the art before IDS: files and sort-merge

Business data processing in the 1950s was built on sequential files: punched cards, then magnetic tape. A tape can only be read in order, so every program was a batch job: sort the transactions into the same key order as the master file, then read both once, in step (a sort-merge), writing a new master. Related data lived in different files joined by matching key values, and the cost of any query was set by the size of the files, not the size of the answer. Application programs also embedded the file layout. Change the layout and every program that read it broke.

Random-access disks (the IBM 305 RAMAC in 1956, then faster drives in the early 1960s) changed what was possible: you could go straight to a record if you knew where it was. What was missing was a general way to organise records so programs could actually exploit it.

### 2. What was new: IDS

Bachman started IDS at General Electric around 1961 and it first ran on the GE 225 around 1963, built with Homer Carney and others, and was first put to heavy use on the Weyerhaeuser order-processing and manufacturing-control project. Bachman and Williams described it in *A General Purpose Programming System for Random Access Memories* at the 1964 Fall Joint Computer Conference. Four ideas carried it.

**Records with stable addresses, found by hashing.** Each record has a database key. A record can be given a CALC key; IDS hashes it to a page and looks in that page and its overflow, so finding a record by name costs a few reads regardless of file size. The implementation models this with a 7-bucket table so collisions (the three parts all land in bucket 1) show up in the read counts.

**Sets as pointer rings.** A set type connects one owner record type to one member record type. An occurrence is an owner plus a chain of members, circular: owner to first member to ... to last member back to owner. In the code each record keeps `ring[set] = [next, prior]` and each member keeps `owner[set]`. Insertion is local pointer surgery:

```python
before = records[before_key]
after = records[before.ring[set][1]]
record.ring[set] = [before_key, after.key]
before.ring[set][1] = record.key
after.ring[set][0] = record.key
```

Deletion is the reverse, and neither touches any other record in the set. Ring order is declared in the schema (`first`, `last`, or `sorted` by a field).

**A record can be a member of several sets.** This is what separates the network model from the hierarchical model that IBM's IMS used. In a hierarchy every record has exactly one parent, so a supply that belongs to both a supplier and a part forces a duplicate or a workaround. In the network model it is simply a member of two rings.

**Currency indicators.** A program is always "somewhere" in the database. The run unit keeps a current record for the whole run, one per record type, and one per set type. A successful `FIND` or `STORE` updates them under a fixed rule: the record becomes current of the run unit, of its type, and of every set it owns or belongs to. `find next within S` means "move from the current of S", and `store` connects a new member to the current owner of each automatic set. This is the part that surprises people coming from SQL: the meaning of a statement depends on state left behind by earlier statements.

### 3. Navigation: the verbs and the "navigator"

The data manipulation language is a handful of record-at-a-time verbs: `FIND` (position), `GET` (read into program variables), `STORE`, `MODIFY`, `CONNECT`, `DISCONNECT`, `ERASE`. A query is a program: find a start, loop with `FIND NEXT`, `FIND OWNER`, test a status register after each call. Bachman's 1973 Turing lecture, *The Programmer as Navigator*, argued this was a genuine change of role. The old programmer moved through a fixed sequential file; the new one chooses a path through a web of data, and the database designer's choice of sets decides which paths are cheap. He compared the shift to the Copernican change of viewpoint from machine-centred to data-centred computing.

The cost model is what makes this attractive. In the worked example, a CALC find plus ring walks costs reads proportional to the answer, 605 reads at 200 suppliers against 21,900 for the sequential files.

### 4. CODASYL and the standard

IDS was GE's product, but the idea spread through the Conference on Data Systems Languages (CODASYL), the committee that also stewarded COBOL. Its Data Base Task Group (DBTG) formed in the mid 1960s with Bachman a key figure, and its 1969 report, revised in 1971, specified a schema data definition language, a subschema for applications, and a COBOL-embeddable data manipulation language, all built on IDS's design. That became the "CODASYL network model". Commercial descendants included IDMS (from Cullinane, later Cullinet), Honeywell's IDS/II (Honeywell took over GE's computer business), and others. The sets, currency and status registers in this repo's implementation follow that model, simplified.

Bachman also invented a notation for drawing record types and sets, the **Bachman diagram** (data structure diagram): a box per record type, an arrow per set pointing from owner to member. It is a direct ancestor of entity-relationship diagrams.

### 5. The relational challenge

In 1970 Edgar Codd published *A Relational Model of Data for Large Shared Data Banks*, arguing that programs should describe the data they want, not the path to it. Where Bachman's program says "find part P2, then loop through its supply ring and hop to the owner", a relational query states the relationship (supplier joined to supply joined to part, with part = P2) and leaves the access path to the system. Two consequences of that argument were hard on the network model.

*Data independence.* In a navigational program the path is in the application code. If a DBA reorganises the sets, programs break. Relational queries survive because the optimiser picks the path.

*Set-at-a-time.* A navigator handles one record per call and writes the loop. A relational statement operates on whole sets of rows.

The well-known contest between the two camps ran through the 1970s (including a 1974 ACM face-off between Codd and Bachman). Relational databases won the commercial argument, helped by System R, SQL, and later Oracle, DB2 and others. Network and hierarchical systems stayed in banks and airlines, where IDMS and IMS still run production workloads.

### 6. What descended from it and what is still around

- **Declarative query optimisers** exist because navigation proved the value of good access paths and then showed the cost of hand-coding them.
- **Graph databases** (Neo4j, and property graph engines generally) store records that point at each other and let you traverse relationships. They are, in structure, the network model again, usually with a declarative query language on top.
- **Document and object stores** with references, and **ORMs** with lazy-loaded relationships, reintroduce record-at-a-time navigation. The N+1 query problem is a navigator's loop written by accident.
- **Linked structures in memory** (pointer-based trees and rings) use the same insert and unlink surgery as the sets here.
- **Bachman's later work:** after IDS he moved to Honeywell, then Cullinane and then his own firm, Bachman Information Systems, building tools for modelling data. He also chaired the ISO committee whose work produced the seven-layer OSI reference model for network protocols, the layers still taught today.

### 7. The thread

IDS stands on an observation that looks obvious now: when memory can be addressed directly, relationships between records can be stored as addresses. Everything else follows: sets, rings, currency, a language of navigation verbs. Codd's later correction was that storing the relationships as addresses *and* making programs follow them is two decisions, and the second one is costly. Both halves of that conversation are still how data systems get argued about.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [The Integrated Data Store — A General Purpose Programming System for Random Access Memories](https://www.mirrorservice.org/sites/www.bitsavers.org/pdf/afips/1964-04_%2325.pdf) *(Bachman and Williams, pp. 411–422 of the proceedings)* | AFIPS Fall Joint Computer Conference | 1964 |
| [The Programmer as Navigator](https://doi.org/10.1145/355611.362534) *(Turing Award lecture)* | Communications of the ACM, 16(11) | 1973 |
| [A Relational Model of Data for Large Shared Data Banks](https://doi.org/10.1145/362384.362685) *(E. F. Codd)* | Communications of the ACM, 13(6) | 1970 |
| CODASYL Data Base Task Group Report *(revised 1971)* | CODASYL Programming Language Committee, ACM | 1969 |

---

*Previous: [Week 07 — Edsger W. Dijkstra (1972)](../07-edsger-dijkstra-1972/)*

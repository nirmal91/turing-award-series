# Week 08 — Charles W. Bachman (1973)

**ACM Turing Award citation:** *"For his outstanding contributions to database technology."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — Bachman's idea in about 50 lines: store a relationship as pointers in a ring (department, then each of its employees, then back to the department), and answer a question by walking the ring instead of reading the whole file.

[`implementation.py`](./implementation.py) — a small network database in the style of IDS and the CODASYL model that grew out of it. Records live at database keys. Sets link one owner to many members as a ring with NEXT, PRIOR and OWNER pointers. CALC lookups use a hash. A many-to-many relationship is built from a connector record that sits in two sets. The program keeps a "currency" (where you are now) and moves with FIND FIRST, FIND NEXT and FIND OWNER. Every record touched is counted, so you can compare navigating with scanning.

```
command line -> parse -> DML verb (STORE / CONNECT / FIND / FIRST / NEXT / OWNER)
             -> pointer updates or pointer hops -> printed result
             -> read counter (what did that cost?)
```

What it supports:
- `store`, `connect`, `disconnect`, `erase` (and `erase ... all` to cascade)
- `find TYPE:name` (CALC), `first SET OWNER`, `next SET`, `owner SET`, `get`
- `scan`: the "before", reading every record like a sequential file
- `compare DEPT`: navigate vs scan for the same question, with read counts
- `check`: verify every ring agrees going forward and backward
- `dump`: print every record with its pointers

```bash
python3 concept.py                          # the core idea, plain
python3 implementation.py                   # interactive REPL
python3 implementation.py practice.dml      # run a script of commands
python3 implementation.py scratch.dml       # your own scratch file
python3 implementation.py --test            # test suite (19 checks)
python3 implementation.py --verbose         # REPL that prints every pointer hop
```

Example session:

```
ids> demo
loaded: 3 departments, 6 employees, 2 projects, 5 assignments
ids> compare Research
Question: which employees are in Research?
  navigate: ['Dee', 'Eve', 'Fay']  records read: 5
  scan:     ['Dee', 'Eve', 'Fay']  records read: 16
  the file has 16 records in total
ids> find DEPT:Research
found #3 DEPT name=Research
ids> first DEPT-EMP DEPT:Research
found #7 EMP name=Dee
ids> next DEPT-EMP
found #8 EMP name=Eve
ids> next DEPT-EMP
found #9 EMP name=Fay
ids> next DEPT-EMP
end of set
```

Same answer both ways. 5 reads against 16. The scan cost grows with the whole file. The navigation cost grows with the size of the answer.

**Before / after.** Before: a tape file, read start to finish, filter in your program. After: land on the owner, follow the ring. The test suite adds 200 unrelated employees to another department and checks the Sales lookup still costs about the same.

---

## Full Worked Example

Use the demo data. Database keys are assigned in the order records are stored.

| key | record |
|---|---|
| 1, 2, 3 | DEPT Sales, Support, Research |
| 4, 5 | EMP Ann, Bob (Sales) |
| 6 | EMP Cy (Support) |
| 7, 8, 9 | EMP Dee, Eve, Fay (Research) |
| 10, 11 | PROJECT Payroll, Atlas |
| 12 to 16 | ASSIGN records (the connectors) |

### Step 1: what a set looks like in memory

The set `DEPT-EMP` for Sales has one owner (key 1) and two members (keys 4 and 5). Stored as pointers:

```
DEPT#1 Sales     owns DEPT-EMP: first=4, last=5
EMP#4  Ann       in DEPT-EMP:   owner=1, next=5, prior=1
EMP#5  Bob       in DEPT-EMP:   owner=1, next=1, prior=4
```

Read it as a ring: 1 -> 4 -> 5 -> 1. Ann's `prior` is 1, which means "I am first, the thing before me is the owner". Bob's `next` is 1, which means "I am last, the thing after me is the owner". That is how you know you reached the end: you arrive back at the owner.

### Step 2: answer "who is in Research?" by navigating

Research is key 3. Its ring is 3 -> 7 -> 8 -> 9 -> 3.

1. `find DEPT:Research`: one hash lookup lands on key 3. Reads so far: 1.
2. `first DEPT-EMP`: read the owner (key 3) to get `first=7`, then read record 7 (Dee). Reads: 3.
3. `next`: Dee's `next` is 8. Read record 8 (Eve). Reads: 4.
4. `next`: Eve's `next` is 9. Read record 9 (Fay). Reads: 5.
5. `next`: Fay's `next` is 3. That is the owner, so the set is over. No read.

Answer: Dee, Eve, Fay. 5 reads.

### Step 3: the same question by scanning

No pointers. Read keys 1 through 16 in order. For each EMP, look up where it belongs and compare the department name. Every record is read once: 16 reads. Same answer.

Add 1,000 more employees to Support and the scan costs about 1,016 reads. The navigation still costs 5.

### Step 4: many-to-many through connector records

Ann works on Payroll and Atlas. An employee can have many projects and a project many employees, so a single set cannot hold it. Bachman's answer is a record that belongs to both. ASSIGN #12 is a member of `EMP-ASSIGN` (owner Ann) and of `PROJ-ASSIGN` (owner Payroll). ASSIGN #13 is in Ann's ring and Atlas's ring.

"Who works on Atlas?" Atlas is key 11. Its `PROJ-ASSIGN` ring holds ASSIGN 13, 14, 15. For each one, `owner EMP-ASSIGN` hops to the employee:

```
13 -> Ann     14 -> Dee     15 -> Eve
```

Answer: Ann, Dee, Eve. One ring walk plus one OWNER hop per member. This is "navigation" in the full sense: down a ring, across a record, up to a different owner.

### Step 5: edge case, removing a member from the middle

Disconnect Eve (key 8) from Research. Her pointers are `prior=7, next=9`. To close the gap:
- Dee (7): `next` changes from 8 to 9.
- Fay (9): `prior` changes from 8 to 7.
- The owner's `first` and `last` stay 7 and 9.

New ring: 3 -> 7 -> 9 -> 3. If Eve had been the first member, the owner's `first` would change instead. If she had been the only member, `first` and `last` would both become empty. The `check` command walks every ring forward and backward to confirm all of this still agrees.

### Step 6: failure case, erase an owner

`erase DEPT:Sales` is refused, because Sales still owns Ann and Bob. Deleting it would leave their `owner` pointers aimed at nothing. `erase DEPT:Sales all` erases the members first, then the owner.

### Step 7: the limit of navigation

"Which employees are named Eve?" has a CALC key, so it is one hop. "Which assignments have more than 10 hours?" has no path. There is no ring that groups assignments by hours. You have to scan. In a network database the paths you can follow fast are the paths somebody designed in advance. That is the trade Codd's relational model attacked in 1970.

---

## ELI5

Imagine a big pile of toy cards, all mixed up. Each card says who owns a toy. To find all of Sam's toys, you have to look at every single card in the pile. That takes forever.

Now imagine Sam's card has a piece of yarn tied to his first toy card. That card has yarn to the next one, and the last one has yarn back to Sam. You grab Sam, follow the yarn, and you have all his toys. You never touch the other cards.

Charles Bachman tied the yarn.

## ELI10

In the early 1960s, a company's information, like who works where and who is working on what, was stored on big spinning magnetic tapes. To answer a question, a computer had to read the tape from the very start and pick out the parts it needed. A bigger company meant a longer tape and a longer wait.

Charles Bachman worked at General Electric. He built a system called the Integrated Data Store, or IDS, around 1961 to 1964. Instead of keeping the records in one long line, he stored them on a disk, where the computer can jump to any spot, and he put pointers in the records. A department record points to its first employee. Each employee points to the next one. The last one points back to the department. That loop is called a set.

So to list the employees in Sales, the computer jumps to Sales and follows the pointers. It reads only the Sales people. Bachman gave the Turing lecture in 1973 and called it "The Programmer as Navigator". Before, programmers processed a pile of data from top to bottom. After, they moved through the data from record to record like a ship following a chart. Bachman compared that change to Copernicus moving the center from the Earth to the Sun.

## CS Graduate Level — Pointers as Relationships, and the Programmer as Navigator

### 1. The state of the art before IDS

Business data processing in the 1950s was built on sequential files: punched cards, then magnetic tape. A program read a master file and a transaction file in the same sort order and wrote a new master file. Two things followed from that. A question about one record cost a pass over the file, and a relationship between two kinds of record (employee and department) was recomputed every time by sorting and merging. Disk drives with random access were arriving, but the software to use them well did not exist.

### 2. What IDS added

IDS (Bachman and colleagues at GE, roughly 1961 to 1964, with an AFIPS paper by Bachman and Williams in 1964) is commonly described as the first direct-access database management system. Priority claims in this area are argued over, so treat "first" as the usual description and not a settled fact. The pieces that matter:

- **Records at addresses.** Each record has a database key. Records can be fetched directly.
- **Chains.** A relationship is stored as a ring of pointers through the member records, with the owner as the anchor. Following the ring is cheap and costs time proportional to the answer.
- **CALC.** A hash on a chosen field gives a direct entry point into the data. After that you navigate.
- **Shared by many programs.** The record layouts and sets were declared once, outside any single application, which is the start of a schema.

This is the network data model: a graph of record types connected by one-to-many sets, with many-to-many built from connector records, as in Step 4 above.

### 3. CODASYL

Through the late 1960s the CODASYL Data Base Task Group worked to standardize this approach, building on IDS. Its April 1971 report defines the schema, sets with owner and member record types, a data manipulation language (STORE, FIND, GET, CONNECT, DISCONNECT, ERASE and so on), and **currency indicators**, the system's memory of the current record of the run unit and of each set. FIND NEXT only makes sense relative to the currency. That is why `implementation.py` keeps `set_currency` and `run_unit`. Commercial systems followed, including IDMS, which descends from IDS.

### 4. "The Programmer as Navigator" (1973)

The Turing lecture argues that the programmer's job had changed. In the sequential world the program passes over the data. In the database world the program moves through the data, choosing a path. Bachman used the Copernican revolution as the analogy, with data at the center and the programmer as a traveler. He also pointed out the consequences: you now need an idea of position (currency), of a map (the data structure diagram, often called a Bachman diagram), and of getting lost (dangling pointers, broken chains). The lecture is also where the term "navigational database" comes from.

### 5. The cost: navigation is path-dependent

The efficiency comes from paths that were designed in advance. A query that follows a built path is fast. A query that does not (hours over 10, as in Step 7) means a scan. Application code is also written against the physical structure: change the sets and the programs change. Edgar Codd's 1970 paper, *A Relational Model of Data for Large Shared Data Banks*, proposed the opposite: describe what you want, let the system pick the path, and keep programs independent of storage. Codd received the Turing Award in 1981. The two sides argued in public for years, and relational won commercially with SQL and System R, Oracle and DB2.

### 6. What descended from it

- **IDMS and other CODASYL systems** ran large mainframe workloads for decades.
- **Hierarchical and graph stores.** IMS used a tree. Modern graph databases (Neo4j and others) store relationships as direct links and query by traversal, which is the same instinct as Bachman's rings.
- **The data structure diagram.** Boxes with arrows from owner to member are close to what entity-relationship diagrams became.
- **OSI.** Bachman later chaired work at ISO that produced the seven-layer OSI reference model. Treat that as a pointer for further reading, not something this chapter tests.
- **Foreign keys and joins.** A foreign key in SQL is Bachman's owner pointer, stored as a value instead of an address. An index lookup followed by a join is navigation done by the system.

### 7. How `implementation.py` maps to the history

| IDS / CODASYL concept | In the code |
|---|---|
| Database key | `Record.key`, the dictionary key |
| Set (owner, members) | `SCHEMA` and the `owns` / `member_of` dictionaries |
| NEXT, PRIOR, OWNER pointers | `member_of[set]["next"/"prior"/"owner"]` |
| CALC | `calc_index` |
| FIND FIRST / NEXT / OWNER | `find_first`, `find_next`, `find_owner` |
| Currency | `run_unit`, `set_currency` |
| STORE / CONNECT / DISCONNECT / ERASE | the methods of the same names |
| Connector record | `ASSIGN`, a member of two sets |

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [The Programmer as Navigator](https://doi.org/10.1145/355611.362534) (Bachman, Turing Award lecture) | Communications of the ACM 16(11) | 1973 |
| [A General Purpose Programming System for Random Access Memories](https://doi.org/10.1145/1464052.1464114) (Bachman and Williams) | AFIPS Fall Joint Computer Conference | 1964 |
| CODASYL Data Base Task Group Report | CODASYL | 1971 |
| [A Relational Model of Data for Large Shared Data Banks](https://doi.org/10.1145/362384.362685) (Codd, the counterpoint) | Communications of the ACM 13(6) | 1970 |
| The Origin of the Integrated Data Store (IDS): The First Direct-Access DBMS (Bachman, retrospective) | IEEE Annals of the History of Computing | 2009 |

*Page numbers and some DOIs above were not checked against the ACM Digital Library. Verify them before quoting.*

# Week 08 — Charles W. Bachman (1973)

**ACM Turing Award citation:** *"For his outstanding contributions to database technology."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — the pure idea in about 45 lines: records point at each other, a set is a ring (owner, first member, ..., last member, back to owner), and you answer a question by following pointers from one record to the next.

[`implementation.py`](./implementation.py) — a small CODASYL-style network database. It has record types, sets, link records for many-to-many, currency indicators, a CALC key for the entry point, and a tiny data manipulation language (`store`, `find`, `get`). It also includes a flat file "before" so you can count the cost of each approach.

```
DML command (find first EMP within DEPT-EMP)
    -> currency lookup      which owner am I positioned on, for this set?
    -> pointer hop          follow NEXT / PRIOR / OWNER, count the hop
    -> update currency      this record is now current of run unit and of each of its sets
    -> status               OK | END-OF-SET | NOT-FOUND
```

What it supports:
- Three sets and four record types: `DEPT-EMP`, `EMP-ASSIGN`, `PROJ-ASSIGN` over `DEPT`, `EMP`, `PROJ`, `ASSIGN`
- `ASSIGN` is a link record. It is a member of two sets at once, which is how a network does many-to-many
- `store` joins the new record to whichever owner is current in each set it belongs to (automatic membership)
- `find any | first | last | next | prior | owner` plus `get`
- Currency: current of run unit, and one current record per set
- Each ring is doubly linked and circular. `check` walks every ring both ways to prove it
- `--demo` runs the same question against a flat file and against the network and prints the cost of each

```bash
python3 concept.py                          # the core idea, plain
python3 implementation.py                   # REPL, sample company preloaded
python3 implementation.py practice.dml      # run a DML script (sample is loaded first)
python3 implementation.py --test            # test suite (17 checks)
python3 implementation.py --verbose         # REPL that prints every pointer hop
python3 implementation.py --demo            # flat file vs navigation, with counts
```

`scratch.dml` is yours. It holds one question to answer: who works on Gemini?

The sample company, as rings (`show rings` prints this):

```
DEPT-EMP:    Eng(1)   -> Ann(2)    -> Bob(3)   -> Eng(1)
DEPT-EMP:    Sales(4) -> Cy(5)     -> Sales(4)
EMP-ASSIGN:  Ann(2)   -> A8(10h)   -> A9(5h)   -> Ann(2)
EMP-ASSIGN:  Bob(3)   -> A10(20h)  -> Bob(3)
EMP-ASSIGN:  Cy(5)    -> A11(8h)   -> Cy(5)
PROJ-ASSIGN: Apollo(6)-> A8(10h)   -> A10(20h) -> Apollo(6)
PROJ-ASSIGN: Gemini(7)-> A9(5h)    -> A11(8h)  -> Gemini(7)
```

Look at A8. It appears in an employee ring (Ann's) and in a project ring (Apollo's). That one record is the whole join.

Example session (`python3 implementation.py practice.dml`):

```
> find any EMP name=Ann
OK  EMP#2 name=Ann salary=50
> find first ASSIGN within EMP-ASSIGN
OK  ASSIGN#8 hours=10
> find owner within PROJ-ASSIGN
OK  PROJ#6 name=Apollo
> find next ASSIGN within EMP-ASSIGN
OK  ASSIGN#9 hours=5
> find owner within PROJ-ASSIGN
OK  PROJ#7 name=Gemini
> find next ASSIGN within EMP-ASSIGN
END-OF-SET
> stats
pointer hops: 5   CALC reads: 1
```

Before and after, from `--demo` (200 employees, 3 assignments each):

```
Question: which projects does e17 work on?
  flat file : ['p17', 'p4', 'p11']  rows read: 600
  navigation: ['p17', 'p4', 'p11']  CALC reads: 1, pointer hops: 7
```

---

## Full Worked Example

Goal: build a tiny database by hand, then answer "which projects does Ann work on, and for how many hours?" Every pointer is shown. The numbers match the code.

### 1. The shape of the data

Four kinds of records. Three sets. A set says "one owner, many members, in order".

| Set | Owner | Member |
|---|---|---|
| DEPT-EMP | DEPT | EMP |
| EMP-ASSIGN | EMP | ASSIGN |
| PROJ-ASSIGN | PROJ | ASSIGN |

Employees and projects are many-to-many (Ann works on two projects, Apollo has two people). A set can only have one owner per member. So the many-to-many is split into two one-to-many sets that share a member type, ASSIGN. Each ASSIGN record is one fact: this employee, this project, this many hours.

### 2. An empty ring

`store DEPT name=Eng` creates record #1. A new owner has an empty ring, so its NEXT and PRIOR point at itself:

```
Eng(1).next[DEPT-EMP]  = Eng(1)
Eng(1).prior[DEPT-EMP] = Eng(1)
```

An empty set is detected by "my first member is me".

### 3. Adding members with currency

`store EMP name=Ann salary=50` creates record #2. The program never says "put Ann in Eng". The database looks at the current record of set DEPT-EMP. That is Eng, because Eng was just stored. So Eng is the owner. Insert Ann at the end of the ring, just before the owner:

```
last      = Eng.prior       = Eng        (empty ring, so the owner is the "last")
Ann.next  = Eng
Ann.prior = Eng
Ann.owner = Eng
Eng.next  = Ann             (old last now points to the new member)
Eng.prior = Ann
```

The ring is `Eng -> Ann -> Eng`.

After the store, Ann is current of the run unit and current of DEPT-EMP and EMP-ASSIGN (she can be a member of the first and an owner of the second).

`store EMP name=Bob salary=40`. Current of DEPT-EMP is Ann. Ann is a member, so the owner is `Ann.owner[DEPT-EMP]`, which is Eng. One hop, and Bob lands in the same ring:

```
last      = Eng.prior       = Ann
Bob.next  = Eng,   Bob.prior = Ann,   Bob.owner = Eng
Ann.next  = Bob
Eng.prior = Bob
```

The ring is `Eng -> Ann -> Bob -> Eng`. Going backward: `Eng -> Bob -> Ann -> Eng`. Both directions list the same two people. That is what `check` verifies.

Then `store DEPT name=Sales` and `store EMP name=Cy salary=30` build `Sales -> Cy -> Sales`. After that `store PROJ name=Apollo` and `store PROJ name=Gemini` make two projects with empty rings.

### 4. Link records: one record in two rings

```
find any PROJ name=Apollo     # CALC read, current of PROJ-ASSIGN = Apollo
find any EMP name=Ann         # CALC read, current of EMP-ASSIGN = Ann
store ASSIGN hours=10
```

ASSIGN is the member of two sets, so the database needs two owners. It takes the current of EMP-ASSIGN (Ann) and the current of PROJ-ASSIGN (Apollo). Record #8 is created and inserted into both rings:

```
Ann's ring:    Ann -> A8 -> Ann
Apollo's ring: Apollo -> A8 -> Apollo
A8.owner[EMP-ASSIGN]  = Ann
A8.owner[PROJ-ASSIGN] = Apollo
```

Repeat for Ann/Gemini 5 hours (A9), Bob/Apollo 20 (A10), Cy/Gemini 8 (A11). Now Ann's ring is `Ann -> A8 -> A9 -> Ann` and Apollo's ring is `Apollo -> A8 -> A10 -> Apollo`.

### 5. The query, one hop at a time

Question: which projects does Ann work on?

| Step | Command | What the database does | Result | Hops |
|---|---|---|---|---|
| 1 | `find any EMP name=Ann` | hash lookup on the CALC key | Ann(#2). Current of EMP-ASSIGN and DEPT-EMP = Ann | 0 (1 read) |
| 2 | `find first ASSIGN within EMP-ASSIGN` | owner = Ann. Follow `Ann.next[EMP-ASSIGN]` | A8, 10 hours. Current of EMP-ASSIGN = A8, current of PROJ-ASSIGN = A8 | 1 |
| 3 | `find owner within PROJ-ASSIGN` | current of PROJ-ASSIGN is A8. Follow `A8.owner[PROJ-ASSIGN]` | Apollo. Current of PROJ-ASSIGN = Apollo | 2 |
| 4 | `find next ASSIGN within EMP-ASSIGN` | current of EMP-ASSIGN is still A8. Follow `A8.next[EMP-ASSIGN]` | A9, 5 hours | 3 |
| 5 | `find owner within PROJ-ASSIGN` | follow `A9.owner[PROJ-ASSIGN]` | Gemini | 4 |
| 6 | `find next ASSIGN within EMP-ASSIGN` | follow `A9.next[EMP-ASSIGN]`, which is Ann | the next record is the owner, so the ring has ended: `END-OF-SET` | 5 |

Total: 1 CALC read, 5 hops. Answer: Ann works on Apollo (10h) and Gemini (5h).

Step 4 is the point of currency. In step 3 we jumped to Apollo, so "where am I" for the run unit moved to Apollo. But the database keeps one current record per set, not one for the whole program. EMP-ASSIGN still remembers A8, so step 4 continues down Ann's ring and does not start from Apollo. Without per-set currency you would lose your place every time you hopped to another ring.

### 6. Failure and edge cases

**End of set.** Step 6 is the happy path ending. A walk is "do this until END-OF-SET". Running past the end is not a crash. It is a status the program is expected to check.

**Missing owner.** On an empty database, `store EMP name=Zed salary=1` is refused: "no current record for set DEPT-EMP". Nothing is created. A member cannot exist without a current owner to attach to.

**Not found.** `find any EMP name=Nobody` returns `NOT-FOUND`. The currency does not move.

**Stale currency.** Run `store ASSIGN hours=10` twice in a row without any `find`. The first store makes the new ASSIGN current of both sets. The second store reads those currents, finds the same Ann and the same Apollo through the ASSIGN's owner pointers, and makes a duplicate. The database did exactly what the program told it. This is the cost of navigation: the program carries the state and must keep it right.

**Cost as data grows.** In `--demo`, the flat file has one row per assignment. Finding e17's projects reads all 600 rows. The network version does 1 CALC read and 7 hops, because e17 has three assignments. Make it 2000 employees and the flat file reads 6000 rows. The network still does 7 hops. The work depends on how many records are linked to the one you start from, not on the size of the database.

### 7. What Codd changed

Look at what the program above had to say: start at Ann, take her first ASSIGN, hop to the project, step along. The program knows the shape of the rings. If the database designer reorders a set or adds one, programs break. A year before Bachman's lecture, Edgar Codd (1970) proposed saying only what you want (`SELECT project FROM assign WHERE emp = 'Ann'`) and letting the system find a path. That is the fight this chapter sits in the middle of.

---

## ELI5

Imagine a big pile of loose papers. Each paper says one thing, like "Ann is on the Apollo team". To find everything about Ann, you have to look at every single paper. Now imagine each paper has strings tied to other papers that are about the same thing. You pick up Ann's paper, and the string pulls you to her team's paper in one step. Charles Bachman figured out how to tie those strings inside a computer, so it can follow them instead of searching the whole pile.

---

## ELI10

In the early 1960s, a company kept its facts in huge files of records, one after another on magnetic tape. If you wanted to know who worked on a project, the computer read the tape from the start and checked every record. Tapes were slow, and files kept getting bigger. Every new question meant writing a new program that read everything again.

Charles Bachman worked at General Electric. He built a system called the Integrated Data Store, or IDS, around 1963 and 1964. The big idea was that records live on a disk and point to each other. One record holds the address of the next one. He made rings out of them. A department record points to its first employee. That employee points to the next one, and the last one points back to the department. To list a department's people, you start at the department and follow the arrows until you are back where you started. To find an employee's department, follow one arrow.

A computer program using IDS had to be a navigator, which is the name of his 1973 Turing Award lecture. It said where to go first, where to go next, and when it had arrived. Bachman said this was like Copernicus. Before him, people put the Earth at the center. Bachman wanted the data, not the program, at the center, and many programs would travel through it. His design became the CODASYL standard in 1971. Many large company databases of the 1970s ran on it, alongside IBM's IMS.

---

## CS Graduate Level

### The state of the art before IDS

Early business data processing was sequential files on tape and cards. A program read a master file and a transaction file in the same sort order and wrote a new master file. Disks (the IBM 350 RAMAC arrived in 1956) made random access possible, but each application defined its own record layout and its own file organization. There was no shared description of data. Two programs that touched the same facts each carried their own copy of the format.

### Contribution 1: the Integrated Data Store

IDS (c. 1961 to 1964, built at General Electric) is generally called one of the first database management systems. Three things were new.

**Records chained by pointers on direct-access storage.** Related records were linked into chains, and the chain was circular: owner, first, ..., last, owner. Retrieval followed the chain. A record that belonged to two chains held two sets of pointers, so the data could form a network (a general graph with typed one-to-many links), not just the tree of a hierarchical system like IBM's IMS, which appeared in the same period.

**A pointer layer under a programming interface.** Programs used verbs such as store, retrieve, modify, delete and the system managed page placement and chain maintenance. The paper by Bachman and Williams (1964) describes this as a general purpose package for random access memories. Records could be located directly by a hashed key (CALC) and then reached by chains.

**Shared data, not per-application files.** The data description sat outside the application, so several programs could use one body of data. This is a theme that reaches all the way to schema in modern systems.

```
store ASSIGN             find owner within PROJ-ASSIGN
 |  currency EMP-ASSIGN    A8 --OWNER--> Apollo
 |  currency PROJ-ASSIGN
 v
joins both rings          A8 sits in:  Ann -> A8 -> A9 -> Ann
                                       Apollo -> A8 -> A10 -> Apollo
```

### Contribution 2: data structure diagrams

Bachman (1969) drew record types as boxes and sets as arrows pointing from owner to member. A one-to-many link is a single arrow, a many-to-many link is two arrows into a link record. These Bachman diagrams are the ancestors of entity-relationship diagrams (Chen, 1976) and of today's schema pictures. They made the structure of a database visible to people who did not read code.

### Contribution 3: the CODASYL network model

The CODASYL Data Base Task Group (DBTG) report of 1971 turned IDS ideas into a standard: a schema data description language, a sub-schema for application views, and a data manipulation language embedded in COBOL. Its vocabulary is what `implementation.py` imitates:

- **Set type**: named relationship, one owner type, one member type, members ordered
- **Currency indicators**: current of run unit, current of record type, current of set type
- **FIND / GET / STORE / MODIFY / ERASE / CONNECT / DISCONNECT**
- **Insertion and retention**: automatic or manual membership, mandatory or optional
- **Status**: end-of-set was a database status value the program had to test

Commercial systems followed: IDMS, Univac DMS 1100, Honeywell IDS/II, and others.

### Contribution 4: the Turing lecture, "The Programmer as Navigator" (1973)

Bachman compared database access to navigation across a space of linked data. His historical frame was the Copernican revolution. Early systems put the computer, or the program, at the center. The new view puts the data at the center, and programmers move through it with several access paths (key, set, and so on). He argued that the programmer needs good maps (the data structure diagram) and discipline about position (currency).

### Navigation versus declarative queries

Navigation costs by path, not by data size. If you know the path, it is hard to beat: a handful of pointer reads. The costs are:

1. **Programs encode physical paths.** Change a set order or add an access path and old programs may stop working. Physical data independence was weak.
2. **State in the program.** Currency is implicit global state. The stale-currency example above is a bug class.
3. **One record at a time.** You write the loop. The optimizer cannot help because there is no query to optimize.

Codd (1970) proposed the relational model, where relations are sets of tuples and queries state a predicate. The system chooses the access path, which is the job the navigator did by hand. IBM System R (1970s) and then SQL won commercially. The 1975 ACM SIGMOD debate between Codd and Bachman is a well known record of the argument. The relational side won the standard, but the pointer idea did not go away.

### What descended from it

- **Graph databases** (Neo4j, Amazon Neptune, property graph models): nodes and typed edges, queried by traversal. A query like `MATCH (e:Emp {name:'Ann'})-[:ASSIGNED]->(p:Proj)` is the walk above in one line, with an optimizer instead of a programmer.
- **Object and document databases**: references between objects and ids between documents, with the application following them.
- **Index and storage internals**: B-tree leaves are linked lists, and a relational join often runs by following row ids or index pointers. The network is underneath even when the interface is declarative.
- **Linked data and knowledge graphs**: subject, predicate, object triples, a network model with a global namespace.
- **Entity-relationship modeling**: direct descendant of the data structure diagram.

### Lasting impact on how we build things

The point that survives is that the shape of the data, drawn and named, is a first-class design artifact. The argument about whether the program or the system chooses the path stayed alive: ORMs with lazy loading, GraphQL resolvers, and the N+1 query problem are all the navigator problem in new clothes. A loop that fetches one record at a time and hops to the next is the programmer navigating, and it is as slow or as fast as it was in 1973, depending on whether the access path was a pointer or a round trip over a network.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [A general purpose programming system for random access memories](https://doi.org/10.1145/1464052.1464114) (Bachman, Williams) | AFIPS Fall Joint Computer Conference | 1964 |
| Data structure diagrams (Bachman) | DATA BASE, ACM SIGBDP | 1969 |
| [A relational model of data for large shared data banks](https://doi.org/10.1145/362384.362685) (Codd) | Communications of the ACM | 1970 |
| CODASYL Data Base Task Group Report | CODASYL Programming Language Committee | 1971 |
| [The evolution of storage structures](https://doi.org/10.1145/361454.361472) (Bachman) | Communications of the ACM | 1972 |
| [The programmer as navigator](https://doi.org/10.1145/355611.362534) (Bachman, Turing Award lecture) | Communications of the ACM | 1973 |

*DOIs were written from memory in an environment with no network access to resolve them. Click each one once before relying on it.*

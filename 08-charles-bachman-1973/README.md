# Week 08 — Charles W. Bachman (1973)

**ACM Turing Award citation:** *"For his outstanding contributions to database technology."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — the network data model in about 60 lines: records, one "set" (an owner record and a chain of member records), and navigation in both directions — walk the owner's chain to list its members, follow a member's owner pointer to go back up.

[`implementation.py`](./implementation.py) — a full working network database built the way Bachman's Integrated Data Store (IDS) worked: declared record types and set types, records that get a database key when stored, sets implemented as real pointer chains (owner → first member, member → next member, member → owner), the CODASYL navigation verbs (`FIND FIRST` / `FIND NEXT WITHIN SET`), and a flat-file scan kept around as the "before" so you can watch it read every record while navigation touches only the ones it needs.

```
store DEPT name=Engineering     -> a record gets a database key (id)
connect WORKS_IN <dept> <emp>   -> splice the member into the owner's chain
    -> members WORKS_IN <dept>   FIND FIRST / NEXT WITHIN SET  (navigate down)
    -> owner   WORKS_IN <emp>    follow the owner pointer        (navigate up)
```

What it supports:
- Declared record types and **set types** (an owner-type → member-type relationship — a Bachman-diagram arrow)
- `store`: add a record, get back a database key
- `connect` / `disconnect`: splice a member into or out of an owner's chain
- `members`: navigate a chain with `FIND FIRST / NEXT WITHIN SET` — the "programmer as navigator" move
- `owner`: follow a member's owner pointer back up in one hop
- Many-to-many relationships via a **link record** connected into two sets at once (students ↔ courses) — the thing flat files could not do without duplicating data
- `find` / `scan`: locate a record by field value; `scan` is the flat-file "before" and reports how many records it read
- A REPL, a script loader, a 17-case test suite, and a verbose mode that prints every pointer hop

```bash
python3 concept.py                       # the core idea, plain
python3 implementation.py                # interactive REPL (small demo DB)
python3 implementation.py practice.ids   # load and run a schema/data script
python3 implementation.py --test         # test suite (17 cases)
python3 implementation.py --verbose      # REPL that prints every pointer hop
```

Example session:

```
ids> store DEPT name=Engineering
stored DEPT #1 {'name': 'Engineering'}
ids> store EMP name=Ada
stored EMP #2 {'name': 'Ada'}
ids> store EMP name=Grace
stored EMP #3 {'name': 'Grace'}
ids> connect WORKS_IN 1 2
connected #2 into WORKS_IN owner #1
ids> connect WORKS_IN 1 3
connected #3 into WORKS_IN owner #1
ids> members WORKS_IN 1
  #2 name=Ada
  #3 name=Grace
ids> owner WORKS_IN 2
  owner is #1 name=Engineering
```

To list Engineering's employees, the database did not read a single record that wasn't an Engineering employee. It followed Engineering's chain — `#1 → #2 → #3` — and stopped. That is the whole idea: the relationship is stored as links you navigate, not re-discovered by scanning.

---

## Full Worked Example

### Part 1 — a set is a chain of pointers

We want to store departments and employees, and answer "who works in Engineering?" without scanning every employee.

**Step 0 — declare the shapes.** A record type is a kind of record. A **set type** is a one-to-many relationship: one owner record type, one member record type. `WORKS_IN` says "a DEPT owns EMPs."

```
rectype DEPT name
rectype EMP  name
set WORKS_IN DEPT EMP
```

**Step 1 — store records.** Each `store` hands back a database key (an id). Nothing is related yet — these are just five records sitting in the store.

```
store DEPT name=Engineering    -> #1
store EMP  name=Ada            -> #2
store EMP  name=Grace          -> #3
store EMP  name=Alan           -> #4
```

**Step 2 — connect members into the owner's chain.** This is where the structure appears. The database keeps three pointers per set. When we connect Ada (`#2`) under Engineering (`#1`):

```
connect WORKS_IN 1 2
  first_member[WORKS_IN][#1] = #2     (Engineering's chain now starts at Ada)
  owner_of[WORKS_IN][#2]     = #1     (Ada remembers her owner)
  next_member[WORKS_IN][#2]  = None   (Ada is the last member, for now)
```

Connect Grace (`#3`) next. Engineering already has a first member, so we walk to the tail (Ada) and hang Grace off her:

```
connect WORKS_IN 1 3
  next_member[WORKS_IN][#2] = #3      (Ada -> Grace)
  owner_of[WORKS_IN][#3]    = #1
  next_member[WORKS_IN][#3] = None    (Grace is now the tail)
```

The chain is now `Engineering(#1) → Ada(#2) → Grace(#3) → None`.

**Step 3 — navigate down (`FIND FIRST / NEXT WITHIN SET`).** To list Engineering's employees, start at the owner's first-member pointer and follow `next_member` until it runs out:

```
members WORKS_IN 1
  first_member[#1] = #2      -> Ada       (hop 1)
  next_member[#2]  = #3      -> Grace     (hop 2)
  next_member[#3]  = None    -> stop
  result: Ada, Grace         (touched 2 records)
```

Two hops, two records touched. Alan (`#4`) was never looked at, because he isn't on Engineering's chain.

**Step 4 — navigate up (follow the owner pointer).** The reverse question, "who owns Grace?", is one lookup, not a search, because every member stores its owner:

```
owner WORKS_IN 3
  owner_of[WORKS_IN][#3] = #1  -> Engineering
```

### Part 2 — the "before", in numbers

Add twenty more employees in other departments (records `#5`–`#24`), none connected to Engineering. Now compare the two ways to answer "who works in Engineering?"

```
navigate:   members WORKS_IN 1     -> touches 2 records (Ada, Grace) and stops
flat scan:  scan EMP dept=Engineering -> reads all 23 EMP records, tests each one
```

Both give the right answer. The flat scan — the flat-file world before IDS — does work proportional to the whole file. Navigation does work proportional to the answer. On a file of millions of records on 1963 disk, that difference was the difference between practical and impossible. `implementation.py --test` asserts exactly this: navigation touches 3 members, the scan reads all 23 records.

### Part 3 — many-to-many, which flat files couldn't do

A department has many employees, but each employee is in one department: that's one-to-many, a single set. Students and courses are different. A student takes many courses; a course has many students. That's **many-to-many**, and a flat file can only fake it by duplicating data (list every student inside each course record, or every course inside each student record, and keep them in sync by hand).

The network model handles it with a **link record**: a third record type that sits between the two and is connected into two sets at once.

```
set STU_ENROLL STUDENT ENROLL      # a student owns her enrollment records
set CRS_ENROLL COURSE  ENROLL      # a course owns its enrollment records
```

Store Alice, Bob, CS101, MATH200, and three `ENROLL` link records:

```
#1 Alice   #2 Bob   #3 CS101   #4 MATH200
#5 ENROLL (Alice–CS101)   #6 ENROLL (Alice–MATH200)   #7 ENROLL (Bob–CS101)
```

Connect each `ENROLL` into both sets — once under its student, once under its course:

```
STU_ENROLL:  Alice(#1) -> #5 -> #6        Bob(#2) -> #7
CRS_ENROLL:  CS101(#3) -> #5 -> #7        MATH200(#4) -> #6
```

Now both questions are pure navigation. **Alice's courses:** walk her enrollments, and for each one follow its *course* owner pointer:

```
members STU_ENROLL 1  -> #5, #6
  owner CRS_ENROLL 5  -> CS101
  owner CRS_ENROLL 6  -> MATH200
Alice takes: CS101, MATH200
```

**CS101's students:** the same navigation from the other side:

```
members CRS_ENROLL 3  -> #5, #7
  owner STU_ENROLL 5  -> Alice
  owner STU_ENROLL 7  -> Bob
CS101 has: Alice, Bob
```

One `ENROLL` record, reachable from both directions, no duplicated data. This is the network model earning its name: the records form a graph, and every question is a walk through it.

### Edge case: disconnect from the middle

Disconnecting a member re-points whatever came before it. Chain `A → B → C`; disconnect `B`. `B` isn't the head, so find the member whose `next` is `B` (that's `A`) and re-point it past `B` to `C`:

```
before:  first -> A -> B -> C
disconnect B:
  next_member[A] = next_member[B] = C
after:   first -> A -> C
```

`B` the record still exists; it's just no longer on this chain. `implementation.py --test` checks the middle-disconnect and the reconnect-at-tail cases, because getting the pointer surgery right is the whole substance of maintaining a set.

---

## ELI5

Imagine a big filing cabinet. Before, if you wanted to find every kid in Mr. Green's class, you had to pull out every single card in the whole cabinet and check "is this kid in Mr. Green's class?" one by one. Slow, and easy to miss one.

Charlie Bachman had a better idea. Give Mr. Green's card a little string tied to the first kid in his class. Tie that kid's card by a string to the next kid, and that one to the next. Now to find Mr. Green's whole class you just grab his card and follow the strings. You never touch a card that isn't on the string.

And the strings go both ways. Each kid's card also has a string back to their teacher. So you can start from a kid and follow the string to find their class. The cabinet stopped being a pile you search and became a web you walk.

---

## ELI10

Charles Bachman was born in Manhattan, Kansas, in 1924. He was an engineer, not a professor — he studied mechanical engineering and spent his whole career in industry, first at Dow Chemical, then at General Electric. That makes him unusual among the people in this series: the first Turing Award winner who never earned a PhD and never worked as an academic. His prize came from a thing he built to solve a real company's real problem.

In the early 1960s, computers stored business data in flat files: one long list of records per application, usually on tape you could only read start to finish. Every program managed its own files, so the same customer's address might live in five places and disagree in three of them. And the relationships between things — which orders belong to which customer, which parts go into which product — weren't stored anywhere. A program had to rediscover them by reading whole files and matching records up, every single time.

At General Electric, Bachman built the **Integrated Data Store**, or IDS, running by 1963. It did two new things. First, it was *integrated*: one shared database that many programs used, instead of each program hoarding its own files, so the data was stored once and stayed consistent. Second, and this is the big one, it made relationships part of the data. IDS let you define a **set**: one owner record (a department) linked by a chain of pointers to its member records (that department's employees). To find a department's employees, the program followed the chain — hop, hop, hop — straight to them, instead of scanning the whole employee file. Bachman called this style "the programmer as navigator," and used it as the title of his 1973 Turing Award lecture: the database is a space of records connected by links, and you move through it one record at a time.

IDS was the first database management system, and the ideas in it were taken up by an industry group called CODASYL and turned into a standard that many companies built on through the 1970s and 80s. A newer idea, Edgar Codd's *relational* model, eventually won the argument for most everyday data, and the two men had a famous public debate about it in 1974. But Bachman's navigational idea never really died. When you use a graph database today — the kind that powers a social network's "friends of friends" or a recommendation engine — you are navigating records along stored links, one hop at a time, which is exactly the thing Bachman built in 1963.

---

## CS Graduate Level — The First DBMS, Sets, and the Programmer as Navigator

### 1. Before: flat files and the application-owned data problem

Early business computing stored data in **flat files** — sequential records, usually on magnetic tape, one file per application. Three problems followed from this, and they compounded:

- **Redundancy and inconsistency.** Each application owned its own files, so the same fact (a customer's address) was copied into many files and updated in some but not others. There was no single source of truth.
- **No stored relationships.** The connection between records — orders belonging to a customer, parts belonging to an assembly — existed only in application code. To follow a relationship, a program re-derived it by reading whole files and matching keys, an operation whose cost scaled with the file, not with the answer.
- **No data independence.** File layouts were baked into every program that read them. Change a record's physical format and you recompiled every application that touched it.

`flat_file_scan()` in `implementation.py` is this world in miniature: to find the records related to something, read every record of the type and test it. Correct, and proportional to the whole file every time.

### 2. What was new: the Integrated Data Store and the network model

At General Electric, Bachman built the **Integrated Data Store (IDS)**, operational by 1963 — by most accounts the first database management system, and the first direct-access one (it assumed random-access disk, not sequential tape). Two ideas define it.

**Integration.** One shared data store that many applications read and write, instead of each application owning private files. Data is stored once; consistency stops being a synchronization chore across duplicated files.

**The set: relationships as stored structure.** IDS represents a one-to-many relationship as a **set** — one *owner* record and an ordered chain of *member* records. Physically, IDS stored this as pointers: the owner points to its first member, each member points to the next, and each member points back to its owner. This chapter's `implementation.py` keeps exactly those three pointers per set:

```python
first_member[set][owner_id]   # owner -> its first member (or None)
next_member[set][member_id]   # member -> the next member in the chain
owner_of[set][member_id]      # member -> its owner (the reverse link)
```

The data model this produced is the **network model**: records are nodes, sets are the edges, and a database is a directed graph of records. It generalizes the strictly-tree-shaped **hierarchical model** (as in IBM's IMS, ~1966) in one crucial way: a record can be a member of many different sets, so a record can have multiple "parents." That is what makes many-to-many relationships expressible directly.

**Many-to-many via link records.** A set is one-to-many by construction. Many-to-many (students ↔ courses) is built by introducing an intersection **link record** and connecting it into two sets at once — owned by a student in one set, by a course in the other. `implementation.py`'s test suite builds exactly this and navigates it from both directions. The relational model would later express the same thing as a junction table with two foreign keys; the network model got there first, with pointer chains instead of keys.

### 3. Navigation and currency: "the programmer as navigator"

The network model came with a procedural data-manipulation language, later standardized by CODASYL, whose verbs walk the structure one record at a time:

```
FIND    locate a record (by key, or by position in a set)
GET     read the located record into program variables
FIND FIRST WITHIN SET   /  FIND NEXT WITHIN SET   -- walk a member chain
STORE   insert a new record
CONNECT / DISCONNECT    splice a record into / out of a set
MODIFY  update the current record
```

The engine tracked **currency indicators** — the "current record of the run-unit", the "current of each set type", the "current of each record type" — so that `FIND NEXT` meant "the next member after wherever I currently am in this set." Programming against it meant holding a position in the structure in your head and stepping through the graph. `members()` in `implementation.py` is the `FIND FIRST / FIND NEXT WITHIN SET` loop; `owner()` follows the reverse pointer; together they are the two fundamental navigation moves.

Bachman named this style in his 1973 Turing Award lecture, **"The Programmer as Navigator."** His metaphor was Copernican: stop thinking of the computer (the CPU) as the center with data pulled toward it, and put the *database* at the center, with the program a navigator moving through a space of records along access paths — set chains, owner pointers, indexes. It is a strikingly physical way to think about data, and it was the right one for the hardware of the time: following a pointer to the exact next record you need is cheap; scanning a file on disk to find it is not.

### 4. Standardization and notation: CODASYL and Bachman diagrams

The ideas in IDS were adopted by the **CODASYL Data Base Task Group (DBTG)** — the same standards body behind COBOL. Its reports (notably the April 1971 DBTG report) defined a network-model standard with a schema **Data Definition Language**, a subschema mechanism (an application's private view of part of the schema — an early, real form of data independence), and the COBOL-embedded navigational **Data Manipulation Language** above. Through the 1970s and 80s this "CODASYL model" was implemented by many vendors; **IDMS** (originally from B.F. Goodrich, later Cullinane/Cullinet, now CA IDMS) is the best-known descendant and still runs on mainframes today.

Bachman also gave the field its first widely used schema notation: the **data structure diagram**, described in his 1969 paper of that name. A box is a record type; an arrow from one box to another is a set (owner at the tail, member at the head). These "Bachman diagrams" were the direct ancestor of the entity-relationship diagram (Peter Chen, 1976) and, through it, essentially every schema-modeling notation since. `print_database()` in `implementation.py` prints a text version of one: each set as `owner → member → member`.

### 5. The Great Debate: navigation vs. the relational model

In 1970, Edgar F. Codd published **"A Relational Model of Data for Large Shared Data Banks,"** proposing that data be organized as *relations* (tables) and queried *declaratively* — you state what you want (a query in relational algebra/calculus), and the system figures out how to get it — with no pointers, no navigation, and full physical data independence. This is the opposite philosophy to Bachman's: where the network model asks the programmer to navigate access paths the schema exposes, the relational model hides all access paths behind a query optimizer.

The two views collided publicly at the 1974 ACM SIGFIDET (soon renamed SIGMOD) workshop in Ann Arbor, in a session titled **"Data Models: Data-Structure-Set versus Relational,"** now remembered as the *Great Debate*. Bachman's camp argued the relational model was too abstract for ordinary programmers and could not be implemented efficiently on the hardware of the day. Codd's camp argued that navigation welded programs to physical structure and that declarative querying plus an optimizer was both cleaner and, eventually, fast enough.

History decided mostly for Codd: SQL databases became the default for general-purpose data, precisely because data independence and declarative queries scaled better with application complexity than hand-coded navigation did. But the debate's framing — *should the programmer navigate access paths, or should the system hide them?* — never closed. It reopens every time a new data shape shows up.

### 6. What descended from it

- **Graph databases.** Neo4j, Amazon Neptune, and the like are the network model's direct intellectual heirs: records (nodes) joined by stored relationships (edges) that you traverse directly, one hop at a time. "Find friends-of-friends" or "follow this recommendation chain" is Bachman's `FIND NEXT WITHIN SET`, rebranded. Graph query languages (Cypher, Gremlin, and the ISO **GQL** standard finalized in 2024) are navigation made declarative — Bachman's traversal with Codd's "say what you want, not how" laid on top.
- **Foreign keys and joins.** The relational join over a foreign key is the set membership relationship re-expressed as matching values instead of pointers. The relationship Bachman made a first-class stored structure, SQL made a first-class query operation.
- **ER modeling.** Bachman diagrams → entity-relationship diagrams → every schema tool in use today.
- **The DBMS itself.** The very idea of a shared, integrated data store that outlives and is independent of any one application program — the thing every Postgres, Oracle, DynamoDB, and Spanner instance is — starts with IDS.

### 7. After databases: the OSI networking model

Bachman's second act is less famous and worth a line. In the late 1970s he chaired the ISO subcommittee that produced the **OSI seven-layer reference model** for computer networking (physical, data link, network, transport, session, presentation, application). It's the "layer 3 / layer 7" vocabulary every network engineer still uses. The through-line with his database work is the same instinct that runs through this whole series' best entries: define a small, layered set of abstractions with clean interfaces between them, so each layer can be reasoned about — and changed — without disturbing the others. The same man gave us both the first database and the mental model for how networks are stacked.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [The Programmer as Navigator](https://doi.org/10.1145/355611.362534) *(Turing Award lecture)* | Communications of the ACM | 1973 |
| [Data Structure Diagrams](https://doi.org/10.1145/1017466.1017467) | Data Base (ACM SIGBDP) | 1969 |
| CODASYL Data Base Task Group, April 1971 Report | ACM | 1971 |
| [The Origin of the Integrated Data Store (IDS): The First Direct-Access DBMS](https://doi.org/10.1109/MAHC.2009.110) *(Bachman's own retrospective)* | IEEE Annals of the History of Computing | 2009 |
| [A Relational Model of Data for Large Shared Data Banks](https://doi.org/10.1145/362384.362685) *(Codd — the counterpoint, and the model that won for general-purpose data)* | Communications of the ACM | 1970 |

---

*Previous: [Week 07 — Edsger W. Dijkstra (1972)](../07-edsger-dijkstra-1972/)*

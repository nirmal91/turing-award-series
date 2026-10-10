# Week 08 — Charles W. Bachman (1973)

**ACM Turing Award citation:** *"For his outstanding contributions to database technology."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — Bachman's idea in about 40 lines: records sit at addresses, a student points to its first enrollment, each enrollment points to the next, the last one points back home, and you answer a question by following pointers instead of searching.

[`implementation.py`](./implementation.py) — a small network database in the style of Bachman's Integrated Data Store and the CODASYL data manipulation language that grew out of it. Records have database keys. Sets are rings of pointers with one owner and many members. The database tracks currency (where you are), and the verbs are the real ones: `STORE`, `FIND ANY`, `FIND FIRST/NEXT/PRIOR/LAST WITHIN`, `FIND OWNER WITHIN`, `GET`, `CONNECT`, `DISCONNECT`, `ERASE`.

```
command text (find any student Ada)
    -> parse        split into a verb and arguments
    -> Database     follow or rewrite pointers, update currency
    -> printed result and a status (OK, END-OF-SET, NOT-FOUND)
```

What it supports:
- A schema with record types, a direct-lookup (CALC) key, and sets with an owner type and a member type
- Many-to-many data through a link record that is a member of two sets (Student and Course through Enrollment)
- Currency indicators: run unit, per record type, per set
- A `FlatFiles` class that answers the same question by scanning, so you can count the records each approach touches
- An integrity check that walks every ring forward and backward
- A REPL, a script loader, a 25-case test suite, and a verbose mode that prints every pointer change

```bash
python3 concept.py                       # the core idea, plain
python3 implementation.py                # interactive REPL (type demo for a tour)
python3 implementation.py practice.dml   # run a command script
python3 implementation.py --test         # test suite (25 cases)
python3 implementation.py --verbose      # REPL that prints every pointer change
```

Example session:

```
db> store course title=Logic
STORED  COURSE#1 title=Logic
db> store student name=Ada
STORED  STUDENT#2 name=Ada
db> find any course Logic
OK  COURSE#1 title=Logic
db> store enrollment grade=A
STORED  ENROLLMENT#3 grade=A
db> find any student Ada
OK  STUDENT#2 name=Ada
db> find first enrollment within STUDENT-ENROLLMENT
OK  ENROLLMENT#3 grade=A
db> find owner within COURSE-ENROLLMENT
OK  COURSE#1 title=Logic
db> find next enrollment within STUDENT-ENROLLMENT
END-OF-SET
```

Before and after, measured by the code (`--test` prints it): asking "which courses does student S150 take?" in a registrar with 200 students, 20 courses and 600 enrollments touches **793 records** by scanning flat files and **7 records** by navigation. With 2000 students scanning touches 7513 records and navigation still touches 7.

---

## Full Worked Example

We build a tiny registrar by hand, look at every pointer, then navigate it. All numbers come from `implementation.py`.

### 1. The schema

Three record types: STUDENT (name), COURSE (title), ENROLLMENT (grade). Two sets:

- `STUDENT-ENROLLMENT`: owner STUDENT, member ENROLLMENT
- `COURSE-ENROLLMENT`: owner COURSE, member ENROLLMENT

An enrollment belongs to one student and one course at the same time. That is a many-to-many relationship between students and courses, built from two one-to-many sets and a link record in the middle.

### 2. Storing records

Records get the next free database key as their address. Currency is the database's memory of the last record touched, and it is what makes `STORE ENROLLMENT` work, because the enrollment needs to know its owners.

```
store course title=Logic            -> COURSE#1
store course title=Databases        -> COURSE#2
store student name=Ada              -> STUDENT#3
find any course Logic               (current of COURSE-ENROLLMENT = #1)
store enrollment grade=A            -> ENROLLMENT#4
```

How did #4 pick its owners? `STORE` looks at each set where ENROLLMENT is a member and asks for the current record of that set:

- `STUDENT-ENROLLMENT`: the last record touched in this set was Ada (#3, stored just before). So the owner is #3.
- `COURSE-ENROLLMENT`: the last one touched was Logic (#1, from `find any`). So the owner is #1.

Then #4 is inserted at the end of each owner's ring. Both rings were empty (the owner points at itself), so:

```
STUDENT-ENROLLMENT ring of #3:   3.next = 4,  4.next = 3,  3.prior = 4,  4.prior = 3
COURSE-ENROLLMENT  ring of #1:   1.next = 4,  4.next = 1,  1.prior = 4,  4.prior = 1
```

### 3. The rest of the data

```
find any course Databases           (current of COURSE-ENROLLMENT = #2)
store enrollment grade=B            -> ENROLLMENT#5
store student name=Grace            -> STUDENT#6
find any course Logic               (current of COURSE-ENROLLMENT = #1)
store enrollment grade=A            -> ENROLLMENT#7
```

For #5, the student owner is still Ada. The last record touched in `STUDENT-ENROLLMENT` was #4, an enrollment, and the owner of #4 is #3. So currency can sit on a member and the owner is still known. Ada's ring grows: `3 -> 4 -> 5 -> 3`.

For #7, the last record touched in `STUDENT-ENROLLMENT` was Grace (#6), so it joins Grace's ring. The `dump` command shows the final state:

```
set STUDENT-ENROLLMENT  (owner STUDENT, member ENROLLMENT)
  STUDENT#3 name=Ada    chain [4 -> 5]
  STUDENT#6 name=Grace  chain [7]
set COURSE-ENROLLMENT  (owner COURSE, member ENROLLMENT)
  COURSE#1 title=Logic      chain [4 -> 7]
  COURSE#2 title=Databases  chain [5]
```

Enrollment #4 sits in two chains. Read it as "Ada takes Logic with a grade of A". Nothing in record #4 says "Ada" or "Logic". Its position says it.

### 4. Happy path: which courses does Ada take?

Records touched are counted as we go.

```
find any student Ada                          -> STUDENT#3         touched 1  (direct lookup, no scan)
find first enrollment within STUDENT-ENROLLMENT -> ENROLLMENT#4    touched 2  (3.next)
find owner within COURSE-ENROLLMENT           -> COURSE#1 Logic    touched 3  (4.owner in that set)
find next enrollment within STUDENT-ENROLLMENT  -> ENROLLMENT#5    touched 4  (4.next)
find owner within COURSE-ENROLLMENT           -> COURSE#2 Databases touched 5
find next enrollment within STUDENT-ENROLLMENT  -> END-OF-SET      (5.next = 3, the owner)
```

Why did the second `NEXT` continue along Ada's chain after we hopped to a course in the middle? Because currency is kept per set. `find owner within COURSE-ENROLLMENT` changed the current of `COURSE-ENROLLMENT`. The current of `STUDENT-ENROLLMENT` still points at #4. A course is not in the student set, so the hop did not disturb the walk.

The answer took 5 touches. It would take 5 touches with 6 students or 6 million, because the cost follows Ada's chain, not the size of the data.

### 5. Edge case: END-OF-SET

`5.next` is #3, which is the owner. A ring closes on its owner, so reaching the owner means there is nothing left. The database returns the status `END-OF-SET` and no record. Every navigation loop in a CODASYL program is "find first, then loop while the status is OK, find next". This is the same shape as the Python loop in `courses_by_navigation`.

### 6. Edge case: the other direction

"Which students take Logic?" is the same walk, started from the course:

```
find any course Logic
find first enrollment within COURSE-ENROLLMENT   -> ENROLLMENT#4
find owner within STUDENT-ENROLLMENT             -> STUDENT#3 Ada
find next enrollment within COURSE-ENROLLMENT    -> ENROLLMENT#7
find owner within STUDENT-ENROLLMENT             -> STUDENT#6 Grace
find next enrollment within COURSE-ENROLLMENT    -> END-OF-SET
```

Same data, same pointers, opposite question. Nothing had to be rebuilt.

### 7. Failure case: no owner

```
fresh database
store enrollment grade=A
ERROR: no current owner for set STUDENT-ENROLLMENT
```

A member record cannot exist in a set without an owner under automatic insertion. The program has to navigate to its owners first. The check happens before anything is written, so nothing half-stored is left behind.

### 8. Failure case: erasing an owner

Erasing Ada while #4 and #5 still hang off her would leave them pointing at nothing. `ERASE` refuses: `cannot erase STUDENT#3 name=Ada: it still owns members of STUDENT-ENROLLMENT`. You have to erase or disconnect the members first. Erasing a member is allowed: it unlinks itself from both rings, and `check` confirms every ring still closes.

### 9. The "before": scanning flat files

With flat files, Ada's courses means:

1. Read the student file until you find Ada.
2. Read the entire enrollment file, because nothing says where Ada's rows end.
3. For each of Ada's rows, read the course file until the title matches.

With 200 students (600 enrollments) that is 793 reads for one student. With 2000 students, 7513. Navigation was 7 reads both times. This is the gap Bachman was selling.

---

## ELI5

Imagine your toys are in one huge pile. To find all your red cars, you have to dig through the whole pile every single time. That is slow.

Now imagine every red car has a string tied to the next red car. You pick up the first one and follow the string. Car, car, car, done. You never touch the other toys.

That was Charles Bachman's idea for computers. Instead of digging through everything, the computer keeps strings between things that belong together and just follows them.

## ELI10

In the 1950s, a company kept its records on tapes and punch cards. A tape is like a very long cassette. To find one customer, the computer had to play the tape from the start, and to answer a question about orders and customers it often had to run through several tapes in order. Nobody minded much, because there was no other way to do it.

Then disk drives showed up. A disk can jump straight to any spot, the way you can skip to track 7 of a CD. Charles Bachman worked at General Electric, and he saw that this changed the question. Records did not have to be found by reading. They could be reached by address. He built a system called the Integrated Data Store, around 1963, where each record held pointers to related records. A student record pointed to the student's first class. That class pointed to the next one. The last pointed back to the student, like a circle.

It was used for big jobs like tracking orders and parts for a timber company. A program written for it did not search for things. It started at one record and walked from record to record. In his 1973 Turing Award lecture, Bachman said programmers should think of themselves as navigators sailing through a space of data. A few years later, a different idea took over most of the industry, but the pointer idea never fully went away.

## CS Graduate Level

### 1. State of the art before IDS

Business data processing in the 1950s ran on sequential files: card decks, then magnetic tape. A "database" was a collection of files, one per application, each with a record layout fixed in the program (COBOL arrived in 1959 and made layouts a declared part of the program). Relating two files meant sorting both on a shared key and merging them in one pass. This is efficient for a nightly batch over the whole file and hopeless for "show me this one customer now." Each application duplicated the data it needed, so the same customer existed in several files that drifted apart.

Random access storage (IBM's RAMAC in 1956, then disk packs in the early 1960s) removed the physical reason for sequential-only access. What was missing was software that exploited it, and a model for organizing data that was not just "a file."

### 2. What IDS added

Bachman built IDS at General Electric in the early 1960s, working with colleagues including Stanley Williams, first for GE's own manufacturing systems and then for outside customers (Weyerhaeuser, the timber company, is the one usually cited). The key ideas:

- **Records at addresses.** Every record has a database key, an address in the store. A record can hold the key of another record, which is a pointer.
- **Chains.** Related records are linked in a ring: an owner points to a first member, each member points to the next, and the last points back to the owner. A record can be on more than one chain, so one enrollment record sits on its student's chain and its course's chain. This is how IDS expressed many-to-many relationships without duplicating data.
- **Direct access by key.** Records that need a front door (a customer number, a part number) are stored at an address computed by hashing the key, so `FIND ANY` is one probe.
- **A shared, schema-defined store.** The record layouts and the chains are declared once, outside the application programs, which makes the data a shared resource and not the property of one program.

The retrieval cost is a function of the chain you walk. In the implementation, `courses_by_navigation` touches 7 records for a student with 3 courses, whether the registrar has 200 students or 2000. `FlatFiles.courses_of_student` touches 793 and 7513.

### 3. CODASYL and the network model

IDS was influential enough that the CODASYL committee, the group behind COBOL, set up the Data Base Task Group (DBTG) in the late 1960s. Its 1971 report standardized a data definition language and a data manipulation language whose concepts came largely from IDS. The vocabulary is Bachman's: **set** (owner plus ordered members), **currency indicators**, **CALC** location mode, and the verbs `FIND`, `GET`, `STORE`, `CONNECT`, `DISCONNECT`, `ERASE`. That is what `implementation.py` implements. This "network data model" was commercialized by Cullinane (later Cullinet) as IDMS, and by Honeywell, Univac and others. Bachman's data structure diagram, with an arrow from owner to member, became the standard way to draw a schema.

The model is a **graph**: a record can have several owners, and sets can form cycles of types. The competing **hierarchical** model, used by IBM's IMS (built in the 1960s for the Apollo program), allows one parent per record. Many-to-many data forces duplication in a hierarchy. In a network it takes a link record and two sets.

### 4. The navigator

Bachman's 1973 lecture, "The Programmer as Navigator," described what this does to the programmer. He compared the move to a Copernican shift: the programmer used to think of data as something brought to the program, and now thinks of the program as moving through a data space, following paths, keeping track of position (currency), and choosing a route. The risk he also named: with several access paths, the programmer must choose one, and the choice is baked into the program. Add a new path and old programs do not see it. Remove or reorder a chain and programs that walked it break.

### 5. What descended from it, and what replaced it

In 1970 Edgar Codd proposed the **relational model**: relations are sets of tuples, queried by value through a declarative language, with the system choosing the access path. It removed the "navigation burden" and with it the dependence of programs on physical structure. The Codd and Bachman camps argued in public in 1974, and the relational model won the mainstream through System R, Oracle and SQL. The code in this chapter shows the trade: a navigational program says *how*; a SQL query says *what*.

The navigational idea did not vanish:

- **Graph databases** (Neo4j and others) advertise index-free adjacency, which means each node holds direct references to its neighbors. That is Bachman's chain, with a query language on top.
- **Object databases, document references, and ORMs** that lazily follow a foreign key are all navigating from one record to related ones.
- **Linked data structures** in memory are the same idea at RAM scale.
- **IDMS** still runs on mainframes.
- Bachman also led the work that became the **OSI seven-layer reference model** for networking, which is a different field but a similar habit: name the layers and the interfaces so independent parts can work together.

Relational systems also borrowed the discipline Bachman pushed: data defined once, centrally, independent of any one program.

### 6. Why it matters today

If you have written a query that joins on a foreign key, you have written the declarative version of walking a ring. If you have tuned a join with an index, you have chosen an access path, the thing the navigator had to do by hand. Bachman made the data layer something with its own structure and its own design, as opposed to a side effect of one program's file format. That separation is the starting point for everything from SQL to graph stores.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [The Programmer as Navigator (Turing Award lecture)](https://doi.org/10.1145/355611.362534) | Communications of the ACM 16(11), 653–658 | 1973 |
| Bachman and Williams, A General Purpose Programming System for Random Access Memories | AFIPS Fall Joint Computer Conference | 1964 |
| Bachman, Software for Random Access Processing | Datamation 11(4) | 1965 |
| Bachman, Data Structure Diagrams | Data Base (ACM SIGBDP) 1(2) | 1969 |
| Bachman, The Evolution of Storage Structures | Communications of the ACM 15(7) | 1972 |
| CODASYL Data Base Task Group, April 1971 Report | ACM | 1971 |
| [Codd, A Relational Model of Data for Large Shared Data Banks](https://doi.org/10.1145/362384.362685) | Communications of the ACM 13(6), 377–387 | 1970 |
| Taylor and Frank, CODASYL Data-Base Management Systems | ACM Computing Surveys 8(1), 67–103 | 1976 |

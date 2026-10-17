# Week 08 — Charles W. Bachman (1973)

**ACM Turing Award citation:** *"For his outstanding contributions to database technology."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — Bachman's idea in about 60 lines: a customer and its orders joined in a ring of pointers, so a question is answered by following links from one record instead of reading a whole file.

[`implementation.py`](./implementation.py) — a small network database in the style of IDS and the CODASYL commands that came from it: records, sets (rings of owner and members), a record that sits in two sets at once, and the currency indicators that make `FIND NEXT` mean "from where I am now". It also keeps the "before" around: the same question answered by scanning three sequential files.

```
command line (find first cust-orders)
    -> execute()     parse the words
    -> Database      follow pointers, update currency
    -> printed record, or "end of set"
```

What it supports:
- Record types with an optional CALC key (direct access by key, like IDS's hashed access)
- Sets: an owner, many members, stored as a ring with next, prior and owner pointers
- A record that is a member of two sets at once (an `ITEM` is in its order's ring and its product's ring)
- `STORE`, `FIND` (by key, first, last, next, prior, owner), `GET`, `MODIFY`, `CONNECT`, `DISCONNECT`, `ERASE`
- Currency: the system remembers the last record you touched, for the run, for each record type and for each set
- `walk SET`: the loop a programmer would write by hand
- `compare PRODUCT`: who bought it, by file scan and by navigation, with the number of records each one touched
- A REPL, a command-file runner, a 26-case test suite, and a verbose mode that prints every pointer followed

```bash
python3 concept.py                       # the core idea, plain
python3 implementation.py                # interactive REPL
python3 implementation.py practice.dml   # run a command file
python3 implementation.py --test         # test suite (26 cases)
python3 implementation.py --verbose      # REPL that prints every pointer followed
```

Example session:

```
ids> load demo
loaded 96 records
ids> find CUSTOMER Acme
CUSTOMER #13 {city=Boston, name=Acme}
ids> find first CUST-ORDERS
ORDER #14 {no=101}
ids> find next CUST-ORDERS
ORDER #17 {no=102}
ids> find next CUST-ORDERS
end of set
ids> compare WIDGET
customers who bought WIDGET: Acme, Binx, Juno, Kilo
  file scan  : 84 records read   (all three files, every time)
  navigation : 13 records touched
```

The demo is small: 12 customers, 24 orders, 48 items. The scan reads all 84 records whatever you ask. Navigation touches 13. Make the files a million records and the scan reads a million. Navigation still touches the same 13, because it only follows links that belong to WIDGET.

The scan here is a fair "before", not a strawman. It is one pass over each file, the way a sort and merge job on tape would do it. The cost is the size of the files.

There are two files for you to write in. `scratch.dml` is empty except for `load demo`. `practice.dml` is a worked script.

---

## Full Worked Example

Question: **which customers bought a WIDGET?**

The data has four kinds of record and three sets:

```
CUSTOMER --CUST-ORDERS--> ORDER --ORDER-ITEMS--> ITEM <--PRODUCT-ITEMS-- PRODUCT
```

Read each arrow as "owns a ring of". A customer owns a ring of orders. An order owns a ring of items. A product owns a ring of items too. The `ITEM` is in two rings: its order's and its product's. That is the whole network.

### What a ring looks like

Acme (record #13) has two orders, #14 and #17. The ring for `CUST-ORDERS` owned by Acme:

```
         next            next            next
  #13 ----------> #14 ----------> #17 ----------> #13
 (Acme)         (order 101)     (order 102)       (back to Acme)

  prior pointers run the other way. Every member also stores
  owner = #13.
```

When the verbose mode builds this ring, it prints exactly that:

```
link CUST-ORDERS: #13 -> #14 -> #13 (owner #13)     the first order: owner, order, owner
link CUST-ORDERS: #14 -> #17 -> #13 (owner #13)     the second one slots in before the owner
```

An empty ring is an owner pointing at itself. "End of set" is what you get when a `next` pointer leads back to the owner.

### Happy path: walking the WIDGET sales

**Step 1: find the product.** One direct access, by key. Nothing is searched.

```
> find PRODUCT WIDGET
PRODUCT #1 {name=WIDGET, price=5}
```

Currency now says: the current record of set `PRODUCT-ITEMS` is #1.

**Step 2: first item in WIDGET's ring.** The product points at its first item.

```
> find first PRODUCT-ITEMS
ITEM #15 {qty=1}
```

Item #15 is in two sets, so it becomes current in both. Currency now: `PRODUCT-ITEMS` = #15, `ORDER-ITEMS` = #15.

**Step 3: go up to the order.** The item stores a pointer to the owner of its `ORDER-ITEMS` ring.

```
> find owner ORDER-ITEMS
ORDER #14 {no=101}
```

**Step 4: go up to the customer.**

```
> find owner CUST-ORDERS
CUSTOMER #13 {city=Boston, name=Acme}
```

Acme bought a WIDGET. Four records touched so far: the product, the item, the order, the customer.

**Step 5: resume the product ring.** The detour up to the order and the customer did not disturb the currency of `PRODUCT-ITEMS`. It is still item #15.

```
> find next PRODUCT-ITEMS
ITEM #23 {qty=2}
```

Item #23 is the next item in WIDGET's ring. Repeat steps 3 and 4:

```
> find owner ORDER-ITEMS        ORDER #21 {no=201}
> find owner CUST-ORDERS        CUSTOMER #20 {... name=Binx}
```

Binx bought a WIDGET. Then the next item, #81, goes to order 1002 and customer Juno. The one after, #89, goes to order 1102 and customer Kilo.

**Step 6: end of set.**

```
> find next PRODUCT-ITEMS
end of set
```

The `next` pointer of item #89 leads back to product #1. That is the signal that the ring is finished. Currency stays on #89.

**Count.** 1 product + 4 items + 4 orders + 4 customers = 13 records touched. Answer: Acme, Binx, Juno, Kilo.

### The same question with sequential files

Three files, linked only by key columns. No record knows where any other record is.

```
items:      48 records, each (order no, product)
orders:     24 records, each (order no, customer)
customers:  12 records
```

1. Read all 48 items. Keep the order numbers where the product is WIDGET: 101, 201, 1002, 1102.
2. Read all 24 orders. Keep the customers whose order number is in that list.
3. Read all 12 customers. Keep the ones in that list.

48 + 24 + 12 = **84 reads**, and they would be 84 reads for BOLT, or for a product nobody bought.

### Edge case: a record with no owner to join

```
> load demo
> store ORDER no=999
error: no current record for set CUST-ORDERS (FIND something in it first)
```

`STORE ORDER` does not say which customer the order belongs to. It does not need to, if currency already says. The set is `AUTOMATIC`: the new order joins the ring owned by whoever is current. With nobody current, it has nowhere to go, so the store fails and nothing changes.

Now the right way:

```
> find CUSTOMER Acme
> store ORDER no=999
stored ORDER #97 {no=999}
> find first CUST-ORDERS
ORDER #14 {no=101}
> find last CUST-ORDERS
ORDER #97 {no=999}
```

This is the part that surprises people coming from SQL. The "where" of a command is not in the command. It is in the state the previous commands left behind.

### Edge case: deleting something that owns things

```
> find CUSTOMER Acme
> erase
error: CUSTOMER #13 {city=Boston, name=Acme} still owns members of CUST-ORDERS; erase them first
```

If this were allowed, the orders would point at an owner that no longer exists.

---

## ELI5

Imagine a huge box with every toy order from a toy store, all dumped in. You want Sam's orders. You have to pick up every piece of paper in the box and read the name on it. All of them. Every time.

Bachman did something different. He tied a string from Sam's name card to Sam's first order, then from that order to Sam's next order, and from the last one back to the name card. Now you find Sam's card, pull the string, and walk along it. You only touch Sam's papers. The rest of the box can be as big as a swimming pool and it makes no difference.

---

## ELI10

Before 1960, businesses kept their records on punched cards and magnetic tape. A file was a long line of records, one after another. If a company wanted every order from one customer, a program had to read the whole order file from the start, check each record and keep the matches. Tape made it worse, because a tape can only be read in order. The cost of a question was the size of the file, not the size of the answer.

Charles Bachman worked at General Electric in the early 1960s. He built a system called the Integrated Data Store, usually called IDS, for GE's computers. The idea was to store the links between records inside the records. A customer record would point to its first order, that order would point to the next one, and the last would point back to the customer, like a necklace. Records could also sit on two necklaces at once, so an item on an order could be found from the order or from the product. Now a program could find one record and follow links, instead of reading the whole file.

That changed what a programmer does. Bachman gave the talk for his 1973 Turing Award the title "The Programmer as Navigator." The programmer is no longer sorting and merging files. The programmer moves through a space of records, one hop at a time, and the system remembers where they are. IDS became the base for a standard written by a group called CODASYL in 1969 and 1971, and it was the main way big companies stored data for about a decade.

Then it lost, mostly. In 1970 a researcher at IBM named Edgar Codd argued that programmers should not have to know the links at all. They should just say what they want and let the system find it. That is SQL. Bachman and Codd debated this in public in 1974. Codd's side won the market. Bachman's pointers did not disappear though. They are inside every graph database and every object model that follows references.

---

## CS Graduate Level — Pointers, Sets, and the Navigating Programmer

### 1. Before: sequential files and the cost of a question

**State of the art.** Business data processing in the 1950s ran on card decks and magnetic tape. A master file sat in key order. A transaction file was sorted to match, and a batch job merged the two. This is efficient for questions that match the sort order. For any other question, the cost is a full pass over the file, `O(n)` in the size of the file, however small the answer. Related records are related only by equal key values. The system has no idea that an order belongs to a customer. The program re-derives it every run.

Random access disk changed what was possible. A disk can reach a record in one seek instead of reading everything before it. But a disk by itself is just a faster tape. Someone had to decide how records on a disk should find each other.

### 2. IDS: relationships stored as pointers

**What was new.** Bachman started the work at General Electric around 1960, with the first version working in the early 1960s. IDS shipped in 1964 for the GE 235. It did three things.

*Direct access by key.* A record type could be declared CALC: the key was hashed to a page address, so one access found the record. That is `find_calc()` in `implementation.py`, with a dict standing in for the hash.

*Chains of records, called sets.* One owner record, many member records. The owner holds a pointer to the first member. Each member holds `next`, `prior` and `owner` pointers. The last member's `next` points back to the owner, so the structure is a ring and end of set is detected by arriving at the owner.

```python
last = records[owner.prior[set_name]]
last.next[set_name]   = member.dbkey      # old last -> new member
member.prior[set_name] = last.dbkey
member.next[set_name]  = owner.dbkey      # new member -> owner (ring closes)
owner.prior[set_name]  = member.dbkey     # owner's "last" pointer
member.owner[set_name] = owner.dbkey
```

Five assignments add a member to any ring in constant time. No search, no shifting of records. Removing one is the same pointer surgery in reverse.

*Members in more than one set.* A record can sit in the ring of several different sets. In the demo, an `ITEM` is in an `ORDER-ITEMS` ring and a `PRODUCT-ITEMS` ring. Two parent records, one child. A tree cannot express that, because in a tree every node has exactly one parent. IBM's IMS (1966), the other big database of the time, is hierarchical. IDS records form a general directed graph with a ring structure. This is why the model is called the **network** model.

The system could also place a member physically near its owner on disk (CODASYL later called this `LOCATION MODE IS VIA SET`), so that walking a ring touched few pages. The logical structure and the physical layout were chosen together.

### 3. Currency: state as part of the interface

The mechanism that makes the commands short is **currency**. The system keeps a record of what you touched last:

```python
self.run_unit        # the last record touched, by anything
self.current_of_type # per record type: the last CUSTOMER, the last ORDER, ...
self.current_of_set  # per set: the last record in this set, owner or member
```

The rule is in `_arrive()`: every successful `FIND` or `STORE` makes the record current for the run unit, its type, and every set it takes part in. Because an `ITEM` is in two sets, arriving at an item updates two set currencies at once.

That is why the walk in the worked example resumes cleanly. After the detour `item -> order -> customer`, `current_of_set["PRODUCT-ITEMS"]` still points at the item, because the order and the customer are not members or owners of that set. `FIND NEXT WITHIN PRODUCT-ITEMS` therefore means "the item after the one I left", with no variable in the program holding that position.

This has a cost. Every command depends on the hidden state left by the previous commands. Reading a program means simulating its currency in your head. The 1969 and 1971 CODASYL reports standardised it (the Data Base Task Group, formed to generalise ideas from IDS), and a generation of COBOL programmers lived with it.

### 4. The navigational programming model

The data manipulation language was record-at-a-time: `FIND`, `GET`, `STORE`, `MODIFY`, `ERASE`, `CONNECT`, `DISCONNECT`. A query was a loop the programmer wrote:

```
find product WIDGET
loop:
    find next within PRODUCT-ITEMS      (exit on end of set)
    find owner within ORDER-ITEMS
    find owner within CUST-ORDERS
    get
```

That is `navigate_who_bought()` in `implementation.py`. The programmer chose the **access path**: which sets to follow, in which order. The system did not optimise it. For a program that always asks the same question, that is the fastest possible plan, written by a human who knows the data. For a question nobody planned for, the programmer has to write a new traversal, and if the sets change, the traversals break.

Bachman's Turing lecture, "The Programmer as Navigator" (CACM, November 1973), argues that this is a real change in the programmer's job. He compares the shift to Copernicus moving the sun to the center. Data is no longer something that arrives in a stream that the program processes in order. It is a space the program moves through. I have only seen summaries of the lecture while building this chapter, so read it directly before quoting it.

### 5. Bachman diagrams and the schema

To design these structures Bachman drew boxes for record types and arrows from owner to member. These data structure diagrams (he published a paper on them in 1969) are the ancestor of the entity relationship diagrams that came later. The CODASYL proposal separated the **schema** (the whole database's structure) from the **subschema** (the part one program sees), which is an early form of a view. The demo's `schema` command prints the equivalent: record types with their keys, and sets with owner, member and insertion mode.

`AUTOMATIC` and `MANUAL` insertion are in the code too. In an automatic set, `STORE` connects the new member to the current owner at once. In a manual set, `CONNECT` does it later. The demo's tests exercise both.

### 6. What happened next: Codd and the relational model

In 1970 Edgar Codd at IBM published "A Relational Model of Data for Large Shared Data Banks." His objection was exactly the weakness above: programs depend on the access paths. Change the sets and every program that walked them must change. Codd proposed that the user states what rows are wanted, in terms of values, and the system chooses the path. The two sides argued in public at an ACM workshop in 1974.

The relational side won commercially. Joins replaced navigation, and query optimisers replaced the programmer as the one who picks the path. Network databases, like Cullinet's IDMS (Bachman worked at Cullinane, which became Cullinet), stayed alive in large mainframe shops for decades.

### 7. What descended from it

- **Graph databases.** Neo4j and its relatives store relationships as direct pointers between records, which they call *index-free adjacency*. Following a relationship is a pointer hop, not a join. That is Bachman's `FIND NEXT` and `FIND OWNER` with a nicer query language on top.
- **ORMs and lazy loading.** `order.customer.name` in an object-relational mapper is navigation. The well-known "N+1 query" problem is what happens when navigation is turned into one SQL query per hop, the exact cost that Bachman's pointers were built to avoid and that SQL's joins were built to remove.
- **Document and object stores.** References between documents, and object graphs in memory, are pointer structures. Garbage collectors walk them.
- **Data modeling.** Entity relationship diagrams, and UML class diagrams, draw the same boxes and arrows Bachman drew.
- **Later work.** Bachman also led work in ISO from the late 1970s that produced the seven layer OSI reference model for networks.

### 8. The thread connecting all of it

The 1973 citation is brief: *"for his outstanding contributions to database technology."* The thread under it: **put the structure of the relationships into the data, so the cost of a question depends on the answer and not on the size of the file.** Codd's answer was to hide the structure from the programmer. Bachman's was to hand it to the programmer as a map. Both are reactions to the same fact. Today we use both.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [The Programmer as Navigator](https://doi.org/10.1145/355611.362534) *(Turing Award lecture)* | Communications of the ACM, 16(11), 653–658 | 1973 |
| [The Origin of the Integrated Data Store (IDS): The First Direct-Access DBMS](https://www.semanticscholar.org/paper/The-Origin-of-the-Integrated-Data-Store-(IDS):-The-Bachman/647727d7ead89da0aec5e66b8724b6a07edcd9a0) | IEEE Annals of the History of Computing | 2009 |
| Data Structure Diagrams | Data Base (ACM SIGBDP Newsletter) | 1969 |
| CODASYL Data Base Task Group Report *(preliminary 1969, final 1971)* | CODASYL | 1971 |
| [A Relational Model of Data for Large Shared Data Banks](https://doi.org/10.1145/362384.362685) *(E. F. Codd, the other side of the argument)* | Communications of the ACM, 13(6) | 1970 |
| [Historical Reflections: How Charles Bachman Invented the DBMS, a Foundation of Our Digital World](https://turing.plymouth.edu/~zshen/Webfiles/notes/CS3600/dbmsHistoryCACM072016.pdf) *(Thomas Haigh)* | Communications of the ACM | 2016 |
| [50 Years of Queries](https://doi.org/10.1145/3649887) *(a history of query languages)* | Communications of the ACM | 2024 |
| [Oral History: Charles Bachman](https://ethw.org/Oral-History:Charles_Bachman) | Engineering and Technology History Wiki | — |

---

*Previous: [Week 07 — Edsger W. Dijkstra (1972)](../07-edsger-dijkstra-1972/)*

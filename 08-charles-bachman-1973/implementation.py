"""
Charles Bachman's Integrated Data Store (IDS), built the way he described
it: General Electric, operational by 1963, standardized industry-wide as
the CODASYL "network data model" (DBTG reports, 1969 and 1971).

BEFORE this: a "database" was one flat file per record type, read
sequentially. To answer "every order for customer 7," a program scanned
the whole order file and checked each record's customer field by hand.
Relating two files (customers and orders) meant sorting both by a shared
key and merging them, or scanning one for every record of the other.
scan_before() below does exactly this: a linear pass over an entire record
type, checking a field on every record it passes.

AFTER this: relationships are stored as pointers, not re-derived by
scanning. A "set type" declares that one record type OWNS a ring of
another: the owner points to its first member, each member points to the
next, and the last member points back to the owner, closing the ring
(a "chain" in IDS terms). Finding "every order for customer 7" means
starting at customer 7's own record and following next-pointers --
touching exactly customer 7's orders, nothing else. find_first_within() /
find_next_within() below do exactly this.

The schema here has FOUR record types and THREE set types on purpose:

    CUSTOMER --(CUSTOMER-ORDERS)--> ORDER --(ORDER-LINES)--> LINE
                                                                 ^
                                                    PART --(PART-LINES)--

LINE is a member of two different sets at once: it belongs to the order it
was ordered on, AND to the part it refers to. Walk from an ORDER and you
get every LINE on that order. Walk from a PART and you get every LINE that
ever referenced that part -- i.e. every order that ever bought it. Same
LINE record, two rings, no copy of the data made for either. That's the
detail that makes this a *network* model rather than a hierarchy: a member
record type is not owned by just one thing.

The DML verbs below (STORE, FIND, CONNECT, FIND FIRST/NEXT/OWNER WITHIN)
mirror Bachman's real IDS/CODASYL command set. The one piece of real IDS
this file keeps faithfully: "currency" -- the database always remembers
the record you last touched, of each type and of each set, and every
WITHIN command moves relative to that, not by name or address you supply.

Pipeline:
    schema (record types, set types)
        -> STORE     create a record, becomes current, auto-connects
                      into any set it's an automatic member of
        -> CONNECT   manually link a record into a set's ring
        -> FIND      the "before": scan a whole record type by field value
        -> FIND FIRST/NEXT/OWNER WITHIN   the "after": walk a ring

Run:
    python3 implementation.py               # interactive REPL
    python3 implementation.py practice.dml  # load and run a DML script
    python3 implementation.py --test        # self-test suite
    python3 implementation.py --verbose     # REPL that prints every pointer update
"""

import sys

VERBOSE = False


# -- Schema: record types and set types --------------------------------------
#
# A record type is just a list of field names. A set type declares one
# record type as OWNER and another as MEMBER -- one owner, many members,
# implemented as a ring of pointers. This is the schema a real IDS/CODASYL
# database administrator would have written out in a Data Description
# Language; here it's two Python dicts.

RECORD_TYPES = {
    "CUSTOMER": ["name", "city"],
    "ORDER": ["order_no", "amount"],
    "PART": ["part_no", "description"],
    "LINE": ["qty"],
}

SET_TYPES = {
    "CUSTOMER-ORDERS": {"owner": "CUSTOMER", "member": "ORDER"},
    "ORDER-LINES": {"owner": "ORDER", "member": "LINE"},
    "PART-LINES": {"owner": "PART", "member": "LINE"},
}


# -- Records -------------------------------------------------------------------

class Record:
    def __init__(self, dbkey, type_name, fields):
        self.dbkey = dbkey
        self.type_name = type_name
        self.fields = fields
        # For every set this record type OWNS: {"first": dbkey|None, "last": dbkey|None}
        self.owner_of = {}
        # For every set this record type is a MEMBER of: {"owner": dbkey|None, "next": dbkey|None}
        self.member_of = {}

    def describe(self):
        field_str = ", ".join("%s=%s" % (k, v) for k, v in self.fields.items())
        return "%s#%d (%s)" % (self.type_name, self.dbkey, field_str)


# -- The database ----------------------------------------------------------------

class Database:
    def __init__(self):
        self.records = {}
        self.next_key = 1
        # "Currency" -- the database's memory of where you last were.
        self.current_run_unit = None
        self.current_of_type = {}
        self.current_owner_of_set = {}
        self.current_member_of_set = {}
        for type_name in RECORD_TYPES:
            self.current_of_type[type_name] = None
        for set_name in SET_TYPES:
            self.current_owner_of_set[set_name] = None
            self.current_member_of_set[set_name] = None

    # -- STORE: create a record, make it current, auto-connect it -----------

    def store(self, type_name, fields):
        if type_name not in RECORD_TYPES:
            raise ValueError("unknown record type: %s" % type_name)
        for field_name in fields:
            if field_name not in RECORD_TYPES[type_name]:
                raise ValueError("%s has no field %s" % (type_name, field_name))

        dbkey = self.next_key
        self.next_key += 1
        record = Record(dbkey, type_name, dict(fields))

        for set_name, definition in SET_TYPES.items():
            if definition["owner"] == type_name:
                record.owner_of[set_name] = {"first": None, "last": None}
            if definition["member"] == type_name:
                record.member_of[set_name] = {"owner": None, "next": None}

        self.records[dbkey] = record
        self._make_current(record)

        if VERBOSE:
            print("  store %s" % record.describe())

        # Automatic membership: if this type is a member of some set, and a
        # current owner is already established for that set, connect now.
        # (Real CODASYL calls this "automatic" set membership -- MANUAL sets
        # need an explicit CONNECT, which this database also supports.)
        for set_name, definition in SET_TYPES.items():
            if definition["member"] == type_name:
                owner_key = self.current_owner_of_set[set_name]
                if owner_key is not None:
                    self._connect(dbkey, set_name, owner_key)

        return dbkey

    def _make_current(self, record):
        self.current_run_unit = record.dbkey
        self.current_of_type[record.type_name] = record.dbkey
        for set_name in record.owner_of:
            self.current_owner_of_set[set_name] = record.dbkey
        for set_name in record.member_of:
            self.current_member_of_set[set_name] = record.dbkey

    # -- CONNECT: link a record into a set's ring ----------------------------

    def connect(self, dbkey, set_name, owner_key=None):
        if owner_key is None:
            owner_key = self.current_owner_of_set[set_name]
        self._connect(dbkey, set_name, owner_key)

    def _connect(self, dbkey, set_name, owner_key):
        if owner_key is None:
            raise ValueError("no current owner of set %s" % set_name)
        if owner_key not in self.records:
            raise ValueError("no such owner record: #%d" % owner_key)
        record = self.records[dbkey]
        owner = self.records[owner_key]
        if set_name not in record.member_of:
            raise ValueError("%s records are not members of %s" % (record.type_name, set_name))
        if set_name not in owner.owner_of:
            raise ValueError("%s records do not own %s" % (owner.type_name, set_name))

        if owner.owner_of[set_name]["first"] is None:
            # First member ever connected: the ring is owner -> record -> owner.
            owner.owner_of[set_name]["first"] = dbkey
            owner.owner_of[set_name]["last"] = dbkey
            record.member_of[set_name]["next"] = owner_key
            if VERBOSE:
                print("  connect #%d into %s: first member, ring is #%d -> #%d -> #%d"
                      % (dbkey, set_name, owner_key, dbkey, owner_key))
        else:
            old_last_key = owner.owner_of[set_name]["last"]
            old_last = self.records[old_last_key]
            old_last.member_of[set_name]["next"] = dbkey
            record.member_of[set_name]["next"] = owner_key
            owner.owner_of[set_name]["last"] = dbkey
            if VERBOSE:
                print("  connect #%d into %s: after #%d, ring closes #%d -> #%d"
                      % (dbkey, set_name, old_last_key, dbkey, owner_key))

        record.member_of[set_name]["owner"] = owner_key
        self.current_owner_of_set[set_name] = owner_key
        self.current_member_of_set[set_name] = dbkey
        self.current_run_unit = dbkey
        self.current_of_type[record.type_name] = dbkey

    # -- FIND: the "before" -- scan a whole record type by field value ------

    def find(self, type_name, where):
        """Scan every record of type_name, in dbkey order, checking every
        field in `where`. No pointer is used -- this is the flat-file way.
        Returns (dbkey_or_None, touched) so callers can see the scan cost."""
        touched = 0
        for dbkey in sorted(self.records.keys()):
            record = self.records[dbkey]
            if record.type_name != type_name:
                continue
            touched += 1
            matched = True
            for field_name, value in where.items():
                if str(record.fields.get(field_name)) != str(value):
                    matched = False
                    break
            if matched:
                self._make_current(record)
                return dbkey, touched
        return None, touched

    # -- FIND FIRST/NEXT/OWNER WITHIN: the "after" -- walk a ring -----------

    def find_first_within(self, set_name):
        owner_key = self.current_owner_of_set[set_name]
        if owner_key is None:
            raise ValueError("no current owner of set %s" % set_name)
        owner = self.records[owner_key]
        first_key = owner.owner_of[set_name]["first"]
        if first_key is None:
            return None
        self._enter_member(first_key, set_name)
        return first_key

    def find_next_within(self, set_name):
        member_key = self.current_member_of_set[set_name]
        if member_key is None:
            raise ValueError("not positioned within %s -- use find_first_within first" % set_name)
        member = self.records[member_key]
        next_key = member.member_of[set_name]["next"]
        owner_key = self.current_owner_of_set[set_name]
        if next_key == owner_key:
            # The ring closed: back at the owner, so the set is exhausted.
            return None
        self._enter_member(next_key, set_name)
        return next_key

    def _enter_member(self, member_key, set_name):
        member = self.records[member_key]
        self.current_run_unit = member_key
        self.current_of_type[member.type_name] = member_key
        self.current_member_of_set[set_name] = member_key

    def find_owner_within(self, set_name):
        member_key = self.current_member_of_set[set_name]
        if member_key is None:
            raise ValueError("not positioned within %s" % set_name)
        member = self.records[member_key]
        owner_key = member.member_of[set_name]["owner"]
        owner = self.records[owner_key]
        self.current_run_unit = owner_key
        self.current_of_type[owner.type_name] = owner_key
        self.current_owner_of_set[set_name] = owner_key
        return owner_key

    def walk_within(self, set_name):
        """Convenience: every member of the set anchored at the current
        owner, starting fresh from first. Touches exactly len(result) records."""
        members = []
        member_key = self.find_first_within(set_name)
        while member_key is not None:
            members.append(member_key)
            member_key = self.find_next_within(set_name)
        return members

    def get(self, dbkey):
        if dbkey not in self.records:
            raise ValueError("no such record: #%d" % dbkey)
        return self.records[dbkey].describe()


# -- REPL / DML-script commands ------------------------------------------------

BANNER = """Charles Bachman's Integrated Data Store (General Electric, 1963-64).
Schema:
  CUSTOMER --(CUSTOMER-ORDERS)--> ORDER --(ORDER-LINES)--> LINE <--(PART-LINES)-- PART
Commands:
  schema                        show record types and set types
  store TYPE field=val ...      create a record (auto-connects if a member type)
  connect SET                   manually connect current record into SET
  find TYPE field=val ...       the "before": scan the whole record type
  first SET / next SET          the "after": walk a set's ring
  owner SET                     jump from current member to its owner
  walk SET                      walk the whole ring from the current owner
  get                           print the current record of run-unit
  currency                      print every currency indicator
  show                          dump every record and its pointers
  help
Ctrl-D to quit."""


def parse_fields(parts):
    fields = {}
    for part in parts:
        if "=" not in part:
            raise ValueError("expected field=value, got %r" % part)
        key, value = part.split("=", 1)
        fields[key] = value
    return fields


def do_command(line, db):
    parts = line.split()
    if len(parts) == 0:
        return
    cmd = parts[0]

    if cmd == "schema":
        print("record types:")
        for type_name, field_names in RECORD_TYPES.items():
            print("  %s: %s" % (type_name, ", ".join(field_names)))
        print("set types:")
        for set_name, definition in SET_TYPES.items():
            print("  %s: %s owns %s" % (set_name, definition["owner"], definition["member"]))

    elif cmd == "store" and len(parts) >= 2:
        type_name = parts[1]
        fields = parse_fields(parts[2:])
        dbkey = db.store(type_name, fields)
        print("stored %s" % db.get(dbkey))

    elif cmd == "connect" and len(parts) == 2:
        set_name = parts[1]
        dbkey = db.current_run_unit
        if dbkey is None:
            print("no current record")
            return
        db.connect(dbkey, set_name)
        print("connected %s into %s" % (db.get(dbkey), set_name))

    elif cmd == "find" and len(parts) >= 2:
        type_name = parts[1]
        where = parse_fields(parts[2:])
        dbkey, touched = db.find(type_name, where)
        if dbkey is None:
            print("not found (scanned %d record(s))" % touched)
        else:
            print("found %s (scanned %d record(s))" % (db.get(dbkey), touched))

    elif cmd == "first" and len(parts) == 2:
        dbkey = db.find_first_within(parts[1])
        print(db.get(dbkey) if dbkey is not None else "(set is empty)")

    elif cmd == "next" and len(parts) == 2:
        dbkey = db.find_next_within(parts[1])
        print(db.get(dbkey) if dbkey is not None else "(end of set)")

    elif cmd == "owner" and len(parts) == 2:
        dbkey = db.find_owner_within(parts[1])
        print(db.get(dbkey))

    elif cmd == "walk" and len(parts) == 2:
        members = db.walk_within(parts[1])
        if len(members) == 0:
            print("  (empty)")
        for dbkey in members:
            print("  " + db.get(dbkey))
        print("  touched %d record(s)" % len(members))

    elif cmd == "get":
        if db.current_run_unit is None:
            print("no current record")
        else:
            print(db.get(db.current_run_unit))

    elif cmd == "currency":
        print("current of run-unit: #%s" % db.current_run_unit)
        for type_name in RECORD_TYPES:
            print("  current of %s: #%s" % (type_name, db.current_of_type[type_name]))
        for set_name in SET_TYPES:
            print("  current owner of %s: #%s, current member of %s: #%s"
                  % (set_name, db.current_owner_of_set[set_name], set_name, db.current_member_of_set[set_name]))

    elif cmd == "show":
        for dbkey in sorted(db.records.keys()):
            record = db.records[dbkey]
            print("  " + record.describe())
            for set_name, pointers in record.owner_of.items():
                print("    owns %s: first=#%s last=#%s" % (set_name, pointers["first"], pointers["last"]))
            for set_name, pointers in record.member_of.items():
                print("    member of %s: owner=#%s next=#%s" % (set_name, pointers["owner"], pointers["next"]))

    elif cmd == "help":
        print(BANNER)

    else:
        print("unknown command: %s (try 'help')" % line)


def repl():
    db = Database()
    print(BANNER)
    while True:
        try:
            line = input("ids> ")
        except EOFError:
            print()
            return
        if line.strip() == "":
            continue
        try:
            do_command(line.strip(), db)
        except (ValueError, KeyError) as err:
            print("error: %s" % err)


def run_file(path):
    """Load and run a DML script: one command per line, '#' starts a
    comment. Each command is echoed before it runs, the same as typing it
    into the REPL by hand."""
    db = Database()
    with open(path) as source_file:
        lines = source_file.readlines()
    for raw_line in lines:
        line = raw_line.split("#")[0].strip()
        if line == "":
            continue
        print("ids> " + line)
        try:
            do_command(line, db)
        except (ValueError, KeyError) as err:
            print("error: %s" % err)


# -- Self-test suite -------------------------------------------------------------

def run_tests():
    passed = 0
    total = 0

    def check(description, condition):
        nonlocal passed, total
        total += 1
        mark = "PASS" if condition else "FAIL"
        if condition:
            passed += 1
        print("[%s] %s" % (mark, description))

    # 1. Storing a customer makes it current, with an empty owned ring.
    db = Database()
    c1 = db.store("CUSTOMER", {"name": "Alice", "city": "Boston"})
    check("store makes the record current", db.current_run_unit == c1)
    check("a fresh owner's ring starts empty", db.records[c1].owner_of["CUSTOMER-ORDERS"]["first"] is None)

    # 2. Storing an ORDER right after a CUSTOMER auto-connects it.
    o1 = db.store("ORDER", {"order_no": "1001", "amount": "50"})
    check("first order auto-connects as first AND last",
          db.records[c1].owner_of["CUSTOMER-ORDERS"]["first"] == o1
          and db.records[c1].owner_of["CUSTOMER-ORDERS"]["last"] == o1)
    check("the ring closes: order's next points back to the owner",
          db.records[o1].member_of["CUSTOMER-ORDERS"]["next"] == c1)

    # 3. A second order extends the ring instead of replacing it.
    o2 = db.store("ORDER", {"order_no": "1002", "amount": "75"})
    check("second order becomes the new last", db.records[c1].owner_of["CUSTOMER-ORDERS"]["last"] == o2)
    check("first order's next now points to the second order",
          db.records[o1].member_of["CUSTOMER-ORDERS"]["next"] == o2)
    check("second order's next closes the ring back to the owner",
          db.records[o2].member_of["CUSTOMER-ORDERS"]["next"] == c1)

    # 4. find_first_within / find_next_within walk the ring in order.
    db.current_owner_of_set["CUSTOMER-ORDERS"] = c1
    first = db.find_first_within("CUSTOMER-ORDERS")
    check("find_first_within returns the first order", first == o1)
    nxt = db.find_next_within("CUSTOMER-ORDERS")
    check("find_next_within returns the second order", nxt == o2)
    check("find_next_within at the last member returns None (ring closed)",
          db.find_next_within("CUSTOMER-ORDERS") is None)

    # 5. find_owner_within jumps back from a member to its owner.
    db.find_first_within("CUSTOMER-ORDERS")
    owner_key = db.find_owner_within("CUSTOMER-ORDERS")
    check("find_owner_within returns the customer", owner_key == c1)

    # 6. Two customers get independent, non-interleaved rings.
    db2 = Database()
    a = db2.store("CUSTOMER", {"name": "Alice", "city": "Boston"})
    db2.store("ORDER", {"order_no": "A1", "amount": "10"})
    db2.store("ORDER", {"order_no": "A2", "amount": "20"})
    b = db2.store("CUSTOMER", {"name": "Bob", "city": "Chicago"})
    db2.store("ORDER", {"order_no": "B1", "amount": "30"})
    db2.current_owner_of_set["CUSTOMER-ORDERS"] = a
    alice_orders = db2.walk_within("CUSTOMER-ORDERS")
    db2.current_owner_of_set["CUSTOMER-ORDERS"] = b
    bob_orders = db2.walk_within("CUSTOMER-ORDERS")
    check("Alice's ring has exactly her 2 orders", len(alice_orders) == 2)
    check("Bob's ring has exactly his 1 order, none of Alice's", len(bob_orders) == 1)

    # 7. walk (pointer-following) and find (scanning) agree on membership,
    #    but touch different numbers of records.
    db3 = Database()
    cust = db3.store("CUSTOMER", {"name": "Carol", "city": "Denver"})
    db3.store("ORDER", {"order_no": "X1", "amount": "5"})
    db3.store("ORDER", {"order_no": "X2", "amount": "6"})
    other_cust = db3.store("CUSTOMER", {"name": "Dave", "city": "Miami"})
    db3.store("ORDER", {"order_no": "Y1", "amount": "7"})
    db3.store("ORDER", {"order_no": "Y2", "amount": "8"})
    db3.store("ORDER", {"order_no": "Y3", "amount": "9"})
    db3.current_owner_of_set["CUSTOMER-ORDERS"] = cust
    carol_walk = db3.walk_within("CUSTOMER-ORDERS")
    _, scan_touched = db3.find("ORDER", {"order_no": "X2"})
    check("walking Carol's ring touches exactly her 2 orders", len(carol_walk) == 2)
    check("scanning for X2 touches every ORDER up to and including it (2, skipping the 2 CUSTOMERs)",
          scan_touched == 2)

    # 8. The network property: a LINE is a member of TWO sets at once
    #    (ORDER-LINES and PART-LINES), reachable from either owner.
    db4 = Database()
    order = db4.store("ORDER", {"order_no": "O1", "amount": "100"})
    part = db4.store("PART", {"part_no": "P1", "description": "bolt"})
    line = db4.store("LINE", {"qty": "12"})
    db4.connect(line, "ORDER-LINES", owner_key=order)
    db4.connect(line, "PART-LINES", owner_key=part)
    db4.current_owner_of_set["ORDER-LINES"] = order
    from_order = db4.walk_within("ORDER-LINES")
    db4.current_owner_of_set["PART-LINES"] = part
    from_part = db4.walk_within("PART-LINES")
    check("the same LINE record is reachable from its ORDER", from_order == [line])
    check("AND from its PART -- one record, two independent rings", from_part == [line])

    # 9. Currency after FIND: scanning and matching updates current_of_type.
    db5 = Database()
    db5.store("CUSTOMER", {"name": "Eve", "city": "Austin"})
    target, _ = db5.find("CUSTOMER", {"name": "Eve"})
    check("find sets current-of-type for the matched record", db5.current_of_type["CUSTOMER"] == target)

    # 10. find_next_within before find_first_within is an error -- you must
    #     be positioned in the set before you can move within it.
    db6 = Database()
    db6.store("CUSTOMER", {"name": "Frank", "city": "Reno"})
    threw = False
    try:
        db6.find_next_within("CUSTOMER-ORDERS")
    except ValueError:
        threw = True
    check("find_next_within with no current member raises an error", threw)

    # 11. An owner with zero members: find_first_within returns None, not
    #     an error.
    db7 = Database()
    db7.store("PART", {"part_no": "P9", "description": "washer"})
    empty = db7.find_first_within("PART-LINES")
    check("find_first_within on an empty set returns None", empty is None)

    # 12. Manual CONNECT (explicit owner_key) works even when the record
    #     was stored before its intended owner existed at all -- store the
    #     LINE FIRST, while current_owner_of_set is still None for both of
    #     its sets, so auto-connect has nothing to attach to. Only the
    #     explicit connect() calls afterward create the links.
    db8 = Database()
    orphan_line = db8.store("LINE", {"qty": "3"})
    orphan_order = db8.store("ORDER", {"order_no": "Z1", "amount": "1"})
    orphan_part = db8.store("PART", {"part_no": "P2", "description": "nut"})
    check("no owner existed yet, so store did not auto-connect the orphan line",
          db8.records[orphan_order].owner_of["ORDER-LINES"]["first"] is None)
    db8.connect(orphan_line, "ORDER-LINES", owner_key=orphan_order)
    db8.connect(orphan_line, "PART-LINES", owner_key=orphan_part)
    check("manual connect links a LINE stored before any owner existed",
          db8.records[orphan_order].owner_of["ORDER-LINES"]["first"] == orphan_line)

    print()
    print("%d/%d passed" % (passed, total))
    return passed == total


# -- Entry point --------------------------------------------------------------

def main():
    global VERBOSE
    args = sys.argv[1:]
    if "--test" in args:
        ok = run_tests()
        sys.exit(0 if ok else 1)
    if "--verbose" in args:
        VERBOSE = True
        print("(verbose mode: every store and connect prints its pointer update)\n")
    files = [a for a in args if not a.startswith("--")]
    if len(files) > 0:
        run_file(files[0])
        return
    repl()


if __name__ == "__main__":
    main()

"""
A miniature Integrated Data Store, after Charles W. Bachman (GE, 1963) and the
CODASYL Data Base Task Group network model (1969-71).

BEFORE IDS: data lived in flat files on tape or cards. To answer "which
customers bought a Widget?" a program read every record from the start and
tested each one. tape_scan_customers_of() below does exactly that and counts
the records it reads.

AFTER IDS: every record has a database key (its address). Records are linked
into SETS. A set is a ring: one owner record, then its member records, chained
by NEXT and PRIOR pointers. The last member points back to the owner. A record
can be a member of several sets at once, so the data forms a network, not a
tree. The program does not search. It navigates: find a starting record, then
follow pointers (FIND FIRST / NEXT / OWNER WITHIN set). Bachman called this the
programmer as navigator. navigate_customers_of() answers the same question by
walking the rings and counts the pointer hops.

CURRENCY: the system remembers where you are. After every successful FIND it
records the current record of the run unit, of that record type, and of every
set the record takes part in. FIND NEXT WITHIN set means "next after the current
of that set". Currency also picks the owner when you STORE a new member.

Pipeline:
    DML text (STORE / FIND / GET ...)
        -> parse()         split a line into a verb and arguments
        -> Database.*      follow or build pointers, update currency
        -> printed result  plus a status (OK, END-OF-SET, NOT-FOUND ...)

Run:
    python3 implementation.py                # interactive REPL
    python3 implementation.py file.dml       # run a DML script file
    python3 implementation.py --test         # self-test suite
    python3 implementation.py --verbose      # REPL that prints every pointer hop
"""

import sys

VERBOSE = False

# ── The schema ────────────────────────────────────────────────────────────────
#
# Record types and the key used for FIND ANY (IDS and CODASYL called this the
# CALC key: the system hashes it to find the record in one step). Then the set
# types: name, owner type, member type.

RECORD_TYPES = {
    "CUSTOMER": "name",
    "PRODUCT": "name",
    "ORDER": "no",
    "LINE": None,
}

SET_TYPES = {
    "CUST_ORDER": ("CUSTOMER", "ORDER"),
    "ORDER_LINE": ("ORDER", "LINE"),
    "PROD_LINE": ("PRODUCT", "LINE"),
}

# Bachman diagram of this schema (arrow points from owner to member):
#
#   CUSTOMER --CUST_ORDER--> ORDER --ORDER_LINE--> LINE <--PROD_LINE-- PRODUCT
#
# LINE has two owners, an ORDER and a PRODUCT. A tree cannot say that. A
# network can.

DEMO_SCRIPT = """
STORE PRODUCT name=Widget price=10
STORE PRODUCT name=Gadget price=25
STORE CUSTOMER name=Acme city=Boston
STORE ORDER no=O1
FIND ANY PRODUCT name=Widget
STORE LINE qty=2
FIND ANY PRODUCT name=Gadget
STORE LINE qty=1
FIND ANY CUSTOMER name=Acme
STORE ORDER no=O3
STORE LINE qty=3
STORE CUSTOMER name=Birch city=Austin
STORE ORDER no=O2
FIND ANY PRODUCT name=Widget
STORE LINE qty=5
STORE CUSTOMER name=Cedar city=Denver
STORE ORDER no=O4
FIND ANY PRODUCT name=Gadget
STORE LINE qty=1
"""

# Statuses, in the spirit of CODASYL's DB-STATUS codes.
OK = "OK"
END_OF_SET = "END-OF-SET"
NOT_FOUND = "NOT-FOUND"
NO_CURRENT = "NO-CURRENT"
ERROR = "ERROR"


# ── Records ───────────────────────────────────────────────────────────────────

class Record:
    def __init__(self, dbkey, rtype, fields):
        self.dbkey = dbkey
        self.rtype = rtype
        self.fields = fields
        # links[set_name] = {"next": key, "prior": key, "owner": key}
        # An owner record has a ring slot for each set it owns. An empty ring
        # is the owner pointing at itself. A member has a slot for each set
        # it belongs to, or no slot if it is not connected.
        self.links = {}


def convert(text):
    if text.lstrip("-").isdigit():
        return int(text)
    return text


def parse_fields(tokens):
    fields = {}
    for token in tokens:
        if "=" not in token:
            raise ValueError("expected field=value, got '" + token + "'")
        name, value = token.split("=", 1)
        fields[name] = convert(value)
    return fields


# ── The database ──────────────────────────────────────────────────────────────

class Database:
    def __init__(self):
        self.records = {}        # dbkey -> Record (the "disk")
        self.next_dbkey = 1
        self.calc_index = {}     # (rtype, key value) -> dbkey, the CALC lookup
        self.run_unit = None     # current of run unit
        self.cur_type = {}       # record type -> dbkey
        self.cur_set = {}        # set name -> dbkey
        self.status = OK
        self.hops = 0            # pointer follows and CALC lookups since reset

    # -- low level -----------------------------------------------------------

    def hop(self, from_key, to_key, why):
        self.hops += 1
        if VERBOSE:
            print("    hop " + str(self.hops) + ": " + str(from_key) + " -> " +
                  str(to_key) + "  (" + why + ")")

    def describe(self, record):
        parts = []
        for name in record.fields:
            parts.append(name + "=" + str(record.fields[name]))
        return record.rtype + " #" + str(record.dbkey) + "  " + " ".join(parts)

    def set_status(self, status):
        self.status = status
        return status

    def make_current(self, record):
        self.run_unit = record.dbkey
        self.cur_type[record.rtype] = record.dbkey
        for set_name in SET_TYPES:
            owner_type = SET_TYPES[set_name][0]
            member_type = SET_TYPES[set_name][1]
            if record.rtype == owner_type or record.rtype == member_type:
                self.cur_set[set_name] = record.dbkey
                if VERBOSE:
                    print("    currency: " + set_name + " -> #" + str(record.dbkey))

    def owner_of_set_position(self, set_name, dbkey):
        """The owner record of the ring that dbkey sits in."""
        record = self.records[dbkey]
        owner_type = SET_TYPES[set_name][0]
        if record.rtype == owner_type:
            return record
        return self.records[record.links[set_name]["owner"]]

    # -- ring operations -----------------------------------------------------

    def make_owner(self, record, set_name):
        record.links[set_name] = {"next": record.dbkey, "prior": record.dbkey,
                                  "owner": record.dbkey}

    def connect_last(self, member, set_name, owner):
        """Insert member just before the owner, which is the end of the ring."""
        last = self.records[owner.links[set_name]["prior"]]
        last.links[set_name]["next"] = member.dbkey
        member.links[set_name] = {"next": owner.dbkey, "prior": last.dbkey,
                                  "owner": owner.dbkey}
        owner.links[set_name]["prior"] = member.dbkey

    def disconnect(self, member, set_name):
        if set_name not in member.links:
            return
        slot = member.links[set_name]
        before = self.records[slot["prior"]]
        after = self.records[slot["next"]]
        before.links[set_name]["next"] = after.dbkey
        after.links[set_name]["prior"] = before.dbkey
        del member.links[set_name]

    def members_of(self, set_name, owner):
        """All members in ring order. For checks and display, not navigation."""
        result = []
        key = owner.links[set_name]["next"]
        while key != owner.dbkey:
            result.append(key)
            key = self.records[key].links[set_name]["next"]
        return result

    # -- DML verbs -----------------------------------------------------------

    def store(self, rtype, fields):
        if rtype not in RECORD_TYPES:
            return self.set_status(ERROR), "unknown record type " + rtype
        calc_field = RECORD_TYPES[rtype]
        if calc_field is not None:
            if calc_field not in fields:
                return self.set_status(ERROR), rtype + " needs " + calc_field
            if (rtype, fields[calc_field]) in self.calc_index:
                return self.set_status(ERROR), "duplicate " + calc_field

        # Choose the owner of each set this type belongs to by currency.
        # Check all of them before creating anything.
        owners = {}
        for set_name in SET_TYPES:
            owner_type = SET_TYPES[set_name][0]
            member_type = SET_TYPES[set_name][1]
            if member_type == rtype:
                if owner_type not in self.cur_type:
                    return self.set_status(NO_CURRENT), \
                        "no current " + owner_type + " to own it in " + set_name
                owners[set_name] = self.records[self.cur_type[owner_type]]

        record = Record(self.next_dbkey, rtype, fields)
        self.next_dbkey += 1
        self.records[record.dbkey] = record
        if calc_field is not None:
            self.calc_index[(rtype, fields[calc_field])] = record.dbkey
        for set_name in SET_TYPES:
            if SET_TYPES[set_name][0] == rtype:
                self.make_owner(record, set_name)
        for set_name in owners:
            self.connect_last(record, set_name, owners[set_name])
            if VERBOSE:
                print("    connected #" + str(record.dbkey) + " into " + set_name +
                      " under #" + str(owners[set_name].dbkey))
        self.make_current(record)
        return self.set_status(OK), "stored " + self.describe(record)

    def find_any(self, rtype, fields):
        if rtype not in RECORD_TYPES:
            return self.set_status(ERROR), "unknown record type " + rtype
        calc_field = RECORD_TYPES[rtype]
        if calc_field is None or list(fields.keys()) != [calc_field]:
            return self.set_status(ERROR), rtype + " is found by " + str(calc_field)
        key = (rtype, fields[calc_field])
        if key not in self.calc_index:
            return self.set_status(NOT_FOUND), "no such " + rtype
        dbkey = self.calc_index[key]
        self.hop(0, dbkey, "CALC " + rtype)
        self.make_current(self.records[dbkey])
        return self.set_status(OK), self.describe(self.records[dbkey])

    def find_in_set(self, direction, rtype, set_name):
        if set_name not in SET_TYPES:
            return self.set_status(ERROR), "unknown set " + set_name
        if SET_TYPES[set_name][1] != rtype:
            return self.set_status(ERROR), rtype + " is not the member type of " + set_name
        if set_name not in self.cur_set:
            return self.set_status(NO_CURRENT), "no current of set " + set_name
        here = self.cur_set[set_name]
        owner = self.owner_of_set_position(set_name, here)

        if direction == "FIRST":
            start = owner.dbkey
            step = "next"
        elif direction == "LAST":
            start = owner.dbkey
            step = "prior"
        elif direction == "NEXT":
            start = here
            step = "next"
        else:
            start = here
            step = "prior"

        target = self.records[start].links[set_name][step]
        self.hop(start, target, step.upper() + " in " + set_name)
        if target == owner.dbkey:
            return self.set_status(END_OF_SET), "end of set " + set_name
        self.make_current(self.records[target])
        return self.set_status(OK), self.describe(self.records[target])

    def find_owner(self, set_name):
        if set_name not in SET_TYPES:
            return self.set_status(ERROR), "unknown set " + set_name
        if set_name not in self.cur_set:
            return self.set_status(NO_CURRENT), "no current of set " + set_name
        here = self.cur_set[set_name]
        owner = self.owner_of_set_position(set_name, here)
        self.hop(here, owner.dbkey, "OWNER in " + set_name)
        self.make_current(owner)
        return self.set_status(OK), self.describe(owner)

    def get(self):
        if self.run_unit is None:
            return self.set_status(NO_CURRENT), "no current record"
        return self.set_status(OK), self.describe(self.records[self.run_unit])

    def modify(self, fields):
        if self.run_unit is None:
            return self.set_status(NO_CURRENT), "no current record"
        record = self.records[self.run_unit]
        calc_field = RECORD_TYPES[record.rtype]
        if calc_field in fields:
            return self.set_status(ERROR), "cannot modify the CALC key " + calc_field
        for name in fields:
            record.fields[name] = fields[name]
        return self.set_status(OK), "modified " + self.describe(record)

    def erase(self):
        if self.run_unit is None:
            return self.set_status(NO_CURRENT), "no current record"
        record = self.records[self.run_unit]
        for set_name in SET_TYPES:
            if SET_TYPES[set_name][0] == record.rtype:
                if len(self.members_of(set_name, record)) > 0:
                    return self.set_status(ERROR), "still owns members in " + set_name
        for set_name in list(record.links.keys()):
            if SET_TYPES[set_name][1] == record.rtype:
                self.disconnect(record, set_name)
        calc_field = RECORD_TYPES[record.rtype]
        if calc_field is not None:
            del self.calc_index[(record.rtype, record.fields[calc_field])]
        # Any currency pointing at the erased record is now empty.
        for name in list(self.cur_type.keys()):
            if self.cur_type[name] == record.dbkey:
                del self.cur_type[name]
        for name in list(self.cur_set.keys()):
            if self.cur_set[name] == record.dbkey:
                del self.cur_set[name]
        self.run_unit = None
        del self.records[record.dbkey]
        return self.set_status(OK), "erased #" + str(record.dbkey)

    # -- the command line ----------------------------------------------------

    def execute(self, line):
        """Run one DML line. Returns the text to print."""
        tokens = line.split()
        if len(tokens) == 0:
            return ""
        verb = tokens[0].upper()
        try:
            if verb == "STORE":
                status, text = self.store(tokens[1].upper(), parse_fields(tokens[2:]))
            elif verb == "FIND":
                status, text = self.execute_find(tokens[1:])
            elif verb == "GET":
                status, text = self.get()
            elif verb == "MODIFY":
                status, text = self.modify(parse_fields(tokens[1:]))
            elif verb == "ERASE":
                status, text = self.erase()
            else:
                return self.set_status(ERROR) + ": unknown command " + verb
        except (IndexError, ValueError) as problem:
            return self.set_status(ERROR) + ": " + str(problem)
        return status + ": " + text

    def execute_find(self, args):
        word = args[0].upper()
        if word == "ANY":
            return self.find_any(args[1].upper(), parse_fields(args[2:]))
        if word == "OWNER":
            return self.find_owner(args[2].upper())
        if word in ("FIRST", "LAST", "NEXT", "PRIOR"):
            if args[2].upper() != "WITHIN":
                return self.set_status(ERROR), "expected WITHIN"
            return self.find_in_set(word, args[1].upper(), args[3].upper())
        return self.set_status(ERROR), "unknown FIND form " + word

    # -- display -------------------------------------------------------------

    def dump(self):
        lines = []
        for dbkey in sorted(self.records.keys()):
            record = self.records[dbkey]
            lines.append(self.describe(record))
            for set_name in sorted(record.links.keys()):
                slot = record.links[set_name]
                role = "owns  " if SET_TYPES[set_name][0] == record.rtype else "member"
                lines.append("      " + role + " " + set_name + "  next=#" + str(slot["next"]) +
                             " prior=#" + str(slot["prior"]) + " owner=#" + str(slot["owner"]))
        return "\n".join(lines)

    def currency(self):
        lines = ["run unit: " + str(self.run_unit)]
        for name in sorted(self.cur_type.keys()):
            lines.append("record type " + name + ": #" + str(self.cur_type[name]))
        for name in sorted(self.cur_set.keys()):
            lines.append("set " + name + ": #" + str(self.cur_set[name]))
        return "\n".join(lines)


def schema_text():
    lines = ["CUSTOMER --CUST_ORDER--> ORDER --ORDER_LINE--> LINE <--PROD_LINE-- PRODUCT"]
    for name in RECORD_TYPES:
        lines.append("  " + name + "  CALC key: " + str(RECORD_TYPES[name]))
    for name in SET_TYPES:
        lines.append("  set " + name + ": owner " + SET_TYPES[name][0] +
                     ", member " + SET_TYPES[name][1])
    return "\n".join(lines)


# ── Before and after ──────────────────────────────────────────────────────────
#
# The same question both ways: which customers bought this product?

def flatten_to_tape(db):
    """Denormalize the database into the flat file a pre-IDS program would read."""
    rows = []
    for dbkey in sorted(db.records.keys()):
        record = db.records[dbkey]
        if record.rtype != "LINE":
            continue
        order = db.records[record.links["ORDER_LINE"]["owner"]]
        customer = db.records[order.links["CUST_ORDER"]["owner"]]
        product = db.records[record.links["PROD_LINE"]["owner"]]
        rows.append((customer.fields["name"], order.fields["no"],
                     product.fields["name"], record.fields["qty"]))
    return rows


def tape_scan_customers_of(rows, product_name):
    """BEFORE: read every record from the start, test each one."""
    names = []
    reads = 0
    for row in rows:
        reads += 1
        if row[2] == product_name:
            if row[0] not in names:
                names.append(row[0])
    return names, reads


def navigate_customers_of(db, product_name):
    """AFTER: find the product, then walk its ring and climb to the owners."""
    names = []
    db.hops = 0
    db.execute("FIND ANY PRODUCT name=" + product_name)
    if db.status != OK:
        return names, db.hops
    db.execute("FIND FIRST LINE WITHIN PROD_LINE")
    while db.status == OK:
        db.execute("FIND OWNER WITHIN ORDER_LINE")
        db.execute("FIND OWNER WITHIN CUST_ORDER")
        record = db.records[db.run_unit]
        if record.fields["name"] not in names:
            names.append(record.fields["name"])
        # PROD_LINE currency is still the line, so NEXT carries on from it.
        db.execute("FIND NEXT LINE WITHIN PROD_LINE")
    return names, db.hops


def add_filler(db, count):
    """Pile on customers who never bought a Widget, to grow the file."""
    db.execute("FIND ANY PRODUCT name=Gadget")
    for number in range(count):
        db.execute("STORE CUSTOMER name=Filler" + str(number))
        db.execute("STORE ORDER no=F" + str(number))
        db.execute("FIND ANY PRODUCT name=Gadget")
        db.execute("STORE LINE qty=1")


def compare(db, product_name):
    rows = flatten_to_tape(db)
    tape_names, reads = tape_scan_customers_of(rows, product_name)
    saved_verbose = globals()["VERBOSE"]
    globals()["VERBOSE"] = False
    nav_names, hops = navigate_customers_of(db, product_name)
    globals()["VERBOSE"] = saved_verbose
    return ("tape scan : " + str(sorted(tape_names)) + "  records read: " + str(reads) + "\n"
            "navigation: " + str(sorted(nav_names)) + "  pointer hops: " + str(hops))


# ── Running scripts and the REPL ──────────────────────────────────────────────

def run_script(db, text, echo):
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            continue
        if echo:
            print("> " + stripped)
        print(handle(db, stripped))


def handle(db, line):
    """Meta commands first, then DML."""
    word = line.split()[0].lower()
    rest = line.split()[1:]
    if word == "demo":
        saved_verbose = globals()["VERBOSE"]
        globals()["VERBOSE"] = False
        for demo_line in DEMO_SCRIPT.strip().split("\n"):
            db.execute(demo_line)
        globals()["VERBOSE"] = saved_verbose
        db.hops = 0
        return "demo database loaded (" + str(len(db.records)) + " records)"
    if word == "show":
        return db.dump()
    if word == "currency":
        return db.currency()
    if word == "schema":
        return schema_text()
    if word == "reset":
        db.__init__()
        return "database emptied"
    if word == "compare":
        return compare(db, rest[0]) if rest else "usage: compare <product>"
    if word == "filler":
        add_filler(db, int(rest[0]) if rest else 10)
        return "added filler customers (" + str(len(db.records)) + " records)"
    if word == "hops":
        return str(db.hops) + " pointer hops so far"
    if word == "help":
        return HELP
    return db.execute(line)


HELP = """DML:
  STORE <type> field=value ...        new record, auto-connected by currency
  FIND ANY <type> key=value           CALC lookup (one hop)
  FIND FIRST|LAST|NEXT|PRIOR <type> WITHIN <set>
  FIND OWNER WITHIN <set>
  GET   MODIFY field=value   ERASE
Meta:
  demo  show  currency  schema  reset  compare <product>  filler [n]  hops  help  quit"""


def repl(db):
    print("Mini IDS. Type 'demo' to load data, 'help' for commands.")
    while True:
        try:
            line = input("ids> ").strip()
        except EOFError:
            break
        if line == "":
            continue
        if line.lower() in ("quit", "exit"):
            break
        print(handle(db, line))


# ── Tests ─────────────────────────────────────────────────────────────────────

def run_tests():
    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            passed += 1
            print("  ok    " + name)
        else:
            failed += 1
            print("  FAIL  " + name)

    def fresh():
        db = Database()
        for line in DEMO_SCRIPT.strip().split("\n"):
            db.execute(line)
        return db

    db = fresh()
    check("demo loads 14 records (2 products, 3 customers, 4 orders, 5 lines)", len(db.records) == 14)

    db = fresh()
    db.execute("FIND ANY CUSTOMER name=Acme")
    check("FIND ANY finds by CALC key", db.records[db.run_unit].fields["city"] == "Boston")

    db.execute("FIND ANY CUSTOMER name=Nobody")
    check("FIND ANY of a missing key is NOT-FOUND", db.status == NOT_FOUND)

    db = fresh()
    db.execute("FIND ANY CUSTOMER name=Acme")
    db.execute("FIND FIRST ORDER WITHIN CUST_ORDER")
    check("FIND FIRST gives Acme's first order", db.records[db.run_unit].fields["no"] == "O1")
    db.execute("FIND NEXT ORDER WITHIN CUST_ORDER")
    check("FIND NEXT gives Acme's second order", db.records[db.run_unit].fields["no"] == "O3")
    db.execute("FIND NEXT ORDER WITHIN CUST_ORDER")
    check("FIND NEXT past the last member is END-OF-SET", db.status == END_OF_SET)

    db = fresh()
    db.execute("FIND ANY CUSTOMER name=Acme")
    db.execute("FIND LAST ORDER WITHIN CUST_ORDER")
    check("FIND LAST gives the newest order", db.records[db.run_unit].fields["no"] == "O3")
    db.execute("FIND PRIOR ORDER WITHIN CUST_ORDER")
    check("FIND PRIOR walks backward", db.records[db.run_unit].fields["no"] == "O1")

    db = fresh()
    db.execute("FIND ANY PRODUCT name=Gadget")
    db.execute("FIND FIRST LINE WITHIN PROD_LINE")
    db.execute("FIND OWNER WITHIN ORDER_LINE")
    db.execute("FIND OWNER WITHIN CUST_ORDER")
    check("climbing owners reaches the customer", db.records[db.run_unit].fields["name"] == "Acme")

    db = fresh()
    check("a LINE is a member of two sets at once",
          "ORDER_LINE" in db.records[5].links and "PROD_LINE" in db.records[5].links)

    db = fresh()
    names, hops = navigate_customers_of(db, "Widget")
    check("navigation finds Widget buyers", sorted(names) == ["Acme", "Birch"])
    names, reads = tape_scan_customers_of(flatten_to_tape(db), "Widget")
    check("tape scan agrees with navigation", sorted(names) == ["Acme", "Birch"])
    check("tape scan reads every row", reads == 5)

    db = fresh()
    add_filler(db, 50)
    names, reads = tape_scan_customers_of(flatten_to_tape(db), "Widget")
    names2, hops2 = navigate_customers_of(db, "Widget")
    names3, hops1 = navigate_customers_of(fresh(), "Widget")
    check("tape scan cost grows with the file", reads == 55)
    check("navigation cost does not grow with unrelated data", hops1 == hops2)

    db = Database()
    db.execute("STORE ORDER no=X")
    check("STORE with no current owner fails", db.status == NO_CURRENT and len(db.records) == 0)

    db = Database()
    db.execute("STORE CUSTOMER name=A")
    db.execute("STORE CUSTOMER name=A")
    check("duplicate CALC key is rejected", db.status == ERROR and len(db.records) == 1)

    db = fresh()
    db.execute("FIND ANY CUSTOMER name=Acme")
    db.execute("ERASE")
    check("ERASE refuses a record that still owns members", db.status == ERROR)

    db = fresh()
    db.execute("FIND ANY CUSTOMER name=Cedar")
    db.execute("FIND FIRST ORDER WITHIN CUST_ORDER")
    db.execute("FIND FIRST LINE WITHIN ORDER_LINE")
    db.execute("ERASE")
    ok_line = db.status == OK
    db.execute("FIND ANY PRODUCT name=Gadget")
    members = db.members_of("PROD_LINE", db.records[db.run_unit])
    check("ERASE removes a member from every ring", ok_line and len(members) == 2)

    db = fresh()
    db.execute("FIND ANY PRODUCT name=Widget")
    db.execute("MODIFY price=11")
    check("MODIFY changes a field", db.records[db.run_unit].fields["price"] == 11)
    db.execute("MODIFY name=Foo")
    check("MODIFY refuses the CALC key", db.status == ERROR)

    db = fresh()
    db.execute("FIND ANY PRODUCT name=Widget")
    db.execute("FIND FIRST LINE WITHIN PROD_LINE")
    check("finding a LINE makes it current of ORDER_LINE too", db.cur_set["ORDER_LINE"] == db.run_unit)

    db = Database()
    db.execute("FIND NEXT ORDER WITHIN CUST_ORDER")
    check("FIND with no currency is NO-CURRENT", db.status == NO_CURRENT)

    db = fresh()
    rings_agree = True
    for owner_key in db.records:
        record = db.records[owner_key]
        for set_name in record.links:
            if SET_TYPES[set_name][0] == record.rtype:
                forward = db.members_of(set_name, record)
                backward = []
                key = record.links[set_name]["prior"]
                while key != record.dbkey:
                    backward.append(key)
                    key = db.records[key].links[set_name]["prior"]
                backward.reverse()
                if forward != backward:
                    rings_agree = False
    check("every ring reads the same forward and backward", rings_agree)

    print()
    print(str(passed) + " passed, " + str(failed) + " failed")
    return failed == 0


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    global VERBOSE
    args = sys.argv[1:]
    if "--verbose" in args:
        VERBOSE = True
        args.remove("--verbose")
    if "--test" in args:
        sys.exit(0 if run_tests() else 1)
    db = Database()
    if len(args) > 0:
        with open(args[0]) as handle_file:
            run_script(db, handle_file.read(), True)
        return
    repl(db)


if __name__ == "__main__":
    main()

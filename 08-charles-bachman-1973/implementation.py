"""
A small network database in the style of Charles Bachman's Integrated Data
Store (IDS, c. 1963) and the CODASYL DBTG commands that grew out of it.

BEFORE IDS: business data lived in sequential files on tape or cards. A
record did not know where its related records were. To answer "which
customers bought a WIDGET?" a program read the item file, the order file and
the customer file from start to finish, matching keys as it went. The cost
was the size of the files, whatever the question. flat_files() and
scan_who_bought() below are that world.

AFTER IDS: the relationships live inside the data. Three ideas carry it.

  1. A SET is a ring of records. One owner record, many member records.
     The owner points to its first member, each member points to the next,
     and the last member points back to the owner. Each member also carries
     a pointer to its owner, and a prior pointer for walking backwards.
  2. A record can be a member of several sets at once. An ITEM sits in the
     ring of its ORDER and in the ring of its PRODUCT. That makes the data a
     network, not a tree (IBM's IMS, 1966, was a tree).
  3. CURRENCY. The system remembers the last record you touched, per set,
     per record type, and for the run as a whole. A command like
     FIND NEXT WITHIN CUST-ORDERS means "from where I am now". The program
     is a navigator moving through the data. That is the title of his
     Turing lecture, "The Programmer as Navigator" (1973).

Pipeline:
    command line (find first cust-orders)
        -> execute()     parse the words
        -> Database      follow pointers, update currency
        -> printed record, or "end of set"

Run:
    python3 implementation.py                # interactive REPL
    python3 implementation.py practice.dml   # run a command file
    python3 implementation.py --test         # self-test suite
    python3 implementation.py --verbose      # REPL that prints every pointer followed
"""

import sys

VERBOSE = False


class DBError(Exception):
    pass


class EndOfSet(DBError):
    # CODASYL reported this as a database status code, not a crash.
    pass


# ── Records ──────────────────────────────────────────────────────────────────
#
# A record is a bag of fields plus pointers. The pointers are keyed by set
# name, because one record can sit in several sets.
#
#   next[S]   the record after this one in the ring of set S
#   prior[S]  the record before this one
#   owner[S]  (members only) the owner of the ring this record is in
#
# For an owner, next[S] is the first member and prior[S] is the last member.
# An empty ring is an owner pointing at itself.

class Record:
    def __init__(self, dbkey, rtype, fields):
        self.dbkey = dbkey
        self.rtype = rtype
        self.fields = fields
        self.next = {}
        self.prior = {}
        self.owner = {}

    def describe(self):
        parts = []
        for name in sorted(self.fields.keys()):
            parts.append("%s=%s" % (name, self.fields[name]))
        return "%s #%d {%s}" % (self.rtype, self.dbkey, ", ".join(parts))


# ── The database ─────────────────────────────────────────────────────────────

class Database:
    def __init__(self, record_types, set_types):
        # record_types: type name -> calc key field name (or None)
        # set_types:    set name -> (owner type, member type, insertion mode)
        #               insertion is "AUTOMATIC" or "MANUAL"
        self.record_types = record_types
        self.set_types = set_types
        self.records = {}
        self.next_dbkey = 1
        self.calc_index = {}        # (type, key value) -> dbkey, like IDS's CALC hashing

        self.run_unit = None        # currency of the run unit: the last record touched
        self.current_of_type = {}   # record type -> dbkey
        self.current_of_set = {}    # set name -> dbkey (an owner or a member)
        self.touches = 0            # records arrived at by FIND, to compare with file scans

    def _log(self, message):
        if VERBOSE:
            print("    . " + message)

    # -- currency -------------------------------------------------------------

    def _arrive(self, dbkey):
        # Every successful FIND or STORE lands here. This is the whole of the
        # currency rule: the record becomes current for the run unit, for its
        # type, and for every set it takes part in, as owner or as member.
        rec = self.records[dbkey]
        self.touches = self.touches + 1
        self.run_unit = dbkey
        self.current_of_type[rec.rtype] = dbkey
        updated = []
        for set_name in sorted(self.set_types.keys()):
            owner_type = self.set_types[set_name][0]
            member_type = self.set_types[set_name][1]
            # A member only counts as "in" the set if it is connected to a
            # ring. A MANUAL member not yet connected leaves the currency
            # on the owner, so CONNECT knows which ring to join.
            in_set = rec.rtype == owner_type
            if rec.rtype == member_type and set_name in rec.owner:
                in_set = True
            if in_set:
                self.current_of_set[set_name] = dbkey
                updated.append(set_name)
        self._log("currency: run unit = #%d, type %s = #%d, sets %s = #%d"
                  % (dbkey, rec.rtype, dbkey, updated, dbkey))
        return rec

    def _need_current_of_set(self, set_name):
        if set_name not in self.set_types:
            raise DBError("no such set: %s" % set_name)
        if set_name not in self.current_of_set:
            raise DBError("no current record for set %s (FIND something in it first)" % set_name)
        return self.records[self.current_of_set[set_name]]

    def _owner_key(self, set_name, rec):
        owner_type = self.set_types[set_name][0]
        member_type = self.set_types[set_name][1]
        if rec.rtype == owner_type:
            return rec.dbkey
        if rec.rtype == member_type:
            if set_name not in rec.owner:
                raise DBError("%s is not connected to any %s" % (rec.describe(), set_name))
            return rec.owner[set_name]
        raise DBError("%s has nothing to do with set %s" % (rec.rtype, set_name))

    # -- ring surgery ---------------------------------------------------------

    def _link_last(self, set_name, owner, member):
        last = self.records[owner.prior[set_name]]
        last.next[set_name] = member.dbkey
        member.prior[set_name] = last.dbkey
        member.next[set_name] = owner.dbkey
        owner.prior[set_name] = member.dbkey
        member.owner[set_name] = owner.dbkey
        self._log("link %s: #%d -> #%d -> #%d (owner #%d)"
                  % (set_name, last.dbkey, member.dbkey, owner.dbkey, owner.dbkey))

    def _unlink(self, set_name, member):
        before = self.records[member.prior[set_name]]
        after = self.records[member.next[set_name]]
        before.next[set_name] = after.dbkey
        after.prior[set_name] = before.dbkey
        del member.next[set_name]
        del member.prior[set_name]
        del member.owner[set_name]
        self._log("unlink %s: #%d now points straight to #%d"
                  % (set_name, before.dbkey, after.dbkey))

    # -- STORE, FIND, GET -----------------------------------------------------

    def store(self, rtype, fields):
        if rtype not in self.record_types:
            raise DBError("no such record type: %s" % rtype)
        calc_field = self.record_types[rtype]
        if calc_field is not None:
            if calc_field not in fields:
                raise DBError("%s needs the key field '%s'" % (rtype, calc_field))
            if (rtype, fields[calc_field]) in self.calc_index:
                raise DBError("duplicate %s key: %s" % (rtype, fields[calc_field]))

        # Find the owner for every AUTOMATIC set this type is a member of,
        # before changing anything, so a failure leaves the database untouched.
        owners = {}
        for set_name in sorted(self.set_types.keys()):
            owner_type, member_type, insertion = self.set_types[set_name]
            if member_type == rtype and insertion == "AUTOMATIC":
                cur = self._need_current_of_set(set_name)
                owners[set_name] = self._owner_key(set_name, cur)

        rec = Record(self.next_dbkey, rtype, dict(fields))
        self.next_dbkey = self.next_dbkey + 1
        self.records[rec.dbkey] = rec
        if calc_field is not None:
            self.calc_index[(rtype, fields[calc_field])] = rec.dbkey

        for set_name in sorted(self.set_types.keys()):
            if self.set_types[set_name][0] == rtype:
                rec.next[set_name] = rec.dbkey      # an empty ring points at itself
                rec.prior[set_name] = rec.dbkey
        for set_name in sorted(owners.keys()):
            self._link_last(set_name, self.records[owners[set_name]], rec)

        self._arrive(rec.dbkey)
        return rec

    def find_calc(self, rtype, key):
        # IDS hashed the key to a page: one direct access, no search.
        if (rtype, key) not in self.calc_index:
            raise DBError("no %s with key %s" % (rtype, key))
        dbkey = self.calc_index[(rtype, key)]
        self._log("calc: %s %s -> #%d" % (rtype, key, dbkey))
        return self._arrive(dbkey)

    def _first_or_last(self, set_name, which):
        cur = self._need_current_of_set(set_name)
        owner = self.records[self._owner_key(set_name, cur)]
        if which == "first":
            target = owner.next[set_name]
        else:
            target = owner.prior[set_name]
        if target == owner.dbkey:
            raise EndOfSet("set %s of #%d is empty" % (set_name, owner.dbkey))
        self._log("%s in %s: owner #%d -> #%d" % (which, set_name, owner.dbkey, target))
        return self._arrive(target)

    def find_first(self, set_name):
        return self._first_or_last(set_name, "first")

    def find_last(self, set_name):
        return self._first_or_last(set_name, "last")

    def _step(self, set_name, direction):
        cur = self._need_current_of_set(set_name)
        owner_key = self._owner_key(set_name, cur)
        if direction == "next":
            target = cur.next[set_name]
        else:
            target = cur.prior[set_name]
        if target == owner_key:
            # Back at the owner means we went all the way round the ring.
            self._log("%s %s from #%d reaches owner #%d: end of set"
                      % (direction, set_name, cur.dbkey, owner_key))
            raise EndOfSet("end of set %s" % set_name)
        self._log("%s in %s: #%d -> #%d" % (direction, set_name, cur.dbkey, target))
        return self._arrive(target)

    def find_next(self, set_name):
        return self._step(set_name, "next")

    def find_prior(self, set_name):
        return self._step(set_name, "prior")

    def find_owner(self, set_name):
        cur = self._need_current_of_set(set_name)
        owner_key = self._owner_key(set_name, cur)
        self._log("owner in %s: #%d -> #%d" % (set_name, cur.dbkey, owner_key))
        return self._arrive(owner_key)

    def get(self):
        if self.run_unit is None:
            raise DBError("no current record of the run unit")
        return self.records[self.run_unit]

    # -- MODIFY, CONNECT, DISCONNECT, ERASE -----------------------------------

    def modify(self, updates):
        rec = self.get()
        calc_field = self.record_types[rec.rtype]
        for name in updates:
            if name == calc_field:
                raise DBError("cannot change the key field '%s'" % name)
        for name in updates:
            rec.fields[name] = updates[name]
        return rec

    def connect(self, set_name):
        rec = self.get()
        owner_type, member_type, insertion = self.set_types[set_name]
        if rec.rtype != member_type:
            raise DBError("%s cannot be a member of %s" % (rec.rtype, set_name))
        if set_name in rec.owner:
            raise DBError("already connected to %s" % set_name)
        cur = self._need_current_of_set(set_name)
        owner = self.records[self._owner_key(set_name, cur)]
        self._link_last(set_name, owner, rec)
        return rec

    def disconnect(self, set_name):
        rec = self.get()
        if set_name not in rec.owner:
            raise DBError("not connected to %s" % set_name)
        owner_key = rec.owner[set_name]
        self._unlink(set_name, rec)
        if self.current_of_set.get(set_name) == rec.dbkey:
            self.current_of_set[set_name] = owner_key
        return rec

    def erase(self):
        rec = self.get()
        for set_name in rec.next:
            if set_name not in rec.owner and rec.next[set_name] != rec.dbkey:
                raise DBError("%s still owns members of %s; erase them first"
                              % (rec.describe(), set_name))
        for set_name in sorted(rec.owner.keys()):
            owner_key = rec.owner[set_name]
            self._unlink(set_name, rec)
            if self.current_of_set.get(set_name) == rec.dbkey:
                self.current_of_set[set_name] = owner_key
        for set_name in list(self.current_of_set.keys()):
            if self.current_of_set[set_name] == rec.dbkey:
                del self.current_of_set[set_name]
        calc_field = self.record_types[rec.rtype]
        if calc_field is not None:
            del self.calc_index[(rec.rtype, rec.fields[calc_field])]
        if self.current_of_type.get(rec.rtype) == rec.dbkey:
            del self.current_of_type[rec.rtype]
        self.run_unit = None
        del self.records[rec.dbkey]
        return rec

    # -- inspection -----------------------------------------------------------

    def members_forward(self, set_name, owner_key):
        result = []
        owner = self.records[owner_key]
        key = owner.next[set_name]
        while key != owner_key:
            result.append(key)
            key = self.records[key].next[set_name]
        return result

    def members_backward(self, set_name, owner_key):
        result = []
        owner = self.records[owner_key]
        key = owner.prior[set_name]
        while key != owner_key:
            result.append(key)
            key = self.records[key].prior[set_name]
        return result


def check_rings(db):
    # Every ring must read the same forwards and backwards, and every member
    # must point at the owner of the ring it is in.
    for set_name in sorted(db.set_types.keys()):
        owner_type = db.set_types[set_name][0]
        for key in sorted(db.records.keys()):
            rec = db.records[key]
            if rec.rtype != owner_type:
                continue
            forward = db.members_forward(set_name, key)
            backward = db.members_backward(set_name, key)
            backward.reverse()
            if forward != backward:
                return False
            for member_key in forward:
                if db.records[member_key].owner[set_name] != key:
                    return False
    return True


# ── The demo schema and data ─────────────────────────────────────────────────
#
#   CUSTOMER --CUST-ORDERS--> ORDER --ORDER-ITEMS--> ITEM <--PRODUCT-ITEMS-- PRODUCT
#
# ITEM is a member of two sets. Follow ORDER-ITEMS upward and you reach the
# order. Follow PRODUCT-ITEMS upward and you reach the product. That crossing
# is what a tree cannot express.

DEMO_RECORD_TYPES = {"CUSTOMER": "name", "ORDER": "no", "PRODUCT": "name", "ITEM": None}
DEMO_SET_TYPES = {
    "CUST-ORDERS": ("CUSTOMER", "ORDER", "AUTOMATIC"),
    "ORDER-ITEMS": ("ORDER", "ITEM", "AUTOMATIC"),
    "PRODUCT-ITEMS": ("PRODUCT", "ITEM", "AUTOMATIC"),
}

DEMO_CUSTOMERS = ["Acme", "Binx", "Corvo", "Delta", "Ember", "Flux",
                  "Gadu", "Helix", "Ionic", "Juno", "Kilo", "Lumen"]
DEMO_CITIES = ["Boston", "Austin", "Denver", "Seattle"]
DEMO_PRODUCTS = [("WIDGET", 5), ("GADGET", 12), ("SPROCKET", 3), ("GEAR", 8),
                 ("BOLT", 1), ("CABLE", 4), ("NUT", 1), ("WASHER", 1),
                 ("VALVE", 20), ("PUMP", 45), ("SPRING", 2), ("LEVER", 6)]


def new_demo_db():
    return Database(dict(DEMO_RECORD_TYPES), dict(DEMO_SET_TYPES))


def load_demo(db):
    global VERBOSE
    was_verbose = VERBOSE
    VERBOSE = False         # 90 stores would drown the output
    for product_name, price in DEMO_PRODUCTS:
        db.store("PRODUCT", {"name": product_name, "price": price})
    for ci in range(len(DEMO_CUSTOMERS)):
        db.store("CUSTOMER", {"name": DEMO_CUSTOMERS[ci], "city": DEMO_CITIES[ci % 4]})
        for o in range(2):
            order_no = 100 * (ci + 1) + o + 1
            db.store("ORDER", {"no": order_no})
            for k in range(2):
                product_name = DEMO_PRODUCTS[(ci * 5 + o * 3 + k * 7) % 12][0]
                # STORE ITEM joins the current ORDER-ITEMS owner (the order
                # just stored) and the current PRODUCT-ITEMS owner (the
                # product just found). Currency does the wiring.
                db.find_calc("PRODUCT", product_name)
                db.store("ITEM", {"qty": 1 + k})
    # Leave currency empty-ish so a fresh session starts clean.
    db.run_unit = None
    db.current_of_type = {}
    db.current_of_set = {}
    db.touches = 0
    VERBOSE = was_verbose


# ── Before and after: "which customers bought this product?" ─────────────────

def flat_files(db):
    # What a tape-era program had: three files, linked only by key columns.
    customers = []
    orders = []
    items = []
    for key in sorted(db.records.keys()):
        rec = db.records[key]
        if rec.rtype == "CUSTOMER":
            customers.append({"name": rec.fields["name"]})
        elif rec.rtype == "ORDER":
            owner = db.records[rec.owner["CUST-ORDERS"]]
            orders.append({"no": rec.fields["no"], "customer": owner.fields["name"]})
        elif rec.rtype == "ITEM":
            order = db.records[rec.owner["ORDER-ITEMS"]]
            product = db.records[rec.owner["PRODUCT-ITEMS"]]
            items.append({"order": order.fields["no"], "product": product.fields["name"]})
    return {"customers": customers, "orders": orders, "items": items}


def scan_who_bought(flat, product_name):
    # One pass over each file, the way a sort-merge job would. Every record
    # of every file is read whatever the question is.
    reads = 0
    order_numbers = set()
    for item in flat["items"]:
        reads = reads + 1
        if item["product"] == product_name:
            order_numbers.add(item["order"])
    customer_names = set()
    for order in flat["orders"]:
        reads = reads + 1
        if order["no"] in order_numbers:
            customer_names.add(order["customer"])
    result = []
    for customer in flat["customers"]:
        reads = reads + 1
        if customer["name"] in customer_names:
            result.append(customer["name"])
    return sorted(result), reads


def navigate_who_bought(db, product_name):
    # Find the product once, then walk. The only searching is the one CALC.
    db.touches = 0
    db.find_calc("PRODUCT", product_name)
    result = []
    try:
        db.find_first("PRODUCT-ITEMS")
        while True:
            db.find_owner("ORDER-ITEMS")      # item -> its order
            db.find_owner("CUST-ORDERS")      # order -> its customer
            name = db.get().fields["name"]
            if name not in result:
                result.append(name)
            # PRODUCT-ITEMS currency is still the item we came from, so this
            # picks up the walk exactly where it left off.
            db.find_next("PRODUCT-ITEMS")
    except EndOfSet:
        pass
    return sorted(result), db.touches


# ── Command interpreter ──────────────────────────────────────────────────────

HELP = """commands (case of record and set names does not matter):
  load demo                       customers, orders, items, products
  schema                          show record types and sets
  store TYPE field=value ...      e.g. store ORDER no=999
  find TYPE KEY                   direct access by key, e.g. find CUSTOMER Acme
  find first|last|next|prior SET  move within the current ring of SET
  find owner SET                  jump to the owner of the current ring
  get                             show the current record of the run unit
  modify field=value ...          change fields of the current record
  connect SET / disconnect SET    join or leave a ring
  erase                           delete the current record (it must own nothing)
  walk SET                        FIND FIRST then FIND NEXT until end of set
  currency                        show what is current, and where
  compare PRODUCT                 who bought it: file scan vs navigation
  help / quit"""


def parse_value(text):
    if text.lstrip("-").isdigit():
        return int(text)
    return text


def parse_fields(words):
    fields = {}
    for word in words:
        if "=" not in word:
            raise DBError("expected field=value, got '%s'" % word)
        name, value = word.split("=", 1)
        fields[name] = parse_value(value)
    return fields


def show_currency(db):
    lines = []
    if db.run_unit is None:
        lines.append("  run unit: (none)")
    else:
        lines.append("  run unit: " + db.records[db.run_unit].describe())
    for rtype in sorted(db.current_of_type.keys()):
        lines.append("  type %-9s #%d" % (rtype, db.current_of_type[rtype]))
    for set_name in sorted(db.current_of_set.keys()):
        key = db.current_of_set[set_name]
        owner_key = db._owner_key(set_name, db.records[key])
        lines.append("  set  %-13s #%d  (ring owned by #%d)" % (set_name, key, owner_key))
    return "\n".join(lines)


def execute(db, line):
    words = line.split()
    if len(words) == 0:
        return ""
    verb = words[0].lower()
    args = words[1:]

    if verb == "help":
        return HELP
    if verb == "schema":
        lines = []
        for rtype in sorted(db.record_types.keys()):
            lines.append("record %-9s calc key: %s" % (rtype, db.record_types[rtype]))
        for set_name in sorted(db.set_types.keys()):
            o, m, ins = db.set_types[set_name]
            lines.append("set    %-13s owner %-9s member %-9s %s" % (set_name, o, m, ins))
        return "\n".join(lines)
    if verb == "load":
        if len(args) == 1 and args[0].lower() == "demo":
            load_demo(db)
            return "loaded %d records" % len(db.records)
        raise DBError("usage: load demo")
    if verb == "currency":
        return show_currency(db)
    if verb == "get":
        return db.get().describe()
    if verb == "store":
        if len(args) < 1:
            raise DBError("usage: store TYPE field=value ...")
        rec = db.store(args[0].upper(), parse_fields(args[1:]))
        return "stored " + rec.describe()
    if verb == "modify":
        return "modified " + db.modify(parse_fields(args)).describe()
    if verb == "erase":
        return "erased " + db.erase().describe()
    if verb == "connect" and len(args) == 1:
        return "connected " + db.connect(args[0].upper()).describe()
    if verb == "disconnect" and len(args) == 1:
        return "disconnected " + db.disconnect(args[0].upper()).describe()
    if verb == "walk" and len(args) == 1:
        set_name = args[0].upper()
        lines = []
        try:
            rec = db.find_first(set_name)
            while True:
                lines.append("  " + rec.describe())
                rec = db.find_next(set_name)
        except EndOfSet:
            lines.append("  (end of set)")
        return "\n".join(lines)
    if verb == "compare" and len(args) == 1:
        product = args[0].upper()
        flat = flat_files(db)
        scanned, reads = scan_who_bought(flat, product)
        navigated, touches = navigate_who_bought(db, product)
        lines = []
        lines.append("customers who bought %s: %s" % (product, ", ".join(navigated)))
        lines.append("  file scan  : %d records read   (all three files, every time)" % reads)
        lines.append("  navigation : %d records touched" % touches)
        if scanned != navigated:
            lines.append("  WARNING: the two methods disagree: %s" % scanned)
        return "\n".join(lines)
    if verb == "find":
        if len(args) < 2:
            raise DBError("usage: find TYPE KEY | find first|last|next|prior|owner SET")
        word = args[0].lower()
        if word == "first":
            return db.find_first(args[1].upper()).describe()
        if word == "last":
            return db.find_last(args[1].upper()).describe()
        if word == "next":
            return db.find_next(args[1].upper()).describe()
        if word == "prior":
            return db.find_prior(args[1].upper()).describe()
        if word == "owner":
            return db.find_owner(args[1].upper()).describe()
        key_text = args[1]
        if "=" in key_text:
            key_text = key_text.split("=", 1)[1]
        return db.find_calc(args[0].upper(), parse_value(key_text)).describe()
    raise DBError("unknown command: %s (try help)" % line)


def run_line(db, line):
    try:
        output = execute(db, line)
    except EndOfSet as e:
        output = "end of set"
    except DBError as e:
        output = "error: %s" % e
    return output


def run_file(path):
    db = new_demo_db()
    with open(path) as f:
        lines = f.read().splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            continue
        print("> " + stripped)
        output = run_line(db, stripped)
        if output != "":
            print(output)


def repl():
    db = new_demo_db()
    print("Bachman-style network database. 'load demo' to fill it, 'help' for commands.")
    while True:
        try:
            line = input("ids> ")
        except EOFError:
            print()
            return
        if line.strip().lower() in ("quit", "exit"):
            return
        output = run_line(db, line)
        if output != "":
            print(output)


# ── Tests ────────────────────────────────────────────────────────────────────

def run_tests():
    passed = 0
    total = 0

    def check(name, condition):
        nonlocal passed, total
        total = total + 1
        if condition:
            passed = passed + 1
            print("  ok    " + name)
        else:
            print("  FAIL  " + name)

    def raises(exception_type, function, *args):
        try:
            function(*args)
        except exception_type:
            return True
        return False

    # 1. STORE then FIND by CALC key.
    db = new_demo_db()
    db.store("CUSTOMER", {"name": "Acme", "city": "Boston"})
    db.store("CUSTOMER", {"name": "Binx", "city": "Austin"})
    check("find by calc key", db.find_calc("CUSTOMER", "Acme").fields["city"] == "Boston")

    # 2. Duplicate key rejected.
    check("duplicate calc key rejected",
          raises(DBError, db.store, "CUSTOMER", {"name": "Acme", "city": "X"}))

    # 3. Orders join the current customer automatically, in insertion order.
    db = new_demo_db()
    db.store("CUSTOMER", {"name": "Acme"})
    db.store("ORDER", {"no": 1})
    db.store("ORDER", {"no": 2})
    db.store("ORDER", {"no": 3})
    db.find_calc("CUSTOMER", "Acme")
    first = db.find_first("CUST-ORDERS").fields["no"]
    second = db.find_next("CUST-ORDERS").fields["no"]
    third = db.find_next("CUST-ORDERS").fields["no"]
    check("auto-connect keeps insertion order", [first, second, third] == [1, 2, 3])

    # 4. End of set after the last member.
    check("find next past the last member is end of set",
          raises(EndOfSet, db.find_next, "CUST-ORDERS"))

    # 5. Owner navigation.
    check("find owner returns the customer",
          db.find_owner("CUST-ORDERS").fields["name"] == "Acme")

    # 6. Empty set.
    db.store("CUSTOMER", {"name": "Binx"})
    check("find first in an empty set is end of set",
          raises(EndOfSet, db.find_first, "CUST-ORDERS"))

    # 7. Prior and last walk backwards.
    db.find_calc("CUSTOMER", "Acme")
    last = db.find_last("CUST-ORDERS").fields["no"]
    prior = db.find_prior("CUST-ORDERS").fields["no"]
    check("find last then prior", [last, prior] == [3, 2])

    # 8. STORE a member with no current owner fails and changes nothing.
    db = new_demo_db()
    before = len(db.records)
    check("store ORDER with no current customer fails",
          raises(DBError, db.store, "ORDER", {"no": 1}))
    check("failed store leaves the database untouched", len(db.records) == before)

    # 9. An ITEM sits in two rings at once.
    db = new_demo_db()
    load_demo(db)
    check("demo rings are consistent", check_rings(db))
    db.find_calc("PRODUCT", "WIDGET")
    item = db.find_first("PRODUCT-ITEMS")
    check("item is a member of both ORDER-ITEMS and PRODUCT-ITEMS",
          "ORDER-ITEMS" in item.owner and "PRODUCT-ITEMS" in item.owner)

    # 10. Currency: finding the item makes it current in BOTH of its sets.
    check("item becomes current in both sets",
          db.current_of_set["ORDER-ITEMS"] == item.dbkey
          and db.current_of_set["PRODUCT-ITEMS"] == item.dbkey)

    # 11. Crossing from one ring to the other, then resuming the first.
    order = db.find_owner("ORDER-ITEMS")
    check("item -> order via ORDER-ITEMS", order.rtype == "ORDER")
    check("PRODUCT-ITEMS currency survives the detour",
          db.current_of_set["PRODUCT-ITEMS"] == item.dbkey)
    second_item = db.find_next("PRODUCT-ITEMS")
    check("find next in PRODUCT-ITEMS resumes after the detour",
          second_item.dbkey != item.dbkey and second_item.owner["PRODUCT-ITEMS"] == item.owner["PRODUCT-ITEMS"])

    # 12. MODIFY works, but not on the calc key.
    db.find_calc("CUSTOMER", "Acme")
    db.modify({"city": "Paris"})
    check("modify a non-key field", db.get().fields["city"] == "Paris")
    check("modify of the calc key rejected", raises(DBError, db.modify, {"name": "Other"}))

    # 13. ERASE refuses to orphan members, and works on a leaf.
    check("erase of an owner with members is rejected", raises(DBError, db.erase))
    db.find_calc("CUSTOMER", "Acme")
    order_rec = db.find_first("CUST-ORDERS")
    item_rec = db.find_first("ORDER-ITEMS")
    db.erase()
    check("erase of a leaf item succeeds", item_rec.dbkey not in db.records)
    check("rings still consistent after erase", check_rings(db))

    # 14. MANUAL sets: store does not connect, CONNECT and DISCONNECT do.
    manual = Database({"DEPT": "name", "EMP": "id"}, {"STAFF": ("DEPT", "EMP", "MANUAL")})
    manual.store("DEPT", {"name": "Sales"})
    manual.store("EMP", {"id": 7})
    check("manual set: not connected after store", "STAFF" not in manual.get().owner)
    manual.find_calc("DEPT", "Sales")
    manual.find_calc("EMP", 7)
    manual.connect("STAFF")
    check("manual set: connect joins the ring", manual.members_forward("STAFF", 1) == [2])
    manual.disconnect("STAFF")
    check("manual set: disconnect empties the ring", manual.members_forward("STAFF", 1) == [])

    # 15. Navigation agrees with the file scan, for every product.
    db = new_demo_db()
    load_demo(db)
    flat = flat_files(db)
    all_agree = True
    all_cheaper = True
    for product_name, price in DEMO_PRODUCTS:
        scanned, reads = scan_who_bought(flat, product_name)
        navigated, touches = navigate_who_bought(db, product_name)
        if scanned != navigated:
            all_agree = False
        if touches >= reads:
            all_cheaper = False
    check("navigation and file scan give the same customers", all_agree)
    check("navigation touches far fewer records than the scan reads", all_cheaper)

    # 16. Walk order of a ring equals the order it was stored in.
    db.find_calc("CUSTOMER", "Corvo")
    numbers = []
    rec = db.find_first("CUST-ORDERS")
    numbers.append(rec.fields["no"])
    rec = db.find_next("CUST-ORDERS")
    numbers.append(rec.fields["no"])
    check("Corvo's orders in stored order", numbers == [301, 302])

    print()
    print("%d/%d passed" % (passed, total))
    return passed == total


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    global VERBOSE
    args = sys.argv[1:]
    if "--test" in args:
        ok = run_tests()
        sys.exit(0 if ok else 1)
    if "--verbose" in args:
        VERBOSE = True
        print("(verbose mode: every pointer followed and every currency update is printed)\n")
    files = []
    for a in args:
        if not a.startswith("--"):
            files.append(a)
    if len(files) > 0:
        run_file(files[0])
        return
    repl()


if __name__ == "__main__":
    main()

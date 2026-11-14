"""
Charles Bachman's Integrated Data Store (IDS) and the CODASYL network data
model -- a full working version.
(C. W. Bachman, General Electric, 1963; standardized by CODASYL's Data Base
Task Group in 1969/1971.)

BEFORE IDS:
    "Database" was not a concept yet. Each program that needed data wrote
    its own file-access code against a sequential tape file -- read record
    1, then record 2, then record 3, in order, start to finish. If program
    A needed "all of Acme's orders" and program B needed "all of today's
    orders," each one re-scanned the whole file its own way, and the same
    customer or order data was often duplicated across several files
    because there was no shared place to put it.

AFTER IDS:
    One shared database, on random-access disk instead of tape. Related
    records are linked through named SETS: an owner record type
    (CUSTOMER) and a member record type (ORDER), wired together the moment
    an order is created for a customer. A program NAVIGATES the database:
    FIND the owner, FIND FIRST member within the set, FIND NEXT -- walking
    direct links instead of scanning. CODASYL's 1969 Data Base Task Group
    report turned Bachman's design into an industry standard: the network
    model became the dominant commercial database design of the 1970s,
    years before SQL and the relational model (Codd, 1970) displaced it.

This file mirrors that model directly: record types, named SET types
(owner -> member -- "set" in the CODASYL sense, not Python's set()), and
navigation primitives (FIND FIRST/NEXT WITHIN SET, FIND OWNER) built on
CURRENCY INDICATORS -- the database's memory of where you last were. That
is exactly how the real IDS/CODASYL Data Manipulation Language worked:
there was no SELECT, only FIND, and FIND always moved a pointer.

Pipeline:
    schema (set types)
        -> STORE records
        -> CONNECT members into owners' sets
        -> FIND FIRST/NEXT WITHIN SET, FIND OWNER   (navigate the links)
        -> printed result

Run:
    python3 implementation.py                 # interactive REPL
    python3 implementation.py practice.network # load and run a script
    python3 implementation.py --test           # self-test suite
    python3 implementation.py --verbose        # REPL that prints currency
"""

import sys

VERBOSE = False


class BachmanError(Exception):
    pass


# -- The database -------------------------------------------------------------
#
# A record is just a dict of fields, keyed by (record_type, numeric_id).
# A SET TYPE is a named link between an owner record type and a member
# record type -- defined once by the schema, just like a real CODASYL DBA
# would define it before any program ran against the database.

class Database:
    def __init__(self):
        self.records = {}          # (rtype, rid) -> {field: value}
        self.next_id = {}          # rtype -> next free numeric id
        self.set_types = {}        # set_name -> (owner_type, member_type)
        self.set_members = {}      # set_name -> {owner_key: [member_key, ...]}
        self.member_owner = {}     # set_name -> {member_key: owner_key}
        self.current_of_set = {}   # set_name -> (owner_key, member_key or None)

    # -- schema --
    def define_set(self, set_name, owner_type, member_type):
        if set_name in self.set_types:
            raise BachmanError("set type already defined: %s" % set_name)
        self.set_types[set_name] = (owner_type, member_type)
        self.set_members[set_name] = {}
        self.member_owner[set_name] = {}

    def _require_set(self, set_name):
        if set_name not in self.set_types:
            raise BachmanError("no such set type: %s" % set_name)
        return self.set_types[set_name]

    # -- DML: STORE --
    def store(self, rtype, fields):
        rid = self.next_id.get(rtype, 1)
        self.next_id[rtype] = rid + 1
        key = (rtype, rid)
        self.records[key] = dict(fields)
        if VERBOSE:
            print("  [currency] current of record type %s -> %s" % (rtype, fmt_key(key)))
        return key

    def get(self, key):
        if key not in self.records:
            raise BachmanError("no such record: %s" % fmt_key(key))
        return self.records[key]

    # -- DML: CONNECT / DISCONNECT --
    def connect(self, set_name, owner_key, member_key):
        owner_type, member_type = self._require_set(set_name)
        if owner_key[0] != owner_type:
            raise BachmanError("%s owns %s records, not %s"
                                % (set_name, owner_type, owner_key[0]))
        if member_key[0] != member_type:
            raise BachmanError("%s holds %s members, not %s"
                                % (set_name, member_type, member_key[0]))
        if owner_key not in self.records:
            raise BachmanError("no such record: %s" % fmt_key(owner_key))
        if member_key not in self.records:
            raise BachmanError("no such record: %s" % fmt_key(member_key))
        if member_key in self.member_owner[set_name]:
            existing_owner = self.member_owner[set_name][member_key]
            raise BachmanError(
                "%s is already connected into %s under owner %s; disconnect first"
                % (fmt_key(member_key), set_name, fmt_key(existing_owner)))

        self.set_members[set_name].setdefault(owner_key, [])
        self.set_members[set_name][owner_key].append(member_key)
        self.member_owner[set_name][member_key] = owner_key
        self.current_of_set[set_name] = (owner_key, member_key)
        if VERBOSE:
            print("  [currency] current of %s -> %s (owner %s)"
                  % (set_name, fmt_key(member_key), fmt_key(owner_key)))

    def disconnect(self, set_name, member_key):
        self._require_set(set_name)
        if member_key not in self.member_owner[set_name]:
            raise BachmanError("%s is not connected into %s" % (fmt_key(member_key), set_name))
        owner_key = self.member_owner[set_name].pop(member_key)
        self.set_members[set_name][owner_key].remove(member_key)
        if self.current_of_set.get(set_name) == (owner_key, member_key):
            self.current_of_set[set_name] = (owner_key, None)

    # -- DML: FIND FIRST/NEXT WITHIN SET, FIND OWNER --
    def find_first_within_set(self, set_name, owner_key):
        self._require_set(set_name)
        members = self.set_members[set_name].get(owner_key, [])
        if len(members) == 0:
            self.current_of_set[set_name] = (owner_key, None)
            if VERBOSE:
                print("  [currency] current of %s -> none (owner %s has no members)"
                      % (set_name, fmt_key(owner_key)))
            return None
        member_key = members[0]
        self.current_of_set[set_name] = (owner_key, member_key)
        if VERBOSE:
            print("  [currency] current of %s -> %s (owner %s)"
                  % (set_name, fmt_key(member_key), fmt_key(owner_key)))
        return member_key

    def find_next_within_set(self, set_name):
        self._require_set(set_name)
        if set_name not in self.current_of_set:
            raise BachmanError(
                "no currency for %s yet -- FIND FIRST WITHIN SET first" % set_name)
        owner_key, member_key = self.current_of_set[set_name]
        members = self.set_members[set_name].get(owner_key, [])
        if member_key is None or member_key not in members:
            return None
        index = members.index(member_key)
        if index + 1 >= len(members):
            self.current_of_set[set_name] = (owner_key, None)
            return None
        next_key = members[index + 1]
        self.current_of_set[set_name] = (owner_key, next_key)
        if VERBOSE:
            print("  [currency] current of %s -> %s (owner %s)"
                  % (set_name, fmt_key(next_key), fmt_key(owner_key)))
        return next_key

    def find_owner(self, set_name, member_key):
        self._require_set(set_name)
        return self.member_owner[set_name].get(member_key)

    # -- the "before": a brute-force scan, counting every record touched --
    def scan(self, rtype, predicate):
        examined = 0
        found = []
        for key in self.records:
            if key[0] != rtype:
                continue
            examined += 1
            if predicate(self.records[key]):
                found.append(key)
        return found, examined


def fmt_key(key):
    if key is None:
        return "none"
    return "%s:%d" % key


def parse_key(token):
    if ":" not in token:
        raise BachmanError("expected TYPE:ID, got %r" % token)
    rtype, rid_str = token.split(":", 1)
    try:
        rid = int(rid_str)
    except ValueError:
        raise BachmanError("expected a numeric id, got %r" % token)
    return (rtype, rid)


def parse_fields(tokens):
    fields = {}
    for token in tokens:
        if "=" not in token:
            raise BachmanError("expected field=value, got %r" % token)
        field, value = token.split("=", 1)
        fields[field] = value
    return fields


# -- The default schema --------------------------------------------------------
#
# In a real CODASYL system the schema (record types and set types) is fixed
# by a database administrator before any application program runs. We mirror
# that here: every REPL session and script starts from the same fixed
# schema, two levels deep, so you can navigate CUSTOMER -> ORDER -> ITEM.

def build_schema():
    db = Database()
    db.define_set("CUSTOMER-ORDER", "CUSTOMER", "ORDER")
    db.define_set("ORDER-ITEM", "ORDER", "ITEM")
    return db


# -- REPL / script commands ----------------------------------------------------

BANNER = """Charles Bachman's network database (IDS / CODASYL, 1963-1973).
Schema: CUSTOMER-ORDER (owner CUSTOMER, member ORDER)
        ORDER-ITEM      (owner ORDER,    member ITEM)
Commands:
  store TYPE field=value ...        store a new record, e.g. store CUSTOMER name=Acme
  connect SET OWNER MEMBER          connect MEMBER into OWNER's set, e.g.
                                       connect CUSTOMER-ORDER CUSTOMER:1 ORDER:1
  disconnect SET MEMBER             remove MEMBER from whichever owner holds it
  find first within SET owner KEY   first member of KEY's set occurrence
  find next within SET              next member, using current currency
  find owner SET MEMBER             which owner holds MEMBER
  get KEY                           print one record, e.g. get ORDER:1
  scan TYPE [field=value ...]       the "before": brute-force table scan
  show                               print the whole database
  help                               show this again
Ctrl-D to quit."""


def do_command(line, db):
    parts = line.split()
    if len(parts) == 0:
        return
    cmd = parts[0]

    if cmd == "store" and len(parts) >= 2:
        rtype = parts[1]
        fields = parse_fields(parts[2:])
        key = db.store(rtype, fields)
        print("stored %s %s" % (fmt_key(key), fields))

    elif cmd == "connect" and len(parts) == 4:
        set_name, owner_key, member_key = parts[1], parse_key(parts[2]), parse_key(parts[3])
        db.connect(set_name, owner_key, member_key)
        print("connected %s into %s owned by %s" % (fmt_key(member_key), set_name, fmt_key(owner_key)))

    elif cmd == "disconnect" and len(parts) == 3:
        set_name, member_key = parts[1], parse_key(parts[2])
        db.disconnect(set_name, member_key)
        print("disconnected %s from %s" % (fmt_key(member_key), set_name))

    elif cmd == "find" and len(parts) == 6 and parts[1] == "first" and parts[2] == "within" and parts[4] == "owner":
        set_name, owner_key = parts[3], parse_key(parts[5])
        result = db.find_first_within_set(set_name, owner_key)
        if result is None:
            print("  (no members)")
        else:
            print("  current: %s %s" % (fmt_key(result), db.get(result)))

    elif cmd == "find" and len(parts) == 4 and parts[1] == "next" and parts[2] == "within":
        set_name = parts[3]
        result = db.find_next_within_set(set_name)
        if result is None:
            print("  (end of set)")
        else:
            print("  current: %s %s" % (fmt_key(result), db.get(result)))

    elif cmd == "find" and len(parts) == 4 and parts[1] == "owner":
        set_name, member_key = parts[2], parse_key(parts[3])
        owner_key = db.find_owner(set_name, member_key)
        if owner_key is None:
            print("  (not connected into %s)" % set_name)
        else:
            print("  owner: %s %s" % (fmt_key(owner_key), db.get(owner_key)))

    elif cmd == "get" and len(parts) == 2:
        key = parse_key(parts[1])
        print("  %s %s" % (fmt_key(key), db.get(key)))

    elif cmd == "scan" and len(parts) >= 2:
        rtype = parts[1]
        fields = parse_fields(parts[2:]) if len(parts) > 2 else {}

        def predicate(record):
            for field, value in fields.items():
                if record.get(field) != value:
                    return False
            return True

        found, examined = db.scan(rtype, predicate)
        print("  found %s after examining %d %s record(s)" % (
            [fmt_key(k) for k in found], examined, rtype))

    elif cmd == "show":
        if len(db.records) == 0:
            print("  (empty database)")
        for key in db.records:
            print("  %s %s" % (fmt_key(key), db.records[key]))
        for set_name in db.set_types:
            owner_type, member_type = db.set_types[set_name]
            print("  SET %s (owner %s, member %s):" % (set_name, owner_type, member_type))
            for owner_key in db.set_members[set_name]:
                members = db.set_members[set_name][owner_key]
                print("    %s -> %s" % (fmt_key(owner_key), [fmt_key(m) for m in members]))

    elif cmd == "help":
        print(BANNER)

    else:
        print("unknown command: %s (try 'help')" % line)


def repl():
    db = build_schema()
    print(BANNER)
    while True:
        try:
            line = input("bachman> ")
        except EOFError:
            print()
            return
        if line.strip() == "":
            continue
        try:
            do_command(line.strip(), db)
        except BachmanError as err:
            print("error: %s" % err)


def run_file(path):
    """Load and run a network-database script: one command per line, '#'
    starts a comment. Each command is echoed before it runs, the same as
    typing it into the REPL by hand."""
    db = build_schema()
    with open(path) as source_file:
        lines = source_file.readlines()
    for raw_line in lines:
        line = raw_line.split("#")[0].strip()
        if line == "":
            continue
        print("bachman> " + line)
        try:
            do_command(line, db)
        except BachmanError as err:
            print("error: %s" % err)


# -- Self-test suite ------------------------------------------------------------

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

    # 1. STORE creates a record with the fields you gave it.
    db = build_schema()
    key = db.store("CUSTOMER", {"name": "Acme"})
    check("store: record exists with the right fields", db.get(key) == {"name": "Acme"})

    # 2. CONNECT links a member under an owner; FIND FIRST sees it.
    db = build_schema()
    acme = db.store("CUSTOMER", {"name": "Acme"})
    order1 = db.store("ORDER", {"total": "250"})
    db.connect("CUSTOMER-ORDER", acme, order1)
    check("find first within set returns the only member",
          db.find_first_within_set("CUSTOMER-ORDER", acme) == order1)

    # 3. Several members connect in order; FIND FIRST then FIND NEXT walks
    #    all of them, and the set ends with None.
    db = build_schema()
    acme = db.store("CUSTOMER", {"name": "Acme"})
    order1 = db.store("ORDER", {"total": "250"})
    order2 = db.store("ORDER", {"total": "80"})
    db.connect("CUSTOMER-ORDER", acme, order1)
    db.connect("CUSTOMER-ORDER", acme, order2)
    walked = [db.find_first_within_set("CUSTOMER-ORDER", acme)]
    walked.append(db.find_next_within_set("CUSTOMER-ORDER"))
    walked.append(db.find_next_within_set("CUSTOMER-ORDER"))
    check("find first then find next walks both members, then None",
          walked == [order1, order2, None])

    # 4. FIND OWNER returns the owner of a connected member.
    db = build_schema()
    acme = db.store("CUSTOMER", {"name": "Acme"})
    order1 = db.store("ORDER", {"total": "250"})
    db.connect("CUSTOMER-ORDER", acme, order1)
    check("find owner returns the connected owner", db.find_owner("CUSTOMER-ORDER", order1) == acme)

    # 5. FIND OWNER on an unconnected member returns None.
    db = build_schema()
    order1 = db.store("ORDER", {"total": "250"})
    check("find owner on an unconnected member returns None",
          db.find_owner("CUSTOMER-ORDER", order1) is None)

    # 6. A member can only be connected into one owner occurrence of a given
    #    set type at a time -- the core CODASYL set rule. Connecting it into
    #    a second owner without disconnecting first raises an error.
    db = build_schema()
    acme = db.store("CUSTOMER", {"name": "Acme"})
    globex = db.store("CUSTOMER", {"name": "Globex"})
    order1 = db.store("ORDER", {"total": "250"})
    db.connect("CUSTOMER-ORDER", acme, order1)
    raised = False
    try:
        db.connect("CUSTOMER-ORDER", globex, order1)
    except BachmanError:
        raised = True
    check("connecting an already-connected member raises an error", raised)

    # 7. After DISCONNECT, a member can be reconnected to a different owner.
    db.disconnect("CUSTOMER-ORDER", order1)
    db.connect("CUSTOMER-ORDER", globex, order1)
    check("disconnect then reconnect to a new owner works",
          db.find_owner("CUSTOMER-ORDER", order1) == globex)

    # 8. FIND FIRST on an owner with no members returns None.
    db = build_schema()
    acme = db.store("CUSTOMER", {"name": "Acme"})
    check("find first on an empty set returns None",
          db.find_first_within_set("CUSTOMER-ORDER", acme) is None)

    # 9. Connecting the wrong record type as the owner is rejected.
    db = build_schema()
    order1 = db.store("ORDER", {"total": "250"})
    order2 = db.store("ORDER", {"total": "80"})
    raised = False
    try:
        db.connect("CUSTOMER-ORDER", order1, order2)   # ORDER is not a valid owner here
    except BachmanError:
        raised = True
    check("connecting the wrong owner type raises an error", raised)

    # 10. Connecting the wrong record type as the member is rejected.
    db = build_schema()
    acme = db.store("CUSTOMER", {"name": "Acme"})
    globex = db.store("CUSTOMER", {"name": "Globex"})
    raised = False
    try:
        db.connect("CUSTOMER-ORDER", acme, globex)      # CUSTOMER is not a valid member here
    except BachmanError:
        raised = True
    check("connecting the wrong member type raises an error", raised)

    # 11. Two-level navigation: CUSTOMER -> ORDER -> ITEM, following two
    #     different set types one after another.
    db = build_schema()
    acme = db.store("CUSTOMER", {"name": "Acme"})
    order1 = db.store("ORDER", {"total": "250"})
    widget = db.store("ITEM", {"sku": "WIDGET-A"})
    db.connect("CUSTOMER-ORDER", acme, order1)
    db.connect("ORDER-ITEM", order1, widget)
    first_order = db.find_first_within_set("CUSTOMER-ORDER", acme)
    first_item = db.find_first_within_set("ORDER-ITEM", first_order)
    check("two-level navigation reaches the item through the order",
          first_order == order1 and first_item == widget)

    # 12. The point of the whole chapter: navigating a set costs one step
    #     per member actually found, while scanning costs one look at every
    #     record of that type -- including the ones that don't match.
    db = build_schema()
    acme = db.store("CUSTOMER", {"name": "Acme"})
    order1 = db.store("ORDER", {"total": "250", "customer": "Acme"})
    order2 = db.store("ORDER", {"total": "80", "customer": "Acme"})
    db.connect("CUSTOMER-ORDER", acme, order1)
    db.connect("CUSTOMER-ORDER", acme, order2)
    for _ in range(8):
        db.store("ORDER", {"total": "999", "customer": "SomeoneElse"})  # unrelated orders

    navigated = []
    current = db.find_first_within_set("CUSTOMER-ORDER", acme)
    while current is not None:
        navigated.append(current)
        current = db.find_next_within_set("CUSTOMER-ORDER")
    scanned, examined = db.scan("ORDER", lambda r: r.get("customer") == "Acme")
    check("navigation finds the same orders as a scan, for far fewer records touched",
          navigated == scanned and len(navigated) == 2 and examined == 10)

    # 13. FIND NEXT WITHIN SET before any FIND FIRST has established
    #     currency is an error -- there's nothing to navigate from yet.
    db = build_schema()
    raised = False
    try:
        db.find_next_within_set("CUSTOMER-ORDER")
    except BachmanError:
        raised = True
    check("find next without prior currency raises an error", raised)

    # 14. Referencing an undefined set type is rejected, whether connecting
    #     or navigating.
    db = build_schema()
    acme = db.store("CUSTOMER", {"name": "Acme"})
    raised = False
    try:
        db.find_first_within_set("NO-SUCH-SET", acme)
    except BachmanError:
        raised = True
    check("navigating an undefined set type raises an error", raised)

    print()
    print("%d/%d passed" % (passed, total))
    return passed == total


# -- Entry point ------------------------------------------------------------

def main():
    global VERBOSE
    args = sys.argv[1:]
    if "--test" in args:
        ok = run_tests()
        sys.exit(0 if ok else 1)
    if "--verbose" in args:
        VERBOSE = True
        print("(verbose mode: every currency update is printed)\n")
    files = [a for a in args if not a.startswith("--")]
    if len(files) > 0:
        run_file(files[0])
        return
    repl()


if __name__ == "__main__":
    main()

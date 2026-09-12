"""
Integrated Data Store (IDS) / CODASYL network model -- a working simulation
of Charles W. Bachman's 1963 invention at General Electric, standardized by
CODASYL's Data Base Task Group (DBTG) in 1969-1971.

Before IDS, "the data" was one flat file per record type. Every program
that needed to relate two files (find a customer's orders) re-derived that
relationship by scanning: read every order, keep the ones whose customer_id
field matched. The relationship existed only in the programmer's head and
in whatever loop they happened to write that week.

Bachman's idea: store the relationship as a first-class structure called a
SET -- an owner record (one CUSTOMER) linked to its member records (that
customer's ORDERs) as a ring of pointers, wired together the moment a
member is STOREd. A program no longer scans; it NAVIGATES: position on a
record, then FIND FIRST / FIND NEXT / FIND OWNER to walk the ring one
pointer at a time. The database always knows where you are -- that's the
"currency indicator" -- so you never pass record IDs around by hand.

This file implements that model directly:
  - Record: a typed bag of fields, plus NEXT/PRIOR/OWNER pointer slots
    per set it participates in (the actual 1960s physical representation).
  - SetType: an owner-record-type -> member-record-type relationship,
    with FIFO or LIFO insertion order.
  - Database: schema + records + the currency indicators every DML verb
    reads and updates -- current of run unit, current of record type,
    current of set type.
  - DML verbs: STORE, FIND ANY, FIND FIRST/NEXT/OWNER WITHIN <set>, GET,
    MODIFY -- a simplified but faithful subset of the DBTG language.

Usage:
    python3 implementation.py                # interactive REPL
    python3 implementation.py script.ids      # run a DML script file
    python3 implementation.py --test          # test suite
    python3 implementation.py --verbose       # REPL that prints currency
                                               # indicators after every verb
"""

import sys

VERBOSE = False


class BachmanError(Exception):
    """A DML error: navigating a set that isn't positioned, a STORE with
    no current owner to connect to, a FIND that matches nothing, and so
    on. Every one of these is a real failure mode of the 1960s system,
    not a made-up one."""


# ── The schema and the data ──────────────────────────────────────────────────

class Record:
    """One record occurrence. `next`, `prior`, and `owner` are dicts keyed
    by set name, because the same record type can play a role (owner or
    member) in more than one set type at once -- CUSTOMER might own both
    a CUSTOMER-ORDERS set and a CUSTOMER-PAYMENTS set."""

    def __init__(self, record_type, record_id, fields):
        self.record_type = record_type
        self.record_id = record_id
        self.fields = fields
        self.next = {}
        self.prior = {}
        self.owner = {}

    def __repr__(self):
        return "%s#%d%s" % (self.record_type, self.record_id, self.fields)


class SetType:
    """A named 1-to-many relationship: one OWNER-type record links to zero
    or more MEMBER-type records. `order` controls where a newly STOREd
    member lands in the ring: FIFO appends at the end, LIFO inserts right
    after the owner (becomes the new first member)."""

    def __init__(self, name, owner_type, member_type, order="FIFO"):
        self.name = name
        self.owner_type = owner_type
        self.member_type = member_type
        self.order = order


class Database:
    def __init__(self):
        self.schema_sets = {}          # set name -> SetType
        self.records_by_type = {}      # record type -> list of Record
        self._next_id = 1

        # Currency indicators. Every DML verb below updates these, and
        # every navigational verb reads them. This is exactly what "the
        # programmer as navigator" means: you don't say WHICH record,
        # you say "the current one", and the database remembers.
        self.current_of_run_unit = None
        self.current_of_type = {}      # record type -> Record
        self.current_of_set = {}       # set name -> Record (owner or member)

    def define_set(self, name, owner_type, member_type, order="FIFO"):
        self.schema_sets[name] = SetType(name, owner_type, member_type, order)
        self.records_by_type.setdefault(owner_type, [])
        self.records_by_type.setdefault(member_type, [])

    # ── currency bookkeeping ────────────────────────────────────────────────

    def _touch(self, record):
        self.current_of_run_unit = record
        self.current_of_type[record.record_type] = record
        for set_name, set_type in self.schema_sets.items():
            is_owner = record.record_type == set_type.owner_type
            is_member = record.record_type == set_type.member_type
            if is_owner or is_member:
                self.current_of_set[set_name] = record

    # ── DML: STORE ──────────────────────────────────────────────────────────

    def store(self, record_type, **fields):
        record = Record(record_type, self._next_id, fields)
        self._next_id += 1
        self.records_by_type.setdefault(record_type, []).append(record)

        # AUTOMATIC set membership: the moment a member-type record is
        # STOREd, connect it into the set owned by the current occurrence
        # of the owner type. That's the whole trick -- the relationship
        # is wired in at write time, not re-derived at read time.
        for set_name, set_type in self.schema_sets.items():
            if set_type.member_type != record_type:
                continue
            owner = self.current_of_type.get(set_type.owner_type)
            if owner is None:
                raise BachmanError(
                    "STORE %s: no current %s to connect it under (set %s)"
                    % (record_type, set_type.owner_type, set_name))
            self._connect(set_name, owner, record)

        self._touch(record)
        return record

    def _connect(self, set_name, owner, member):
        """Wire `member` into the ring owned by `owner`. The ring is:
        owner.next = first member ... last member.next = owner (closes
        the loop). An empty set has owner.next == owner.prior == owner."""
        set_type = self.schema_sets[set_name]
        member.owner[set_name] = owner

        if owner.next.get(set_name) is None:
            owner.next[set_name] = owner
            owner.prior[set_name] = owner

        if set_type.order == "LIFO":
            first = owner.next[set_name]
            member.next[set_name] = first
            member.prior[set_name] = owner
            first.prior[set_name] = member
            owner.next[set_name] = member
        else:  # FIFO
            last = owner.prior[set_name]
            member.prior[set_name] = last
            member.next[set_name] = owner
            last.next[set_name] = member
            owner.prior[set_name] = member

    # ── DML: FIND ───────────────────────────────────────────────────────────

    def find_any(self, record_type, **where):
        """The entry point into the database: a plain scan for a record
        matching every field in `where`. This is the one operation IDS
        could NOT make cheap -- you have to start somewhere. Everything
        after this point is navigation, which is cheap."""
        for record in self.records_by_type.get(record_type, []):
            matched = True
            for key, value in where.items():
                if record.fields.get(key) != value:
                    matched = False
                    break
            if matched:
                self._touch(record)
                return record
        raise BachmanError("FIND ANY %s: no record matches %s" % (record_type, where))

    def find_first(self, set_name):
        self._require_set(set_name)
        owner = self._occurrence_owner(set_name)
        # An owner that never had a member CONNECTed has no ring pointers
        # at all yet -- that's an empty set occurrence, same as a ring
        # that points back to itself.
        first = owner.next.get(set_name, owner)
        if first is owner:
            raise BachmanError("FIND FIRST WITHIN %s: set occurrence is empty" % set_name)
        self._touch(first)
        return first

    def find_next(self, set_name):
        set_type = self._require_set(set_name)
        position = self.current_of_set.get(set_name)
        if position is None:
            raise BachmanError("FIND NEXT WITHIN %s: set not positioned" % set_name)
        nxt = position.next.get(set_name, position)
        if nxt.record_type == set_type.owner_type:
            raise BachmanError("FIND NEXT WITHIN %s: end of set" % set_name)
        self._touch(nxt)
        return nxt

    def find_owner(self, set_name):
        set_type = self._require_set(set_name)
        position = self.current_of_set.get(set_name)
        if position is None:
            raise BachmanError("FIND OWNER WITHIN %s: set not positioned" % set_name)
        if position.record_type == set_type.owner_type:
            self._touch(position)
            return position
        owner = position.owner[set_name]
        self._touch(owner)
        return owner

    def _require_set(self, set_name):
        if set_name not in self.schema_sets:
            raise BachmanError("no such set type: %s" % set_name)
        return self.schema_sets[set_name]

    def _occurrence_owner(self, set_name):
        set_type = self.schema_sets[set_name]
        position = self.current_of_set.get(set_name)
        if position is None:
            raise BachmanError("FIND FIRST WITHIN %s: no current occurrence" % set_name)
        if position.record_type == set_type.owner_type:
            return position
        return position.owner[set_name]

    # ── DML: GET / MODIFY ───────────────────────────────────────────────────

    def get(self):
        if self.current_of_run_unit is None:
            raise BachmanError("GET: nothing is current")
        return self.current_of_run_unit.fields

    def modify(self, **fields):
        if self.current_of_run_unit is None:
            raise BachmanError("MODIFY: nothing is current")
        self.current_of_run_unit.fields.update(fields)
        return self.current_of_run_unit

    # ── the "before" comparison: what a flat file makes you do ────────────

    def scan_for_members(self, record_type, owner_field, owner_id):
        """No set, no ring -- just what every program had to write before
        1963: read every record of this type and keep the ones whose
        owner_field matches. Returns (matches, records_examined)."""
        matches = []
        examined = 0
        for record in self.records_by_type.get(record_type, []):
            examined += 1
            if record.fields.get(owner_field) == owner_id:
                matches.append(record)
        return matches, examined


# ── Demo schema used by the REPL and script runner ───────────────────────────

def build_demo_database():
    db = Database()
    db.define_set("CUSTOMER-ORDERS", owner_type="CUSTOMER", member_type="ORDER", order="FIFO")
    return db


# ── Command language: a simplified DBTG DML ──────────────────────────────────

def parse_fields(tokens):
    fields = {}
    for token in tokens:
        key, _, value = token.partition("=")
        if value.lstrip("-").isdigit():
            fields[key] = int(value)
        else:
            fields[key] = value
    return fields


def print_currency(db):
    print("  currency:")
    print("    run unit: %s" % (db.current_of_run_unit,))
    for record_type in sorted(db.current_of_type):
        print("    of %s: %s" % (record_type, db.current_of_type[record_type]))
    for set_name in sorted(db.current_of_set):
        print("    of set %s: %s" % (set_name, db.current_of_set[set_name]))


def print_help():
    print("commands:")
    print("  store <TYPE> field=value ...       STORE a new record")
    print("  find any <TYPE> field=value ...     FIND ANY matching record")
    print("  find first <SET>                    FIND FIRST WITHIN set")
    print("  find next <SET>                     FIND NEXT WITHIN set")
    print("  find owner <SET>                    FIND OWNER WITHIN set")
    print("  get                                  GET the current record's fields")
    print("  modify field=value ...              MODIFY the current record")
    print("  schema                               show record types and sets")
    print("  scan <TYPE> <owner_field> <id>       the pre-1963 flat-file scan")
    print("  help / quit")


def print_schema(db):
    print("record types:", ", ".join(sorted(db.records_by_type)) or "(none)")
    for name, set_type in db.schema_sets.items():
        print("  set %s: %s (owner) -> %s (member), %s"
              % (name, set_type.owner_type, set_type.member_type, set_type.order))


def execute(db, line, verbose=False):
    tokens = line.strip().split()
    if not tokens:
        return
    command = tokens[0].lower()

    if command == "store":
        record_type = tokens[1]
        fields = parse_fields(tokens[2:])
        record = db.store(record_type, **fields)
        print("stored", record)

    elif command == "find":
        sub = tokens[1].lower()
        if sub == "any":
            record_type = tokens[2]
            fields = parse_fields(tokens[3:])
            record = db.find_any(record_type, **fields)
        elif sub == "first":
            record = db.find_first(tokens[2])
        elif sub == "next":
            record = db.find_next(tokens[2])
        elif sub == "owner":
            record = db.find_owner(tokens[2])
        else:
            print("unknown find form:", sub)
            return
        print("found", record)

    elif command == "get":
        print(db.get())

    elif command == "modify":
        fields = parse_fields(tokens[1:])
        record = db.modify(**fields)
        print("modified", record)

    elif command == "schema":
        print_schema(db)

    elif command == "scan":
        record_type, owner_field, owner_id = tokens[1], tokens[2], tokens[3]
        if owner_id.isdigit():
            owner_id = int(owner_id)
        matches, examined = db.scan_for_members(record_type, owner_field, owner_id)
        print("scanned %d %s records, matched %d: %s" % (examined, record_type, len(matches), matches))

    elif command in ("help", "?"):
        print_help()

    elif command in ("quit", "exit"):
        raise SystemExit

    else:
        print("unknown command:", command)
        return

    if verbose:
        print_currency(db)


def repl(db, verbose=False):
    print("IDS/CODASYL navigator -- 'help' for commands, 'quit' to leave.")
    if verbose:
        print("(verbose: currency indicators printed after every command)")
    while True:
        try:
            line = input("ids> ")
        except EOFError:
            print()
            break
        try:
            execute(db, line, verbose)
        except SystemExit:
            break
        except BachmanError as err:
            print("error:", err)


def run_script(db, path, verbose=False):
    with open(path) as handle:
        lines = handle.readlines()
    for raw_line in lines:
        line = raw_line.split("#")[0].strip()
        if line == "":
            continue
        print("ids> " + line)
        try:
            execute(db, line, verbose)
        except SystemExit:
            break
        except BachmanError as err:
            print("error:", err)


# ── Self-test suite ───────────────────────────────────────────────────────────

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

    # 1. Store an owner, then two members -- FIFO order preserves insertion.
    db = Database()
    db.define_set("CUSTOMER-ORDERS", "CUSTOMER", "ORDER", order="FIFO")
    ada = db.store("CUSTOMER", name="Ada")
    o1 = db.store("ORDER", item="Punched cards")
    o2 = db.store("ORDER", item="Vacuum tube")
    db.find_any("CUSTOMER", name="Ada")
    first = db.find_first("CUSTOMER-ORDERS")
    check("FIND FIRST returns the first-stored order (FIFO)", first is o1)

    # 2. FIND NEXT walks to the second member.
    second = db.find_next("CUSTOMER-ORDERS")
    check("FIND NEXT returns the second order", second is o2)

    # 3. FIND NEXT past the last member reports end of set.
    ended = False
    try:
        db.find_next("CUSTOMER-ORDERS")
    except BachmanError:
        ended = True
    check("FIND NEXT past the last member raises end-of-set", ended)

    # 4. FIND OWNER from a member jumps straight back to the owner, O(1).
    db.find_first("CUSTOMER-ORDERS")
    owner = db.find_owner("CUSTOMER-ORDERS")
    check("FIND OWNER from a member returns the owning customer", owner is ada)

    # 5. FIND OWNER when already positioned on the owner is a no-op.
    owner_again = db.find_owner("CUSTOMER-ORDERS")
    check("FIND OWNER from the owner itself returns the owner", owner_again is ada)

    # 6. LIFO insertion order: newest member comes back first.
    db2 = Database()
    db2.define_set("STACK-SET", "OWNER", "ITEM", order="LIFO")
    db2.store("OWNER", name="root")
    first_item = db2.store("ITEM", label="a")
    second_item = db2.store("ITEM", label="b")
    db2.find_any("OWNER", name="root")
    check("LIFO set returns the most recently stored member first",
          db2.find_first("STACK-SET") is second_item)

    # 7. An empty set occurrence has nothing to find.
    db3 = Database()
    db3.define_set("EMPTY-SET", "OWNER", "ITEM")
    db3.store("OWNER", name="lonely")
    empty_error = False
    try:
        db3.find_first("EMPTY-SET")
    except BachmanError:
        empty_error = True
    check("FIND FIRST on an empty set occurrence raises an error", empty_error)

    # 8. STORE a member with no current owner fails -- the set has nowhere
    #    to connect it. This is not a bug, it's the model's whole contract.
    db4 = Database()
    db4.define_set("ORPHAN-SET", "OWNER", "ITEM")
    unpositioned = False
    try:
        db4.store("ITEM", label="x")
    except BachmanError:
        unpositioned = True
    check("STORE ing a member with no current owner raises an error", unpositioned)

    # 9. GET reflects MODIFY on the current record.
    db.find_any("ORDER", item="Vacuum tube")
    db.modify(item="Vacuum tube (2 units)")
    check("MODIFY changes the fields GET returns",
          db.get()["item"] == "Vacuum tube (2 units)")

    # 10. Two owners keep two separate rings -- navigating one never
    #     touches the other's members.
    db5 = Database()
    db5.define_set("CUSTOMER-ORDERS", "CUSTOMER", "ORDER", order="FIFO")
    grace = db5.store("CUSTOMER", name="Grace")
    grace_order = db5.store("ORDER", item="Teletype")
    ada2 = db5.store("CUSTOMER", name="Ada")
    ada_order = db5.store("ORDER", item="Punched cards")
    db5.find_any("CUSTOMER", name="Ada")
    ada_first = db5.find_first("CUSTOMER-ORDERS")
    check("navigating Ada's set never returns Grace's order", ada_first is ada_order)
    db5.find_any("CUSTOMER", name="Grace")
    grace_first = db5.find_first("CUSTOMER-ORDERS")
    check("navigating Grace's set never returns Ada's order", grace_first is grace_order)

    # 11. FIND ANY with no match raises -- the one operation that has to scan.
    no_match = False
    try:
        db5.find_any("CUSTOMER", name="Nobody")
    except BachmanError:
        no_match = True
    check("FIND ANY with no matching record raises an error", no_match)

    # 12. The "before" scan and the "after" navigation agree on the answer,
    #     but the scan always pays for the whole file.
    matches, examined = db5.scan_for_members("ORDER", "item", "Teletype")
    check("flat-file scan finds the same record navigation would",
          matches == [grace_order])
    check("flat-file scan examines every order, not just the match",
          examined == len(db5.records_by_type["ORDER"]))

    print()
    print("%d/%d passed" % (passed, total))
    return passed == total


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    global VERBOSE
    args = sys.argv[1:]
    if "--test" in args:
        ok = run_tests()
        sys.exit(0 if ok else 1)
    if "--verbose" in args:
        VERBOSE = True
    files = [a for a in args if not a.startswith("--")]
    db = build_demo_database()
    if files:
        run_script(db, files[0], VERBOSE)
        return
    repl(db, VERBOSE)


if __name__ == "__main__":
    main()

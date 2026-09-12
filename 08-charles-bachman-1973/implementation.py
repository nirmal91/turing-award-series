"""
A navigational database, built the way Charles Bachman's Integrated Data
Store (IDS, General Electric, 1963-64) and its standardized descendant,
CODASYL's Data Base Task Group model (DBTG report, 1971), described one.

BEFORE this: connecting two kinds of records -- "which employees work in
the Sales department" -- meant scanning a whole file of EMPLOYEE records
and testing a department field on each one. scan_linear() below does
exactly that: it is O(n) in the number of records of that type, every
single time, no matter how many times you ask the same question.

AFTER this: the relationship itself is stored, once, as a ring of
pointers -- a SET occurrence, in Bachman's terminology (nothing to do with
the mathematical set). One OWNER record (a DEPARTMENT), a chain of MEMBER
records (its EMPLOYEEs), the last member's pointer closing the ring back
to the owner. Finding "the next employee in this department" is one
pointer-follow. Finding "which department owns this employee" is also one
pointer-follow, because every member also keeps a direct pointer back to
its current owner. Neither operation re-reads anything.

The program does not describe *what* it wants and let the system search
for it -- there is no query language here. It keeps a CURRENCY INDICATOR,
"which record am I standing on right now, in this set," and moves that
position one link at a time: FIND FIRST, FIND NEXT, FIND OWNER. Bachman's
1973 Turing Award lecture named this "The Programmer as Navigator" --
and it is also exactly the style of programming that E. F. Codd's
relational model (1970) was proposed to replace with declarative queries.

This file also gives a record type more than one owner. An EMPLOYEE here
is a member of DEPT-EMP (its department's set) AND of PROJ-EMP (its
project's set), two independent rings through the SAME record, at the
same time. That is the "network" in "network data model": a hierarchical
system (like IBM's contemporary IMS) allows a record only one parent, so
an employee shared between a department and a project would have to be
either duplicated or force-fit under just one of them. Here it is neither.

Pipeline:
    record / set   (schema: record types, and named owner->member rings)
        -> store        create a record instance
        -> connect      splice a record into a set occurrence's ring
        -> find first/next/prior/owner   move the currency indicator
        -> printed result

Run:
    python3 implementation.py                # interactive REPL
    python3 implementation.py company.ids     # load and run a schema+data script
    python3 implementation.py --test          # self-test suite
    python3 implementation.py --verbose       # REPL that prints every pointer update
"""

import sys

VERBOSE = False


# -- The schema: record types and set types -----------------------------------
#
# A record type is just a name plus a list of field names -- a struct
# definition. A set type is a named 1:N relationship: one owner record
# type, one member record type. (The real DBTG standard allows several
# member record types per set; this keeps one, to keep the ring logic
# readable -- nothing about the pointer-chasing idea depends on that.)

class RecordType:
    def __init__(self, name, fields):
        self.name = name
        self.fields = fields


class SetType:
    def __init__(self, name, owner_type, member_type):
        self.name = name
        self.owner_type = owner_type
        self.member_type = member_type


# -- A record instance ---------------------------------------------------------
#
# Every record carries, per set type it takes part in, up to three
# pointers: the next record in that set's ring, the prior record in that
# ring, and (for members only) a direct pointer straight back to its
# current owner. That third pointer is what makes FIND OWNER free -- an
# implementation choice IDS made precisely so "who owns this?" never has
# to walk a whole ring to find out.

class Record:
    def __init__(self, kind, key, fields):
        self.kind = kind
        self.key = key
        self.fields = fields
        self.ring_next = {}     # set_name -> next Record in that ring
        self.ring_prior = {}    # set_name -> prior Record in that ring
        self.owner_of = {}      # set_name -> the Record that owns this one

    def __repr__(self):
        pairs = ", ".join("%s=%s" % kv for kv in sorted(self.fields.items()))
        return "%s %s(%s)" % (self.key, self.kind, pairs)


# -- The database: schema + records + currency indicators ---------------------

class Database:
    def __init__(self):
        self.record_types = {}   # name -> RecordType
        self.set_types = {}      # name -> SetType
        self.records = {}        # key -> Record
        self.next_seq = {}       # record type name -> next sequence number

        # Currency indicators -- the DBTG's "where am I" state. A real
        # CODASYL system keeps one of each per record type and per set
        # type; a run-unit-wide "last record touched of any kind" too.
        self.current_run_unit = None          # key of the last record touched
        self.current_of_type = {}             # record type name -> key
        self.current_of_set = {}              # set type name -> key

    # -- schema definition --------------------------------------------------

    def define_record_type(self, name, fields):
        self.record_types[name] = RecordType(name, fields)
        self.next_seq[name] = 0

    def define_set_type(self, name, owner_type, member_type):
        if owner_type not in self.record_types:
            raise ValueError("unknown record type: %s" % owner_type)
        if member_type not in self.record_types:
            raise ValueError("unknown record type: %s" % member_type)
        self.set_types[name] = SetType(name, owner_type, member_type)

    # -- currency bookkeeping ------------------------------------------------

    def _touch(self, record):
        """Every DML statement that lands on a record updates the currency
        indicators for it: current of the whole run unit, current of its
        record type. (Current of set is updated by the set-aware
        operations themselves, since it depends on which set moved.)"""
        self.current_run_unit = record.key
        self.current_of_type[record.kind] = record.key

    # -- STORE: create a record instance -------------------------------------

    def store(self, kind, fields):
        if kind not in self.record_types:
            raise ValueError("unknown record type: %s" % kind)
        record_type = self.record_types[kind]
        for field in fields:
            if field not in record_type.fields:
                raise ValueError("%s has no field '%s'" % (kind, field))
        self.next_seq[kind] += 1
        key = "%s-%d" % (kind, self.next_seq[kind])
        record = Record(kind, key, dict(fields))
        self.records[key] = record

        # If this record type owns any set types, its ring for each of
        # them starts as a self-loop -- an owner with no members yet.
        for set_type in self.set_types.values():
            if set_type.owner_type == kind:
                record.ring_next[set_type.name] = record
                record.ring_prior[set_type.name] = record

        self._touch(record)
        if VERBOSE:
            print("  stored %s" % record)
        return record

    # -- CONNECT / DISCONNECT: splice a member into an owner's ring ---------

    def connect(self, set_name, owner_key, member_key):
        set_type = self._set_type(set_name)
        owner = self._record(owner_key)
        member = self._record(member_key)
        if owner.kind != set_type.owner_type:
            raise ValueError("%s is not an owner of %s" % (owner_key, set_name))
        if member.kind != set_type.member_type:
            raise ValueError("%s is not a member of %s" % (member_key, set_name))
        if member.owner_of.get(set_name) is not None:
            raise ValueError(
                "%s is already connected in %s -- disconnect first"
                % (member_key, set_name))

        # Insert MEMBER at the end of the ring: splice it in between the
        # current last record and the owner. A brand-new set occurrence
        # has owner.ring_prior[set_name] == owner itself, so the very
        # first CONNECT splices member between the owner and itself --
        # which is exactly "insert right after the owner."
        last = owner.ring_prior[set_name]
        last.ring_next[set_name] = member
        member.ring_prior[set_name] = last
        member.ring_next[set_name] = owner
        owner.ring_prior[set_name] = member
        member.owner_of[set_name] = owner

        self.current_of_set[set_name] = member.key
        self._touch(member)
        if VERBOSE:
            print("  connected %s into %s owned by %s"
                  % (member_key, set_name, owner_key))

    def disconnect(self, set_name, member_key):
        set_type = self._set_type(set_name)
        member = self._record(member_key)
        owner = member.owner_of.get(set_name)
        if owner is None:
            raise ValueError("%s is not connected in %s" % (member_key, set_name))

        before = member.ring_prior[set_name]
        after = member.ring_next[set_name]
        before.ring_next[set_name] = after
        after.ring_prior[set_name] = before
        del member.ring_next[set_name]
        del member.ring_prior[set_name]
        member.owner_of[set_name] = None

        if self.current_of_set.get(set_name) == member_key:
            self.current_of_set[set_name] = None
        self._touch(member)
        if VERBOSE:
            print("  disconnected %s from %s" % (member_key, set_name))

    # -- FIND: move the currency indicator along a ring ----------------------

    def find_first(self, set_name, owner_key):
        set_type = self._set_type(set_name)
        owner = self._record(owner_key)
        first = owner.ring_next[set_name]
        if first is owner:
            self.current_of_set[set_name] = owner_key
            if VERBOSE:
                print("  FIND FIRST %s WITHIN %s: set is empty" % (set_type.member_type, set_name))
            return None
        self.current_of_set[set_name] = first.key
        self._touch(first)
        return first

    def find_next(self, set_name):
        set_type = self._set_type(set_name)
        current_key = self.current_of_set.get(set_name)
        if current_key is None:
            raise ValueError(
                "no current of set %s -- FIND FIRST there before FIND NEXT" % set_name)
        current = self._record(current_key)
        candidate = current.ring_next[set_name]
        if candidate.kind == set_type.owner_type:
            if VERBOSE:
                print("  FIND NEXT %s: end of set, back at owner %s" % (set_name, candidate.key))
            return None
        self.current_of_set[set_name] = candidate.key
        self._touch(candidate)
        return candidate

    def find_prior(self, set_name):
        set_type = self._set_type(set_name)
        current_key = self.current_of_set.get(set_name)
        if current_key is None:
            raise ValueError(
                "no current of set %s -- FIND FIRST there before FIND PRIOR" % set_name)
        current = self._record(current_key)
        candidate = current.ring_prior[set_name]
        if candidate.kind == set_type.owner_type:
            if VERBOSE:
                print("  FIND PRIOR %s: start of set, at owner %s" % (set_name, candidate.key))
            return None
        self.current_of_set[set_name] = candidate.key
        self._touch(candidate)
        return candidate

    def find_owner(self, set_name):
        set_type = self._set_type(set_name)
        current_key = self.current_run_unit
        if current_key is None:
            raise ValueError("no current record of run-unit yet")
        current = self._record(current_key)
        owner = current.owner_of.get(set_name)
        if owner is None:
            raise ValueError(
                "%s is not currently a member of %s" % (current_key, set_name))
        self.current_of_set[set_name] = owner.key
        self._touch(owner)
        return owner

    # -- the "before": a linear scan, no stored relationship at all ---------

    def scan_linear(self, kind, field, value):
        """What you had to do before sets existed: read every record of a
        type and test a field on each one. No pointer helps here -- there
        is nothing stored except the flat file of records."""
        matches = []
        for record in self.records.values():
            if record.kind == kind and str(record.fields.get(field)) == str(value):
                matches.append(record)
        if VERBOSE:
            print("  scanned %d %s record(s) to find %d match(es)"
                  % (sum(1 for r in self.records.values() if r.kind == kind),
                     kind, len(matches)))
        return matches

    # -- lookups --------------------------------------------------------------

    def _record(self, key):
        if key not in self.records:
            raise ValueError("no such record: %s" % key)
        return self.records[key]

    def _set_type(self, name):
        if name not in self.set_types:
            raise ValueError("unknown set type: %s" % name)
        return self.set_types[name]


# -- REPL / script commands ----------------------------------------------------

BANNER = """Bachman's navigational database (IDS / CODASYL network model, 1963-71).
Schema commands:
  record TYPE field1 field2 ...        define a record type
  set NAME owner TYPE member TYPE      define a set type (a named ring)
Data commands:
  store TYPE field=value field=value   create a record, prints its key
  connect SET OWNERKEY MEMBERKEY       splice a member into an owner's ring
  disconnect SET MEMBERKEY             remove a member from its ring
Navigation commands (move the currency indicator):
  find first SET OWNERKEY              first member of that set occurrence
  find next SET                        next member, from current position
  find prior SET                       prior member, from current position
  find owner SET                       owner of the current record, within SET
Other:
  scan TYPE field=value                the "before": linear scan, no pointers
  show                                  print schema, records, and currency
  help                                  show this again
Ctrl-D to quit."""


def parse_kv(token):
    if "=" not in token:
        raise ValueError("expected field=value, got '%s'" % token)
    field, value = token.split("=", 1)
    return field, value


def format_record(record):
    return repr(record) if record is not None else "(none)"


def do_command(line, db):
    parts = line.split()
    if len(parts) == 0:
        return
    cmd = parts[0]

    if cmd == "record" and len(parts) >= 2:
        name = parts[1]
        fields = parts[2:]
        db.define_record_type(name, fields)
        print("defined record type %s(%s)" % (name, ", ".join(fields)))

    elif cmd == "set" and len(parts) == 6 and parts[2] == "owner" and parts[4] == "member":
        name, owner_type, member_type = parts[1], parts[3], parts[5]
        db.define_set_type(name, owner_type, member_type)
        print("defined set type %s: %s owns %s" % (name, owner_type, member_type))

    elif cmd == "store" and len(parts) >= 2:
        kind = parts[1]
        fields = dict(parse_kv(tok) for tok in parts[2:])
        record = db.store(kind, fields)
        print("stored %s" % record)

    elif cmd == "connect" and len(parts) == 4:
        set_name, owner_key, member_key = parts[1], parts[2], parts[3]
        db.connect(set_name, owner_key, member_key)
        print("connected %s into %s owned by %s" % (member_key, set_name, owner_key))

    elif cmd == "disconnect" and len(parts) == 3:
        set_name, member_key = parts[1], parts[2]
        db.disconnect(set_name, member_key)
        print("disconnected %s from %s" % (member_key, set_name))

    elif cmd == "find" and len(parts) >= 3 and parts[1] == "first":
        set_name, owner_key = parts[2], parts[3]
        record = db.find_first(set_name, owner_key)
        print("  " + ("(empty set)" if record is None else format_record(record)))

    elif cmd == "find" and len(parts) == 3 and parts[1] == "next":
        record = db.find_next(parts[2])
        print("  " + ("(end of set)" if record is None else format_record(record)))

    elif cmd == "find" and len(parts) == 3 and parts[1] == "prior":
        record = db.find_prior(parts[2])
        print("  " + ("(start of set)" if record is None else format_record(record)))

    elif cmd == "find" and len(parts) == 3 and parts[1] == "owner":
        record = db.find_owner(parts[2])
        print("  " + format_record(record))

    elif cmd == "scan" and len(parts) == 3:
        kind = parts[1]
        field, value = parse_kv(parts[2])
        matches = db.scan_linear(kind, field, value)
        if len(matches) == 0:
            print("  (no matches)")
        for record in matches:
            print("  " + format_record(record))

    elif cmd == "show":
        print("record types:")
        for rt in db.record_types.values():
            print("  %s(%s)" % (rt.name, ", ".join(rt.fields)))
        print("set types:")
        for st in db.set_types.values():
            print("  %s: %s owns %s" % (st.name, st.owner_type, st.member_type))
        print("records:")
        for key in sorted(db.records, key=lambda k: (db.records[k].kind, k)):
            print("  " + format_record(db.records[key]))
        print("currency:")
        print("  run-unit: %s" % db.current_run_unit)
        print("  of type: %s" % db.current_of_type)
        print("  of set: %s" % db.current_of_set)

    elif cmd == "help":
        print(BANNER)

    else:
        print("unknown command: %s (try 'help')" % line)


def repl():
    db = Database()
    print(BANNER)
    while True:
        try:
            line = input("navigator> ")
        except EOFError:
            print()
            return
        if line.strip() == "":
            continue
        try:
            do_command(line.strip(), db)
        except ValueError as err:
            print("error: %s" % err)


def run_file(path):
    """Load and run a schema+data script: one command per line, '#' starts
    a comment. Each command is echoed before it runs, the same as typing
    it into the REPL by hand."""
    db = Database()
    with open(path) as source_file:
        lines = source_file.readlines()
    for raw_line in lines:
        line = raw_line.split("#")[0].strip()
        if line == "":
            continue
        print("navigator> " + line)
        try:
            do_command(line, db)
        except ValueError as err:
            print("error: %s" % err)


# -- Self-test suite -----------------------------------------------------------

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

    def fresh_db():
        db = Database()
        db.define_record_type("DEPARTMENT", ["name"])
        db.define_record_type("EMPLOYEE", ["name"])
        db.define_record_type("PROJECT", ["name"])
        db.define_set_type("DEPT-EMP", "DEPARTMENT", "EMPLOYEE")
        db.define_set_type("PROJ-EMP", "PROJECT", "EMPLOYEE")
        return db

    # 1. Storing a record assigns a sequential key and current-of-type.
    db = fresh_db()
    sales = db.store("DEPARTMENT", {"name": "Sales"})
    check("first DEPARTMENT gets key DEPARTMENT-1", sales.key == "DEPARTMENT-1")
    check("current of type DEPARTMENT is DEPARTMENT-1",
          db.current_of_type["DEPARTMENT"] == "DEPARTMENT-1")

    # 2. A brand-new owner's ring is a self-loop -- an empty set.
    check("new owner's ring points to itself (empty set)",
          sales.ring_next["DEPT-EMP"] is sales and sales.ring_prior["DEPT-EMP"] is sales)

    # 3. FIND FIRST on an empty set returns None.
    check("FIND FIRST on an empty set returns None",
          db.find_first("DEPT-EMP", "DEPARTMENT-1") is None)

    # 4. Connecting members builds a ring walkable with FIND FIRST/NEXT.
    db = fresh_db()
    sales = db.store("DEPARTMENT", {"name": "Sales"})
    alice = db.store("EMPLOYEE", {"name": "Alice"})
    bob = db.store("EMPLOYEE", {"name": "Bob"})
    carol = db.store("EMPLOYEE", {"name": "Carol"})
    db.connect("DEPT-EMP", sales.key, alice.key)
    db.connect("DEPT-EMP", sales.key, bob.key)
    db.connect("DEPT-EMP", sales.key, carol.key)
    seen = []
    record = db.find_first("DEPT-EMP", sales.key)
    while record is not None:
        seen.append(record.key)
        record = db.find_next("DEPT-EMP")
    check("walking the ring visits all three members in connect order",
          seen == ["EMPLOYEE-1", "EMPLOYEE-2", "EMPLOYEE-3"])

    # 5. FIND NEXT past the last member reports end-of-set (None), and
    #    does not silently wrap back to the first member.
    check("FIND NEXT past the last member is None (end of set)",
          db.find_next("DEPT-EMP") is None)

    # 6. FIND PRIOR walks the ring backward from the last valid position.
    db.find_first("DEPT-EMP", sales.key)
    db.find_next("DEPT-EMP")
    db.find_next("DEPT-EMP")   # currency is now on Carol
    prior = db.find_prior("DEPT-EMP")
    check("FIND PRIOR from Carol lands on Bob", prior.key == "EMPLOYEE-2")

    # 7. FIND PRIOR past the first member reports start-of-set (None).
    db.find_first("DEPT-EMP", sales.key)
    check("FIND PRIOR before the first member is None (start of set)",
          db.find_prior("DEPT-EMP") is None)

    # 8. FIND OWNER is a direct pointer -- works from any member, no walk.
    db.find_first("DEPT-EMP", sales.key)
    db.find_next("DEPT-EMP")
    db.find_next("DEPT-EMP")   # currency of run-unit is now Carol
    owner = db.find_owner("DEPT-EMP")
    check("FIND OWNER from Carol returns the department", owner.key == sales.key)

    # 9. The network property: one EMPLOYEE record is a member of TWO
    #    independent sets at once (its department AND its project) --
    #    something a strict one-parent hierarchy cannot do without
    #    duplicating the record.
    db = fresh_db()
    sales = db.store("DEPARTMENT", {"name": "Sales"})
    launch = db.store("PROJECT", {"name": "Launch"})
    alice = db.store("EMPLOYEE", {"name": "Alice"})
    db.connect("DEPT-EMP", sales.key, alice.key)
    db.connect("PROJ-EMP", launch.key, alice.key)
    check("Alice's department owner is Sales",
          alice.owner_of["DEPT-EMP"].key == sales.key)
    check("the SAME Alice record's project owner is Launch",
          alice.owner_of["PROJ-EMP"].key == launch.key)

    # 10. Connecting an already-connected member to the same set type
    #     without disconnecting first is rejected.
    raised = False
    try:
        db.connect("DEPT-EMP", sales.key, alice.key)
    except ValueError:
        raised = True
    check("re-connecting an already-connected member raises an error", raised)

    # 11. DISCONNECT removes a member and repairs the ring around it.
    db = fresh_db()
    sales = db.store("DEPARTMENT", {"name": "Sales"})
    alice = db.store("EMPLOYEE", {"name": "Alice"})
    bob = db.store("EMPLOYEE", {"name": "Bob"})
    carol = db.store("EMPLOYEE", {"name": "Carol"})
    db.connect("DEPT-EMP", sales.key, alice.key)
    db.connect("DEPT-EMP", sales.key, bob.key)
    db.connect("DEPT-EMP", sales.key, carol.key)
    db.disconnect("DEPT-EMP", bob.key)
    seen = []
    record = db.find_first("DEPT-EMP", sales.key)
    while record is not None:
        seen.append(record.key)
        record = db.find_next("DEPT-EMP")
    check("disconnecting Bob leaves Alice and Carol correctly linked",
          seen == ["EMPLOYEE-1", "EMPLOYEE-3"])
    check("Bob no longer has an owner in DEPT-EMP", bob.owner_of["DEPT-EMP"] is None)

    # 12. A disconnected member can be reconnected (e.g. to a different
    #     owner), since owner_of was cleared.
    hr = db.store("DEPARTMENT", {"name": "HR"})
    db.connect("DEPT-EMP", hr.key, bob.key)
    check("Bob can be reconnected to a different department after disconnect",
          bob.owner_of["DEPT-EMP"].key == hr.key)

    # 13. scan_linear (the "before") finds the same records that the ring
    #     finds, on a case where every employee happens to share a set.
    db = fresh_db()
    sales = db.store("DEPARTMENT", {"name": "Sales"})
    alice = db.store("EMPLOYEE", {"name": "Alice"})
    bob = db.store("EMPLOYEE", {"name": "Bob"})
    db.connect("DEPT-EMP", sales.key, alice.key)
    db.connect("DEPT-EMP", sales.key, bob.key)
    matches = db.scan_linear("EMPLOYEE", "name", "Bob")
    check("linear scan finds Bob by field value", len(matches) == 1 and matches[0].key == bob.key)

    # 14. STORE rejects a field the record type does not have.
    raised = False
    try:
        db.store("EMPLOYEE", {"salary": "1"})
    except ValueError:
        raised = True
    check("storing an undefined field raises an error", raised)

    print()
    print("%d/%d passed" % (passed, total))
    return passed == total


# -- Entry point ----------------------------------------------------------------

def main():
    global VERBOSE
    args = sys.argv[1:]
    if "--test" in args:
        ok = run_tests()
        sys.exit(0 if ok else 1)
    if "--verbose" in args:
        VERBOSE = True
        print("(verbose mode: every store/connect/find prints its pointer update)\n")
    files = [a for a in args if not a.startswith("--")]
    if len(files) > 0:
        run_file(files[0])
        return
    repl()


if __name__ == "__main__":
    main()

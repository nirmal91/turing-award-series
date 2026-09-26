"""
Charles Bachman's Integrated Data Store (IDS), General Electric, running by
1963 -- the first widely used database management system. Bachman's design
became the basis for the CODASYL Data Base Task Group's 1969 "network data
model", the industry standard before the relational model displaced it in
the 1980s. Bachman's 1973 Turing lecture was titled "The Programmer as
Navigator" -- and that title is the whole idea. There is no query language
here. You do not describe WHAT you want and let the system figure out how
to get it (that is Codd's relational idea, six years later). You describe
HOW to walk there: store a record, connect it into a ring, follow the ring.

BEFORE this: mid-1960s business applications each kept their own flat
files. Payroll had an employee file. Personnel had a different employee
file with overlapping fields. Every program duplicated data and wrote its
own file-handling code, because there was no shared structure for "an
employee" that multiple programs could navigate.

AFTER this: one shared structure. A RECORD is a typed bundle of fields
(an EMPLOYEE, a DEPARTMENT). A SET is a named 1-to-many relationship
between an OWNER record type and a MEMBER record type (DEPARTMENT owns
EMPLOYEE). A set OCCURRENCE is physically a ring: the owner points to its
first member, each member points to the next, and the last member points
back to the owner. CONNECT splices a record into that ring. FIND OWNER,
FIND FIRST, and FIND NEXT are the only ways to move -- there is no scan,
no join, no WHERE clause. And critically, a record can be a MEMBER of
several different sets at once (an employee belongs to a department set
AND a project set) -- so the structure is a network of rings, not a
single tree. That is why CODASYL called it the network data model, and
why it could represent relationships IBM's hierarchical IMS could not.

Pipeline:
    DEFINE SET (declare an owner/member relationship)
        -> STORE (create records)
        -> CONNECT (splice a record into a set's ring)
        -> FIND FIRST / FIND NEXT / FIND OWNER (navigate the ring)
        -> currency indicators track "where you are" between commands

Run:
    python3 implementation.py                # interactive REPL
    python3 implementation.py schema.ids      # load and run a script
    python3 implementation.py --test          # self-test suite
    python3 implementation.py --verbose       # REPL that prints ring internals
"""

import sys

VERBOSE = False


# ── The database ─────────────────────────────────────────────────────────────
#
# Everything IDS/CODASYL needed lives in four small dictionaries. There is no
# table, no index, no query planner -- just records, ring pointers, and a
# notion of "where the program currently is" in each set (currency).

class Database:
    def __init__(self):
        self.records = {}            # record id -> {"kind": str, "fields": dict}
        self.counters = {}           # kind -> next auto-id number
        self.set_types = {}          # set name -> (owner_kind, member_kind)
        self.ring_next = {}          # (set_name, node_id) -> next node id in the ring
        self.owner_of = {}           # (set_name, node_id) -> the owner id of its ring

        # Currency indicators: DBTG's term for "what the program is
        # positioned at right now." Every STORE and every successful FIND
        # updates these, and CONNECT/DISCONNECT/PRINT can use them so you
        # rarely have to type a record id by hand.
        self.current_run_unit = None       # last record touched, of any kind
        self.current_of_record_type = {}   # kind -> last record id of that kind
        self.current_of_set = {}           # set name -> last record id touched in that set

    # -- schema --------------------------------------------------------------

    def define_set(self, set_name, owner_kind, member_kind):
        if set_name in self.set_types:
            raise ValueError("set %r is already defined" % set_name)
        self.set_types[set_name] = (owner_kind, member_kind)

    # -- records ---------------------------------------------------------------

    def store(self, kind, fields):
        n = self.counters.get(kind, 0) + 1
        self.counters[kind] = n
        record_id = "%s#%d" % (kind, n)
        self.records[record_id] = {"kind": kind, "fields": fields}
        self._touch(record_id)
        return record_id

    def _touch(self, record_id):
        """Update currency indicators after STORE or a successful FIND."""
        kind = self.records[record_id]["kind"]
        self.current_run_unit = record_id
        self.current_of_record_type[kind] = record_id

    # -- sets: CONNECT and the ring ---------------------------------------------

    def connect(self, set_name, owner_id, member_id):
        if set_name not in self.set_types:
            raise ValueError("no such set: %r" % set_name)
        owner_kind, member_kind = self.set_types[set_name]
        if self.records[owner_id]["kind"] != owner_kind:
            raise ValueError("%r is not a %s, cannot own set %r" % (owner_id, owner_kind, set_name))
        if self.records[member_id]["kind"] != member_kind:
            raise ValueError("%r is not a %s, cannot join set %r" % (member_id, member_kind, set_name))

        key = (set_name, owner_id)
        if key not in self.ring_next:
            # First member: owner -> member -> owner (ring of one).
            self.ring_next[key] = member_id
            self.ring_next[(set_name, member_id)] = owner_id
        else:
            # Walk from the owner to find the current tail (the node whose
            # "next" is the owner), then splice the new member in before it.
            tail = owner_id
            while self.ring_next[(set_name, tail)] != owner_id:
                tail = self.ring_next[(set_name, tail)]
            self.ring_next[(set_name, tail)] = member_id
            self.ring_next[(set_name, member_id)] = owner_id

        self.owner_of[(set_name, owner_id)] = owner_id
        self.owner_of[(set_name, member_id)] = owner_id
        self.current_of_set[set_name] = member_id
        self._touch(member_id)

    def disconnect(self, set_name, member_id):
        key = (set_name, member_id)
        if key not in self.owner_of:
            raise ValueError("%r is not currently a member of set %r" % (member_id, set_name))
        owner_id = self.owner_of[key]

        # Find the predecessor (owner or member) whose "next" is member_id.
        pred = owner_id
        while self.ring_next[(set_name, pred)] != member_id:
            pred = self.ring_next[(set_name, pred)]

        self.ring_next[(set_name, pred)] = self.ring_next[(set_name, member_id)]
        del self.ring_next[(set_name, member_id)]
        del self.owner_of[(set_name, member_id)]

    # -- navigation: FIND FIRST / FIND NEXT / FIND OWNER ------------------------

    def _ring_step(self, set_name, node_id):
        """Advance one pointer around the ring from node_id. Returns
        (next_id, wrapped) where wrapped is True if next_id closes the ring
        back to the owner. Returns None if node_id has no ring at all
        (an owner nothing has ever been CONNECTed to)."""
        key = (set_name, node_id)
        if key not in self.ring_next:
            return None
        next_id = self.ring_next[key]
        owner_id = self.owner_of.get((set_name, node_id), node_id)
        wrapped = (next_id == owner_id)
        return next_id, wrapped

    def find_first(self, set_name, owner_id):
        step = self._ring_step(set_name, owner_id)
        if step is None:
            return None
        first_id, wrapped = step
        if wrapped:
            return None   # ring with nothing but the owner: an empty set
        self.current_of_set[set_name] = first_id
        self._touch(first_id)
        return first_id

    def find_next(self, set_name):
        current = self.current_of_set.get(set_name)
        if current is None:
            raise ValueError("not currently positioned in set %r (FIND FIRST first)" % set_name)
        step = self._ring_step(set_name, current)
        if step is None:
            raise ValueError("no ring for set %r" % set_name)
        next_id, wrapped = step
        if wrapped:
            self.current_of_set[set_name] = next_id   # positioned back at the owner
            return None
        self.current_of_set[set_name] = next_id
        self._touch(next_id)
        return next_id

    def find_owner(self, set_name):
        current = self.current_of_set.get(set_name)
        if current is None:
            current = self.current_run_unit
        key = (set_name, current)
        if key not in self.owner_of:
            raise ValueError("%r is not a member of set %r" % (current, set_name))
        owner_id = self.owner_of[key]
        self.current_of_set[set_name] = owner_id
        self._touch(owner_id)
        return owner_id

    def members_of(self, set_name, owner_id):
        """Not part of the historical DML (there was no 'list all
        members' verb) -- purely a convenience for DUMP and --verbose."""
        result = []
        step = self._ring_step(set_name, owner_id)
        while step is not None:
            next_id, wrapped = step
            if wrapped:
                break
            result.append(next_id)
            step = self._ring_step(set_name, next_id)
        return result


# ── DML command interpreter ──────────────────────────────────────────────────

BANNER = """Bachman's navigational database (IDS / CODASYL DBTG style, 1963-1969).
Commands:
  DEFINE SET name OWNER kind MEMBER kind   declare a 1-to-many set type
  STORE kind field=value ...               create a record (becomes current)
  CONNECT name                             connect current owner + current member
  CONNECT name OWNER id MEMBER id          connect two specific records
  FIND FIRST name [OWNER id]               go to the first member of a set
  FIND NEXT name                           advance to the next member
  FIND OWNER name                          jump from a member to its owner
  DISCONNECT name [MEMBER id]              remove a member from a set's ring
  PRINT CURRENT | PRINT id | PRINT ALL kind
  DUMP                                     show every record and every ring
  help                                     show this again
Ctrl-D to quit."""


def format_record(db, record_id):
    if record_id is None:
        return "(none)"
    rec = db.records[record_id]
    return "%s %s" % (record_id, rec["fields"])


def do_command(line, db):
    tokens = line.split()
    if len(tokens) == 0:
        return
    cmd = tokens[0].upper()

    if cmd == "DEFINE" and len(tokens) == 7 and tokens[1].upper() == "SET" \
            and tokens[3].upper() == "OWNER" and tokens[5].upper() == "MEMBER":
        set_name, owner_kind, member_kind = tokens[2], tokens[4], tokens[6]
        db.define_set(set_name, owner_kind, member_kind)
        print("defined set %s: %s owns %s" % (set_name, owner_kind, member_kind))

    elif cmd == "STORE" and len(tokens) >= 2:
        kind = tokens[1]
        fields = {}
        for token in tokens[2:]:
            if "=" not in token:
                raise ValueError("bad field %r, expected key=value" % token)
            key, value = token.split("=", 1)
            fields[key] = value
        record_id = db.store(kind, fields)
        print("stored %s" % format_record(db, record_id))
        if VERBOSE:
            print("  (current run unit is now %s)" % record_id)

    elif cmd == "CONNECT" and len(tokens) == 2:
        set_name = tokens[1]
        owner_kind, member_kind = db.set_types.get(set_name, (None, None))
        if owner_kind is None:
            raise ValueError("no such set: %r" % set_name)
        owner_id = db.current_of_record_type.get(owner_kind)
        member_id = db.current_of_record_type.get(member_kind)
        if owner_id is None or member_id is None:
            raise ValueError("need a current %s and a current %s to CONNECT implicitly"
                              % (owner_kind, member_kind))
        db.connect(set_name, owner_id, member_id)
        print("connected %s -> %s into set %s" % (owner_id, member_id, set_name))

    elif cmd == "CONNECT" and len(tokens) == 6 and tokens[2].upper() == "OWNER" \
            and tokens[4].upper() == "MEMBER":
        set_name, owner_id, member_id = tokens[1], tokens[3], tokens[5]
        db.connect(set_name, owner_id, member_id)
        print("connected %s -> %s into set %s" % (owner_id, member_id, set_name))

    elif cmd == "FIND" and len(tokens) >= 2 and tokens[1].upper() == "FIRST":
        set_name = tokens[2]
        if len(tokens) == 5 and tokens[3].upper() == "OWNER":
            owner_id = tokens[4]
        else:
            owner_kind = db.set_types[set_name][0]
            owner_id = db.current_of_record_type.get(owner_kind)
            if owner_id is None:
                raise ValueError("no current %s to use as owner" % owner_kind)
        result = db.find_first(set_name, owner_id)
        if result is None:
            print("(empty set: %s has no members in %s)" % (owner_id, set_name))
        else:
            print(format_record(db, result))

    elif cmd == "FIND" and len(tokens) == 3 and tokens[1].upper() == "NEXT":
        set_name = tokens[2]
        result = db.find_next(set_name)
        if result is None:
            owner_id = db.current_of_set[set_name]
            print("(end of set %s -- back at owner %s)" % (set_name, owner_id))
        else:
            print(format_record(db, result))

    elif cmd == "FIND" and len(tokens) == 3 and tokens[1].upper() == "OWNER":
        set_name = tokens[2]
        owner_id = db.find_owner(set_name)
        print(format_record(db, owner_id))

    elif cmd == "DISCONNECT" and len(tokens) == 2:
        set_name = tokens[1]
        member_kind = db.set_types[set_name][1]
        member_id = db.current_of_record_type.get(member_kind)
        if member_id is None:
            raise ValueError("no current %s to disconnect" % member_kind)
        db.disconnect(set_name, member_id)
        print("disconnected %s from set %s" % (member_id, set_name))

    elif cmd == "DISCONNECT" and len(tokens) == 4 and tokens[2].upper() == "MEMBER":
        set_name, member_id = tokens[1], tokens[3]
        db.disconnect(set_name, member_id)
        print("disconnected %s from set %s" % (member_id, set_name))

    elif cmd == "PRINT" and len(tokens) == 2 and tokens[1].upper() == "CURRENT":
        print(format_record(db, db.current_run_unit))

    elif cmd == "PRINT" and len(tokens) == 3 and tokens[1].upper() == "ALL":
        kind = tokens[2]
        found = [rid for rid, rec in db.records.items() if rec["kind"] == kind]
        if len(found) == 0:
            print("  (no %s records)" % kind)
        for rid in found:
            print("  " + format_record(db, rid))

    elif cmd == "PRINT" and len(tokens) == 2:
        print(format_record(db, tokens[1]))

    elif cmd == "DUMP":
        print("records:")
        for rid in db.records:
            print("  " + format_record(db, rid))
        print("sets:")
        for set_name, (owner_kind, member_kind) in db.set_types.items():
            owners = [rid for rid, rec in db.records.items() if rec["kind"] == owner_kind]
            for owner_id in owners:
                members = db.members_of(set_name, owner_id)
                print("  %s: %s -> %s" % (set_name, owner_id, members))
        print("currency: run_unit=%s  of_record_type=%s  of_set=%s"
              % (db.current_run_unit, db.current_of_record_type, db.current_of_set))

    elif cmd == "HELP":
        print(BANNER)

    else:
        raise ValueError("unknown command: %s (try 'help')" % line)


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


def strip_comment(line):
    """Cut off a trailing '# comment', but only where '#' starts a word --
    record ids like EMPLOYEE#1 use '#' too, and must survive untouched."""
    index = line.find("#")
    while index != -1:
        if index == 0 or line[index - 1].isspace():
            return line[:index]
        index = line.find("#", index + 1)
    return line


def run_file(path):
    """Load and run a DML script: one command per line, '# comment' starts
    a comment (only when '#' begins a word, so record ids like EMPLOYEE#1
    are untouched). This is literally how IDS worked -- a batch COBOL job
    full of STORE/FIND/CONNECT statements, run against the shared store."""
    db = Database()
    with open(path) as source_file:
        lines = source_file.readlines()
    for raw_line in lines:
        line = strip_comment(raw_line).strip()
        if line == "":
            continue
        print("ids> " + line)
        try:
            do_command(line, db)
        except (ValueError, KeyError) as err:
            print("error: %s" % err)


# ── Self-test suite ──────────────────────────────────────────────────────────

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

    # 1. Defining a set registers the owner/member kinds.
    db = Database()
    db.define_set("DEPT-EMP", "DEPARTMENT", "EMPLOYEE")
    check("DEFINE SET registers owner/member kinds",
          db.set_types["DEPT-EMP"] == ("DEPARTMENT", "EMPLOYEE"))

    # 2. STORE creates a record with an auto-assigned id and makes it current.
    db = Database()
    eng = db.store("DEPARTMENT", {"name": "Engineering"})
    check("STORE assigns a readable id", eng == "DEPARTMENT#1")
    check("STORE makes the record current", db.current_run_unit == eng)

    # 3. CONNECT builds a one-member ring: owner -> member -> owner.
    db = Database()
    db.define_set("DEPT-EMP", "DEPARTMENT", "EMPLOYEE")
    eng = db.store("DEPARTMENT", {"name": "Engineering"})
    alice = db.store("EMPLOYEE", {"name": "Alice"})
    db.connect("DEPT-EMP", eng, alice)
    check("ring closes: owner -> member -> owner",
          db.ring_next[("DEPT-EMP", eng)] == alice and db.ring_next[("DEPT-EMP", alice)] == eng)

    # 4. FIND FIRST returns the first member connected.
    check("FIND FIRST returns the only member", db.find_first("DEPT-EMP", eng) == alice)

    # 5. FIND NEXT walks the ring in insertion order across several members.
    db = Database()
    db.define_set("DEPT-EMP", "DEPARTMENT", "EMPLOYEE")
    eng = db.store("DEPARTMENT", {"name": "Engineering"})
    alice = db.store("EMPLOYEE", {"name": "Alice"})
    db.connect("DEPT-EMP", eng, alice)
    bob = db.store("EMPLOYEE", {"name": "Bob"})
    db.connect("DEPT-EMP", eng, bob)
    carol = db.store("EMPLOYEE", {"name": "Carol"})
    db.connect("DEPT-EMP", eng, carol)
    db.find_first("DEPT-EMP", eng)
    order = [db.current_of_set["DEPT-EMP"]]
    order.append(db.find_next("DEPT-EMP"))
    order.append(db.find_next("DEPT-EMP"))
    check("FIND NEXT walks members in insertion order", order == [alice, bob, carol])

    # 6. FIND NEXT past the last member reports the wrap (end of set), not a crash.
    end = db.find_next("DEPT-EMP")
    check("FIND NEXT past the last member returns None (end of set)", end is None)
    check("currency after wrap is back at the owner", db.current_of_set["DEPT-EMP"] == eng)

    # 7. FIND OWNER from any member returns the department that owns it.
    db.find_first("DEPT-EMP", eng)
    db.find_next("DEPT-EMP")   # now positioned at bob
    check("FIND OWNER jumps from a member back to its owner", db.find_owner("DEPT-EMP") == eng)

    # 8. Two different owners of the same set TYPE keep separate rings.
    db = Database()
    db.define_set("DEPT-EMP", "DEPARTMENT", "EMPLOYEE")
    eng = db.store("DEPARTMENT", {"name": "Engineering"})
    sales = db.store("DEPARTMENT", {"name": "Sales"})
    alice = db.store("EMPLOYEE", {"name": "Alice"})
    db.connect("DEPT-EMP", eng, alice)
    dave = db.store("EMPLOYEE", {"name": "Dave"})
    db.connect("DEPT-EMP", sales, dave)
    check("Engineering's ring holds only Alice", db.members_of("DEPT-EMP", eng) == [alice])
    check("Sales's ring holds only Dave", db.members_of("DEPT-EMP", sales) == [dave])

    # 9. DISCONNECT removes a middle member and re-links the ring around it.
    db = Database()
    db.define_set("DEPT-EMP", "DEPARTMENT", "EMPLOYEE")
    eng = db.store("DEPARTMENT", {"name": "Engineering"})
    alice = db.store("EMPLOYEE", {"name": "Alice"})
    db.connect("DEPT-EMP", eng, alice)
    bob = db.store("EMPLOYEE", {"name": "Bob"})
    db.connect("DEPT-EMP", eng, bob)
    carol = db.store("EMPLOYEE", {"name": "Carol"})
    db.connect("DEPT-EMP", eng, carol)
    db.disconnect("DEPT-EMP", bob)
    check("DISCONNECT removes the member and re-links the ring",
          db.members_of("DEPT-EMP", eng) == [alice, carol])

    # 10. A record can be a MEMBER of two different set types at once --
    #     the network property that a strict tree (hierarchical model)
    #     cannot express. Alice reports to Engineering AND works on Compiler.
    db = Database()
    db.define_set("DEPT-EMP", "DEPARTMENT", "EMPLOYEE")
    db.define_set("PROJ-EMP", "PROJECT", "EMPLOYEE")
    eng = db.store("DEPARTMENT", {"name": "Engineering"})
    alice = db.store("EMPLOYEE", {"name": "Alice"})
    db.connect("DEPT-EMP", eng, alice)
    compiler = db.store("PROJECT", {"name": "Compiler"})
    db.current_of_record_type["EMPLOYEE"] = alice   # re-select Alice as current member
    db.connect("PROJ-EMP", compiler, alice)
    check("Alice is a member of the department set", db.find_owner("DEPT-EMP") == eng
          if db.current_of_set.get("DEPT-EMP") else True)
    check("Alice is ALSO a member of the project set (network, not a tree)",
          db.owner_of[("PROJ-EMP", alice)] == compiler and db.owner_of[("DEPT-EMP", alice)] == eng)

    # 11. Explicit CONNECT with named ids works the same as implicit currency.
    db = Database()
    db.define_set("DEPT-EMP", "DEPARTMENT", "EMPLOYEE")
    eng = db.store("DEPARTMENT", {"name": "Engineering"})
    alice = db.store("EMPLOYEE", {"name": "Alice"})
    db.connect("DEPT-EMP", owner_id=eng, member_id=alice)
    check("explicit CONNECT(owner_id=, member_id=) works", db.find_first("DEPT-EMP", eng) == alice)

    # 12. STORE gives unique ids even when field VALUES repeat.
    db = Database()
    a = db.store("EMPLOYEE", {"name": "Sam"})
    b = db.store("EMPLOYEE", {"name": "Sam"})
    check("duplicate field values still get distinct record ids", a != b)

    # 13. FIND NEXT with nothing current in that set raises, rather than
    #     silently returning garbage.
    db = Database()
    db.define_set("DEPT-EMP", "DEPARTMENT", "EMPLOYEE")
    raised = False
    try:
        db.find_next("DEPT-EMP")
    except ValueError:
        raised = True
    check("FIND NEXT with no currency in the set raises ValueError", raised)

    # 14. CONNECT against an undefined set name raises, rather than silently
    #     creating one -- schemas in DBTG were declared up front.
    db = Database()
    eng = db.store("DEPARTMENT", {"name": "Engineering"})
    alice = db.store("EMPLOYEE", {"name": "Alice"})
    raised = False
    try:
        db.connect("NO-SUCH-SET", eng, alice)
    except ValueError:
        raised = True
    check("CONNECT into an undefined set raises ValueError", raised)

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
        print("(verbose mode: STORE announces currency changes)\n")
    files = [a for a in args if not a.startswith("--")]
    if len(files) > 0:
        run_file(files[0])
        return
    repl()


if __name__ == "__main__":
    main()

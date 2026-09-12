"""
The network (CODASYL) data model, built the way Charles W. Bachman described it
in the Integrated Data Store (IDS, 1963) and the CODASYL Data Base Task Group
reports that grew out of it.

BEFORE this: business data lived in flat files, one file per application. To
answer "which employees are in Engineering?" a program read the ENTIRE employee
file and tested every record. Relationships between records lived only in the
programmer's code and were re-derived by scanning, every time. flat_file_scan()
below is that old world, kept so you can watch it examine every record while
navigation touches only the ones it needs.

AFTER this: the relationship is data the database stores, called a "set". A set
has one owner record and a chain of member records. The owner points to its
first member; each member points to the next (and back to the owner). To list a
department's employees you FIND the department, then FIND FIRST / FIND NEXT
WITHIN SET, hopping along the chain straight to exactly those employees. Bachman
called this "the programmer as navigator": you move through the data along the
links, one record at a time, instead of searching it. Many-to-many
relationships (students <-> courses) are modeled with a link record connected
into two sets at once -- something flat files could not do without duplicating
data.

Pipeline:
    store DEPT name=Engineering        -> a record gets a database key (id)
    connect WORKS_IN <dept> <emp>      -> splice the member into the owner's chain
        -> members WORKS_IN <dept>     FIND FIRST / NEXT WITHIN SET  (navigate down)
        -> owner   WORKS_IN <emp>      follow the owner pointer       (navigate up)

Run:
    python3 implementation.py                # interactive REPL (a small demo DB)
    python3 implementation.py practice.ids   # load and run a schema/data script
    python3 implementation.py --test         # self-test suite (16 cases)
    python3 implementation.py --verbose      # REPL that prints every pointer hop
"""

import sys

VERBOSE = False


# ── The database ─────────────────────────────────────────────────────────────
#
# A record is a dict of fields plus a type and an id. The structure between
# records lives in "set types" (a declared owner-type -> member-type
# relationship) and the pointer chains that implement each set instance.
#
# IDS stored, per set, a pointer from the owner to its first member and a "next"
# pointer in each member. We keep the same three pointers explicitly so that
# navigation here is genuinely pointer-following, not a table lookup:
#   first_member[set][owner_id]   -> the owner's first member, or None
#   next_member[set][member_id]   -> the member after this one, or None
#   owner_of[set][member_id]      -> the owner this member hangs under
# Real IDS used circular chains (the last member points back to the owner); we
# use None-terminated chains, which navigate identically and read more simply.

class Database:
    def __init__(self):
        self.record_types = {}     # type name -> list of field names (the schema)
        self.set_types = {}        # set name -> (owner_type, member_type)
        self.records = {}          # id -> {"_type":..., "_id":..., fields...}
        self.next_id = 1

        self.first_member = {}     # set name -> {owner_id: first member id or None}
        self.next_member = {}      # set name -> {member_id: next member id or None}
        self.owner_of = {}         # set name -> {member_id: owner id}

    # ── schema ────────────────────────────────────────────────────────────

    def add_record_type(self, name, fields):
        self.record_types[name] = list(fields)

    def add_set_type(self, name, owner_type, member_type):
        """Declare a set: a one-to-many relationship from an owner record type
        to a member record type. This is a Bachman-diagram arrow."""
        self.set_types[name] = (owner_type, member_type)
        self.first_member[name] = {}
        self.next_member[name] = {}
        self.owner_of[name] = {}

    # ── STORE: add a record, give it a database key ───────────────────────

    def store(self, rtype, **fields):
        record_id = self.next_id
        self.next_id += 1
        record = {"_type": rtype, "_id": record_id}
        for field_name, value in fields.items():
            record[field_name] = value
        self.records[record_id] = record
        if VERBOSE:
            print("      STORE %s #%d %s" % (rtype, record_id, fields))
        return record_id

    def get(self, record_id):
        return self.records.get(record_id)

    # ── CONNECT / DISCONNECT: splice a member into (out of) an owner's chain ─

    def connect(self, set_name, owner_id, member_id):
        """Add member_id to the end of owner_id's chain for this set. Appending
        at the tail keeps the chain in the order members were connected, which
        is the behavior of an IDS set declared with INSERTION IS LAST."""
        if set_name not in self.set_types:
            raise KeyError("no such set: %s" % set_name)
        if owner_id not in self.records:
            raise KeyError("no such owner record: %d" % owner_id)
        if member_id not in self.records:
            raise KeyError("no such member record: %d" % member_id)

        self.owner_of[set_name][member_id] = owner_id
        self.next_member[set_name][member_id] = None

        first = self.first_member[set_name].get(owner_id)
        if first is None:
            # Empty chain: the owner's first-member pointer now points here.
            self.first_member[set_name][owner_id] = member_id
            if VERBOSE:
                print("      CONNECT %s: owner #%d first -> #%d"
                      % (set_name, owner_id, member_id))
        else:
            # Walk to the tail and hang the new member off the last one.
            current = first
            while self.next_member[set_name][current] is not None:
                current = self.next_member[set_name][current]
            self.next_member[set_name][current] = member_id
            if VERBOSE:
                print("      CONNECT %s: #%d next -> #%d"
                      % (set_name, current, member_id))

    def disconnect(self, set_name, member_id):
        """Unlink a member from its chain, re-pointing the previous member (or
        the owner's first pointer) past it. The member record still exists; it
        is just no longer in this set."""
        owner_id = self.owner_of[set_name].get(member_id)
        if owner_id is None:
            return
        first = self.first_member[set_name].get(owner_id)
        after = self.next_member[set_name].get(member_id)

        if first == member_id:
            # It was the head: the owner's first pointer skips to the next one.
            self.first_member[set_name][owner_id] = after
        else:
            # Find the member just before it and re-point that one past it.
            current = first
            while current is not None and self.next_member[set_name][current] != member_id:
                current = self.next_member[set_name][current]
            if current is not None:
                self.next_member[set_name][current] = after

        del self.owner_of[set_name][member_id]
        if member_id in self.next_member[set_name]:
            del self.next_member[set_name][member_id]
        if VERBOSE:
            print("      DISCONNECT %s: removed #%d" % (set_name, member_id))

    # ── Navigation: the whole point of the model ──────────────────────────

    def members(self, set_name, owner_id):
        """FIND FIRST WITHIN SET, then FIND NEXT WITHIN SET until the chain
        ends. Returns the member ids in chain order. This touches only the
        members of this one owner -- never an unrelated record."""
        if set_name not in self.set_types:
            raise KeyError("no such set: %s" % set_name)
        result = []
        current = self.first_member[set_name].get(owner_id)
        hops = 0
        while current is not None:
            hops += 1
            result.append(current)
            if VERBOSE:
                record = self.records[current]
                print("      hop %d: WITHIN %s at #%d %s"
                      % (hops, set_name, current, self._describe(record)))
            current = self.next_member[set_name][current]
        if VERBOSE:
            print("      (navigation touched %d record(s))" % hops)
        return result

    def owner(self, set_name, member_id):
        """Follow the owner pointer: which owner's chain is this member on? One
        hop, because every member stores its owner -- not a search."""
        if set_name not in self.set_types:
            raise KeyError("no such set: %s" % set_name)
        return self.owner_of[set_name].get(member_id)

    # ── FIND by field value: the CALC / scan access path ──────────────────

    def find(self, rtype, **criteria):
        """Locate records of a type whose fields match. This is a scan over
        records of that type -- the access path you use to get an initial
        foothold before you start navigating sets."""
        result = []
        for record_id, record in self.records.items():
            if record["_type"] != rtype:
                continue
            matches = True
            for field_name, value in criteria.items():
                if record.get(field_name) != value:
                    matches = False
                    break
            if matches:
                result.append(record_id)
        return result

    # ── helpers ───────────────────────────────────────────────────────────

    def _describe(self, record):
        parts = []
        for key in record:
            if key == "_type" or key == "_id":
                continue
            parts.append("%s=%s" % (key, record[key]))
        return " ".join(parts)


# ── Before: the flat-file world ──────────────────────────────────────────────

def flat_file_scan(db, rtype, field_name, value):
    """What you did before the network model: to find related records you read
    every record of a type and tested it. Returns (matching_ids, records_read)
    so you can compare the work done against navigating a set."""
    matching = []
    records_read = 0
    for record_id, record in db.records.items():
        if record["_type"] != rtype:
            continue
        records_read += 1
        if record.get(field_name) == value:
            matching.append(record_id)
    return matching, records_read


# ── A small demo database for the REPL ───────────────────────────────────────

def build_demo():
    db = Database()
    db.add_record_type("DEPT", ["name"])
    db.add_record_type("EMP", ["name"])
    db.add_set_type("WORKS_IN", "DEPT", "EMP")

    eng = db.store("DEPT", name="Engineering")
    sales = db.store("DEPT", name="Sales")
    ada = db.store("EMP", name="Ada")
    grace = db.store("EMP", name="Grace")
    alan = db.store("EMP", name="Alan")

    db.connect("WORKS_IN", eng, ada)
    db.connect("WORKS_IN", eng, grace)
    db.connect("WORKS_IN", sales, alan)
    return db


# ── REPL / script commands ───────────────────────────────────────────────────

BANNER = """The network data model (Charles W. Bachman, IDS, 1963).
Commands:
  rectype DEPT name             declare a record type and its fields
  set WORKS_IN DEPT EMP         declare a set: owner type -> member type
  store DEPT name=Engineering   store a record, prints its id (#)
  connect WORKS_IN 1 3          connect member #3 into owner #1's chain
  disconnect WORKS_IN 3         unlink member #3 from that set
  members WORKS_IN 1            navigate owner #1's member chain (FIND NEXT)
  owner WORKS_IN 3              follow member #3's owner pointer (navigate up)
  find EMP name=Ada             locate records by field value
  scan EMP name=Ada            the "before": flat-file scan, reports work done
  show                          print all records and the set chains
  help                          show this again
Ctrl-D to quit.
(Starts with a small demo DB: Engineering owns Ada and Grace, Sales owns Alan.)"""


def parse_fields(parts):
    """Turn ['name=Ada', 'level=3'] into {'name': 'Ada', 'level': '3'}."""
    fields = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        fields[key] = value
    return fields


def do_command(line, db):
    parts = line.split()
    if len(parts) == 0:
        return
    cmd = parts[0]

    if cmd == "rectype" and len(parts) >= 2:
        db.add_record_type(parts[1], parts[2:])
        print("declared record type %s %s" % (parts[1], parts[2:]))

    elif cmd == "set" and len(parts) == 4:
        db.add_set_type(parts[1], parts[2], parts[3])
        print("declared set %s: %s owns %s" % (parts[1], parts[2], parts[3]))

    elif cmd == "store" and len(parts) >= 2:
        rtype = parts[1]
        fields = parse_fields(parts[2:])
        record_id = db.store(rtype, **fields)
        print("stored %s #%d %s" % (rtype, record_id, fields))

    elif cmd == "connect" and len(parts) == 4:
        db.connect(parts[1], int(parts[2]), int(parts[3]))
        print("connected #%s into %s owner #%s" % (parts[3], parts[1], parts[2]))

    elif cmd == "disconnect" and len(parts) == 3:
        db.disconnect(parts[1], int(parts[2]))
        print("disconnected #%s from %s" % (parts[2], parts[1]))

    elif cmd == "members" and len(parts) == 3:
        owner_id = int(parts[2])
        member_ids = db.members(parts[1], owner_id)
        if len(member_ids) == 0:
            print("  (no members)")
        for member_id in member_ids:
            record = db.get(member_id)
            print("  #%d %s" % (member_id, db._describe(record)))

    elif cmd == "owner" and len(parts) == 3:
        member_id = int(parts[2])
        owner_id = db.owner(parts[1], member_id)
        if owner_id is None:
            print("  (#%d is not a member of %s)" % (member_id, parts[1]))
        else:
            record = db.get(owner_id)
            print("  owner is #%d %s" % (owner_id, db._describe(record)))

    elif cmd == "find" and len(parts) >= 3:
        rtype = parts[1]
        criteria = parse_fields(parts[2:])
        ids = db.find(rtype, **criteria)
        if len(ids) == 0:
            print("  (no match)")
        for record_id in ids:
            print("  #%d %s" % (record_id, db._describe(db.get(record_id))))

    elif cmd == "scan" and len(parts) == 3:
        rtype = parts[1]
        criteria = parse_fields([parts[2]])
        field_name = list(criteria.keys())[0]
        value = criteria[field_name]
        ids, read = flat_file_scan(db, rtype, field_name, value)
        print("  flat-file scan read %d %s record(s) to find %d match(es)"
              % (read, rtype, len(ids)))

    elif cmd == "show":
        print_database(db)

    elif cmd == "help":
        print(BANNER)

    else:
        print("unknown command: %s (try 'help')" % line)


def print_database(db):
    print("  records:")
    if len(db.records) == 0:
        print("    (none)")
    for record_id in sorted(db.records):
        record = db.records[record_id]
        print("    #%d %s: %s" % (record_id, record["_type"], db._describe(record)))
    print("  sets:")
    if len(db.set_types) == 0:
        print("    (none)")
    for set_name in db.set_types:
        owner_type, member_type = db.set_types[set_name]
        print("    %s (%s owns %s):" % (set_name, owner_type, member_type))
        owners = db.first_member[set_name]
        printed_any = False
        for owner_id in sorted(owners):
            member_ids = db.members(set_name, owner_id)
            if len(member_ids) == 0:
                continue
            printed_any = True
            chain = " -> ".join("#%d" % m for m in member_ids)
            print("      #%d -> %s" % (owner_id, chain))
        if not printed_any:
            print("      (no connected members)")


def repl():
    db = build_demo()
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
    """Load and run a script: one command per line, '#' starts a comment. Each
    command is echoed before it runs, as if typed into the REPL. Starts from an
    EMPTY database (not the demo) so a script defines its own schema and data."""
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

    # 1. STORE hands out sequential database keys, and GET returns the record.
    db = Database()
    db.add_record_type("DEPT", ["name"])
    db.add_record_type("EMP", ["name"])
    db.add_set_type("WORKS_IN", "DEPT", "EMP")
    eng = db.store("DEPT", name="Engineering")
    ada = db.store("EMP", name="Ada")
    check("store returns sequential ids", eng == 1 and ada == 2)
    check("get returns the stored record", db.get(ada)["name"] == "Ada")

    # 2. CONNECT then navigate: members come back in connection order.
    grace = db.store("EMP", name="Grace")
    db.connect("WORKS_IN", eng, ada)
    db.connect("WORKS_IN", eng, grace)
    check("members navigate in connection order",
          db.members("WORKS_IN", eng) == [ada, grace])

    # 3. An owner with no members navigates to an empty chain.
    sales = db.store("DEPT", name="Sales")
    check("owner with no members -> empty", db.members("WORKS_IN", sales) == [])

    # 4. The reverse link: a member follows its owner pointer back.
    check("owner pointer: Ada's owner is Engineering",
          db.owner("WORKS_IN", ada) == eng)

    # 5. DISCONNECT the head; the rest of the chain survives.
    db.disconnect("WORKS_IN", ada)
    check("disconnect head: chain is now just Grace",
          db.members("WORKS_IN", eng) == [grace])
    check("disconnected member has no owner",
          db.owner("WORKS_IN", ada) is None)

    # 6. Disconnect a middle member, previous re-points past it.
    db2 = Database()
    db2.add_set_type("WORKS_IN", "DEPT", "EMP")
    d = db2.store("DEPT", name="D")
    a = db2.store("EMP", name="A")
    b = db2.store("EMP", name="B")
    c = db2.store("EMP", name="C")
    db2.connect("WORKS_IN", d, a)
    db2.connect("WORKS_IN", d, b)
    db2.connect("WORKS_IN", d, c)
    db2.disconnect("WORKS_IN", b)
    check("disconnect middle: chain closes to A -> C",
          db2.members("WORKS_IN", d) == [a, c])

    # 7. Reconnect after disconnect goes to the tail.
    db2.connect("WORKS_IN", d, b)
    check("reconnect appends at the tail: A -> C -> B",
          db2.members("WORKS_IN", d) == [a, c, b])

    # 8. One record can be a member in one set and an owner in another:
    #    Company owns Departments; Department owns Employees. Navigate both.
    db3 = Database()
    db3.add_set_type("HAS_DEPT", "CO", "DEPT")
    db3.add_set_type("WORKS_IN", "DEPT", "EMP")
    co = db3.store("CO", name="Acme")
    eng3 = db3.store("DEPT", name="Engineering")
    emp3 = db3.store("EMP", name="Ada")
    db3.connect("HAS_DEPT", co, eng3)
    db3.connect("WORKS_IN", eng3, emp3)
    check("record is member in one set and owner in another",
          db3.members("HAS_DEPT", co) == [eng3]
          and db3.members("WORKS_IN", eng3) == [emp3])

    # 9. Many-to-many via a link record: the thing flat files could not do.
    #    Students and Courses, joined by an ENROLL link record connected into
    #    two sets at once (a student's enrollments, a course's enrollments).
    db4 = Database()
    db4.add_set_type("STU_ENROLL", "STUDENT", "ENROLL")
    db4.add_set_type("CRS_ENROLL", "COURSE", "ENROLL")
    alice = db4.store("STUDENT", name="Alice")
    bob = db4.store("STUDENT", name="Bob")
    cs101 = db4.store("COURSE", name="CS101")
    math200 = db4.store("COURSE", name="MATH200")
    e1 = db4.store("ENROLL")      # Alice in CS101
    e2 = db4.store("ENROLL")      # Alice in MATH200
    e3 = db4.store("ENROLL")      # Bob in CS101
    db4.connect("STU_ENROLL", alice, e1)
    db4.connect("STU_ENROLL", alice, e2)
    db4.connect("STU_ENROLL", bob, e3)
    db4.connect("CRS_ENROLL", cs101, e1)
    db4.connect("CRS_ENROLL", cs101, e3)
    db4.connect("CRS_ENROLL", math200, e2)

    # Alice's courses: navigate her enrollments, then each enrollment's owning
    # course.
    alice_courses = []
    for enroll in db4.members("STU_ENROLL", alice):
        course_id = db4.owner("CRS_ENROLL", enroll)
        alice_courses.append(db4.get(course_id)["name"])
    check("M:N: Alice is enrolled in CS101 and MATH200",
          alice_courses == ["CS101", "MATH200"])

    # CS101's students: the same navigation from the other side.
    cs101_students = []
    for enroll in db4.members("CRS_ENROLL", cs101):
        student_id = db4.owner("STU_ENROLL", enroll)
        cs101_students.append(db4.get(student_id)["name"])
    check("M:N: CS101 has Alice and Bob",
          cs101_students == ["Alice", "Bob"])

    # 10. FIND by field value locates the initial record.
    check("find by field returns the matching record",
          db4.find("STUDENT", name="Bob") == [bob])
    check("find with no match returns empty",
          db4.find("STUDENT", name="Nobody") == [])

    # 11. The before/after in numbers: navigation touches only the members;
    #     the flat-file scan reads every record of the type.
    db5 = Database()
    db5.add_set_type("WORKS_IN", "DEPT", "EMP")
    dept = db5.store("DEPT", name="Engineering")
    members_ids = []
    for i in range(3):
        member = db5.store("EMP", name="in%d" % i, dept="Engineering")
        db5.connect("WORKS_IN", dept, member)
        members_ids.append(member)
    for i in range(20):
        db5.store("EMP", name="out%d" % i, dept="Other")
    navigated = db5.members("WORKS_IN", dept)
    _, records_read = flat_file_scan(db5, "EMP", "dept", "Engineering")
    check("navigation touches only the 3 members", len(navigated) == 3)
    check("flat-file scan reads all 23 EMP records", records_read == 23)

    # 12. owner() on a record that was never connected is None.
    stray = db5.store("EMP", name="stray")
    check("unconnected member has no owner",
          db5.owner("WORKS_IN", stray) is None)

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
        print("(verbose mode: every store, connect and pointer hop is printed)\n")
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

"""
A small network database in the style of Bachman's Integrated Data Store (IDS)
and the CODASYL DBTG model that grew out of it.

The historical ideas implemented here:
  * Records live at database keys (think: disk addresses).
  * A SET is a named one-to-many relationship. One OWNER record, many MEMBER
    records, linked as a ring: owner.first -> member -> member -> ... -> owner.
    Each member also holds PRIOR and OWNER pointers.
  * A CALC lookup (hashing on a key field) is the one way to land on a record
    without walking from another one.
  * Currency indicators: the system remembers "where you are" (current of run
    unit, current of each set), and FIND NEXT is relative to that.
  * A many-to-many relationship (employees <-> projects) is built from a
    connector record that is a member of two sets.
  * The programmer navigates, one record at a time. That is the point of the
    1973 Turing lecture, "The Programmer as Navigator".

Pipeline:
  command line -> parse -> DML verb (STORE / CONNECT / FIND / GET ...)
               -> pointer updates or pointer hops -> printed result
  Every record read is counted, so you can compare navigating with scanning.

Run:
  python3 implementation.py                 REPL
  python3 implementation.py file.dml        run a script of commands
  python3 implementation.py --test          test suite
  python3 implementation.py --verbose       REPL that prints every pointer hop
"""

import sys

VERBOSE = False

# The schema: set name -> (owner record type, member record type).
SCHEMA = {
    "DEPT-EMP": ("DEPT", "EMP"),
    "EMP-ASSIGN": ("EMP", "ASSIGN"),
    "PROJ-ASSIGN": ("PROJECT", "ASSIGN"),
}

# Which field is the CALC (hash) key for each record type.
CALC_FIELD = {
    "DEPT": "name",
    "EMP": "name",
    "PROJECT": "name",
}


class DBError(Exception):
    pass


class Record:
    def __init__(self, key, rtype, data):
        self.key = key
        self.rtype = rtype
        self.data = data
        # Role as OWNER: set name -> {"first": key or None, "last": key or None}
        self.owns = {}
        # Role as MEMBER: set name -> {"owner": key, "next": key, "prior": key}
        # In the ring, "next" of the last member is the owner's key, and
        # "prior" of the first member is the owner's key.
        self.member_of = {}


class Database:
    def __init__(self):
        self.records = {}
        self.next_key = 1
        self.calc_index = {}      # (rtype, value) -> key
        self.reads = 0            # how many records have been touched
        self.run_unit = None      # current of run unit
        self.set_currency = {}    # set name -> key of current record in that set

    # ---------- helpers ----------

    def log(self, text):
        if VERBOSE:
            print("    [hop] " + text)

    def touch(self, key):
        # Every time the program looks at a record, we count it.
        self.reads += 1
        if key not in self.records:
            raise DBError("no record at database key " + str(key))
        return self.records[key]

    def label(self, key):
        rec = self.records[key]
        calc_name = CALC_FIELD.get(rec.rtype)
        if calc_name is not None:
            return rec.rtype + ":" + str(rec.data.get(calc_name))
        return rec.rtype + "#" + str(key)

    def resolve(self, ref):
        # A ref is either a database key (7) or TYPE:calcvalue (EMP:Ann).
        if isinstance(ref, int):
            return ref
        if ref.isdigit():
            return int(ref)
        if ":" in ref:
            rtype, value = ref.split(":", 1)
            return self.find_calc(rtype.upper(), value)
        raise DBError("cannot understand reference " + ref)

    # ---------- STORE / CALC ----------

    def store(self, rtype, data):
        if rtype not in set(r for pair in SCHEMA.values() for r in pair):
            raise DBError("unknown record type " + rtype)
        key = self.next_key
        self.next_key = self.next_key + 1
        rec = Record(key, rtype, dict(data))
        # Every set this type owns starts empty: first and last are None.
        for set_name in SCHEMA:
            owner_type, member_type = SCHEMA[set_name]
            if owner_type == rtype:
                rec.owns[set_name] = {"first": None, "last": None}
        self.records[key] = rec
        calc_name = CALC_FIELD.get(rtype)
        if calc_name is not None:
            value = rec.data.get(calc_name)
            if value is None:
                raise DBError(rtype + " needs a " + calc_name + " field")
            if (rtype, value) in self.calc_index:
                raise DBError("duplicate " + rtype + " " + str(value))
            self.calc_index[(rtype, value)] = key
        self.run_unit = key
        self.log("STORE -> database key " + str(key))
        return key

    def find_calc(self, rtype, value):
        # One hash lookup: one record touched, no walking.
        if (rtype, value) not in self.calc_index:
            raise DBError("no " + rtype + " with " + CALC_FIELD.get(rtype, "?") + " " + value)
        key = self.calc_index[(rtype, value)]
        self.touch(key)
        self.log("CALC " + rtype + ":" + value + " -> key " + str(key))
        self.run_unit = key
        return key

    # ---------- CONNECT / DISCONNECT ----------

    def connect(self, member_key, set_name, owner_key):
        if set_name not in SCHEMA:
            raise DBError("unknown set " + set_name)
        owner_type, member_type = SCHEMA[set_name]
        member = self.records[member_key]
        owner = self.records[owner_key]
        if member.rtype != member_type:
            raise DBError(set_name + " members must be " + member_type)
        if owner.rtype != owner_type:
            raise DBError(set_name + " owner must be " + owner_type)
        if set_name in member.member_of:
            raise DBError(self.label(member_key) + " is already in " + set_name)

        chain = owner.owns[set_name]
        old_last = chain["last"]
        if old_last is None:
            # First member: owner.first and owner.last both point at it.
            member.member_of[set_name] = {"owner": owner_key, "next": owner_key, "prior": owner_key}
            chain["first"] = member_key
            chain["last"] = member_key
        else:
            # Append at the end of the ring.
            member.member_of[set_name] = {"owner": owner_key, "next": owner_key, "prior": old_last}
            self.records[old_last].member_of[set_name]["next"] = member_key
            chain["last"] = member_key
        self.log("CONNECT " + self.label(member_key) + " into " + set_name + " owned by " + self.label(owner_key))

    def disconnect(self, member_key, set_name):
        member = self.records[member_key]
        if set_name not in member.member_of:
            raise DBError(self.label(member_key) + " is not in " + set_name)
        links = member.member_of[set_name]
        owner_key = links["owner"]
        owner = self.records[owner_key]
        chain = owner.owns[set_name]
        next_key = links["next"]
        prior_key = links["prior"]

        # Repair the forward direction.
        if prior_key == owner_key:
            # member was first
            if next_key == owner_key:
                chain["first"] = None
            else:
                chain["first"] = next_key
        else:
            self.records[prior_key].member_of[set_name]["next"] = next_key

        # Repair the backward direction.
        if next_key == owner_key:
            # member was last
            if prior_key == owner_key:
                chain["last"] = None
            else:
                chain["last"] = prior_key
        else:
            self.records[next_key].member_of[set_name]["prior"] = prior_key

        del member.member_of[set_name]
        self.log("DISCONNECT " + self.label(member_key) + " from " + set_name)

    def erase(self, key, cascade=False):
        rec = self.records[key]
        # Members owned by this record first.
        for set_name in list(rec.owns.keys()):
            members = self.members_of(set_name, key, count_reads=False)
            if len(members) > 0:
                if not cascade:
                    raise DBError(self.label(key) + " still owns members in " + set_name
                                  + " (use ERASE ALL to cascade)")
                for member_key in members:
                    self.erase(member_key, cascade=True)
        # Then leave every set this record belongs to.
        for set_name in list(rec.member_of.keys()):
            self.disconnect(key, set_name)
        calc_name = CALC_FIELD.get(rec.rtype)
        if calc_name is not None:
            del self.calc_index[(rec.rtype, rec.data[calc_name])]
        del self.records[key]
        if self.run_unit == key:
            self.run_unit = None

    # ---------- Navigation: the heart of it ----------

    def find_first(self, set_name, owner_key):
        owner = self.touch(owner_key)
        if set_name not in owner.owns:
            raise DBError(self.label(owner_key) + " does not own " + set_name)
        first_key = owner.owns[set_name]["first"]
        if first_key is None:
            self.log("FIRST in " + set_name + " of " + self.label(owner_key) + " -> empty")
            return None
        self.touch(first_key)
        self.log("FIRST in " + set_name + " of " + self.label(owner_key) + " -> " + self.label(first_key))
        self.set_currency[set_name] = first_key
        self.run_unit = first_key
        return first_key

    def find_next(self, set_name, member_key):
        member = self.records[member_key]
        if set_name not in member.member_of:
            raise DBError(self.label(member_key) + " is not in " + set_name)
        next_key = member.member_of[set_name]["next"]
        owner_key = member.member_of[set_name]["owner"]
        if next_key == owner_key:
            # Wrapped around the ring: end of set.
            self.log("NEXT in " + set_name + " after " + self.label(member_key) + " -> end of set")
            return None
        self.touch(next_key)
        self.log("NEXT in " + set_name + " after " + self.label(member_key) + " -> " + self.label(next_key))
        self.set_currency[set_name] = next_key
        self.run_unit = next_key
        return next_key

    def find_owner(self, set_name, member_key):
        member = self.records[member_key]
        if set_name not in member.member_of:
            raise DBError(self.label(member_key) + " is not in " + set_name)
        owner_key = member.member_of[set_name]["owner"]
        self.touch(owner_key)
        self.log("OWNER in " + set_name + " of " + self.label(member_key) + " -> " + self.label(owner_key))
        self.run_unit = owner_key
        return owner_key

    def members_of(self, set_name, owner_key, count_reads=True):
        # A loop of FIND FIRST / FIND NEXT. Written out so the hops are visible.
        keys = []
        owner = self.records[owner_key]
        if set_name not in owner.owns:
            raise DBError(self.label(owner_key) + " does not own " + set_name)
        if count_reads:
            key = self.find_first(set_name, owner_key)
        else:
            key = owner.owns[set_name]["first"]
        while key is not None:
            keys.append(key)
            if count_reads:
                key = self.find_next(set_name, key)
            else:
                nxt = self.records[key].member_of[set_name]["next"]
                if nxt == owner_key:
                    key = None
                else:
                    key = nxt
        return keys

    # ---------- The "before": sequential scan ----------

    def scan(self, rtype, field, value):
        # Read every record in the file, in key order, keep matches.
        # This is what you did with a tape file: no pointers, just reading.
        matches = []
        for key in sorted(self.records.keys()):
            rec = self.touch(key)
            if rec.rtype != rtype:
                continue
            if str(rec.data.get(field)) == value:
                matches.append(key)
        return matches

    def scan_members(self, owner_type, owner_name, member_type, set_name):
        # "Which members belong to this owner?" with no pointers: read everything,
        # and for every member record, look at where it belongs.
        found = []
        for key in sorted(self.records.keys()):
            rec = self.touch(key)
            if rec.rtype != member_type:
                continue
            if set_name not in rec.member_of:
                continue
            owner_key = rec.member_of[set_name]["owner"]
            owner = self.records[owner_key]
            if owner.data.get(CALC_FIELD[owner_type]) == owner_name:
                found.append(key)
        return found

    # ---------- Integrity ----------

    def check_integrity(self):
        # Walk every ring forward and backward and make sure they agree.
        problems = []
        for key in self.records:
            rec = self.records[key]
            for set_name in rec.owns:
                chain = rec.owns[set_name]
                forward = []
                cur = chain["first"]
                while cur is not None and cur != key:
                    forward.append(cur)
                    nxt = self.records[cur].member_of[set_name]["next"]
                    cur = nxt
                    if len(forward) > len(self.records):
                        problems.append("ring loops forever in " + set_name)
                        break
                backward = []
                cur = chain["last"]
                while cur is not None and cur != key:
                    backward.append(cur)
                    cur = self.records[cur].member_of[set_name]["prior"]
                    if len(backward) > len(self.records):
                        problems.append("backward ring loops in " + set_name)
                        break
                backward.reverse()
                if forward != backward:
                    problems.append(self.label(key) + " " + set_name + ": forward " + str(forward)
                                    + " != backward " + str(backward))
        return problems

    def describe(self, key):
        rec = self.records[key]
        parts = []
        for field in rec.data:
            parts.append(field + "=" + str(rec.data[field]))
        text = "#" + str(key) + " " + rec.rtype + " " + " ".join(parts)
        return text


# ---------- Sample data ----------

def load_demo(db):
    for name in ["Sales", "Support", "Research"]:
        db.store("DEPT", {"name": name})
    people = [("Ann", "Sales"), ("Bob", "Sales"), ("Cy", "Support"), ("Dee", "Research"),
              ("Eve", "Research"), ("Fay", "Research")]
    for person, dept in people:
        e = db.store("EMP", {"name": person})
        db.connect(e, "DEPT-EMP", db.find_calc("DEPT", dept))
    for project in ["Payroll", "Atlas"]:
        db.store("PROJECT", {"name": project})
    # Many-to-many: each ASSIGN record sits in one employee ring and one project ring.
    assignments = [("Ann", "Payroll", 10), ("Ann", "Atlas", 5), ("Dee", "Atlas", 20),
                   ("Eve", "Atlas", 15), ("Cy", "Payroll", 8)]
    for person, project, hours in assignments:
        a = db.store("ASSIGN", {"hours": hours})
        db.connect(a, "EMP-ASSIGN", db.find_calc("EMP", person))
        db.connect(a, "PROJ-ASSIGN", db.find_calc("PROJECT", project))
    db.reads = 0
    db.run_unit = None


# ---------- Command interpreter ----------

HELP = """Commands (a tiny DML in the spirit of CODASYL):
  demo                          load sample departments, employees, projects
  store TYPE field=value ...    STORE a record (TYPE: DEPT EMP PROJECT ASSIGN)
  connect REF SET OWNERREF      CONNECT a record into a set
  disconnect REF SET
  erase REF [all]               ERASE (all = also erase owned members)
  find TYPE:value               FIND by CALC key (one hash lookup)
  first SET OWNERREF            FIND FIRST within set
  next SET                      FIND NEXT within set (uses current of set)
  owner SET                     FIND OWNER of the current record within set
  get                           GET the current record of the run unit
  members SET OWNERREF          loop FIRST/NEXT and print every member
  scan TYPE field value         the old way: read every record
  compare DEPTNAME              navigate vs scan for a department's employees
  reads                         show the record-read counter
  check                         verify every ring is consistent
  dump                          print all records and pointers
  help, quit
REF is a database key (7) or TYPE:name (EMP:Ann)."""


def parse_fields(tokens):
    data = {}
    for token in tokens:
        if "=" not in token:
            raise DBError("expected field=value, got " + token)
        name, value = token.split("=", 1)
        if value.isdigit():
            data[name] = int(value)
        else:
            data[name] = value
    return data


def execute(db, line):
    line = line.strip()
    if line == "" or line.startswith("#"):
        return True
    tokens = line.split()
    verb = tokens[0].lower()
    args = tokens[1:]

    if verb in ("quit", "exit"):
        return False
    elif verb == "help":
        print(HELP)
    elif verb == "demo":
        load_demo(db)
        print("loaded: 3 departments, 6 employees, 2 projects, 5 assignments")
    elif verb == "store":
        key = db.store(args[0].upper(), parse_fields(args[1:]))
        print("stored " + db.describe(key))
    elif verb == "connect":
        db.connect(db.resolve(args[0]), args[1].upper(), db.resolve(args[2]))
        print("connected")
    elif verb == "disconnect":
        db.disconnect(db.resolve(args[0]), args[1].upper())
        print("disconnected")
    elif verb == "erase":
        cascade = len(args) > 1 and args[1].lower() == "all"
        db.erase(db.resolve(args[0]), cascade)
        print("erased")
    elif verb == "find":
        rtype, value = args[0].split(":", 1)
        key = db.find_calc(rtype.upper(), value)
        print("found " + db.describe(key))
    elif verb == "first":
        key = db.find_first(args[0].upper(), db.resolve(args[1]))
        if key is None:
            print("set is empty")
        else:
            print("found " + db.describe(key))
    elif verb == "next":
        set_name = args[0].upper()
        if set_name not in db.set_currency:
            raise DBError("no current record in " + set_name + " (use FIRST first)")
        key = db.find_next(set_name, db.set_currency[set_name])
        if key is None:
            print("end of set")
        else:
            print("found " + db.describe(key))
    elif verb == "owner":
        set_name = args[0].upper()
        if db.run_unit is None:
            raise DBError("no current record")
        key = db.find_owner(set_name, db.run_unit)
        print("owner is " + db.describe(key))
    elif verb == "get":
        if db.run_unit is None:
            raise DBError("no current record")
        print(db.describe(db.run_unit))
    elif verb == "members":
        keys = db.members_of(args[0].upper(), db.resolve(args[1]))
        for key in keys:
            print("  " + db.describe(key))
        print("(" + str(len(keys)) + " members)")
    elif verb == "scan":
        keys = db.scan(args[0].upper(), args[1], args[2])
        for key in keys:
            print("  " + db.describe(key))
        print("(" + str(len(keys)) + " matches)")
    elif verb == "compare":
        compare(db, args[0])
    elif verb == "reads":
        print("records read so far: " + str(db.reads))
    elif verb == "check":
        problems = db.check_integrity()
        if len(problems) == 0:
            print("all rings consistent")
        else:
            for p in problems:
                print("PROBLEM: " + p)
    elif verb == "dump":
        for key in sorted(db.records.keys()):
            rec = db.records[key]
            print(db.describe(key))
            for set_name in rec.owns:
                print("     owns " + set_name + ": " + str(rec.owns[set_name]))
            for set_name in rec.member_of:
                print("     in   " + set_name + ": " + str(rec.member_of[set_name]))
    else:
        print("unknown command: " + verb + " (try help)")
    return True


def compare(db, dept_name):
    # The before/after in one command.
    print("Question: which employees are in " + dept_name + "?")
    db.reads = 0
    owner = db.find_calc("DEPT", dept_name)
    members = db.members_of("DEPT-EMP", owner)
    navigate_reads = db.reads
    print("  navigate: " + str([db.records[k].data["name"] for k in members])
          + "  records read: " + str(navigate_reads))
    db.reads = 0
    scanned = db.scan_members("DEPT", dept_name, "EMP", "DEPT-EMP")
    scan_reads = db.reads
    print("  scan:     " + str([db.records[k].data["name"] for k in scanned])
          + "  records read: " + str(scan_reads))
    print("  the file has " + str(len(db.records)) + " records in total")


def run_line(db, line):
    try:
        return execute(db, line)
    except DBError as err:
        print("error: " + str(err))
    except (IndexError, KeyError) as err:
        print("error: bad command or unknown record (" + repr(err) + ")")
    return True


def run_file(path):
    db = Database()
    with open(path) as handle:
        lines = handle.readlines()
    for line in lines:
        text = line.strip()
        if text != "" and not text.startswith("#"):
            print("> " + text)
        if not run_line(db, line):
            break


def repl():
    db = Database()
    print("Bachman network database. Type 'demo' to load data, 'help' for commands.")
    while True:
        try:
            line = input("ids> ")
        except EOFError:
            print()
            break
        if not run_line(db, line):
            break


# ---------- Tests ----------

def run_tests():
    results = []

    def check(name, condition):
        results.append((name, condition))

    def fresh():
        db = Database()
        load_demo(db)
        return db

    # 1. store and CALC find
    db = Database()
    k = db.store("DEPT", {"name": "Sales"})
    check("store then CALC find returns same key", db.find_calc("DEPT", "Sales") == k)

    # 2. duplicate CALC key rejected
    try:
        db.store("DEPT", {"name": "Sales"})
        check("duplicate CALC key rejected", False)
    except DBError:
        check("duplicate CALC key rejected", True)

    # 3. members come back in insertion order
    db = fresh()
    names = [db.records[k].data["name"] for k in db.members_of("DEPT-EMP", db.find_calc("DEPT", "Research"))]
    check("members in connect order", names == ["Dee", "Eve", "Fay"])

    # 4. empty set
    db = Database()
    d = db.store("DEPT", {"name": "Empty"})
    check("FIRST on empty set is None", db.find_first("DEPT-EMP", d) is None)

    # 5. find owner
    db = fresh()
    ann = db.find_calc("EMP", "Ann")
    owner = db.find_owner("DEPT-EMP", ann)
    check("FIND OWNER of Ann is Sales", db.records[owner].data["name"] == "Sales")

    # 6. NEXT ends at the owner, not past it
    db = fresh()
    sales = db.find_calc("DEPT", "Sales")
    first = db.find_first("DEPT-EMP", sales)
    second = db.find_next("DEPT-EMP", first)
    third = db.find_next("DEPT-EMP", second)
    check("ring ends after last member", third is None)

    # 7. many-to-many: Atlas people through ASSIGN records
    db = fresh()
    atlas = db.find_calc("PROJECT", "Atlas")
    people = []
    for a in db.members_of("PROJ-ASSIGN", atlas):
        emp = db.find_owner("EMP-ASSIGN", a)
        people.append(db.records[emp].data["name"])
    check("Atlas staff via connector records", sorted(people) == ["Ann", "Dee", "Eve"])

    # 8. many-to-many the other way
    ann = db.find_calc("EMP", "Ann")
    projects = []
    for a in db.members_of("EMP-ASSIGN", ann):
        proj = db.find_owner("PROJ-ASSIGN", a)
        projects.append(db.records[proj].data["name"])
    check("Ann's projects via connector records", sorted(projects) == ["Atlas", "Payroll"])

    # 9. disconnect a middle member
    db = fresh()
    bob_dept = db.find_calc("DEPT", "Research")
    eve = db.find_calc("EMP", "Eve")
    db.disconnect(eve, "DEPT-EMP")
    names = [db.records[k].data["name"] for k in db.members_of("DEPT-EMP", bob_dept)]
    check("disconnect middle keeps others linked", names == ["Dee", "Fay"])
    check("rings consistent after disconnect", db.check_integrity() == [])

    # 10. disconnect first and last, then everything
    db = fresh()
    for name in ["Dee", "Fay", "Eve"]:
        db.disconnect(db.find_calc("EMP", name), "DEPT-EMP")
    research = db.find_calc("DEPT", "Research")
    check("set empties after all members leave", db.find_first("DEPT-EMP", research) is None)
    check("rings consistent after emptying", db.check_integrity() == [])

    # 11. wrong member type
    db = fresh()
    try:
        db.connect(db.find_calc("DEPT", "Sales"), "DEPT-EMP", db.find_calc("DEPT", "Research"))
        check("wrong member type rejected", False)
    except DBError:
        check("wrong member type rejected", True)

    # 12. double connect
    try:
        db.connect(db.find_calc("EMP", "Ann"), "DEPT-EMP", db.find_calc("DEPT", "Research"))
        check("double connect rejected", False)
    except DBError:
        check("double connect rejected", True)

    # 13. erase owner with members refused, ERASE ALL cascades
    db = fresh()
    sales = db.find_calc("DEPT", "Sales")
    try:
        db.erase(sales)
        check("erase owner with members refused", False)
    except DBError:
        check("erase owner with members refused", True)
    db.erase(sales, cascade=True)
    check("erase all removes members too", ("EMP", "Ann") not in db.calc_index)
    check("rings consistent after cascade", db.check_integrity() == [])

    # 14. navigating reads fewer records than scanning
    db = fresh()
    db.reads = 0
    owner = db.find_calc("DEPT", "Sales")
    db.members_of("DEPT-EMP", owner)
    nav = db.reads
    db.reads = 0
    db.scan_members("DEPT", "Sales", "EMP", "DEPT-EMP")
    scn = db.reads
    check("navigate reads fewer records than scan", nav < scn)

    # 15. cost of navigation does not grow with unrelated records
    db = fresh()
    for i in range(200):
        e = db.store("EMP", {"name": "x" + str(i)})
        db.connect(e, "DEPT-EMP", db.find_calc("DEPT", "Support"))
    db.reads = 0
    owner = db.find_calc("DEPT", "Sales")
    db.members_of("DEPT-EMP", owner)
    check("Sales lookup still costs 1 + 2 members + ring reads", db.reads <= 5)

    passed = 0
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print("  " + status + "  " + name)
        if ok:
            passed = passed + 1
    print(str(passed) + "/" + str(len(results)) + " passed")
    return passed == len(results)


def main():
    global VERBOSE
    args = sys.argv[1:]
    if "--test" in args:
        ok = run_tests()
        sys.exit(0 if ok else 1)
    if "--verbose" in args:
        VERBOSE = True
        print("(verbose mode: every pointer hop is printed)\n")
    files = [a for a in args if not a.startswith("--")]
    if len(files) > 0:
        run_file(files[0])
        return
    repl()


if __name__ == "__main__":
    main()

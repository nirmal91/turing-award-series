"""
A small network database in the style of Charles Bachman's Integrated Data
Store (IDS, early 1960s) and the CODASYL DBTG data manipulation language that
grew out of it.

BEFORE IDS: business data lived in flat files, usually on tape or cards. To
answer "which courses is Ada taking?" you ran a program that read a whole file
from the start, matched records by key, and then read another whole file for
the next question. Every relationship was a key you matched by scanning.

AFTER IDS: records live at addresses on a disk. A record that belongs to a
group is linked to the others by pointers: an owner record points to its first
member, each member points to the next one, and the last one points back to
the owner. The programmer does not search. He navigates: find the student,
walk the student's chain, hop from each link record to its course.
Bachman's 1973 Turing lecture called this "The Programmer as Navigator."

This file keeps those ideas and nothing else:

  * records with a type and fields, each stored at a database key (an address)
  * "sets": a ring of pointers with one owner record and many member records
  * currency indicators: the database remembers where you are, so "next"
    means next from the record you touched last
  * a handful of verbs: STORE, FIND ANY, FIND FIRST/NEXT/PRIOR/LAST WITHIN,
    FIND OWNER WITHIN, GET, CONNECT, DISCONNECT, ERASE

The sample schema is the classic many-to-many case: Students take Courses
through Enrollment records. An Enrollment is a member of two sets at once, one
owned by its student and one owned by its course. A hierarchy (one parent per
record) cannot say that. A network can.

Pipeline:
    command text (find any student name=Ada)
        -> parse        split into a verb and arguments
        -> Database     follow or rewrite pointers, update currency
        -> printed result and a status (OK, END-OF-SET, NOT-FOUND)

Run:
    python3 implementation.py                  # interactive REPL
    python3 implementation.py practice.dml     # run a command script
    python3 implementation.py --test           # self-test suite
    python3 implementation.py --verbose        # REPL that prints every pointer change
"""

import sys

VERBOSE = False


class DBError(Exception):
    pass


# ── The schema ────────────────────────────────────────────────────────────────
#
# records: record type -> list of field names
# calc:    record type -> the field used for direct lookup (a hash, in IDS and
#          later CODASYL. "Location mode CALC.")
# sets:    set name -> (owner record type, member record type)

REGISTRAR_SCHEMA = {
    "records": {
        "STUDENT": ["name"],
        "COURSE": ["title"],
        "ENROLLMENT": ["grade"],
    },
    "calc": {
        "STUDENT": "name",
        "COURSE": "title",
    },
    "sets": {
        "STUDENT-ENROLLMENT": ("STUDENT", "ENROLLMENT"),
        "COURSE-ENROLLMENT": ("COURSE", "ENROLLMENT"),
    },
}


# ── A stored record ───────────────────────────────────────────────────────────

class Record:
    def __init__(self, key, rtype, fields, schema):
        self.key = key
        self.rtype = rtype
        self.fields = fields
        # links: set name -> {"next": key, "prior": key, "owner": key}
        # An owner starts as an empty ring that points at itself.
        # A member has no links until it is connected.
        self.links = {}
        for set_name, pair in schema["sets"].items():
            owner_type = pair[0]
            if rtype == owner_type:
                self.links[set_name] = {"next": key, "prior": key, "owner": key}

    def __str__(self):
        parts = []
        for name, value in self.fields.items():
            parts.append(name + "=" + value)
        return self.rtype + "#" + str(self.key) + " " + " ".join(parts)


# ── The database ──────────────────────────────────────────────────────────────

class Database:
    def __init__(self, schema):
        self.schema = schema
        self.records = {}          # database key -> Record
        self.next_key = 1
        self.calc_index = {}       # (record type, value) -> list of database keys
        self.touches = 0           # how many records we visited, to compare costs
        self.status = "OK"

        # Currency indicators: the database remembers where we are.
        self.current_run_unit = None   # the last record touched by anyone
        self.current_of_type = {}      # record type -> last record of that type
        self.current_of_set = {}       # set name -> last owner or member touched

    # -- small helpers ------------------------------------------------------

    def _log(self, text):
        if VERBOSE:
            print("    [db] " + text)

    def _touch(self, key):
        self.touches = self.touches + 1
        return self.records[key]

    def _check_type(self, rtype):
        if rtype not in self.schema["records"]:
            raise DBError("unknown record type " + rtype)

    def _check_set(self, set_name):
        if set_name not in self.schema["sets"]:
            raise DBError("unknown set " + set_name)

    def owner_type(self, set_name):
        return self.schema["sets"][set_name][0]

    def member_type(self, set_name):
        return self.schema["sets"][set_name][1]

    def _owner_key_of(self, record, set_name):
        """Given an owner or a member of a set, return the owner's key."""
        if record.rtype == self.owner_type(set_name):
            return record.key
        if set_name not in record.links:
            raise DBError(record.rtype + " is not connected to " + set_name)
        return record.links[set_name]["owner"]

    # -- currency -----------------------------------------------------------

    def _make_current(self, record):
        self.current_run_unit = record.key
        self.current_of_type[record.rtype] = record.key
        for set_name, pair in self.schema["sets"].items():
            if record.rtype == pair[0] or record.rtype == pair[1]:
                self.current_of_set[set_name] = record.key
        self._log("currency: run unit = " + str(record.key))

    def _forget(self, key):
        """Drop any currency indicator that points at a deleted record."""
        if self.current_run_unit == key:
            self.current_run_unit = None
        for rtype in list(self.current_of_type.keys()):
            if self.current_of_type[rtype] == key:
                del self.current_of_type[rtype]
        for set_name in list(self.current_of_set.keys()):
            if self.current_of_set[set_name] == key:
                del self.current_of_set[set_name]

    # -- STORE --------------------------------------------------------------

    def store(self, rtype, values):
        self._check_type(rtype)
        allowed = self.schema["records"][rtype]
        fields = {}
        for name in allowed:
            fields[name] = values.get(name, "")
        for name in values:
            if name not in allowed:
                raise DBError(rtype + " has no field " + name)

        # AUTOMATIC insertion: every set this record is a member of needs an
        # owner, taken from that set's current record. Check before we write.
        owners_to_use = {}
        for set_name, pair in self.schema["sets"].items():
            if pair[1] == rtype:
                if set_name not in self.current_of_set:
                    raise DBError("no current owner for set " + set_name)
                current = self.records[self.current_of_set[set_name]]
                owners_to_use[set_name] = self._owner_key_of(current, set_name)

        key = self.next_key
        self.next_key = self.next_key + 1
        record = Record(key, rtype, fields, self.schema)
        self.records[key] = record
        self._log("stored " + str(record))

        calc_field = self.schema["calc"].get(rtype)
        if calc_field is not None:
            index_key = (rtype, fields[calc_field])
            if index_key not in self.calc_index:
                self.calc_index[index_key] = []
            self.calc_index[index_key].append(key)

        for set_name, owner_key in owners_to_use.items():
            self._connect_key(key, set_name, owner_key)

        self._make_current(record)
        self.status = "OK"
        return record

    # -- CONNECT / DISCONNECT -----------------------------------------------

    def _connect_key(self, key, set_name, owner_key):
        """Insert a member at the end of the owner's ring (before the owner)."""
        member = self.records[key]
        owner = self.records[owner_key]
        last = self.records[owner.links[set_name]["prior"]]

        member.links[set_name] = {"next": owner.key, "prior": last.key, "owner": owner.key}
        last.links[set_name]["next"] = key
        owner.links[set_name]["prior"] = key
        self._log("connect " + str(key) + " to " + set_name + " after " + str(last.key)
                  + " (owner " + str(owner.key) + ")")

    def connect(self, set_name):
        """CONNECT current of run unit TO set, under the set's current owner."""
        self._check_set(set_name)
        if self.current_run_unit is None:
            raise DBError("no current record")
        record = self.records[self.current_run_unit]
        if record.rtype != self.member_type(set_name):
            raise DBError(record.rtype + " cannot be a member of " + set_name)
        if set_name in record.links:
            raise DBError("record is already connected to " + set_name)
        if set_name not in self.current_of_set:
            raise DBError("no current owner for set " + set_name)
        current = self.records[self.current_of_set[set_name]]
        owner_key = self._owner_key_of(current, set_name)
        self._connect_key(record.key, set_name, owner_key)
        self.status = "OK"

    def disconnect(self, set_name):
        """DISCONNECT current of run unit FROM set. The record stays in the database."""
        self._check_set(set_name)
        if self.current_run_unit is None:
            raise DBError("no current record")
        record = self.records[self.current_run_unit]
        if record.rtype != self.member_type(set_name) or set_name not in record.links:
            raise DBError("record is not connected to " + set_name)
        links = record.links[set_name]
        before = self.records[links["prior"]]
        after = self.records[links["next"]]
        before.links[set_name]["next"] = after.key
        after.links[set_name]["prior"] = before.key
        del record.links[set_name]
        self._log("disconnect " + str(record.key) + " from " + set_name)
        self.status = "OK"

    # -- ERASE --------------------------------------------------------------

    def erase(self):
        """ERASE the current record. Refuses if it still owns members."""
        if self.current_run_unit is None:
            raise DBError("no current record")
        record = self.records[self.current_run_unit]
        for set_name, pair in self.schema["sets"].items():
            if pair[0] == record.rtype:
                if record.links[set_name]["next"] != record.key:
                    raise DBError("cannot erase " + str(record) + ": it still owns members of " + set_name)

        for set_name, pair in self.schema["sets"].items():
            if pair[1] == record.rtype and set_name in record.links:
                self.current_run_unit = record.key
                self.disconnect(set_name)

        calc_field = self.schema["calc"].get(record.rtype)
        if calc_field is not None:
            index_key = (record.rtype, record.fields[calc_field])
            self.calc_index[index_key].remove(record.key)
            if len(self.calc_index[index_key]) == 0:
                del self.calc_index[index_key]

        del self.records[record.key]
        self._forget(record.key)
        self._log("erased " + str(record))
        self.status = "OK"

    # -- FIND ---------------------------------------------------------------

    def find_any(self, rtype, value):
        """Direct lookup by the CALC field. One hop, no scanning."""
        self._check_type(rtype)
        if rtype not in self.schema["calc"]:
            raise DBError(rtype + " has no CALC key")
        index_key = (rtype, value)
        if index_key not in self.calc_index:
            self.status = "NOT-FOUND"
            return None
        record = self._touch(self.calc_index[index_key][0])
        self._make_current(record)
        self.status = "OK"
        return record

    def find_in_set(self, direction, set_name):
        """FIND FIRST / LAST / NEXT / PRIOR within a set, from the set's currency."""
        self._check_set(set_name)
        if direction not in ("FIRST", "LAST", "NEXT", "PRIOR"):
            raise DBError("unknown direction " + direction)
        if set_name not in self.current_of_set:
            raise DBError("no currency for set " + set_name)

        current = self.records[self.current_of_set[set_name]]
        owner_key = self._owner_key_of(current, set_name)
        owner = self.records[owner_key]

        if direction == "FIRST":
            candidate_key = owner.links[set_name]["next"]
        elif direction == "LAST":
            candidate_key = owner.links[set_name]["prior"]
        elif direction == "NEXT":
            candidate_key = current.links[set_name]["next"]
        else:
            candidate_key = current.links[set_name]["prior"]

        # The ring closes on the owner. Reaching the owner means we ran off the end.
        if candidate_key == owner_key:
            self.status = "END-OF-SET"
            return None

        record = self._touch(candidate_key)
        self._make_current(record)
        self.status = "OK"
        return record

    def find_owner(self, set_name):
        """Jump straight to the owner of the current record's set. One hop."""
        self._check_set(set_name)
        if set_name not in self.current_of_set:
            raise DBError("no currency for set " + set_name)
        current = self.records[self.current_of_set[set_name]]
        owner_key = self._owner_key_of(current, set_name)
        record = self._touch(owner_key)
        self._make_current(record)
        self.status = "OK"
        return record

    # -- GET ----------------------------------------------------------------

    def get(self):
        if self.current_run_unit is None:
            raise DBError("no current record")
        return self.records[self.current_run_unit]

    # -- inspection (does not count as navigation) --------------------------

    def members_of(self, owner_key, set_name):
        """Walk a ring without touching currency or the touch counter."""
        owner = self.records[owner_key]
        result = []
        key = owner.links[set_name]["next"]
        while key != owner_key:
            result.append(self.records[key])
            key = self.records[key].links[set_name]["next"]
        return result

    def check_integrity(self):
        """Every ring must close, run both directions, and agree on its owner."""
        problems = []
        seen_members = {}
        for set_name, pair in self.schema["sets"].items():
            for record in self.records.values():
                if record.rtype != pair[0]:
                    continue
                forward = []
                key = record.links[set_name]["next"]
                steps = 0
                while key != record.key:
                    forward.append(key)
                    key = self.records[key].links[set_name]["next"]
                    steps = steps + 1
                    if steps > len(self.records):
                        problems.append(set_name + ": ring of " + str(record.key) + " never closes")
                        break
                backward = []
                key = record.links[set_name]["prior"]
                steps = 0
                while key != record.key:
                    backward.append(key)
                    key = self.records[key].links[set_name]["prior"]
                    steps = steps + 1
                    if steps > len(self.records):
                        problems.append(set_name + ": back ring of " + str(record.key) + " never closes")
                        break
                backward.reverse()
                if forward != backward:
                    problems.append(set_name + ": next and prior disagree for owner " + str(record.key))
                for member_key in forward:
                    if self.records[member_key].links[set_name]["owner"] != record.key:
                        problems.append(set_name + ": member " + str(member_key) + " has wrong owner")
                    seen_members[(set_name, member_key)] = True
        for record in self.records.values():
            for set_name, pair in self.schema["sets"].items():
                if record.rtype == pair[1] and set_name in record.links:
                    if (set_name, record.key) not in seen_members:
                        problems.append(set_name + ": member " + str(record.key) + " is in no ring")
        return problems

    def dump(self):
        lines = []
        for set_name, pair in self.schema["sets"].items():
            lines.append("set " + set_name + "  (owner " + pair[0] + ", member " + pair[1] + ")")
            for record in self.records.values():
                if record.rtype != pair[0]:
                    continue
                member_texts = []
                for member in self.members_of(record.key, set_name):
                    member_texts.append(str(member.key))
                ring = "[" + " -> ".join(member_texts) + "]" if member_texts else "[empty]"
                lines.append("  " + str(record) + "  chain " + ring)
        return "\n".join(lines)


# ── The "before": flat files, found by scanning ───────────────────────────────
#
# Three flat files and nothing else. A relationship is a key that you match by
# reading. This is what a batch program on tape (or a naive disk file) does.

class FlatFiles:
    def __init__(self):
        self.students = []       # list of {"name": ...}
        self.courses = []        # list of {"title": ...}
        self.enrollments = []    # list of {"student": ..., "course": ..., "grade": ...}
        self.touches = 0

    def courses_of_student(self, student_name):
        found_student = False
        for row in self.students:
            self.touches = self.touches + 1
            if row["name"] == student_name:
                found_student = True
                break
        if not found_student:
            return []

        titles = []
        # A sequential file has no "end early". Read every enrollment.
        for enrollment in self.enrollments:
            self.touches = self.touches + 1
            if enrollment["student"] == student_name:
                for course in self.courses:
                    self.touches = self.touches + 1
                    if course["title"] == enrollment["course"]:
                        titles.append(course["title"])
                        break
        return titles


def registrar_rows(n_students, n_courses, per_student):
    """Deterministic sample data: (student, course, grade) triples."""
    grades = ["A", "B", "C"]
    rows = []
    for s in range(n_students):
        for k in range(per_student):
            course_number = (s * 7 + k * 3) % n_courses
            rows.append(("S" + str(s).zfill(3), "C" + str(course_number).zfill(2), grades[(s + k) % 3]))
    return rows


def build_flat(n_students, n_courses, per_student):
    flat = FlatFiles()
    for s in range(n_students):
        flat.students.append({"name": "S" + str(s).zfill(3)})
    for c in range(n_courses):
        flat.courses.append({"title": "C" + str(c).zfill(2)})
    for student, course, grade in registrar_rows(n_students, n_courses, per_student):
        flat.enrollments.append({"student": student, "course": course, "grade": grade})
    return flat


def build_network(n_students, n_courses, per_student):
    db = Database(REGISTRAR_SCHEMA)
    for c in range(n_courses):
        db.store("COURSE", {"title": "C" + str(c).zfill(2)})
    for s in range(n_students):
        name = "S" + str(s).zfill(3)
        db.store("STUDENT", {"name": name})
        for k in range(per_student):
            course_number = (s * 7 + k * 3) % n_courses
            grade = ["A", "B", "C"][(s + k) % 3]
            db.find_any("COURSE", "C" + str(course_number).zfill(2))
            db.store("ENROLLMENT", {"grade": grade})
    return db


def courses_by_navigation(db, student_name):
    """The programmer as navigator: find the student, walk the chain, hop to each course."""
    titles = []
    student = db.find_any("STUDENT", student_name)
    if student is None:
        return titles
    enrollment = db.find_in_set("FIRST", "STUDENT-ENROLLMENT")
    while enrollment is not None:
        course = db.find_owner("COURSE-ENROLLMENT")
        titles.append(course.fields["title"])
        # No reset needed. A course is not in STUDENT-ENROLLMENT, so that set's
        # currency still points at this enrollment and NEXT continues the chain.
        enrollment = db.find_in_set("NEXT", "STUDENT-ENROLLMENT")
    return titles


# ── Command language ──────────────────────────────────────────────────────────

HELP = """commands (case-insensitive):
  store TYPE field=value ...        store a record; auto-connects under the current owners
  find any TYPE value               direct lookup by the CALC field
  find first|last|next|prior TYPE within SET
  find owner within SET
  get                               show the current record
  connect to SET / disconnect from SET
  erase                             erase the current record
  currency                          show where you are
  dump                              show every chain
  schema                            show record types and sets
  demo                              load a small registrar and walk it
  check                             verify every pointer ring
  touches                           records visited so far
  help, quit"""


def parse_fields(tokens):
    values = {}
    for token in tokens:
        if "=" not in token:
            raise DBError("expected field=value, got " + token)
        name, value = token.split("=", 1)
        values[name.lower()] = value
    return values


def show_result(db, record):
    if record is None:
        return db.status
    return db.status + "  " + str(record)


def run_command(db, line):
    text = line.strip()
    if text == "" or text.startswith("#") or text.startswith("--"):
        return ""
    tokens = text.split()
    verb = tokens[0].lower()

    if verb == "help":
        return HELP
    if verb == "schema":
        lines = []
        for rtype, fields in db.schema["records"].items():
            calc = db.schema["calc"].get(rtype)
            note = "  (CALC " + calc + ")" if calc else ""
            lines.append("record " + rtype + ": " + ", ".join(fields) + note)
        for set_name, pair in db.schema["sets"].items():
            lines.append("set " + set_name + ": owner " + pair[0] + ", member " + pair[1])
        return "\n".join(lines)
    if verb == "dump":
        return db.dump()
    if verb == "check":
        problems = db.check_integrity()
        if problems:
            return "PROBLEMS:\n" + "\n".join(problems)
        return "all rings are consistent"
    if verb == "touches":
        return "records touched: " + str(db.touches)
    if verb == "currency":
        lines = []
        if db.current_run_unit is None:
            lines.append("run unit: none")
        else:
            lines.append("run unit: " + str(db.records[db.current_run_unit]))
        for set_name in db.schema["sets"]:
            if set_name in db.current_of_set:
                lines.append("set " + set_name + ": " + str(db.records[db.current_of_set[set_name]]))
            else:
                lines.append("set " + set_name + ": none")
        return "\n".join(lines)
    if verb == "get":
        return str(db.get())
    if verb == "store":
        if len(tokens) < 2:
            raise DBError("usage: store TYPE field=value ...")
        record = db.store(tokens[1].upper(), parse_fields(tokens[2:]))
        return "STORED  " + str(record)
    if verb == "connect":
        db.connect(tokens[-1].upper())
        return "OK"
    if verb == "disconnect":
        db.disconnect(tokens[-1].upper())
        return "OK"
    if verb == "erase":
        db.erase()
        return "ERASED"
    if verb == "find":
        if len(tokens) >= 4 and tokens[1].lower() == "any":
            return show_result(db, db.find_any(tokens[2].upper(), " ".join(tokens[3:])))
        if len(tokens) == 4 and tokens[1].lower() == "owner" and tokens[2].lower() == "within":
            return show_result(db, db.find_owner(tokens[3].upper()))
        if len(tokens) == 5 and tokens[3].lower() == "within":
            direction = tokens[1].upper()
            record = db.find_in_set(direction, tokens[4].upper())
            if record is not None and record.rtype != tokens[2].upper():
                raise DBError("set member type is " + record.rtype + ", not " + tokens[2].upper())
            return show_result(db, record)
        raise DBError("could not parse find command (try help)")
    raise DBError("unknown command " + verb + " (try help)")


def run_lines(db, lines, echo, quiet=False):
    for line in lines:
        text = line.strip()
        if echo and text != "" and not text.startswith("#") and not text.startswith("--"):
            print("db> " + text)
        try:
            output = run_command(db, line)
        except DBError as error:
            output = "ERROR: " + str(error)
        if output != "" and not quiet:
            print(output)


DEMO = """# Two students, two courses, three enrollments.
store course title=Logic
store course title=Databases
store student name=Ada
find any course Logic
store enrollment grade=A
find any course Databases
store enrollment grade=B
store student name=Grace
find any course Logic
store enrollment grade=A
dump
# Walk Ada's chain by hand.
find any student Ada
find first enrollment within STUDENT-ENROLLMENT
find owner within COURSE-ENROLLMENT
find any student Ada
find first enrollment within STUDENT-ENROLLMENT
find next enrollment within STUDENT-ENROLLMENT
find next enrollment within STUDENT-ENROLLMENT
"""


def repl():
    db = Database(REGISTRAR_SCHEMA)
    print("Bachman-style network database. Type help for commands, demo for a quick tour.")
    while True:
        try:
            line = input("db> ")
        except EOFError:
            print()
            return
        if line.strip().lower() in ("quit", "exit"):
            return
        if line.strip().lower() == "demo":
            run_lines(db, DEMO.splitlines(), True)
            continue
        try:
            output = run_command(db, line)
        except DBError as error:
            output = "ERROR: " + str(error)
        if output != "":
            print(output)


def run_file(path):
    db = Database(REGISTRAR_SCHEMA)
    with open(path) as handle:
        lines = handle.read().splitlines()
    run_lines(db, lines, True)


# ── Tests ─────────────────────────────────────────────────────────────────────

EMPLOYER_SCHEMA = {
    "records": {"DEPT": ["name"], "EMP": ["name"]},
    "calc": {"DEPT": "name"},
    "sets": {"DEPT-EMP": ("DEPT", "EMP")},
}


def make_registrar():
    """Ada takes Logic (A) and Databases (B). Grace takes Logic (A)."""
    db = Database(REGISTRAR_SCHEMA)
    run_lines(db, DEMO.splitlines()[:11], False, quiet=True)
    return db


def test_all():
    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            passed = passed + 1
            print("  ok    " + name)
        else:
            failed = failed + 1
            print("  FAIL  " + name)

    # 1
    db = make_registrar()
    found = db.find_any("STUDENT", "Ada")
    check("find any returns the stored student", found is not None and found.fields["name"] == "Ada")

    # 2
    found = db.find_any("STUDENT", "Nobody")
    check("find any on a missing key gives NOT-FOUND", found is None and db.status == "NOT-FOUND")

    # 3
    db.find_any("STUDENT", "Ada")
    first = db.find_in_set("FIRST", "STUDENT-ENROLLMENT")
    second = db.find_in_set("NEXT", "STUDENT-ENROLLMENT")
    check("chain keeps insertion order (first then next)",
          first.fields["grade"] == "A" and second.fields["grade"] == "B")

    # 4
    after_last = db.find_in_set("NEXT", "STUDENT-ENROLLMENT")
    check("next past the last member is END-OF-SET", after_last is None and db.status == "END-OF-SET")

    # 5
    db.find_any("STUDENT", "Ada")
    last = db.find_in_set("LAST", "STUDENT-ENROLLMENT")
    check("find last reaches the end of the chain directly", last.fields["grade"] == "B")

    # 6
    before_first = db.find_in_set("PRIOR", "STUDENT-ENROLLMENT")
    before_first = db.find_in_set("PRIOR", "STUDENT-ENROLLMENT")
    check("find prior walks backward then reports END-OF-SET",
          before_first is None and db.status == "END-OF-SET")

    # 7
    db.find_any("STUDENT", "Ada")
    db.find_in_set("FIRST", "STUDENT-ENROLLMENT")
    course = db.find_owner("COURSE-ENROLLMENT")
    check("a member reaches its other owner (enrollment -> course)", course.fields["title"] == "Logic")

    # 8
    owner = db.find_owner("COURSE-ENROLLMENT")
    check("find owner from the owner stays on the owner", owner.fields["title"] == "Logic")

    # 9 many-to-many from the course side
    db.find_any("COURSE", "Logic")
    names = []
    enrollment = db.find_in_set("FIRST", "COURSE-ENROLLMENT")
    while enrollment is not None:
        student = db.find_owner("STUDENT-ENROLLMENT")
        names.append(student.fields["name"])
        enrollment = db.find_in_set("NEXT", "COURSE-ENROLLMENT")
    check("many-to-many works from the course side (Logic has Ada and Grace)", names == ["Ada", "Grace"])

    # 10
    check("navigation returns Ada's courses", courses_by_navigation(db, "Ada") == ["Logic", "Databases"])

    # 11 currency
    db.find_any("STUDENT", "Grace")
    check("currency follows the last record touched", db.get().fields["name"] == "Grace")

    # 12 store needs an owner
    fresh = Database(REGISTRAR_SCHEMA)
    try:
        fresh.store("ENROLLMENT", {"grade": "A"})
        refused = False
    except DBError:
        refused = True
    check("storing a member with no current owner is refused", refused)

    # 13 disconnect
    db = make_registrar()
    db.find_any("STUDENT", "Ada")
    db.find_in_set("FIRST", "STUDENT-ENROLLMENT")
    db.disconnect("STUDENT-ENROLLMENT")
    ada = db.find_any("STUDENT", "Ada")
    chain = db.members_of(ada.key, "STUDENT-ENROLLMENT")
    check("disconnect removes the member from the ring", len(chain) == 1 and chain[0].fields["grade"] == "B")
    check("rings stay consistent after disconnect", db.check_integrity() == [])

    # 14 connect again
    db.find_any("STUDENT", "Grace")
    db.get()
    orphan_key = None
    for record in db.records.values():
        if record.rtype == "ENROLLMENT" and "STUDENT-ENROLLMENT" not in record.links:
            orphan_key = record.key
    db.current_run_unit = orphan_key
    db.connect("STUDENT-ENROLLMENT")
    grace = db.find_any("STUDENT", "Grace")
    check("connect puts a disconnected record under a new owner",
          len(db.members_of(grace.key, "STUDENT-ENROLLMENT")) == 2)

    # 15 erase a member
    db = make_registrar()
    db.find_any("STUDENT", "Grace")
    db.find_in_set("FIRST", "STUDENT-ENROLLMENT")
    before = len(db.records)
    db.erase()
    check("erase removes a member and fixes both rings",
          len(db.records) == before - 1 and db.check_integrity() == [])
    db.find_any("COURSE", "Logic")
    check("the course no longer lists the erased enrollment",
          len(db.members_of(db.get().key, "COURSE-ENROLLMENT")) == 1)

    # 16 erase an owner with members
    db = make_registrar()
    db.find_any("STUDENT", "Ada")
    try:
        db.erase()
        refused = False
    except DBError:
        refused = True
    check("erasing an owner that still has members is refused", refused)

    # 17 empty set
    db = make_registrar()
    db.store("STUDENT", {"name": "Linus"})
    empty = db.find_in_set("FIRST", "STUDENT-ENROLLMENT")
    check("find first in an empty set is END-OF-SET", empty is None and db.status == "END-OF-SET")

    # 18 another schema entirely
    other = Database(EMPLOYER_SCHEMA)
    other.store("DEPT", {"name": "Research"})
    other.store("EMP", {"name": "Bachman"})
    other.store("EMP", {"name": "Dijkstra"})
    other.find_any("DEPT", "Research")
    names = []
    employee = other.find_in_set("FIRST", "DEPT-EMP")
    while employee is not None:
        names.append(employee.fields["name"])
        employee = other.find_in_set("NEXT", "DEPT-EMP")
    check("the same engine runs a different schema (department -> employees)",
          names == ["Bachman", "Dijkstra"])

    # 19 navigation vs scanning
    flat = build_flat(200, 20, 3)
    net = build_network(200, 20, 3)
    scan_answer = flat.courses_of_student("S150")
    net.touches = 0
    nav_answer = courses_by_navigation(net, "S150")
    check("scanning and navigation give the same answer", sorted(scan_answer) == sorted(nav_answer))
    check("navigation touches far fewer records than scanning (" + str(net.touches) + " vs "
          + str(flat.touches) + ")", net.touches * 20 < flat.touches)

    # 20 big build stays consistent
    check("a 200-student registrar has consistent rings", net.check_integrity() == [])

    # 21 script runner
    script_db = Database(REGISTRAR_SCHEMA)
    output = run_command(script_db, "store student name=Test")
    check("run_command stores and reports", output.startswith("STORED"))
    check("run_command reports errors as DBError", _raises(script_db, "frobnicate"))

    print("")
    print(str(passed) + " passed, " + str(failed) + " failed")
    return failed == 0


def _raises(db, line):
    try:
        run_command(db, line)
    except DBError:
        return True
    return False


# ── Entry point ───────────────────────────────────────────────────────────────

def main(argv):
    global VERBOSE
    args = []
    for arg in argv:
        if arg == "--verbose":
            VERBOSE = True
        else:
            args.append(arg)

    if "--test" in args:
        ok = test_all()
        sys.exit(0 if ok else 1)
    if len(args) >= 1:
        run_file(args[0])
        return
    repl()


if __name__ == "__main__":
    main(sys.argv[1:])

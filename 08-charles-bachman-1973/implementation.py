#!/usr/bin/env python3
"""
A small CODASYL-style network database (Bachman's IDS idea, 1964 to 1971).

Historical pieces mirrored here:
  * Records live in memory and hold pointers to each other.
  * A SET is a ring: owner -> first member -> ... -> last member -> owner.
    Every member also keeps PRIOR and OWNER pointers.
  * A record can be a member of several sets, so the data is a network, not a
    tree. Many-to-many is done with a LINK record that sits in two sets.
  * The program navigates. It never says what it wants, it says where to go next.
  * CURRENCY INDICATORS remember "where I am": current of run unit, and one
    current record per set. FIND NEXT only makes sense relative to them.
  * CALC keys: a hash lookup to get an entry point into the network.

Before (flat file):   scan every row to answer a question.
After (navigation):   find one entry record, then follow pointers.

Usage:
  python3 implementation.py                # REPL, sample company preloaded
  python3 implementation.py script.dml     # run a DML script file
  python3 implementation.py --test         # test suite
  python3 implementation.py --verbose      # REPL, prints every pointer hop
"""

import sys

# ---------------------------------------------------------------- schema ----

SCHEMA_RECORDS = {
    "DEPT":   {"fields": ["name"],           "calc": "name"},
    "EMP":    {"fields": ["name", "salary"], "calc": "name"},
    "PROJ":   {"fields": ["name"],           "calc": "name"},
    "ASSIGN": {"fields": ["hours"],          "calc": None},
}

# set name -> (owner record type, member record type)
SCHEMA_SETS = {
    "DEPT-EMP":    ("DEPT", "EMP"),
    "EMP-ASSIGN":  ("EMP", "ASSIGN"),
    "PROJ-ASSIGN": ("PROJ", "ASSIGN"),
}

OK = "OK"
END_OF_SET = "END-OF-SET"
NOT_FOUND = "NOT-FOUND"


class DBError(Exception):
    pass


class Record:
    def __init__(self, rid, rtype, fields):
        self.rid = rid
        self.rtype = rtype
        self.fields = fields
        # All three dicts are keyed by set name.
        self.next = {}
        self.prior = {}
        self.owner = {}

    def label(self):
        parts = []
        for key in self.fields:
            parts.append(key + "=" + str(self.fields[key]))
        return self.rtype + "#" + str(self.rid) + " " + " ".join(parts)

    def short(self):
        first = ""
        for key in self.fields:
            first = str(self.fields[key])
            break
        return self.rtype + "#" + str(self.rid) + "(" + first + ")"


class Database:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.reset()

    def reset(self):
        self.records = []            # every record ever stored
        self.calc_index = {}         # (rtype, key value) -> [records]
        self.run_unit = None         # currency: current of run unit
        self.set_currency = {}       # set name -> current record of that set
        self.hops = 0                # pointer follows
        self.reads = 0               # CALC lookups or file-scan reads
        self.status = OK
        for set_name in SCHEMA_SETS:
            self.set_currency[set_name] = None

    # ------------------------------------------------------ bookkeeping ----

    def _hop(self, src, set_name, direction, dst):
        self.hops += 1
        if self.verbose:
            print("    hop: " + src.short() + " --" + direction + "[" +
                  set_name + "]--> " + dst.short())

    def _set_currency(self, rec):
        # Any record we touch becomes current of the run unit and current of
        # every set it takes part in (as owner or as member).
        self.run_unit = rec
        for set_name in SCHEMA_SETS:
            owner_type = SCHEMA_SETS[set_name][0]
            member_type = SCHEMA_SETS[set_name][1]
            if rec.rtype == owner_type or rec.rtype == member_type:
                self.set_currency[set_name] = rec

    def _owner_of_current(self, set_name):
        # The owner of the set occurrence we are currently positioned in.
        if set_name not in SCHEMA_SETS:
            raise DBError("unknown set " + set_name)
        cur = self.set_currency[set_name]
        if cur is None:
            raise DBError("no current record for set " + set_name)
        owner_type = SCHEMA_SETS[set_name][0]
        if cur.rtype == owner_type:
            return cur
        return cur.owner[set_name]

    # ------------------------------------------------------------ STORE ----

    def store(self, rtype, fields):
        if rtype not in SCHEMA_RECORDS:
            raise DBError("unknown record type " + rtype)
        allowed = SCHEMA_RECORDS[rtype]["fields"]
        for key in fields:
            if key not in allowed:
                raise DBError(rtype + " has no field " + key)
        for key in allowed:
            if key not in fields:
                raise DBError(rtype + " needs field " + key)

        # Automatic membership: find every owner BEFORE creating anything,
        # so a failure leaves the database untouched.
        owners = {}
        for set_name in SCHEMA_SETS:
            if SCHEMA_SETS[set_name][1] == rtype:
                owners[set_name] = self._owner_of_current(set_name)

        ordered = {}
        for key in allowed:
            ordered[key] = fields[key]
        rec = Record(len(self.records) + 1, rtype, ordered)
        self.records.append(rec)

        # An owner starts with an empty ring: it points at itself.
        for set_name in SCHEMA_SETS:
            if SCHEMA_SETS[set_name][0] == rtype:
                rec.next[set_name] = rec
                rec.prior[set_name] = rec

        for set_name in owners:
            self._connect(owners[set_name], rec, set_name)

        calc = SCHEMA_RECORDS[rtype]["calc"]
        if calc is not None:
            index_key = (rtype, ordered[calc])
            if index_key not in self.calc_index:
                self.calc_index[index_key] = []
            self.calc_index[index_key].append(rec)

        self._set_currency(rec)
        self.status = OK
        return rec

    def _connect(self, owner, member, set_name):
        # Insert at the end of the ring, just before the owner.
        last = owner.prior[set_name]
        member.next[set_name] = owner
        member.prior[set_name] = last
        member.owner[set_name] = owner
        last.next[set_name] = member
        owner.prior[set_name] = member

    # ------------------------------------------------------------- FIND ----

    def find_any(self, rtype, fields):
        # Entry point into the network by CALC key (a hash lookup in IDS).
        if rtype not in SCHEMA_RECORDS:
            raise DBError("unknown record type " + rtype)
        calc = SCHEMA_RECORDS[rtype]["calc"]
        if calc is None:
            raise DBError(rtype + " has no CALC key, reach it by navigation")
        if calc not in fields:
            raise DBError("FIND ANY " + rtype + " needs " + calc + "=...")
        self.reads += 1
        matches = self.calc_index.get((rtype, fields[calc]))
        if not matches:
            self.status = NOT_FOUND
            return None
        rec = matches[0]
        self._set_currency(rec)
        self.status = OK
        return rec

    def _check_member(self, rtype, set_name):
        if set_name not in SCHEMA_SETS:
            raise DBError("unknown set " + set_name)
        if SCHEMA_SETS[set_name][1] != rtype:
            raise DBError(rtype + " is not the member type of " + set_name)

    def find_first(self, rtype, set_name):
        self._check_member(rtype, set_name)
        owner = self._owner_of_current(set_name)
        first = owner.next[set_name]
        self._hop(owner, set_name, "NEXT", first)
        if first is owner:
            self.status = END_OF_SET
            return None
        self._set_currency(first)
        self.status = OK
        return first

    def find_last(self, rtype, set_name):
        self._check_member(rtype, set_name)
        owner = self._owner_of_current(set_name)
        last = owner.prior[set_name]
        self._hop(owner, set_name, "PRIOR", last)
        if last is owner:
            self.status = END_OF_SET
            return None
        self._set_currency(last)
        self.status = OK
        return last

    def find_next(self, rtype, set_name):
        self._check_member(rtype, set_name)
        cur = self.set_currency[set_name]
        if cur is None:
            raise DBError("no current record for set " + set_name)
        nxt = cur.next[set_name]
        self._hop(cur, set_name, "NEXT", nxt)
        if nxt.rtype != rtype:
            # We walked all the way round the ring back to the owner.
            self.status = END_OF_SET
            return None
        self._set_currency(nxt)
        self.status = OK
        return nxt

    def find_prior(self, rtype, set_name):
        self._check_member(rtype, set_name)
        cur = self.set_currency[set_name]
        if cur is None:
            raise DBError("no current record for set " + set_name)
        prv = cur.prior[set_name]
        self._hop(cur, set_name, "PRIOR", prv)
        if prv.rtype != rtype:
            self.status = END_OF_SET
            return None
        self._set_currency(prv)
        self.status = OK
        return prv

    def find_owner(self, set_name):
        if set_name not in SCHEMA_SETS:
            raise DBError("unknown set " + set_name)
        cur = self.set_currency[set_name]
        if cur is None:
            raise DBError("no current record for set " + set_name)
        if cur.rtype != SCHEMA_SETS[set_name][1]:
            raise DBError("current of " + set_name + " is the owner, it has no owner")
        owner = cur.owner[set_name]
        self._hop(cur, set_name, "OWNER", owner)
        self._set_currency(owner)
        self.status = OK
        return owner

    def get(self):
        if self.run_unit is None:
            raise DBError("no current of run unit")
        return self.run_unit

    # -------------------------------------------------------- integrity ----

    def check_integrity(self):
        # Walk every ring forward and backward. Both must visit the same members.
        problems = []
        for rec in self.records:
            for set_name in SCHEMA_SETS:
                if SCHEMA_SETS[set_name][0] != rec.rtype:
                    continue
                forward = []
                cur = rec.next[set_name]
                while cur is not rec:
                    forward.append(cur.rid)
                    if cur.owner[set_name] is not rec:
                        problems.append(cur.short() + " has the wrong owner in " + set_name)
                    cur = cur.next[set_name]
                backward = []
                cur = rec.prior[set_name]
                while cur is not rec:
                    backward.append(cur.rid)
                    cur = cur.prior[set_name]
                backward.reverse()
                if forward != backward:
                    problems.append("ring " + set_name + " of " + rec.short() + " is inconsistent")
        return problems


# ------------------------------------------------------------ flat file -----
# The "before": one wide row per fact, no pointers. To answer anything you
# read rows from the top and keep the ones that match.

class FlatFile:
    def __init__(self):
        self.rows = []
        self.reads = 0

    def add(self, emp, dept, proj, hours):
        self.rows.append({"emp": emp, "dept": dept, "proj": proj, "hours": hours})

    def projects_of(self, emp):
        found = []
        for row in self.rows:
            self.reads += 1
            if row["emp"] == emp:
                found.append(row["proj"])
        return found


# ---------------------------------------------------------- DML interpreter --

SAMPLE = """
# Departments, employees, projects, and the link records that join them.
store DEPT name=Eng
store EMP name=Ann salary=50
store EMP name=Bob salary=40
store DEPT name=Sales
store EMP name=Cy salary=30
store PROJ name=Apollo
store PROJ name=Gemini

# Each ASSIGN joins ONE employee and ONE project. Set currency picks both.
find any PROJ name=Apollo
find any EMP name=Ann
store ASSIGN hours=10
find any PROJ name=Gemini
find any EMP name=Ann
store ASSIGN hours=5
find any PROJ name=Apollo
find any EMP name=Bob
store ASSIGN hours=20
find any PROJ name=Gemini
find any EMP name=Cy
store ASSIGN hours=8
"""


def parse_value(text):
    if text.lstrip("-").isdigit():
        return int(text)
    return text


def parse_fields(tokens):
    fields = {}
    for token in tokens:
        if "=" not in token:
            raise DBError("expected key=value, got " + token)
        key, value = token.split("=", 1)
        fields[key] = parse_value(value)
    return fields


def show_result(db, rec):
    if rec is None:
        return db.status
    return OK + "  " + rec.label()


def execute(db, line):
    line = line.split("#", 1)[0].strip()
    if line == "":
        return ""
    tokens = line.split()
    cmd = tokens[0].lower()
    try:
        if cmd == "store":
            rec = db.store(tokens[1].upper(), parse_fields(tokens[2:]))
            return "stored " + rec.label()
        if cmd == "find":
            return execute_find(db, tokens)
        if cmd == "get":
            return db.get().label()
        if cmd == "show":
            return execute_show(db, tokens)
        if cmd == "stats":
            return "pointer hops: " + str(db.hops) + "   CALC reads: " + str(db.reads)
        if cmd == "check":
            problems = db.check_integrity()
            if problems:
                return "\n".join(problems)
            return "all rings consistent"
        if cmd == "reset":
            db.reset()
            return "database emptied"
        if cmd == "sample":
            db.reset()
            run_script(db, SAMPLE, echo=False)
            db.hops = 0
            db.reads = 0
            return "sample company loaded (" + str(len(db.records)) + " records)"
        if cmd == "help":
            return HELP
    except IndexError:
        return "ERROR: incomplete command, try help"
    except DBError as err:
        return "ERROR: " + str(err)
    return "ERROR: unknown command " + cmd + ", try help"


def execute_find(db, tokens):
    how = tokens[1].lower()
    if how == "any":
        rec = db.find_any(tokens[2].upper(), parse_fields(tokens[3:]))
        return show_result(db, rec)
    if how == "owner":
        if tokens[2].lower() != "within":
            return "ERROR: usage: find owner within SET"
        return show_result(db, db.find_owner(tokens[3].upper()))
    if how in ("first", "next", "prior", "last"):
        if tokens[3].lower() != "within":
            return "ERROR: usage: find " + how + " RECTYPE within SET"
        rtype = tokens[2].upper()
        set_name = tokens[4].upper()
        if how == "first":
            rec = db.find_first(rtype, set_name)
        elif how == "next":
            rec = db.find_next(rtype, set_name)
        elif how == "prior":
            rec = db.find_prior(rtype, set_name)
        else:
            rec = db.find_last(rtype, set_name)
        return show_result(db, rec)
    return "ERROR: find any | first | next | prior | last | owner"


def execute_show(db, tokens):
    what = tokens[1].lower()
    if what == "currency":
        lines = []
        if db.run_unit is None:
            lines.append("run unit: (none)")
        else:
            lines.append("run unit: " + db.run_unit.short())
        for set_name in SCHEMA_SETS:
            cur = db.set_currency[set_name]
            if cur is None:
                lines.append("set " + set_name + ": (none)")
            else:
                lines.append("set " + set_name + ": " + cur.short())
        return "\n".join(lines)
    if what == "sets":
        lines = []
        for set_name in SCHEMA_SETS:
            owner_type = SCHEMA_SETS[set_name][0]
            member_type = SCHEMA_SETS[set_name][1]
            lines.append(set_name + ": owner " + owner_type + ", member " + member_type)
        return "\n".join(lines)
    if what == "all":
        lines = []
        for rec in db.records:
            lines.append(rec.label())
        return "\n".join(lines)
    if what == "rings":
        lines = []
        for rec in db.records:
            for set_name in SCHEMA_SETS:
                if SCHEMA_SETS[set_name][0] != rec.rtype:
                    continue
                chain = [rec.short()]
                cur = rec.next[set_name]
                while cur is not rec:
                    chain.append(cur.short())
                    cur = cur.next[set_name]
                chain.append(rec.short())
                lines.append(set_name + ": " + " -> ".join(chain))
        return "\n".join(lines)
    return "ERROR: show currency | sets | all | rings"


def run_script(db, text, echo=True):
    outputs = []
    for line in text.splitlines():
        stripped = line.split("#", 1)[0].strip()
        if stripped == "":
            continue
        result = execute(db, line)
        if echo:
            print("> " + stripped)
            print(result)
        outputs.append(result)
    return outputs


HELP = """commands:
  store TYPE field=value ...       new record, auto-joins the CURRENT owner of each set it belongs to
  find any TYPE key=value          CALC lookup (DEPT, EMP, PROJ have name as key)
  find first|last TYPE within SET  first or last member of the current set occurrence
  find next|prior TYPE within SET  step along the ring from the current record of that set
  find owner within SET            follow the OWNER pointer
  get                              print the current record of the run unit
  show currency|sets|rings|all     look inside
  stats  check  sample  reset  quit
types: DEPT(name) EMP(name,salary) PROJ(name) ASSIGN(hours)
sets:  DEPT-EMP  EMP-ASSIGN  PROJ-ASSIGN"""


# -------------------------------------------------------------- the demo ----

def demo_before_after():
    # Same question, two ways: "which projects does employee e17 work on?"
    db = Database()
    flat = FlatFile()
    people = 200
    projects = 20
    for p in range(projects):
        db.store("PROJ", {"name": "p" + str(p)})
    for e in range(people):
        db.store("DEPT", {"name": "d" + str(e)})
        db.store("EMP", {"name": "e" + str(e), "salary": 10})
        for k in range(3):
            proj_name = "p" + str((e + k * 7) % projects)
            db.find_any("PROJ", {"name": proj_name})
            db.find_any("EMP", {"name": "e" + str(e)})
            db.store("ASSIGN", {"hours": k + 1})
            flat.add("e" + str(e), "d" + str(e), proj_name, k + 1)

    db.hops = 0
    db.reads = 0
    names = navigate_projects_of(db, "e17")
    flat_names = flat.projects_of("e17")
    print("Question: which projects does e17 work on?")
    print("  flat file : " + str(flat_names) + "  rows read: " + str(flat.reads))
    print("  navigation: " + str(names) + "  CALC reads: " + str(db.reads) +
          ", pointer hops: " + str(db.hops))
    print("Double the employees and the flat scan doubles. The navigation does not move.")


def navigate_projects_of(db, emp_name):
    names = []
    db.find_any("EMP", {"name": emp_name})
    link = db.find_first("ASSIGN", "EMP-ASSIGN")
    while link is not None:
        proj = db.find_owner("PROJ-ASSIGN")
        names.append(proj.fields["name"])
        link = db.find_next("ASSIGN", "EMP-ASSIGN")
    return names


# ----------------------------------------------------------------- tests ----

def make_sample_db():
    db = Database()
    run_script(db, SAMPLE, echo=False)
    return db


def test_suite():
    results = []

    def check(name, condition):
        results.append((name, bool(condition)))

    # 1. Automatic membership: EMP joins the DEPT that is current.
    db = make_sample_db()
    db.find_any("EMP", {"name": "Ann"})
    check("employee Ann belongs to Eng", db.find_owner("DEPT-EMP").fields["name"] == "Eng")

    # 2. Storing a member with no current owner is refused.
    db = Database()
    try:
        db.store("EMP", {"name": "Zed", "salary": 1})
        refused = False
    except DBError:
        refused = True
    check("EMP with no current DEPT is refused", refused and len(db.records) == 0)

    # 3. FIND FIRST / NEXT walk members in insertion order.
    db = make_sample_db()
    db.find_any("DEPT", {"name": "Eng"})
    names = []
    rec = db.find_first("EMP", "DEPT-EMP")
    while rec is not None:
        names.append(rec.fields["name"])
        rec = db.find_next("EMP", "DEPT-EMP")
    check("Eng members are Ann then Bob", names == ["Ann", "Bob"])

    # 4. The walk ends with END-OF-SET, not a crash.
    check("walk ends with END-OF-SET", db.status == END_OF_SET)

    # 5. FIND LAST and FIND PRIOR walk backwards.
    db.find_any("DEPT", {"name": "Eng"})
    last = db.find_last("EMP", "DEPT-EMP")
    prior = db.find_prior("EMP", "DEPT-EMP")
    check("last is Bob, prior is Ann",
          last.fields["name"] == "Bob" and prior.fields["name"] == "Ann")

    # 6. Prior from the first member runs off the front.
    after = db.find_prior("EMP", "DEPT-EMP")
    check("prior from first is END-OF-SET", after is None and db.status == END_OF_SET)

    # 7. Many to many, employee side: Ann works on Apollo and Gemini.
    db = make_sample_db()
    check("Ann's projects", navigate_projects_of(db, "Ann") == ["Apollo", "Gemini"])

    # 8. Many to many, project side: Apollo has Ann and Bob.
    db.find_any("PROJ", {"name": "Apollo"})
    people = []
    link = db.find_first("ASSIGN", "PROJ-ASSIGN")
    while link is not None:
        people.append(db.find_owner("EMP-ASSIGN").fields["name"])
        link = db.find_next("ASSIGN", "PROJ-ASSIGN")
    check("Apollo's people", people == ["Ann", "Bob"])

    # 9. Currency per set survives a detour through another set.
    db = make_sample_db()
    db.find_any("EMP", {"name": "Ann"})
    db.find_first("ASSIGN", "EMP-ASSIGN")
    db.find_owner("PROJ-ASSIGN")
    second = db.find_next("ASSIGN", "EMP-ASSIGN")
    check("EMP-ASSIGN currency kept while visiting PROJ",
          second is not None and second.fields["hours"] == 5)

    # 10. FIND ANY on a missing key reports NOT-FOUND.
    db = make_sample_db()
    rec = db.find_any("EMP", {"name": "Nobody"})
    check("missing key gives NOT-FOUND", rec is None and db.status == NOT_FOUND)

    # 11. Empty set: FIND FIRST gives END-OF-SET.
    db = make_sample_db()
    db.find_any("EMP", {"name": "Cy"})
    db.find_owner("DEPT-EMP")
    db.store("DEPT", {"name": "Empty"})
    rec = db.find_first("EMP", "DEPT-EMP")
    check("empty set has no first member", rec is None and db.status == END_OF_SET)

    # 12. Bad input is rejected with DBError.
    db = make_sample_db()
    bad = 0
    for attempt in [lambda: db.store("NOPE", {}),
                    lambda: db.store("PROJ", {"title": "x"}),
                    lambda: db.find_any("ASSIGN", {"hours": 1}),
                    lambda: db.find_first("DEPT", "DEPT-EMP")]:
        try:
            attempt()
        except DBError:
            bad += 1
    check("four malformed requests rejected", bad == 4)

    # 13. Every ring is consistent forward and backward.
    db = make_sample_db()
    check("rings consistent", db.check_integrity() == [])

    # 14. A link record has two owners at once.
    db = make_sample_db()
    db.find_any("EMP", {"name": "Bob"})
    link = db.find_first("ASSIGN", "EMP-ASSIGN")
    check("ASSIGN has an EMP owner and a PROJ owner",
          link.owner["EMP-ASSIGN"].fields["name"] == "Bob" and
          link.owner["PROJ-ASSIGN"].fields["name"] == "Apollo")

    # 15. Navigation reads far less than a flat scan, same answer.
    db = Database()
    flat = FlatFile()
    for p in range(5):
        db.store("PROJ", {"name": "p" + str(p)})
    for e in range(100):
        db.store("DEPT", {"name": "d" + str(e)})
        db.store("EMP", {"name": "e" + str(e), "salary": 1})
        for k in range(2):
            pname = "p" + str((e + k) % 5)
            db.find_any("PROJ", {"name": pname})
            db.find_any("EMP", {"name": "e" + str(e)})
            db.store("ASSIGN", {"hours": 1})
            flat.add("e" + str(e), "d" + str(e), pname, 1)
    db.hops = 0
    db.reads = 0
    nav = navigate_projects_of(db, "e42")
    scan = flat.projects_of("e42")
    check("same answer both ways", nav == scan)
    check("navigation cost far below scan", db.hops + db.reads < flat.reads // 10)

    # 16. The DML interpreter works end to end.
    db = make_sample_db()
    out = run_script(db, "find any EMP name=Cy\nget", echo=False)
    check("script: find then get", out[1] == "EMP#5 name=Cy salary=30")

    return results


def run_tests():
    results = test_suite()
    passed = 0
    for name, ok in results:
        mark = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print("  " + mark + "  " + name)
    print(str(passed) + "/" + str(len(results)) + " passed")
    return passed == len(results)


# ------------------------------------------------------------------ main ----

def repl(verbose):
    db = Database(verbose=verbose)
    run_script(db, SAMPLE, echo=False)
    db.hops = 0
    db.reads = 0
    print("Network database ready. Sample company loaded (" +
          str(len(db.records)) + " records). Type help.")
    while True:
        try:
            line = input("dml> ")
        except EOFError:
            print()
            return
        if line.strip().lower() in ("quit", "exit"):
            return
        out = execute(db, line)
        if out != "":
            print(out)


def main(argv):
    verbose = "--verbose" in argv
    rest = []
    for arg in argv:
        if not arg.startswith("--"):
            rest.append(arg)
    if "--test" in argv:
        ok = run_tests()
        sys.exit(0 if ok else 1)
    if "--demo" in argv:
        demo_before_after()
        return
    if rest:
        db = Database(verbose=verbose)
        with open(rest[0]) as handle:
            text = handle.read()
        # Scripts start from the sample company unless they say 'reset'.
        run_script(db, SAMPLE, echo=False)
        db.hops = 0
        db.reads = 0
        run_script(db, text)
        return
    repl(verbose)


if __name__ == "__main__":
    main(sys.argv[1:])

"""
A miniature Integrated Data Store (IDS) — Charles W. Bachman's database system
at General Electric, early 1960s — and the CODASYL network model that grew
out of it.

BEFORE IDS: business data lived in sequential files on tape and cards. To
answer "which suppliers supply part P2?" a program read the whole supply
file, and for each hit it read through the supplier file to find the name.
Every question was a new batch program that touched every record.

AFTER IDS: records live on disk and point at each other. A "set" links one
OWNER record to a ring of MEMBER records through real pointers (next, prior,
owner). One record can be a member of several sets at once, so the data forms
a network, not a tree. A program finds one record directly (by a hashed CALC
key or by its database key) and then NAVIGATES by following pointers. Bachman
called this programmer "the navigator" in his 1973 Turing Award lecture. The
program keeps track of where it is with "currency indicators": the current
record of the run, of each record type, and of each set.

This file mirrors that design, not just the idea of it:
  - records are stored under integer database keys
  - each set is a circular ring of next/prior pointers through the owner
  - CALC records are located by hashing a key into a bucket
  - currency indicators decide what "find next" and "store" mean
  - the verbs are FIND, GET, STORE, MODIFY, CONNECT, DISCONNECT, ERASE
  - every record fetch is counted, so you can see what navigation costs

Pipeline:
    schema (record, set lines)
        -> Database            records, rings, hash table, currency
        -> Interpreter         one DML verb per line, loop ... end blocks
        -> printed result

Run:
    python3 implementation.py                 # interactive REPL (type 'demo')
    python3 implementation.py practice.ids    # run a script file
    python3 implementation.py --test          # self-test suite
    python3 implementation.py --verbose       # also print every record fetch
"""

import sys

VERBOSE = False

SYSTEM = "SYSTEM"       # the built-in owner for sets that hold "all of a type"
SYSTEM_KEY = 0
FIRST_KEY = 1001
BUCKETS = 7             # a tiny hash table, so collisions are visible
MAX_LOOP = 10000

OK = "OK"
END_OF_SET = "END-OF-SET"
NOT_FOUND = "NOT-FOUND"
NO_CURRENCY = "NO-CURRENCY"
DUPLICATE = "DUPLICATE-KEY"
HAS_MEMBERS = "HAS-MEMBERS"
NOT_CONNECTED = "NOT-CONNECTED"
BAD_REQUEST = "BAD-REQUEST"


class DBStatus(Exception):
    """A DML verb did not succeed. The status name plays the role of the
    DB-STATUS register a COBOL program checked after every call."""

    def __init__(self, status, message):
        Exception.__init__(self, message)
        self.status = status
        self.message = message


# ── The schema ────────────────────────────────────────────────────────────────
#
# The schema says which record types exist and which set types link them.
# A set type has exactly one owner record type and one member record type.
# Owner SYSTEM means "one big set holding every record of the member type",
# which is how a program walks all suppliers.

class Schema:
    def __init__(self):
        self.records = {}   # name -> {"fields": [...], "calc": field or None}
        self.sets = {}      # name -> {"owner", "member", "order", "sort", "insertion"}

    def add_record(self, name, fields, calc):
        if name in self.records or name == SYSTEM:
            raise DBStatus(BAD_REQUEST, "record type %s already defined" % name)
        if calc is not None and calc not in fields:
            raise DBStatus(BAD_REQUEST, "calc field %s is not a field of %s" % (calc, name))
        self.records[name] = {"fields": fields, "calc": calc}

    def add_set(self, name, owner, member, order, sort_field, insertion):
        if name in self.sets:
            raise DBStatus(BAD_REQUEST, "set %s already defined" % name)
        if owner != SYSTEM and owner not in self.records:
            raise DBStatus(BAD_REQUEST, "unknown owner record type %s" % owner)
        if member not in self.records:
            raise DBStatus(BAD_REQUEST, "unknown member record type %s" % member)
        if owner == member:
            raise DBStatus(BAD_REQUEST, "a record type cannot own itself in one set")
        if order == "sorted":
            if sort_field not in self.records[member]["fields"]:
                raise DBStatus(BAD_REQUEST, "%s is not a field of %s" % (sort_field, member))
        self.sets[name] = {"owner": owner, "member": member, "order": order,
                           "sort": sort_field, "insertion": insertion}

    def sets_owned_by(self, rtype):
        names = []
        for name in sorted(self.sets):
            if self.sets[name]["owner"] == rtype:
                names.append(name)
        return names

    def sets_with_member(self, rtype):
        names = []
        for name in sorted(self.sets):
            if self.sets[name]["member"] == rtype:
                names.append(name)
        return names


class Record:
    """One stored record. 'ring' holds the [next, prior] pointers for every
    set this record owns or belongs to. 'owner' holds, for each set this record
    is currently a member of, the database key of its owner."""

    def __init__(self, key, rtype, fields):
        self.key = key
        self.rtype = rtype
        self.fields = fields
        self.ring = {}
        self.owner = {}


def sort_value(value):
    # numbers sort before text, so a sorted set never compares int to str
    return (isinstance(value, str), value)


def hash_key(rtype, value):
    """A deterministic toy hash for CALC. Real IDS hashed the key to a page
    number; the idea is the same: compute where the record lives, do not
    search for it."""
    total = 0
    position = 1
    for ch in rtype + ":" + str(value):
        total = total + ord(ch) * position
        position = position + 1
    return total % BUCKETS


# ── The database ──────────────────────────────────────────────────────────────

class Database:
    def __init__(self, schema, verbose=False):
        self.schema = schema
        self.verbose = verbose
        self.records = {}
        self.next_key = FIRST_KEY
        self.table = []
        for i in range(BUCKETS):
            self.table.append([])
        self.reads = 0
        # currency indicators
        self.cur_run = None
        self.cur_type = {}
        self.cur_set = {}
        # the SYSTEM record owns every SYSTEM-owned set
        system = Record(SYSTEM_KEY, SYSTEM, {})
        for set_name in schema.sets_owned_by(SYSTEM):
            system.ring[set_name] = [SYSTEM_KEY, SYSTEM_KEY]
        self.records[SYSTEM_KEY] = system

    # -- low level ----------------------------------------------------------

    def fetch(self, key):
        """Read a record. Everything that follows a pointer goes through here,
        so self.reads is the cost of a navigation in record reads."""
        self.reads = self.reads + 1
        record = self.records[key]
        if self.verbose:
            print("    read #%d %s" % (key, record.rtype))
        return record

    def _set(self, set_name):
        if set_name not in self.schema.sets:
            raise DBStatus(BAD_REQUEST, "unknown set %s" % set_name)
        return self.schema.sets[set_name]

    def _owner_key(self, set_name):
        """Who owns the set occurrence the program is positioned in? Answered
        from currency: the current of the set is either the owner or one of
        its members."""
        info = self._set(set_name)
        if info["owner"] == SYSTEM:
            return SYSTEM_KEY
        key = self.cur_set.get(set_name)
        if key is None:
            raise DBStatus(NO_CURRENCY, "no current record of set %s" % set_name)
        record = self.records[key]
        if record.rtype == info["owner"]:
            return key
        return record.owner[set_name]

    def _make_current(self, record):
        """The currency rule. A record just found or stored becomes the
        current of the run unit, of its record type, and of every set it owns
        or is connected into."""
        self.cur_run = record.key
        self.cur_type[record.rtype] = record.key
        for set_name in self.schema.sets_owned_by(record.rtype):
            self.cur_set[set_name] = record.key
        for set_name in record.owner:
            self.cur_set[set_name] = record.key

    # -- the ring -----------------------------------------------------------

    def _link(self, record, set_name, owner_key):
        """Put a record into a set's ring. The ring runs owner -> member1 ->
        ... -> memberN -> owner, with prior pointers the other way."""
        info = self._set(set_name)
        owner = self.records[owner_key]
        # 'before' is the record the new one will sit just in front of
        before_key = owner_key
        if info["order"] == "first":
            before_key = owner.ring[set_name][0]
        elif info["order"] == "sorted":
            before_key = owner.ring[set_name][0]
            while before_key != owner_key:
                candidate = self.fetch(before_key)
                if sort_value(candidate.fields[info["sort"]]) > sort_value(record.fields[info["sort"]]):
                    break
                before_key = candidate.ring[set_name][0]
        before = self.records[before_key]
        after_key = before.ring[set_name][1]
        after = self.records[after_key]
        record.ring[set_name] = [before_key, after_key]
        before.ring[set_name][1] = record.key
        after.ring[set_name][0] = record.key
        record.owner[set_name] = owner_key

    def _unlink(self, record, set_name):
        next_key = record.ring[set_name][0]
        prior_key = record.ring[set_name][1]
        self.records[prior_key].ring[set_name][0] = next_key
        self.records[next_key].ring[set_name][1] = prior_key
        del record.ring[set_name]
        del record.owner[set_name]

    def members_of(self, set_name, owner_key):
        """Keys of the members in ring order, read without counting."""
        keys = []
        key = self.records[owner_key].ring[set_name][0]
        while key != owner_key:
            keys.append(key)
            key = self.records[key].ring[set_name][0]
        return keys

    # -- CALC hashing -------------------------------------------------------

    def _calc_bucket(self, rtype, value):
        return self.table[hash_key(rtype, value)]

    # -- the DML verbs ------------------------------------------------------

    def store(self, rtype, values):
        if rtype not in self.schema.records:
            raise DBStatus(BAD_REQUEST, "unknown record type %s" % rtype)
        info = self.schema.records[rtype]
        for name in values:
            if name not in info["fields"]:
                raise DBStatus(BAD_REQUEST, "%s has no field %s" % (rtype, name))
        fields = {}
        for name in info["fields"]:
            fields[name] = values.get(name, "")
        # check everything before changing anything, so STORE is all or nothing
        calc = info["calc"]
        if calc is not None:
            if fields[calc] == "":
                raise DBStatus(BAD_REQUEST, "%s needs a value for its calc key %s" % (rtype, calc))
            if self._calc_lookup(rtype, fields[calc]) is not None:
                raise DBStatus(DUPLICATE, "%s %s already exists" % (rtype, fields[calc]))
        owners = {}
        for set_name in self.schema.sets_with_member(rtype):
            if self.schema.sets[set_name]["insertion"] == "automatic":
                owners[set_name] = self._owner_key(set_name)
        key = self.next_key
        self.next_key = self.next_key + 1
        record = Record(key, rtype, fields)
        self.records[key] = record
        for set_name in self.schema.sets_owned_by(rtype):
            record.ring[set_name] = [key, key]
        if calc is not None:
            self._calc_bucket(rtype, fields[calc]).append(key)
        for set_name in sorted(owners):
            self._link(record, set_name, owners[set_name])
        self._make_current(record)
        return record

    def _calc_lookup(self, rtype, value):
        """Walk one hash bucket. Each entry costs one read."""
        bucket = self._calc_bucket(rtype, value)
        calc = self.schema.records[rtype]["calc"]
        for key in bucket:
            record = self.fetch(key)
            if record.rtype == rtype and str(record.fields[calc]) == str(value):
                return record
        return None

    def find_calc(self, rtype, value):
        if rtype not in self.schema.records:
            raise DBStatus(BAD_REQUEST, "unknown record type %s" % rtype)
        if self.schema.records[rtype]["calc"] is None:
            raise DBStatus(BAD_REQUEST, "%s has no calc key" % rtype)
        record = self._calc_lookup(rtype, value)
        if record is None:
            raise DBStatus(NOT_FOUND, "no %s with key %s" % (rtype, value))
        self._make_current(record)
        return record

    def find_key(self, key):
        if key not in self.records or key == SYSTEM_KEY:
            raise DBStatus(NOT_FOUND, "no record with database key %d" % key)
        record = self.fetch(key)
        self._make_current(record)
        return record

    def find_position(self, which, set_name):
        """FIND FIRST / LAST / NEXT / PRIOR within a set."""
        owner_key = self._owner_key(set_name)
        if which == "first" or which == "last":
            start_key = owner_key
        else:
            start_key = self.cur_set[set_name] if self.schema.sets[set_name]["owner"] != SYSTEM \
                else self.cur_set.get(set_name, SYSTEM_KEY)
        direction = 0
        if which == "last" or which == "prior":
            direction = 1
        start = self.fetch(start_key)
        target_key = start.ring[set_name][direction]
        if target_key == owner_key:
            raise DBStatus(END_OF_SET, "no %s member in set %s" % (which, set_name))
        record = self.fetch(target_key)
        self._make_current(record)
        return record

    def find_owner(self, set_name):
        owner_key = self._owner_key(set_name)
        if owner_key == SYSTEM_KEY:
            raise DBStatus(BAD_REQUEST, "set %s is owned by SYSTEM, there is no owner record" % set_name)
        record = self.fetch(owner_key)
        self._make_current(record)
        return record

    def get(self):
        if self.cur_run is None:
            raise DBStatus(NO_CURRENCY, "no current record of the run unit")
        return self.records[self.cur_run]

    def modify(self, values):
        record = self.get()
        info = self.schema.records[record.rtype]
        for name in values:
            if name not in info["fields"]:
                raise DBStatus(BAD_REQUEST, "%s has no field %s" % (record.rtype, name))
            if name == info["calc"]:
                raise DBStatus(BAD_REQUEST, "cannot modify the calc key %s" % name)
            for set_name in record.owner:
                set_info = self.schema.sets[set_name]
                if set_info["order"] == "sorted" and set_info["sort"] == name:
                    raise DBStatus(BAD_REQUEST, "%s orders set %s, disconnect first" % (name, set_name))
        for name in values:
            record.fields[name] = values[name]
        return record

    def connect(self, set_name):
        record = self.get()
        info = self._set(set_name)
        if record.rtype != info["member"]:
            raise DBStatus(BAD_REQUEST, "%s is not a member type of %s" % (record.rtype, set_name))
        if set_name in record.owner:
            raise DBStatus(BAD_REQUEST, "already connected to %s" % set_name)
        owner_key = self._owner_key(set_name)
        self._link(record, set_name, owner_key)
        self._make_current(record)
        return record

    def disconnect(self, set_name):
        record = self.get()
        self._set(set_name)
        if set_name not in record.owner:
            raise DBStatus(NOT_CONNECTED, "%s #%d is not in set %s" % (record.rtype, record.key, set_name))
        owner_key = record.owner[set_name]
        self._unlink(record, set_name)
        # currency of the set falls back to the owner so you can keep walking
        self.cur_set[set_name] = owner_key
        return record

    def erase(self, erase_all=False):
        record = self.get()
        self._erase_record(record, erase_all)

    def _erase_record(self, record, erase_all):
        owned = self.schema.sets_owned_by(record.rtype)
        if not erase_all:
            for set_name in owned:
                if len(self.members_of(set_name, record.key)) > 0:
                    raise DBStatus(HAS_MEMBERS, "%s #%d still owns members in %s (use erase all)"
                                   % (record.rtype, record.key, set_name))
        for set_name in owned:
            for member_key in self.members_of(set_name, record.key):
                if member_key in self.records:
                    self._erase_record(self.records[member_key], True)
        for set_name in list(record.owner.keys()):
            self._unlink(record, set_name)
        calc = self.schema.records[record.rtype]["calc"]
        if calc is not None:
            self._calc_bucket(record.rtype, record.fields[calc]).remove(record.key)
        del self.records[record.key]
        if self.cur_run == record.key:
            self.cur_run = None
        if self.cur_type.get(record.rtype) == record.key:
            del self.cur_type[record.rtype]
        for set_name in list(self.cur_set.keys()):
            if self.cur_set[set_name] == record.key:
                del self.cur_set[set_name]

    # -- checks and views ---------------------------------------------------

    def check_integrity(self):
        """Verify every invariant the pointers should keep. Returns a list of
        problems; an empty list means the database is sound. Reads are not
        counted."""
        problems = []
        seen = {}
        for set_name in self.schema.sets:
            info = self.schema.sets[set_name]
            owner_keys = []
            for key in self.records:
                if self.records[key].rtype == info["owner"]:
                    owner_keys.append(key)
            for owner_key in owner_keys:
                owner = self.records[owner_key]
                if set_name not in owner.ring:
                    problems.append("owner #%d has no ring for %s" % (owner_key, set_name))
                    continue
                key = owner.ring[set_name][0]
                previous = owner_key
                steps = 0
                last_sort = None
                while key != owner_key:
                    steps = steps + 1
                    if steps > len(self.records) + 1 or key not in self.records:
                        problems.append("ring %s of #%d is broken or loops" % (set_name, owner_key))
                        break
                    member = self.records[key]
                    if member.rtype != info["member"]:
                        problems.append("#%d in %s has wrong type" % (key, set_name))
                    if member.ring[set_name][1] != previous:
                        problems.append("prior pointer of #%d in %s is wrong" % (key, set_name))
                    if member.owner.get(set_name) != owner_key:
                        problems.append("owner pointer of #%d in %s is wrong" % (key, set_name))
                    if (set_name, key) in seen:
                        problems.append("#%d appears twice in %s" % (key, set_name))
                    seen[(set_name, key)] = True
                    if info["order"] == "sorted":
                        value = sort_value(member.fields[info["sort"]])
                        if last_sort is not None and value < last_sort:
                            problems.append("set %s is out of order at #%d" % (set_name, key))
                        last_sort = value
                    previous = key
                    key = member.ring[set_name][0]
                if key == owner_key and owner.ring[set_name][1] != previous:
                    problems.append("owner #%d prior pointer in %s is wrong" % (owner_key, set_name))
        for key in self.records:
            record = self.records[key]
            for set_name in record.owner:
                if (set_name, key) not in seen:
                    problems.append("#%d claims membership of %s but is in no ring" % (key, set_name))
        in_table = 0
        for bucket in self.table:
            for key in bucket:
                in_table = in_table + 1
                if key not in self.records:
                    problems.append("hash table points at missing #%d" % key)
        with_calc = 0
        for key in self.records:
            record = self.records[key]
            if key != SYSTEM_KEY and self.schema.records[record.rtype]["calc"] is not None:
                with_calc = with_calc + 1
        if in_table != with_calc:
            problems.append("hash table holds %d entries but %d records have a calc key" % (in_table, with_calc))
        return problems

    def describe(self, record):
        parts = []
        for name in self.schema.records[record.rtype]["fields"]:
            parts.append("%s=%s" % (name, record.fields[name]))
        return "%s #%d  %s" % (record.rtype, record.key, "  ".join(parts))

    def dump_sets(self):
        lines = []
        for set_name in sorted(self.schema.sets):
            info = self.schema.sets[set_name]
            lines.append("set %s  (%s owns %s, order %s%s, insertion %s)" % (
                set_name, info["owner"], info["member"], info["order"],
                " " + info["sort"] if info["order"] == "sorted" else "", info["insertion"]))
            for key in sorted(self.records):
                owner = self.records[key]
                if owner.rtype != info["owner"]:
                    continue
                label = "SYSTEM" if key == SYSTEM_KEY else "%s #%d" % (owner.rtype, key)
                chain = ["[%s]" % label]
                for member_key in self.members_of(set_name, key):
                    chain.append("#%d" % member_key)
                chain.append("[%s]" % label)
                lines.append("  " + " -> ".join(chain))
        return lines

    def dump_currency(self):
        lines = []
        run = "none" if self.cur_run is None else "#%d" % self.cur_run
        lines.append("current of run unit: %s" % run)
        for rtype in sorted(self.cur_type):
            lines.append("current of record %s: #%d" % (rtype, self.cur_type[rtype]))
        for set_name in sorted(self.cur_set):
            lines.append("current of set %s: #%d" % (set_name, self.cur_set[set_name]))
        return lines


# ── Flat files: the "before" ─────────────────────────────────────────────────

def export_flat_files(db):
    """Flatten the network into the three sequential files a 1950s shop would
    have had: a supplier file, a part file, and a supply file whose records
    carry the supplier number and part number as plain data (no pointers).
    Only works for the supplier/part/supply schema in DEMO_SCHEMA."""
    suppliers = []
    parts = []
    supplies = []
    for key in sorted(db.records):
        record = db.records[key]
        if record.rtype == "SUPPLIER":
            suppliers.append(dict(record.fields))
        elif record.rtype == "PART":
            parts.append(dict(record.fields))
        elif record.rtype == "SUPPLY":
            supplier = db.records[record.owner["SUPPLIER-SUPPLY"]]
            part = db.records[record.owner["PART-SUPPLY"]]
            supplies.append({"sno": supplier.fields["sno"], "pno": part.fields["pno"],
                             "qty": record.fields["qty"]})
    return suppliers, parts, supplies


def flat_file_query(suppliers, parts, supplies, pno):
    """Which suppliers supply part pno? With sequential files: read every
    supply record, and for each match, read the supplier file from the top
    until the supplier turns up. Returns (names, records_read)."""
    reads = 0
    names = []
    for supply in supplies:
        reads = reads + 1
        if supply["pno"] != pno:
            continue
        for supplier in suppliers:
            reads = reads + 1
            if supplier["sno"] == supply["sno"]:
                names.append(supplier["name"])
                break
    return names, reads


def navigate_query(db, pno):
    """The same question the IDS way: one CALC find, then walk the ring of
    supplies for that part, hopping to each supply's supplier owner. Returns
    (names, records_read)."""
    before = db.reads
    names = []
    db.find_calc("PART", pno)
    while True:
        try:
            db.find_position("next", "PART-SUPPLY")
        except DBStatus as status:
            if status.status == END_OF_SET:
                break
            raise
        supplier = db.find_owner("SUPPLIER-SUPPLY")
        names.append(supplier.fields["name"])
    return names, db.reads - before


# ── The command interpreter ──────────────────────────────────────────────────
#
# One verb per line, the way a COBOL program issued one DML call per statement.
#
#   record SUPPLIER sno name city calc sno
#   set SUPPLIER-SUPPLY owner SUPPLIER member SUPPLY order last
#   store SUPPLIER sno=S1 name=Smith city=London
#   find calc SUPPLIER S1          find key 1001
#   find first|last|next|prior within SET
#   find owner within SET
#   get    modify f=v    connect SET    disconnect SET    erase [all]
#   loop ... end                   repeat until a command fails

HELP = """\
Schema (before the first store):
  record NAME field field ... [calc FIELD]
  set NAME owner REC|SYSTEM member REC [order first|last|sorted FIELD] [insertion manual]
Navigate and change:
  store REC f=v ...              create a record (auto-connects to the current owner of its sets)
  find calc REC KEY              hash straight to a record
  find key N                     go to a database key
  find first|last|next|prior within SET
  find owner within SET
  get                            print the current record of the run unit
  modify f=v ...                 change fields of the current record
  connect SET / disconnect SET   move the current record in or out of a set
  erase [all]                    delete the current record (all = and its members)
  loop ... end                   repeat the body until a command fails
Look inside:
  currency   sets   schema   stats   status
Other:
  demo (load suppliers, parts, supplies)   new   verbose on|off   help   quit"""

DEMO_SCHEMA = """\
record SUPPLIER sno name city calc sno
record PART pno name calc pno
record SUPPLY qty
set ALL-SUPPLIERS owner SYSTEM member SUPPLIER order sorted sno
set ALL-PARTS owner SYSTEM member PART order sorted pno
set SUPPLIER-SUPPLY owner SUPPLIER member SUPPLY order last
set PART-SUPPLY owner PART member SUPPLY order last"""

DEMO_DATA = """\
store SUPPLIER sno=S1 name=Smith city=London
store SUPPLIER sno=S2 name=Jones city=Paris
store SUPPLIER sno=S3 name=Blake city=Paris
store PART pno=P1 name=Nut
store PART pno=P2 name=Bolt
store PART pno=P3 name=Screw
find calc SUPPLIER S1
find calc PART P1
store SUPPLY qty=300
find calc PART P2
store SUPPLY qty=200
find calc PART P3
store SUPPLY qty=400
find calc SUPPLIER S2
find calc PART P1
store SUPPLY qty=300
find calc PART P2
store SUPPLY qty=400
find calc SUPPLIER S3
find calc PART P2
store SUPPLY qty=200"""

BANNER = """\
Mini IDS — Bachman's Integrated Data Store, in miniature.
Type 'demo' to load suppliers, parts and supplies. 'help' lists the verbs."""


def parse_values(tokens):
    values = {}
    for token in tokens:
        if "=" not in token:
            raise DBStatus(BAD_REQUEST, "expected field=value, got '%s'" % token)
        name, value = token.split("=", 1)
        if value.lstrip("-").isdigit():
            values[name] = int(value)
        else:
            values[name] = value
    return values


def split_blocks(lines):
    """Turn a flat list of lines into nested items: a line is a string, a
    loop is ('loop', [items])."""
    stack = [[]]
    for line in lines:
        if line == "loop":
            stack.append([])
        elif line == "end":
            if len(stack) == 1:
                raise DBStatus(BAD_REQUEST, "'end' without 'loop'")
            body = stack.pop()
            stack[-1].append(("loop", body))
        else:
            stack[-1].append(line)
    if len(stack) != 1:
        raise DBStatus(BAD_REQUEST, "'loop' without 'end'")
    return stack[0]


class Interpreter:
    def __init__(self, out=print, verbose=False):
        self.out = out
        self.verbose = verbose
        self.status = OK
        self.reset()

    def reset(self):
        self.schema = Schema()
        self.db = None

    def _need_db(self):
        if self.db is None:
            if len(self.schema.records) == 0:
                raise DBStatus(BAD_REQUEST, "define a schema first (or type 'demo')")
            self.db = Database(self.schema, self.verbose)
        return self.db

    def run_line(self, line):
        """Run one command. Returns True if it succeeded, False if it failed
        with a status (a loop uses that to stop)."""
        line = line.split("#")[0].strip()
        if line == "":
            return True
        try:
            self._dispatch(line)
            self.status = OK
            return True
        except DBStatus as status:
            self.status = status.status
            self.out("  status: %s  (%s)" % (status.status, status.message))
            return False

    def run_items(self, items):
        for item in items:
            if isinstance(item, tuple):
                self._run_loop(item[1])
            else:
                self.out("ids> " + item)
                self.run_line(item)

    def _run_loop(self, body):
        for count in range(MAX_LOOP):
            for item in body:
                if isinstance(item, tuple):
                    self._run_loop(item[1])
                    self.status = OK
                    continue
                self.out("ids>   " + item)
                if not self.run_line(item):
                    self.out("  (loop ends: %s)" % self.status)
                    return
        self.out("  (loop stopped after %d passes)" % MAX_LOOP)

    def run_text(self, text):
        lines = []
        for raw in text.splitlines():
            line = raw.split("#")[0].strip()
            if line != "":
                lines.append(line)
        self.run_items(split_blocks(lines))

    def _dispatch(self, line):
        tokens = line.split()
        verb = tokens[0].lower()
        args = tokens[1:]

        if verb == "help":
            self.out(HELP)
        elif verb == "demo":
            self._demo()
        elif verb == "new":
            self.reset()
            self.out("  schema cleared")
        elif verb == "verbose":
            on = len(args) > 0 and args[0] == "on"
            self.verbose = on
            if self.db is not None:
                self.db.verbose = on
            self.out("  verbose %s" % ("on" if on else "off"))
        elif verb == "record":
            self._need_schema_open()
            self._define_record(args)
        elif verb == "set":
            self._need_schema_open()
            self._define_set(args)
        elif verb == "schema":
            self._show_schema()
        elif verb == "status":
            self.out("  last status: %s" % self.status)
        else:
            self._dml(verb, args)

    def _need_schema_open(self):
        if self.db is not None:
            raise DBStatus(BAD_REQUEST, "schema is frozen once data exists; type 'new' to start over")

    def _define_record(self, args):
        if len(args) < 2:
            raise DBStatus(BAD_REQUEST, "usage: record NAME field ... [calc FIELD]")
        name = args[0]
        rest = args[1:]
        calc = None
        if "calc" in rest:
            at = rest.index("calc")
            if at + 1 >= len(rest):
                raise DBStatus(BAD_REQUEST, "calc needs a field name")
            calc = rest[at + 1]
            rest = rest[:at] + rest[at + 2:]
        self.schema.add_record(name, rest, calc)
        self.out("  record %s defined" % name)

    def _define_set(self, args):
        if len(args) < 5 or args[1] != "owner" or args[3] != "member":
            raise DBStatus(BAD_REQUEST, "usage: set NAME owner REC|SYSTEM member REC [order ...] [insertion manual]")
        name = args[0]
        owner = args[2]
        member = args[4]
        order = "last"
        sort_field = None
        insertion = "automatic"
        i = 5
        while i < len(args):
            if args[i] == "order" and i + 1 < len(args):
                order = args[i + 1]
                i = i + 2
                if order == "sorted":
                    if i >= len(args):
                        raise DBStatus(BAD_REQUEST, "order sorted needs a field")
                    sort_field = args[i]
                    i = i + 1
                elif order not in ("first", "last"):
                    raise DBStatus(BAD_REQUEST, "order must be first, last or sorted FIELD")
            elif args[i] == "insertion" and i + 1 < len(args):
                insertion = args[i + 1]
                if insertion not in ("automatic", "manual"):
                    raise DBStatus(BAD_REQUEST, "insertion must be automatic or manual")
                i = i + 2
            else:
                raise DBStatus(BAD_REQUEST, "unexpected '%s' in set definition" % args[i])
        self.schema.add_set(name, owner, member, order, sort_field, insertion)
        self.out("  set %s defined" % name)

    def _show_schema(self):
        if len(self.schema.records) == 0:
            self.out("  (no schema yet)")
        for name in self.schema.records:
            info = self.schema.records[name]
            calc = ""
            if info["calc"] is not None:
                calc = "   calc key: %s" % info["calc"]
            self.out("  record %s (%s)%s" % (name, ", ".join(info["fields"]), calc))
        for name in self.schema.sets:
            info = self.schema.sets[name]
            self.out("  set %s: %s owns %s" % (name, info["owner"], info["member"]))

    def _demo(self):
        self.reset()
        for line in DEMO_SCHEMA.splitlines():
            self.run_line(line)
        for line in DEMO_DATA.splitlines():
            self.run_line(line)
        self.out("  demo loaded: 3 suppliers, 3 parts, 6 supplies")
        self.out("  try:  find calc PART P2   then   find next within PART-SUPPLY")

    def _dml(self, verb, args):
        db = self._need_db()
        if verb == "store":
            if len(args) < 1:
                raise DBStatus(BAD_REQUEST, "usage: store REC f=v ...")
            record = db.store(args[0], parse_values(args[1:]))
            self.out("  stored " + db.describe(record))
        elif verb == "find":
            self._find(db, args)
        elif verb == "get":
            self.out("  " + db.describe(db.get()))
        elif verb == "modify":
            record = db.modify(parse_values(args))
            self.out("  modified " + db.describe(record))
        elif verb == "connect":
            self._one_arg(verb, args)
            record = db.connect(args[0])
            self.out("  connected #%d into %s" % (record.key, args[0]))
        elif verb == "disconnect":
            self._one_arg(verb, args)
            record = db.disconnect(args[0])
            self.out("  disconnected #%d from %s" % (record.key, args[0]))
        elif verb == "erase":
            record = db.get()
            db.erase(len(args) > 0 and args[0] == "all")
            self.out("  erased %s #%d" % (record.rtype, record.key))
        elif verb == "currency":
            for line in db.dump_currency():
                self.out("  " + line)
        elif verb == "sets":
            for line in db.dump_sets():
                self.out("  " + line)
        elif verb == "stats":
            self.out("  records: %d   reads so far: %d" % (len(db.records) - 1, db.reads))
        else:
            raise DBStatus(BAD_REQUEST, "unknown command '%s' (try 'help')" % verb)

    def _one_arg(self, verb, args):
        if len(args) != 1:
            raise DBStatus(BAD_REQUEST, "usage: %s SET" % verb)

    def _find(self, db, args):
        if len(args) == 0:
            raise DBStatus(BAD_REQUEST, "usage: find calc|key|first|last|next|prior|owner ...")
        how = args[0].lower()
        if how == "calc" and len(args) == 3:
            record = db.find_calc(args[1], args[2])
        elif how == "key" and len(args) == 2 and args[1].isdigit():
            record = db.find_key(int(args[1]))
        elif how in ("first", "last", "next", "prior") and len(args) == 3 and args[1] == "within":
            record = db.find_position(how, args[2])
        elif how == "owner" and len(args) == 3 and args[1] == "within":
            record = db.find_owner(args[2])
        else:
            raise DBStatus(BAD_REQUEST, "usage: find calc REC KEY | key N | first|last|next|prior|owner within SET")
        self.out("  found " + db.describe(record))


# ── REPL and script runner ───────────────────────────────────────────────────

def repl():
    interp = Interpreter(verbose=VERBOSE)
    print(BANNER)
    pending = []
    depth = 0
    while True:
        try:
            line = input("ids> " if depth == 0 else "...  ")
        except EOFError:
            print()
            return
        line = line.split("#")[0].strip()
        if line == "":
            continue
        if line.lower() in ("quit", "exit"):
            return
        if line == "loop":
            depth = depth + 1
        if depth > 0:
            pending.append(line)
            if line == "end":
                depth = depth - 1
                if depth == 0:
                    try:
                        interp.run_items(split_blocks(pending))
                    except DBStatus as status:
                        print("error: %s" % status.message)
                    pending = []
            continue
        interp.run_line(line)


def run_file(path):
    interp = Interpreter(verbose=VERBOSE)
    with open(path) as source_file:
        text = source_file.read()
    try:
        interp.run_text(text)
    except DBStatus as status:
        print("error: %s" % status.message)


# ── Self-test suite ──────────────────────────────────────────────────────────

def build_demo():
    interp = Interpreter(out=lambda text: None)
    interp.run_text(DEMO_SCHEMA)
    interp.run_text(DEMO_DATA)
    return interp


def run_tests():
    passed = 0
    total = 0

    def check(name, condition):
        nonlocal passed, total
        total = total + 1
        if condition:
            passed = passed + 1
            print("  PASS  " + name)
        else:
            print("  FAIL  " + name)

    def status_of(db, action):
        try:
            action()
        except DBStatus as status:
            return status.status
        return OK

    print("Running tests\n")

    # 1. CALC find lands on the right record
    demo = build_demo()
    db = demo.db
    record = db.find_calc("SUPPLIER", "S2")
    check("find calc returns the supplier with that key", record.fields["name"] == "Jones")

    # 2. missing CALC key
    check("find calc on a missing key reports NOT-FOUND",
          status_of(db, lambda: db.find_calc("SUPPLIER", "S99")) == NOT_FOUND)

    # 3. duplicate CALC key
    check("storing a duplicate calc key is refused",
          status_of(db, lambda: db.store("SUPPLIER", {"sno": "S1", "name": "X", "city": "Y"})) == DUPLICATE)

    # 4. set order last, walk with next
    db.find_calc("PART", "P2")
    names = []
    while True:
        try:
            db.find_position("next", "PART-SUPPLY")
        except DBStatus:
            break
        names.append(db.find_owner("SUPPLIER-SUPPLY").fields["name"])
    check("walking PART-SUPPLY for P2 reaches Smith, Jones, Blake in store order",
          names == ["Smith", "Jones", "Blake"])

    # 5. end of set
    check("find next past the last member reports END-OF-SET",
          status_of(db, lambda: db.find_position("next", "PART-SUPPLY")) == END_OF_SET)

    # 6. first and last
    db.find_calc("PART", "P2")
    first = db.find_position("first", "PART-SUPPLY")
    db.find_calc("PART", "P2")
    last = db.find_position("last", "PART-SUPPLY")
    check("first and last members of P2's supplies are different records",
          first.key != last.key and first.fields["qty"] == 200 and last.fields["qty"] == 200)

    # 7. prior from the last member walks backward
    prior = db.find_position("prior", "PART-SUPPLY")
    check("prior from the last member lands on the middle one",
          prior.fields["qty"] == 400)

    # 8. the network: one supply record is a member of two sets
    supply = db.get()
    supplier = db.find_owner("SUPPLIER-SUPPLY")
    db.find_key(supply.key)
    part = db.find_owner("PART-SUPPLY")
    check("one supply record reaches both its supplier and its part",
          supplier.fields["sno"] == "S2" and part.fields["pno"] == "P2")

    # 9. SYSTEM set walks every supplier in sorted order
    sorted_names = []
    db.cur_set.pop("ALL-SUPPLIERS", None)
    db.find_position("first", "ALL-SUPPLIERS")
    sorted_names.append(db.get().fields["sno"])
    while True:
        try:
            db.find_position("next", "ALL-SUPPLIERS")
        except DBStatus:
            break
        sorted_names.append(db.get().fields["sno"])
    check("a SYSTEM-owned sorted set lists all suppliers in order",
          sorted_names == ["S1", "S2", "S3"])

    # 10. currency rule
    db.find_calc("SUPPLIER", "S3")
    check("finding a supplier makes it current of the run unit and its sets",
          db.cur_run == db.cur_set["SUPPLIER-SUPPLY"] == db.cur_set["ALL-SUPPLIERS"] == db.cur_type["SUPPLIER"])

    # 11. automatic store needs currency
    fresh = Interpreter(out=lambda text: None)
    fresh.run_text(DEMO_SCHEMA)
    fresh.run_line("store SUPPLIER sno=S1 name=Smith city=London")
    fresh.run_line("store PART pno=P1 name=Nut")
    # the last store was a part, so PART-SUPPLY has currency but SUPPLIER-SUPPLY
    # currency is still on S1 (stored earlier). Clear it to test the refusal.
    fresh.db.cur_set.pop("SUPPLIER-SUPPLY")
    ok = fresh.run_line("store SUPPLY qty=1")
    check("storing a member with no owner currency is refused with NO-CURRENCY",
          ok is False and fresh.status == NO_CURRENCY and len(fresh.db.members_of("PART-SUPPLY", fresh.db.cur_type["PART"])) == 0)

    # 12. manual insertion, connect and disconnect
    manual = Interpreter(out=lambda text: None)
    manual.run_text("""
        record DEPT dno name calc dno
        record EMP eno name calc eno
        set DEPT-EMP owner DEPT member EMP order sorted name insertion manual
    """)
    manual.run_text("""
        store DEPT dno=D1 name=Research
        store EMP eno=E1 name=Zed
        store EMP eno=E2 name=Amy
        find calc DEPT D1
        find calc EMP E1
        connect DEPT-EMP
        find calc EMP E2
        connect DEPT-EMP
    """)
    mdb = manual.db
    dept_key = mdb.cur_type["DEPT"]
    ordered = []
    for key in mdb.members_of("DEPT-EMP", dept_key):
        ordered.append(mdb.records[key].fields["name"])
    check("connect into a sorted manual set keeps names in order", ordered == ["Amy", "Zed"])
    manual.run_text("disconnect DEPT-EMP")
    check("disconnect removes the record from the ring",
          len(mdb.members_of("DEPT-EMP", dept_key)) == 1 and mdb.check_integrity() == [])

    # 13. modify
    demo = build_demo()
    db = demo.db
    db.find_calc("SUPPLIER", "S1")
    db.modify({"city": "Oslo"})
    check("modify changes a field of the current record", db.get().fields["city"] == "Oslo")
    check("modify refuses to change the calc key",
          status_of(db, lambda: db.modify({"sno": "S9"})) == BAD_REQUEST)

    # 14. erase a member keeps rings sound
    db.find_calc("PART", "P2")
    db.find_position("first", "PART-SUPPLY")
    db.erase()
    check("erasing a supply unlinks it from both of its sets",
          len(db.members_of("PART-SUPPLY", db.cur_type["PART"])) == 2 and db.check_integrity() == [])

    # 15. erase an owner with members is refused, erase all cascades
    db.find_calc("SUPPLIER", "S2")
    check("erasing an owner that still has members is refused",
          status_of(db, db.erase) == HAS_MEMBERS)
    before_count = len(db.records)
    db.erase(True)
    check("erase all removes the owner and its members",
          len(db.records) == before_count - 3 and db.check_integrity() == [])

    # 16. navigation agrees with the flat file query
    demo = build_demo()
    db = demo.db
    suppliers, parts, supplies = export_flat_files(db)
    flat_names, flat_reads = flat_file_query(suppliers, parts, supplies, "P2")
    nav_names, nav_reads = navigate_query(db, "P2")
    check("navigation and sequential files give the same suppliers for P2",
          sorted(flat_names) == sorted(nav_names) and len(nav_names) == 3)

    # 17. at scale, navigation reads far fewer records
    big = Interpreter(out=lambda text: None)
    big.run_text(DEMO_SCHEMA)
    big.run_line("store PART pno=P0 name=Seed")
    bdb = big.db
    for s in range(60):
        bdb.store("SUPPLIER", {"sno": "S%d" % s, "name": "N%d" % s, "city": "C"})
        for p in range(1, 10):
            part_key = "P%d" % p
            if bdb._calc_lookup("PART", part_key) is None:
                bdb.store("PART", {"pno": part_key, "name": "part%d" % p})
            bdb.find_calc("SUPPLIER", "S%d" % s)
            bdb.find_calc("PART", part_key)
            bdb.store("SUPPLY", {"qty": s + p})
    bsup, bpart, bsupply = export_flat_files(bdb)
    flat_names, flat_reads = flat_file_query(bsup, bpart, bsupply, "P3")
    nav_names, nav_reads = navigate_query(bdb, "P3")
    check("at 60 suppliers navigation returns the same answer", sorted(flat_names) == sorted(nav_names))
    check("at 60 suppliers navigation reads under a tenth of what the flat files read",
          nav_reads * 10 < flat_reads)

    # 18. integrity after a pile of mixed operations
    check("pointer rings, hash table and owners are consistent after the big load",
          bdb.check_integrity() == [])
    for s in range(0, 60, 3):
        bdb.find_calc("SUPPLIER", "S%d" % s)
        bdb.erase(True)
    check("integrity still holds after erase-all on every third supplier",
          bdb.check_integrity() == [] and bdb._calc_lookup("SUPPLIER", "S3") is None)

    # 19. loop blocks in the interpreter
    collected = []
    looper = Interpreter(out=collected.append)
    looper.run_text(DEMO_SCHEMA)
    looper.run_text(DEMO_DATA)
    del collected[:]
    looper.run_text("""
        find calc PART P2
        loop
          find next within PART-SUPPLY
          find owner within SUPPLIER-SUPPLY
          get
        end
    """)
    got = [line for line in collected if line.strip().startswith("SUPPLIER #")]
    check("a loop block walks all three suppliers of P2 and stops at END-OF-SET",
          len(got) == 3 and any("END-OF-SET" in line for line in collected))

    # 20. bad input does not crash
    bad = Interpreter(out=lambda text: None)
    ok1 = bad.run_line("store NOTHING a=1")
    bad.run_line("record R a calc a")
    ok2 = bad.run_line("find calc R x")
    check("bad commands report a status instead of raising", ok1 is False and ok2 is False)

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
        print("(verbose mode: every record fetch is printed)\n")
    files = [a for a in args if not a.startswith("--")]
    if len(files) > 0:
        run_file(files[0])
        return
    repl()


if __name__ == "__main__":
    main()

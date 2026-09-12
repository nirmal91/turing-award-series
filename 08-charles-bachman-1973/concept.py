"""
Bachman's network data model / navigational database -- the core idea
(Charles W. Bachman, Integrated Data Store, General Electric, 1963-64;
standardized by CODASYL's Data Base Task Group, 1969-71).

Before this, connecting two kinds of records meant re-scanning a whole
file: to find every employee in the Sales department, you read every
EMPLOYEE record and checked its department field, one by one. IDS's idea:
store the CONNECTION itself, as a chain of pointers on disk, so following
a relationship is one pointer-follow, not a scan.

A SET (Bachman's word -- nothing to do with the mathematical set) is a
named 1:N relationship: one OWNER record, and a ring of MEMBER records
linked to it and to each other. The ring closes: the last member points
back to the owner. There is no query language here -- the program keeps a
CURRENCY INDICATOR, "where am I right now in this set," and moves it one
pointer at a time. That act of moving a position through a stored
structure, instead of describing what you want and letting the system
find it, is what Bachman's 1973 Turing lecture called
"the programmer as navigator."
"""


class Record:
    def __init__(self, kind, **fields):
        self.kind = kind
        self.fields = fields
        self.next_in_set = None   # ring pointer: this record -> the next one
        self.owner = None         # every member points straight back to its owner

    def __repr__(self):
        pairs = ", ".join("%s=%s" % kv for kv in self.fields.items())
        return "%s(%s)" % (self.kind, pairs)


def connect(owner, members):
    """Build one set occurrence: OWNER ring-linked to every record in
    MEMBERS, in order, and back to OWNER again -- the physical chain IDS
    stored on disk instead of a scannable file."""
    owner.next_in_set = members[0] if len(members) > 0 else owner
    for i, member in enumerate(members):
        member.owner = owner
        member.next_in_set = members[i + 1] if i + 1 < len(members) else owner


if __name__ == "__main__":
    sales = Record("DEPARTMENT", name="Sales")
    alice = Record("EMPLOYEE", name="Alice")
    bob = Record("EMPLOYEE", name="Bob")
    carol = Record("EMPLOYEE", name="Carol")
    connect(sales, [alice, bob, carol])

    print("walking the ring, starting from the owner (FIND FIRST / FIND NEXT):")
    current = sales.next_in_set          # FIND FIRST WITHIN <set>
    while current is not sales:
        print("  ", current)
        current = current.next_in_set    # FIND NEXT WITHIN <set>

    print()
    print("from a member, FIND OWNER WITHIN <set> is one pointer, not a scan:")
    print("  ", bob, "-> owner ->", bob.owner)

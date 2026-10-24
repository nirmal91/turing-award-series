"""
Bachman's idea — the core of IDS and the network data model (C. W. Bachman, 1960s).

Before IDS, related facts sat in separate sequential files. To answer "who
supplies part P2?" a program scanned the supply file and then scanned the
supplier file, record by record, for every match.

Bachman's move: store records on disk and let them POINT at each other. A "set"
is one owner record plus a ring of member records, linked by next pointers.
One record can sit in two sets at once, so the data is a network, not a tree.
A program finds a starting record directly, then navigates by following
pointers. Bachman called that programmer "the navigator".
"""

# Every record is a dict. 'next' holds one pointer per set the record is in,
# 'owner' says who owns that set occurrence.
records = {}


def make(key, kind, **data):
    records[key] = {"kind": kind, "data": data, "next": {}, "owner": {}}
    return key


def connect(set_name, owner, member):
    """Put member at the end of owner's ring: owner -> ... -> member -> owner."""
    if set_name not in records[owner]["next"]:
        records[owner]["next"][set_name] = owner      # an empty ring points at itself
    # walk to the last member (the one whose next pointer returns to the owner)
    last = owner
    while records[last]["next"][set_name] != owner:
        last = records[last]["next"][set_name]
    records[last]["next"][set_name] = member
    records[member]["next"][set_name] = owner
    records[member]["owner"][set_name] = owner


# Two suppliers, two parts, three supply records. Each SUPPLY is a member of
# one supplier's ring AND one part's ring: that is what makes it a network.
smith = make(1, "SUPPLIER", name="Smith")
jones = make(2, "SUPPLIER", name="Jones")
nut = make(3, "PART", name="Nut")
bolt = make(4, "PART", name="Bolt")
s1 = make(5, "SUPPLY", qty=300)
s2 = make(6, "SUPPLY", qty=200)
s3 = make(7, "SUPPLY", qty=400)
for supply, supplier, part in [(s1, smith, nut), (s2, smith, bolt), (s3, jones, bolt)]:
    connect("SUPPLIER-SUPPLY", supplier, supply)
    connect("PART-SUPPLY", part, supply)

# The navigator's program: "who supplies the bolt?"
# Start at the part (found directly), walk its ring, hop from each supply to
# its supplier owner. No file is scanned. Only pointers are followed.
print("Suppliers of", records[bolt]["data"]["name"])
current = records[bolt]["next"]["PART-SUPPLY"]      # first member of the ring
while current != bolt:                              # back at the owner = end of set
    supplier = records[current]["owner"]["SUPPLIER-SUPPLY"]
    print("  ", records[supplier]["data"]["name"], "supplies", records[current]["data"]["qty"])
    current = records[current]["next"]["PART-SUPPLY"]

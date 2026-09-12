"""
The network data model — the core idea (Charles W. Bachman, IDS, 1963).

Before this, business data lived in flat files: one file per application, each
a long list of records. To answer "which employees are in Engineering?" a
program read the ENTIRE employee file top to bottom, testing every record. The
relationship between a department and its employees existed only in the
programmer's head and in that scan.

Bachman's Integrated Data Store made the relationship a thing the database
itself stores: a "set". A set has one owner record and a chain of member
records. The owner points to its first member; each member points to the next.
To list Engineering's employees you FIND the Engineering record, then follow
its member chain, hopping pointer to pointer straight to exactly those
employees. No scan of unrelated records. Bachman called this "the programmer as
navigator": you move through the data along the links, one record at a time,
instead of searching it.
"""

# Records, stored by id. Just fields -- the structure lives in the sets below.
records = {
    1: {"type": "DEPT", "name": "Engineering"},
    2: {"type": "DEPT", "name": "Sales"},
    3: {"type": "EMP", "name": "Ada"},
    4: {"type": "EMP", "name": "Grace"},
    5: {"type": "EMP", "name": "Alan"},
}

# A set: owner id -> the chain of member ids it owns. In real IDS this was a
# pointer in the owner record to the first member, and a "next" pointer in each
# member; walking the list here is walking that pointer chain.
works_in = {
    1: [3, 4],   # Engineering owns Ada, Grace
    2: [5],      # Sales owns Alan
}


def members(owner_id):
    """FIND FIRST/NEXT WITHIN SET: walk the owner's member chain, one hop at a
    time. This touches only the members, never an unrelated record."""
    result = []
    for member_id in works_in.get(owner_id, []):
        result.append(records[member_id]["name"])
    return result


def owner(member_id):
    """The reverse link: which owner's chain is this member on? In IDS every
    member also carried an owner pointer, so this was one hop, not a search."""
    for owner_id, chain in works_in.items():
        if member_id in chain:
            return records[owner_id]["name"]
    return None


if __name__ == "__main__":
    # Navigate down: owner -> its members.
    print("Engineering's employees (follow the set chain):")
    for name in members(1):
        print("  " + name)

    # Navigate up: member -> its owner.
    print()
    print("Ada works in:", owner(3))

    print()
    print("Before IDS, 'who works in Engineering?' scanned every employee "
          "record.")
    print("After IDS, you follow Engineering's member chain straight to them.")

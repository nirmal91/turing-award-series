"""
Charles Bachman built the Integrated Data Store (IDS) at General Electric,
running by 1963. Its core idea, later standardized by CODASYL in 1969 as the
"network data model", is the SET: an OWNER record and its MEMBER records,
wired together as a ring. The owner points to the first member, each member
points to the next, and the last member points back to the owner.

That ring is the whole trick. To list a department's employees, you don't
scan a table and match a foreign key -- you follow the ring, one pointer at
a time. To find an employee's department, you follow their OWNER pointer
back. No searching, no joins: just pointer chasing, which is why Bachman's
1973 Turing lecture was titled "The Programmer as Navigator."

This file is that idea with nothing else: two functions, one ring.
"""

class Record:
    def __init__(self, kind, **fields):
        self.kind = kind
        self.fields = fields
        self.next = None    # next record around the ring (member, or owner to close it)
        self.owner = None   # the owner of the set occurrence this record is a member of

    def __repr__(self):
        return "%s(%s)" % (self.kind, self.fields)


def connect(owner, member):
    """CONNECT member TO the set occurrence owned by owner.
    Splices member onto the end of the ring, then closes the ring back
    to owner -- exactly the physical layout IDS wrote to disk."""
    member.owner = owner
    if owner.next is None:
        owner.next = member
        member.next = owner
    else:
        tail = owner.next
        while tail.next is not owner:
            tail = tail.next
        tail.next = member
        member.next = owner


def members_of(owner):
    """FIND FIRST, then FIND NEXT repeatedly: walk the ring until it
    returns to the owner. This is the only way to list a set's members --
    there is no table to scan."""
    result = []
    node = owner.next
    while node is not None and node is not owner:
        result.append(node)
        node = node.next
    return result


if __name__ == "__main__":
    engineering = Record("DEPARTMENT", name="Engineering")
    alice = Record("EMPLOYEE", name="Alice")
    bob = Record("EMPLOYEE", name="Bob")
    carol = Record("EMPLOYEE", name="Carol")

    connect(engineering, alice)
    connect(engineering, bob)
    connect(engineering, carol)

    print("Owner:", engineering)
    print("Members, in ring order (FIND FIRST / FIND NEXT):", members_of(engineering))
    print("Bob's owner (FIND OWNER):", bob.owner)

    # Before this: an application that needed "Engineering's employees" and
    # another that needed "Alice's department" each kept their own file,
    # often duplicating the same facts. IDS's whole pitch was ONE shared,
    # navigable structure that both applications walk -- hence "Integrated."

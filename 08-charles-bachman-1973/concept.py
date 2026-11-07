"""
Navigational database: the core idea (Bachman, Integrated Data Store, 1964)

Records are not rows in a table you search. They are things in memory
that point at each other. A "set" is a ring: the owner points to its first
member, each member points to the next, and the last one points back to
the owner. To answer a question you start at one record and follow pointers.
Bachman called this the programmer as navigator (his 1973 Turing lecture).
"""

# Before this: records sat in flat files, in sequence on tape or cards.
#              To find Ann's department you read the file from the top.
# After this:  Ann holds a pointer to her department. One hop.

def new(kind, name):
    # An empty ring is an owner pointing at itself.
    rec = {"kind": kind, "name": name, "next": None, "owner": None}
    rec["next"] = rec
    return rec

def last_in_ring(owner):
    cur = owner
    while cur["next"] is not owner:
        cur = cur["next"]
    return cur

def connect(owner, member):
    # Put the member at the end of the owner's ring.
    last = last_in_ring(owner)
    member["next"] = owner      # new last member points back to the owner
    last["next"] = member       # old last (or the owner) points to the new one
    member["owner"] = owner     # shortcut straight back to the owner

def members(owner):
    cur = owner["next"]
    while cur is not owner:
        yield cur
        cur = cur["next"]

eng = new("DEPT", "Engineering")
for person in ["Ann", "Bob", "Cy"]:
    connect(eng, new("EMP", person))

print("Members of Engineering, by following next pointers:")
for m in members(eng):
    print("  ", m["name"])

ann = eng["next"]
print("Ann's department, one hop on the owner pointer:", ann["owner"]["name"])

"""
Bachman's core idea: records linked by pointers, and a programmer who navigates.

Before IDS (Integrated Data Store, c. 1963), business data lived in sequential
files on tape or cards. To answer "which orders belong to Acme?" you read the
whole order file and kept the matches. Nothing in a record said where its
related records were.

Bachman's move: store the relationships inside the data. A "set" is a ring of
records. The owner points to its first member, each member points to the next,
and the last points back to the owner. The program no longer searches. It
finds one record, then follows pointers, and the system remembers where it
is (the "currency" indicator) so the next step starts from there.
"""

# Each record has a name, and one pointer ("next") in a single set.
# The ring: ACME -> order 1 -> order 2 -> order 3 -> back to ACME.
records = {
    "ACME":    {"next": "ORDER-1"},
    "ORDER-1": {"next": "ORDER-2"},
    "ORDER-2": {"next": "ORDER-3"},
    "ORDER-3": {"next": "ACME"},
    "ZENITH":  {"next": "ORDER-4"},
    "ORDER-4": {"next": "ZENITH"},
}

# Pad the world with 200 other orders, so the size of the file matters.
for n in range(5, 205):
    records["ORDER-%d" % n] = {"next": "ZENITH"}

# Before: a sequential file. Every question reads every record.
order_file = [("ORDER-1", "ACME"), ("ORDER-4", "ZENITH"),
              ("ORDER-2", "ACME"), ("ORDER-3", "ACME")]
for n in range(5, 205):
    order_file.append(("ORDER-%d" % n, "ZENITH"))

reads = 0
found = []
for order, customer in order_file:
    reads = reads + 1
    if customer == "ACME":
        found.append(order)
print("sequential scan:", found, "after", reads, "reads")

# After: find the owner once, then follow the ring until you are back at it.
current = "ACME"            # the currency indicator
touches = 1                 # one record found directly
found = []
current = records[current]["next"]       # FIND FIRST
touches = touches + 1
while current != "ACME":                 # end of set = back at the owner
    found.append(current)
    current = records[current]["next"]   # FIND NEXT
    touches = touches + 1
print("navigation:     ", found, "after", touches, "touches")

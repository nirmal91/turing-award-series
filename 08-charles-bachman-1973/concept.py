"""
Bachman's core idea: records linked into chains, and the programmer walks them.
(Charles W. Bachman, Integrated Data Store, General Electric, early 1960s.)

Before IDS, business data lived in sequential files on tape, one record after
another. To answer "which employees work in Sales?" you read every employee
record and kept the ones that matched. Cost: the size of the whole file.

Bachman's move: store the relationship itself as pointers. A department record
points to its first employee. Each employee points to the next employee in
the same department, and the last one points back to the department. That
ring is called a "set" (later a CODASYL set). To list Sales employees you jump
to Sales and follow the ring. Cost: the number of Sales employees.

Ten years later his Turing lecture called this "the programmer as navigator":
you do not process a file from top to bottom, you move through the data from
record to record, like a ship on a chart.
"""

# Every record has a database key (its address). Think of it as a disk address.
records = {
    1: {"type": "DEPT", "name": "Sales",   "first": 3, "next": None},
    2: {"type": "DEPT", "name": "Support", "first": 5, "next": None},
    3: {"type": "EMP",  "name": "Ann",     "next": 4, "owner": 1},
    4: {"type": "EMP",  "name": "Bob",     "next": 1, "owner": 1},   # last: ring closes on owner
    5: {"type": "EMP",  "name": "Cy",      "next": 2, "owner": 2},
}


def employees_of(dept_key):
    # Navigate: jump to the owner, follow the ring until we are back at it.
    found = []
    key = records[dept_key]["first"]
    while key != dept_key:
        found.append(records[key]["name"])
        key = records[key]["next"]
    return found


def employees_of_by_scan(dept_name):
    # The "before": read every record, keep the matches.
    found = []
    for key in records:
        rec = records[key]
        if rec["type"] == "EMP" and records[rec["owner"]]["name"] == dept_name:
            found.append(rec["name"])
    return found


if __name__ == "__main__":
    print("navigate:", employees_of(1))
    print("scan:    ", employees_of_by_scan("Sales"))

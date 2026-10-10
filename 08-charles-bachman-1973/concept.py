"""
Bachman's idea in about 60 lines: records at addresses, linked by pointers.

Before IDS, "which courses is Ada taking?" meant reading files from the top and
matching keys. After IDS, the student record points to its first enrollment,
each enrollment points to the next, and the last one points back to the
student. An enrollment also points to its course. You do not search. You
follow pointers. Bachman called that navigating.
"""

# Storage: address -> record. The address is the "database key."
# Each record holds its fields and its pointers.
store = {
    1: {"kind": "student",    "name": "Ada",       "first": 4},   # owner of a chain
    2: {"kind": "course",     "title": "Logic"},
    3: {"kind": "course",     "title": "Databases"},
    4: {"kind": "enrollment", "grade": "A", "course": 2, "next": 5},
    5: {"kind": "enrollment", "grade": "B", "course": 3, "next": 1},  # last one points home
}


def courses_of(student_address):
    titles = []
    here = store[student_address]["first"]           # step 1: go to the first member
    while here != student_address:                    # the ring closes on the owner
        enrollment = store[here]
        course = store[enrollment["course"]]          # step 2: hop to the course
        titles.append(course["title"] + " (" + enrollment["grade"] + ")")
        here = enrollment["next"]                     # step 3: follow the chain
    return titles


print(courses_of(1))   # ['Logic (A)', 'Databases (B)']

# Each line above is one pointer hop. No file was read from the top.
# The cost depends on how many courses Ada takes, not on how many students exist.

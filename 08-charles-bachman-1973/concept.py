"""
Charles Bachman's Integrated Data Store (IDS) -- the core idea
(C. W. Bachman, General Electric, 1963).

BEFORE this, data lived in flat, sequential files on tape. To find "all the
orders belonging to Acme Corp", a program read every single order record
from the start of the tape to the end, checked its customer field, and kept
the ones that matched. There was no way to jump straight to Acme's orders --
you always paid the cost of the whole file, every time, for every program
that needed that data.

Bachman's insight: store a direct link, a named SET, from each owner record
(a CUSTOMER) to its member records (that customer's ORDERs), wired together
on disk when the order is created. A program then NAVIGATES: FIND the owner,
FIND FIRST member within the set, FIND NEXT -- following links instead of
scanning everything. This became the network data model, standardized a few
years later as the CODASYL specification and the dominant commercial
database design of the 1970s.
"""

customers = {1: {"name": "Acme Corp"}, 2: {"name": "Globex"}}
orders = {
    101: {"total": 250, "customer": 1},
    102: {"total": 80, "customer": 1},
    103: {"total": 500, "customer": 2},
}

# The named set CUSTOMER-ORDER: owner CUSTOMER id -> ordered list of member
# ORDER ids. This is wired up once, when each order is connected to its
# customer -- not recomputed every time someone asks a question.
customer_order_set = {1: [101, 102], 2: [103]}


# The "before": a flat file. Finding Acme's orders means reading every
# order record on the tape and checking its customer field by hand.
def scan_for_orders(customer_id):
    examined = 0
    found = []
    for order_id in orders:
        examined += 1
        if orders[order_id]["customer"] == customer_id:
            found.append(order_id)
    return found, examined


# The "after": navigate the set directly. Every step lands on a record that
# is actually part of the answer -- order 103 is never even looked at.
def find_first_within_set(customer_id):
    members = customer_order_set.get(customer_id, [])
    if len(members) == 0:
        return None
    return members[0]


def find_next_within_set(customer_id, current_order_id):
    members = customer_order_set[customer_id]
    index = members.index(current_order_id)
    if index + 1 >= len(members):
        return None
    return members[index + 1]


if __name__ == "__main__":
    found, examined = scan_for_orders(1)
    print("scanning the flat file for Acme's orders:")
    print("  found %s after examining %d of %d order records"
          % (found, examined, len(orders)))

    print()
    print("navigating the CUSTOMER-ORDER set instead:")
    navigated = []
    steps = 0
    current = find_first_within_set(1)
    while current is not None:
        navigated.append(current)
        steps += 1
        current = find_next_within_set(1, current)
    print("  found %s after %d navigation steps -- order 103 was never touched"
          % (navigated, steps))

"""
The network data model — the core idea (Charles W. Bachman, Integrated Data
Store, General Electric, 1963).

Before this, "the data" was a flat file: one record type per file, records
processed top to bottom, start to end. If you wanted a customer's orders,
you scanned the whole ORDERS file and kept every row whose customer_id
matched. Every program that needed that answer paid that scan again.

Bachman's insight: store the relationship itself, not just the two flat
files. A "set" is a named 1-to-many link between an owner record (one
customer) and its member records (that customer's orders), wired together
as a ring of pointers at STORE time. To list a customer's orders you don't
scan anything — you stand on the customer record and walk the ring one
pointer at a time. The cost of the question is the size of the answer, not
the size of the database.
"""

# A record is just a dict of fields. Nothing fancy yet — the interesting
# part is how records get wired together, not the records themselves.
customers = {
    1: {"name": "Ada"},
    2: {"name": "Grace"},
}
orders = {
    101: {"item": "Punched cards", "customer": 1},
    102: {"item": "Vacuum tube", "customer": 1},
    103: {"item": "Teletype", "customer": 2},
}

# The set: for each owner (customer), a ring of its members (orders), in
# the order they were connected. This is the part a flat file doesn't have.
# Real IDS stored this as NEXT/PRIOR/OWNER pointers baked into each record;
# a Python list of ids is the same idea without the pointer arithmetic.
customer_orders_set = {
    1: [101, 102],
    2: [103],
}


def scan_orders_before(customer_id):
    # The pre-1963 way: no relationship is stored, so you re-derive it
    # every time by reading every order and checking its customer field.
    matches = []
    for order_id in orders:
        if orders[order_id]["customer"] == customer_id:
            matches.append(order_id)
    return matches


def walk_set_after(customer_id):
    # The IDS way: the relationship already exists as a ring. Walking it
    # only ever touches the records you actually want.
    return customer_orders_set[customer_id]


if __name__ == "__main__":
    for customer_id, customer in customers.items():
        print("%s's orders:" % customer["name"])

        before = scan_orders_before(customer_id)
        print("  scanning every order (before):", before)

        after = walk_set_after(customer_id)
        print("  walking the set (after):      ", after)
        print()

    print("Both answers agree. The difference is what each one had to touch")
    print("to get there: scan_orders_before() reads all %d orders every time;"
          % len(orders))
    print("walk_set_after() reads exactly the orders it returns.")

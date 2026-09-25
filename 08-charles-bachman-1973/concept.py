"""
Charles Bachman's Integrated Data Store (IDS) -- the core idea
(General Electric, operational 1963-64).

BEFORE this: a "database" was a flat file of records. To find every order
belonging to customer 7, a program read the whole order file, record by
record, and checked each one's customer field. The cost of that search
grows with the size of the WHOLE file, not with how many orders customer 7
actually has.

AFTER this: records are linked directly to the records they relate to.
A "set" is a ring of pointers -- the owner (a customer) points to its first
member (an order), each member points to the next, and the last member
points back to the owner, closing the ring. Finding customer 7's orders
means starting at customer 7's own record and following pointers. You visit
exactly as many records as customer 7 actually has orders. Nothing else.

This is a "chain" in IDS terms -- one owner, a ring of members. Bachman's
real system had many chains per record and a schema describing all of them;
this file keeps it to one, to make the pointer-following itself legible.
"""

customers = {}   # customer_id -> {"name": ..., "first_order": id or None, "last_order": id or None}
orders = {}      # order_id    -> {"item": ..., "owner": customer_id, "next": id (a customer_id closes the ring)}

# One shared counter for every record, customers and orders alike -- exactly
# like a real IDS database-key. If customers and orders numbered themselves
# separately, Alice's customer id could collide with one of her own order
# ids, and the ring-closing check ("have we looped back to the owner?")
# would break.
next_id = 1


def add_customer(name):
    global next_id
    customer_id = next_id
    next_id += 1
    customers[customer_id] = {"name": name, "first_order": None, "last_order": None}
    return customer_id


def connect_order(customer_id, item):
    global next_id
    order_id = next_id
    next_id += 1
    customer = customers[customer_id]
    order = {"item": item, "owner": customer_id, "next": customer_id}  # ring closes to the owner
    if customer["first_order"] is None:
        customer["first_order"] = order_id
    else:
        orders[customer["last_order"]]["next"] = order_id
    customer["last_order"] = order_id
    orders[order_id] = order
    return order_id


def walk_orders(customer_id):
    """AFTER: follow the ring. Touches exactly this customer's orders."""
    result = []
    current = customers[customer_id]["first_order"]
    while current is not None and current != customer_id:
        result.append(orders[current]["item"])
        current = orders[current]["next"]
    return result


def scan_orders(customer_id):
    """BEFORE: check every order in the whole file, one at a time."""
    result = []
    for order_id in orders:
        if orders[order_id]["owner"] == customer_id:
            result.append(orders[order_id]["item"])
    return result


if __name__ == "__main__":
    alice = add_customer("Alice")
    bob = add_customer("Bob")
    connect_order(alice, "widget")
    connect_order(bob, "gadget")
    connect_order(alice, "sprocket")
    connect_order(alice, "gizmo")

    alice_items = walk_orders(alice)
    print("walking the ring for Alice:", alice_items, "(touched %d records)" % len(alice_items))
    print("scanning the whole file for Alice:", scan_orders(alice), "(touched %d records)" % len(orders))
    print()
    print("Same answer. The ring only ever touches Alice's own orders --")
    print("Bob's order never gets looked at. The scan looks at everything.")

"""
The core idea of Bachman's Integrated Data Store (IDS, 1963): records point
at other records.

Before IDS, data lived in flat files on tape or cards. To answer "who bought
a Widget?" a program read every record from the start and tested each one.

IDS gave every record a database key (an address) and let records hold the
addresses of other records. A "set" is a ring: an owner record, then its
member records, chained by NEXT pointers, and the last member points back to
the owner. You do not search for data. You walk to it. Bachman called this
the programmer as navigator.

Here are two sets and a handful of records. LINE is a member of two sets at
once, which is what makes this a network and not a tree.
"""

# Each record: its fields, plus one NEXT pointer per set it belongs to.
# A record that owns a set also has a NEXT pointer into that set's ring.
records = {
    1: {"name": "Widget"},                                  # PRODUCT
    2: {"name": "Gadget"},                                  # PRODUCT
    3: {"name": "Acme"},                                    # CUSTOMER
    4: {"name": "Birch"},                                   # CUSTOMER
    5: {"qty": 2, "owner_customer": 3, "owner_prod": 1},       # LINE: Acme buys 2 Widgets
    6: {"qty": 1, "owner_customer": 3, "owner_prod": 2},       # LINE: Acme buys 1 Gadget
    7: {"qty": 5, "owner_customer": 4, "owner_prod": 1},       # LINE: Birch buys 5 Widgets
}

# The PROD_LINE ring for Widget: owner 1 -> line 5 -> line 7 -> back to 1.
prod_line_next = {1: 5, 5: 7, 7: 1}


def customers_who_bought(product_key):
    names = []
    line = prod_line_next[product_key]          # first member of the ring
    while line != product_key:                  # back at the owner means done
        customer_key = records[line]["owner_customer"]
        names.append(records[customer_key]["name"])
        line = prod_line_next[line]             # follow the NEXT pointer
    return names


print("Who bought a Widget?", customers_who_bought(1))
print("Only the 2 lines in the Widget ring were visited, not every record in the file.")

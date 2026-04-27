"""
Microprogramming — the core idea (Wilkes, 1951)

A machine instruction is just a lookup into a ROM.
The ROM holds the recipe. The CPU follows it.
That's it.
"""

# ── The ROM — Wilkes's invention ──────────────────────────────────────────────
#
# Before this: each instruction was hardwired into logic gates.
# After this:  each instruction is a list of steps stored in memory.
# To add a new instruction, add a new entry here. No hardware change.

CONTROL_STORE = {
    'LOADI': ['A = operand'],
    'LOAD':  ['MAR = operand',
              'MDR = RAM[MAR]',
              'A = MDR'],
    'STORE': ['MAR = operand',
              'MDR = A',
              'RAM[MAR] = MDR'],
    'ADD':   ['MAR = operand',
              'MDR = RAM[MAR]',
              'A = A + MDR'],
    'SUB':   ['MAR = operand',
              'MDR = RAM[MAR]',
              'A = A - MDR'],
    'HALT':  ['stop'],
}

# ── The machine ───────────────────────────────────────────────────────────────

A   = 0      # accumulator register
MAR = 0      # memory address register
MDR = 0      # memory data register
RAM = [0] * 256

def run(program, verbose=True):
    global A, MAR, MDR, RAM
    A = MAR = MDR = 0
    RAM = [0] * 256

    for instruction in program:
        parts    = instruction.split()
        opcode   = parts[0]
        operand  = int(parts[1]) if len(parts) > 1 else 0
        recipe   = CONTROL_STORE[opcode]

        if verbose:
            print(f"\n  {instruction}")

        for step in recipe:
            if   step == 'stop':             break
            elif step == 'A = operand':      A = operand
            elif step == 'MAR = operand':    MAR = operand
            elif step == 'MDR = RAM[MAR]':   MDR = RAM[MAR]
            elif step == 'A = MDR':          A = MDR
            elif step == 'MDR = A':          MDR = A
            elif step == 'RAM[MAR] = MDR':   RAM[MAR] = MDR
            elif step == 'A = A + MDR':      A = A + MDR
            elif step == 'A = A - MDR':      A = A - MDR

            if verbose:
                print(f"    → {step}  (A={A})")

        if opcode == 'HALT':
            break

    print(f"\n  Result: A={A}")

# ── Example programs ──────────────────────────────────────────────────────────

print("Program 1: store 10, add it to 25")
run([
    "LOADI 10",
    "STORE 200",
    "LOADI 25",
    "ADD 200",
    "HALT",
])

print("\nProgram 2: store two values, subtract one from the other")
run([
    "LOADI 30",
    "STORE 200",
    "LOADI 50",
    "SUB 200",
    "HALT",
])

"""
Microprogrammed CPU — inspired by Maurice Wilkes (1967 Turing Award)

Wilkes's key insight, published 1951:
  Instead of wiring machine instructions directly to logic gates (hardwired
  control), store sequences of primitive microinstructions in a small
  read-only control store. Each machine instruction dispatches to its
  microprogram. Adding a new instruction means writing new microcode,
  not redesigning hardware.

BEFORE microprogramming (~1945-1950):
  Machine instructions were hardwired. IBM 701 designers discovered missing
  useful instructions after manufacture — no recourse. Every change to
  instruction behavior required months of hardware redesign.

AFTER microprogramming (Wilkes 1951):
  Three-level hierarchy:
    1. Logic gates        — fixed silicon
    2. Microinstructions  — read-only control store (this file's key structure)
    3. Machine ISA        — what programmers write

  IBM System/360 (1964) used microprogramming to run one ISA across
  wildly different hardware models. Intel x86 CPUs still use microcode today.

This simulator implements:
  - 16-instruction ISA  (the programmer-visible level)
  - 68-word control store  (microinstruction ROM — the Wilkes layer)
  - 8 registers, ALU with 5 ops, 256 words of RAM

Usage:
  python implementation.py           # interactive assembler REPL
  python implementation.py --test    # run test suite
  python implementation.py --verbose # show microinstruction trace
"""

import sys
import argparse

# ── Register IDs ──────────────────────────────────────────────────────────────

A, B, PC, IR, MAR, MDR, TEMP, ZERO = range(8)
REG_NAMES = ['A', 'B', 'PC', 'IR', 'MAR', 'MDR', 'TEMP', 'ZERO']

# ── ALU operations ────────────────────────────────────────────────────────────

ALU_PASS, ALU_ADD, ALU_SUB, ALU_INC, ALU_DEC = range(5)

def alu(op, a, b=0):
    a &= 0xFFFF; b &= 0xFFFF
    if op == ALU_PASS: return a
    if op == ALU_ADD:  return (a + b) & 0xFFFF
    if op == ALU_SUB:  return (a - b) & 0xFFFF
    if op == ALU_INC:  return (a + 1) & 0xFFFF
    if op == ALU_DEC:  return (a - 1) & 0xFFFF
    return 0

# ── Memory operation codes ────────────────────────────────────────────────────

MEM_NONE, MEM_READ, MEM_WRITE = 0, 1, 2

# ── Sequencer action codes ────────────────────────────────────────────────────

SEQ_NEXT     = 0  # μPC ← μPC + 1
SEQ_FETCH    = 1  # μPC ← 0  (start next machine instruction)
SEQ_DISPATCH = 2  # μPC ← DISPATCH_BASE + opcode * STRIDE; MAR ← operand
SEQ_JZ       = 3  # μPC ← jaddr if A == 0, else μPC + 1
SEQ_HALT     = 4  # stop execution

# ── Control store layout ──────────────────────────────────────────────────────
#
#  Wilkes called this the "control matrix" — a 2D array where rows are
#  time steps and columns are control signals. Here we represent each row
#  as a microinstruction object.
#
#  Layout:
#    μ0..μ3         — fetch cycle (shared by all machine instructions)
#    μ4 + op*4 ..   — per-opcode execute microprograms (STRIDE = 4)

FETCH_BASE    = 0
DISPATCH_BASE = 4
STRIDE        = 4
NUM_OPCODES   = 16
CS_SIZE       = DISPATCH_BASE + NUM_OPCODES * STRIDE  # 68 words

# ── ISA opcodes (4-bit, 0x0–0xF) ─────────────────────────────────────────────

HALT  = 0x0  # stop
LOAD  = 0x1  # A ← MEM[addr]
STORE = 0x2  # MEM[addr] ← A
ADD   = 0x3  # A ← A + MEM[addr]
SUB   = 0x4  # A ← A - MEM[addr]
JMP   = 0x5  # PC ← addr
JZ    = 0x6  # PC ← addr if A == 0
JNZ   = 0x7  # PC ← addr if A != 0
LOADI = 0x8  # A ← imm  (immediate)
ADDI  = 0x9  # A ← A + imm
SUBI  = 0xA  # A ← A - imm
MOVE  = 0xB  # B ← A
MOVEB = 0xC  # A ← B
INC_OP = 0xD # A ← A + 1
DEC_OP = 0xE # A ← A - 1
NOP   = 0xF  # no operation

OP_NAMES = {
    HALT: 'HALT', LOAD: 'LOAD', STORE: 'STORE', ADD: 'ADD',
    SUB: 'SUB', JMP: 'JMP', JZ: 'JZ', JNZ: 'JNZ',
    LOADI: 'LOADI', ADDI: 'ADDI', SUBI: 'SUBI',
    MOVE: 'MOVE', MOVEB: 'MOVEB', INC_OP: 'INC', DEC_OP: 'DEC', NOP: 'NOP',
}
OP_CODES = {v: k for k, v in OP_NAMES.items()}

# Machine word format (16-bit):
#   bits 15-12 : opcode  (4 bits)
#   bits 11-8  : unused
#   bits  7-0  : operand / address  (8 bits, 0-255)

def encode(op, operand=0):
    return ((op & 0xF) << 12) | (operand & 0xFF)

def decode(word):
    return (word >> 12) & 0xF, word & 0xFF

# ── Microinstruction ──────────────────────────────────────────────────────────

class MI:
    """
    One microinstruction controls the data path for one clock cycle.

    Wilkes's 1951 paper showed that all the complexity of a CPU's control
    unit could be expressed as a table of these entries — the control store.
    Each entry activates a set of data-path signals simultaneously:
      - an ALU operation
      - a register write
      - a memory operation
      - a next-μPC selection
    """
    __slots__ = ('src1', 'src2', 'alu_op', 'dst', 'mem', 'seq', 'jaddr', 'label')

    def __init__(self, *, src1=ZERO, src2=ZERO, alu_op=ALU_PASS, dst=None,
                 mem=MEM_NONE, seq=SEQ_NEXT, jaddr=0, label=''):
        self.src1 = src1; self.src2 = src2; self.alu_op = alu_op
        self.dst = dst; self.mem = mem; self.seq = seq
        self.jaddr = jaddr; self.label = label

    def describe(self):
        parts = []
        if self.dst is not None:
            n = REG_NAMES[self.dst]
            s1 = REG_NAMES[self.src1]; s2 = REG_NAMES[self.src2]
            if self.alu_op == ALU_PASS: parts.append(f"{n}←{s1}")
            elif self.alu_op == ALU_INC: parts.append(f"{n}←{s1}+1")
            elif self.alu_op == ALU_DEC: parts.append(f"{n}←{s1}-1")
            elif self.alu_op == ALU_ADD: parts.append(f"{n}←{s1}+{s2}")
            elif self.alu_op == ALU_SUB: parts.append(f"{n}←{s1}-{s2}")
        if self.mem == MEM_READ:  parts.append("MDR←MEM[MAR]")
        if self.mem == MEM_WRITE: parts.append("MEM[MAR]←MDR")
        tail = {SEQ_FETCH: '→FETCH', SEQ_DISPATCH: '→DISPATCH',
                SEQ_HALT: 'HALT', SEQ_JZ: f'→μ{self.jaddr}?A=0'}.get(self.seq, '')
        if tail: parts.append(tail)
        return '  '.join(parts) or '(nop)'

# ── Build the control store ───────────────────────────────────────────────────

def build_control_store():
    """
    This is the heart of microprogramming. Every machine instruction's
    behaviour is fully specified here in ROM, not in logic gates.
    Wilkes's contribution was realising you could do this at all.
    """
    cs = [MI(seq=SEQ_FETCH, label='pad') for _ in range(CS_SIZE)]

    # ── Fetch cycle (μ0..μ3) — shared by every machine instruction ────────────
    #
    #  μ0: address the memory location holding the next instruction
    #  μ1: read that location into MDR
    #  μ2: copy MDR into IR (the instruction register)
    #  μ3: advance PC; then dispatch to the opcode's microprogram
    #
    cs[0] = MI(src1=PC,  alu_op=ALU_PASS, dst=MAR,                   label='MAR←PC')
    cs[1] = MI(                           mem=MEM_READ,               label='MDR←MEM[MAR]')
    cs[2] = MI(src1=MDR, alu_op=ALU_PASS, dst=IR,                    label='IR←MDR')
    cs[3] = MI(src1=PC,  alu_op=ALU_INC,  dst=PC, seq=SEQ_DISPATCH,  label='PC++; DISPATCH')
    #
    # SEQ_DISPATCH: computes μPC ← DISPATCH_BASE + opcode * STRIDE
    # and, as a side effect, sets MAR ← IR[7:0]  (the operand field).
    # Every opcode's microprogram thus starts with MAR already loaded.

    def slot(op):
        return DISPATCH_BASE + op * STRIDE

    # ── HALT (0x0) ────────────────────────────────────────────────────────────
    cs[slot(HALT)] = MI(seq=SEQ_HALT, label='HALT')

    # ── LOAD addr (0x1): A ← MEM[addr] ───────────────────────────────────────
    cs[slot(LOAD)  ] = MI(mem=MEM_READ,                                   label='MDR←MEM[MAR]')
    cs[slot(LOAD)+1] = MI(src1=MDR, alu_op=ALU_PASS, dst=A, seq=SEQ_FETCH, label='A←MDR; →FETCH')

    # ── STORE addr (0x2): MEM[addr] ← A ──────────────────────────────────────
    cs[slot(STORE)  ] = MI(src1=A, alu_op=ALU_PASS, dst=MDR,              label='MDR←A')
    cs[slot(STORE)+1] = MI(mem=MEM_WRITE, seq=SEQ_FETCH,                   label='MEM[MAR]←MDR; →FETCH')

    # ── ADD addr (0x3): A ← A + MEM[addr] ────────────────────────────────────
    cs[slot(ADD)  ] = MI(mem=MEM_READ,                                     label='MDR←MEM[MAR]')
    cs[slot(ADD)+1] = MI(src1=A, src2=MDR, alu_op=ALU_ADD, dst=A, seq=SEQ_FETCH, label='A←A+MDR; →FETCH')

    # ── SUB addr (0x4): A ← A - MEM[addr] ────────────────────────────────────
    cs[slot(SUB)  ] = MI(mem=MEM_READ,                                     label='MDR←MEM[MAR]')
    cs[slot(SUB)+1] = MI(src1=A, src2=MDR, alu_op=ALU_SUB, dst=A, seq=SEQ_FETCH, label='A←A-MDR; →FETCH')

    # ── JMP addr (0x5): PC ← addr ────────────────────────────────────────────
    cs[slot(JMP)] = MI(src1=MAR, alu_op=ALU_PASS, dst=PC, seq=SEQ_FETCH,  label='PC←MAR; →FETCH')

    # ── JZ addr (0x6): PC ← addr if A == 0 ───────────────────────────────────
    #   SEQ_JZ: if A==0 → jaddr, else μPC+1
    #   μ+0: test; if A==0 go to μ+2 (branch taken), else μ+1 (not taken)
    #   μ+1: not taken — fall through to FETCH
    #   μ+2: taken — set PC, return to FETCH
    b = slot(JZ)
    cs[b  ] = MI(seq=SEQ_JZ, jaddr=b+2,                                   label='test A=0')
    cs[b+1] = MI(seq=SEQ_FETCH,                                            label='→FETCH (not taken)')
    cs[b+2] = MI(src1=MAR, alu_op=ALU_PASS, dst=PC, seq=SEQ_FETCH,        label='PC←MAR; →FETCH (taken)')

    # ── JNZ addr (0x7): PC ← addr if A != 0 ──────────────────────────────────
    #   Flip the test: SEQ_JZ fires on A==0, so jaddr points to "not taken".
    #   μ+0: if A==0 → μ+2 (not taken), else → μ+1 (taken)
    b = slot(JNZ)
    cs[b  ] = MI(seq=SEQ_JZ, jaddr=b+2,                                   label='test A!=0')
    cs[b+1] = MI(src1=MAR, alu_op=ALU_PASS, dst=PC, seq=SEQ_FETCH,        label='PC←MAR; →FETCH (taken)')
    cs[b+2] = MI(seq=SEQ_FETCH,                                            label='→FETCH (not taken)')

    # ── LOADI imm (0x8): A ← imm  [MAR holds imm from DISPATCH] ─────────────
    cs[slot(LOADI)] = MI(src1=MAR, alu_op=ALU_PASS, dst=A, seq=SEQ_FETCH,  label='A←imm; →FETCH')

    # ── ADDI imm (0x9): A ← A + imm ──────────────────────────────────────────
    cs[slot(ADDI)] = MI(src1=A, src2=MAR, alu_op=ALU_ADD, dst=A, seq=SEQ_FETCH, label='A←A+imm; →FETCH')

    # ── SUBI imm (0xA): A ← A - imm ──────────────────────────────────────────
    cs[slot(SUBI)] = MI(src1=A, src2=MAR, alu_op=ALU_SUB, dst=A, seq=SEQ_FETCH, label='A←A-imm; →FETCH')

    # ── MOVE (0xB): B ← A ────────────────────────────────────────────────────
    cs[slot(MOVE)] = MI(src1=A, alu_op=ALU_PASS, dst=B, seq=SEQ_FETCH,    label='B←A; →FETCH')

    # ── MOVEB (0xC): A ← B ───────────────────────────────────────────────────
    cs[slot(MOVEB)] = MI(src1=B, alu_op=ALU_PASS, dst=A, seq=SEQ_FETCH,   label='A←B; →FETCH')

    # ── INC (0xD): A ← A + 1 ─────────────────────────────────────────────────
    cs[slot(INC_OP)] = MI(src1=A, alu_op=ALU_INC, dst=A, seq=SEQ_FETCH,   label='A←A+1; →FETCH')

    # ── DEC (0xE): A ← A - 1 ─────────────────────────────────────────────────
    cs[slot(DEC_OP)] = MI(src1=A, alu_op=ALU_DEC, dst=A, seq=SEQ_FETCH,   label='A←A-1; →FETCH')

    # ── NOP (0xF) ─────────────────────────────────────────────────────────────
    cs[slot(NOP)] = MI(seq=SEQ_FETCH, label='NOP; →FETCH')

    return cs

# ── CPU ───────────────────────────────────────────────────────────────────────

class MicroCPU:
    """
    The CPU. Everything interesting is in the control store.
    The data path (ALU, registers, memory bus) is just plumbing.
    """

    def __init__(self, verbose=False):
        self.mem          = [0] * 256
        self.regs         = [0] * 8
        self.upc          = FETCH_BASE
        self.halted       = False
        self.micro_cycles = 0
        self.instrs       = 0
        self.verbose      = verbose
        self.cs           = build_control_store()

    def load(self, program, start=0):
        for i, w in enumerate(program):
            self.mem[start + i] = w & 0xFFFF
        self.regs[PC] = start
        self.upc = FETCH_BASE
        self.halted = False
        self.micro_cycles = 0
        self.instrs = 0

    def step(self):
        """Execute one microinstruction."""
        if self.halted:
            return False

        mi = self.cs[self.upc]
        old_upc = self.upc

        if self.verbose and self.upc == FETCH_BASE:
            word = self.mem[self.regs[PC] & 0xFF]
            op, operand = decode(word)
            print(f"\n  [{self.instrs:3d}] PC={self.regs[PC]}  "
                  f"{OP_NAMES.get(op, '?')} {operand}  (word=0x{word:04X})")

        # ALU
        s1 = 0 if mi.src1 == ZERO else self.regs[mi.src1]
        s2 = 0 if mi.src2 == ZERO else self.regs[mi.src2]
        result = alu(mi.alu_op, s1, s2)

        prev = {}
        if mi.dst is not None and mi.dst != ZERO:
            prev[mi.dst] = self.regs[mi.dst]
            self.regs[mi.dst] = result

        # Memory
        if mi.mem == MEM_READ:
            addr = self.regs[MAR] & 0xFF
            self.regs[MDR] = self.mem[addr]
        elif mi.mem == MEM_WRITE:
            addr = self.regs[MAR] & 0xFF
            self.mem[addr] = self.regs[MDR]

        # Sequencing
        if mi.seq == SEQ_NEXT:
            self.upc += 1
        elif mi.seq == SEQ_FETCH:
            self.instrs += 1
            self.upc = FETCH_BASE
        elif mi.seq == SEQ_DISPATCH:
            op, operand = decode(self.regs[IR])
            self.regs[MAR] = operand
            self.upc = DISPATCH_BASE + op * STRIDE
        elif mi.seq == SEQ_JZ:
            self.upc = mi.jaddr if self.regs[A] == 0 else self.upc + 1
        elif mi.seq == SEQ_HALT:
            self.instrs += 1
            self.halted = True

        self.micro_cycles += 1

        if self.verbose:
            note = ''
            if mi.dst is not None and mi.dst != ZERO:
                note += f"  [{REG_NAMES[mi.dst]}: {prev[mi.dst]} → {self.regs[mi.dst]}]"
            if mi.mem == MEM_READ:
                note += f"  [MDR←{self.regs[MDR]}]"
            if mi.mem == MEM_WRITE:
                note += f"  [MEM[{self.regs[MAR]&0xFF}]←{self.regs[MDR]}]"
            print(f"    μ{old_upc:02d}: {mi.describe()}{note}")

        return not self.halted

    def run(self, max_cycles=100_000):
        while not self.halted and self.micro_cycles < max_cycles:
            self.step()
        if self.micro_cycles >= max_cycles:
            print("  [stopped: cycle limit reached — possible infinite loop]")
        return self.halted

# ── Assembler ─────────────────────────────────────────────────────────────────

def assemble(source):
    """
    Two-pass assembler.

    Syntax:
      OPNAME [operand]   ; comment
      label:

    Immediate operands: decimal or 0x hex.
    Labels: any identifier ending in colon.
    """
    if isinstance(source, str):
        lines = source.strip().split('\n')
    else:
        lines = list(source)

    # Strip comments and blanks
    cleaned = []
    for raw in lines:
        line = raw.split(';')[0].strip()
        if line:
            cleaned.append(line)

    # Pass 1: collect labels, count instruction addresses
    labels = {}
    instructions = []
    addr = 0
    for line in cleaned:
        if line.endswith(':'):
            labels[line[:-1].strip()] = addr
        else:
            instructions.append((addr, line))
            addr += 1

    # Pass 2: encode
    program = [0] * addr
    no_operand_ops = {HALT, MOVE, MOVEB, INC_OP, DEC_OP, NOP}

    for pc, line in instructions:
        parts = line.split()
        name = parts[0].upper()
        if name not in OP_CODES:
            raise ValueError(f"Unknown instruction '{name}' at address {pc}")
        op = OP_CODES[name]

        if op in no_operand_ops:
            operand = 0
        else:
            if len(parts) < 2:
                raise ValueError(f"'{name}' requires an operand at address {pc}")
            raw = parts[1]
            if raw in labels:
                operand = labels[raw]
            else:
                operand = int(raw, 0)

        program[pc] = encode(op, operand)

    return program

# ── Test suite ────────────────────────────────────────────────────────────────

def run_tests():
    passed = 0
    failed = 0

    def check(name, source, *, expected_A=None, expected_B=None, mem=None):
        nonlocal passed, failed
        try:
            prog = assemble(source)
            cpu = MicroCPU(verbose=False)
            cpu.load(prog)
            cpu.run()
            ok = True
            msgs = []
            if expected_A is not None and cpu.regs[A] != expected_A:
                ok = False; msgs.append(f"A={cpu.regs[A]} (want {expected_A})")
            if expected_B is not None and cpu.regs[B] != expected_B:
                ok = False; msgs.append(f"B={cpu.regs[B]} (want {expected_B})")
            if mem:
                for addr_k, val in mem.items():
                    if cpu.mem[addr_k] != val:
                        ok = False; msgs.append(f"MEM[{addr_k}]={cpu.mem[addr_k]} (want {val})")
            if ok:
                print(f"  PASS  {name}")
                passed += 1
            else:
                print(f"  FAIL  {name}: {'; '.join(msgs)}")
                failed += 1
        except Exception as e:
            print(f"  ERROR {name}: {e}")
            failed += 1

    print("\nMicroprogrammed CPU — Wilkes (1967)  Test Suite")
    print("─" * 50)

    check("LOADI: load immediate value",
          "LOADI 42\nHALT",
          expected_A=42)

    check("ADDI: add immediate to A",
          "LOADI 10\nADDI 5\nHALT",
          expected_A=15)

    check("SUBI: subtract immediate from A",
          "LOADI 10\nSUBI 3\nHALT",
          expected_A=7)

    check("STORE then LOAD: round-trip through memory",
          "LOADI 99\nSTORE 200\nLOADI 0\nLOAD 200\nHALT",
          expected_A=99, mem={200: 99})

    check("ADD: accumulate from memory",
          "LOADI 7\nSTORE 201\nLOADI 3\nADD 201\nHALT",
          expected_A=10)

    check("SUB: subtract memory from A",
          "LOADI 15\nSTORE 202\nLOADI 20\nSUB 202\nHALT",
          expected_A=5)

    check("JMP: unconditional jump skips instructions",
          "JMP over\nLOADI 99\nover:\nLOADI 42\nHALT",
          expected_A=42)

    check("JZ taken: branch when A equals zero",
          "LOADI 0\nJZ target\nLOADI 99\ntarget:\nHALT",
          expected_A=0)

    check("JZ not taken: fall through when A is nonzero",
          "LOADI 5\nJZ target\nLOADI 42\ntarget:\nHALT",
          expected_A=42)

    check("JNZ taken: branch when A is nonzero",
          "LOADI 7\nJNZ target\nLOADI 99\ntarget:\nHALT",
          expected_A=7)

    check("JNZ not taken: fall through when A equals zero",
          "LOADI 0\nJNZ target\nLOADI 42\ntarget:\nHALT",
          expected_A=42)

    check("MOVE / MOVEB: copy between A and B",
          "LOADI 5\nMOVE\nLOADI 10\nMOVEB\nHALT",
          expected_A=5, expected_B=5)

    check("INC: increment A by one",
          "LOADI 9\nINC\nHALT",
          expected_A=10)

    check("DEC: decrement A by one",
          "LOADI 10\nDEC\nHALT",
          expected_A=9)

    check("NOP: no-op does not alter A",
          "LOADI 3\nNOP\nNOP\nHALT",
          expected_A=3)

    check("Loop: countdown from 5 to 0 with JNZ",
          "LOADI 5\nloop:\nSUBI 1\nJNZ loop\nHALT",
          expected_A=0)

    check("Underflow wraps: 0 - 1 = 65535",
          "LOADI 0\nSUBI 1\nHALT",
          expected_A=65535)

    check("Chain: STORE into two slots, ADD both",
          "LOADI 10\nSTORE 210\nLOADI 20\nSTORE 211\nLOADI 5\nADD 210\nADD 211\nHALT",
          expected_A=35)

    check("INC then DEC cancels out",
          "LOADI 7\nINC\nDEC\nHALT",
          expected_A=7)

    check("Conditional chain: sum only positives",
          # A = 5, store at 220. Load 0 (sentinel). JZ skip. ADD 220.
          # Effectively: if A (before reload) was 0, skip the add.
          "LOADI 5\nSTORE 220\nLOADI 3\nSTORE 221\nLOADI 0\nADD 220\nADD 221\nHALT",
          expected_A=8)

    print(f"\n{'─'*50}")
    print(f"  {passed} passed, {failed} failed")
    return failed == 0

# ── REPL ──────────────────────────────────────────────────────────────────────

BANNER = """
Microprogrammed CPU — Wilkes (1967)
════════════════════════════════════════════════════════
  Type assembly instructions one per line.
  Blank line (or RUN) assembles and executes the buffer.
  Use 'label:' syntax for jump targets.

  ISA:
    LOADI n    A ← n (immediate, 0-255)
    ADDI  n    A ← A + n
    SUBI  n    A ← A - n
    LOAD  a    A ← MEM[a]
    STORE a    MEM[a] ← A
    ADD   a    A ← A + MEM[a]
    SUB   a    A ← A - MEM[a]
    JMP   a    PC ← a
    JZ    a    PC ← a if A = 0
    JNZ   a    PC ← a if A ≠ 0
    MOVE       B ← A
    MOVEB      A ← B
    INC        A ← A + 1
    DEC        A ← A - 1
    NOP        no-op
    HALT       stop

  Commands: RUN  REGS  MEM n  CLEAR  HELP  QUIT
════════════════════════════════════════════════════════
"""

def repl(verbose=False):
    print(BANNER)
    cpu = MicroCPU(verbose=verbose)
    buf = []

    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            if buf:
                _execute(cpu, buf, verbose)
                buf = []
            continue

        cmd = line.upper()

        if cmd in ('QUIT', 'EXIT', 'Q'):
            break
        elif cmd == 'RUN':
            if buf:
                _execute(cpu, buf, verbose)
                buf = []
            else:
                print("  No program in buffer. Type instructions first.")
        elif cmd == 'REGS':
            r = cpu.regs
            print(f"  A={r[A]}  B={r[B]}  PC={r[PC]}")
        elif cmd.startswith('MEM '):
            try:
                addr = int(cmd.split()[1], 0)
                print(f"  MEM[{addr}] = {cpu.mem[addr & 0xFF]}")
            except (IndexError, ValueError):
                print("  Usage: MEM <address>")
        elif cmd == 'CLEAR':
            buf = []
            print("  Buffer cleared.")
        elif cmd == 'RESET':
            cpu = MicroCPU(verbose=verbose)
            buf = []
            print("  CPU reset.")
        elif cmd == 'HELP':
            print(BANNER)
        else:
            buf.append(line)

def _execute(cpu, lines, verbose):
    try:
        program = assemble(lines)
    except ValueError as e:
        print(f"  Assemble error: {e}")
        return

    cpu.load(program)
    cpu.run()

    r = cpu.regs
    print(f"\n  {cpu.instrs} instructions  ({cpu.micro_cycles} μcycles)")
    print(f"  A={r[A]}  B={r[B]}  PC={r[PC]}")

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Microprogrammed CPU — Wilkes (1967)")
    p.add_argument('--test',    action='store_true', help='run test suite')
    p.add_argument('--verbose', action='store_true', help='show microinstruction trace')
    args = p.parse_args()

    if args.test:
        ok = run_tests()
        sys.exit(0 if ok else 1)

    repl(verbose=args.verbose)

if __name__ == '__main__':
    main()

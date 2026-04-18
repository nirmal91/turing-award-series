"""
Microprogram-controlled CPU — inspired by Maurice Wilkes's microprogramming design, 1951.

Wilkes's insight: replace hardwired control logic with a small control memory (ROM).
Each machine instruction maps to a sequence of micro-operations stored at a fixed
address in the control store. Adding a new instruction means adding rows to the
control store, not rewiring gates.

This mirrors the two-level structure from:
  "The Best Way to Design an Automatic Calculating Machine" (Wilkes, 1951)

Architecture:
    Registers:    AC (accumulator), PC, MAR, MDR, IR
    Memory:       256 words of 16-bit RAM
    Control unit: microprogram ROM (the control store) + microsequencer

Machine instructions:
    LOAD  addr     AC = RAM[addr]
    STORE addr     RAM[addr] = AC
    ADD   addr     AC = AC + RAM[addr]
    SUB   addr     AC = AC - RAM[addr]
    JMP   addr     PC = addr
    JZ    addr     if AC == 0: PC = addr
    HALT           stop

Usage:
    python microprogramming.py            # interactive REPL
    python microprogramming.py --test     # run test suite (10+ cases)
    python microprogramming.py --verbose  # show micro-op trace per step
"""

from __future__ import annotations
import sys
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# 1. MACHINE INSTRUCTION SET
# ---------------------------------------------------------------------------

OPCODES: dict[str, int] = {
    "LOAD":  0,
    "STORE": 1,
    "ADD":   2,
    "SUB":   3,
    "JMP":   4,
    "JZ":    5,
    "HALT":  6,
}
OPCODE_NAMES: dict[int, str] = {v: k for k, v in OPCODES.items()}

ADDR_BITS = 8        # 8-bit address field → 256 words of RAM
WORD_MASK = 0xFFFF


# ---------------------------------------------------------------------------
# 2. CONTROL STORE — the microprogram ROM
#
# Each entry: (micro-op name, next-MPC)
# next-MPC:
#   None        → MPC + 1 (fall through to next microinstruction)
#   "FETCH"     → 0       (restart the fetch cycle = start next instruction)
#   "DISPATCH"  → DISPATCH_TABLE[IR.opcode]  (decode opcode, jump to routine)
# ---------------------------------------------------------------------------

# Maps each machine opcode to its starting address in the control store.
DISPATCH_TABLE: dict[int, int] = {
    0: 10,   # LOAD
    1: 20,   # STORE
    2: 30,   # ADD
    3: 40,   # SUB
    4: 50,   # JMP
    5: 60,   # JZ
    6: 70,   # HALT
}

#   μaddr  (micro-op,    next-MPC)
CONTROL_STORE: dict[int, tuple[str, object]] = {

    # ── Fetch cycle (shared by every machine instruction) ─────────────────
    # This is what Wilkes called the "order fetch" — identical hardware path
    # regardless of which instruction is being fetched.
    0: ("MAR_PC",   None),          # MAR ← PC
    1: ("MDR_RAM",  None),          # MDR ← RAM[MAR]
    2: ("PC_INCR",  None),          # PC  ← PC + 1
    3: ("IR_MDR",   "DISPATCH"),    # IR  ← MDR; decode opcode → routine

    # ── LOAD: AC = RAM[addr] ──────────────────────────────────────────────
    10: ("MAR_IR",  None),          # MAR ← IR.addr
    11: ("MDR_RAM", None),          # MDR ← RAM[MAR]
    12: ("AC_MDR",  "FETCH"),       # AC  ← MDR; done

    # ── STORE: RAM[addr] = AC ─────────────────────────────────────────────
    20: ("MAR_IR",  None),          # MAR ← IR.addr
    21: ("MDR_AC",  None),          # MDR ← AC
    22: ("RAM_MDR", "FETCH"),       # RAM[MAR] ← MDR; done

    # ── ADD: AC = AC + RAM[addr] ──────────────────────────────────────────
    30: ("MAR_IR",  None),          # MAR ← IR.addr
    31: ("MDR_RAM", None),          # MDR ← RAM[MAR]
    32: ("AC_ADD",  "FETCH"),       # AC  ← AC + MDR; done

    # ── SUB: AC = AC - RAM[addr] ──────────────────────────────────────────
    40: ("MAR_IR",  None),          # MAR ← IR.addr
    41: ("MDR_RAM", None),          # MDR ← RAM[MAR]
    42: ("AC_SUB",  "FETCH"),       # AC  ← AC - MDR; done

    # ── JMP: PC = addr ────────────────────────────────────────────────────
    50: ("PC_JMP",  "FETCH"),       # PC  ← IR.addr; done

    # ── JZ: if AC == 0: PC = addr ─────────────────────────────────────────
    60: ("PC_JZ",   "FETCH"),       # if AC==0: PC ← IR.addr; done

    # ── HALT ──────────────────────────────────────────────────────────────
    70: ("HALT",    None),
}


# ---------------------------------------------------------------------------
# 3. ASSEMBLER — source text → machine words placed in RAM
#
# Machine word layout:
#   bits 15-8: opcode  (8 bits)
#   bits  7-0: address (8 bits)
#
# Directives:
#   .data ADDR VALUE   — place VALUE at explicit RAM address ADDR
#   name:              — label; resolves to current instruction address
# ---------------------------------------------------------------------------

def assemble(source: str) -> tuple[dict[int, int], dict[str, int]]:
    lines = source.splitlines()

    cleaned: list[str] = []
    for line in lines:
        for comment_char in (";", "#"):
            if comment_char in line:
                line = line[:line.index(comment_char)]
        line = line.strip()
        if line:
            cleaned.append(line)

    # Pass 1: resolve labels and separate instructions from .data directives
    labels: dict[str, int] = {}
    instr_list: list[tuple[int, str]] = []   # (instruction_addr, line)
    data_list:  list[tuple[int, int]] = []   # (ram_addr, value)

    pc = 0
    for line in cleaned:
        if line.endswith(":"):
            labels[line[:-1].strip().upper()] = pc
        elif line.lower().startswith(".data"):
            parts = line.split()
            if len(parts) != 3:
                raise SyntaxError(f".data requires address and value: {line!r}")
            data_list.append((int(parts[1], 0), int(parts[2], 0)))
        else:
            instr_list.append((pc, line))
            pc += 1

    # Pass 2: encode instructions
    words: dict[int, int] = {}

    for addr, val in data_list:
        words[addr] = val & WORD_MASK

    for iaddr, line in instr_list:
        parts = line.split()
        mnemonic = parts[0].upper()
        if mnemonic not in OPCODES:
            raise SyntaxError(f"Unknown mnemonic {mnemonic!r}")
        opcode = OPCODES[mnemonic]
        operand = 0
        if len(parts) > 1:
            raw = parts[1].upper()
            if raw in labels:
                operand = labels[raw]
            else:
                try:
                    operand = int(raw, 0)
                except ValueError:
                    raise SyntaxError(f"Bad operand {parts[1]!r}")
        words[iaddr] = ((opcode << ADDR_BITS) | (operand & 0xFF)) & WORD_MASK

    return words, labels


# ---------------------------------------------------------------------------
# 4. CPU — registers + microsequencer
# ---------------------------------------------------------------------------

@dataclass
class CPU:
    ram:         dict[int, int] = field(default_factory=dict)
    AC:          int  = 0      # accumulator
    PC:          int  = 0      # program counter
    MAR:         int  = 0      # memory address register
    MDR:         int  = 0      # memory data register
    IR:          int  = 0      # instruction register
    MPC:         int  = 0      # microprogram counter
    halted:      bool = False
    cycle_count: int  = 0      # completed machine instructions
    micro_count: int  = 0      # microinstructions executed

    def _ram_read(self, addr: int) -> int:
        return self.ram.get(addr & 0xFF, 0)

    def _ram_write(self, addr: int, val: int) -> None:
        self.ram[addr & 0xFF] = val & WORD_MASK

    @property
    def _ir_opcode(self) -> int:
        return (self.IR >> ADDR_BITS) & 0xFF

    @property
    def _ir_addr(self) -> int:
        return self.IR & 0xFF

    def step_micro(self, verbose: bool = False) -> bool:
        """Execute one microinstruction. Returns False when halted."""
        if self.halted:
            return False

        if self.MPC == 0:
            self.cycle_count += 1

        entry = CONTROL_STORE.get(self.MPC)
        if entry is None:
            raise RuntimeError(f"No microinstruction at μPC={self.MPC}")

        op, next_mpc = entry
        self.micro_count += 1

        if verbose:
            instr_name = OPCODE_NAMES.get(self._ir_opcode, "?")
            print(f"  μPC={self.MPC:3d}  {op:12s}  "
                  f"AC={self.AC:6}  PC={self.PC:3}  "
                  f"MAR={self.MAR:3}  MDR={self.MDR:6}  "
                  f"IR={instr_name}({self._ir_addr})")

        # Execute the micro-op — each line is one datapath transfer
        if   op == "MAR_PC":   self.MAR = self.PC
        elif op == "MDR_RAM":  self.MDR = self._ram_read(self.MAR)
        elif op == "PC_INCR":  self.PC  = (self.PC + 1) & 0xFF
        elif op == "IR_MDR":   self.IR  = self.MDR
        elif op == "MAR_IR":   self.MAR = self._ir_addr
        elif op == "AC_MDR":   self.AC  = self.MDR
        elif op == "MDR_AC":   self.MDR = self.AC
        elif op == "RAM_MDR":  self._ram_write(self.MAR, self.MDR)
        elif op == "AC_ADD":   self.AC  = (self.AC + self.MDR) & WORD_MASK
        elif op == "AC_SUB":   self.AC  = (self.AC - self.MDR) & WORD_MASK
        elif op == "PC_JMP":   self.PC  = self._ir_addr
        elif op == "PC_JZ":
            if self.AC == 0:
                self.PC = self._ir_addr
        elif op == "HALT":
            self.halted = True
            return False
        else:
            raise RuntimeError(f"Unknown micro-op: {op!r}")

        # Advance the microprogram counter
        if next_mpc == "FETCH":
            self.MPC = 0
        elif next_mpc == "DISPATCH":
            opcode = self._ir_opcode
            if opcode not in DISPATCH_TABLE:
                raise RuntimeError(f"Unknown opcode: {opcode}")
            self.MPC = DISPATCH_TABLE[opcode]
        elif next_mpc is None:
            self.MPC += 1
        else:
            self.MPC = int(next_mpc)

        return True

    def run(self, max_cycles: int = 100_000, verbose: bool = False) -> None:
        while not self.halted and self.cycle_count <= max_cycles:
            if not self.step_micro(verbose=verbose):
                break
        if not self.halted:
            raise RuntimeError(f"Exceeded {max_cycles} machine instruction cycles")


# ---------------------------------------------------------------------------
# 5. REPL
# ---------------------------------------------------------------------------

EXAMPLE_PROGRAMS: dict[str, tuple[str, str]] = {
    "1": (
        "Add two numbers (10 + 32 = 42)",
        ".data 100 10\n.data 101 32\nLOAD 100\nADD  101\nHALT",
    ),
    "2": (
        "Conditional: load 99 only if first value is zero",
        ".data 100 0\n.data 200 99\n"
        "LOAD 100\nJZ   NONZERO\nHALT\n"
        "NONZERO:\nLOAD 200\nHALT",
    ),
    "3": (
        "Memory round-trip: compute 50 - 8, store result, reload",
        ".data 100 50\n.data 101 8\n"
        "LOAD 100\nSUB  101\nSTORE 102\nLOAD 102\nHALT",
    ),
}

HELP_TEXT = """\
Commands:
  load          — enter a program line by line (blank line finishes)
  run           — run the loaded program from PC=0
  example N     — load built-in example (N = 1, 2, or 3)
  show          — show registers and non-zero RAM
  reset         — clear everything
  help          — this message
  quit / exit   — exit

Assembly syntax:
  OPCODE [addr]         LOAD 100 / ADD 101 / JMP 5 / HALT
  .data ADDR VALUE      place a value at a specific RAM address
  label:                define a label (resolves to next instruction address)
  ; or # comment        rest of line ignored

Examples:
  > example 1           load the "10 + 32" program
  > run                 execute it
"""

def _show_cpu(cpu: CPU) -> None:
    ac = cpu.AC if cpu.AC < 0x8000 else cpu.AC - 0x10000
    print(f"  AC={ac}  PC={cpu.PC}  halted={cpu.halted}  "
          f"cycles={cpu.cycle_count}  micro-ops={cpu.micro_count}")
    nonzero = {k: v for k, v in sorted(cpu.ram.items()) if v != 0}
    if nonzero:
        print(f"  RAM (non-zero): {nonzero}")


def repl(verbose: bool = False) -> None:
    print("Microprogram-controlled CPU  (Wilkes, 1951 style)")
    print("Type 'help' for commands, 'quit' to exit.\n")

    cpu = CPU()
    program_lines: list[str] = []
    program_loaded = False

    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue
        lower = line.lower()

        if lower in ("quit", "exit"):
            break

        elif lower == "help":
            print(HELP_TEXT)

        elif lower == "reset":
            cpu = CPU()
            program_lines = []
            program_loaded = False
            print("Reset.")

        elif lower == "show":
            _show_cpu(cpu)

        elif lower.startswith("example"):
            parts = lower.split()
            key = parts[1] if len(parts) > 1 else ""
            if key not in EXAMPLE_PROGRAMS:
                print(f"  Unknown example. Choose 1, 2, or 3.")
                continue
            desc, src = EXAMPLE_PROGRAMS[key]
            print(f"  {desc}")
            print()
            for l in src.splitlines():
                print(f"    {l}")
            print()
            try:
                cpu = CPU()
                words, labels = assemble(src)
                cpu.ram.update(words)
                program_lines = src.splitlines()
                program_loaded = True
                print(f"  Loaded {len(words)} word(s)."
                      + (f" Labels: {dict((k.lower(), v) for k,v in labels.items())}" if labels else ""))
            except SyntaxError as e:
                print(f"  Assembler error: {e}")

        elif lower == "load":
            print("Enter program (blank line to finish):")
            new_lines: list[str] = []
            while True:
                try:
                    pline = input("  ")
                except EOFError:
                    break
                if not pline.strip():
                    break
                new_lines.append(pline)
            src = "\n".join(new_lines)
            try:
                cpu = CPU()
                words, labels = assemble(src)
                cpu.ram.update(words)
                program_lines = new_lines
                program_loaded = True
                print(f"  Loaded {len(words)} word(s)."
                      + (f" Labels: {dict((k.lower(), v) for k,v in labels.items())}" if labels else ""))
            except (SyntaxError, ValueError) as e:
                print(f"  Assembler error: {e}")

        elif lower == "run":
            if not program_loaded:
                print("  No program loaded. Use 'load' or 'example N'.")
                continue
            cpu.PC = 0
            cpu.MPC = 0
            cpu.halted = False
            cpu.cycle_count = 0
            cpu.micro_count = 0
            cpu.AC = 0
            try:
                cpu.run(verbose=verbose)
                ac = cpu.AC if cpu.AC < 0x8000 else cpu.AC - 0x10000
                print(f"  Halted.  AC={ac}  cycles={cpu.cycle_count}  "
                      f"micro-ops={cpu.micro_count}")
                nonzero = {k: v for k, v in sorted(cpu.ram.items())
                           if v != 0 and k >= 64}  # skip instruction words
                if nonzero:
                    print(f"  RAM (data): {nonzero}")
            except RuntimeError as e:
                print(f"  Runtime error: {e}")

        else:
            print(f"  Unknown command: {line!r}. Type 'help' for commands.")


# ---------------------------------------------------------------------------
# 6. TESTS
# ---------------------------------------------------------------------------

def run_tests() -> None:
    def check(name: str, source: str, expected_ac: int) -> None:
        cpu = CPU()
        words, _ = assemble(source)
        cpu.ram.update(words)
        cpu.run()
        ac = cpu.AC if cpu.AC < 0x8000 else cpu.AC - 0x10000
        assert ac == expected_ac, (
            f"FAIL [{name}]: AC={ac}, expected {expected_ac}"
        )
        print(f"  PASS  {name}")

    print("Running tests...")

    # 1. LOAD a value from RAM into AC
    check("LOAD",
          ".data 100 42\nLOAD 100\nHALT",
          42)

    # 2. ADD two values
    check("ADD",
          ".data 100 10\n.data 101 32\nLOAD 100\nADD 101\nHALT",
          42)

    # 3. SUB two values
    check("SUB",
          ".data 100 50\n.data 101 8\nLOAD 100\nSUB 101\nHALT",
          42)

    # 4. STORE then reload
    check("STORE and reload",
          ".data 100 99\nLOAD 100\nSTORE 101\nLOAD 101\nHALT",
          99)

    # 5. JMP skips HALT, reaches LOAD
    check("JMP unconditional",
          "JMP SKIP\nHALT\nSKIP:\n.data 100 7\nLOAD 100\nHALT",
          7)

    # 6. JZ taken: AC is zero, so jump executes
    check("JZ taken (AC=0)",
          ".data 100 0\n.data 200 99\n"
          "LOAD 100\nJZ NONZERO\nHALT\n"
          "NONZERO:\nLOAD 200\nHALT",
          99)

    # 7. JZ not taken: AC is nonzero, jump does not execute
    check("JZ not taken (AC!=0)",
          ".data 100 1\n.data 200 99\n"
          "LOAD 100\nJZ SKIP\nHALT\n"
          "SKIP:\nLOAD 200\nHALT",
          1)

    # 8. Chain: (10 + 5) - 3 = 12
    check("chain arithmetic",
          ".data 200 10\n.data 201 5\n.data 202 3\n"
          "LOAD 200\nADD 201\nSUB 202\nHALT",
          12)

    # 9. Sum five values: 1+2+3+4+5 = 15
    check("sum 1..5",
          ".data 200 1\n.data 201 2\n.data 202 3\n.data 203 4\n.data 204 5\n"
          "LOAD 200\nADD 201\nADD 202\nADD 203\nADD 204\nHALT",
          15)

    # 10. STORE result then check it via LOAD
    check("store result",
          ".data 200 100\n.data 201 23\n"
          "LOAD 200\nSUB 201\nSTORE 202\nLOAD 202\nHALT",
          77)

    # 11. Negative result (signed 16-bit)
    check("negative result",
          ".data 200 3\n.data 201 10\n"
          "LOAD 200\nSUB 201\nHALT",
          -7)

    # 12. Micro-op count: HALT alone must execute >0 micro-ops
    cpu = CPU()
    words, _ = assemble("HALT")
    cpu.ram.update(words)
    cpu.run()
    assert cpu.micro_count > 0
    print(f"  PASS  micro-op count (HALT = {cpu.micro_count} micro-ops, "
          f"{cpu.cycle_count} instruction cycle)")

    # 13. LOAD instruction uses exactly 7 micro-ops (4 fetch + 3 LOAD routine)
    cpu = CPU()
    words, _ = assemble(".data 100 1\nLOAD 100\nHALT")
    cpu.ram.update(words)
    cpu.run()
    # LOAD: 7 micro-ops; HALT: 5 micro-ops; total = 12
    assert cpu.micro_count == 12, f"Expected 12 micro-ops, got {cpu.micro_count}"
    print(f"  PASS  micro-op count for LOAD+HALT = {cpu.micro_count}")

    print("\nAll tests passed.\n")


# ---------------------------------------------------------------------------
# 7. ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--test" in sys.argv:
        run_tests()
    else:
        verbose = "--verbose" in sys.argv or "-v" in sys.argv
        repl(verbose=verbose)

# Week 02 — Maurice Wilkes (1967)

**ACM Turing Award citation:** *"Professor Wilkes is best known as the builder of the EDSAC, the first computer with an internally stored program."*

---

## My Take

*[Nirmal's take — coming soon.]*

---

## The Code

[`microprogramming.py`](./microprogramming.py) — a microprogram-controlled CPU simulator that mirrors Wilkes's 1951 design:

```
control store (ROM) → microsequencer → datapath transfers → result
```

Each machine instruction (LOAD, ADD, JMP, etc.) is implemented as a short routine of micro-operations stored in the control store. The CPU doesn't know how to "do ADD" in hardware — it reads the ADD routine from the control store and follows it step by step.

```bash
# Interactive assembler REPL
python microprogramming.py

# Run the test suite (13 test cases)
python microprogramming.py --test

# Show micro-op trace for each instruction
python microprogramming.py --verbose
```

Example session:

```
> example 1
  Add two numbers (10 + 32 = 42)

    .data 100 10
    .data 101 32
    LOAD 100
    ADD  101
    HALT

  Loaded 5 word(s).
> run
  Halted.  AC=42  cycles=3  micro-ops=19
  RAM (data): {100: 10, 101: 32}
```

With `--verbose`, you see every micro-op:

```
  μPC=  0  MAR_PC        AC=     0  PC=  0  MAR=  0  MDR=     0  IR=LOAD(0)
  μPC=  1  MDR_RAM       AC=     0  PC=  0  MAR=  0  MDR=   100  IR=LOAD(0)
  μPC=  2  PC_INCR       AC=     0  PC=  1  MAR=  0  MDR=   100  IR=LOAD(0)
  μPC=  3  IR_MDR        AC=     0  PC=  1  MAR=  0  MDR=   100  IR=LOAD(100)
  μPC= 10  MAR_IR        AC=     0  PC=  1  MAR=100  MDR=   100  IR=LOAD(100)
  μPC= 11  MDR_RAM       AC=     0  PC=  1  MAR=100  MDR=    10  IR=LOAD(100)
  μPC= 12  AC_MDR        AC=    10  PC=  1  MAR=100  MDR=    10  IR=LOAD(100)
  ...
```

The fetch cycle (μPC 0–3) is identical for every instruction. After decoding the opcode, the microsequencer jumps to that instruction's routine in the control store.

---

## ELI5 — Explain Like I'm 5

Imagine a toy robot that can wave, walk, and jump. Inside the robot, "walk" is really lots of tiny steps: move left foot, shift weight, move right foot, shift weight. Someone had to figure out each of those tiny steps.

Old computers had the tiny steps glued in — wired permanently into the machine. If you wanted to change how something worked, you had to rebuild the whole machine.

Maurice Wilkes said: write the tiny steps in a small notebook, and have the robot read the notebook. Now you can change what "walk" means just by rewriting a page. You don't have to touch the robot at all.

---

## ELI10 — Explain Like I'm 10

Every computer instruction — ADD, LOAD, JUMP — is actually several tiny steps happening one after another. Before 1951, engineers wired those steps directly into the processor using transistors and logic gates. One instruction per wire pattern. If you wanted to change how ADD worked, you had to physically rebuild the chip.

Maurice Wilkes had a better idea: put those tiny steps in a small, fast memory called a **control store**. The hardware reads the control store like a recipe book. Want to add a new instruction? Add a recipe. Want to fix a bug in MUL? Change that recipe.

Those tiny steps are called **micro-operations**, and the technique is called **microprogramming**. Wilkes published it in 1951. IBM used it to build the System/360 family in 1964 — the same set of instructions running on machines with completely different hardware, all because different machines could have different control stores mapping to the same recipes. Today's x86 processors still use a version of this.

But Wilkes didn't just invent microprogramming. Before that, in 1949, he built **EDSAC** at Cambridge — one of the first computers where the program lived in memory alongside the data. That's the stored-program design. Before stored-program computers, programs were wired in externally or set up by physically plugging cables. Wilkes made the program just another thing the computer reads from memory, the same way it reads data. Every computer since works that way.

---

## CS Graduate Level — Why Wilkes Actually Mattered

### 1. EDSAC (1949): Stored-Program in Practice

EDSAC (Electronic Delay Storage Automatic Calculator) at Cambridge ran its first program on 6 May 1949 — computing a table of squares. It was one of the first operational stored-program computers, running weeks after Manchester's SSEM but before most other machines.

**Mercury delay-line memory** was EDSAC's storage technology. Tubes of liquid mercury with transducers at each end: a bit entered as an electrical pulse, converted to an ultrasound pulse, propagated through the mercury at ~1450 m/s, and was re-amplified and re-injected at the near end to circulate. This gave cheap sequential storage — but with a catch: you couldn't address a bit randomly. You had to wait for it to cycle past the read head. Optimal EDSAC programming meant scheduling instructions to minimize this rotational wait, much like Perlis's IBM 650 drum timing.

**Subroutines as a design pattern.** Wilkes, Wheeler, and Gill published *The Preparation of Programs for an Electronic Digital Computer* in 1951 — the first programming textbook. It introduced the subroutine library as a first-class engineering concept: reusable, named, callable routines stored separately from the main program. The book included a library of 87 subroutines on punched cards. This was the first software library.

### 2. Microprogramming (1951): The Control Store

Wilkes presented "The Best Way to Design an Automatic Calculating Machine" at the Manchester University Computer Inaugural Conference in 1951. The paper introduced microprogramming.

**The problem.** A CPU's control unit coordinates every datapath action: which register to read, what the ALU should do, which register to write, whether to access memory, whether to branch. In a hardwired design, this logic is custom combinational circuitry per instruction. For a small instruction set (8 instructions) this is manageable. For a large one (100+ instructions, as IBM wanted) it becomes a verification nightmare.

**Wilkes's solution.** Decompose the control unit into:
1. A **control store** — a small ROM containing microinstructions
2. A **microsequencer** — a counter that steps through microinstructions
3. A **dispatch table** — maps each machine opcode to its starting address in the control store

Each machine instruction becomes a short subroutine of micro-operations. The fetch cycle (read instruction from memory, increment PC, decode opcode) is itself a shared micro-routine. The microsequencer just reads and executes entries from the control store.

**A microinstruction** specifies one or more register transfers happening simultaneously on the datapath. In Wilkes's original 1951 diagram, microinstructions were organized as a matrix: rows were micro-ops, columns were control signals (read A, read B, write C, ALU function, memory enable). Each entry in the matrix was a bit: 1 = this signal fires this cycle, 0 = it doesn't. This gave a compact, regular structure.

In modern terms: a microinstruction is a wide control word that encodes all signals needed for one datapath cycle. Horizontal microprogramming uses one bit per control signal (wide, fast). Vertical microprogramming encodes signals more compactly (narrower words, needs decoding). The control store is traded off against the complexity of each microinstruction's encoding.

### 3. IBM System/360 and the Legacy

IBM used microprogramming to implement the System/360 (1964). The 360 family spanned multiple models — widely different speeds and costs — but all executed the same instruction set. This was the first truly compatible family of computers, enabling IBM to sell upgrades without forcing software rewrites.

Microprogramming made compatibility feasible: each model had a different microprogram implementing the same machine-level ISA. The fast, expensive models had hardware that let them execute micro-ops quickly; the slower models had simpler hardware and longer micro-routines. The ISA was the stable interface; the microcode was the implementation detail.

### 4. x86 and Modern Relevance

Intel's x86 line, starting with the 8086 (1978), used microprogramming to implement CISC instructions. The 8086 had a ROM-based microcode engine: complex instructions (ENTER, LOOP, string ops) decoded into sequences of micro-ops internally.

Modern x86 processors still translate x86 instructions into RISC-like micro-ops before issuing them to the execution engine. This isn't classical microprogramming in Wilkes's sense — it's a ROM-based decode table feeding a superscalar out-of-order engine — but the fundamental idea is the same: machine instructions are an abstraction over an internal micro-operation level.

The RISC movement of the 1980s (Patterson, Hennessy) argued that microprogramming enabled excessive complexity. RISC designs eliminated microcode by using only instructions simple enough to implement directly in hardwired logic. The debate between RISC simplicity and CISC microprogrammed compatibility is still live in the ARM vs. x86 space.

### 5. Wilkes on Cache Memory (1965)

In 1965 Wilkes proposed the "slave store" — a small, fast memory sitting between the CPU and main memory, transparently holding recently accessed data. His paper described the hit/miss logic and the benefit in access latency. The term "cache" came from other researchers, but the architectural concept is Wilkes's.

This is the cache hierarchy that every modern CPU uses: L1, L2, L3 caches sitting between the processor and DRAM, transparently managed by hardware.

### Connecting the Two Contributions

EDSAC and microprogramming look like separate ideas, but they share a design philosophy: separate the specification of computation from its physical implementation. With EDSAC, the program is a specification stored in memory, not wired into hardware. With microprogramming, the instruction set is a specification stored in the control store, not wired into logic. Both are instances of the same move: put the description in memory, let hardware interpret it. This is the central idea of the stored-program model, taken one level down.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [The Best Way to Design an Automatic Calculating Machine](https://doi.org/10.1007/978-1-4684-1372-3_14) | Manchester University Computer Inaugural Conference | 1951 |
| [The Preparation of Programs for an Electronic Digital Computer](https://dl.acm.org/doi/10.5555/1102399) *(with Wheeler & Gill)* | Addison-Wesley | 1951 |
| [Slave Memories and Dynamic Storage Allocation](https://doi.org/10.1109/PGEC.1965.263770) *(cache proposal)* | IEEE Transactions on Electronic Computers | 1965 |
| [Computers Then and Now](https://dl.acm.org/doi/10.1145/321439.321440) *(Turing Award lecture)* | JACM 15(1) | 1968 |
| [Memoirs of a Computer Pioneer](https://mitpress.mit.edu/9780262730518/) | MIT Press | 1985 |

---

*Previous: [Week 01 — Alan Jay Perlis (1966)](../01-alan-perlis-1966/)*
*Next: Week 03 — Richard Hamming (1968)*

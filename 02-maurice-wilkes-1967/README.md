# Week 02 — Maurice Wilkes (1967)

**ACM Turing Award citation:** *"Professor Wilkes is best known as the builder and designer of the EDSAC, the first computer with an internally stored program. Built in 1949, the EDSAC used a mercury delay line memory."*

---

## My Take

Before Wilkes, if you wanted to change how a computer worked, you changed the hardware. He made it a software problem instead.

Every small change required rewiring. New chips, new gates, because instructions were hardcoded into the silicon. If you wanted to add one, or fix one, you weren't updating code. You were rebuilding the machine.

Wilkes changed that in 1951 with microprogramming. Instead of hardcoding operations into hardware, he introduced a recipe book stored in ROM (read only memory), called a control store. If you wanted to change how the underlying hardware behaves, don't touch transistors and just change the recipe. That was a massive shift in reusability and portability.

Almost all progress over the last 70 years has been about adding more of these abstractions, each one building on the last. BIOS, operating systems, applications. All follow the same pattern. I have always dreaded on-prem compared to cloud because it seems painful to slowly push updates, bulk things, etc. Having to actually change hardware seems like 100x more complex, which was the norm before Wilkes. The thing we take for granted, that you can change behavior without touching the machine, started here.

---

## The Code

[`implementation.py`](./implementation.py) — a microprogrammed CPU simulator that mirrors Wilkes's 1951 architecture:

```
assembly source → assembler → machine program
                                     ↓
             ┌───────────────────────────────────────────┐
             │  MicroCPU                                 │
             │                                           │
             │  fetch:  MAR←PC → MDR←MEM[MAR] → IR←MDR  │
             │          → PC++ → DISPATCH                │
             │                     ↓                     │
             │  control store  (68-word ROM)              │
             │  opcode × STRIDE → microprogram            │
             │                     ↓                     │
             │  data path: registers ↔ ALU ↔ memory      │
             └───────────────────────────────────────────┘
                                     ↓
                              register state
```

The control store is the whole point. Every machine instruction's behavior is encoded as a sequence of microinstructions in ROM. Nothing is hardwired.

ISA (16 instructions): `LOADI ADDI SUBI LOAD STORE ADD SUB JMP JZ JNZ MOVE MOVEB INC DEC NOP HALT`

```bash
python3 implementation.py           # interactive assembler REPL
python3 implementation.py --test    # run test suite (20 cases)
python3 implementation.py --verbose # show microinstruction trace
```

Example session — summing two values:

```
> LOADI 10
> STORE 200
> LOADI 25
> ADD 200
> HALT
>
  5 instructions  (26 μcycles)
  A=35  B=0  PC=5
```

With `--verbose`, the ADD instruction expands into its microprogram:

```
  [  3] PC=3  ADD 200  (word=0x30C8)
    μ00: MAR←PC          [MAR: 200 → 3]
    μ01: MDR←MEM[MAR]    [MDR←12488]
    μ02: IR←MDR          [IR: 24576 → 12488]
    μ03: PC←PC+1  →DISPATCH  [PC: 3 → 4]
    μ16: MDR←MEM[MAR]    [MDR←10]
    μ17: A←A+MDR  →FETCH [A: 25 → 35]
```

Six microinstructions to execute one machine instruction. Each microinstruction controls the data path for one clock cycle. That's the Wilkes layer.

---

## ELI5

Imagine a machine that can only do one thing: add two numbers. That's it. The ADD instruction is wired directly into the circuits inside.

Now you want it to also subtract. You can't just ask nicely. You have to open the machine, pull out wires, solder new ones in. It takes weeks. And if you want multiply after that, same thing all over again.

Wilkes said: stop wiring instructions into the machine. Write them down in a little book instead. ADD is page 1: "take these two numbers, run them through the adder, write the result back." To add SUBTRACT, you add page 2. No wires touched. No hardware changed. Just a new page.

That book is the control store. That's his invention.

---

## ELI10

Before Wilkes, every instruction a computer understood was wired directly into its hardware. The circuits for "add two numbers" were physical relays and vacuum tubes, soldered in a fixed arrangement. If you wanted to add a new instruction, you had to redesign the circuitry. IBM hit this wall — they'd committed the chip design before realising they'd left out useful instructions. Too late to fix without building a new machine.

Wilkes's idea: instead of wiring instruction logic into hardware, write it down in a small read-only memory called a *control store*. To add a new instruction, you add new entries to that memory. No hardware change.

This meant IBM could build a cheap slow machine and an expensive fast machine that ran the same programs — like a Toyota and a Ferrari that both respond to the same steering wheel. Each had different hardware underneath, but the same instructions on top, each implemented in its own microcode. That was the IBM System/360 in 1964, and it changed the industry.

Modern Intel and AMD chips still work this way. When Intel patched the Spectre vulnerability in 2018, they didn't ship new hardware. They pushed a microcode update.

---

## CS Graduate Level — Why Microprogramming Mattered

### 1. The State of the Art Before (1945–1950)

Early stored-program computers (Manchester Baby, June 1948; EDSAC, May 1949) implemented the Von Neumann architecture: programs and data in the same memory, instructions executed sequentially. But the *control unit* — the part that decoded instructions and sequenced the data path — was purely hardwired.

Each machine instruction had a corresponding fixed arrangement of logic gates. The decode logic would recognise the opcode and activate a set of gates in the right order, each clock cycle doing one step of the operation. If you wanted to change what an instruction did, or add a new one, you were in the hardware.

The prevailing assumption was that this was inevitable. Control is complex; you need silicon to be fast.

### 2. Wilkes's Insight (1951)

Wilkes presented the idea at the Manchester University Computer Inaugural Conference in July 1951. The paper was titled "The Best Way to Design an Automatic Calculating Machine."

His key observation: the control unit itself can be seen as a special-purpose computer, interpreting a program stored in memory. That "program" is the microprogram. The "memory" holding it is the control store — a small ROM, much faster than main memory.

Each microinstruction is a wide word (20+ bits in early implementations) where different bit fields activate different data-path signals simultaneously:
- Which register feeds the ALU's left input
- Which register (or immediate) feeds the ALU's right input
- Which ALU operation to perform
- Which register receives the result
- Whether to read or write main memory
- Which microinstruction comes next

The collection of these entries forms a *control matrix* — Wilkes's term. The machine instruction decoder just indexes into this matrix to find the first microinstruction for that opcode, then the microprogram runs to completion before fetching the next machine instruction.

### 3. Concrete Example — the ADD Instruction

**Before microprogramming (hardwired control):**

To execute `ADD addr`, the control unit's gate network would:
1. Assert "route PC to memory address bus" — a fixed gate path
2. Latch the memory output into IR — another fixed path
3. Increment PC — via a hardwired incrementer circuit
4. Decode IR's opcode field — a fixed combinational logic block activating the "ADD" signal
5. Route `addr` to the memory address bus — a fixed mux selection
6. Route the memory output to one ALU input — a fixed wire
7. Route the accumulator to the other ALU input — another fixed wire
8. Assert "ALU = ADD" — activates the adder logic
9. Write ALU output back to the accumulator — a fixed feedback path

Each of these steps involves specific gates, wires, and timing circuits permanently etched into the hardware. Changing the sequence, or adding a new variant, requires a new chip.

**After microprogramming (Wilkes's control store):**

The same ADD is described as two microinstructions in ROM:

```
FETCH CYCLE (shared by all instructions):
  μ0: MAR ← PC
  μ1: MDR ← MEM[MAR]
  μ2: IR  ← MDR
  μ3: PC  ← PC + 1 ;  dispatch to slot (opcode × STRIDE)

ADD EXECUTE (microaddresses 16–17 in this simulator):
  μ16: MDR ← MEM[MAR]       ; MAR already holds addr from DISPATCH
  μ17: A   ← A + MDR ; →FETCH
```

The data path hardware is generic — an ALU that can add, registers with muxes, a memory bus. The *specific behaviour* of ADD lives only in the ROM entries. To add a new instruction `ADD_TWICE addr` that adds memory to A twice, you write two new ROM entries. No hardware change.

### 4. The First Full Implementation — EDSAC 2 (1958)

Wilkes designed EDSAC 2 from scratch as the first computer *fully* built around microprogramming. Its control store was 768 words of 20-bit ferrite-core ROM. The data path was *bit-sliced*: 16 identical plug-in units, one per bit position, so hardware faults could be isolated and replaced at the board level. Every instruction in EDSAC 2's ISA was purely microcode; nothing was hardwired.

EDSAC 2 ran from 1958 to 1965 and proved the concept at scale.

### 5. IBM System/360 and the Industry Adoption (1964)

IBM's System/360 is the canonical example of microprogramming's commercial value. The 360 family ran a single ISA across eight models spanning a 50:1 performance range and 100:1 cost range. That compatibility was only possible because of microprogramming: each model's hardware ran a tailored microprogram that implemented the common ISA on different underlying data paths.

The System/360/30 (the cheapest model) had an 8-bit data bus and did 32-bit operations in four memory cycles, each cycle directed by a microinstruction. The System/360/75 (the fastest) had a 64-bit bus and executed most instructions in hardwired logic. The same binary programs ran on both. Customers could start cheap and migrate up.

Gene Amdahl, the System/360's chief architect, later said the decision to use microprogramming throughout the line was one of the most consequential architectural choices in computing history.

### 6. Lasting Impact

**CISC:** Microprogramming made complex instruction sets practical. When an instruction is just ROM entries, complexity is "free" — you can add floating-point operations, string instructions, decimal arithmetic without touching the logic. The Intel 8086 (1978) and all its descendants have microcode engines underneath the x86 ISA.

**Microcode updates:** Modern CPUs ship microcode that can be patched after manufacture. Intel's response to Spectre and Meltdown (2018) was partly a microcode update — changing the behaviour of speculative execution by rewriting control store entries, not replacing chips.

**RISC as reaction:** The RISC movement (IBM 801, 1975; Stanford MIPS, 1981; Berkeley RISC, 1982) explicitly rejected microprogramming's complexity in favour of a simple ISA that hardwires to silicon directly. But even RISC CPUs use microsequencers for multi-cycle operations and exception handling. You never fully escape the Wilkes layer.

**Emulation:** The idea of "an ISA is just a microprogram" generalised naturally to software emulation. Virtual machines, binary translation layers (Apple Rosetta, WSL), and JIT compilers are all variations on Wilkes's insight: the machine your software targets need not be the machine your silicon implements.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [The Best Way to Design an Automatic Calculating Machine](https://doi.org/10.1145/1461541.1461548) | Manchester University Computer Inaugural Conference | 1951 |
| [Micro-programming and the Design of the Control Circuits in an Electronic Digital Computer](https://doi.org/10.1017/S0305004100028322) *(with J. B. Stringer)* | Mathematical Proceedings of the Cambridge Philosophical Society | 1953 |
| [Preparation of Programs for Electronic Digital Computers](https://dl.acm.org/doi/book/10.5555/1102780) *(with Wheeler & Gill)* | Addison-Wesley | 1951 |
| [The Growth of Interest in Microprogramming](https://dl.acm.org/doi/10.1145/356540.356543) | ACM Computing Surveys | 1969 |

---

*Previous: [Week 01 — Alan Jay Perlis (1966)](../01-alan-perlis-1966/)*

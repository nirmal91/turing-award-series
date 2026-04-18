# Week 01 — Alan Jay Perlis (1966)

**ACM Turing Award citation:** *"For his influence in the area of advanced programming techniques and compiler construction."*

---

## My Take

*Written by me — no AI assist.*

---

## The Code

[`compiler.py`](./compiler.py) — a mini expression compiler that mirrors IT's pipeline:

```
source text → tokens → AST → stack bytecode → execution
```

Supports arithmetic expressions with correct operator precedence, variables, and assignment.

```bash
# Interactive REPL
python compiler.py

# Run the test suite
python compiler.py --test

# See the bytecode for each expression
python compiler.py --verbose
```

Example session:
```
> x = 3
> y = x * (2 + 4)
> y
18
> (100 - 64) / 4
9
```

---

## ELI5 — Explain Like I'm 5

Computers speak a secret language made of numbers. Before Alan Perlis, if you wanted a computer to do something, you had to learn that secret language yourself and write out every single number by hand.

Perlis built a translator. Now you could write normal math like `2 + 3` and the translator would figure out the secret number language for you. Nobody had done that before.

---

## ELI10 — Explain Like I'm 10

Imagine you want to tell a robot to do your math homework. You could write it in robot-speak — something like `65 8003 8001 0000  10 8001 8003 0000` — but that's exhausting and nobody can read it.

Alan Perlis had the same problem in 1955. Computers back then understood only their own weird number codes. If you wanted to say `x = (a + b) * c`, you had to hand-translate every single symbol into dozens of numeric instructions, in exactly the right order, accounting for where the computer's spinning drum happened to be at that moment. One mistake and the whole thing was garbage.

Perlis's big idea: **write a program that does the translating for you.** You type normal-looking math, the program (called a *compiler*) reads it, understands it, and spits out the robot-speak automatically.

That program was called IT — the Internal Translator. It was the first compiler that actually worked well. Before IT, most people thought you couldn't do this automatically — that human cleverness was required. Perlis proved them wrong.

Then he did something even bigger. He got mathematicians and computer scientists from America and Europe in a room in Zurich in 1958 and said: let's agree on *one* language that runs everywhere, not hundreds of different robot-speak dialects. That language became ALGOL 60. It introduced ideas — like scoping (variables staying inside their block), recursion (functions that call themselves), and clear logical structure — that every language since has borrowed. Python, Java, C, Go, Rust — they all descend from ALGOL 60.

Finally, Perlis became president of the ACM (the main computer science professional society) and wrote the first-ever university CS curriculum. Before that, "computer science" wasn't really a subject — it was just math or electrical engineering with computers bolted on. Perlis made it its own thing.

He also wrote 130 one-liner jokes about programming called *Epigrams on Programming* (1982) that programmers still quote today. Like: *"A language that doesn't affect the way you think about programming is not worth knowing."*

---

## CS Graduate Level — Why Perlis Actually Mattered

### 1. IT: The First Practical Compiler (1955–56)

Before IT, the state of the art was hand-assembly or semi-automated symbol substitution. The prevailing belief — articulated by luminaries including von Neumann — was that a compiler would produce code so much slower than hand-coded assembly that it would be impractical. Perlis, working with Joseph Smith and H. R. Van Zoeren at Purdue and then Carnegie Tech, built IT for the IBM 650 and refuted that belief directly.

IT was remarkable for two reasons beyond its existence:

**Machine independence by design.** IT targeted the IBM 650, but Perlis designed it with portability in mind. The source language described computation abstractly; the code-generation phase was kept separate. This anticipates the front-end/back-end split that every compiler today takes for granted.

**Algebraic notation, direct.** IT accepted expressions like `A + B * C` with proper operator precedence — not pseudo-assembly, actual infix algebra. Knuth later called it "the first really working compiler," and noted that its output quality was competitive with careful hand-coding for most programs.

The IBM 650 it targeted was a drum-memory decimal computer where instruction sequencing was non-trivial: each instruction encoded not just an opcode and data address but a *next instruction address*, because instructions had to be placed on the drum at positions that minimized rotational latency. Writing correct 650 machine code by hand was error-prone in a uniquely mechanical way; automating it was a genuine engineering achievement.

Every IBM 650 instruction was exactly 10 digits — three fields:

| Field | Digits | Meaning |
|-------|--------|---------|
| `OP` | 2 | Operation code — what to do |
| `DDDD` | 4 | Data address — where in memory to find the operand |
| `NNNN` | 4 | Next instruction address — where on the drum the next instruction lives |

To compute `x = (a + b) * c`, assuming `a` at 0100, `b` at 0101, `c` at 0102, `x` at 0103:

```
65  0100  0011    OP=65 (RAL: clear accumulator, load a)    next instr at drum position 0011
15  0101  0012    OP=15 (AL:  add b to accumulator)         next instr at drum position 0012
19  0102  0013    OP=19 (MPY: multiply by c)                next instr at drum position 0013
24  0103  0014    OP=24 (STD: store result into x)          next instr at drum position 0014
```

What each opcode actually means:

**RAL — Reset Add Lower.** Three words describing one action. *Reset* means clear the accumulator completely (wipe whatever was in it from a previous calculation). *Add* means load a value from memory into it. *Lower* means put it in the lower half — the IBM 650 had a 20-digit accumulator split into an upper 10 digits and a lower 10 digits, and most arithmetic happened in the lower half. So `65 0100` means: start fresh, load the value at address 0100 into the lower accumulator. This was the standard way to begin any calculation.

**AL — Add Lower.** Take whatever is at the given memory address and add it to what's already sitting in the lower accumulator. No reset — just add on top.

**MPY — Multiply.** Multiply the value in the accumulator by the value at the given address. The result filled both the upper and lower halves of the accumulator because multiplication of two 10-digit numbers can produce a 20-digit result.

**STD — Store Distributor.** Copy the result out of the accumulator and write it to the given memory address. This is how you saved your answer.

The `NNNN` field is what made this brutal. The drum spun at 12,500 RPM. If your next instruction wasn't physically sitting at the right spot on the drum when the read head arrived, the computer waited a full rotation — about 5 milliseconds, enormous at the time. So programmers didn't just write logic, they solved a packing puzzle: place each instruction at the drum position that would arrive just in time after the previous one finished. Every program was also a timing optimization problem. Perlis's compiler handled that automatically.

### 2. ALGOL 58 and ALGOL 60: The Language That Taught Every Language

In 1958 Perlis chaired a joint ACM/GAMM meeting in Zurich that produced the International Algebraic Language (later renamed ALGOL 58). He then co-authored both the 1958 preliminary report and the full ALGOL 60 Revised Report (with Backus, McCarthy, Naur, and nine others).

ALGOL 60's contributions to language design are so foundational they are now invisible:

- **Block structure and lexical scoping.** `begin`/`end` blocks define scope; a variable declared inside a block is invisible outside it. Every language with curly-brace blocks inherited this.
- **Recursive procedures.** ALGOL 60 was the first widely-used language to formally specify recursion. Before this, most languages either forbade it or supported it accidentally.
- **Call by value and call by name.** ALGOL 60 distinguished these explicitly; the distinction between value and reference semantics traces here.
- **Formal syntax specification via BNF.** Peter Naur used Backus–Naur Form in the ALGOL 60 report; this was the first time a major language was defined by a formal grammar rather than prose description. Every language spec since does this.
- **Type declarations.** Variables had declared types — integer, real, Boolean, array — enforced at compile time.

The lineage is direct: ALGOL → CPL → BCPL → B → C → C++ → Java → C#, and ALGOL → Pascal → Modula → Ada in a parallel branch.

Crucially, ALGOL 60 was designed by a committee spanning multiple countries and machine architectures. Perlis had to forge consensus across genuinely different computing traditions. The result was a language that defined "what a programming language should look like" for a generation.

### 3. ACM Presidency and the Birth of CS as a Discipline

As ACM president (1962–64) Perlis chaired the effort to define a standard undergraduate CS curriculum — the first of its kind. Before this, "computer science" lived inside mathematics or electrical engineering departments with no agreed core. Perlis's curriculum established CS as a field with its own epistemology: algorithms, data structures, formal languages, compilers, operating systems.

His Turing Award lecture, "The Synthesis of Algorithmic Systems" (JACM 1967), argued that programming is a mathematical activity — that programs are formal objects subject to proof and analysis, not merely engineering artifacts. This framing underlies both formal verification and type theory as practiced today.

### 4. Epigrams on Programming (1982)

Published in SIGPLAN Notices, these 130 aphorisms are still cited in language design papers. A few that aged well:

> *"Syntactic sugar causes cancer of the semicolon."*

> *"It is easier to write an incorrect program than to understand a correct one."*

> *"Every program is a part of some other program and rarely fits."*

> *"A language that doesn't affect the way you think about programming is not worth knowing."*

They read less like jokes and more like distilled experience from someone who had been building systems since before most of computing's vocabulary existed.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [A Mathematical Language Compiler](https://dl.acm.org/doi/10.1145/800258.808917) | ACM Annual Conference | 1956 |
| [Preliminary Report — International Algebraic Language](https://dl.acm.org/doi/10.1145/367424.367501) | CACM 1(8) | 1958 |
| [Report on the Algorithmic Language ALGOL 60](https://dl.acm.org/doi/10.1145/367236.367261) | CACM 3(5) | 1960 |
| [Revised Report on the Algorithmic Language ALGOL 60](https://dl.acm.org/doi/10.1145/366552.366553) | CACM 6(1) | 1963 |
| [The Synthesis of Algorithmic Systems](https://dl.acm.org/doi/10.1145/321371.321372) *(Turing Award lecture)* | JACM 14(1) | 1967 |
| [Epigrams on Programming](https://dl.acm.org/doi/10.1145/947955.1083808) | SIGPLAN Notices 17(9) | 1982 |

---

*Next: [Week 02 — Maurice Wilkes (1967)](../02-maurice-wilkes-1967/)*

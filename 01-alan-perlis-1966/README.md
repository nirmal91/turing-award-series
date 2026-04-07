# Week 01 — Alan Jay Perlis (1966)

**ACM Turing Award citation:** *"for his influence in the area of advanced programming techniques and compiler construction."*

---

## ELI10 — Explain like I'm 10

Imagine you want to bake a cake, but the only instructions you have are written in a secret code that only the oven understands — something like:

```
10 00001 00002
20 00003 00004
```

That's what early computers were like. Every program had to be written in the machine's own strange number language. It was exhausting and error-prone. Only a handful of specialists in the world could do it.

Alan Perlis looked at this and said: *"What if the computer could read normal math?"* What if you could write `x = (a + b) * c` and the computer would figure out the secret number code on its own?

That's a **compiler** — a program that reads human-friendly code and translates it into machine instructions automatically. Perlis built one of the very first working compilers, called **IT** (Internal Translator), in 1955–56. Donald Knuth (a later Turing Award winner himself) called it the first *successful* compiler.

But Perlis didn't stop there. He got scientists from the US, Europe, and the Soviet Union to agree on a *shared* programming language — **ALGOL 60** — so that code written in Germany could be understood in America. ALGOL introduced ideas like:

- **Block structure** (`begin ... end`) — code organized in chunks
- **Recursion** — a function can call itself to solve smaller pieces of the same problem
- **Typed variables** — you say upfront whether something is a number or text

Every programming language you've ever heard of — C, Python, Java, JavaScript — is a direct descendant of ALGOL 60. Perlis planted the family tree.

Finally, he convinced universities that *Computer Science* was a real discipline, not just a side hobby for mathematicians. He wrote the first recommended CS undergraduate curriculum. Before Perlis, there were no CS degrees. After Perlis, there were.

---

## CS Graduate Level — Why Perlis mattered

### 1. The IT Compiler (1955–56)

Before IT, the dominant view was that automatic coding systems were a curiosity — useful for simple problems, but no substitute for hand-tuned assembly. Perlis and his team at Purdue/Carnegie disproved this empirically.

IT compiled a subset of algebraic notation to **IBM 650 machine code**. The IBM 650 was a drum-memory machine where the physical rotation of the drum made instruction scheduling a manual optimization problem: each instruction encoded the address of the *next* instruction, so programmers had to lay out code to minimize rotational latency. IT automated this translation entirely.

Two architectural decisions made IT historically significant:

- **Machine independence as a design goal.** IT was specified to be retargetable; the algebraic input language was defined independently of the 650's instruction set. This prefigured the front-end/back-end split that defines every production compiler today.
- **Practical success at scale.** Earlier "automatic coding" systems (e.g., Grace Hopper's A-0) were mostly symbolic assemblers. IT performed genuine expression parsing and code generation, demonstrating that compilation was tractable for real scientific programs.

### 2. ALGOL 58 and ALGOL 60

The 1958 Zurich meeting (GAMM/ACM joint committee) produced **IAL** — the International Algebraic Language, later renamed ALGOL 58. Perlis co-chaired and co-authored the preliminary report with Klaus Samelson.

ALGOL 60, finalized in Paris in 1960 and published in *Numerische Mathematik* in 1960 (with the canonical "Revised Report" in *CACM* in 1963), introduced several concepts that became load-bearing pillars of programming language theory:

| Feature | Significance |
|---|---|
| **Block structure** | Lexically scoped name bindings; `begin`/`end` delimit variable lifetimes. First clean separation of static scope from dynamic execution. |
| **Recursive procedures** | Enabled by stack-allocated activation records. Previously, most languages (including FORTRAN) allocated fixed memory for each subroutine, making recursion impossible. |
| **Call-by-name** | ALGOL's default parameter-passing mode; equivalent to substituting the argument expression textually, evaluated each time it is referenced (Jensen's device). Inspired lazy evaluation in functional languages. |
| **BNF notation** | Peter Naur used Backus-Naur Form to formally specify ALGOL 60's syntax — the first use of a formal grammar to define a programming language. Every language spec since uses it. |
| **Type system** | Variables declared with explicit types (`integer`, `real`, `Boolean`). First mainstream language with a static type discipline. |

The ALGOL lineage runs directly to Pascal (Wirth, 1970), which led to Modula/Oberon, and via C (Ritchie, 1972 — which borrowed block structure wholesale) to C++, Java, C#, Go, Rust, and Swift. ALGOL 60 is the ancestor of virtually every imperative language in production today.

### 3. CS as an Academic Discipline

As ACM president (1962–64), Perlis authored the first recommended undergraduate curriculum for Computer Science. This was not merely administrative: it was an intellectual argument that CS had a coherent body of knowledge distinct from mathematics, electrical engineering, and applied statistics — that algorithms and computation were objects of study in their own right.

His 1967 Turing Award lecture, "The Synthesis of Algorithmic Systems," articulated a philosophy of programming as a formal discipline concerned with the *structure* of computation, not merely its practice. His 1982 "Epigrams on Programming" (SIGPLAN Notices) remains widely quoted — aphorisms like *"A programming language is low level when its programs require attention to the irrelevant"* and *"Syntactic sugar causes cancer of the semicolon"* show a mind that thought about language design at the level of epistemology, not just engineering.

### The Code in This Folder

`compiler.py` implements the same pipeline Perlis's IT used:

```
source text → tokenizer → recursive-descent parser → AST
    → stack-based bytecode compiler → virtual machine execution
```

It supports integer/float literals, variables, the four arithmetic operators, exponentiation (`^`, right-associative), unary negation, parentheses, and assignment. Variables persist across statements, mirroring how IT maintained a symbol table across the translation of a full program.

Run it:

```bash
python compiler.py
```

The interactive mode lets you type expressions; variables carry over between lines, just as they would in a compiled program's data segment.

---

## Key Papers

| Paper | Venue | Year |
|---|---|---|
| "A Mathematical Language Compiler" | ACM Annual Conference | 1956 |
| "Preliminary Report — International Algebraic Language" (with Samelson) | *CACM* | 1958 |
| "Report on the Algorithmic Language ALGOL 60" (with Backus, Naur et al.) | *Numerische Mathematik* | 1960 |
| "Revised Report on the Algorithmic Language ALGOL 60" (with Backus, McCarthy, Naur et al.) | *CACM* | 1963 |
| "The Synthesis of Algorithmic Systems" (Turing Award lecture) | *JACM* | 1967 |
| "Epigrams on Programming" | *SIGPLAN Notices* | 1982 |

---

## Running ALGOL 60 Today

ALGOL 60 is still runnable via **GNU MARST** (`marst` transpiles `.alg` source to C, then compile with `gcc`). Online sandboxes exist at tutorialspoint. A minimal ALGOL 60 program looks like:

```algol
begin
  integer i;
  real sum;
  sum := 0;
  for i := 1 step 1 until 10 do
    sum := sum + i;
  print(sum)
end
```

---

*Next: [Week 02 — Maurice Wilkes (1967)](../02-maurice-wilkes-1967/README.md)*

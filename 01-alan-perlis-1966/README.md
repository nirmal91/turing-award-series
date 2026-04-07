# 01 — Alan Jay Perlis (1966)

**Award citation:** *"For his influence in the area of advanced programming techniques and compiler construction."*

---

## ELI10 — Explain it to a 10-year-old

Imagine you want to tell a robot to do math homework. But the robot only understands a secret code with numbers like `65 8003 8001` — nothing like normal math. Writing that secret code by hand for every single problem is exhausting and almost impossible to get right.

Alan Perlis built a *translator* — a program that reads normal math (like `x = a * b + c`) and automatically converts it into the secret robot code. Before him, every programmer had to write the robot code by hand. After him, you could just write something that looked like math and the computer figured out the rest.

But that was just the start. He also helped *invent the rules for a language called ALGOL 60* — a language so well-designed that almost every programming language you've ever heard of (C, Java, Python, JavaScript) borrowed its core ideas: things like putting code in blocks with `{` and `}`, functions that can call themselves, and variables that "belong" to the part of the program where they were created.

And on top of all that, he *invented Computer Science as a school subject*. Before Perlis, there were no CS degrees. He wrote the first recommended curriculum and convinced universities that programming deserved its own department — just like math or physics.

---

## CS Graduate Level — Why Perlis Mattered

### 1. The IT Compiler (1955–56)

Before Perlis, the IBM 650 was programmed by hand in decimal machine code. Every instruction was a 10-digit number: two digits for the opcode, four for the data address, four for the *next* instruction address — the last field existed because drum memory was physically rotating and you had to time your reads to the right drum position or pay full-rotation penalties.

Perlis built the **IT (Internal Translator)** compiler at Purdue and then Carnegie (published 1956). Its innovations:

- **Machine-independent design from day one.** IT was not a Purdue 650 tool; it was designed to run on any 650 — an idea radical enough that Knuth later called IT "the first successful compiler."
- **Algebraic notation → machine code.** IT tokenized infix expressions, applied an operator-precedence parser (before such things had formal names), and emitted correct 650 code — automatically handling the next-instruction address chaining.
- **No hand-scheduling.** The compiler optimized drum access timing, something human programmers agonized over.

### 2. ALGOL 58 / ALGOL 60 and the Block-Structure Revolution

In 1958, Perlis led the joint ACM/GAMM meeting in Zurich that produced **ALGOL 58** — the first attempt at a universal, machine-independent algorithmic language. ALGOL 60 followed (Paris, 1960), co-authored with Backus, McCarthy, Naur, and nine others.

ALGOL 60 gave us things we now take completely for granted:

| ALGOL 60 innovation | What it enabled |
|---|---|
| **Block structure** (`begin`/`end`) | Scoped variables; stack-based activation records |
| **Lexical (static) scoping** | Variables resolve at definition site, not call site |
| **Recursion** | First spec to explicitly allow and define it |
| **Call-by-value / call-by-name** | Formal parameter passing modes |
| **BNF grammar in the report** | First language defined by a formal grammar — Naur's BNF became the standard notation for PL theory |

The lineage is direct: ALGOL → CPL → BCPL → B → **C** → C++ → Java → every curly-brace language. Python, Ruby, and Rust inherit the same scoping model. ALGOL 60 is the grammar of modern programming.

### 3. Establishing Computer Science as a Discipline

As ACM president (1962–64), Perlis chaired the committee that published the first recommended undergraduate CS curriculum. Before this work, "computer science" was taught ad hoc inside math or EE departments. The curriculum established CS as an independent discipline with its own theory and pedagogy — the framework every university CS department today descends from.

### 4. Epigrams on Programming (1982)

His SIGPLAN essay contains 130 one-liners, still quoted in every PL course:

> *"A language that doesn't affect the way you think about programming is not worth knowing."*

> *"Syntactic sugar causes cancer of the semicolons."*

> *"Every program is a part of some other program and rarely fits neatly."*

---

## The Code: `compiler.py`

A four-stage mini compiler that mirrors what IT did:

```
source text
    │
    ▼  tokenize()       regex → token list
    │
    ▼  Parser.parse()   recursive-descent → AST
    │
    ▼  compile_ast()    AST → stack-based bytecode
    │
    ▼  execute()        virtual stack machine → result
```

**Run it:**

```bash
python compiler.py "2 + 3 * 4"          # → 14
python compiler.py "(2 + 3) * 4"        # → 20
python compiler.py "2 ** 10"            # → 1024
python compiler.py --test               # run all 14 unit tests
python compiler.py                      # interactive REPL
```

**Verbose mode** (prefix with `!` in the REPL, or pass `-v`) prints tokens, AST, and bytecode — useful for seeing the compilation pipeline in action:

```
> !2 + 3 * 4
  Tokens   : [('NUMBER', 2.0), ('OP', '+'), ('NUMBER', 3.0), ('OP', '*'), ('NUMBER', 4.0)]
  AST:
  BINOP(+)
    NUMBER(2.0)
    BINOP(*)
      NUMBER(3.0)
      NUMBER(4.0)
  Bytecode:
      0  PUSH   2.0
      1  PUSH   3.0
      2  PUSH   4.0
      3  MUL
      4  ADD
14
```

---

## Key Papers

| Paper | Venue | Year |
|---|---|---|
| "A Mathematical Language Compiler" | ACM Annual Conference | 1956 |
| "Preliminary Report — International Algebraic Language" (with Samelson) | CACM | 1958 |
| "Report on the Algorithmic Language ALGOL" | Numerische Mathematik | 1959 |
| "Revised Report on the Algorithmic Language ALGOL 60" (Backus, McCarthy, Naur et al.) | CACM | 1963 |
| "The Synthesis of Algorithmic Systems" (Turing Award lecture) | JACM | 1967 |
| "Epigrams on Programming" | SIGPLAN Notices | 1982 |

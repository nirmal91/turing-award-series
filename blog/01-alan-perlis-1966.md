# The Man Who Made Programming Human: Alan Jay Perlis (1966)

*Week 01 of the Turing Award Series*

---

There's something I genuinely miss from my CS undergrad days.

Not the exams, not the all-nighters. The thing I miss is sitting with a paper — a real one, written by someone who figured something out for the first time — and working through it until it clicked. Then building something from it. That feeling of *oh, that's how it actually works* doesn't show up in tutorials or documentation. It only comes from going to the source.

I'm starting this series to get that back. Every Turing Award winner, starting from 1966. One per week. Working code, real writeups, back to first principles. If you were that person in undergrad who stayed late in the lab not because you had to but because you wanted to — this is for you.

Week one: **Alan Jay Perlis. 1966. The first Turing Award ever given.**

---

## The One-Sentence Version

Before Perlis, you programmed computers by hand-writing numeric machine codes. Perlis built the first program that could read algebra and translate it into machine code automatically — then convinced the entire world to agree on one programming language.

---

## What This Would Look Like at Your Company

Picture your best senior engineer. They're fast, meticulous, never make mistakes. Now imagine every time a product manager wants a new feature, that engineer has to translate the spec into assembly — not write Python, but actual bytes for the CPU, by hand, in the right order, accounting for memory timing.

That was programming in 1955. Every computation had to be hand-translated into the machine's native number codes. One person. One program. Weeks of work for something trivial. No abstraction layer between human thought and machine behavior.

Perlis's insight: **write a program that does the translating.** You describe what you want in algebra — `result = (sales * margin) - costs` — and the compiler figures out the machine instructions. The engineer writes the spec. The machine handles the rest.

This is why your company's engineers write Python, not x86 assembly. This is why every developer tool you use exists. Perlis is the reason a 22-year-old with a MacBook can build something that runs on a billion devices.

---

## What the World Looked Like Before

The machine Perlis worked on was the IBM 650. It had no RAM, no screen, no keyboard in any modern sense. Memory was a spinning metal drum, 12,500 RPM, and you had to physically account for where data was on the drum as it rotated.

Every instruction was a 10-digit decimal number — packed like a phone number:

```
6501000201
│││    │
│││    └── next instruction at drum slot 0201
│└┘
│└── data lives at drum slot 0100
└─── opcode 65 = "reset accumulator and load"
```

To compute `result = 3 + 5`, a programmer hand-wrote this:

```
Drum slot 0100:  0000000003   ← store the number 3 here
Drum slot 0101:  0000000005   ← store the number 5 here
Drum slot 0102:  0000000000   ← result goes here

Drum slot 0200:  6501000201   ← load 3 into accumulator, go to 0201
Drum slot 0201:  1001010202   ← add 5, go to 0202
Drum slot 0202:  2001020203   ← store result, go to 0203
Drum slot 0203:  0100000000   ← halt
```

And the numbers `0201`, `0202`, `0203` in the "go to" positions? Those weren't arbitrary — you calculated them based on drum rotation timing. Put an instruction in the wrong drum slot and it would take a full rotation (4.8 milliseconds) to execute instead of a quarter-rotation (0.24ms). A 20-instruction program could run 20× slower from bad scheduling alone.

**Von Neumann himself said you couldn't automate this.** The output would be too slow to be practical. Human judgment was irreplaceable.

---

## What Perlis Did (The Technical Version)

In 1955, working at Purdue and then Carnegie Tech with Joseph Smith and H. R. Van Zoeren, Perlis built **IT — the Internal Translator**. A program that:

1. Read algebraic expressions: `X = (A + B) * C`
2. Tokenized them into symbols
3. Parsed them into a tree respecting operator precedence
4. Compiled the tree into IBM 650 machine code
5. *Optimized the drum scheduling automatically*

Donald Knuth later called it "the first really working compiler." The output quality was competitive with careful hand-coding. Von Neumann was wrong.

But IT was just the opening act.

In 1958, Perlis chaired a joint meeting of American and European computer scientists in Zurich. The goal: design *one* programming language that would work everywhere, instead of every machine having its own dialect. That language became **ALGOL 60**, and it introduced ideas so fundamental we no longer notice them:

- **Block structure** — `{ }` encloses a scope. Variables inside are invisible outside. Before ALGOL, variables were global by default. Every language you use today has this.
- **Recursion** — functions that call themselves. ALGOL 60 was the first widely-used language to formally support it. Before this, many languages either forbade it or broke on it.
- **Formal grammar (BNF)** — the ALGOL 60 spec was the first to define a language using a formal grammar instead of prose. Every language spec since does this. Your IDE's syntax highlighting traces here.
- **Call by value vs. call by reference** — explicitly distinguished for the first time. The mental model you use when reasoning about function parameters comes from ALGOL 60.

The lineage is direct:
```
ALGOL 60 → CPL → BCPL → B → C → C++ → Java → C#
ALGOL 60 → Pascal → Modula → Ada
ALGOL 60 → (influence) → Python, Go, Rust, everything
```

Then, as ACM president (1962–64), Perlis wrote the first university CS curriculum. Before that, "computer science" lived inside math or electrical engineering departments. Perlis made it its own field with its own epistemology: algorithms, compilers, formal languages, operating systems.

He also wrote *Epigrams on Programming* in 1982 — 130 one-liners, still quoted in papers today. My favorite:

> *"A language that doesn't affect the way you think about programming is not worth knowing."*

---

## The Code: Before and After

The full pipeline — tokenizer, recursive-descent parser, AST compiler, stack VM — is in [`compiler.py`](../01-alan-perlis-1966/compiler.py). It mirrors exactly what IT did.

**Before Perlis** — what you'd write by hand for `y = x * (2 + 4)`:

```
# Store constants
slot 0100: 0000000002   ← the number 2
slot 0101: 0000000004   ← the number 4
slot 0102: 0000000000   ← intermediate result (2+4)
slot 0103: 0000000000   ← final result y

# Load x (assume it's at slot 0050)
0200: 6500500201   ← RAU: reset, load x, → 0201
# Add 2
0201: 1001000202   ← AU: add 2, → 0202
# Add 4
0202: 1001010203   ← AU: add 4, → 0203
# Store (2+4) to slot 0102
0203: 2001020204   ← STL: store sum, → 0204
# Reload x
0204: 6500500205   ← RAU: reset, load x, → 0205
# Multiply by contents of 0102 (no MUL opcode — requires loop!)
# ... 8+ more instructions for the multiply loop ...
# Store result to y (slot 0103)
# HLT
```

**After Perlis** — what IT let you write:

```
y = x * (2 + 4)
```

**What our compiler.py generates internally:**

```
> y = x * (2 + 4)
  bytecode: PUSH_VAR 'x'
            PUSH_CONST 2.0
            PUSH_CONST 4.0
            ADD
            MUL
            STORE 'y'
> y
  18
```

Run it yourself:

```bash
git clone https://github.com/nirmal91/turing-award-series
cd turing-award-series/01-alan-perlis-1966
python compiler.py           # interactive REPL
python compiler.py --test    # 13 tests
python compiler.py --verbose # see the bytecode
```

---

## Why It Still Matters Monday Morning

Every time you:
- Write `if (x > 0) { ... }` — that's Perlis's block structure
- Call a function recursively — Perlis proved it was practical
- Get a syntax error in your IDE before you run code — that's BNF-based parsing, from ALGOL 60
- Use any compiled language — Perlis proved compilers were worth building
- Study CS at a university — Perlis invented that curriculum

The entire stack between your brain and the transistors was made possible, in large part, by one person who decided in 1955 that humans shouldn't have to think in machine codes.

---

## The Papers

If you want to go to the source:

| Paper | What it is |
|---|---|
| [A Mathematical Language Compiler (1956)](https://dl.acm.org/doi/10.1145/800258.808917) | The IT compiler paper |
| [Preliminary Report — International Algebraic Language (1958)](https://dl.acm.org/doi/10.1145/367424.367501) | ALGOL 58 |
| [Revised Report on ALGOL 60 (1963)](https://dl.acm.org/doi/10.1145/366552.366553) | The full ALGOL 60 spec |
| [The Synthesis of Algorithmic Systems (1967)](https://dl.acm.org/doi/10.1145/321371.321372) | His Turing Award lecture |
| [Epigrams on Programming (1982)](https://dl.acm.org/doi/10.1145/947955.1083808) | The 130 aphorisms |

The Turing Award lecture is worth reading in full. It's short, dense, and he's writing about programming as a mathematical activity decades before that became mainstream language theory.

---

*Next week: Maurice Wilkes (1967) — microprogramming and the EDSAC. The person who figured out how to make CPUs programmable at the hardware level.*

*[GitHub](https://github.com/nirmal91/turing-award-series) · [Series index](../README.md)*

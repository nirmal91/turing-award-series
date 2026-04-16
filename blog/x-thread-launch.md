# X Thread — Project Launch + Week 01

*Copy-paste ready. Each block = one tweet.*

---

**[1/8] — Hook**

One thing I genuinely miss from CS undergrad: sitting with a paper, understanding it deeply, then building something from it.

Starting a project to get that back.

Deep-diving every Turing Award winner, one per week, from 1966. Code + writeups, back to first principles. 🧵

---

**[2/8] — What the project is**

The Turing Award is CS's Nobel Prize. 70+ winners since 1966.

Each week:
→ pick a winner
→ understand why they won
→ implement their core idea in code
→ write it up two ways: explain it to a 10-year-old AND a CS grad

Week 1: Alan Jay Perlis (1966)

---

**[3/8] — The before picture**

Before Perlis, programming meant writing things like this.

To compute result = 3 + 5:

```
slot 0200:  6501000201
slot 0201:  1001010202
slot 0202:  2001020203
slot 0203:  0100000000
```

Four instructions. Each a 10-digit decimal code. Hand-calculated drum rotation timing baked into every line.

This was the state of the art in 1955.

---

**[4/8] — The insight**

Perlis's idea: write a program that does the translating for you.

You write:   result = 3 + 5
IT outputs:  the machine code above, drum-optimized

This seems obvious now. In 1955, von Neumann said it was impossible — that no compiler could match hand-written assembly.

Perlis proved him wrong.

---

**[5/8] — ALGOL 60**

Then he did something bigger.

He flew US + European CS people to Zurich (1958) and designed one language that would run everywhere.

ALGOL 60 gave every language since:
→ block scope  { variables staying inside blocks }
→ recursion  (functions that call themselves)
→ formal grammar specs (BNF)

Python. Java. C. Go. Rust. All of it traces here.

---

**[6/8] — The modern connection**

Every time you:
- write { } around a block of code → Perlis
- call a function recursively → Perlis
- get a syntax error before you run → Perlis (BNF parsing)
- study CS at university → Perlis wrote that curriculum

The entire abstraction stack between your brain and the transistors started here.

---

**[7/8] — The code**

Implemented IT's full pipeline in Python: tokenizer → parser → AST → bytecode compiler → stack VM

```
> x = 3
> y = x * (2 + 4)
> y
18
```

13 tests passing. Run it yourself:
github.com/nirmal91/turing-award-series

---

**[8/8] — CTA**

One winner per week, all the way through.

Next: Maurice Wilkes (1967) — microprogramming and EDSAC

If you were that person who stayed late in the CS lab not because you had to but because you wanted to — follow along.

Full writeup + code → [link to blog post]
Repo → github.com/nirmal91/turing-award-series


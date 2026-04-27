# Turing Award Series

## Why

I miss learning for the sake of learning and going into rabbit holes. Reading research papers has always been aspirational for me but hard to be consistent with. They were complex and you had to spend hours getting enough context around them to actually understand what was being said.

What's different now is that the barrier to actually grokking hard concepts is so much lower. You can take a dense 1960s systems paper, work through it with an LLM, and come out the other side genuinely understanding it. You can customize the learning based on your skills, your experience, your knowledge. That wasn't possible before.

---

## Format

Each entry has code, an ELI10 explanation, and a CS grad-level writeup. A lot of this is automated — the code, the structure, the technical writeups. That's intentional.

But every entry has one section written by me. No AI assist on those.

Writing is how I think. There's writing I'm happy to outsource — status updates, instructions, documentation. The writing that validates my understanding has to come from me.

Each week:
- **My take** — written by me, validated for accuracy after
- **Code** — a working implementation of the core idea, with instructions to run it
- **ELI5** — the contribution explained to a curious five-year-old
- **ELI10** — the contribution explained to a curious ten-year-old
- **CS grad** — the technical depth: what was new, what it replaced, why it mattered, what descended from it
- **Papers and citations** — links to the primary sources

---

## Index

| # | Winner | Year | Core Contribution | Code | Writeup |
|---|--------|------|-------------------|------|---------|
| 01 | Alan Jay Perlis | 1966 | First working compiler (IT), co-designed ALGOL 60, founded CS as a discipline | [compiler.py](./01-alan-perlis-1966/compiler.py) | [README](./01-alan-perlis-1966/README.md) |
| 02 | Maurice Wilkes | 1967 | Invented microprogramming — machine instructions implemented as ROM microcode, not hardwired logic | [implementation.py](./02-maurice-wilkes-1967/implementation.py) | [README](./02-maurice-wilkes-1967/README.md) |

---

## Running the code

Each entry and section has its own implementation. Each folder's README has the specific instructions. In general:

```bash
cd 01-alan-perlis-1966
python compiler.py          # interactive REPL
python compiler.py --test   # run test suite
python compiler.py --verbose # show bytecode
```

## License

MIT — see [LICENSE](./LICENSE).

# Turing Award Series

## Why

I miss learning for the sake of learning and going into rabbit holes. Reading research papers has always been aspirational for me but hard to be consistent with. They were complex and you had to spend hours getting enough context around them to actually understand what was being said.

What's different now is that the barrier to actually grokking hard concepts is so much lower. You can take a dense 1960s systems paper, work through it with an LLM, and come out the other side genuinely understanding it. You can customize the learning based on your skills, your experience, your knowledge. That wasn't possible before.

So I'm picking this back up. Starting with Turing Award winners from 1966, but I'm interested in both — Turing Award winners and other interesting CS papers worth understanding deeply. Reading the work, writing about it, building something from it. Learning for the sake of learning — with better tools than I had in school.

---

## Index

| # | Winner | Year | Core Contribution | Code | Writeup |
|---|--------|------|-------------------|------|---------|
| 01 | Alan Jay Perlis | 1966 | First working compiler (IT), co-designed ALGOL 60, founded CS as a discipline | [compiler.py](./01-alan-perlis-1966/compiler.py) | [README](./01-alan-perlis-1966/README.md) |

---

## Format

Each entry has code, an ELI10 explanation, and a CS grad-level writeup. A lot of this is automated — the code, the structure, the technical writeups. That's intentional.

But every entry has one section written by me. No AI assist on those.

Writing is how I think. It's how I actually understand something, not just recognize it. There's writing I'm happy to outsource — status updates, instructions, documentation. But the writing that makes me think has to come from me first. I'll get it fact-checked by an LLM after, but the thinking has to happen on the page before that.

Each week:
- **ELI10** — the contribution explained to a curious ten-year-old
- **CS grad** — the technical depth: what was new, what it replaced, why it mattered, what descended from it
- **Code** — a working implementation of the core idea
- **My take** — written by me, validated for accuracy after
- **Papers** — links to the primary sources

## Running the code

All implementations are self-contained. Each folder's README has specific instructions. In general:

```bash
cd 01-alan-perlis-1966
python compiler.py          # interactive REPL
python compiler.py --test   # run test suite
python compiler.py --verbose # show bytecode
```

## License

MIT — see [LICENSE](./LICENSE).

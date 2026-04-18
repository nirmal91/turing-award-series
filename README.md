# Turing Award Series

## Why

*This section is written by me — Nirmal. The rest of the repo is code and writeups that Claude helps structure, but this part is mine.*

I used to read research papers just because I was curious. Not because they were assigned, not because they'd help me ship something faster — just because I wanted to understand how someone figured something out. I've missed that.

What's different now is that the barrier to actually grokking hard concepts is so much lower. You can take a dense 1960s systems paper, work through it with an LLM, and come out the other side genuinely understanding it — not a surface-level summary, but the actual idea. And you can customize how deep you go, how it's explained, what you build from it. That wasn't possible before.

So I'm picking this back up. Starting with Turing Award winners from 1966, but I'm interested in both — Turing Award winners and other interesting CS papers worth understanding deeply. Reading the work, writing about it, building something from it. Learning for the sake of learning — with better tools than I had in school.

One Turing Award winner per week, starting from 1966. Working code, real writeups, back to first principles. Each entry covers two audiences: someone curious with no CS background, and someone with a CS degree who wants the actual depth.

---

## Index

| # | Winner | Year | Core Contribution | Code | Writeup |
|---|--------|------|-------------------|------|---------|
| 01 | Alan Jay Perlis | 1966 | First working compiler (IT), co-designed ALGOL 60, founded CS as a discipline | [compiler.py](./01-alan-perlis-1966/compiler.py) | [README](./01-alan-perlis-1966/README.md) |

---

## Format

Each week:
- **ELI10** — the contribution explained to a curious ten-year-old
- **CS grad** — the technical depth: what was new, what it replaced, why it mattered, what descended from it
- **Code** — a working implementation of the core idea
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

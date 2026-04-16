# Turing Award Series

One thing I genuinely miss from CS undergrad: sitting with a paper — a real one, written by someone who figured something out for the first time — working through it until it clicked, then building something from it. That feeling of *oh, that's how it actually works* doesn't show up in tutorials. It only comes from going to the source.

This series is an attempt to get that back. Every Turing Award winner, starting from 1966. One per week. Working code, real writeups, back to first principles.

Each entry is written for two audiences: someone curious with no CS background, and someone with a CS degree who wants the actual depth.

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

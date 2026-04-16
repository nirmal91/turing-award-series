# Turing Award Series

A weekly deep-dive into every Turing Award winner — who they were, why they mattered, and working implementations of their core ideas. Starting from 1966.

Each entry has two audiences: an ELI10 explanation and a CS graduate-level analysis, plus code that actually runs.

---

## Index

| # | Winner | Year | Core Contribution | Code | Writeup | Blog |
|---|--------|------|-------------------|------|---------|------|
| 01 | Alan Jay Perlis | 1966 | First working compiler (IT), co-designed ALGOL 60, founded CS as a discipline | [compiler.py](./01-alan-perlis-1966/compiler.py) | [README](./01-alan-perlis-1966/README.md) | [Post](./blog/01-alan-perlis-1966.md) |

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
```

## License

MIT — see [LICENSE](./LICENSE).

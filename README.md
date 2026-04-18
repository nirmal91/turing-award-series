# Turing Award Series

## Why

*This section is written by me — Nirmal. The rest of the repo is code and writeups that Claude helps structure, but this part is mine.*

I miss reading research papers. Not to apply them to a sprint or turn them into a feature — just to understand them. There's a version of learning that has no immediate ROI and I've been doing less and less of it the busier I've gotten.

Writing is how I think. When I write something down, I understand it differently than if I just read it or talked about it. I don't want to lose that.

There's a category of writing I'm happy to hand off entirely — status updates, documentation, instructions, meeting recaps. AI can have all of that. But writing to understand something? That I want to keep. This series is me doing that in public.

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

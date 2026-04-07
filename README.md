# Turing Award Series

A weekly deep-dive into every Turing Award winner — who they were, why they mattered, and working implementations of their core ideas. Starting from 1966.

Each entry has two audiences: a plain-language explanation for anyone curious, and a technical explanation for CS graduates. Every entry includes runnable code.

---

## Index

| # | Winner | Year | Core contribution | Code | Writeup |
|---|---|---|---|---|---|
| 01 | Alan Jay Perlis | 1966 | IT compiler; ALGOL 60 block structure & lexical scoping; founded CS curriculum | [compiler.py](01-alan-perlis-1966/compiler.py) | [README](01-alan-perlis-1966/README.md) |

---

## Structure

```
turing-award-series/
├── README.md                        ← this file (master index)
├── 01-alan-perlis-1966/
│   ├── README.md                    ← writeup (ELI10 + CS grad)
│   └── compiler.py                  ← expression compiler
├── 02-maurice-wilkes-1967/
│   └── ...
└── ...
```

## Running any week's code

Each folder is self-contained. Check the folder's README for specific instructions. Most entries require only a standard Python install:

```bash
python 01-alan-perlis-1966/compiler.py --test
```

## License

MIT — see [LICENSE](LICENSE).

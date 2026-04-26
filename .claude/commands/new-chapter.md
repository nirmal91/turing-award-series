You are helping add a new chapter to the Turing Award Series at /home/user/turing-award-series.

The user will provide: a winner's name, year, and optionally a topic hint.

Your job is to produce everything for that chapter. Work through these steps in order and confirm completion of each before moving on.

---

## Step 1 — Research

Find out:
- Full name, award year, ACM citation
- Core contribution (one sentence)
- Why it mattered at the time (what existed before, what changed after)
- Technical depth: how it worked, what it introduced, what descended from it
- Key papers (title, venue, year, DOI if available)
- One concrete before/after example (code, math, or concept — something visual)

---

## Step 2 — Folder and files

Create: `XX-firstname-lastname-YYYY/` (zero-padded number matching index)

Files to create:
- `README.md` (full chapter writeup)
- `implementation.py` (or appropriate language)

---

## Step 3 — README.md structure

Sections in this exact order:

### 1. Header
```
# Week XX — Full Name (YYYY)
**ACM Turing Award citation:** *"exact citation text"*
```

### 2. My Take
```
## My Take
*[Placeholder — written by Nirmal, not AI]*
```
Leave blank. Never fill this in. Nirmal writes it himself.

### 3. The Code
- Filename and link
- Pipeline or architecture diagram (text-based, e.g. `input → stage1 → stage2 → output`)
- What it supports / what you can do with it
- How to run it:
```bash
python implementation.py          # default mode
python implementation.py --test   # test suite
python implementation.py --verbose # show internals
```
- Example session showing input and output

### 4. ELI5
Explain the contribution to a curious 5-year-old. 4-6 lines. One concrete analogy. No jargon.

### 5. ELI10
Explain to a curious 10-year-old. 15-20 lines. Tell the story: what existed before, what the problem was, what changed, why it mattered. Include one specific detail that makes it feel real (a number, a name, a physical description).

### 6. CS Graduate Level
Deep technical writeup. Subsections for each major contribution. Cover:
- What the state of the art was before
- What was technically new
- How it worked (with a concrete example — code, math, or diagram)
- What it enabled or what descended from it
- Any lasting impact on how we build things today

### 7. Papers and Citations
Table format:
| Paper | Venue | Year |
|---|---|---|
| [Title](doi-link) | Journal/Conference | YYYY |

---

## Step 4 — Implementation code

Write a working implementation of the core idea. Requirements:
- Self-contained, no external dependencies beyond the standard library
- Interactive REPL or demo mode by default
- `--test` flag runs a self-test suite (minimum 10 test cases)
- `--verbose` flag shows internals (intermediate states, data structures, steps)
- The code should mirror the historical concept — not just simulate it, but actually implement the key idea
- Include a before/after example in comments or output: what you had to do before this invention, what you can do now

The implementation pipeline for most CS contributions follows one of these patterns:
- Compiler/language: input → lexer → parser → compiler → VM/executor
- Algorithm: problem setup → core algorithm → verification
- System concept: simplified model of the system with observable behavior

---

## Step 5 — Update root README index

Add a row to the index table in /home/user/turing-award-series/README.md:
```
| XX | Full Name | YYYY | One-line core contribution | [implementation.py](./XX-name-YYYY/implementation.py) | [README](./XX-name-YYYY/README.md) |
```

---

## Step 6 — LinkedIn post

Write a LinkedIn post in Nirmal's voice. Rules:
- Short sentences. No em dashes. No rule-of-three lists. No AI-sounding openers.
- Open with the personal hook: missing learning for the sake of learning, rabbit holes, research papers
- One sentence on the series and how most of it is AI generated but each entry has one section written by him
- 2-3 sentences on this winner's contribution — in plain language, what they did and why it matters today
- End with: "Link in comments."
- No headings, no bullet points, no bold. Just paragraphs.

---

## Step 7 — X thread

5 tweets. No numbers at the top. Each one is a reply to the previous.

- Tweet 1: Personal hook (rabbit holes, learning) + series announcement. Attach the image here.
- Tweet 2: AI generated vs human written — the writing philosophy.
- Tweet 3: This winner's contribution in plain language.
- Tweet 4: The broader impact — why it still matters today, connection to something modern.
- Tweet 5: github.com/nirmal91/turing-award-series

---

## Step 8 — Image spec

Describe a split image for the LinkedIn/X post:
- Left side: what things looked like BEFORE this contribution (code, notation, process)
- Right side: what this contribution made possible (the cleaner, more human version)
- Dark background, monospace font
- No headshots, no stock photos
- The contrast should tell the story without any text explanation

---

## Step 9 — Commit and push

```bash
git add .
git commit -m "Week XX: Full Name (YYYY) — [core contribution]"
git push origin main
```

---

## Checklist before finishing

- [ ] Folder created with correct naming convention
- [ ] README.md has all 7 sections in correct order
- [ ] My Take section is blank (placeholder only)
- [ ] Implementation runs: default, --test, --verbose
- [ ] Test suite has 10+ cases
- [ ] Before/after example included in code or README
- [ ] Root README index updated
- [ ] LinkedIn post drafted
- [ ] X thread drafted (5 tweets)
- [ ] Image spec written
- [ ] Committed and pushed to main

---

## Nirmal's voice (for LinkedIn and X)

Based on how he writes:
- Direct. Gets in fast, gets out fast.
- Short sentences. Doesn't over-explain.
- Personal but not performative.
- No "In today's world", no "It's worth noting", no "Dive into"
- No parallel three-part structures
- Casual language is fine if it's genuinely his — don't manufacture casualness
- The rabbit holes / learning for its own sake framing is his — use it

$ARGUMENTS

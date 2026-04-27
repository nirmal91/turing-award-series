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
- `concept.py` — simplified version (see Step 4a)
- `implementation.py` — full working version (see Step 4b)

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
- Link both files: `concept.py` and `implementation.py`
- Describe concept.py in one line: what the pure idea is, nothing else
- Pipeline or architecture diagram (text-based, e.g. `input → stage1 → stage2 → output`) for implementation.py
- What it supports / what you can do with it
- How to run it:
```bash
python concept.py                       # the core idea, plain
python implementation.py               # full working version
python implementation.py --test        # test suite
python implementation.py --verbose     # show internals
```
- Example session showing input and output

### 4. ELI5
Explain the contribution to a curious 5-year-old. 4-6 lines. No jargon.

**Required:** Use the specific before/after of this invention as the analogy. Do not use a generic analogy. The ELI5 must show: what the world looked like before, what was hard or painful about it, and what changed. If the invention was about changing instructions without touching hardware, show that. If it was about error correction, show what a corrupted message looks like before and after.

### 5. ELI10
Explain to a curious 10-year-old. **3-4 paragraphs max.** Tell the story: what existed before, what the problem was, what changed, why it mattered. Include one specific detail that makes it feel real (a number, a name, a physical description).

Do not pad. If 3 paragraphs cover it, stop at 3. The Maurice Wilkes ELI10 is the target length.

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

## Step 4a — concept.py (the pure idea)

Write a minimal Python file (~60 lines) that distills the core invention to its essence.

Requirements:
- No interactive REPL, no flags, no test harness
- Just the idea, runnable: `python concept.py`
- Should make the invention legible to someone who finds implementation.py too complex
- Comments should explain what this represents historically, not what the code does

Example: for Wilkes, concept.py had a `CONTROL_STORE` dict mapping opcodes to microinstruction lists, a `run()` function that followed those lists, and two example programs. That's it.

---

## Step 4b — implementation.py (full working version)

Write a complete working implementation of the core idea. Requirements:
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
- Short sentences. No em dashes. No hyphens. No rule-of-three lists. No AI-sounding openers.
- **For Week 02 onward:** Open with "Week XX of my learning series on Turing Award winners:" followed by 1-2 sentences from My Take (the most concrete insight). Do not re-explain the series or the AI-generated vs human-written split in the opener.
- 2-3 sentences on the winner's contribution — in plain language, what they did and why it matters today
- End with: "Link in comments."
- No headings, no bullet points, no bold. Just paragraphs.

Note: The full series setup (AI-generated, one section written by me, etc.) was in the Week 01 post. From Week 02 onward, readers know the series. Just tell them what this week's winner did.

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
- **No text labels on the image.** The visual contrast should tell the story without words.
- The contrast should be immediately legible — someone should understand left = bad/old, right = new/better just from seeing the code or structure

---

## Step 9 — Commit and push

**Do not push directly to main.** The repo has a hook that blocks direct pushes to main.

```bash
git add .
git commit -m "Week XX: Full Name (YYYY) — [core contribution]"
git push origin week-XX-firstname-lastname
gh pr create --title "Week XX: Full Name (YYYY)" --body "..."
gh pr merge --merge
```

---

## Checklist before finishing

- [ ] Folder created with correct naming convention
- [ ] README.md has all 7 sections in correct order
- [ ] My Take section is blank (placeholder only)
- [ ] concept.py created and runnable
- [ ] implementation.py runs: default, --test, --verbose
- [ ] Test suite has 10+ cases
- [ ] Before/after example included in code or README
- [ ] Root README index updated
- [ ] LinkedIn post drafted (Week 02+ format)
- [ ] X thread drafted (5 tweets)
- [ ] Image spec written (no text labels)
- [ ] Pushed via feature branch and PR, merged to main

---

## Nirmal's writing voice (for LinkedIn and X)

Based on how he writes:
- Direct. Gets in fast, gets out fast.
- Short sentences. Doesn't over-explain.
- Personal but not performative.
- No em dashes, no hyphens in prose
- No parallel three-part structures
- No "In today's world", no "It's worth noting", no "Dive into"
- Casual language is fine if it's genuinely his — don't manufacture casualness
- The rabbit holes / learning for its own sake framing is his — use it

## Code walkthrough guidance (if Nirmal asks to understand the code)

Go section by section, a few lines at a time. Lead with what the thing *is* historically before explaining what the code does. For example: "Registers are just storage slots on the chip — think of them as variables the hardware keeps around. Here's the code:" works better than "This section defines the register file."

If Nirmal says the code is too complex, offer to distill it down. concept.py exists for exactly this reason.

$ARGUMENTS

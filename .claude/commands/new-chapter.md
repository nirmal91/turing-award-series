You are helping add a new chapter to the Turing Award Series at /home/user/turing-award-series.

Your job is to produce everything for that chapter. Work through these steps in order and confirm completion of each before moving on.

---

## Auto-detecting the next winner

**If the user provides no arguments**, determine the next winner automatically:

1. List the folders in `/home/user/turing-award-series/` that match the pattern `NN-*` (e.g. `04-marvin-minsky-1969`).
2. Find the highest chapter number.
3. Look up the next entry in the winner list below.
4. Proceed with that winner — no confirmation needed.

**If the user provides a name and year**, use those instead.

### Complete Turing Award winner list

| # | Name | Year |
|---|------|------|
| 01 | Alan Jay Perlis | 1966 |
| 02 | Maurice Wilkes | 1967 |
| 03 | Richard Hamming | 1968 |
| 04 | Marvin Minsky | 1969 |
| 05 | James Wilkinson | 1970 |
| 06 | John McCarthy | 1971 |
| 07 | Edsger Dijkstra | 1972 |
| 08 | Charles Bachman | 1973 |
| 09 | Donald Knuth | 1974 |
| 10 | Allen Newell & Herbert Simon | 1975 |
| 11 | Michael Rabin & Dana Scott | 1976 |
| 12 | John Backus | 1977 |
| 13 | Robert Floyd | 1978 |
| 14 | Kenneth Iverson | 1979 |
| 15 | Tony Hoare | 1980 |
| 16 | Edgar Codd | 1981 |
| 17 | Stephen Cook | 1982 |
| 18 | Ken Thompson & Dennis Ritchie | 1983 |
| 19 | Niklaus Wirth | 1984 |
| 20 | Richard Karp | 1985 |
| 21 | John Hopcroft & Robert Tarjan | 1986 |
| 22 | John Cocke | 1987 |
| 23 | Ivan Sutherland | 1988 |
| 24 | William Kahan | 1989 |
| 25 | Fernando Corbató | 1990 |
| 26 | Robin Milner | 1991 |
| 27 | Butler Lampson | 1992 |
| 28 | Juris Hartmanis & Richard Stearns | 1993 |
| 29 | Edward Feigenbaum & Raj Reddy | 1994 |
| 30 | Manuel Blum | 1995 |
| 31 | Amir Pnueli | 1996 |
| 32 | Douglas Engelbart | 1997 |
| 33 | Jim Gray | 1998 |
| 34 | Fred Brooks | 1999 |
| 35 | Andrew Yao | 2000 |
| 36 | Ole-Johan Dahl & Kristen Nygaard | 2001 |
| 37 | Ron Rivest, Adi Shamir & Leonard Adleman | 2002 |
| 38 | Alan Kay | 2003 |
| 39 | Vint Cerf & Bob Kahn | 2004 |
| 40 | Peter Naur | 2005 |
| 41 | Frances Allen | 2006 |
| 42 | Edmund Clarke, Allen Emerson & Joseph Sifakis | 2007 |
| 43 | Barbara Liskov | 2008 |
| 44 | Charles Thacker | 2009 |
| 45 | Leslie Valiant | 2010 |
| 46 | Judea Pearl | 2011 |
| 47 | Silvio Micali & Shafi Goldwasser | 2012 |
| 48 | Leslie Lamport | 2013 |
| 49 | Michael Stonebraker | 2014 |
| 50 | Whitfield Diffie & Martin Hellman | 2015 |
| 51 | Tim Berners-Lee | 2016 |
| 52 | John Hennessy & David Patterson | 2017 |
| 53 | Yann LeCun, Geoffrey Hinton & Yoshua Bengio | 2018 |
| 54 | Ed Catmull & Pat Hanrahan | 2019 |
| 55 | Alfred Aho & Jeffrey Ullman | 2020 |
| 56 | Jack Dongarra | 2021 |
| 57 | Bob Metcalfe | 2022 |
| 58 | Avi Wigderson | 2023 |
| 59 | Andrew Barto & Richard Sutton | 2024 |

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

### 4. Full Worked Example

A complete step-by-step walkthrough of the core algorithm or concept with real numbers. No skipping steps. This section is for Nirmal to refer back to when writing his My Take and for readers who want to understand the mechanics.

Structure:
- Start from scratch: given inputs, what do you do first?
- Show every intermediate step with actual values
- For algorithms: show the happy path, then at least one edge case or failure case
- For the Hamming chapter this meant: finding r by trial and error, assigning positions, computing each parity bit, sending, then all three receive cases (data flip, parity flip, no flip)

This section did not exist in Week 02 and was added during Week 03 after Nirmal asked for it. Include it from Week 04 onward.

### 5. ELI5
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

**Go slow. Never fast-forward.** Nirmal needs to understand every step before moving to the next. The Hamming session required 10+ rounds before the syndrome logic clicked. What worked: concrete examples with real numbers, grids/tables for visual patterns, walking every case by hand. What failed: stating the conclusion before building up to it.

**Use visualizations first for abstract concepts.** If explaining anything involving positions, patterns, binary, or coverage — draw a grid or table before writing prose. The Hamming parity bit assignment only clicked when positions 1-7 were written in binary as a grid.

## LinkedIn post guidance

Start from the My Take text, not a fresh draft. Trim to LinkedIn length, add the week opener and "Link in comments." The My Take already has Nirmal's voice — every fresh draft was worse.

Tweet 4 of the X thread should connect to the most concrete modern example: name specific companies (Mag-7, hyperscalers), specific hardware (H100s, ECC RAM), specific numbers. Generic "it matters today" is weak.

## Image spec guidance

For algorithm/concept chapters, the image should show the actual data being processed, not an abstract before/after. Real values, real encoding steps, a real error or transformation — that's more useful than a metaphor.

Expect two generations minimum. After the first image comes back: check labels are factually correct, check no decorative elements crept in, check the visual tells the right story. Give specific feedback on what to fix.

**Labels are fine.** Nirmal prefers text labels on the image for clarity. The original spec said no labels but he consistently opts in.

**Geometry-heavy images require precision.** If the concept involves spatial relationships (points in a plane, lines, regions, network layers), be explicit in the prompt: name exact positions, specify angles, describe whether the boundary is a line or a region. Vague prompts produce wrong geometry every time. Expect 4-6 iterations for anything geometric.

**Model choice matters.** Imagen 3 in Google AI Studio and DALL-E 3 via ChatGPT tend to follow spatial instructions more literally than other tools. If one model keeps getting it wrong after 2-3 tries, switch.

---

## Nirmal's exploration pattern (what he digs into each session)

Nirmal consistently goes deep on these areas — build them into the session proactively:

**Conceptual connections:** He will ask how this invention connects to things he already knows — other fields, modern tools, prior chapters. Answer directly and precisely. Don't deflect, but don't overclaim either. If the connection is real, confirm it. If it's a parallel but not causal, say so.

**Historical context:** He wants to know who else was involved, what the relationships were, what was happening at the time. Personal details (who knew whom, what institution, what year) are the kind of thing he finds interesting.

**Real-world anchors:** He always connects to modern tech — specific companies, specific hardware, specific numbers. Bring these in proactively in the CS Grad section and Tweet 4. Don't wait for him to ask.

**Code walkthroughs:** He will ask to understand the code in plain language. Go slow. Always have a non-CS framing ready for the core concept — what is this thing in the physical world, before explaining what the code does.

**Fact-checking his instincts:** He will make strong claims and want to know if they hold. Engage with these directly — confirm what's right, correct what's not, explain the nuance. He appreciates precision over diplomacy.

---

## My Take guidance

**Nirmal writes his own My Take.** The AI placeholder stays until he writes it. But he will ask for bullet points and drafts to work from. Provide:
1. A clean bullet list of verifiable facts in order
2. Flag anything to double-check before he writes (founding dates, attribution claims, causation vs correlation)
3. A draft that he will then rewrite in his own words — expect multiple rounds

**His writing pattern for My Take:**
- Opens with the person's name and their biggest claim to fame
- Connects to institutions or ideas that still exist today (makes it feel relevant)
- Two highlights max, each given its own paragraph
- Ends with the modern connection: specific companies, hardware, numbers
- Longer sentences than his LinkedIn/X posts — more explanatory, less punchy
- Personal observations and casual asides are his voice — keep them

**What not to do:**
- Don't make it punchy/clipped — his My Take is more expansive than his social posts
- Don't use em dashes — replace with periods or colons
- Don't overclaim causation — if the winner influenced something, say influenced, not caused
- Don't make him sound like an AI wrote it — if a draft sounds too clean, it's wrong

---

## LinkedIn post guidance

**The LinkedIn post IS the My Take, trimmed.** Start from his My Take text, not a fresh draft. Add the week opener, trim to fit, end with "Link in comments." The My Take already has his voice — fresh drafts are always worse.

**Week opener format:** "Week XX of my learning series on Turing Award winners: [Full Name]." Then go straight into the content — no meta-commentary about the series format.

**His LinkedIn voice:**
- Longer sentences than X, but still direct
- Paragraph breaks between major ideas
- No bullet points, no bold, no headings
- Ends every post with "Link in comments." on its own line
- Casual language is fine if it's genuinely his — don't manufacture it

---

## X thread guidance

**Thread structure Nirmal confirmed:**
- Tweet 1: Week opener + one hook sentence + image
- Tweet 2: AI generated vs human written (the writing philosophy) — keep this brief
- Tweet 3: The winner's background and core contribution
- Tweet 4: First technical highlight
- Tweet 5: Second technical highlight or modern impact
- Tweet 6: GitHub link with full chapter URL (not just the repo root)

**Do not:** add a "each week I cover one winner" framing — his audience knows the series.

**Do:** use his exact LinkedIn language broken into tweet-sized chunks. Don't rewrite or improve it. He will push back if you do.

---

## Extra demos (when Nirmal asks for code beyond the chapter)

Nirmal often asks for additional code explorations beyond concept.py and implementation.py. These go in the chapter folder as extra files.

**Terminal animations:** Use ANSI escape codes. No matplotlib needed. A grid of colored characters works well for visualizing any kind of progression, boundary, or state change over time.

**Simulation/emergent behavior demos:** When the concept involves multiple interacting components, build a demo where each component prints what it's doing, with a small delay so it's watchable. The emergent behavior should be visible in the output.

**Naming:** Be descriptive, not generic. Name the file after what it demonstrates.

---

## PR and merge workflow

Use GitHub MCP tools, not gh CLI:
1. `mcp__github__create_pull_request` to open the PR
2. `mcp__github__merge_pull_request` to merge it
3. Branch: always `claude/new-chapter-XXXX` (session-specific, already exists)
4. Do not push directly to main

Images cannot be committed from this environment — they are not accessible as files in the session. Tell Nirmal to save the image locally and add it himself, or drag it into the next session.

$ARGUMENTS

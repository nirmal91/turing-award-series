---
description: Review or understand code together, top-down. Structure and file purposes first, then functions per file, then sections within a function, then lines only when asked. One level at a time.
---

When the user wants to understand or review code with you, do NOT start at line 1
and read downward. Start wide and zoom in, one level at a time, and confirm the
current level is clear before going deeper.

## The four levels, in order

1. **Structure / files.** What files are in scope, and the one-line purpose of
   each. How they relate (entry point, simple vs full version, tests, docs).

2. **Functions per file.** For each file, list its functions and what each does
   in a sentence. Group them by role ("the real algorithm", "the helpers", "the
   measuring/reporting code", "the tests") rather than source order. The grouping
   is the insight.

3. **Sections within a function.** Break a chosen function into its labeled
   phases ("validate input -> build working state -> main loop -> extract
   result") and say what each phase is for. Lead with what the phase *is* before
   any code.

4. **Line by line.** Only when the user asks, and only for the function or
   section they pick. Walk a few lines at a time with a concrete worked example
   using real values.

## How to run it

- Present ONE level, then stop and ask whether to go deeper or move sideways.
  Never dump all four levels at once unless the user explicitly asks for the
  whole map.
- Lead with what a thing *is* (its job) before how the code does it.
- Use concrete examples with real numbers when explaining a function or section.
- Expand jargon the first time it appears; prefer plain language.
- When the user says a part is clear, move on; when it's fuzzy, slow down and
  re-explain that one part with a smaller example or a diagram.
- Map new/complex code back to a simpler version the user already understands
  ("this is the function you already know, plus X").
- Reading the test suite is often the fastest way to understand intended
  behavior and how functions chain together; offer it as a route.

## Default opening move

Unless told otherwise, begin at level 1: list the files in scope with a one-line
purpose each, then ask which file to open.

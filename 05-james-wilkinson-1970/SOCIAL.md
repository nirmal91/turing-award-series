# Week 05 — James H. Wilkinson — social drafts

*(LinkedIn opener is best rewritten from My Take once Nirmal writes it. This is a draft in his voice to work from.)*

---

## LinkedIn

Week 05 of my learning series on Turing Award winners: James Wilkinson.

In the 1950s people were genuinely scared of letting computers do math. Every calculation rounds, and the theory at the time said those tiny rounding errors would pile up until the answer to a large system of equations was useless. So people avoided big problems.

Wilkinson had actually used the machines. He built one of the first computers at Britain's National Physical Laboratory, sitting right next to Alan Turing. He kept noticing that the answers were far better than the gloomy theory said they should be, and he wanted to know why.

His move was to ask a different question. Not "how far is my answer from the perfect one" but "is my answer the exact solution to a question almost identical to the one I asked." If it is, the method did its job, and any leftover error is the problem being sensitive, not the method being bad. He called it backward error analysis.

That one shift is why we trust floating point math at all today. It sits underneath NumPy, LAPACK, and the mixed precision tricks that let GPUs train large AI models fast without losing accuracy.

Link in comments.

---

## X thread

**1/**
I keep falling down rabbit holes into old computer science papers. Week 5 of my series on every Turing Award winner: James Wilkinson, 1970.
[attach cover image]

**2/**
Same setup as always. The code and most of the writeups are AI generated. One section every week is written by me, no AI. Writing is how I check that I actually understand a thing.

**3/**
In the 1950s the theory said rounding errors would ruin any large calculation. Wilkinson, who built early computers next to Alan Turing, asked a smarter question: is my answer the exact solution to a problem almost identical to the one I asked? If yes, the method is trustworthy.

**4/**
This is why we trust floating point math. His backward error analysis is baked into LAPACK and NumPy, and it is the reason mixed precision solvers can run most of the work in fp16 on H100 tensor cores and still come back with an accurate answer.

**5/**
github.com/nirmal91/turing-award-series

---

## Image spec (cover.png)

Split image, dark background, monospace font. No headshots, no stock photos, no descriptive text labels (no "before/after" words). The contrast is the actual arithmetic from the worked example: the same 3-digit machine solving the same system, once badly and once well.

**Left half (the unstable solve, rendered in a decaying / red-orange tone):**

```
0.0001·x₁ + 1·x₂ = 1
     1·x₁ + 1·x₂ = 2

m = 1 / 0.0001 = 10000
1 − 10000  →  −9999  →  −10000
x = [0, 1]   ✗
```

The visual point: the multiplier balloons to 10000, the real data (the small 1s) gets swallowed, and the answer is wrong. Numbers grow large and the final vector is marked with an ✗.

**Right half (the stable solve, rendered in a clean / green tone):**

```
(swap rows)
m = 0.0001 / 1 = 0.0001
1 − 0.0001  →  0.9999  →  1
x = [1, 1]   ✓
```

The visual point: one row swap, the multiplier stays tiny, the numbers stay near 1, the answer is right, marked with a ✓.

Same machine, same digits. Left looks like an explosion of large numbers ending in a wrong answer; right looks calm and ends in the right answer. The reader should grasp "left = blew up, right = stayed under control" purely from the size of the numbers and the ✗ vs ✓, without any caption.

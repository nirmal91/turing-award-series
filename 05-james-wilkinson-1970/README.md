# Week 05 — James H. Wilkinson (1970)

**ACM Turing Award citation:** *"For his research in numerical analysis to facilitate the use of the high-speed digital computer, having received special recognition for his work in computations in linear algebra and 'backward' error analysis."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — solve a sensitive 2x2 system on a 4-digit machine; the answer is far off the truth but is the exact answer to a problem almost identical to the one we asked.

[`implementation.py`](./implementation.py) — a finite-precision machine, Gaussian elimination on it, and the three numbers Wilkinson taught us to measure:

```
matrix A, vector b
    ↓
finite-precision machine (round every result to k significant digits)
    ↓
Gaussian elimination
    ├─ no pivoting    → tiny pivot, huge multiplier, good digits wiped out
    └─ partial pivot  → largest entry first, multipliers ≤ 1, stays stable
    ↓
measure three things:
    forward error   = how far the answer is from the true solution
    backward error  = how small a change to (A, b) makes the answer exact
    condition number = how much this problem amplifies input error
    ↓
the law that ties them together:
    forward error  ≤  condition number  ×  backward error
```

What it supports:
- Solve any linear system on a machine with a configurable number of digits
- Compare Gaussian elimination with and without partial pivoting, with growth factors
- Compute backward error, forward error, and the condition number of a matrix
- Expand and probe Wilkinson's polynomial `(x-1)(x-2)...(x-20)` — the textbook ill-conditioned problem

```bash
python concept.py                       # the core idea, plain
python implementation.py                # full working demo
python implementation.py --test         # test suite (16 cases)
python implementation.py --verbose      # show elimination steps and internals
```

Example session:

```
B) Same problem, two algorithms: why partial pivoting matters
    A = [[0.0001, 1.0], [1.0, 1.0]],  b = [1.0001, 2.0],  true x ~ [1.0, 1.0]
    condition number = 4.0  (this system is fine)

    no pivoting:       x = [0.0, 1.0]
        growth factor  = 10000.0
        backward error = 2.5e-01   <- huge, UNSTABLE
    partial pivoting:  x = [1.0, 1.0]
        growth factor  = 1.0
        backward error = 0.0e+00   <- tiny, STABLE

D) Wilkinson's polynomial: (x-1)(x-2)...(x-20)
    change the x^19 coefficient by 2^-23 = 1.19e-07
    worst root (root 16) then moves by ~ 287.00
```

---

## Full Worked Example

**Problem:** solve a 2x2 system two ways and watch one ordering stay trustworthy while the other falls apart. Then separate the algorithm's fault from the problem's fault.

The system:

```
0.0001·x1 + 1·x2 = 1.0001
     1·x1 + 1·x2 = 2.0
```

The true solution is `x = [1, 1]`. The matrix is well-behaved — its condition number is only 4. Any honest method should get close. We solve on a **3-significant-digit machine**: every multiply and subtract is rounded to 3 figures, the way real hardware rounds to its word length.

### Step 1 — No pivoting

Use the first row as the pivot row. The pivot is `0.0001`.

```
multiplier m = a21 / a11 = 1 / 0.0001 = 10000
```

That huge multiplier is the warning sign. Now eliminate `x1` from row 2:

```
a22_new = 1 - 10000·1 = 1 - 10000 = -9999  → round to 3 figs → -10000
b2_new  = 2 - 10000·1.0001 = 2 - 10001 = -9999  → round to 3 figs → -10000
```

Look at what happened. The real `a22_new` is `-9999`, but on a 3-digit machine it rounds to `-10000`. The original `1` in that slot got swallowed. The good information is gone.

Back-substitute:

```
x2 = b2_new / a22_new = -10000 / -10000 = 1.00       (looks fine)
x1 = (b1 - a12·x2) / a11 = (1.0001 - 1·1.00) / 0.0001
   = 0.0001 / 0.0001  ... but 1.0001 rounded to 3 figs is 1.00,
   so the numerator is (1.00 - 1.00) = 0
x1 = 0 / 0.0001 = 0
```

Result: `x = [0, 1]`. The true answer was `[1, 1]`. `x1` is 100% wrong.

Is this just a sensitive problem? No. Plug `[0, 1]` back in:

```
row 1:  0.0001·0 + 1·1 = 1.0000   vs  b1 = 1.0001   (off by 0.0001)
row 2:       1·0 + 1·1 = 1.0      vs  b2 = 2.0       (off by 1.0)
```

The residual is `[0.0001, 1.0]`. To make `[0, 1]` the *exact* answer you would have to change `b` from `2.0` to `1.0` — a 50% change to the problem. **Backward error ≈ 0.25.** The algorithm invented a different problem. That is instability.

### Step 2 — Partial pivoting

Before eliminating column 1, swap in the row with the largest entry in that column. `|1| > |0.0001|`, so swap the rows:

```
     1·x1 + 1·x2 = 2.0
0.0001·x1 + 1·x2 = 1.0001
```

Now the pivot is `1`, and the multiplier is small:

```
multiplier m = 0.0001 / 1 = 0.0001
a22_new = 1 - 0.0001·1 = 0.9999  → round to 3 figs → 1.00
b2_new  = 1.0001 - 0.0001·2 = 1.0001 - 0.0002 = 0.9999  → round → 1.00
```

This time the rounding throws away `0.0001`, which was never going to matter. Back-substitute:

```
x2 = 1.00 / 1.00 = 1.00
x1 = (2.0 - 1·1.00) / 1 = 1.00
```

Result: `x = [1, 1]`. Correct. Plug it back in and the residual is on the order of `0.0001` — **backward error ≈ 0**. Same data, same machine, same arithmetic. The only difference is the order of elimination. One order is backward stable, the other is not. That is Wilkinson's central result about Gaussian elimination: pivot, and the method is trustworthy.

### Step 3 — When the problem itself is the villain

Now take a system that really is sensitive:

```
1·x1 + 1·x2      = 2
1·x1 + 1.0001·x2 = 2.0001     true x = [1, 1]
```

Its condition number is about 40000. Solve it *exactly* (no rounding at all), but pretend the right-hand side carried a measurement error of one part in a million — change `b1` from `2` to `2.000002`:

```
exact solution of the perturbed system ≈ [1.02, 0.98]
```

A 0.0001% nudge to the input moved the answer by 2%. The amplification is roughly `40000 × 0.000001 = 0.04`, the condition number times the input error. No algorithm did anything wrong. The problem itself magnifies error. This is the other half of the story:

```
forward error   ≤   condition number   ×   backward error
   (2%)               (40000)               (0.0001%)
```

A backward-stable algorithm guarantees the backward error is tiny. The condition number is fixed by the problem. Multiply them and you get the accuracy you can actually expect. If the answer is bad, this inequality tells you whether to fix your code or accept that the question was delicate.

### Step 4 — The polynomial that traumatized Wilkinson

The same idea, at its most extreme. Take `p(x) = (x-1)(x-2)...(x-20)`. The roots are obviously `1, 2, ..., 20`. Expanded into coefficients, the `x^19` term is `-210`. Now change that one coefficient by `2^-23 ≈ 0.00000012`:

```
sensitivity of root 16 to that coefficient ≈ 2.4e9
root 16 moves by about 2.4e9 × 1.19e-7 ≈ 287
```

Several roots leave the real line entirely and become complex. Evaluating this polynomial is trivial arithmetic. Recovering its roots is hopeless in finite precision — not because of a bad algorithm, but because the roots are insanely sensitive to the coefficients. The condition number is astronomical. Wilkinson called it "the most traumatic experience in my career as a numerical analyst," and it is why we still teach it.

---

## ELI5

Imagine I ask you to share 2 cookies between 2 friends. Easy: one each.

Now imagine the scale you weigh cookies on only shows whole numbers. You weigh things, you round, you do the sharing. At the end one friend has 0 cookies and the other has 1. That looks totally wrong!

But here is the trick. Instead of asking "how wrong is the answer?", ask "what question did I actually answer?" It turns out your answer is the perfectly correct answer to *almost the same* cookie question — just the tiniest bit different from the one I asked.

Before this idea, people were scared that all the little roundings a computer does would pile up into garbage. Wilkinson showed that a good method gives you the exact right answer to a question that is barely different from yours. So you can trust it. And if the answer still looks weird, it means your question was a tricky one, not that the computer messed up.

---

## ELI10

In the 1940s, the first computers could do thousands of arithmetic steps, and people wanted to use them to solve big systems of equations — the kind that show up in engineering and physics. There was a real fear holding everyone back. Every step, a computer rounds its numbers to fit in a fixed amount of space. Solving a system of 100 equations takes about a million steps. If every step adds a little error, surely a million steps turn the answer into nonsense? One early estimate suggested the error could grow like 4 multiplied by itself 100 times. That is a number with 60 digits. If true, computers would be useless for serious math.

James Wilkinson, working at the National Physical Laboratory in England on an early computer called the Pilot ACE, looked at this the right way around. Instead of trying to track how far the computed answer drifts from the true answer, he asked: what problem does my computed answer solve *exactly*? He proved that for the standard method (Gaussian elimination, with a simple trick called pivoting — always divide by the biggest number available, never a tiny one), the messy computed answer is the perfect, exact answer to a problem that is only a hair's breadth away from the real one. The errors do not pile up the way everyone feared. He called this backward error analysis.

This split the world into two clean questions. Is the algorithm good? That is backward error, and pivoting keeps it tiny. Is the problem itself touchy? That is the condition number, and it has nothing to do with your code. Wilkinson's favorite example of a touchy problem was a polynomial with roots at 1, 2, all the way to 20. Nudge one of its coefficients by less than a millionth, and a root jumps by almost 300. No computer could ever find those roots accurately, and it would not be the computer's fault. Today every piece of scientific software — the libraries behind weather models, aircraft design, and machine learning — rests on the confidence Wilkinson gave us that the arithmetic underneath can be trusted.

---

## CS Graduate Level — Backward Error Analysis and Conditioning

### 1. The State of the Art Before (1940s–1950s)

The first stored-program computers made direct solution of linear systems feasible for the first time, and the obvious algorithm was Gaussian elimination. But the theory of rounding error was pessimistic. The dominant approach was **forward error analysis**: track how the error in each intermediate quantity propagates to the final answer. Done naively, the bounds are catastrophic, because they assume errors add up in the worst possible way at every one of the `O(n³)` operations.

Hotelling's 1943 analysis of elimination produced an error bound that grew like `4ⁿ`. Von Neumann and Goldstine's 1947 paper *Numerical Inverting of Matrices of High Order* was more careful but still framed the problem in forward terms and through matrix inversion. The widespread belief was that Gaussian elimination on large systems was numerically dangerous, and that you might need to invert the matrix or use special stabilization to trust the result. This was a real barrier to using computers for the linear algebra at the heart of engineering and physics.

### 2. Wilkinson's Contribution: Backward Error Analysis

Wilkinson, at the National Physical Laboratory, reframed the question. Let `x̂` be the computed solution to `Ax = b`. Forward error asks for `‖x̂ − x‖`. Wilkinson instead asked: for what perturbed problem is `x̂` the *exact* solution? That is, find the smallest `E` and `e` such that

```
(A + E) x̂ = b + e
```

The size of `(E, e)` relative to `(A, b)` is the **backward error**. Wilkinson's theorem for Gaussian elimination with partial pivoting: the computed `x̂` is the exact solution of `(A + E)x = b` where

```
‖E‖∞  ≤  c·n·ρ·u·‖A‖∞
```

`u` is the unit roundoff (the machine's relative precision), `n` is the matrix size, `c` is a small constant, and `ρ` is the **growth factor** — the largest entry that appears during elimination, relative to the largest entry of the original matrix. The crucial point: with partial pivoting, every multiplier has magnitude `≤ 1`, so entries cannot blow up freely, and `ρ` is empirically small (it can be bounded by `2ⁿ⁻¹` in pathological constructions, but in practice it stays near 1). The feared `4ⁿ` growth simply does not occur. The algorithm is **backward stable**: it solves a problem negligibly different from the one posed.

This is a representational shift, not just a tighter bound. Backward error puts the algorithm's error on the same footing as the uncertainty already in the data — measurement noise, the rounding of `A` and `b` into the machine to begin with. If your inputs are only known to relative precision `u` anyway, an algorithm with backward error `O(u)` has done everything that could possibly be asked of it.

### 3. The Condition Number: Separating Two Sources of Error

Backward error answers "is the algorithm good?" It says nothing about "is the answer accurate?" The bridge is the **condition number**. For a linear system, perturbing `(A, b)` to `(A + E, b + e)` changes the solution by

```
‖x̂ − x‖     ‖E‖   ‖e‖
───────  ≲  κ(A)·( ─── + ─── ),     κ(A) = ‖A‖·‖A⁻¹‖
  ‖x‖             ‖A‖   ‖b‖
```

`κ(A)` measures how much the *problem* amplifies input perturbations, independent of any algorithm. This yields the rule of thumb that organizes the whole field:

```
forward error   ≲   condition number   ×   backward error
```

A backward-stable algorithm makes the second factor `O(u)`. The first factor belongs to the problem. So the accuracy you can expect is roughly `κ(A)·u`: lose about `log₁₀ κ(A)` decimal digits to conditioning, no matter how good your code is. If `κ(A) ≈ 10⁶` and you have 16 digits of double precision, expect about 10 correct digits. This is not a defect to be fixed; it is information about the problem.

A concrete demonstration from `implementation.py`: the matrix `[[1, 1], [1, 1.0001]]` has `κ ≈ 40000`. Solving it exactly but with the right-hand side perturbed by a relative `10⁻⁶` moves the solution by a relative `2 × 10⁻²` — the amplification `κ × 10⁻⁶ ≈ 4 × 10⁻²` predicts it. The algorithm is blameless; the conditioning is the whole story.

### 4. Why Pivoting Is the Whole Ballgame (a worked contrast)

The system `[[10⁻⁴, 1], [1, 1]] x = [1.0001, 2]` has condition number 4 — it is a well-posed problem. On a 3-digit machine:

- **Without pivoting**, the pivot `10⁻⁴` forces multiplier `10⁴`. Computing `a₂₂ ← 1 − 10⁴·1 = −9999` rounds to `−10000`; the original `1` is lost to rounding. Back-substitution returns `x = [0, 1]`. The residual is `[10⁻⁴, 1]`, a backward error of `≈ 0.25`. The growth factor is `10⁴`. **Unstable.**
- **With partial pivoting**, the rows swap so the pivot is `1` and the multiplier is `10⁻⁴`. The lost digit is now `0.0001`, which never mattered. Back-substitution returns `x = [1, 1]`, backward error `≈ 0`, growth factor `1`. **Stable.**

Same data, same arithmetic, same precision. The only variable is the order of elimination. This is why partial pivoting is not an optimization but a correctness requirement, and Wilkinson's growth-factor analysis is what proved it.

### 5. What Descended From It

**LAPACK / BLAS and every numerical library.** The error bounds in LAPACK's documentation are stated in exactly Wilkinson's terms: a computed solution with a small backward error, an accuracy governed by the condition number. NumPy, SciPy, MATLAB, R, Julia, and Eigen all call into this lineage. When `numpy.linalg.solve` returns an answer, the guarantee you are implicitly trusting is Wilkinson's backward-stability theorem.

**The standard vocabulary of numerical analysis.** "Backward stable," "condition number," "growth factor," and "forward versus backward error" are now the first concepts taught in any numerical methods course. Trefethen and Bau's *Numerical Linear Algebra* is built around them. The framework applies far beyond linear systems — eigenvalues, least squares, FFTs, ODE solvers — and Wilkinson's own *The Algebraic Eigenvalue Problem* (1965) extended it to the symmetric and unsymmetric eigenproblem.

**IEEE 754 floating point (1985).** The standard's careful definition of correctly-rounded operations — `fl(a op b) = round(a op b)` exactly — is what makes backward error analysis rigorous rather than heuristic. Wilkinson's analyses assumed this rounding model; the standard made hardware obey it. William Kahan, who drove IEEE 754, worked squarely in the tradition Wilkinson established.

**Modern mixed-precision and machine learning numerics.** The current move to `float16` and `bfloat16` for training large models is a direct application of conditioning analysis: which parts of a computation tolerate a large `u`, and which need high precision to keep `κ·u` acceptable? Iterative refinement — solve cheaply in low precision, correct using the residual — is a Wilkinson-era technique now central to mixed-precision linear solvers on GPUs. The question "how many bits do I actually need here?" is backward error analysis wearing modern clothes.

### 6. The Lasting Idea

The deepest contribution is not any single theorem but a way of thinking. Before Wilkinson, error analysis chased the answer and usually despaired. After him, the question became: *what problem did I actually solve, and how sensitive was it?* Splitting accuracy into an algorithm part (backward error) and a problem part (condition number) is one of the cleanest conceptual moves in computing. It turned floating-point arithmetic from something to be feared into something to be reasoned about precisely — which is the only reason we trust a computer to fly an aircraft, model the climate, or train a neural network.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [Error Analysis of Direct Methods of Matrix Inversion](https://doi.org/10.1145/321075.321076) (Wilkinson) | Journal of the ACM | 1961 |
| [Rounding Errors in Algebraic Processes](https://archive.org/details/roundingerrorsin0000wilk) (Wilkinson) | Prentice-Hall / HMSO | 1963 |
| [The Algebraic Eigenvalue Problem](https://global.oup.com/academic/product/the-algebraic-eigenvalue-problem-9780198534181) (Wilkinson) | Oxford University Press | 1965 |
| [The Evaluation of the Zeros of Ill-conditioned Polynomials (Parts I & II)](https://doi.org/10.1007/BF01386366) (Wilkinson) | Numerische Mathematik | 1959 |
| [Numerical Inverting of Matrices of High Order](https://doi.org/10.1090/S0002-9904-1947-08909-6) (von Neumann & Goldstine) | Bulletin of the AMS | 1947 |
| [Modern Error Analysis](https://doi.org/10.1137/1013001) (Wilkinson) | SIAM Review | 1971 |

---

*Previous: [Week 04 — Marvin Minsky (1969)](../04-marvin-minsky-1969/)*

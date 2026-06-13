# Week 05 — James H. Wilkinson (1970)

**ACM Turing Award citation:** *"For his research in numerical analysis to facilitate the use of high-speed digital computing machines, having received special recognition for his work in computations in linear algebra and 'backward' error analysis."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — solve a 2x2 system in 3-digit arithmetic, then measure two different errors: how far the answer is from the truth, and how small a change to the question would make the answer exactly right.

[`implementation.py`](./implementation.py) — finite-precision Gaussian elimination with the full backward-error toolkit:

```
linear system A x = b
    ↓
solve in finite precision (Gaussian elimination, with/without partial pivoting)
    → computed answer x̂
    ↓
backward error = ||b - A·x̂|| / ||b||      ← measurable without the true answer
    (how much you'd nudge the question to make x̂ exact — blames the ALGORITHM)
    ↓
condition number κ(A) = ||A||·||A⁻¹||       ← a property of the problem alone
    (how much the problem amplifies any input change)
    ↓
forward error = ||x̂ - x_true|| / ||x_true||  ← what you actually got
    ↓
the inequality that ties them together:  forward  ≤  κ(A) × backward
```

What it supports:
- Solve any linear system in a chosen number of significant digits
- Compare Gaussian elimination with and without partial pivoting on the same problem
- Compute backward error, condition number, and forward error, and verify the bound that links them
- Separate algorithm instability (large backward error) from problem sensitivity (large condition number)

```bash
python concept.py                       # the core idea, plain
python implementation.py                # demo: stability vs conditioning
python implementation.py --test         # test suite (16 cases)
python implementation.py --verbose      # show the elimination trace and norms
```

Example session:

```
Scenario 1 — well-conditioned problem, true x = [10, 1].
Same matrix, 4-digit arithmetic. Only the algorithm differs.

  (a) Gaussian elimination WITHOUT pivoting:
    computed x : [-10.0, 1.001]
    true x     : [10.0, 1.0]
    condition number kappa(A) : 12.3
    backward error ||r||/||b|| : 1.79   (blame the algorithm)
    forward error  ||dx||/||x||: 2      (what you actually got)

  (b) Gaussian elimination WITH partial pivoting:
    computed x : [10.0, 1.0]
    true x     : [10.0, 1.0]
    backward error ||r||/||b|| : 0
    forward error  ||dx||/||x||: 0
```

Same matrix. Same precision. The only change is moving the largest entry onto the diagonal before eliminating. Without it the answer flips sign; with it the answer is exact. The condition number (12.3) says the problem was never hard. The backward error tells you which run you can trust.

---

## Full Worked Example

We solve this system on a machine that keeps only **4 significant digits** — the way an early computer with a short word would.

```
0.003 x1 + 59.14 x2 = 59.17
5.291 x1 -  6.130 x2 = 46.78
```

The true answer is `x1 = 10`, `x2 = 1`. Check: `0.003·10 + 59.14·1 = 59.17` and `5.291·10 - 6.130·1 = 46.78`. Both exact.

### Step 1 — The floating-point model

Every arithmetic result is rounded to 4 significant digits before the next step uses it. Wilkinson wrote this as:

```
fl(a op b) = (a op b)(1 + δ),    |δ| ≤ u
```

`u` is the unit roundoff — the largest relative error one rounded operation can introduce. With 4 decimal digits, `u ≈ 0.5 × 10⁻³`. Each operation is nearly exact. The question is what happens when you chain thousands of them.

### Step 2 — Two different errors

```
forward error   =  how far the computed answer is from the true answer
backward error  =  how small a change to the INPUT would make the
                   computed answer exactly correct
```

You can almost never measure the forward error directly — you would need the true answer, which is the thing you were trying to compute. You can always measure the backward error: it is just the residual `r = b - A·x̂`, plugged straight back into the original equations.

### Step 3 — Solve WITHOUT pivoting (the failure case)

Eliminate `x1` from row 2 using row 1. The multiplier is:

```
m = 5.291 / 0.003 = 1763.67  →  rounds to 1764
```

That huge multiplier is the warning sign. Now form the new row 2:

```
new coeff of x2:  -6.130 - 1764 × 59.14
                = -6.130 - 104322.96
                  └─ 1764 × 59.14 = 104322.96, rounds to 104300 ─┘
                = -104306.13  →  rounds to -104300

new RHS:          46.78 - 1764 × 59.17
                = 46.78 - 104375.88
                  └─ rounds to 104400 ─┘
                = -104353.22  →  rounds to -104400
```

Watch what just happened. The original `-6.130` and `46.78` were swallowed whole by the rounding of a number a thousand times larger. The information they carried is gone. Back-substitute:

```
x2 = -104400 / -104300 = 1.001
x1 = (59.17 - 59.14 × 1.001) / 0.003
   = (59.17 - 59.20) / 0.003        ← 59.14 × 1.001 = 59.199, rounds to 59.20
   = -0.03 / 0.003
   = -10
```

Computed answer: `x1 = -10`, `x2 = 1.001`. The true answer was `x1 = +10`. **The sign is wrong.**

Now the backward error. Plug `x̂ = [-10, 1.001]` back into the *original* equations and see what right-hand side it actually satisfies:

```
row 1:  0.003·(-10) + 59.14·1.001 = -0.03 + 59.199 = 59.169   (wanted 59.17, off by 0.001)
row 2:  5.291·(-10) -  6.130·1.001 = -52.91 - 6.136 = -59.046   (wanted 46.78, off by 105.83)
```

Residual `r = [0.001, 105.83]`. The backward error `||r|| / ||b|| = 105.83 / 59.17 ≈ 1.79`. That is enormous. The computed answer does not solve our problem or any problem close to it. **The algorithm is to blame.**

### Step 4 — Solve WITH partial pivoting (the fix)

Partial pivoting first swaps in the row with the largest entry in the pivot column. `5.291 > 0.003`, so swap the rows:

```
5.291 x1 -  6.130 x2 = 46.78
0.003 x1 + 59.14 x2 = 59.17
```

Now the multiplier is small:

```
m = 0.003 / 5.291 = 0.000567
```

Eliminate:

```
new coeff of x2:  59.14 - 0.000567 × (-6.130) = 59.14 + 0.003476 = 59.14
new RHS:          59.17 - 0.000567 × 46.78    = 59.17 - 0.02652  = 59.14
```

Nothing got swallowed this time, because we never multiplied by a giant number. Back-substitute:

```
x2 = 59.14 / 59.14 = 1.0
x1 = (46.78 - (-6.130)·1.0) / 5.291 = 52.91 / 5.291 = 10.0
```

Computed answer: `x1 = 10`, `x2 = 1`. Exact. Residual is zero. Backward error is zero.

### Step 5 — The point

Both runs used the same matrix, the same right-hand side, and the same 4-digit precision. The condition number of this matrix is about **12.3** — small, so the problem is well-conditioned and a good algorithm should return a good answer.

```
                    multiplier   backward error   forward error   verdict
without pivoting       1764           1.79             2.0         algorithm failed
with pivoting          0.000567       0.0              0.0         algorithm fine
```

Backward error analysis lets you say, precisely, that the no-pivot run failed because the *algorithm* was unstable, not because the *problem* was hard. That separation is the whole contribution.

### Edge case — when the algorithm is fine but the answer is still wrong

Now flip it. Take the 6×6 Hilbert matrix, `H[i][j] = 1/(i+j+1)`, with true solution all ones. Solve it with partial pivoting (a stable algorithm) in 6-digit arithmetic:

```
backward error ||r||/||b|| : 2.26e-06   (tiny — algorithm did its job)
condition number kappa(A)  : 2.91e+07   (huge — the problem is sensitive)
forward error  ||dx||/||x||: 2.42       (the answer is garbage anyway)
```

The algorithm behaved perfectly: its answer exactly solves a problem within `2.26e-06` of the one you asked. But because `κ ≈ 2.9 × 10⁷`, that tiny input wiggle gets amplified into a 240% error in the output. The bound `forward ≤ κ × backward` holds: `2.42 ≤ 2.9e7 × 2.26e-6 ≈ 66`. Nobody did anything wrong. The problem itself cannot be solved accurately in 6 digits. Knowing that is what stops you from blaming your code.

---

## ELI5

Imagine you ask a friend to add up a long list of numbers, and they hand you back an answer.

Before Wilkinson, the only way to check them was to know the real total already. But if you knew the total, you wouldn't have asked.

Wilkinson's trick: don't ask "is the answer right?" Ask "is there a list *almost exactly like mine* that gives this answer perfectly?" If your friend's answer is the perfect total for a list that's only a tiny bit different from yours, your friend did a great job. The numbers they worked with were basically yours.

If you'd have to change your list a lot to match their answer, then they messed up. You can tell a good worker from a bad one without ever knowing the true total.

---

## ELI10

In the 1950s, computers did arithmetic with a fixed, small number of digits. Every time the machine multiplied or divided, it had to throw away the digits that didn't fit. One rounding is harmless. But solving a system of equations or finding the roots of a matrix takes thousands of operations, and people were terrified that all those tiny roundings would pile up into a useless answer. The standard way to check was "forward error analysis": track how far the computed numbers drift from the true numbers at every step. The bounds it produced were so pessimistic they were worthless. They'd tell you the answer might be off by a factor of a billion when it was actually fine.

James Wilkinson, working at the National Physical Laboratory in England (he had helped build the Pilot ACE computer there, designed from Alan Turing's plans), flipped the question around. Instead of asking how wrong the answer is, he asked: *what problem did this answer solve exactly?* A computer solving `A x = b` hands you some `x̂`. Wilkinson showed you can almost always find a slightly different matrix and right-hand side that `x̂` solves perfectly. If that "slightly different" problem is genuinely close to the one you asked, the algorithm is trustworthy. He called this **backward error analysis**.

The payoff is that it splits one confusing question into two clean ones. The backward error measures the *algorithm*: did it stay close to the real problem? The condition number measures the *problem*: how much does it magnify small changes? Multiply them together and you get a bound on the actual error. So when an answer comes out wrong, you can tell whether your code is buggy or whether the problem was simply impossible to solve accurately on that machine. Wilkinson used this to prove that Gaussian elimination with partial pivoting — the method everybody already used — is stable, which is why it's still the default in every numerical library today, from LAPACK to NumPy.

---

## CS Graduate Level — Why Backward Error Analysis Mattered

### 1. The State of the Art Before (1940s–1950s)

Two giants had already looked at rounding error in matrix computations. John von Neumann and Herman Goldstine (1947) analysed the inversion of positive-definite matrices and produced rigorous but extremely pessimistic forward-error bounds. Alan Turing (1948) introduced the idea of a *condition number* and analysed Gaussian elimination, getting closer to the modern view. But the dominant technique was **forward error analysis**: bound the error in each intermediate quantity, then propagate those bounds forward through the computation.

The trouble with forward analysis is that errors compound multiplicatively. A bound that loses a constant factor at each of `n` steps degrades like that factor to the `n`-th power. For realistic problem sizes the resulting bounds were astronomically larger than the errors actually observed. Practitioners knew Gaussian elimination worked well in practice, but the theory said it might be catastrophic. There was no framework that matched observed behavior.

### 2. Wilkinson's Reframing

Wilkinson's insight (developed through the 1950s, consolidated in *Rounding Errors in Algebraic Processes*, 1963, and *The Algebraic Eigenvalue Problem*, 1965) was to stop tracking the error in the answer and instead attribute all of the accumulated roundoff to a perturbation of the **input data**.

Formally: a computed solution `x̂` to `A x = b` has **backward error** if there exist perturbations `ΔA`, `Δb` such that

```
(A + ΔA) x̂ = b + Δb
```

holds *exactly*, with `‖ΔA‖` and `‖Δb‖` small relative to `‖A‖` and `‖b‖`. The normwise backward error is the size of the smallest such perturbation. An algorithm is **backward stable** if it always produces an `x̂` whose backward error is of order the unit roundoff `u`.

This is a profound shift in what "correct" means. A backward-stable algorithm does not promise an accurate answer. It promises that the answer it gives is the *exact* answer to a problem indistinguishable from yours at machine precision. That is the most you can ask of any algorithm running on rounded inputs — the input was already only known to precision `u`.

### 3. The Floating-Point Model and the Master Inequality

Wilkinson worked from a simple axiom about each elementary operation:

```
fl(a op b) = (a op b)(1 + δ),    |δ| ≤ u,    op ∈ {+, −, ×, ÷}
```

From this, the error in any algorithm can be folded into perturbations of the inputs. For solving `A x = b` by Gaussian elimination, Wilkinson proved the computed solution satisfies

```
(A + ΔA) x̂ = b,    ‖ΔA‖∞ ≤ c(n) · ρ · u · ‖A‖∞
```

where `c(n)` is a low-degree polynomial in the dimension and `ρ` is the **growth factor** — the ratio of the largest entry encountered during elimination to the largest entry of the original matrix. The entire stability question reduces to controlling `ρ`.

The backward error then connects to the forward error through the condition number `κ(A) = ‖A‖ ‖A⁻¹‖`:

```
‖x̂ − x‖        ‖ΔA‖
───────  ≤  κ(A) · ─────   +  O(u²)
 ‖x‖           ‖A‖
```

This is the rule of thumb every numerical analyst carries: **forward error ≲ condition number × backward error**. A stable algorithm makes the backward error tiny; the condition number, a property of the problem, decides whether the forward error is also tiny. The implementation in this chapter verifies this inequality numerically on every example.

### 4. Worked Mechanism — Why Pivoting Controls the Growth Factor

Consider eliminating `x₁` from the system in the worked example, in 4-digit arithmetic:

```
0.003 x1 + 59.14 x2 = 59.17
5.291 x1 -  6.130 x2 = 46.78
```

Without pivoting, the multiplier is `5.291 / 0.003 ≈ 1764`. The updated entry `-6.130 - 1764 × 59.14 ≈ -104300` is four orders of magnitude larger than any original entry, so the growth factor `ρ` is huge. When `-6.130` is subtracted from a number near `-104300` and rounded to 4 digits, it vanishes entirely. The backward error `‖ΔA‖/‖A‖` ends up of order 1 — the computed answer solves a completely different problem.

Partial pivoting swaps the rows so the multiplier becomes `0.003 / 5.291 ≈ 0.000567 < 1`. Every multiplier is bounded by 1 in magnitude, so no entry can grow by more than a factor of 2 per step, and `ρ ≤ 2ⁿ⁻¹` in the worst case (and almost always `O(1)` in practice). The backward error stays at order `u`. Same problem, same arithmetic, stable versus unstable — the difference is entirely the growth factor, and Wilkinson's analysis is what made that visible.

### 5. What Descended From It

**LAPACK / LINPACK / EISPACK.** Wilkinson co-authored the Handbook for Automatic Computation (1971) and the algorithms that became EISPACK and LINPACK, which became LAPACK — the linear algebra core underneath MATLAB, NumPy, R, Julia, and essentially every scientific computing stack. The QR algorithm for eigenvalues, which he analysed and made practical, is still the standard method today.

**The definition of numerical stability.** "Backward stable" is now the default criterion for judging any numerical algorithm. When a new solver is published, the headline theorem is almost always a backward-error bound. Nick Higham's *Accuracy and Stability of Numerical Algorithms* (the field's standard reference) is essentially a 700-page elaboration of Wilkinson's program.

**The Wilkinson polynomial.** To show that root-finding can be wildly ill-conditioned, Wilkinson exhibited the polynomial with roots `1, 2, …, 20`. A change of `2⁻²³` in a single coefficient moves some roots by more than 2 — a dramatic, concrete demonstration that conditioning is a property of the problem, not a failure of any method. It remains the canonical example of ill-conditioning.

**IEEE 754.** The 1985 floating-point standard, which guarantees correctly rounded operations, is exactly the clean `fl(a op b) = (a op b)(1 + δ)` model Wilkinson's analysis assumed. His framework is one reason the standard was worth the effort: with correctly rounded operations, backward error bounds are clean and portable across machines.

### 6. Lasting Impact

Every time NumPy solves a linear system and returns an answer you trust, you are relying on Wilkinson. The reason `numpy.linalg.solve` does not come with a warning label is that the algorithm underneath is provably backward stable, and the library can (via the condition number) tell you when the *problem* is the issue. Modern machine learning inherits the same machinery: training is a sequence of enormous linear-algebra operations in low precision (float16, bfloat16, even float8), and the question of whether a low-precision matrix multiply or attention computation is stable is answered with backward-error analysis. The unit roundoff `u` got bigger as precision got smaller, but the framework for reasoning about it is unchanged. Wilkinson gave the field the language to say "the algorithm is fine, the problem is hard" and mean something precise by it.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [Error Analysis of Direct Methods of Matrix Inversion](https://doi.org/10.1145/321105.321107) | Journal of the ACM | 1961 |
| [Rounding Errors in Algebraic Processes](https://archive.org/details/roundingerrorsin0000wilk) (book) | Prentice-Hall / HMSO | 1963 |
| [The Algebraic Eigenvalue Problem](https://global.oup.com/academic/product/the-algebraic-eigenvalue-problem-9780198534181) (book) | Oxford University Press | 1965 |
| [Handbook for Automatic Computation, Vol. II: Linear Algebra](https://doi.org/10.1007/978-3-642-86940-2) (with C. Reinsch) | Springer | 1971 |
| [Numerical Inverting of Matrices of High Order](https://doi.org/10.1090/S0002-9904-1947-08909-6) (von Neumann & Goldstine, the prior art) | Bulletin of the AMS | 1947 |
| [Rounding Errors in Algebraic Processes (Turing Award Lecture context)](https://amturing.acm.org/award_winners/wilkinson_0671216.cfm) | ACM | 1970 |

---

*Previous: [Week 04 — Marvin Minsky (1969)](../04-marvin-minsky-1969/)*

# Week 05 — James H. Wilkinson (1970)

**ACM Turing Award citation:** *"For his research in numerical analysis to facilitate the use of the high-speed digital computer, having received special recognition for his work in computations in linear algebra and 'backward' error analysis."*

---

## My Take

The entire AI data centers' compute resources are all trying to fight over getting more FLOPs (Floating Point Operations). Creating a big model is trillions times trillions of FLOPs, run for multiple weeks. But people didn't trust the results of FLOPs not so long ago, when computers were very new. There was a lot of doubt that floating-point arithmetic could happen correctly. There's some rounding that happens, and the worry was that all the rounding would lead to a really big error and the answers would be wrong.

It was Wilkinson, who got the Turing Award in 1970, who changed that. He helped introduce a new way to measure the answer and check if we can trust it. Forward errors are hard to compute in general because you need the right answer and then do the subtraction, but backward errors are much easier to compute. It's how much you have to nudge the inputs to make your answer exactly right. Instead of thinking if the result answered the question perfectly, think what question did the result answer, and for very well-designed algorithms the answer is very, very little, 10 to the minus 16 or something very small.

This became the gold standard on how to measure how good algorithms are. Backward errors are always in reason; they stay about the size of the rounding. But errors can still get big, and that's because of finicky inputs, not just because of algorithms. A finicky input blows up the error no matter what algorithm you use or what machine it runs on. How finicky the input is is called the condition number. So it comes together like this:

```
forward error  ≈  condition number  ×  backward error
```

TLDR: he helped build confidence in algorithms that do floating-point arithmetic, which is the foundation of everything in the AI world today.

---

## The Code

[`concept.py`](./concept.py) — solve one nasty system, then ask two questions about the same answer: how wrong is it, and how wrong would the problem have to be for it to be right.

[`implementation.py`](./implementation.py) — Gaussian elimination with partial pivoting, plus an exact rational solver to measure against, plus the two error metrics and the condition number:

```
matrix A, vector b
    ↓
Gaussian elimination + partial pivoting  (floating point, the real solver)
    ↓
computed solution x
    ↓
   ├── residual r = b - A x        → backward error: how wrong the QUESTION is
   ├── exact rational solve        → forward error: how wrong the ANSWER is
   └── exact inverse               → condition number: the amplification factor
```

What it supports:
- Solve any linear system in floating point the way LAPACK does (partial pivoting)
- Measure the backward error (the residual, normalized) of the computed solution
- Compare against an exact rational solution to get the true forward error
- Compute the condition number exactly and watch `forward ≈ condition × backward`

```bash
python3 concept.py                      # the core idea, plain
python3 implementation.py               # guided demo
python3 implementation.py --test        # test suite (18 cases)
python3 implementation.py --verbose     # show pivoting steps and residuals
```

Example session:

```
2. Hilbert matrices. As n grows they edge toward singular.
   Watch the split: backward error stays at machine precision while
   the forward error explodes in lockstep with the condition number.

  Hilbert 8x8
    condition number : 3.39e+10
    backward error   : 4.08e-17   (near u = 1.1e-16, machine precision)
    forward error    : 1.37e-07   (rule of thumb: ~ cond x backward = 1.38e-06)

  Hilbert 12x12
    condition number : 4.04e+16
    backward error   : 7.14e-17   (near u = 1.1e-16, machine precision)
    forward error    : 5.95e-03   (rule of thumb: ~ cond x backward = 2.88e+00)
```

The backward error never moves. The forward error tracks the condition number. That gap is the whole point.

---

## Full Worked Example

The question Wilkinson answered: when a computed answer looks wrong, is the algorithm broken, or was the problem just hard? You separate those with the backward error. Here is the entire mechanic, by hand.

### Step 0 — The rounding axiom

A computer stores numbers in fixed precision, so almost every operation rounds:

```
fl(a op b) = (a op b)(1 + δ),   |δ| ≤ u
```

`u` is the unit roundoff, about `1.1e-16` for IEEE double precision. Concretely:

```
0.1 + 0.2  =  0.30000000000000004     not exactly 0.3
```

The key reading of that axiom: a rounded result is the *exact* result for slightly perturbed inputs. `fl(a + b)` is the true sum of `a(1+δ)` and `b(1+δ)`. Backward error analysis is this one observation pushed through an entire algorithm.

### Step 1 — A system with a known answer

```
A = | 1     1      |        b = | 2      |
    | 1     1.0001 |            | 2.0001 |
```

The exact solution is `x = [1, 1]`:

```
row 1:  1·1 + 1·1        = 2        ✓
row 2:  1·1 + 1.0001·1   = 2.0001   ✓
```

The two rows are almost the same line. That is what makes this matrix dangerous.

### Step 2 — A computed answer that looks broken

Suppose the solver hands back

```
z = [0, 2]
```

Forward error — how far is `z` from the true `[1, 1]`?

```
||z - x|| / ||x|| = ||[-1, 1]|| / ||[1, 1]|| = 1 / 1 = 1.0     (100% off)
```

By the forward-error verdict this is a disaster. Hold that thought.

### Step 3 — The residual

Plug `z` back into the original system and see what is left over: `r = b - A z`.

```
A z = | 1·0 + 1·2        |  = | 2      |
      | 1·0 + 1.0001·2   |    | 2.0002 |

r = b - A z = | 2      | - | 2      | = | 0       |
              | 2.0001 |   | 2.0002 |   | -0.0001 |
```

The residual is tiny. `z` *almost* satisfies the equations.

### Step 4 — The backward error

How small a relative change to `A` and `b` would make `z` the exact answer? The normwise relative backward error (Rigal–Gaches, 1967):

```
η = ||r||∞  /  ( ||A||∞ · ||z||∞  +  ||b||∞ )
```

Fill in the infinity norms (largest absolute row sum for the matrix, largest absolute entry for the vectors):

```
||r||∞ = 0.0001
||A||∞ = max(1+1, 1+1.0001) = 2.0001
||z||∞ = 2
||b||∞ = 2.0001

η = 0.0001 / (2.0001·2 + 2.0001) = 0.0001 / 6.0003 = 1.67e-05
```

So `z` is the exact solution of a problem that sits `0.0017%` away from the one we asked. The method did almost nothing wrong.

### Step 5 — Show the perturbed problem explicitly

This is not hand-waving. There is a concrete `E` with `(A + E) z = b` exactly:

```
E = r zᵀ / (zᵀz)
zᵀz = 0² + 2² = 4

E = | 0       | · [0  2]  / 4   =  | 0   0        |
    | -0.0001 |                    | 0   -0.00005 |
```

Check it:

```
A + E = | 1   1        |
        | 1   1.00005  |

(A + E) z = | 1·0 + 1·2          | = | 2      | = b   ✓
            | 1·0 + 1.00005·2    |   | 2.0001 |
```

One entry of `A` nudged by `0.00005` and `z` becomes exact. That perturbation is far smaller than any real measurement error you would have in the data.

### Step 6 — Why the answer was bad anyway: the condition number

The condition number is the amplification factor from input error to output error: `κ(A) = ||A||∞ · ||A⁻¹||∞`.

```
det A = 1·1.0001 - 1·1 = 0.0001

A⁻¹ = (1/det) | 1.0001   -1 | = | 10001   -10000 |
              | -1        1 |   | -10000   10000 |

||A⁻¹||∞ = max(10001+10000, 10000+10000) = 20001

κ(A) = 2.0001 · 20001 ≈ 4.0e4
```

The rule of thumb ties the three numbers together:

```
forward error  ≈  condition number  ×  backward error
     1.0        ≈      4.0e4         ×      1.67e-5      ≈  0.67
```

Same order of magnitude. The backward error was at the level of rounding noise; the condition number multiplied it up to a 100% forward error. The blow-up came from the *problem*, not the *algorithm*.

### Edge case — the same residual on a well-conditioned matrix

Swap in a tame matrix and the story changes:

```
A = | 2   1 |        b = | 3 |        true x = [1, 1],   κ(A) ≈ 3.2
    | 1   3 |            | 4 |
```

Suppose a computed answer leaves the *same size* residual, `η ≈ 1.67e-5`. The forward error this time:

```
forward error  ≈  κ(A) × η  ≈  3.2 × 1.67e-5  ≈  5e-5
```

Identical backward error, tiny forward error. The only thing that changed is the condition number. That is the lesson: backward error grades the algorithm, the condition number grades the problem, and only their product tells you how good the answer is. Wilkinson proved Gaussian elimination with partial pivoting keeps the backward error near `u` for any size of matrix, so the algorithm is never the thing to blame.

---

## ELI5

Imagine you have a tricky weighing scale and you measure your dog at 12 kilos.

The old way to grade your measurement was to ask: how far is 12 from the dog's real weight? But you do not know the real weight, so that question goes nowhere and just makes you nervous.

Wilkinson asked a better question. He said: pretend 12 is exactly right. How much would the dog's real weight have to change for 12 to be the perfect answer? If the dog only has to be a tiny hair heavier, your scale is great. If the dog would have to be a totally different dog, your scale is junk.

So instead of grading the answer, you grade how much you would have to bend the question. A tiny bend means you can trust the tool.

---

## ELI10

In the 1950s, people had finally built fast computers, but a lot of mathematicians did not trust them with real arithmetic. The reason was rounding. A computer can only keep so many digits, so every multiply and add throws away a little bit. The worry was that these little errors would pile up. The standard way to check that was to track how far the computed answer drifted from the true answer, and when you did that math for solving a big system of equations the predicted error grew enormously. On paper it looked like computers were useless for anything large.

James Wilkinson, who had worked with Alan Turing on an early British computer called the Pilot ACE, noticed the prediction did not match reality. The machines kept giving good answers on real problems. So he changed the question. Instead of asking "how wrong is the answer," he asked "what slightly different problem did this answer solve perfectly?" He could prove that the computer's answer was the exact solution to a problem almost identical to the one you typed in, off by an amount no bigger than the rounding itself.

That reframe was huge. It meant the algorithm was not the problem. When an answer came out badly wrong, it was because the *problem itself* was super sensitive, where even a microscopic change to the inputs swings the answer wildly. He gave that sensitivity a number, the condition number, and showed the real relationship: how wrong your answer is roughly equals the condition number times the backward error. Good algorithm, tiny backward error. Touchy problem, big condition number. Multiply them to know how much to trust the result. Every numerical library today, the code that runs weather models, aircraft simulations, and machine learning, is built on this way of thinking.

---

## CS Graduate Level — Why Backward Error Analysis Mattered

### 1. The State of the Art Before (1940s–1950s)

The dominant tool was **forward error analysis**: bound the error in each operation, then propagate those bounds forward through the computation. For an isolated operation this is fine. For a long algorithm it is a catastrophe of pessimism, because the bounds compound multiplicatively and ignore the cancellations that actually occur.

The notorious case was Gaussian elimination. A naive forward analysis of elimination on an `n × n` matrix produced error bounds that grew like `2ⁿ`. By that estimate, solving a `100 × 100` system would be hopeless. Hotelling published exactly this kind of pessimistic bound in 1943, and it scared a generation of mathematicians away from trusting computers with linear algebra. Yet in practice the method worked beautifully. There was no theory explaining the gap between the terrifying bounds and the reliable results.

### 2. Wilkinson's Insight

The starting point is the floating-point model. For any basic operation,

```
fl(a op b) = (a op b)(1 + δ),     |δ| ≤ u
```

where `u` is the unit roundoff. Read it the other way: the rounded result is the **exact** result on perturbed operands. Wilkinson's move was to carry this interpretation through an entire algorithm and collect all the little `(1 + δ)` factors into a single perturbation of the *input data*.

For a computed solution `x̂` of `Ax = b`, the claim takes the form

```
(A + E) x̂ = b
```

with `||E||` small relative to `||A||`. The computed answer is the *exact* answer to a nearby problem. Wilkinson called `E` the backward error, and the size of the smallest such `E` (and perturbation to `b`) is the **backward error** of the computation.

The crucial separation follows immediately. Combine the backward error with a **perturbation bound** for the problem:

```
relative forward error  ≲  κ(A) · (relative backward error)
```

where `κ(A) = ||A|| · ||A⁻¹||` is the condition number. This factorizes accuracy into two independent pieces:

- **Backward error** measures the *algorithm*. An algorithm is *backward stable* if it keeps this near `u`.
- **Condition number** measures the *problem*. It is a property of the data, not the method, and no algorithm can beat it.

A large forward error therefore has exactly two possible causes, and the backward error tells you which: either the algorithm is unstable (large backward error) or the problem is ill-conditioned (large `κ`). You can no longer blame the computer for a hard problem.

### 3. How It Works on Gaussian Elimination

Wilkinson's headline result, worked out in his 1961 *Journal of the ACM* paper and his 1965 book *The Algebraic Eigenvalue Problem*, is that Gaussian elimination with partial pivoting (GEPP) is backward stable in practice. The computed solution satisfies

```
(A + E) x̂ = b,     ||E||∞ ≤ c · n · ρ · u · ||A||∞
```

where `n` is the dimension, `c` is a small constant, and `ρ` is the **growth factor**, the ratio of the largest entry encountered during elimination to the largest entry of the original matrix. The entire stability question reduces to controlling `ρ`. Partial pivoting (always eliminate with the largest-magnitude entry in the column) bounds `ρ ≤ 2ⁿ⁻¹` in the worst case, but Wilkinson observed that for real matrices `ρ` is almost always tiny, on the order of `n^(1/2)`. That single empirical-plus-theoretical fact is why GEPP is the workhorse of `LAPACK` and every linear solver shipped since.

The demonstration in `implementation.py` makes the split visible on Hilbert matrices, which are symmetric, positive definite, and viciously ill-conditioned:

```
Hilbert 4x4    κ ≈ 2.8e4     backward ≈ 0          forward ≈ 4.6e-13
Hilbert 8x8    κ ≈ 3.4e10    backward ≈ 4.1e-17    forward ≈ 1.4e-07
Hilbert 12x12  κ ≈ 4.0e16    backward ≈ 7.1e-17    forward ≈ 6.0e-03
```

The backward error sits at machine precision the entire time. The forward error climbs in lockstep with `κ`. Same algorithm, behaving identically; the answers degrade because the problems get harder.

### 4. Backward Error of a Single Operation

The model scales down to the simplest case, which is the cleanest illustration. Take the inner product of two `n`-vectors computed in the obvious order. The result satisfies

```
fl(xᵀy) = Σ xᵢ yᵢ (1 + θᵢ),     |θᵢ| ≤ γ_n = n·u / (1 - n·u)
```

Every product term is perturbed by a relative amount bounded by roughly `n·u`. The computed inner product is the *exact* inner product of slightly perturbed inputs. There is no statement about how close it is to the true value, and there does not need to be. That is supplied separately by the conditioning of the inner product. Wilkinson's whole edifice is this `γ_n` bookkeeping applied recursively to elimination, factorization, and eigenvalue iterations.

### 5. What Descended From It

- **EISPACK and LINPACK (1970s):** Wilkinson and Reinsch's *Handbook for Automatic Computation, Vol. II: Linear Algebra* (1971) collected backward-stable Algol procedures for eigenvalue and linear-system problems. Those procedures were translated directly into EISPACK and LINPACK.
- **LAPACK and BLAS (1990s–today):** the libraries underneath NumPy, SciPy, MATLAB, R, Julia, and every HPC stack. Their error guarantees are stated in exactly Wilkinson's terms: "the computed solution is the exact solution of a nearby system."
- **IEEE 754 (1985):** the floating-point standard codified the `fl(a op b) = (a op b)(1 + δ)` model with correctly rounded operations, which is precisely the axiom backward error analysis needs to be rigorous rather than approximate.
- **Numerical reproducibility and stability analysis** of essentially every algorithm: QR factorization, the QR algorithm for eigenvalues (Francis, building on Wilkinson), Cholesky, least squares, and modern randomized numerical linear algebra all carry backward stability proofs in Wilkinson's framework.

### 6. Lasting Impact

The deepest legacy is conceptual. Before Wilkinson, "is this computation accurate?" was a single fuzzy question. After him it is two sharp ones: *is the algorithm stable* (backward error) and *is the problem well-conditioned* (condition number). That decomposition is now reflexive for anyone who does numerical work. When a deep learning training run diverges, when a Kalman filter drifts, when a physics simulation blows up, the first diagnostic instinct is to ask which of the two it is. Half-precision and mixed-precision training on modern accelerators (the `bfloat16` and `fp8` formats on hyperscaler TPUs and NVIDIA H100s) live or die by exactly this analysis: you are deliberately raising `u`, so you had better know your algorithm is backward stable and your problem is well-conditioned, or the loss of precision will surface as a wrong answer. Wilkinson, who hand-analyzed rounding on a machine with a few thousand words of memory, wrote the playbook that those systems still follow.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [Error Analysis of Direct Methods of Matrix Inversion](https://doi.org/10.1145/321075.321076) | Journal of the ACM | 1961 |
| [Rounding Errors in Algebraic Processes](https://doi.org/10.1090/S0025-5718-1966-0192673-4) *(book)* | Prentice-Hall / HMSO | 1963 |
| [The Algebraic Eigenvalue Problem](https://global.oup.com/academic/product/the-algebraic-eigenvalue-problem-9780198534181) *(book)* | Oxford University Press | 1965 |
| [Modern Error Analysis](https://doi.org/10.1137/1013095) | SIAM Review | 1971 |
| [Handbook for Automatic Computation, Vol. II: Linear Algebra](https://doi.org/10.1007/978-3-642-86940-2) *(with C. Reinsch)* | Springer | 1971 |

---

*Previous: [Week 04 — Marvin Minsky (1969)](../04-marvin-minsky-1969/)*

# Week 05 — James H. Wilkinson (1970)

**ACM Turing Award citation:** *"For his research in numerical analysis to facilitate the use of the high-speed digital computer, having received special recognition for his work in computations in linear algebra and 'backward' error analysis."*

---

## My Take
*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — the pure idea: solve one 2x2 system on a 3-digit machine and ask not "how wrong is the answer" but "what problem did this answer solve exactly."

[`implementation.py`](./implementation.py) — finite-precision Gaussian elimination instrumented to measure backward error, forward error, and the growth factor:

```
matrix A, vector b
    ↓
round every entry to s significant digits (a 1960s machine word)
    ↓
forward elimination  (optional partial pivoting), rounding every operation
    ↓
track the growth factor: how large do the entries get?
    ↓
back-substitution → computed x
    ↓
residual r = b - A·x          → backward error  ||r|| / (||A||·||x||)
compare to true x (15 digits)  → forward error   ||x - x_true|| / ||x_true||
    ↓
check Wilkinson's bound: forward error  ≤  condition number × backward error
```

What it supports:
- Solve any 2x2 or 3x3 system at a chosen precision, with or without partial pivoting
- See the growth factor that controls stability
- See the residual, the backward error, the forward error, and the condition number side by side
- Watch partial pivoting turn an unstable solve into a stable one

```bash
python3 concept.py                      # the core idea, plain
python3 implementation.py               # interactive demo
python3 implementation.py --test        # test suite (15 cases)
python3 implementation.py --verbose     # show every elimination step
```

Example session:

```
=== small-pivot (NO pivoting) ===
  computed x     : [0, 1]
  true x         : [1.0001, 0.9999]
  growth factor  : 1e+04
  backward error : 5.000e-01   (what nearby system x solved exactly)
  forward error  : 1.000e+00   (how far x is from the truth)

=== small-pivot (partial pivoting) ===
  computed x     : [1, 1]
  true x         : [1.0001, 0.9999]
  growth factor  : 1
  backward error : 5.000e-05   (what nearby system x solved exactly)
  forward error  : 1.000e-04   (how far x is from the truth)
```

Same matrix, same arithmetic, same number of digits. The only change is one row swap. The growth factor drops from 10,000 to 1 and the backward error drops by four orders of magnitude. That row swap is the whole argument for partial pivoting, and Wilkinson is the one who proved why it works.

---

## Full Worked Example

We solve this system on a machine that keeps only **3 significant digits**, the kind of precision early computers had:

```
0.0001·x₁ + 1·x₂ = 1
     1·x₁ + 1·x₂ = 2
```

The true answer is `x₁ = 1.0001`, `x₂ = 0.9999` (about `[1, 1]`).

### Attempt 1 — Gaussian elimination, no pivoting

Use the top-left entry `0.0001` as the pivot. The multiplier for row 2 is:

```
m = 1 / 0.0001 = 10000
```

Subtract `m × row 1` from row 2, rounding each result to 3 digits:

```
new a₂₂ = 1 - 10000·1 = 1 - 10000 = -9999  →  round to 3 digits  →  -10000
new b₂  = 2 - 10000·1 = 2 - 10000 = -9998  →  round to 3 digits  →  -10000
```

Look at what just happened. The real values were `-9999` and `-9998`. The original `1`s in row 2 mattered, but next to `10000` they fall off the end of a 3-digit word. They are gone.

Back-substitute:

```
x₂ = -10000 / -10000 = 1
x₁ = (1 - 1·1) / 0.0001 = 0 / 0.0001 = 0
```

Computed answer: `x = [0, 1]`. The true `x₁` is about `1`. We got `0`. The answer is **completely wrong**.

Now the backward question. What system did `[0, 1]` solve exactly? Compute the residual:

```
r = b - A·x
r₁ = 1 - (0.0001·0 + 1·1) = 1 - 1 = 0
r₂ = 2 - (1·0     + 1·1) = 2 - 1 = 1
r = [0, 1]
```

So `[0, 1]` is the exact solution of `A·x = b - [0, 1] = [1, 1]`. We asked for the right-hand side `[1, 2]` and the algorithm effectively answered a problem with right-hand side `[1, 1]`. That is a **huge** change to the data. Backward error ≈ `||r|| / (||A||·||x||) = 1 / (2·1) = 0.5`. The algorithm rewrote the problem. It was **unstable**.

The culprit is the **growth factor**: the entries grew from a max of `1` to a max of `10000`, a growth factor of 10,000. The tiny pivot forced a giant multiplier, the giant multiplier wiped out the real data, and 3 digits could not hold both scales at once.

### Attempt 2 — same system, partial pivoting

Partial pivoting picks the largest entry in the current column as the pivot. In column 1, `|1| > |0.0001|`, so swap the rows first:

```
1·x₁ + 1·x₂ = 2          (was row 2)
0.0001·x₁ + 1·x₂ = 1     (was row 1)
```

Now the multiplier is small:

```
m = 0.0001 / 1 = 0.0001
```

Eliminate, rounding to 3 digits:

```
new a₂₂ = 1 - 0.0001·1 = 1 - 0.0001 = 0.9999  →  round to 3 digits  →  1
new b₂  = 1 - 0.0001·2 = 1 - 0.0002 = 0.9998  →  round to 3 digits  →  1
```

This time the rounding only trims the *fifth* digit. The important information survives. Back-substitute:

```
x₂ = 1 / 1 = 1
x₁ = (2 - 1·1) / 1 = 1
```

Computed answer: `x = [1, 1]`. The true answer is `[1.0001, 0.9999]`. Forward error ≈ `0.0001`. Almost perfect.

Backward check:

```
r = b - A·x = [1, 2] - [0.0001·1 + 1·1, 1·1 + 1·1] = [1, 2] - [1.0001, 2] = [-0.0001, 0]
```

`[1, 1]` is the exact solution of a system whose data was nudged by `0.0001`. Backward error ≈ `0.0001 / (2·1) = 5e-5`. The algorithm barely touched the problem. It was **stable**. The growth factor is `1`.

### The lesson

Both attempts used identical arithmetic and identical precision. The unstable one let the entries grow by 10,000×; the stable one kept them at their original scale. Wilkinson's contribution was proving, in general, that the backward error of Gaussian elimination is bounded by the unit roundoff times this growth factor, and that partial pivoting keeps the growth factor small. The fear of rounding error did not need a better machine. It needed a row swap and a proof.

---

## ELI5

Imagine you have a tiny calculator that can only show three numbers at a time. You want to share 2 cookies fairly using a recipe.

You follow the recipe one way and your calculator runs out of room. The big numbers push the small numbers off the screen, and your answer comes out as "give the first kid zero cookies." That is clearly wrong.

So you try the recipe in a smarter order. You do the big step first, while there is still room, and then the small step. Now nothing falls off the screen. Your answer comes out right.

Same calculator. Same cookies. The only thing that changed was the order you did the steps in. A man named James Wilkinson figured out the right order, and he proved that with that order your little calculator can be trusted even for very big recipes.

---

## ELI10

In the 1940s and 50s, computers worked with numbers that had only a handful of digits. Every time the machine multiplied or subtracted, it had to round the answer to fit, the way your calculator rounds `1/3` to `0.333`. Solving a big set of equations takes thousands of these rounded steps. So mathematicians were scared. They thought all those little rounding errors would add up into one giant error, and that the answer to a system of fifty or a hundred equations would be useless noise.

James Wilkinson had actually used these machines. He worked at Britain's National Physical Laboratory, right next to Alan Turing, building one of the first computers, the Pilot ACE. He had hand-solved systems of equations during the war and noticed something odd: the answers were far better than the gloomy theory predicted. He wanted to know why.

His big idea was to stop asking "how far is my answer from the perfect answer?" That question is hard and often scary. Instead he asked "is my answer the *perfect* answer to a question *almost identical* to the one I asked?" If you wanted to solve a system and your computed answer is the exact solution to a system that differs from yours by a hair, then your algorithm did a great job. Any leftover error is the fault of the question being touchy, not the method being bad. He called this looking at the error "backward," and he proved that the standard method for solving equations, Gaussian elimination, is trustworthy this way as long as you do the steps in the right order (a trick called pivoting). One number, the "growth factor," tells you whether you are safe.

That single shift in perspective rescued numerical computing. It turned a field full of pessimism into one with solid guarantees, and the same idea now sits underneath the math libraries that run on every machine, from your laptop to the GPUs training large AI models.

---

## CS Graduate Level — Backward Error Analysis

### 1. The state of the art before (late 1940s)

The model for finite-precision arithmetic was understood: each floating-point operation produces the true result times `(1 + δ)` with `|δ| ≤ u`, where `u` is the unit roundoff. The open problem was what those per-operation errors did *in aggregate* over a long computation.

The dominant technique was **forward error analysis**: bound the difference between each computed intermediate and its exact counterpart, then propagate those bounds forward through the algorithm. For Gaussian elimination on an `n × n` matrix this produced bounds that grew like a high power of `n`. The famous conclusion, associated with Hotelling's 1943 analysis, was that the error could grow by a factor on the order of `4ⁿ`, implying that solving even moderately sized systems was hopeless. Practitioners on real machines kept getting good answers anyway. The theory and the practice disagreed, and nobody could explain the gap.

### 2. What was technically new

Wilkinson's reframing was **backward error analysis**. Rather than bounding how far the computed solution `x̂` is from the exact solution `x`, he showed that `x̂` is the *exact* solution of a perturbed system:

```
(A + E) x̂ = b,     with E small.
```

The question becomes: how small is `E`? If `‖E‖ / ‖A‖` is on the order of the unit roundoff, the algorithm is **backward stable** — it has done as well as could be hoped given the precision of the machine, because the input `A` itself was only known to that precision in the first place.

This decouples two things people had been conflating:

```
relative forward error   ≤   κ(A)  ×   relative backward error
   (how wrong x̂ is)        (condition  (how much the algorithm
                            number)      perturbed the problem)
```

A large forward error can now have two distinct causes: a large backward error (the algorithm is bad) or a large condition number `κ(A)` (the problem is intrinsically sensitive). Gaussian elimination has the first under control, so any remaining inaccuracy is the problem's fault, not the method's. That sentence is the entire shift.

### 3. How the analysis works (Gaussian elimination)

The key quantity is the **growth factor**:

```
ρ = ( max over all steps k of |a_ij^(k)| ) / ( max |a_ij| in the original A )
```

Wilkinson proved that the backward error of Gaussian elimination satisfies a bound of the form:

```
‖E‖∞  ≤  c · n · ρ · u · ‖A‖∞
```

for a small constant `c`. Everything except `ρ` is benign: `n` is modest polynomial growth, `u` is the machine precision. **All the danger lives in `ρ`.**

Without pivoting, `ρ` can be enormous. A tiny pivot forces a large multiplier `m = a_ik / a_kk`, the update `a_ij - m·a_kj` produces large intermediate entries, and finite precision loses the original data — exactly the `0.0001` example in the worked section, where `ρ = 10⁴`.

**Partial pivoting** chooses the largest-magnitude entry in the current column as the pivot, which forces every multiplier to satisfy `|m| ≤ 1`. With multipliers bounded by 1, the entries can at most double at each of the `n-1` steps:

```
ρ ≤ 2^(n-1)
```

That worst case is exponential, but it is attainable only by pathological matrices (the "Wilkinson matrix" with `±1` structure). For essentially every matrix arising in practice, `ρ` is a small constant, often below 10 even for large `n`. This is the gap between theory and practice resolved: Gaussian elimination with partial pivoting is backward stable in practice, and the growth factor is the precise object that tells you so.

### 4. A worked instance of the bound

Take the worked example, `A = [[0.0001, 1], [1, 1]]`, 3 significant digits (`u ≈ 5·10⁻³`):

| | no pivoting | partial pivoting |
|---|---|---|
| growth factor `ρ` | 10⁴ | 1 |
| backward error `‖r‖/(‖A‖‖x‖)` | 0.5 | 5·10⁻⁵ |
| forward error | 1.0 | 10⁻⁴ |
| condition number `κ(A)` | ≈ 4 | ≈ 4 |

Note `κ(A) ≈ 4` is *small* — the problem is well-conditioned, so a good algorithm should return a good answer. Without pivoting it does not, and the backward error of 0.5 correctly flags the algorithm (not the problem) as the culprit. With pivoting the backward error drops to roundoff level and `forward ≤ κ · backward` holds: `10⁻⁴ ≤ 4 · 5·10⁻⁵ = 2·10⁻⁴`. The bound diagnoses exactly what went wrong and exactly why the fix works.

### 5. What descended from it

- **The IEEE 754 standard (1985)** assumes the rounding model `fl(a op b) = (a op b)(1 + δ)` that backward error analysis is built on. Every guarantee about a floating-point library is stated in backward-error terms.
- **LAPACK and BLAS**, the reference numerical libraries underneath NumPy, SciPy, MATLAB, R, and every scientific computing stack, ship backward-error bounds for their routines. `dgesv` (the LU solver) is documented as backward stable; that documentation is Wilkinson's theorem.
- **Iterative refinement** uses the residual `r = b - A x̂` (the backward-error object itself) to cheaply recover lost digits, and is the basis of modern *mixed-precision* solvers that run the bulk of the work in low precision (fp16/bf16 on GPU tensor cores) and refine in higher precision. This is how Top500 supercomputers and large-model training pipelines get speed without sacrificing accuracy.
- **The condition number** became the standard separator of "hard problem" from "bad algorithm" across all of numerical analysis, optimization, and machine learning (e.g. the conditioning of the Hessian governing gradient-descent convergence).

### 6. Lasting impact

Backward error analysis is the reason we trust floating-point computation at all. It replaced a fog of pessimism with a clean, provable criterion: an algorithm is good if it solves a nearby problem exactly, and you measure that with the residual. Wilkinson packaged the technique, the growth-factor analysis of Gaussian elimination, and a generation's worth of worked examples into two books — *Rounding Errors in Algebraic Processes* (1963) and *The Algebraic Eigenvalue Problem* (1965) — that taught the field how to think. Every numerical library written since is, in effect, a footnote to that work.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [Error Analysis of Floating-Point Computation](https://doi.org/10.1007/BF01386233) | Numerische Mathematik | 1960 |
| [Error Analysis of Direct Methods of Matrix Inversion](https://doi.org/10.1145/321075.321076) | Journal of the ACM | 1961 |
| [Rounding Errors in Algebraic Processes](https://archive.org/details/roundingerrorsin0000wilk) *(book)* | Prentice-Hall / HMSO | 1963 |
| [The Algebraic Eigenvalue Problem](https://global.oup.com/academic/product/the-algebraic-eigenvalue-problem-9780198534181) *(book)* | Oxford University Press | 1965 |
| [Some Comments from a Numerical Analyst](https://doi.org/10.1145/1283920.1283925) *(Turing Award lecture)* | Journal of the ACM | 1971 |

---

*Previous: [Week 04 — Marvin Minsky (1969)](../04-marvin-minsky-1969/)*

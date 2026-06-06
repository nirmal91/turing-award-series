# Week 05 — James H. Wilkinson (1970)

**ACM Turing Award citation:** *"For his research in numerical analysis to facilitate the use of the high-speed digital computer, having received special recognition for his work in computations in linear algebra and 'backward' error analysis."*

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — sum five numbers on a 4-digit machine, then show the computed answer is the exact sum of the same numbers each nudged by a tiny amount.

[`implementation.py`](./implementation.py) — a finite-precision machine (built on `decimal`) used to demonstrate backward error analysis on two classic problems:

```
inputs + chosen precision (significant digits)
    ↓
finite-precision machine  (rounds every operation to `digits` figures)
    ↓
  ├─ summation  → forward error (how wrong)  vs  backward error (nudge to inputs)
  └─ quadratic  → naive formula (cancellation) vs stable formula (c/q)
    ↓
backward error = size of the smallest input perturbation that makes
                 the computed answer exactly correct
```

What it supports:
- Sum any list of numbers at any precision and recover the exact per-input perturbations `delta_i` such that `computed = sum(x_i * (1 + delta_i))`
- Solve any quadratic two ways and compare their backward errors
- Measure the backward error of any candidate root (normalized residual)

```bash
python3 concept.py                      # the core idea, plain
python3 implementation.py               # demo, then an interactive REPL
python3 implementation.py --test        # test suite (16 cases)
python3 implementation.py --verbose     # show per-step rounding and perturbations
```

Example session:

```
[1] Summing ['1', '0.0001', '0.0001', '0.0001', '0.0001']  on a 4-digit machine
    exact sum     = 1.0004
    computed sum  = 1.000   (the small terms 'vanished')
    FORWARD error = 0.0004   <- looks like data was lost
    BACKWARD view: computed sum is the exact sum of inputs each
                   perturbed by at most 4.0e-4 (bound (n-1)u = 2.0e-3)

[2] Solving x^2 - 100000 x + 1 = 0  on a 6-digit machine
    true roots:        1e-05   and  100000
    naive  small root: 0   (backward error 1.0e+0)  UNSTABLE
    stable small root: 1e-05   (backward error 5.0e-11)  stable
```

The REPL lets you try your own:

```
wilkinson> quad 6 1 -100000 1
  true   roots: 1e-05, 100000
  naive  roots: 0, 100000  (backward error 1.0e+0)
  stable roots: 1e-05, 100000  (backward error 5.0e-11)
```

---

## Full Worked Example

Two algorithms run on the same toy machine. The first shows what backward error analysis *is*. The second shows why it changes which algorithm you pick.

### Part A — Summation on a 4-digit machine

The machine keeps 4 significant figures after every operation. Unit roundoff is `u = 0.5 x 10^(1-4) = 5e-4`: the most any single rounding can change a number, relative to its size.

Inputs: `1, 0.0001, 0.0001, 0.0001, 0.0001`. The exact sum is `1.0004`.

**Step 1 — run the sum left to right, rounding each partial sum to 4 figures.**

```
s1 = 1
s2 = fl(1      + 0.0001) = fl(1.0001) = 1.000   (5th figure dropped)
s3 = fl(1.000  + 0.0001) = fl(1.0001) = 1.000
s4 = fl(1.000  + 0.0001) = fl(1.0001) = 1.000
s5 = fl(1.000  + 0.0001) = fl(1.0001) = 1.000
```

Computed sum = `1.000`. The four small terms never survived a single rounding.

**Step 2 — forward error.** How far is the answer from the truth?

```
forward error = |1.000 - 1.0004| = 0.0004
```

In a forward-error worldview you stop here and panic: the small terms were lost, and a longer list would lose more.

**Step 3 — name the rounding error at each step.** Each addition rounded, so write `s_j = (s_{j-1} + x_j)(1 + eps_j)` and solve for `eps_j` exactly:

```
eps_2 = 1.000 / (1     + 0.0001) - 1 = 1.000 / 1.0001 - 1 = -9.999e-5
eps_3 = 1.000 / (1.000 + 0.0001) - 1 =                      -9.999e-5
eps_4 = -9.999e-5
eps_5 = -9.999e-5
```

Every step error is about `1e-4` — comfortably below `u`. That is the whole point: a single rounding is always small. The fear was that *many* of them compound into something large.

**Step 4 — push the errors back onto the inputs.** Expand the recurrence. `x1` rode through all four roundings, `x2` also through all four (it joined at step 2), `x3` through three, and so on. Collect the factors:

```
1 + delta_0 (x1)  = (1+eps_2)(1+eps_3)(1+eps_4)(1+eps_5)  -> delta_0 = -3.999e-4
1 + delta_1 (x2)  = (1+eps_2)(1+eps_3)(1+eps_4)(1+eps_5)  -> delta_1 = -3.999e-4
1 + delta_2 (x3)  =          (1+eps_3)(1+eps_4)(1+eps_5)  -> delta_2 = -2.999e-4
1 + delta_3 (x4)  =                   (1+eps_4)(1+eps_5)  -> delta_3 = -2.000e-4
1 + delta_4 (x5)  =                            (1+eps_5)  -> delta_4 = -9.999e-5
```

**Step 5 — check the claim.** The computed answer should be the *exact* sum of the perturbed inputs:

```
1*(1 - 3.999e-4) + 0.0001*(1 - 3.999e-4) + 0.0001*(1 - 2.999e-4)
  + 0.0001*(1 - 2.000e-4) + 0.0001*(1 - 9.999e-5)  =  1.000
```

It matches `1.000` to 50+ digits. No approximation — an identity.

**The reframing.** The forward error said "you lost 0.0004." The backward error says "you computed the exact sum of five numbers, each within 0.04% of the ones you gave me." The largest nudge is `4e-4`, under the bound `(n-1)u = 4 x 5e-4 = 2e-3`. If you don't know your inputs to better than 0.04% — and you almost never do — the algorithm gave you a perfect answer to a question indistinguishable from yours.

### Part B — Same machine, a problem where the algorithm matters

Solve `x^2 - 100000 x + 1 = 0` on a 6-figure machine. The true roots are `100000` (almost exactly) and `0.00001`.

**The discriminant.** `b^2 - 4ac = 10000000000 - 4 = 9999999996`. Rounded to 6 figures this is `1.00000e10`, and the `-4` is gone. `sqrt(1.00000e10) = 100000` exactly.

**Naive formula** `x = (-b +/- sqrt) / 2a`:

```
large root = (100000 + 100000) / 2 = 100000        fine
small root = (100000 - 100000) / 2 = 0 / 2 = 0      catastrophic cancellation
```

Two numbers equal to 6 figures were subtracted. Every surviving figure cancelled, leaving `0`. The computed small root is `0` — 100% wrong.

**Backward error of that root.** Plug `r = 0` back in: residual `= |0 - 0 + 1| = 1`. Normalized, the backward error is `1.0` — to make `0` an exact root you would have to throw away the entire constant term. The algorithm did not solve a nearby problem. It solved a completely different one.

**Stable formula.** Never subtract the near-equal pair. Form `q` with an addition, then get the second root from the product relation `x1 * x2 = c/a`:

```
sign(b) = -1                       (b is negative)
q  = -(b + sign(b)*sqrt) / 2 = -(-100000 + (-1)*100000)/2 = -(-200000)/2 = 100000
x1 = q / a = 100000
x2 = c / q = 1 / 100000 = 0.00001
```

**Backward error of the stable root.** Plug `r = 0.00001` back in: residual `= |1e-10 - 1 + 1| = 1e-10`, normalized to about `5e-11` — the level of unit roundoff. Backward stable.

Same hardware, same problem, two algorithms. One is useless and one is exact, and backward error is the single number that tells them apart *before* you ever know the true answer.

---

## ELI5

Imagine you add up a big pile of coins on a calculator that only shows a few digits. At the end the calculator says `1.000` dollars, but you actually had `1.0004`. It looks like the calculator ate four of your pennies.

Before Wilkinson, people stared at that missing `0.0004` and decided calculators could not be trusted for big sums.

Wilkinson turned the question around. He said: the calculator did not make a mistake adding *your* coins. It added a pile of coins that is almost exactly yours, just a tiny sliver different, and it added *that* pile perfectly. The sliver is smaller than a speck of dust on the coins. So the answer is as good as the coins were to begin with. The calculator was honest. You just could not see the dust either.

---

## ELI10

In the 1940s and 50s, computers were new and people were scared of them for math. A long calculation does thousands of tiny roundings, one after another, and the worry was that these errors pile up. The accepted way to measure the danger was the "forward error": how far is the computer's answer from the true answer? When you worked out the worst case, the bound grew so fast that it suggested solving a big system of equations was hopeless. Some respected mathematicians said exactly that.

James Wilkinson had a rare vantage point. In the late 1940s he worked with Alan Turing at Britain's National Physical Laboratory building the Pilot ACE, one of the first real computers. He ran enormous calculations on it by hand and by machine, and he noticed something. The answers were far better than the gloomy forward-error bounds promised. The bounds were not wrong, they were just asking the wrong question.

His idea was to ask it backward. Don't ask how wrong the answer is. Ask: for what slightly different *input* would this answer be exactly right? It turns out that when a computer adds a list of numbers, the result it gives is the perfectly exact sum of the same numbers each changed by a hair, far less than a hair you would even notice in real measured data. The rounding doesn't pile up into garbage. It hides inside a tiny, harmless change to the input.

This split numerical analysis cleanly in two. Backward error measures the algorithm: did it solve a nearby problem? Conditioning measures the problem itself: are nearby problems even close to each other? Once Wilkinson proved that good algorithms like Gaussian elimination are "backward stable," people stopped fearing the machine and started trusting it. Every scientific simulation, weather model, and engineering solver running today rests on that confidence.

---

## CS Graduate Level — Why Backward Error Analysis Mattered

### 1. The State of the Art Before (1940s–1950s)

Floating-point arithmetic was understood at the level of a single operation: the result of `a op b` is the true value times `(1 + delta)` with `|delta| <= u`, where `u` is the unit roundoff. The open problem was *composition*. A real computation chains thousands of these operations, and the natural analysis was **forward**: bound the error of each step, then propagate those bounds through the computation.

Forward bounds compound multiplicatively. For Gaussian elimination on an `n x n` system the naive forward bound grows like a high power of `n` times the roundoff, large enough that it implied 100x100 systems would return noise. Hotelling published such a pessimistic analysis in 1943. The bounds were correct as worst-case statements and almost never observed in practice, which left a gap between theory and the machines that were plainly producing useful answers.

### 2. Wilkinson's Insight

Wilkinson inverted the question. Rather than bounding `||computed - exact||` directly (the forward error), he sought the smallest perturbation `E` to the **inputs** such that the computed result is the *exact* result for the perturbed inputs:

```
computed = solve(input + E)         find the smallest such E
```

`||E||` is the **backward error**. An algorithm is **backward stable** if `||E||` is of order `u` (unit roundoff) for every input. This separates two concerns that forward error tangles together:

- **Backward error** is a property of the *algorithm*: did it solve a problem close to the one posed?
- **Condition number** `kappa` is a property of the *problem*: how much does the exact answer move when the input moves?

They combine in the single most useful inequality in the field:

```
relative forward error   <=   kappa   x   relative backward error
```

A backward-stable algorithm contributes the minimum possible backward error. Whatever inaccuracy remains is the problem's fault (large `kappa`), not the algorithm's. You can no longer blame the computer for an ill-conditioned problem, and you can no longer excuse a bad algorithm on a well-conditioned one.

### 3. How It Works — Summation

Summing `x_1, ..., x_n` left to right with `s_j = fl(s_{j-1} + x_j)` introduces a relative error `eps_j` at each step, `|eps_j| <= u`. Unrolling the recurrence:

```
computed_sum = sum_i  x_i * prod_{j>=i} (1 + eps_j)  =  sum_i  x_i (1 + delta_i)
```

with `|delta_i| <= (n-1)u / (1 - (n-1)u) ~ (n-1)u`. The computed sum is the **exact** sum of slightly perturbed inputs. `implementation.py` recovers the actual `delta_i` for any input and verifies the identity to full precision — the reconstruction residual is `0`. This is the prototype for every backward analysis: convert accumulated rounding into a small perturbation of the data.

### 4. How It Works — Catastrophic Cancellation and the Quadratic

Backward stability is a property of the algorithm, and the quadratic formula proves two algorithms for one problem can differ wildly. For `ax^2 + bx + c = 0` with `b^2 >> 4ac`, the naive root `(-b + sign(b)·sqrt(b^2-4ac)) / 2a` subtracts two nearly equal quantities. Cancellation does not create a large *rounding* error — the subtraction itself is exact — but it exposes earlier rounding in the operands, destroying every significant figure. The backward error of the resulting root is `O(1)`.

The stable formulation computes `q = -(b + sign(b)·sqrt(b^2-4ac)) / 2` (an addition of same-sign quantities, no cancellation), then takes `x_1 = q/a` and `x_2 = c/q` from `x_1 x_2 = c/a`. Backward error returns to `O(u)`. The problem's conditioning is identical in both cases; only the algorithm changed. `implementation.py` reports backward error `1.0` for the naive small root and `~5e-11` for the stable one on `x^2 - 100000x + 1 = 0`.

### 5. Gaussian Elimination and the Growth Factor

Wilkinson's landmark result (1961) was the backward error analysis of Gaussian elimination with partial pivoting. The computed solution `x̂` of `Ax = b` is the exact solution of `(A + E)x̂ = b` with

```
||E||_inf  <=  c · n · rho · u · ||A||_inf
```

where `rho` is the **growth factor**, the largest magnitude any matrix entry reaches during elimination relative to the original. Partial pivoting bounds `rho <= 2^(n-1)` in the worst case, but Wilkinson observed that in practice `rho` is almost always `O(n)` or smaller. This is why Gaussian elimination — the algorithm the 1943 forward analysis declared hopeless — is in fact backward stable for essentially all matrices encountered in practice. He had explained the gap between the pessimistic theory and the working machines.

### 6. The Wilkinson Polynomial — Conditioning Made Visceral

To show that conditioning is real and separate from algorithm quality, Wilkinson studied `w(x) = (x-1)(x-2)...(x-20)`, whose roots are the integers 1 through 20. Expanding to coefficient form and perturbing the coefficient of `x^19` by `2^-23` (a change in roughly the 7th significant figure) moves the roots dramatically: several pairs collide and split off the real axis into complex conjugates, with root 19 shifting by around `0.8`. No algorithm error is involved — the *problem* of recovering roots from coefficients is catastrophically ill-conditioned. Wilkinson called it "the most traumatic experience in my career as a numerical analyst." It is the canonical example of a large condition number, the other half of the `forward <= kappa x backward` story.

### 7. What Descended From It

**The EISPACK / LINPACK / LAPACK lineage.** Wilkinson and Reinsch's *Handbook for Automatic Computation* (1971) collected backward-stable algorithms (notably the QR algorithm for eigenvalues, and the algorithms behind the `eig`/`\` you call today) into reference implementations. EISPACK and LINPACK in the 1970s and LAPACK in the 1990s carried them into the libraries underneath MATLAB, NumPy, SciPy, R, and Julia. When you call a linear solver, you are running code whose correctness argument is a Wilkinson-style backward error bound.

**IEEE 754 (1985).** The standard that fixed floating-point behavior was designed by people (William Kahan foremost) steeped in this framework. The `(1 + delta)` model with a guaranteed `u`, correctly rounded operations, and a meaningful `sqrt` are exactly the primitives backward error analysis assumes. Reproducible, analyzable arithmetic is a direct consequence of taking Wilkinson's program seriously.

**Numerical stability as standard vocabulary.** "Backward stable," "condition number," and "growth factor" are now first-week terms in any numerical methods course. The discipline of proving an algorithm correct by exhibiting a small backward perturbation — rather than by chasing forward bounds — is the default method, used today to analyze everything from FFTs to the mixed-precision matrix multiplies inside deep-learning accelerators.

### 8. Lasting Impact

Modern hardware has made the split more relevant, not less. GPUs train models in `bfloat16` and `fp8`, where `u` is enormous (around `4e-3` for fp8). The only reason such low precision works is that the underlying operations are backward stable: each rounded matmul is the exact product of slightly perturbed weights, and the perturbation stays bounded as long as the network is not pathologically conditioned. The vocabulary Wilkinson built in the 1960s to defend room-sized computers is what justifies the numerics of the H100s and TPUs training frontier models. The question never changed: not "how wrong is the answer," but "how nearby is the problem I actually solved."

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [Rounding Errors in Algebraic Processes](https://epubs.siam.org/doi/book/10.1137/1.9781611977523) | HMSO / Prentice-Hall (repr. SIAM) | 1963 |
| [Error Analysis of Direct Methods of Matrix Inversion](https://doi.org/10.1145/321075.321076) | Journal of the ACM | 1961 |
| [The Algebraic Eigenvalue Problem](https://global.oup.com/academic/product/the-algebraic-eigenvalue-problem-9780198534181) | Oxford University Press | 1965 |
| [Handbook for Automatic Computation, Vol. II: Linear Algebra](https://doi.org/10.1007/978-3-642-86940-2) *(with C. Reinsch)* | Springer | 1971 |
| [The Perfidious Polynomial](https://www.jstor.org/stable/2689134) *(studies in numerical analysis, ed. G. H. Golub)* | MAA | 1984 |

---

*Previous: [Week 04 — Marvin Minsky (1969)](../04-marvin-minsky-1969/)*

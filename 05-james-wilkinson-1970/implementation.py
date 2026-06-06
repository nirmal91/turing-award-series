"""
Backward error analysis — full implementation (J. H. Wilkinson, 1960s)

Usage:
    python implementation.py               # interactive demo + REPL
    python implementation.py --test        # test suite (16 cases)
    python implementation.py --verbose     # show the per-step rounding errors

Before Wilkinson: error was judged by FORWARD analysis — bound how far the
computed answer drifts from the true answer. For a chain of n operations the
bounds grew so fast they implied that large computations (e.g. solving a 100x100
linear system) were hopeless. People genuinely distrusted the machines.

After Wilkinson: BACKWARD analysis. Show that the computed answer is the EXACT
answer to a slightly perturbed problem. If the perturbation is no larger than
the uncertainty already in the input data, the algorithm is "backward stable"
and there is nothing more to ask of it. Whatever inaccuracy remains belongs to
the PROBLEM (its conditioning), not the algorithm.

    forward error   <=   condition number   x   backward error
    (how wrong)          (property of problem)   (property of algorithm)

This file models a finite-precision machine with `decimal` (configurable number
of significant digits per operation) and uses it to demonstrate both ideas:
  1. Summation: the computed sum is exactly sum(x_i * (1 + delta_i)), all delta_i tiny.
  2. The quadratic formula: two algorithms for the SAME problem, one backward
     stable, one not — proof that accuracy is about the algorithm, not the machine.
"""

import sys
from decimal import Decimal, localcontext

EXACT_PREC = 60   # "infinite precision" reference for measuring errors


# ── A finite-precision machine ─────────────────────────────────────────────────
#
# Real hardware rounds every result to a fixed number of significant binary
# digits. We model the same thing in decimal: each operation is carried out, then
# rounded to `digits` significant figures. The unit roundoff u is the largest
# relative error a single rounding can introduce: u = 0.5 * 10^(1-digits).

def unit_roundoff(digits):
    return Decimal(5) * Decimal(10) ** (-digits)


def to_dec(x):
    return x if isinstance(x, Decimal) else Decimal(str(x))


# ── 1. Summation, with backward error analysis ─────────────────────────────────
#
# Summing left to right: s_1 = x_1, s_j = fl(s_{j-1} + x_j).
# Each step rounds, so s_j = (s_{j-1} + x_j)(1 + eps_j) with |eps_j| <= u.
# Expanding the recurrence, the final computed sum equals
#       sum_i  x_i * (1 + delta_i),
# i.e. the EXACT sum of inputs each perturbed by a relative amount delta_i.
# The standard bound is |delta_i| <= (n-1)u / (1 - (n-1)u) ~ (n-1)u.

def sum_backward(xs, digits):
    xs = [to_dec(x) for x in xs]
    n = len(xs)

    with localcontext() as ctx:                 # the finite-precision machine
        ctx.prec = digits
        partials = [+xs[0]]
        for x in xs[1:]:
            partials.append(partials[-1] + x)
    computed = partials[-1]

    with localcontext() as ctx:                 # exact reference + analysis
        ctx.prec = EXACT_PREC
        exact = sum(xs[1:], xs[0])
        eps = [partials[j] / (partials[j - 1] + xs[j]) - 1 for j in range(1, n)]
        deltas = []
        for i in range(n):
            prod = Decimal(1)
            start = 1 if i == 0 else i           # x[0],x[1] pass through every step
            for k in range(start, n):
                prod *= (1 + eps[k - 1])
            deltas.append(prod - 1)
        reconstructed = sum((xs[i] * (1 + deltas[i]) for i in range(n)), Decimal(0))

    return {
        "computed": computed,
        "exact": exact,
        "forward_error": abs(computed - exact),
        "rel_forward_error": abs(computed - exact) / abs(exact) if exact != 0 else Decimal(0),
        "deltas": deltas,
        "eps": eps,
        "max_backward": max(abs(d) for d in deltas),
        "reconstruction_residual": abs(reconstructed - computed),
        "bound": (n - 1) * unit_roundoff(digits),
    }


# ── 2. The quadratic formula: stable vs unstable ───────────────────────────────
#
# Solve a*x^2 + b*x + c = 0 on the finite-precision machine.
#
# Naive: x = (-b +/- sqrt(b^2 - 4ac)) / 2a. When b^2 >> 4ac, one root is computed
#   as the difference of two nearly equal numbers — catastrophic cancellation.
#   The computed root can be 100% wrong even though the problem is well behaved.
#
# Stable: form  q = -(b + sign(b)*sqrt(b^2-4ac)) / 2  (an ADDITION, never a
#   cancelling subtraction), then x1 = q/a and x2 = c/q (from x1*x2 = c/a).
#   This is the textbook backward-stable formulation.

def _sqrt_disc(a, b, c):
    return (b * b - 4 * a * c).sqrt()


def quadratic_naive(a, b, c, digits):
    a, b, c = to_dec(a), to_dec(b), to_dec(c)
    with localcontext() as ctx:
        ctx.prec = digits
        sq = _sqrt_disc(a, b, c)
        r1 = (-b + sq) / (2 * a)
        r2 = (-b - sq) / (2 * a)
    return sorted([r1, r2])


def quadratic_stable(a, b, c, digits):
    a, b, c = to_dec(a), to_dec(b), to_dec(c)
    with localcontext() as ctx:
        ctx.prec = digits
        sq = _sqrt_disc(a, b, c)
        sign = Decimal(1) if b >= 0 else Decimal(-1)
        q = -(b + sign * sq) / 2
        r1 = q / a
        r2 = c / q
    return sorted([r1, r2])


def root_backward_error(a, b, c, root):
    """
    Relative backward error of a computed root: the size of the smallest
    coefficient perturbation for which `root` is an EXACT root. Equal to the
    normalized residual |a r^2 + b r + c| / (|a|r^2 + |b||r| + |c|).
    A backward-stable algorithm returns roots with backward error ~ u.
    """
    a, b, c, r = to_dec(a), to_dec(b), to_dec(c), to_dec(root)
    with localcontext() as ctx:
        ctx.prec = EXACT_PREC
        residual = abs(a * r * r + b * r + c)
        scale = abs(a) * r * r + abs(b) * abs(r) + abs(c)
        return residual / scale if scale != 0 else Decimal(0)


def true_roots(a, b, c):
    a, b, c = to_dec(a), to_dec(b), to_dec(c)
    with localcontext() as ctx:
        ctx.prec = EXACT_PREC
        sq = _sqrt_disc(a, b, c)
        return sorted([(-b + sq) / (2 * a), (-b - sq) / (2 * a)])


# ── Demo ────────────────────────────────────────────────────────────────────────

def demo(verbose=False):
    print("Backward error analysis — J. H. Wilkinson (1970 Turing Award)")
    print("=" * 64)
    print("Question Wilkinson asked: not 'how wrong is my answer' but")
    print("'for what nearby INPUT is my answer exactly right?'\n")

    # --- Summation -------------------------------------------------------------
    digits = 4
    xs = [Decimal("1"), Decimal("0.0001"), Decimal("0.0001"),
          Decimal("0.0001"), Decimal("0.0001")]
    r = sum_backward(xs, digits)
    print(f"[1] Summing {[str(x) for x in xs]}  on a {digits}-digit machine")
    print(f"    exact sum     = {r['exact']}")
    print(f"    computed sum  = {r['computed']}   (the small terms 'vanished')")
    print(f"    FORWARD error = {r['forward_error']}   <- looks like data was lost")
    print(f"    BACKWARD view: computed sum is the exact sum of inputs each")
    print(f"                   perturbed by at most {r['max_backward']:.1e} "
          f"(bound (n-1)u = {r['bound']:.1e})")
    if verbose:
        print("    per-step rounding errors eps_j:")
        for j, e in enumerate(r["eps"], start=2):
            print(f"        step {j}: eps = {e:+.3e}")
        print("    per-input backward perturbations delta_i:")
        for i, d in enumerate(r["deltas"]):
            print(f"        x{i}: delta = {d:+.3e}")
        print(f"    reconstruction residual = {r['reconstruction_residual']:.0e} (exact match)")
    print("    Lesson: the answer is the exact sum of data 0.04% from yours.")
    print("            If your data isn't known that well, nothing was lost.\n")

    # --- Quadratic: same problem, two algorithms -------------------------------
    a, b, c, digits = Decimal(1), Decimal(-100000), Decimal(1), 6
    tr = true_roots(a, b, c)
    naive = quadratic_naive(a, b, c, digits)
    stable = quadratic_stable(a, b, c, digits)
    print(f"[2] Solving x^2 - 100000 x + 1 = 0  on a {digits}-digit machine")
    print(f"    true roots:        {_fmt(tr[0])}   and  {_fmt(tr[1])}")
    print(f"    naive  small root: {_fmt(naive[0])}   "
          f"(backward error {root_backward_error(a, b, c, naive[0]):.1e})  UNSTABLE")
    print(f"    stable small root: {_fmt(stable[0])}   "
          f"(backward error {root_backward_error(a, b, c, stable[0]):.1e})  stable")
    if verbose:
        with localcontext() as ctx:
            ctx.prec = digits
            disc = (b * b - 4 * a * c)
            print(f"    discriminant b^2-4ac rounds {b*b} - {4*a*c} -> {disc}")
            print(f"    naive small root = (-b - sqrt)/2a subtracts two equal numbers")
            print(f"    stable small root = c/q avoids the subtraction entirely")
    print("    Lesson: same machine, same problem. The unstable algorithm reports")
    print("            a 100% wrong root; the stable one is exact to rounding.")
    print("            Accuracy is a property of the ALGORITHM, not the hardware.\n")

    print("forward error  <=  condition number  x  backward error")
    print("Wilkinson split every numerical question into those two pieces.")


def _fmt(d):
    """Compact fixed-ish formatting for Decimals."""
    return f"{float(d):.6g}"


# ── Interactive REPL ─────────────────────────────────────────────────────────────

REPL_HELP = """commands:
  sum <digits> <x1> <x2> ...     backward error analysis of summing the numbers
  quad <digits> <a> <b> <c>      solve a x^2 + b x + c = 0, naive vs stable
  help                           show this help
  quit                           exit
"""


def repl():
    print("\nInteractive backward-error explorer. Type 'help' for commands.\n")
    while True:
        try:
            line = input("wilkinson> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()
        try:
            if cmd in ("quit", "exit", "q"):
                return
            if cmd == "help":
                print(REPL_HELP)
            elif cmd == "sum":
                digits = int(parts[1])
                xs = [Decimal(p) for p in parts[2:]]
                r = sum_backward(xs, digits)
                print(f"  computed = {r['computed']}   exact = {r['exact']}")
                print(f"  relative forward error  = {r['rel_forward_error']:.3e}")
                print(f"  max backward error      = {r['max_backward']:.3e}  "
                      f"(bound {r['bound']:.3e})")
            elif cmd == "quad":
                digits = int(parts[1])
                a, b, c = (Decimal(parts[2]), Decimal(parts[3]), Decimal(parts[4]))
                naive = quadratic_naive(a, b, c, digits)
                stable = quadratic_stable(a, b, c, digits)
                tr = true_roots(a, b, c)
                print(f"  true   roots: {_fmt(tr[0])}, {_fmt(tr[1])}")
                print(f"  naive  roots: {_fmt(naive[0])}, {_fmt(naive[1])}  "
                      f"(backward error {max(root_backward_error(a,b,c,x) for x in naive):.1e})")
                print(f"  stable roots: {_fmt(stable[0])}, {_fmt(stable[1])}  "
                      f"(backward error {max(root_backward_error(a,b,c,x) for x in stable):.1e})")
            else:
                print(f"  unknown command: {cmd} (try 'help')")
        except (IndexError, ValueError) as e:
            print(f"  bad input: {e}")


# ── Test suite ────────────────────────────────────────────────────────────────

def run_tests():
    passed = failed = 0

    def check(name, got, expected):
        nonlocal passed, failed
        if got == expected:
            print(f"  PASS  {name}")
            passed += 1
        else:
            print(f"  FAIL  {name}: got {got!r}, expected {expected!r}")
            failed += 1

    u4 = unit_roundoff(4)

    # 1. Forward error is real: small terms are lost at 4 digits.
    r = sum_backward([Decimal("1")] + [Decimal("0.0001")] * 4, 4)
    check("summation loses small terms (forward error > 0)", r["forward_error"] > 0, True)

    # 2. The backward reconstruction is exact: computed == sum(x_i (1+delta_i)).
    check("summation reconstruction is exact", r["reconstruction_residual"] < Decimal("1e-40"), True)

    # 3. Backward error is tiny, even though forward error looked big.
    check("backward error is small (<= (n-1)u)", r["max_backward"] <= 4 * u4, True)

    # 4. Backward error obeys the (n-1)u bound for a longer, harder sum.
    r2 = sum_backward([Decimal("1")] + [Decimal("1e-6")] * 49, 5)
    check("backward error within (n-1)u bound", r2["max_backward"] <= r2["bound"], True)

    # 5. Exact-precision summation has zero forward error (sanity).
    r3 = sum_backward([Decimal("0.1"), Decimal("0.2"), Decimal("0.3")], 50)
    check("high precision: forward error ~ 0", r3["forward_error"] < Decimal("1e-40"), True)

    # 6. Adding numbers of the same magnitude is harmless (backward error ~ 0).
    r4 = sum_backward([Decimal("1000"), Decimal("2000"), Decimal("3000")], 6)
    check("nice sum has ~zero backward error", r4["max_backward"] < Decimal("1e-5"), True)

    # 7. Quadratic: true roots of x^2 - 100000x + 1 are ~100000 and ~1e-5.
    tr = true_roots(1, -100000, 1)
    check("true large root ~ 100000", abs(tr[1] - Decimal(100000)) < Decimal("1e-3"), True)
    check("true small root ~ 1e-5", abs(tr[0] - Decimal("0.00001")) < Decimal("1e-9"), True)

    # 8. Naive formula is UNSTABLE: the small root has large backward error.
    naive = quadratic_naive(1, -100000, 1, 6)
    be_naive = max(root_backward_error(1, -100000, 1, x) for x in naive)
    check("naive quadratic is backward-UNSTABLE (be > 0.01)", be_naive > Decimal("0.01"), True)

    # 9. Stable formula: backward error at the level of unit roundoff.
    stable = quadratic_stable(1, -100000, 1, 6)
    be_stable = max(root_backward_error(1, -100000, 1, x) for x in stable)
    check("stable quadratic is backward-stable (be < 1e-4)", be_stable < Decimal("1e-4"), True)

    # 10. Stable small root is accurate; naive small root is ruined by cancellation.
    check("stable small root accurate", abs(stable[0] - Decimal("0.00001")) < Decimal("1e-7"), True)
    check("naive small root inaccurate (cancellation)", abs(naive[0] - Decimal("0.00001")) > Decimal("1e-7"), True)

    # 11. Both formulas agree on the WELL-conditioned large root.
    check("naive and stable agree on large root", abs(naive[1] - stable[1]) < Decimal("1e-3"), True)

    # 12. A benign quadratic: both methods are fine (x^2 - 5x + 6 = 0 -> 2,3).
    nb = quadratic_naive(1, -5, 6, 10)
    check("benign quadratic roots are 2 and 3",
          [round(float(x)) for x in nb], [2, 3])

    # 13. unit_roundoff scales by powers of ten.
    check("unit roundoff at 6 digits", unit_roundoff(6), Decimal("5e-6"))

    # 14. Backward error of an EXACT root is zero.
    check("exact root has zero backward error", root_backward_error(1, -5, 6, 2), Decimal(0))

    print(f"\n  {passed} passed, {failed} failed")
    return failed == 0


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    verbose = "--verbose" in sys.argv
    if "--test" in sys.argv:
        print("Running test suite...\n")
        sys.exit(0 if run_tests() else 1)
    else:
        demo(verbose)
        if sys.stdin.isatty():
            repl()

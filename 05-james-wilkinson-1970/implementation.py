"""
Backward error analysis — full implementation (J. H. Wilkinson, 1960s)

Usage:
    python implementation.py               # demo: stability vs conditioning
    python implementation.py --test        # test suite (16 cases)
    python implementation.py --verbose     # show the elimination trace and norms

Before Wilkinson: error analysis tried to track how the true answer drifts
away from the computed one, step by step (FORWARD error). For anything bigger
than a few operations the bounds blew up and told you nothing.

After Wilkinson: ask instead "what problem did my computed answer solve
EXACTLY?" (BACKWARD error). If a tiny perturbation of the input would make the
computed answer correct, the algorithm is fine. Whether the answer is also
close to the truth then depends only on how sensitive the problem is — the
condition number. The two questions are linked by one inequality:

    forward error  ≲  condition number  ×  backward error

That split — blame the algorithm (backward error) separately from blaming the
problem (condition number) — is the idea this file implements.
"""

import sys
from fractions import Fraction
from math import floor, log10


# ── Finite-precision arithmetic ───────────────────────────────────────────────
#
# A 1950s machine kept only a handful of significant digits. We model that by
# rounding every arithmetic result to `sig` significant decimal digits. This is
# the source of all roundoff in the floating-point solve below. The rounding
# model is fl(a op b) = (a op b)(1 + d), |d| <= u, where u is the unit roundoff.

def chop(x, sig=4):
    """Round x to `sig` significant decimal digits — our floating point."""
    if x == 0:
        return 0.0
    return round(x, sig - 1 - floor(log10(abs(x))))


# ── Norms ──────────────────────────────────────────────────────────────────────
#
# We use the infinity norm: for a vector, the largest absolute entry; for a
# matrix, the largest absolute row sum. Wilkinson's bounds work in any norm;
# infinity is the easiest to compute by hand.

def vec_norm(v):
    return max(abs(float(x)) for x in v)

def mat_norm(A):
    return max(sum(abs(float(x)) for x in row) for row in A)


# ── Floating-point Gaussian elimination ───────────────────────────────────────
#
# This is the algorithm Wilkinson analysed. Every intermediate result is chopped
# to `sig` digits. With partial pivoting (pivot=True) the largest available
# entry is moved to the diagonal before each elimination step, which keeps the
# multipliers <= 1 in magnitude and the algorithm backward stable. Without it,
# a tiny pivot produces huge multipliers and the rounding errors are amplified.

def ge_solve(A, b, sig=4, pivot=True, verbose=False):
    n = len(A)
    # work on chopped copies
    M = [[chop(A[i][j], sig) for j in range(n)] for i in range(n)]
    c = [chop(b[i], sig) for i in range(n)]

    for k in range(n):
        if pivot:
            p = max(range(k, n), key=lambda i: abs(M[i][k]))
            if p != k:
                M[k], M[p] = M[p], M[k]
                c[k], c[p] = c[p], c[k]
                if verbose:
                    print(f"    pivot: swap row {k} <-> row {p}")
        for i in range(k + 1, n):
            m = chop(M[i][k] / M[k][k], sig)
            if verbose:
                print(f"    eliminate row {i}, col {k}: multiplier m = {m}")
            for j in range(k, n):
                M[i][j] = chop(M[i][j] - chop(m * M[k][j], sig), sig)
            c[i] = chop(c[i] - chop(m * c[k], sig), sig)

    # back substitution
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = c[i]
        for j in range(i + 1, n):
            s = chop(s - chop(M[i][j] * x[j], sig), sig)
        x[i] = chop(s / M[i][i], sig)
    return x


# ── Exact linear algebra (the "truth" to compare against) ──────────────────────
#
# Fractions give exact rational arithmetic with no roundoff at all. We use them
# to compute the true solution and the exact inverse, so we can measure how far
# the floating-point answer really drifted.

def exact_solve(A, b):
    n = len(A)
    M = [[Fraction(A[i][j]) for j in range(n)] + [Fraction(b[i])] for i in range(n)]
    for k in range(n):
        p = next(i for i in range(k, n) if M[i][k] != 0)
        M[k], M[p] = M[p], M[k]
        piv = M[k][k]
        M[k] = [v / piv for v in M[k]]
        for i in range(n):
            if i != k and M[i][k] != 0:
                f = M[i][k]
                M[i] = [M[i][j] - f * M[k][j] for j in range(n + 1)]
    return [M[i][n] for i in range(n)]

def exact_inverse(A):
    n = len(A)
    cols = []
    for c in range(n):
        e = [1 if i == c else 0 for i in range(n)]
        cols.append(exact_solve(A, e))
    # cols[c] is the c-th column of the inverse; transpose into rows
    return [[cols[c][r] for c in range(n)] for r in range(n)]


# ── The three numbers that matter ──────────────────────────────────────────────

def forward_error(x_hat, x_true):
    """Relative distance between the computed answer and the true answer."""
    num = max(abs(float(x_hat[i]) - float(x_true[i])) for i in range(len(x_hat)))
    return num / vec_norm(x_true)

def residual(A, b, x_hat):
    """r = b - A x_hat. The thing you can actually measure without the truth."""
    n = len(A)
    return [float(b[i]) - sum(float(A[i][j]) * float(x_hat[j]) for j in range(n))
            for i in range(n)]

def backward_error(A, b, x_hat):
    """||r|| / ||b||. How much you'd have to change b for x_hat to be exact."""
    r = residual(A, b, x_hat)
    return vec_norm(r) / vec_norm(b)

def condition_number(A):
    """kappa(A) = ||A|| * ||A^-1||. How much the problem amplifies input changes."""
    Ainv = exact_inverse(A)
    return mat_norm(A) * mat_norm(Ainv)


# ── Demo ────────────────────────────────────────────────────────────────────────

def report(name, A, b, sig, pivot, verbose):
    print(f"  {name}")
    if verbose:
        print(f"    solving in {sig}-digit arithmetic, pivoting={'on' if pivot else 'off'}")
    x_true = exact_solve(A, b)
    x_hat = ge_solve(A, b, sig=sig, pivot=pivot, verbose=verbose)
    kappa = condition_number(A)
    fwd = forward_error(x_hat, x_true)
    bwd = backward_error(A, b, x_hat)
    print(f"    computed x : {[round(v, 6) for v in x_hat]}")
    print(f"    true x     : {[round(float(v), 6) for v in x_true]}")
    print(f"    condition number kappa(A) : {kappa:.3g}")
    print(f"    backward error ||r||/||b|| : {bwd:.3g}   (blame the algorithm)")
    print(f"    forward error  ||dx||/||x||: {fwd:.3g}   (what you actually got)")
    print(f"    bound check: forward {fwd:.3g}  <=  kappa*backward {kappa*bwd:.3g}   "
          f"{'OK' if fwd <= kappa * bwd + 1e-12 else 'VIOLATED'}")
    print()


def demo(verbose=False):
    print("Backward error analysis — J. H. Wilkinson (1970 Turing Award)")
    print("=" * 60)
    print("A good algorithm keeps the BACKWARD error small (its answer exactly")
    print("solves a nearby problem). The FORWARD error is then bounded by the")
    print("problem's condition number times the backward error.\n")

    # Scenario 1: same well-conditioned problem, two algorithms.
    # Tiny pivot in the (0,0) slot. Without pivoting the multiplier is ~1764,
    # the rounding errors explode, and the residual is huge. With pivoting the
    # multiplier is <1 and the answer is essentially exact. The PROBLEM is the
    # same and well-conditioned both times; only the ALGORITHM changed.
    A1 = [[0.003, 59.14], [5.291, -6.130]]
    b1 = [59.17, 46.78]
    print("Scenario 1 — well-conditioned problem, true x = [10, 1].")
    print("Same matrix, 4-digit arithmetic. Only the algorithm differs.\n")
    report("(a) Gaussian elimination WITHOUT pivoting:", A1, b1, 4, False, verbose)
    report("(b) Gaussian elimination WITH partial pivoting:", A1, b1, 4, True, verbose)
    print("  Lesson: same problem, same precision. Pivoting keeps the backward")
    print("  error tiny, so the answer is right. No pivoting blows it up. The")
    print("  problem was never the issue — the algorithm was.\n")

    # Scenario 2: a good algorithm on an ill-conditioned problem. The Hilbert
    # matrix H[i][j] = 1/(i+j+1) is famously ill-conditioned. Even with
    # pivoting and a backward-stable solve, the forward error is large — not
    # because the algorithm misbehaved (backward error stays tiny) but because
    # the problem amplifies any perturbation by kappa.
    n = 6
    H = [[1.0 / (i + j + 1) for j in range(n)] for i in range(n)]
    x_set = [1.0] * n
    bH = [sum(H[i][j] * x_set[j] for j in range(n)) for i in range(n)]
    print(f"Scenario 2 — ill-conditioned problem ({n}x{n} Hilbert matrix), true x = [1,...,1].")
    print("Best algorithm we have (partial pivoting), 6-digit arithmetic.\n")
    report("Gaussian elimination WITH partial pivoting:", H, bH, 6, True, verbose)
    print("  Lesson: the algorithm did its job (backward error is tiny). The")
    print("  forward error is large anyway because kappa is enormous. That is")
    print("  the problem's fault, not the algorithm's. Wilkinson's framework")
    print("  lets you tell the two apart.")


# ── Test suite ────────────────────────────────────────────────────────────────

def run_tests():
    passed = 0
    failed = 0

    def check(name, got, expected):
        nonlocal passed, failed
        if got == expected:
            print(f"  PASS  {name}")
            passed += 1
        else:
            print(f"  FAIL  {name}: got {got!r}, expected {expected!r}")
            failed += 1

    # 1. chop keeps the requested number of significant digits
    check("chop 3.14159 to 3 sig = 3.14", chop(3.14159, 3), 3.14)
    # 2. chop on a large number
    check("chop 104375.88 to 4 sig = 104400", chop(104375.88, 4), 104400.0)
    # 3. chop of zero is zero
    check("chop 0 = 0", chop(0.0, 4), 0.0)

    # 4. exact_solve recovers an integer solution exactly
    xs = exact_solve([[2, 1], [1, 4]], [4, 5])
    check("exact_solve [[2,1],[1,4]] x = [4,5]", [str(v) for v in xs], ["11/7", "6/7"])

    # 5. exact_inverse times A is the identity (exact, no roundoff)
    A = [[4, 3], [6, 3]]
    Ainv = exact_inverse(A)
    prod = [[sum(Fraction(A[i][k]) * Ainv[k][j] for k in range(2)) for j in range(2)]
            for i in range(2)]
    check("A * A^-1 = I", prod, [[Fraction(1), Fraction(0)], [Fraction(0), Fraction(1)]])

    # 6. condition number of identity is 1
    check("kappa(I) = 1", condition_number([[1, 0], [0, 1]]), 1.0)

    # 7. residual of the exact solution is zero
    A = [[2.0, 1.0], [1.0, 4.0]]
    b = [4.0, 5.0]
    xt = [float(v) for v in exact_solve(A, b)]
    check("residual of exact solution ~ 0", round(vec_norm(residual(A, b, xt)), 9), 0.0)

    # 8. pivoting solves the small-pivot system accurately
    A1 = [[0.003, 59.14], [5.291, -6.130]]
    b1 = [59.17, 46.78]
    x_piv = ge_solve(A1, b1, sig=4, pivot=True)
    check("with pivoting: x1 ~ 10", abs(x_piv[0] - 10.0) < 0.05, True)

    # 9. no pivoting wrecks the same system (forward error is large)
    x_nopiv = ge_solve(A1, b1, sig=4, pivot=False)
    check("without pivoting: x1 far from 10", abs(x_nopiv[0] - 10.0) > 1.0, True)

    # 10. backward error: pivoting keeps the residual small
    check("pivoting -> small backward error", backward_error(A1, b1, x_piv) < 1e-3, True)

    # 11. backward error: no pivoting gives a large residual (unstable)
    check("no pivoting -> large backward error", backward_error(A1, b1, x_nopiv) > 0.1, True)

    # 12. this problem is actually well-conditioned (so #9 is the algorithm's fault)
    check("scenario-1 matrix is well-conditioned (kappa < 100)",
          condition_number(A1) < 100, True)

    # 13. forward <= kappa * backward bound holds (pivoting case)
    xt1 = exact_solve(A1, b1)
    fwd = forward_error(x_piv, xt1)
    kb = condition_number(A1) * backward_error(A1, b1, x_piv)
    check("bound holds: forward <= kappa*backward (pivot)", fwd <= kb + 1e-12, True)

    # 14. forward <= kappa * backward bound holds (no-pivot case too)
    fwd2 = forward_error(x_nopiv, xt1)
    kb2 = condition_number(A1) * backward_error(A1, b1, x_nopiv)
    check("bound holds: forward <= kappa*backward (no pivot)", fwd2 <= kb2 + 1e-12, True)

    # 15. Hilbert matrix is ill-conditioned
    n = 6
    H = [[1.0 / (i + j + 1) for j in range(n)] for i in range(n)]
    check("6x6 Hilbert is ill-conditioned (kappa > 1e6)", condition_number(H) > 1e6, True)

    # 16. Hilbert with pivoting: small backward error despite large forward error
    bH = [sum(H[i][j] for j in range(n)) for i in range(n)]  # true x = all ones
    xH = ge_solve(H, bH, sig=10, pivot=True)
    check("Hilbert: backward error stays small", backward_error(H, bH, xH) < 1e-6, True)

    print(f"\n  {passed} passed, {failed} failed")
    return failed == 0


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    verbose = '--verbose' in sys.argv
    if '--test' in sys.argv:
        print("Running test suite...\n")
        ok = run_tests()
        sys.exit(0 if ok else 1)
    else:
        demo(verbose)

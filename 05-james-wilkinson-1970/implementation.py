"""
Week 05 - James H. Wilkinson (1970)
Backward error analysis for Gaussian elimination.

ACM Turing Award citation:
"For his research in numerical analysis to facilitate the use of the high-speed
digital computer, having received special recognition for his work in
computations in linear algebra and 'backward' error analysis."

------------------------------------------------------------------------------
BEFORE Wilkinson:
  Solving a linear system on a finite-precision machine, people tracked the
  FORWARD error - how far the computed x strays from the true x. The bounds
  they could prove grew like a high power of the matrix size, so the consensus
  in the late 1940s was that Gaussian elimination on anything larger than a
  handful of equations would be swamped by rounding noise.

AFTER Wilkinson:
  He asked a different question: what system did the computed x solve EXACTLY?
  He proved the computed x is the exact solution of (A + E)x = b for a
  perturbation E that is tiny - bounded by the unit roundoff times a "growth
  factor" that measures how large the entries get during elimination. Gaussian
  elimination with partial pivoting keeps that growth factor small, so the
  method is BACKWARD STABLE. The large forward errors people feared come from
  ill-conditioned PROBLEMS, not from a bad ALGORITHM:

      forward error  <=  condition number  x  backward error

This file implements finite-precision Gaussian elimination, measures the
growth factor, the backward error (relative residual) and the forward error,
and shows how partial pivoting tames an unstable solve.
------------------------------------------------------------------------------

Run:
  python3 implementation.py            # interactive demo
  python3 implementation.py --test     # self-test suite (15 cases)
  python3 implementation.py --verbose  # show every elimination step
"""

import sys
from math import log10, floor


# --------------------------------------------------------------------------
# Finite-precision arithmetic: a 1960s "machine word" keeping `sig` digits.
# --------------------------------------------------------------------------

def chop(x, sig):
    """Round x to `sig` significant decimal digits."""
    if x == 0:
        return 0.0
    d = sig - 1 - floor(log10(abs(x)))
    return round(x, d)


# --------------------------------------------------------------------------
# Vector / matrix helpers (infinity norm, matrix-vector product, residual).
# --------------------------------------------------------------------------

def matvec(A, x):
    return [sum(A[i][j] * x[j] for j in range(len(x))) for i in range(len(A))]


def residual(A, b, x):
    Ax = matvec(A, x)
    return [b[i] - Ax[i] for i in range(len(b))]


def inf_norm_vec(v):
    return max((abs(c) for c in v), default=0.0)


def inf_norm_mat(A):
    return max((sum(abs(c) for c in row) for row in A), default=0.0)


# --------------------------------------------------------------------------
# Gaussian elimination in finite precision, instrumented for error analysis.
# --------------------------------------------------------------------------

def gauss_solve(A, b, sig, pivot=True, verbose=False):
    """
    Solve A x = b by Gaussian elimination, rounding every operation to `sig`
    significant digits. Returns (x, growth_factor, swaps).
    """
    n = len(A)
    U = [[chop(A[i][j], sig) for j in range(n)] for i in range(n)]
    c = [chop(b[i], sig) for i in range(n)]

    orig_max = max(abs(U[i][j]) for i in range(n) for j in range(n))
    growth_max = orig_max
    swaps = 0

    for k in range(n):
        if pivot:
            p = max(range(k, n), key=lambda i: abs(U[i][k]))
            if p != k:
                U[k], U[p] = U[p], U[k]
                c[k], c[p] = c[p], c[k]
                swaps += 1
                if verbose:
                    print(f"  pivot: swap row {k} <-> row {p} "
                          f"(|{U[k][k]:g}| is the largest in column {k})")
        if U[k][k] == 0:
            raise ZeroDivisionError(f"zero pivot in column {k}; matrix is singular")
        for i in range(k + 1, n):
            m = chop(U[i][k] / U[k][k], sig)
            if verbose:
                print(f"  row {i} -= {m:g} * row {k}")
            U[i][k] = 0.0
            for j in range(k + 1, n):
                U[i][j] = chop(U[i][j] - chop(m * U[k][j], sig), sig)
                growth_max = max(growth_max, abs(U[i][j]))
            c[i] = chop(c[i] - chop(m * c[k], sig), sig)
        if verbose:
            print(f"  after column {k}: {fmt_matrix(U)}")

    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = c[i]
        for j in range(i + 1, n):
            s = chop(s - chop(U[i][j] * x[j], sig), sig)
        x[i] = chop(s / U[i][i], sig)

    growth_factor = growth_max / orig_max if orig_max else 1.0
    return x, growth_factor, swaps


def reference_solve(A, b):
    """High-precision solution used as 'truth' for the forward error."""
    x, _, _ = gauss_solve(A, b, sig=15, pivot=True)
    return x


def condition_number(A):
    """kappa = ||A|| * ||A^-1|| in the infinity norm (high precision)."""
    n = len(A)
    cols = []
    for j in range(n):
        e = [1.0 if i == j else 0.0 for i in range(n)]
        cols.append(reference_solve(A, e))
    Ainv = [[cols[j][i] for j in range(n)] for i in range(n)]
    return inf_norm_mat(A) * inf_norm_mat(Ainv)


# --------------------------------------------------------------------------
# The full backward-error report for one solve.
# --------------------------------------------------------------------------

def analyze(A, b, sig, pivot=True, verbose=False):
    x, growth, swaps = gauss_solve(A, b, sig, pivot=pivot, verbose=verbose)
    r = residual(A, b, x)
    x_true = reference_solve(A, b)

    nx = inf_norm_vec(x)
    nA = inf_norm_mat(A)
    nxt = inf_norm_vec(x_true)

    # Smallest perturbation E with (A+E)x = b has ||E||/||A|| = ||r||/(||A||*||x||).
    # This is the backward error that pairs with forward <= condition * backward.
    backward = inf_norm_vec(r) / (nA * nx) if (nA * nx) else 0.0
    fwd_num = inf_norm_vec([x[i] - x_true[i] for i in range(len(x))])
    forward = fwd_num / nxt if nxt else 0.0
    kappa = condition_number(A)

    return {
        "x": x, "x_true": x_true, "residual": r,
        "growth": growth, "swaps": swaps,
        "backward": backward, "forward": forward, "condition": kappa,
        "sig": sig, "pivot": pivot,
    }


def fmt_vec(v):
    return "[" + ", ".join(f"{c:.5g}" for c in v) + "]"


def fmt_matrix(A):
    return "[" + "; ".join(" ".join(f"{c:.4g}" for c in row) for row in A) + "]"


def print_report(name, res):
    print(f"\n=== {name} ===")
    print(f"  precision      : {res['sig']} significant digits   "
          f"pivoting: {'on' if res['pivot'] else 'off'}")
    print(f"  computed x     : {fmt_vec(res['x'])}")
    print(f"  true x         : {fmt_vec(res['x_true'])}")
    print(f"  residual b-Ax  : {fmt_vec(res['residual'])}")
    print(f"  growth factor  : {res['growth']:.4g}")
    print(f"  condition no.  : {res['condition']:.4g}")
    print(f"  backward error : {res['backward']:.3e}   "
          f"(what nearby system x solved exactly)")
    print(f"  forward error  : {res['forward']:.3e}   "
          f"(how far x is from the truth)")
    print(f"  check: forward <= condition x backward  ->  "
          f"{res['forward']:.2e} <= {res['condition'] * res['backward']:.2e}")


# --------------------------------------------------------------------------
# Example systems used by the demo.
# --------------------------------------------------------------------------

EXAMPLES = {
    "small-pivot": (
        [[0.0001, 1.0], [1.0, 1.0]], [1.0, 2.0],
        "Tiny top-left entry. Without pivoting the multiplier explodes and the "
        "answer is garbage; pivoting fixes it. Wilkinson's case for pivoting."),
    "well-conditioned": (
        [[2.0, 1.0], [1.0, 3.0]], [3.0, 4.0],
        "A tame system. Both forward and backward error stay tiny."),
    "ill-conditioned": (
        [[1.0, 0.99], [0.99, 1.0]], [1.0, 1.0],
        "Nearly singular (rows almost parallel). Backward error stays small but "
        "forward error is much larger, because the PROBLEM is sensitive, not the "
        "algorithm."),
    "3x3": (
        [[3.0, 2.0, -1.0], [2.0, -2.0, 4.0], [-1.0, 0.5, -1.0]],
        [1.0, -2.0, 0.0],
        "A standard 3x3 textbook system with a clean integer solution."),
}


def demo(verbose=False):
    print("Backward error analysis - James H. Wilkinson (1970)")
    print("Each system is solved on a machine keeping 3 significant digits.\n")
    print("The punchline: a large FORWARD error does not mean the algorithm")
    print("failed. Check the BACKWARD error to judge the algorithm itself.")

    for name, (A, b, note) in EXAMPLES.items():
        print("\n" + "-" * 70)
        print(f"{name}: {note}")
        if name == "small-pivot":
            print_report(name + " (NO pivoting)",
                         analyze(A, b, sig=3, pivot=False, verbose=verbose))
            print_report(name + " (partial pivoting)",
                         analyze(A, b, sig=3, pivot=True, verbose=verbose))
        else:
            print_report(name, analyze(A, b, sig=3, pivot=True, verbose=verbose))

    print("\n" + "-" * 70)
    print("Try your own system interactively below (or Ctrl-D to quit).")
    repl()


def repl():
    print("\nEnter a matrix row by row, then the right-hand side.")
    print("Example for a 2x2:  rows '2 1' then '1 3', rhs '3 4'.\n")
    try:
        n = input("size n (2 or 3): ").strip()
        if not n:
            return
        n = int(n)
        A = []
        for i in range(n):
            row = [float(v) for v in input(f"row {i} ({n} numbers): ").split()]
            if len(row) != n:
                print("wrong number of entries"); return
            A.append(row)
        b = [float(v) for v in input(f"rhs ({n} numbers): ").split()]
        if len(b) != n:
            print("wrong number of entries"); return
        sig = input("significant digits [3]: ").strip()
        sig = int(sig) if sig else 3
        print_report("your system (NO pivoting)", analyze(A, b, sig, pivot=False))
        print_report("your system (partial pivoting)", analyze(A, b, sig, pivot=True))
    except (EOFError, KeyboardInterrupt):
        print()
    except (ValueError, ZeroDivisionError) as e:
        print(f"could not solve: {e}")


# --------------------------------------------------------------------------
# Self-test suite.
# --------------------------------------------------------------------------

def run_tests():
    passed = 0
    failed = 0

    def check(name, cond):
        nonlocal passed, failed
        if cond:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name}")

    # 1. chop keeps the right number of significant digits.
    check("chop(3.14159, 3) == 3.14", chop(3.14159, 3) == 3.14)
    # 2. chop on a large value rounds in the high digits.
    check("chop(-9999, 3) == -10000", chop(-9999, 3) == -10000)
    # 3. chop of zero is zero.
    check("chop(0, 5) == 0", chop(0.0, 5) == 0.0)

    # 4. Identity system returns the right-hand side unchanged.
    I = [[1.0, 0.0], [0.0, 1.0]]
    x, g, _ = gauss_solve(I, [5.0, -7.0], sig=6)
    check("identity solve", x == [5.0, -7.0] and abs(g - 1.0) < 1e-9)

    # 5. Well-conditioned 2x2 solved exactly at high precision.
    A = [[2.0, 1.0], [1.0, 3.0]]
    b = [3.0, 4.0]  # true x = [1, 1]
    x = reference_solve(A, b)
    check("well-conditioned exact", abs(x[0] - 1) < 1e-9 and abs(x[1] - 1) < 1e-9)

    # 6. 3x3 integer system: residual is essentially zero at high precision.
    A3, b3, _ = EXAMPLES["3x3"]
    x3 = reference_solve(A3, b3)
    check("3x3 residual ~ 0", inf_norm_vec(residual(A3, b3, x3)) < 1e-9)

    # 7. Small-pivot system WITHOUT pivoting has a large backward error.
    Asp, bsp, _ = EXAMPLES["small-pivot"]
    no = analyze(Asp, bsp, sig=3, pivot=False)
    check("no-pivot backward error large", no["backward"] > 0.1)

    # 8. Same system WITH pivoting has a tiny backward error.
    yes = analyze(Asp, bsp, sig=3, pivot=True)
    check("pivot backward error tiny", yes["backward"] < 1e-2)

    # 9. Pivoting drastically reduces the growth factor here.
    check("pivot shrinks growth factor", yes["growth"] < no["growth"] / 10)

    # 10. Pivoting reduces the forward error on the small-pivot system.
    check("pivot reduces forward error", yes["forward"] < no["forward"])

    # 11. Wilkinson's bound holds: forward <= condition * backward (with slack).
    check("forward <= cond * backward (pivot)",
          yes["forward"] <= yes["condition"] * yes["backward"] * 10 + 1e-12)

    # 12. Ill-conditioned system: backward small but forward much larger.
    Aic, bic, _ = EXAMPLES["ill-conditioned"]
    ic = analyze(Aic, bic, sig=3, pivot=True)
    check("ill-conditioned: backward << forward",
          ic["backward"] < ic["forward"] and ic["condition"] > 100)

    # 13. Condition number of the identity is 1.
    check("condition(I) == 1", abs(condition_number(I) - 1.0) < 1e-9)

    # 14. Residual really is what the computed x solves exactly:
    #     A x = b - r, so A x + r == b.
    xv, _, _ = gauss_solve(Asp, bsp, sig=3, pivot=True)
    r = residual(Asp, bsp, xv)
    recon = [matvec(Asp, xv)[i] + r[i] for i in range(2)]
    check("A x + residual == b", all(abs(recon[i] - bsp[i]) < 1e-9 for i in range(2)))

    # 15. Singular matrix raises rather than returning nonsense.
    singular_raised = False
    try:
        gauss_solve([[1.0, 2.0], [2.0, 4.0]], [1.0, 2.0], sig=6, pivot=True)
    except ZeroDivisionError:
        singular_raised = True
    check("singular matrix raises", singular_raised)

    print(f"\n{passed} passed, {failed} failed")
    return failed == 0


# --------------------------------------------------------------------------

def main():
    if "--test" in sys.argv:
        ok = run_tests()
        sys.exit(0 if ok else 1)
    demo(verbose="--verbose" in sys.argv)


if __name__ == "__main__":
    main()

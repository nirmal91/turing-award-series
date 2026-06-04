"""
Backward error analysis and stable linear-system solving
Based on the work of J. H. Wilkinson (Turing Award, 1970).

Usage:
    python implementation.py            # guided demo
    python implementation.py --test     # test suite (17 cases)
    python implementation.py --verbose  # show pivoting steps and residuals

Before Wilkinson: people bounded the FORWARD error of a calculation, asking
    how far the computed answer drifts from the true one. Tracked naively
    through Gaussian elimination on an n x n matrix that bound grew like 2^n,
    and the conclusion was that elimination was hopeless for large systems.
    Computers "obviously" could not be trusted with real arithmetic.

After Wilkinson: he measured the BACKWARD error instead. The computed
    solution of A x = b is the EXACT solution of (A + E) x = b for some small
    E. He proved ||E|| stays near machine precision for Gaussian elimination
    with partial pivoting, no matter how large n is. The algorithm was fine
    all along. When the answer was bad, the problem was ill-conditioned, not
    the method:   forward error  <=  condition number  x  backward error.
"""

import sys
from fractions import Fraction


# ── The floating-point axiom Wilkinson built everything on ──────────────────────
#
# Every basic operation returns the true result times (1 + d), with |d| <= u,
# where u is the unit roundoff (about 1.11e-16 for IEEE double precision):
#       fl(a op b) = (a op b)(1 + d)
# A rounded operation is the EXACT operation on slightly perturbed operands.
# Backward error analysis is that single idea pushed through a whole algorithm.

UNIT_ROUNDOFF = 2.0 ** -53     # ~1.11e-16 for IEEE double precision


# ── The algorithm Wilkinson proved backward stable ──────────────────────────────

def gepp(A, b, verbose=False):
    """
    Solve A x = b by Gaussian elimination with partial pivoting (GEPP).
    Pure floating point. Returns the computed solution x.

    Partial pivoting (always eliminate using the largest-magnitude entry in the
    column) is the detail that keeps the growth factor small and the method
    backward stable in practice. This is exactly what LAPACK still does today.
    """
    n = len(b)
    M = [list(map(float, row)) + [float(b[i])] for i, row in enumerate(A)]

    for k in range(n):
        # partial pivoting: choose the largest-magnitude entry in column k
        pivot = max(range(k, n), key=lambda i: abs(M[i][k]))
        if M[pivot][k] == 0.0:
            raise ZeroDivisionError("matrix is singular")
        if pivot != k:
            M[k], M[pivot] = M[pivot], M[k]
            if verbose:
                print(f"    col {k}: swap row {k} <-> row {pivot}  (pivot {M[k][k]:.4g})")
        for i in range(k + 1, n):
            f = M[i][k] / M[k][k]
            for j in range(k, n + 1):
                M[i][j] -= f * M[k][j]
            if verbose and f != 0.0:
                print(f"    col {k}: row {i} -= {f:.4g} * row {k}")

    # back-substitution
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = M[i][n] - sum(M[i][j] * x[j] for j in range(i + 1, n))
        x[i] = s / M[i][i]
    return x


# ── Exact arithmetic, used only to know the truth we compare against ────────────

def exact_solve(A, b):
    """Exact solution using rational arithmetic (no rounding). The 'true' answer."""
    n = len(b)
    M = [[Fraction(A[i][j]) for j in range(n)] + [Fraction(b[i])] for i in range(n)]
    for k in range(n):
        pivot = next(i for i in range(k, n) if M[i][k] != 0)
        if pivot != k:
            M[k], M[pivot] = M[pivot], M[k]
        piv = M[k][k]
        for i in range(n):
            if i != k and M[i][k] != 0:
                f = M[i][k] / piv
                for j in range(k, n + 1):
                    M[i][j] -= f * M[k][j]
    return [M[i][n] / M[i][i] for i in range(n)]


def exact_inverse(A):
    """Exact inverse via Gauss-Jordan on rationals. Used for the condition number."""
    n = len(A)
    M = [[Fraction(A[i][j]) for j in range(n)] +
         [Fraction(1 if i == j else 0) for j in range(n)] for i in range(n)]
    for k in range(n):
        pivot = next(i for i in range(k, n) if M[i][k] != 0)
        if pivot != k:
            M[k], M[pivot] = M[pivot], M[k]
        piv = M[k][k]
        M[k] = [v / piv for v in M[k]]
        for i in range(n):
            if i != k and M[i][k] != 0:
                f = M[i][k]
                M[i] = [M[i][j] - f * M[k][j] for j in range(2 * n)]
    return [[M[i][j + n] for j in range(n)] for i in range(n)]


# ── Norms, residual, and the two errors ─────────────────────────────────────────

def inf_norm_matrix(A):
    """Infinity norm: the largest absolute row sum."""
    return max(sum(abs(float(v)) for v in row) for row in A)


def inf_norm_vec(v):
    return max(abs(float(x)) for x in v)


def residual(A, x, b):
    """r = b - A x. The leftover when the computed x is plugged back in."""
    n = len(b)
    return [float(b[i]) - sum(float(A[i][j]) * x[j] for j in range(n)) for i in range(n)]


def backward_error(A, x, b):
    """
    Normwise relative backward error (Rigal-Gaches, 1967):
        eta = ||r||  /  (||A|| ||x|| + ||b||),   with r = b - A x.
    This is the smallest relative perturbation to A and b for which the
    computed x is the EXACT solution. A good solver keeps it near unit roundoff.
    """
    r = residual(A, x, b)
    denom = inf_norm_matrix(A) * inf_norm_vec(x) + inf_norm_vec(b)
    return inf_norm_vec(r) / denom if denom else 0.0


def forward_error(x, x_true):
    """Relative distance from the true solution: ||x - x_true|| / ||x_true||."""
    num = max(abs(x[i] - float(x_true[i])) for i in range(len(x)))
    den = inf_norm_vec(x_true)
    return num / den if den else num


def condition_number(A):
    """Infinity-norm condition number ||A|| * ||A^-1||, computed exactly."""
    return inf_norm_matrix(A) * inf_norm_matrix(exact_inverse(A))


def hilbert(n):
    """Hilbert matrix H[i][j] = 1/(i+j+1). The classic ill-conditioned example."""
    return [[1.0 / (i + j + 1) for j in range(n)] for i in range(n)]


# ── Reporting ───────────────────────────────────────────────────────────────────

def analyze(A, b, x_true=None, label="", verbose=False):
    """Solve A x = b, then report condition number, backward error, forward error."""
    x = gepp(A, b, verbose=verbose)
    if x_true is None:
        x_true = exact_solve(A, b)
    be = backward_error(A, x, b)
    fe = forward_error(x, x_true)
    cond = condition_number(A)

    if verbose:
        r = residual(A, x, b)
        print(f"    computed x : {[round(v, 6) for v in x]}")
        print(f"    residual   : {['%.1e' % v for v in r]}")

    print(f"  {label}")
    print(f"    condition number : {cond:.2e}")
    print(f"    backward error   : {be:.2e}   (near u = {UNIT_ROUNDOFF:.1e}, machine precision)")
    print(f"    forward error    : {fe:.2e}   (rule of thumb: ~ cond x backward = {cond * be:.2e})")
    print()
    return x, be, fe, cond


# ── Guided demo ──────────────────────────────────────────────────────────────────

def demo(verbose=False):
    print("Backward error analysis (J. H. Wilkinson, Turing Award 1970)\n")

    print("The floating-point axiom everything rests on:")
    print("    fl(a op b) = (a op b)(1 + d),   |d| <= u")
    print(f"    unit roundoff u = {UNIT_ROUNDOFF:.3e}")
    print(f"    example: 0.1 + 0.2 = {0.1 + 0.2!r}  (rounded, not exactly 0.3)\n")

    print("Solving A x = b with Gaussian elimination + partial pivoting.")
    print("For every system: backward error tells you whether the METHOD behaved;")
    print("the condition number tells you whether the PROBLEM was answerable.\n")

    print("1. A well-conditioned system. Both errors are tiny.")
    analyze([[2.0, 1.0], [1.0, 3.0]], [3.0, 4.0],
            x_true=[1.0, 1.0], label="2x2, modest condition number", verbose=verbose)

    print("2. Hilbert matrices. As n grows they edge toward singular.")
    print("   Watch the split: backward error stays at machine precision while")
    print("   the forward error explodes in lockstep with the condition number.\n")
    for n in (4, 6, 8, 10, 12):
        A = hilbert(n)
        x_true = [1.0] * n
        b = [float(sum(Fraction(A[i][j]) * Fraction(x_true[j]) for j in range(n)))
             for i in range(n)]
        analyze(A, b, x_true=x_true, label=f"Hilbert {n}x{n}", verbose=verbose)

    print("The solver never misbehaves. When the answer is bad, the PROBLEM is")
    print("ill-conditioned, not the algorithm. Separating those two is Wilkinson's gift.")


# ── Test suite ────────────────────────────────────────────────────────────────────

def run_tests():
    passed = 0
    failed = 0

    def check(name, cond):
        nonlocal passed, failed
        if cond:
            print(f"  PASS  {name}")
            passed += 1
        else:
            print(f"  FAIL  {name}")
            failed += 1

    def close(a, b, tol=1e-9):
        return all(abs(a[i] - b[i]) <= tol for i in range(len(a)))

    # 1. GEPP solves a simple 2x2 system
    x = gepp([[2.0, 1.0], [1.0, 3.0]], [3.0, 4.0])
    check("gepp solves 2x2", close(x, [1.0, 1.0]))

    # 2. GEPP on the identity returns b unchanged
    x = gepp([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], [5.0, -2.0, 7.0])
    check("gepp identity", close(x, [5.0, -2.0, 7.0]))

    # 3. GEPP needs a row swap (zero leading pivot) and still solves
    x = gepp([[0.0, 1.0], [1.0, 0.0]], [2.0, 3.0])
    check("gepp pivots past a zero pivot", close(x, [3.0, 2.0]))

    # 4. exact_solve gives exact rationals, not floats
    xe = exact_solve([[3, 0], [0, 3]], [1, 1])
    check("exact_solve returns 1/3 exactly", xe == [Fraction(1, 3), Fraction(1, 3)])

    # 5. exact_inverse of a 2x2
    inv = exact_inverse([[4, 7], [2, 6]])
    check("exact_inverse 2x2", inv == [[Fraction(6, 10), Fraction(-7, 10)],
                                       [Fraction(-2, 10), Fraction(4, 10)]])

    # 6. inf_norm_matrix is the max absolute row sum
    check("inf_norm_matrix", inf_norm_matrix([[1, -2], [3, 4]]) == 7)

    # 7. inf_norm_vec is the max absolute entry
    check("inf_norm_vec", inf_norm_vec([1, -9, 3]) == 9)

    # 8. condition number of the identity is 1
    check("cond(I) == 1", abs(condition_number([[1.0, 0.0], [0.0, 1.0]]) - 1.0) < 1e-12)

    # 9. residual of an exact solution is essentially zero
    A = [[2.0, 1.0], [1.0, 3.0]]
    r = residual(A, gepp(A, [3.0, 4.0]), [3.0, 4.0])
    check("residual of solution ~ 0", inf_norm_vec(r) < 1e-12)

    # 10. backward error of GEPP is near machine precision for several systems
    systems = [
        ([[2.0, 1.0], [1.0, 3.0]], [3.0, 4.0]),
        ([[4.0, 3.0], [6.0, 3.0]], [10.0, 12.0]),
        ([[1.0, 2.0, 3.0], [2.0, 5.0, 3.0], [1.0, 0.0, 8.0]], [6.0, 10.0, 9.0]),
    ]
    check("backward error <= 1e-13 on well-posed systems",
          all(backward_error(A, gepp(A, b), b) <= 1e-13 for A, b in systems))

    # 11. forward error is zero for an exact match
    check("forward error of exact match == 0", forward_error([1.0, 2.0], [1.0, 2.0]) == 0.0)

    # 12. condition number of Hilbert grows with n
    conds = [condition_number(hilbert(n)) for n in (3, 5, 7)]
    check("cond(Hilbert) grows with n", conds[0] < conds[1] < conds[2])

    # 13. THE central result: backward error stays tiny even as forward error blows up
    A = hilbert(12)
    xt = [1.0] * 12
    b = [float(sum(Fraction(A[i][j]) * Fraction(xt[j]) for j in range(12))) for i in range(12)]
    x = gepp(A, b)
    be = backward_error(A, x, b)
    fe = forward_error(x, xt)
    check("Hilbert(12): backward error near u", be < 1e-13)
    check("Hilbert(12): forward error is large", fe > 1e-3)

    # 14. the rule of thumb holds: forward error <= cond * backward error (with slack)
    cond = condition_number(A)
    check("forward <= cond * backward (Hilbert 12)", fe <= cond * be * 100)

    # 15. backward error stays small across a sweep of Hilbert sizes
    stable = True
    for n in (4, 6, 8, 10):
        A = hilbert(n)
        xt = [1.0] * n
        b = [float(sum(Fraction(A[i][j]) * Fraction(xt[j]) for j in range(n))) for i in range(n)]
        if backward_error(A, gepp(A, b), b) > 1e-13:
            stable = False
    check("GEPP backward-stable across Hilbert sweep", stable)

    # 16. singular matrix is detected
    try:
        gepp([[1.0, 2.0], [2.0, 4.0]], [1.0, 2.0])
        check("singular matrix raises", False)
    except ZeroDivisionError:
        check("singular matrix raises", True)

    # 17. GEPP agrees with the exact solution on a well-conditioned random-ish system
    A = [[10.0, 2.0, 1.0], [1.0, 8.0, 3.0], [2.0, 1.0, 9.0]]
    b = [13.0, 12.0, 12.0]
    x = gepp(A, b)
    xe = [float(v) for v in exact_solve(A, b)]
    check("gepp matches exact on well-conditioned system", close(x, xe, tol=1e-9))

    print(f"\n  {passed} passed, {failed} failed")
    return failed == 0


# ── Entry point ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    verbose = '--verbose' in sys.argv

    if '--test' in sys.argv:
        print("Running test suite...\n")
        ok = run_tests()
        sys.exit(0 if ok else 1)
    else:
        demo(verbose)

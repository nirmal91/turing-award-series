"""
Backward error analysis and conditioning — full implementation (J. H. Wilkinson)

Usage:
    python implementation.py               # interactive demo
    python implementation.py --test        # test suite (16 cases)
    python implementation.py --verbose     # show elimination steps and internals

Before Wilkinson (1940s): the standard fear was that rounding errors in
Gaussian elimination grew with the number of operations (~n^3), so large
systems looked unsolvable. Hotelling's bound suggested error could grow like
4^n. People doubted computers could do linear algebra at all.

After Wilkinson (1948 onward): backward error analysis showed that Gaussian
elimination WITH PARTIAL PIVOTING is backward stable. The computed solution
x_hat is the exact solution of (A + E)x = b where ||E|| is tiny -- on the
order of the machine's rounding unit times a modest growth factor. The
algorithm is trustworthy. When the answer is still inaccurate, the blame
lies with the problem's CONDITION NUMBER, not the algorithm:

        forward error   <=   condition number   x   backward error

This file implements a finite-precision machine, Gaussian elimination with and
without pivoting on it, the backward/forward error and condition number, and
Wilkinson's own polynomial -- the textbook example of an ill-conditioned
problem where a stable algorithm still cannot save you.
"""

import sys
from math import log10, floor


# ── A finite-precision machine ────────────────────────────────────────────────
#
# Real hardware keeps a fixed number of digits and rounds every result. We model
# that with round-to-`sig`-significant-digits. fl(a op b) = round(a op b). Set
# sig=None to compute in full (float64) precision, our stand-in for "exact".

def fl(x, sig):
    """Round x to `sig` significant digits. sig=None means full precision."""
    if sig is None or x == 0:
        return float(x)
    return round(x, sig - int(floor(log10(abs(x)))) - 1)


# ── Mini linear algebra (no numpy) ────────────────────────────────────────────

def matvec(A, x):
    return [sum(A[i][j] * x[j] for j in range(len(x))) for i in range(len(A))]


def vecnorm_inf(v):
    return max(abs(c) for c in v)


def matnorm_inf(A):
    # max absolute row sum
    return max(sum(abs(c) for c in row) for row in A)


def residual(A, b, x):
    Ax = matvec(A, x)
    return [b[i] - Ax[i] for i in range(len(b))]


# ── Gaussian elimination on the finite-precision machine ──────────────────────
#
# This is the algorithm Wilkinson analysed. `pivot=True` does partial pivoting:
# before eliminating column k, swap in the row with the largest entry in that
# column. That single step is what makes the method backward stable. Without it,
# a tiny pivot forces a huge multiplier, the multiplier wipes out good digits,
# and the backward error explodes.

def gauss_solve(A, b, sig=None, pivot=True, verbose=False):
    n = len(A)
    # work on copies, rounded into the machine
    M = [[fl(A[i][j], sig) for j in range(n)] for i in range(n)]
    v = [fl(b[i], sig) for i in range(n)]
    max_entry = max(abs(M[i][j]) for i in range(n) for j in range(n))
    growth = 1.0  # growth factor: largest entry ever seen / largest at start

    for k in range(n):
        if pivot:
            p = max(range(k, n), key=lambda i: abs(M[i][k]))
            if p != k:
                M[k], M[p] = M[p], M[k]
                v[k], v[p] = v[p], v[k]
                if verbose:
                    print(f"    pivot: swap row {k} and row {p}")
        if M[k][k] == 0:
            raise ZeroDivisionError("zero pivot -- matrix is singular at this precision")
        for i in range(k + 1, n):
            mult = fl(M[i][k] / M[k][k], sig)
            if verbose:
                print(f"    eliminate row {i} with multiplier m = {mult}")
            M[i][k] = 0.0
            for j in range(k + 1, n):
                M[i][j] = fl(M[i][j] - fl(mult * M[k][j], sig), sig)
            v[i] = fl(v[i] - fl(mult * v[k], sig), sig)
        cur = max(abs(M[i][j]) for i in range(n) for j in range(n))
        growth = max(growth, cur / max_entry)

    # back substitution
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = fl(sum(fl(M[i][j] * x[j], sig) for j in range(i + 1, n)), sig)
        x[i] = fl((v[i] - s) / M[i][i], sig)
    return x, growth


def mat_inverse(A):
    """Full-precision inverse via Gauss-Jordan. Used only for condition number."""
    n = len(A)
    M = [[float(A[i][j]) for j in range(n)] + [1.0 if i == j else 0.0 for j in range(n)]
         for i in range(n)]
    for k in range(n):
        p = max(range(k, n), key=lambda i: abs(M[i][k]))
        M[k], M[p] = M[p], M[k]
        pivot = M[k][k]
        M[k] = [c / pivot for c in M[k]]
        for i in range(n):
            if i != k:
                f = M[i][k]
                M[i] = [M[i][j] - f * M[k][j] for j in range(2 * n)]
    return [row[n:] for row in M]


def cond_inf(A):
    """Infinity-norm condition number: ||A|| * ||A^-1||."""
    return matnorm_inf(A) * matnorm_inf(mat_inverse(A))


def backward_error(A, b, x):
    """Normwise relative backward error (Rigal-Gaches): the smallest relative
    perturbation of (A, b) for which x is the exact solution."""
    r = residual(A, b, x)
    denom = matnorm_inf(A) * vecnorm_inf(x) + vecnorm_inf(b)
    return vecnorm_inf(r) / denom


def forward_error(x_hat, x_true):
    return vecnorm_inf([x_hat[i] - x_true[i] for i in range(len(x_true))]) / vecnorm_inf(x_true)


# ── Wilkinson's polynomial ────────────────────────────────────────────────────
#
# p(x) = (x-1)(x-2)...(x-n). The roots are obviously 1, 2, ..., n. Wilkinson
# expanded it into coefficient form and watched in horror as a tiny change to
# one coefficient sent the roots flying -- some even became complex. He called
# it "the most traumatic experience in my career as a numerical analyst."
#
# The sensitivity of root r_k to coefficient a_j is |r_k^j / p'(r_k)|, where
# p'(r_k) = product over i != k of (r_k - r_i). This is a CONDITION NUMBER for
# the root. It can be astronomically large even though evaluating the polynomial
# is trivial. The problem is ill-conditioned; no stable algorithm can fix that.

def wilkinson_coeffs(n):
    """Expand (x-1)(x-2)...(x-n) into coefficients, exactly, using integers.
    Returns [a_0, a_1, ..., a_n] (constant term first)."""
    coeffs = [1]  # the polynomial "1"
    for r in range(1, n + 1):
        # multiply current polynomial by (x - r)
        new = [0] * (len(coeffs) + 1)
        for i, c in enumerate(coeffs):
            new[i] += c * (-r)   # constant side: c * (-r)
            new[i + 1] += c      # x side: c * x
        coeffs = new
    return coeffs


def root_sensitivity(n, j):
    """For each root k = 1..n, the amplification factor |k^j / p'(k)| describing
    how far root k moves per unit change in the coefficient of x^j."""
    out = []
    for k in range(1, n + 1):
        deriv = 1.0
        for i in range(1, n + 1):
            if i != k:
                deriv *= (k - i)
        out.append((k, abs(k ** j / deriv)))
    return out


# ── Interactive demo ──────────────────────────────────────────────────────────

def demo(verbose=False):
    print("Backward Error Analysis -- J. H. Wilkinson (1970 Turing Award)")
    print("=" * 64)
    print("The question is not 'how wrong is the answer?' but")
    print("'for what nearby problem is this answer exactly right?'\n")

    # ---- Demo A: a well-conditioned system solves cleanly ---------------------
    print("A) Well-conditioned system, solved on a 4-digit machine")
    A = [[2.0, 1.0], [1.0, 3.0]]
    x_true = [3.0, -1.0]
    b = matvec(A, x_true)
    x_hat, _ = gauss_solve(A, b, sig=4, pivot=True, verbose=verbose)
    print(f"    true x      = {x_true}")
    print(f"    computed x  = {x_hat}")
    print(f"    condition number    = {cond_inf(A):.1f}")
    print(f"    forward error       = {forward_error(x_hat, x_true):.1e}")
    print(f"    backward error      = {backward_error(A, b, x_hat):.1e}")
    print("    Small condition number -> small forward error. Easy case.\n")

    # ---- Demo B: pivoting is what makes the algorithm stable ------------------
    print("B) Same problem, two algorithms: why partial pivoting matters")
    A = [[1e-4, 1.0], [1.0, 1.0]]
    x_true = [1.0, 1.0]
    b = matvec(A, x_true)   # b = [1.0001, 2.0]
    print(f"    A = {A},  b = {b},  true x ~ {x_true}")
    print(f"    condition number = {cond_inf(A):.1f}  (this system is fine)\n")

    if verbose:
        print("    -- no pivoting --")
    x_no, g_no = gauss_solve(A, b, sig=3, pivot=False, verbose=verbose)
    if verbose:
        print("    -- partial pivoting --")
    x_pp, g_pp = gauss_solve(A, b, sig=3, pivot=True, verbose=verbose)

    print(f"    no pivoting:       x = {x_no}")
    print(f"        growth factor  = {g_no:.1f}")
    print(f"        backward error = {backward_error(A, b, x_no):.1e}   <- huge, UNSTABLE")
    print(f"    partial pivoting:  x = {x_pp}")
    print(f"        growth factor  = {g_pp:.1f}")
    print(f"        backward error = {backward_error(A, b, x_pp):.1e}   <- tiny, STABLE")
    print("    The tiny pivot 1e-4 forces a multiplier of 1e4 that wipes out")
    print("    the good digits. Pivoting swaps it away. Same math, same data,")
    print("    one ordering is trustworthy and the other is not.\n")

    # ---- Demo C: forward error = condition number x backward error ------------
    print("C) An ill-conditioned problem: a stable algorithm still can't save you")
    A = [[1.0, 1.0], [1.0, 1.0001]]
    x_true = [1.0, 1.0]
    b = matvec(A, x_true)
    kappa = cond_inf(A)
    # perturb the right-hand side by a tiny relative amount, solve exactly
    rel_pert = 1e-6
    b_pert = [b[0] * (1 + rel_pert), b[1]]
    x_pert, _ = gauss_solve(A, b_pert, sig=None, pivot=True)
    fwd = forward_error(x_pert, x_true)
    print(f"    condition number kappa = {kappa:.1f}")
    print(f"    perturb b by a relative {rel_pert:.0e}  (the size of one rounding)")
    print(f"    solution moves by a relative {fwd:.1e}")
    print(f"    that is about kappa x perturbation = {kappa * rel_pert:.1e}")
    print("    The algorithm was exact here. The amplification is pure conditioning.")
    print("    forward error  <=  condition number  x  backward error.\n")

    # ---- Demo D: Wilkinson's polynomial ---------------------------------------
    print("D) Wilkinson's polynomial: (x-1)(x-2)...(x-20)")
    n = 20
    sens = root_sensitivity(n, 19)   # sensitivity to the x^19 coefficient (= -210)
    worst = max(sens, key=lambda kv: kv[1])
    print(f"    roots are exactly 1, 2, ..., {n}")
    print(f"    coefficient of x^19 is {wilkinson_coeffs(n)[19]}")
    print("    sensitivity of each root to a change in that one coefficient:")
    for k, s in sens:
        if k in (1, 5, 14, 15, 16, 19, 20):
            print(f"        root {k:2d}:  amplification ~ {s:.2e}")
    dc = 2 ** -23   # the perturbation Wilkinson famously used
    print(f"    change that coefficient by 2^-23 = {dc:.2e}")
    print(f"    worst root (root {worst[0]}) then moves by ~ {worst[1] * dc:.2f}")
    print("    Evaluating this polynomial is trivial. Finding its roots is not.")
    print("    No algorithm is to blame -- the problem itself is ill-conditioned.")


# ── Test suite ────────────────────────────────────────────────────────────────

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

    # 1. fl rounds to significant digits, not decimal places
    check("fl(123.456, 4) == 123.5", fl(123.456, 4) == 123.5)
    # 2. fl(x, None) is exact
    check("fl(x, None) is identity", fl(0.1 + 0.2, None) == 0.1 + 0.2)
    # 3. fl preserves zero
    check("fl(0, 3) == 0", fl(0.0, 3) == 0.0)

    # 4. exact solve of a clean system
    A = [[2.0, 1.0], [1.0, 3.0]]
    x_true = [3.0, -1.0]
    b = matvec(A, x_true)
    x, _ = gauss_solve(A, b, sig=None, pivot=True)
    check("full-precision solve is exact", all(abs(x[i] - x_true[i]) < 1e-9 for i in range(2)))

    # 5. solving recovers a known 3x3 solution
    A3 = [[4.0, 3.0, 2.0], [1.0, 5.0, 1.0], [2.0, 1.0, 6.0]]
    xt = [1.0, -1.0, 2.0]
    b3 = matvec(A3, xt)
    x3, _ = gauss_solve(A3, b3, sig=None, pivot=True)
    check("3x3 solve is exact", all(abs(x3[i] - xt[i]) < 1e-9 for i in range(3)))

    # 6. residual of the exact solution is ~zero
    check("exact residual ~ 0", vecnorm_inf(residual(A3, b3, x3)) < 1e-9)

    # 7. backward error of the exact solution is ~0
    check("exact backward error ~ 0", backward_error(A3, b3, x3) < 1e-12)

    # 8. pivoting beats no-pivoting on the tiny-pivot system (the core result)
    Abad = [[1e-4, 1.0], [1.0, 1.0]]
    xt2 = [1.0, 1.0]
    bbad = matvec(Abad, xt2)
    x_no, _ = gauss_solve(Abad, bbad, sig=3, pivot=False)
    x_pp, _ = gauss_solve(Abad, bbad, sig=3, pivot=True)
    be_no = backward_error(Abad, bbad, x_no)
    be_pp = backward_error(Abad, bbad, x_pp)
    check("no-pivot backward error is large", be_no > 1e-2)
    # 9
    check("partial-pivot backward error is tiny", be_pp < 1e-3)
    # 10
    check("pivoting improves backward error by orders of magnitude", be_no > 100 * be_pp)

    # 11. growth factor without pivoting is large on the tiny-pivot system
    _, g_no = gauss_solve(Abad, bbad, sig=3, pivot=False)
    check("no-pivot growth factor is large", g_no > 100)

    # 12. condition number of identity is 1
    check("cond(I) == 1", abs(cond_inf([[1.0, 0.0], [0.0, 1.0]]) - 1.0) < 1e-9)

    # 13. condition number grows as the matrix nears singular
    near = [[1.0, 1.0], [1.0, 1.0001]]
    check("near-singular matrix is ill-conditioned", cond_inf(near) > 1e4)

    # 14. forward error bounded by condition number times backward error
    A = [[2.0, 1.0], [1.0, 3.0]]
    b = matvec(A, [3.0, -1.0])
    xh, _ = gauss_solve(A, b, sig=4, pivot=True)
    fe = forward_error(xh, [3.0, -1.0])
    bound = cond_inf(A) * backward_error(A, b, xh)
    check("forward error <= cond * backward error", fe <= bound + 1e-12)

    # 15. Wilkinson coefficients: (x-1)(x-2) = x^2 - 3x + 2
    check("wilkinson_coeffs(2) == [2, -3, 1]", wilkinson_coeffs(2) == [2, -3, 1])

    # 16. Wilkinson polynomial is wildly ill-conditioned for n=20
    sens = root_sensitivity(20, 19)
    worst = max(s for _, s in sens)
    check("Wilkinson root sensitivity is enormous", worst > 1e8)

    print(f"\n  {passed} passed, {failed} failed")
    return failed == 0


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    verbose = '--verbose' in sys.argv
    if '--test' in sys.argv:
        print("Running test suite...\n")
        sys.exit(0 if run_tests() else 1)
    else:
        demo(verbose)

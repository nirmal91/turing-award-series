"""
Week 05 - James H. Wilkinson (1970)
Backward error analysis: the pure idea.

Before Wilkinson, the question everyone asked about a computed answer was
"how far is it from the true answer?" That is the FORWARD error. On the early
machines (Wilkinson worked on Turing's Pilot ACE) every operation lost a little
precision, and people feared that across thousands of operations the rounding
errors would pile up and ruin everything.

Wilkinson turned the question around. Instead of asking how wrong the answer is,
he asked: "what problem did my computed answer solve EXACTLY?" If the answer you
got is the exact solution of a problem that is very close to the one you typed
in, then the algorithm did its job. Any remaining error came from the problem
being sensitive, not from the algorithm being sloppy. That is BACKWARD error.

This file solves a 2x2 linear system on a "machine" that keeps only 3
significant digits, the way a 1960s computer would, and shows the two views.
"""

from math import log10, floor


def chop(x, sig=3):
    """Round x to `sig` significant digits - one 'word' of a small machine."""
    if x == 0:
        return 0.0
    d = sig - 1 - floor(log10(abs(x)))
    return round(x, d)


def solve_2x2(A, b, pivot):
    """Gaussian elimination on a 2x2 system, every operation rounded to 3 digits."""
    a, c, d, e = A[0][0], A[0][1], A[1][0], A[1][1]
    b0, b1 = b
    if pivot and abs(d) > abs(a):          # swap rows so the pivot is the larger entry
        a, c, b0, d, e, b1 = d, e, b1, a, c, b0
    m = chop(d / a)                        # multiplier
    e = chop(e - chop(m * c))             # eliminate below the pivot
    b1 = chop(b1 - chop(m * b0))
    x1 = chop(b1 / e)                      # back-substitute
    x0 = chop((b0 - chop(c * x1)) / a)    # a and c now hold the working row 0
    return [x0, x1]


def residual(A, b, x):
    """b - A*x, computed exactly. This is what backward error measures."""
    return [b[0] - (A[0][0] * x[0] + A[0][1] * x[1]),
            b[1] - (A[1][0] * x[0] + A[1][1] * x[1])]


# A system with a tiny entry in the top-left corner. The true answer is about
# x = [1.0001, 0.9999]. Watch what each method's answer actually solves.
A = [[0.0001, 1.0],
     [1.0,    1.0]]
b = [1.0, 2.0]

for label, use_pivot in [("WITHOUT pivoting", False), ("WITH pivoting", True)]:
    x = solve_2x2(A, b, use_pivot)
    r = residual(A, b, x)
    r_str = "[" + ", ".join(f"{v:.4g}" for v in r) + "]"
    print(f"{label}:")
    print(f"  computed answer x = {x}")
    print(f"  forward view : that is off from the true [1.0001, 0.9999]")
    print(f"  backward view: x exactly solves A*x = b - {r_str}")
    print(f"                 so the data was effectively nudged by {max(abs(v) for v in r):g}")
    print()

print("Same algorithm, same arithmetic. Pivoting nudges the data by a hair;")
print("skipping it rewrites the problem entirely. Backward error sees the")
print("difference that forward error alone could not explain.")

"""
Backward error analysis — the core idea (J. H. Wilkinson, 1960s)

When a computer solves a problem in finite precision, the answer it gives is
almost never the exact answer. The old question was: "how wrong is the answer?"
(forward error). That question is often hard and the news is often bad.

Wilkinson asked a different question: "for what problem is this answer exactly
right?" (backward error). His insight: a good algorithm returns the EXACT
solution to a problem that is only slightly different from the one you asked.

If that nearby problem is close enough (a change the size of the rounding
itself), the algorithm did nothing wrong. Any error in the answer is the fault
of the problem being sensitive, not the algorithm being sloppy.
"""

# Before Wilkinson: people feared rounding errors in Gaussian elimination would
#   pile up across the ~n^3 operations and make large systems unsolvable. The
#   pessimism was so deep that solving a 100x100 system seemed hopeless.
# After Wilkinson: backward error analysis showed the computed answer is the
#   exact solution of (A + E)x = b with E tiny. The algorithm is trustworthy;
#   any inaccuracy is the conditioning of the problem talking.

from math import log10, floor


def round_sig(x, sig=4):
    """Round x to `sig` significant digits — our stand-in for a finite machine."""
    if x == 0:
        return 0.0
    return round(x, sig - int(floor(log10(abs(x)))) - 1)


# A mildly ill-conditioned 2x2 system. The true solution is x = [1, -2].
A = [[3.0, 1.0],
     [1.0, 0.333]]
b = [1.0, 0.334]
x_true = [1.0, -2.0]

# ── Solve it on a 4-significant-digit "machine" (Gaussian elimination) ─────────
# Round after every multiply and subtract, exactly as a finite machine would.
m = round_sig(A[1][0] / A[0][0])              # multiplier
a22 = round_sig(A[1][1] - round_sig(m * A[0][1]))
b2 = round_sig(b[1] - round_sig(m * b[0]))
x2 = round_sig(b2 / a22)
x1 = round_sig((b[0] - round_sig(A[0][1] * x2)) / A[0][0])
x_hat = [x1, x2]

# ── Forward error: how far the computed answer is from the truth ──────────────
fwd = max(abs(x_hat[i] - x_true[i]) for i in range(2))

# ── Backward error: plug the computed answer back in, see what problem it solves
# r = b - A x_hat. The computed x_hat is the EXACT solution of A x = b - r,
# i.e. a problem whose right-hand side differs from b by only r.
Ax = [A[0][0] * x_hat[0] + A[0][1] * x_hat[1],
      A[1][0] * x_hat[0] + A[1][1] * x_hat[1]]
r = [b[0] - Ax[0], b[1] - Ax[1]]
bwd = max(abs(ri) for ri in r) / max(abs(bi) for bi in b)

print("Solving Ax = b on a 4-digit machine")
print(f"  true solution    x = {x_true}")
print(f"  computed answer  x = {x_hat}")
print()
print(f"  forward error  (how wrong the answer is):     {fwd:.3f}   <- large")
print(f"  backward error (how wrong the question is):   {bwd:.1e}   <- tiny")
print()
print("The answer is off by a lot. But it is the EXACT solution to")
print(f"  A x = {[round(bi - ri, 6) for bi, ri in zip(b, r)]}")
print(f"which differs from the b we asked for, {b}, by almost nothing.")
print()
print("The machine did its job perfectly. The system was just sensitive.")
print("That reframing is backward error analysis.")

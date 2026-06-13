"""
Backward error analysis — the core idea (J. H. Wilkinson, 1960s)

The old question (FORWARD error): "How far is my computed answer from the
  true answer?" Hard to bound, because it depends on how touchy the problem is.

Wilkinson's question (BACKWARD error): "What problem did my computed answer
  solve EXACTLY?" If a tiny change to the input would make the answer correct,
  the algorithm did its job. The size of that change is the backward error.

A good algorithm keeps the backward error small. Whether the answer is also
close to the truth then depends on the problem, not the algorithm.
"""

from math import floor, log10


def chop(x, sig=3):
    """Round to `sig` significant digits — a 1950s 'floating point' word."""
    if x == 0:
        return 0.0
    return round(x, sig - 1 - floor(log10(abs(x))))


# Solve A x = b keeping only 3 significant digits at every step.
# The exact answer is x = [11/7, 6/7] = [1.5714..., 0.8571...], which does not
# fit in 3 digits, so roundoff has to creep in somewhere.
A = [[2.0, 1.0],
     [1.0, 4.0]]
b = [4.0, 5.0]
x_true = [11 / 7, 6 / 7]

# Gaussian elimination, chopping each result to 3 digits.
m   = chop(A[1][0] / A[0][0])                 # multiplier = 0.5
a22 = chop(A[1][1] - chop(m * A[0][1]))       # eliminate x1 from row 2
b2  = chop(b[1]    - chop(m * b[0]))
x2  = chop(b2 / a22)                          # 0.857142... -> 0.857
x1  = chop((b[0] - chop(A[0][1] * x2)) / A[0][0])
x_hat = [x1, x2]

# FORWARD error: how far the computed answer is from the truth.
fwd = max(abs(x_hat[i] - x_true[i]) for i in range(2))

# BACKWARD error: the residual r = b - A x_hat. It is exactly how much you would
# have to nudge b for x_hat to be the perfect answer — measurable without ever
# knowing the true x.
r = [b[i] - (A[i][0] * x_hat[0] + A[i][1] * x_hat[1]) for i in range(2)]
bwd = max(abs(ri) for ri in r)

print("computed x :", x_hat)
print("true x     :", [round(v, 6) for v in x_true])
print(f"forward error  (answer off by)   : {fwd:.4f}")
print(f"backward error (residual b - Ax) : {bwd:.4f}")
print()
print(f"The computed answer EXACTLY solves the system with b changed from")
print(f"  {b}  to  {[round(b[i] - r[i], 4) for i in range(2)]}.")
print("That nudge is tiny, so the algorithm did its job. Both errors are small")
print("here because the problem is well-conditioned. When they diverge, the")
print("gap between them is the problem's sensitivity, not the algorithm's fault.")

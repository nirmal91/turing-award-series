"""
Backward error analysis — the core idea (J. H. Wilkinson, 1960s)

A computer cannot store most real numbers exactly, and every arithmetic
operation rounds the result a little. The old way to judge a calculation
was the FORWARD error: how far is the computed answer from the true one?
Tracked through a long calculation that bound balloons, and by its logic
you could never trust a machine to solve anything hard.

Wilkinson turned the question around. Do not ask how wrong the ANSWER is.
Ask how small a change to the INPUTS would make the computed answer exactly
right. If that change is far smaller than the uncertainty already in your
data, the algorithm did nothing wrong. It solved a problem sitting right
next to the one you posed. That gap is the BACKWARD error, and for a good
algorithm it stays near machine precision even when the forward error is huge.
"""

from fractions import Fraction


def solve(A, b):
    """Plain Gaussian elimination in floating point. Returns x with A x = b."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]   # augmented matrix
    for k in range(n):
        for i in range(k + 1, n):
            f = M[i][k] / M[k][k]
            for j in range(k, n + 1):
                M[i][j] -= f * M[k][j]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = M[i][n] - sum(M[i][j] * x[j] for j in range(i + 1, n))
        x[i] = s / M[i][i]
    return x


def hilbert(n):
    """The Hilbert matrix H[i][j] = 1/(i+j+1). Famously close to singular."""
    return [[1.0 / (i + j + 1) for j in range(n)] for i in range(n)]


# ── A calculation that looks like it failed, but didn't ─────────────────────────

n = 12
A = hilbert(n)
x_true = [1.0] * n                                   # the answer we want back
b = [sum(A[i][j] * x_true[j] for j in range(n)) for i in range(n)]

x = solve(A, b)                                      # what the machine computes

# Forward error: distance from the true answer. Large, because Hilbert is nasty.
forward = max(abs(x[i] - x_true[i]) for i in range(n))

# Backward error: the residual b - A x. Plug the computed x back in and see how
# far it lands from b. A tiny residual means x is the EXACT solution of a system
# (A, b + r) that sits a hair away from the one we actually asked.
r = [b[i] - sum(A[i][j] * x[j] for j in range(n)) for i in range(n)]
backward = max(abs(ri) for ri in r)

print(f"computed x:     {[round(v, 3) for v in x]}")
print(f"true x:         {x_true}")
print(f"forward error:  {forward:.2e}   how wrong the ANSWER is")
print(f"backward error: {backward:.2e}   how wrong the QUESTION would have to be")
print()
print("Same computed answer, two verdicts.")
print("Forward error says 'untrustworthy.'")
print("Backward error says 'this exactly solved a problem next door.'")
print("Wilkinson showed the second number is the honest one to judge an algorithm by.")

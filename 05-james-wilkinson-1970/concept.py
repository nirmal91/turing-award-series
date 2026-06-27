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

def solve(A, b):
    """Plain Gaussian elimination in floating point. Returns x with A x = b.

    Inputs:
      A  the coefficient grid: a list of rows, one row per equation.
      b  the right-hand sides: a flat list of numbers, one per equation.
      x  the unknowns we solve for and return.

    Example. For the 3-equation system
        2x + 1y + 1z = 8
        1x + 3y + 2z = 13
        1x + 0y + 0z = 2
    you call solve(A, b) with
        A = [[2, 1, 1],
             [1, 3, 2],
             [1, 0, 0]]
        b = [8, 13, 2]
    """
    n = len(b)

    # Augmented matrix M: weld b onto A as one extra column so that every row
    # operation below sweeps the right-hand side too and the equations stay
    # intact. For the example above, M becomes
    #     [[2, 1, 1,  8],
    #      [1, 3, 2, 13],
    #      [1, 0, 0,  2]]
    #
    # Mechanics of the line below:
    #   enumerate(A)  -> yields (i, row) pairs: the index and that row of A
    #   row[:]        -> a COPY of the row, so editing M never touches A
    #   + [b[i]]      -> joins two lists, appending this row's b value on the end
    M = [row[:] + [b[i]] for i, row in enumerate(A)]

    # Elimination: drive M down to an upper triangle (zeros below the diagonal).
    # k is the pivot row. For each pivot we look at every row BELOW it and
    # cancel the column-k variable out of that lower row.
    #
    # Note: this is plain elimination with no pivoting, on purpose, to keep the
    # idea simple. A zero on the diagonal (e.g. [[0, 1], [1, 0]]) would divide by
    # zero here. implementation.py adds partial pivoting to handle that safely.
    for k in range(n):
        for i in range(k + 1, n):
            # Compare the lower row (i) against the pivot row (k) on the one
            # variable we are cancelling, column k. f is the ratio between them:
            # how many pivot rows fit into row i at that spot. Subtracting
            # f * (pivot row) from row i then makes its column-k entry zero.
            #
            # Example, first pivot of the system in the docstring above:
            #   pivot row 0 has 2x, row 1 has 1x  ->  f = 1 / 2 = 0.5
            #   so we subtract half of row 0 from row 1 to kill its x.
            f = M[i][k] / M[k][k]

            # Apply that subtraction across the whole row, including the b column
            # at the end, so the equation stays balanced.
            for j in range(k, n + 1):
                M[i][j] -= f * M[k][j]
    # Back-substitution: climb from the bottom row upward. By the time we reach a
    # row, every variable to its right is already solved, so the row has just one
    # unknown left. Subtract the known parts, then divide by the diagonal.
    x = [0.0] * n                      # answers, filled in as we go
    for i in range(n - 1, -1, -1):     # range(n-1, -1, -1) counts DOWN: n-1, ..., 0
        # M[i][n] is this row's b value. The sum is the already-solved variables
        # to the right (columns i+1 .. n-1), moved over to the other side.
        s = M[i][n] - sum(M[i][j] * x[j] for j in range(i + 1, n))
        x[i] = s / M[i][i]             # divide by the diagonal to isolate x[i]
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

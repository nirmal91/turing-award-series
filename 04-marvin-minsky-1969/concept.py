"""
Perceptrons — the core idea (Minsky & Papert, 1969)

A single-layer perceptron draws one straight line through the input space.
Any problem separable by one line, it can learn.
Any problem that cannot — it never will, no matter how long you train it.

XOR is one such problem. Minsky and Papert proved this formally in 1969.
"""

# Before (1958-1969): Rosenblatt's perceptron convergence theorem guaranteed
#   it would learn any linearly separable function. People assumed more epochs
#   or more data could handle everything else.
# After (1969): Minsky & Papert proved single-layer networks are bounded by
#   geometry. XOR, parity, connectivity — all impossible for one layer.


def step(z):
    return 1 if z >= 0 else 0


def perceptron_train(examples, max_epochs=10000):
    w1, w2, b = 0.0, 0.0, 0.0
    for _ in range(max_epochs):
        mistakes = 0
        for (x1, x2), label in examples:
            pred = step(w1 * x1 + w2 * x2 + b)
            if pred != label:
                delta = label - pred
                w1 += delta * x1
                w2 += delta * x2
                b  += delta
                mistakes += 1
        if mistakes == 0:
            break
    return w1, w2, b


# ── AND: linearly separable — perceptron converges ────────────────────────────

AND = [((0, 0), 0), ((0, 1), 0), ((1, 0), 0), ((1, 1), 1)]
w1, w2, b = perceptron_train(AND)
correct = sum(1 for (x1, x2), label in AND if step(w1*x1 + w2*x2 + b) == label)
print("AND (linearly separable):")
for (x1, x2), label in AND:
    pred = step(w1 * x1 + w2 * x2 + b)
    print(f"  {x1} AND {x2} = {pred}  {'ok' if pred == label else 'WRONG'}")
print(f"  {correct}/4 correct\n")

# ── XOR: not linearly separable — perceptron oscillates forever ───────────────

XOR = [((0, 0), 0), ((0, 1), 1), ((1, 0), 1), ((1, 1), 0)]
w1, w2, b = perceptron_train(XOR, max_epochs=10000)
correct = sum(1 for (x1, x2), label in XOR if step(w1*x1 + w2*x2 + b) == label)
print("XOR (not linearly separable):")
for (x1, x2), label in XOR:
    pred = step(w1 * x1 + w2 * x2 + b)
    print(f"  {x1} XOR {x2} = {pred}  (expected {label})  {'ok' if pred == label else 'WRONG'}")
print(f"  {correct}/4 correct — provably impossible to exceed 3/4 with one layer\n")

# ── The geometry ──────────────────────────────────────────────────────────────
#
# XOR plotted on a 2D grid (1 = class A, 0 = class B):
#
#     x2
#     1  |  1(0,1)    0(1,1)
#        |
#     0  |  0(0,0)    1(1,0)
#        +------------------  x1
#              0          1
#
# The 1s sit at diagonal corners. The 0s sit at the other diagonal corners.
# No straight line can put all 1s on one side and all 0s on the other.
# A single-layer perceptron IS a straight line. That's the limitation.
#
# A hidden layer solves this by creating new coordinates — a new space
# where the XOR points ARE linearly separable.

print("The geometry:")
print("  (0,1) and (1,0) are diagonal corners — the '1' class")
print("  (0,0) and (1,1) are the other diagonal corners — the '0' class")
print("  No straight line separates them. That's a theorem, not a bug.")

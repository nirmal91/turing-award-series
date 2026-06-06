"""
Backward error analysis — the core idea (Wilkinson, 1960s)

A computer cannot add a long list of numbers exactly. Every operation rounds.
The old way to judge the damage was the forward error: how far is the computed
answer from the true answer? Those bounds grew so fast with the number of
operations that they suggested most real computations were worthless.

Wilkinson asked a different question. Instead of "how wrong is my answer", he
asked: "for what slightly different INPUT would my answer be exactly right?"

The computed sum turns out to be the EXACT sum of the inputs, each nudged by a
tiny amount. If those nudges are no larger than the rounding you already accept
when you store the numbers, the algorithm is as good as arithmetic allows. The
error stops being a mysterious property of the algorithm and becomes a property
of the data you fed it.
"""

from decimal import Decimal, localcontext

DIGITS = 4  # our toy machine keeps 4 significant decimal figures per operation

xs = [Decimal("1"), Decimal("0.0001"), Decimal("0.0001"),
      Decimal("0.0001"), Decimal("0.0001")]

# Run the sum on the toy machine, recording every partial sum it produced.
with localcontext() as ctx:
    ctx.prec = DIGITS
    partials = [+xs[0]]
    for x in xs[1:]:
        partials.append(partials[-1] + x)      # rounds to DIGITS each step
computed = partials[-1]

# The exact sum, for reference (50 digits is "infinite precision" here).
with localcontext() as ctx:
    ctx.prec = 50
    exact = sum(xs[1:], xs[0])

    # Backward analysis. Each step j rounded, introducing a relative error eps_j:
    #     partial_j = (partial_{j-1} + x_j) * (1 + eps_j).
    # Propagate those forward and the computed sum equals  sum_i x_i*(1 + delta_i),
    # where delta_i collects the rounding of every step that x_i passed through.
    eps = [partials[j] / (partials[j-1] + xs[j]) - 1 for j in range(1, len(xs))]
    deltas = []
    for i in range(len(xs)):
        prod = Decimal(1)
        start = 1 if i == 0 else i            # x[0] and x[1] ride through every step
        for k in range(start, len(xs)):
            prod *= (1 + eps[k - 1])
        deltas.append(prod - 1)
    reconstructed = sum((xs[i] * (1 + deltas[i]) for i in range(len(xs))), Decimal(0))

print(f"Toy machine: {DIGITS} significant digits per addition\n")
print(f"  inputs:        {[str(x) for x in xs]}")
print(f"  exact sum:     {exact}")
print(f"  computed sum:  {computed}      (rounding swallowed the small terms)")
print(f"  forward error: {abs(computed - exact)}\n")

print("Backward view — the computed sum is the EXACT sum of perturbed inputs:")
for i, (x, d) in enumerate(zip(xs, deltas)):
    print(f"    x{i} = {x:<8} ->  perturbed by {d:+.2e}")
print(f"\n  largest input nudge needed: {max(abs(d) for d in deltas):.2e}")
print(f"  reconstruction matches computed sum to {abs(reconstructed - computed):.0e}\n")

print("The forward error looks alarming. The backward error is tiny.")
print("If you don't know your inputs to better than that nudge, the answer is")
print("as good as the data deserves. That reframing is Wilkinson's whole idea.")

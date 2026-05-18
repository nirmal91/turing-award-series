"""
Perceptrons and their limits — full implementation (Minsky & Papert, 1969)

Usage:
    python implementation.py               # interactive demo
    python implementation.py --test        # test suite (14 cases)
    python implementation.py --verbose     # show weights and training progress

Before the Perceptrons proof (1969): people assumed single-layer networks
could learn anything given enough training time.
After: Minsky & Papert proved that XOR, parity, and connectivity are
geometrically inaccessible to any single-layer network — not hard, impossible.
That proof forced the field to develop multi-layer networks and, eventually,
backpropagation to train them.
"""

import sys
import math
import random


# ── Single-layer perceptron (Rosenblatt, 1958) ────────────────────────────────
#
# Learns with the perceptron learning rule: if a prediction is wrong,
# nudge weights toward the correct answer by the error amount.
# Guaranteed to converge in finite steps if and only if the data is linearly
# separable (Rosenblatt's convergence theorem).

class Perceptron:
    def __init__(self, n_inputs):
        self.weights = [0.0] * n_inputs
        self.bias = 0.0

    def predict(self, x):
        total = sum(w * xi for w, xi in zip(self.weights, x)) + self.bias
        return 1 if total >= 0 else 0

    def train(self, data, max_epochs=1000, lr=1.0, verbose=False):
        """
        Returns epochs used. If max_epochs reached without convergence,
        the data is not linearly separable.
        """
        for epoch in range(max_epochs):
            errors = 0
            for x, label in data:
                pred = self.predict(x)
                if pred != label:
                    diff = label - pred
                    self.weights = [w + lr * diff * xi for w, xi in zip(self.weights, x)]
                    self.bias += lr * diff
                    errors += 1
            if verbose:
                acc = self.accuracy(data)
                print(f"    epoch {epoch+1:4d}: {errors} errors, acc={acc:.2f}, "
                      f"w={[f'{w:.3f}' for w in self.weights]}, b={self.bias:.3f}")
            if errors == 0:
                return epoch + 1
        return max_epochs

    def accuracy(self, data):
        return sum(1 for x, y in data if self.predict(x) == y) / len(data)


# ── Two-layer network with backpropagation ────────────────────────────────────
#
# Layer 1 (hidden): learns intermediate features — new coordinates that
#   reshape the input space so XOR becomes linearly separable.
# Layer 2 (output): combines those features into a final prediction.
#
# Trained with gradient descent (backpropagation — Rumelhart, Hinton,
# Williams 1986). Backprop is the algorithm that solved the training problem
# Minsky's book implicitly posed: how do you update hidden layer weights
# when you only observe the output error?

def sigmoid(z):
    # clamp to avoid overflow
    z = max(-500, min(500, z))
    return 1.0 / (1.0 + math.exp(-z))

def sigmoid_deriv(a):
    return a * (1.0 - a)


class TwoLayerNet:
    def __init__(self, n_inputs=2, n_hidden=2, seed=42):
        rng = random.Random(seed)
        # hidden layer: n_hidden neurons, each with n_inputs weights + bias
        self.w1 = [[rng.uniform(-1, 1) for _ in range(n_inputs)] for _ in range(n_hidden)]
        self.b1 = [rng.uniform(-1, 1) for _ in range(n_hidden)]
        # output layer: 1 neuron with n_hidden weights + bias
        self.w2 = [rng.uniform(-1, 1) for _ in range(n_hidden)]
        self.b2 = rng.uniform(-1, 1)

    def forward(self, x):
        """Returns (hidden activations, output activation)."""
        h = [
            sigmoid(sum(self.w1[j][i] * x[i] for i in range(len(x))) + self.b1[j])
            for j in range(len(self.w1))
        ]
        out = sigmoid(sum(self.w2[j] * h[j] for j in range(len(h))) + self.b2)
        return h, out

    def predict(self, x):
        _, out = self.forward(x)
        return 1 if out >= 0.5 else 0

    def train(self, data, epochs=10000, lr=1.0, verbose=False):
        for epoch in range(epochs):
            total_loss = 0.0
            for x, label in data:
                h, out = self.forward(x)
                total_loss += 0.5 * (label - out) ** 2

                # output layer delta
                d_out = -(label - out) * sigmoid_deriv(out)

                # hidden layer deltas (backpropagate output error)
                d_h = [d_out * self.w2[j] * sigmoid_deriv(h[j]) for j in range(len(h))]

                # update output layer
                self.w2 = [self.w2[j] - lr * d_out * h[j] for j in range(len(h))]
                self.b2 -= lr * d_out

                # update hidden layer
                for j in range(len(h)):
                    self.w1[j] = [self.w1[j][i] - lr * d_h[j] * x[i] for i in range(len(x))]
                    self.b1[j] -= lr * d_h[j]

            if verbose and (epoch + 1) % 2000 == 0:
                acc = self.accuracy(data)
                print(f"    epoch {epoch+1:6d}: loss={total_loss:.4f}, acc={acc:.2f}")

    def accuracy(self, data):
        return sum(1 for x, y in data if self.predict(x) == y) / len(data)


# ── Datasets ──────────────────────────────────────────────────────────────────

DATASETS = {
    'AND':  [([0, 0], 0), ([0, 1], 0), ([1, 0], 0), ([1, 1], 1)],
    'OR':   [([0, 0], 0), ([0, 1], 1), ([1, 0], 1), ([1, 1], 1)],
    'NAND': [([0, 0], 1), ([0, 1], 1), ([1, 0], 1), ([1, 1], 0)],
    'NOR':  [([0, 0], 1), ([0, 1], 0), ([1, 0], 0), ([1, 1], 0)],
    'XOR':  [([0, 0], 0), ([0, 1], 1), ([1, 0], 1), ([1, 1], 0)],
    'XNOR': [([0, 0], 1), ([0, 1], 0), ([1, 0], 0), ([1, 1], 1)],
}


# ── Interactive demo ──────────────────────────────────────────────────────────

def show_table(name, data, predict_fn):
    correct = 0
    rows = []
    for x, label in data:
        pred = predict_fn(x)
        mark = "ok" if pred == label else "WRONG"
        if pred == label:
            correct += 1
        rows.append(f"    {x[0]} {x[1]} → {pred}  (expected {label})  {mark}")
    print(f"  {name}:")
    for r in rows:
        print(r)
    return correct == len(data)


def demo(verbose=False):
    print("Perceptrons — Minsky & Papert (1969)")
    print("="*50)
    print("Single-layer perceptron learns AND and OR.")
    print("It cannot learn XOR. Not with more data. Not with more epochs.")
    print("Minsky & Papert proved this is a geometric fact.\n")
    print("A two-layer network learns XOR by creating a hidden feature space")
    print("where XOR becomes linearly separable.\n")

    # Single-layer: linear functions
    for name in ('AND', 'OR'):
        p = Perceptron(n_inputs=2)
        if verbose:
            print(f"  Training perceptron on {name}:")
        epochs = p.train(DATASETS[name], max_epochs=100, verbose=verbose)
        passed = show_table(f"Perceptron on {name} (converged in {epochs} epoch(s))",
                            DATASETS[name], p.predict)
        print(f"  {'LEARNED' if passed else 'FAILED'}\n")

    # Single-layer: XOR (will fail to converge)
    p = Perceptron(n_inputs=2)
    if verbose:
        print("  Training perceptron on XOR:")
    p.train(DATASETS['XOR'], max_epochs=1000, verbose=verbose)
    acc = p.accuracy(DATASETS['XOR'])
    show_table("Perceptron on XOR (1000 epochs, never converges)",
               DATASETS['XOR'], p.predict)
    print(f"  FAILED  (accuracy {acc:.0%}  — best any single-layer net can do on XOR)\n")

    # Two-layer: XOR
    net = TwoLayerNet(n_inputs=2, n_hidden=2, seed=0)
    if verbose:
        print("  Training two-layer network on XOR:")
    net.train(DATASETS['XOR'], epochs=10000, lr=1.0, verbose=verbose)
    passed = show_table("Two-layer net on XOR (10000 epochs, backprop)",
                        DATASETS['XOR'], net.predict)
    print(f"  {'LEARNED' if passed else 'FAILED'}\n")

    if verbose:
        print("  Final hidden layer weights:")
        for j, (ws, b) in enumerate(zip(net.w1, net.b1)):
            print(f"    h{j+1}: w={[f'{w:.3f}' for w in ws]}, b={b:.3f}")
        print(f"  Output layer: w={[f'{w:.3f}' for w in net.w2]}, b={net.b2:.3f}")
        print()
        print("  Hidden activations for each XOR input:")
        for x, label in DATASETS['XOR']:
            h, out = net.forward(x)
            print(f"    input={x}: h=[{h[0]:.3f}, {h[1]:.3f}], out={out:.3f} → {1 if out>=0.5 else 0}")
        print()

    print("The single-layer failure on XOR is not a training bug.")
    print("No weights exist that classify all four XOR cases correctly.")
    print("The hidden layer creates a new feature space where they are separable.")


# ── Test suite ────────────────────────────────────────────────────────────────

def run_tests():
    passed = 0
    failed = 0

    def check(name, got, expected):
        nonlocal passed, failed
        if got == expected:
            print(f"  PASS  {name}")
            passed += 1
        else:
            print(f"  FAIL  {name}: got {got!r}, expected {expected!r}")
            failed += 1

    # 1. Perceptron learns AND
    p = Perceptron(n_inputs=2)
    p.train(DATASETS['AND'], max_epochs=100)
    check("perceptron AND: 100% accuracy", p.accuracy(DATASETS['AND']), 1.0)

    # 2. Perceptron learns OR
    p = Perceptron(n_inputs=2)
    p.train(DATASETS['OR'], max_epochs=100)
    check("perceptron OR: 100% accuracy", p.accuracy(DATASETS['OR']), 1.0)

    # 3. Perceptron learns NAND
    p = Perceptron(n_inputs=2)
    p.train(DATASETS['NAND'], max_epochs=100)
    check("perceptron NAND: 100% accuracy", p.accuracy(DATASETS['NAND']), 1.0)

    # 4. Perceptron learns NOR
    p = Perceptron(n_inputs=2)
    p.train(DATASETS['NOR'], max_epochs=100)
    check("perceptron NOR: 100% accuracy", p.accuracy(DATASETS['NOR']), 1.0)

    # 5. Perceptron cannot learn XOR (accuracy < 1.0 — the Minsky-Papert theorem)
    p = Perceptron(n_inputs=2)
    p.train(DATASETS['XOR'], max_epochs=1000)
    check("perceptron XOR: cannot reach 100%", p.accuracy(DATASETS['XOR']) < 1.0, True)

    # 6. Perceptron cannot learn XNOR (same reason — not linearly separable)
    p = Perceptron(n_inputs=2)
    p.train(DATASETS['XNOR'], max_epochs=1000)
    check("perceptron XNOR: cannot reach 100%", p.accuracy(DATASETS['XNOR']) < 1.0, True)

    # 7. Two-layer net learns XOR
    net = TwoLayerNet(n_inputs=2, n_hidden=2, seed=0)
    net.train(DATASETS['XOR'], epochs=10000, lr=1.0)
    check("two-layer net XOR: 100% accuracy", net.accuracy(DATASETS['XOR']), 1.0)

    # 8. Two-layer net learns XNOR
    net = TwoLayerNet(n_inputs=2, n_hidden=2, seed=99)
    net.train(DATASETS['XNOR'], epochs=10000, lr=1.0)
    check("two-layer net XNOR: 100% accuracy", net.accuracy(DATASETS['XNOR']), 1.0)

    # 9. Two-layer net also learns AND (multi-layer is strictly more powerful)
    net = TwoLayerNet(n_inputs=2, n_hidden=2, seed=7)
    net.train(DATASETS['AND'], epochs=5000, lr=0.5)
    check("two-layer net AND: 100% accuracy", net.accuracy(DATASETS['AND']), 1.0)

    # 10. Sigmoid outputs are always strictly in (0, 1)
    net = TwoLayerNet(n_inputs=2, n_hidden=2, seed=1)
    for x, _ in DATASETS['XOR']:
        _, out = net.forward(x)
        check(f"sigmoid output in (0,1) for input {x}", 0.0 < out < 1.0, True)

    # 14. Perceptron: no weight update when prediction matches label
    p = Perceptron(n_inputs=2)
    p.weights = [0.0, 0.0]
    p.bias = 0.0
    w_before = p.weights[:]
    p.train([([1, 1], 1)], max_epochs=1)  # step(0+0+0=0) >= 0 → pred=1, label=1, no update
    check("no weight update when prediction is correct", p.weights, w_before)

    # 15. Perceptron: weights move toward correct label on error
    p = Perceptron(n_inputs=2)
    p.weights = [0.0, 0.0]
    p.bias = -1.0  # step(0+0-1) = step(-1) → pred=0, but label=1 → update
    p.train([([1, 1], 1)], max_epochs=1)
    check("weights updated toward correct label", p.weights[0] > 0, True)

    print(f"\n  {passed} passed, {failed} failed")
    return failed == 0


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    verbose = '--verbose' in sys.argv

    if '--test' in sys.argv:
        print("Running test suite...\n")
        ok = run_tests()
        sys.exit(0 if ok else 1)
    else:
        demo(verbose)

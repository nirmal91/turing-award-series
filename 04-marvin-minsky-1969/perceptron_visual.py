"""
Perceptron decision boundary — terminal animation (Minsky & Papert, 1969)

Watch the boundary converge on AND, then oscillate forever on XOR.
Green = correctly classified. Red = misclassified. Yellow = boundary line.

Usage:
    python perceptron_visual.py          # animated
    python perceptron_visual.py --fast   # faster
"""

import sys
import time

# ANSI
CLR = '\033[2J\033[H'
GRN = '\033[92m'
RED = '\033[91m'
YEL = '\033[93m'
DIM = '\033[2m'
RST = '\033[0m'
BLD = '\033[1m'

W, H   = 54, 22
X_LO, X_HI = -0.4, 1.4
Y_LO, Y_HI = -0.4, 1.4


def grid_pos(x1, x2):
    col = round((x1 - X_LO) / (X_HI - X_LO) * (W - 1))
    row = round((1 - (x2 - Y_LO) / (Y_HI - Y_LO)) * (H - 1))
    return row, col


def render(w1, w2, b, epoch, data, title):
    dx = (X_HI - X_LO) / W
    dy = (Y_HI - Y_LO) / H
    threshold = (abs(w1) * dx + abs(w2) * dy) * 0.85

    cells = [[(None, RST)] * W for _ in range(H)]

    for r in range(H):
        x2 = Y_HI - (r / (H - 1)) * (Y_HI - Y_LO)
        for c in range(W):
            x1 = X_LO + (c / (W - 1)) * (X_HI - X_LO)
            score = w1 * x1 + w2 * x2 + b
            if threshold > 0 and abs(score) < threshold:
                cells[r][c] = ('|', YEL)
            elif score >= 0:
                cells[r][c] = ('·', DIM)
            else:
                cells[r][c] = (' ', RST)

    for (x1, x2), label in data:
        pred = 1 if w1 * x1 + w2 * x2 + b >= 0 else 0
        r, c = grid_pos(x1, x2)
        color = GRN + BLD if pred == label else RED + BLD
        cells[r][c] = (str(label), color)

    n_correct = sum(
        1 for (xy, label) in data
        if (1 if w1 * xy[0] + w2 * xy[1] + b >= 0 else 0) == label
    )

    lines = [
        f"{BLD}{title}{RST}   epoch {epoch:3d}   acc {n_correct}/{len(data)}",
        f"  w=[{w1:+.3f}, {w2:+.3f}]  b={b:+.3f}",
        "",
    ]
    for r in range(H):
        row_str = "  "
        for c in range(W):
            ch, color = cells[r][c]
            row_str += color + ch + RST
        lines.append(row_str)
    lines += [
        "",
        f"  {GRN}green{RST} = correct   {RED}red{RST} = wrong   {YEL}yellow{RST} = decision boundary",
    ]
    return "\n".join(lines)


def train_and_show(data, title, max_epochs=60, delay=0.15):
    w1, w2, b = 0.0, 0.0, 0.0

    for epoch in range(max_epochs):
        errors = 0
        for (x1, x2), label in data:
            pred = 1 if w1 * x1 + w2 * x2 + b >= 0 else 0
            if pred != label:
                diff = label - pred
                w1 += diff * x1
                w2 += diff * x2
                b  += diff
                errors += 1

        print(CLR + render(w1, w2, b, epoch + 1, data, title), flush=True)
        time.sleep(delay)

        if errors == 0:
            print(f"\n  {GRN}{BLD}Converged.{RST} Boundary is stable.\n", flush=True)
            time.sleep(2.0)
            return

    print(
        f"\n  {RED}{BLD}Did not converge after {max_epochs} epochs.{RST}"
        f"\n  {title} is not linearly separable — no boundary can classify all points.",
        flush=True,
    )
    time.sleep(2.5)


AND_data = [((0, 0), 0), ((0, 1), 0), ((1, 0), 0), ((1, 1), 1)]
OR_data  = [((0, 0), 0), ((0, 1), 1), ((1, 0), 1), ((1, 1), 1)]
XOR_data = [((0, 0), 0), ((0, 1), 1), ((1, 0), 1), ((1, 1), 0)]

fast  = "--fast" in sys.argv
delay = 0.05 if fast else 0.15

print(CLR + f"{BLD}Perceptron decision boundary — Minsky & Papert (1969){RST}\n")
print("The perceptron learning rule moves a hyperplane through the input space.")
print("If a straight line can separate the classes, it finds one.")
print("If not, it oscillates forever — that's the theorem.\n")
time.sleep(2.0)

train_and_show(AND_data, "AND — linearly separable", max_epochs=25, delay=delay)
train_and_show(OR_data,  "OR  — linearly separable", max_epochs=25, delay=delay)
train_and_show(XOR_data, "XOR — NOT linearly separable", max_epochs=50, delay=delay)

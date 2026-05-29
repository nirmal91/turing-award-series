# Week 04 — Marvin Minsky (1969)

**ACM Turing Award citation:** *"For his central role in creating the science of artificial intelligence."*

---

## My Take

Marvin Minsky, along with John McCarthy, was hugely pivotal in starting AI as a field. They organized the Dartmouth conference in 1956, got the best minds in the room, named the discipline of AI, and then went off and built the two institutions that shaped everything after: Minsky at MIT, McCarthy at Stanford. The MIT AI Lab is still running today as CSAIL.

The first highlight is moving from flat lists of rules to structured knowledge. Before his frames paper, AI systems stored knowledge as giant if-then rule lists, which doesn't scale well. Minsky's intuition was that this is very different than how humans think. When you see a chair, your brain doesn't rederive what a chair is from scratch every time — it has a mental template made up of four legs, a back, a seat, some material, and you fill in the details. He called that idea of structure "frames": structured objects with named slots and defaults. This is how most programming languages work today in terms of classes and objects.

The second, and the more important one, is his book on perceptrons and their limitations. Rosenblatt's single-layer network was the hot AI thing in 1958, and there was a lot of optimism that you could scale this infinitely and solve intelligence. Minsky was the party pooper and proved mathematically that regardless of data size or compute, a single layer isn't enough for a computer to understand even a basic operation like XOR. This did play a big role in the first AI winter: funding dried up, research stalled, the whole neural network agenda lost momentum for nearly a decade. Minsky, to his credit, also explicitly said that multi-layer networks wouldn't have this problem and pushed researchers towards training them. Backpropagation for multi-layer networks arrived in 1986, which was a big unlock, followed by deep learning. The AI era we know today — H100 clusters, hyperscalers, Mag-7, all training the next frontier models — all of it traces back to Minsky pushing the world towards multi-layer networks.

---

## The Code

[`concept.py`](./concept.py) — a perceptron that learns AND, then fails on XOR, with a geometry comment explaining why.

[`implementation.py`](./implementation.py) — single-layer perceptron and two-layer network, side by side:

```
training data (AND/OR/XOR/XNOR)
    ↓
single-layer perceptron (perceptron learning rule)
    → converges in a few epochs for AND and OR
    → oscillates forever on XOR (never converges — Minsky's theorem)
    ↓
two-layer network (backpropagation, gradient descent)
    → hidden layer learns intermediate features
    → output layer combines them
    → correctly classifies all four XOR inputs
```

What it supports:
- Train and test a perceptron on AND, OR, NAND, NOR, XOR, XNOR
- Show the hard limit: any single-layer net on XOR tops out at 75%
- Train a two-layer network that solves XOR using backpropagation

```bash
python concept.py                       # the core idea, plain
python implementation.py               # full working demo
python implementation.py --test        # test suite (15 cases)
python implementation.py --verbose     # show weights and training steps
```

Example session:

```
Perceptrons — Minsky & Papert (1969)
Single-layer perceptron learns AND and OR.
It cannot learn XOR. Not with more data. Not with more epochs.
Minsky & Papert proved this is a geometric fact.

  Perceptron on AND (converged in 6 epoch(s)):
    0 0 → 0  (expected 0)  ok
    1 1 → 1  (expected 1)  ok
  LEARNED

  Perceptron on XOR (1000 epochs, never converges):
    0 0 → 1  (expected 0)  WRONG
    0 1 → 1  (expected 1)  ok
    1 0 → 0  (expected 1)  WRONG
    1 1 → 0  (expected 0)  ok
  FAILED  (accuracy 50% — best any single-layer net can do on XOR)

  Two-layer net on XOR (10000 epochs, backprop):
    0 0 → 0  (expected 0)  ok
    0 1 → 1  (expected 1)  ok
    1 0 → 1  (expected 1)  ok
    1 1 → 0  (expected 0)  ok
  LEARNED
```

---

## Full Worked Example

**Problem:** Classify all four XOR inputs correctly.

```
XOR truth table:
  0 XOR 0 = 0
  0 XOR 1 = 1
  1 XOR 0 = 1
  1 XOR 1 = 0
```

### Step 1 — Plot the inputs

Each input is a point in 2D space. Class `1` needs to be on one side of a line, class `0` on the other.

```
x2
 1  |  1 · · · · 0
    |   (0,1)   (1,1)
    |
 0  |  0 · · · · 1
    |   (0,0)   (1,0)
    +------------------  x1
         0         1
```

The `1` class sits at `(0,1)` and `(1,0)` — diagonal corners.  
The `0` class sits at `(0,0)` and `(1,1)` — the other diagonal corners.

No straight line can put `(0,1)` and `(1,0)` on one side while keeping `(0,0)` and `(1,1)` on the other. This is the core geometric fact.

### Step 2 — Try to find perceptron weights

A perceptron computes: output = 1 if `w1·x1 + w2·x2 + b ≥ 0` else 0.

The four constraints from the XOR table:

```
(0,1) → 1:   w2 + b ≥ 0       →   w2 ≥ -b
(1,0) → 1:   w1 + b ≥ 0       →   w1 ≥ -b
(0,0) → 0:   b < 0             →   b < 0
(1,1) → 0:   w1 + w2 + b < 0
```

From `b < 0`, say `b = -1`. Then from the first two constraints: `w1 ≥ 1` and `w2 ≥ 1`.  
But then `w1 + w2 + b ≥ 1 + 1 - 1 = 1 > 0`, so `(1,1)` fires — contradicting the fourth constraint.

No values of `w1`, `w2`, `b` satisfy all four constraints simultaneously. The system is inconsistent.  
This is not a numerical problem. It is a proof.

### Step 3 — The two-layer solution

The fix: add a hidden layer that computes new features, then combine them.

**Weights that solve XOR:**

```
Hidden neuron h1 (computes OR):  w=[1, 1],  b=-0.5
    (0,0): 0+0-0.5 = -0.5 → fires: NO   → h1=0
    (0,1): 0+1-0.5 =  0.5 → fires: YES  → h1=1
    (1,0): 1+0-0.5 =  0.5 → fires: YES  → h1=1
    (1,1): 1+1-0.5 =  1.5 → fires: YES  → h1=1

Hidden neuron h2 (computes NAND):  w=[-1, -1],  b=1.5
    (0,0): 0+0+1.5 =  1.5 → fires: YES  → h2=1
    (0,1): 0-1+1.5 =  0.5 → fires: YES  → h2=1
    (1,0): -1+0+1.5 = 0.5 → fires: YES  → h2=1
    (1,1): -1-1+1.5 = -0.5 → fires: NO  → h2=0
```

**New feature space** (h1, h2) for each original input:

```
original (x1,x2)  →  (h1, h2)
    (0,0) → 0        →  (0, 1)
    (0,1) → 1        →  (1, 1)
    (1,0) → 1        →  (1, 1)
    (1,1) → 0        →  (1, 0)
```

**Output neuron (computes AND of h1, h2):**  w=[1, 1],  b=-1.5

```
    (0,0) input → (h1=0, h2=1):  0+1-1.5 = -0.5 → 0  ✓ (XOR=0)
    (0,1) input → (h1=1, h2=1):  1+1-1.5 =  0.5 → 1  ✓ (XOR=1)
    (1,0) input → (h1=1, h2=1):  1+1-1.5 =  0.5 → 1  ✓ (XOR=1)
    (1,1) input → (h1=1, h2=0):  1+0-1.5 = -0.5 → 0  ✓ (XOR=0)
```

All four cases correct.

The hidden layer does not learn XOR directly. It learns two simpler features — OR and NAND — and creates a transformed space where the XOR points ARE linearly separable. The output neuron just does AND in that new space.

Minsky's proof said: you cannot do this with one layer. He was right. Two layers is the minimum.

---

## ELI5

Imagine you have four pieces of candy on a table, in the four corners of a square. Two of them — at opposite corners — are yours. The other two are your friend's.

Someone asks: can you draw one straight line so all your candy is on one side and your friend's is on the other?

You try. Every line you draw leaves at least one candy on the wrong side. You try a thousand times. It never works.

Before Minsky, people thought computers could learn any pattern if you gave them enough tries. Minsky proved some patterns — like this candy puzzle — are impossible to solve with one straight line, no matter how long you try. The machine was not slow. The problem was unsolvable that way.

---

## ELI10

In 1958, a scientist named Frank Rosenblatt built a learning machine called the perceptron. You showed it examples — this input means yes, that input means no — and it adjusted its internal numbers (weights) until it got them right. It had a mathematical guarantee: if a pattern can be separated by a straight line, the perceptron will find the weights.

The problem was the fine print. "If a pattern can be separated by a straight line" is a big restriction.

Marvin Minsky and Seymour Papert spent years in the 1960s mapping out exactly which patterns fail. Their 1969 book proved it rigorously. The simplest failing case is XOR — a function where inputs `(0,1)` and `(1,0)` output 1, while `(0,0)` and `(1,1)` output 0. If you plot those four points on a grid, the 1s sit at diagonal corners and the 0s sit at the other diagonal corners. No straight line separates them. The perceptron, which can only draw one line, cannot solve it — ever, no matter how many training rounds you run.

The book effectively ended the first era of neural network optimism and redirected the field toward multi-layer networks. With two layers, XOR is solvable — the hidden layer learns two intermediate features and reshapes the problem into one the output layer can handle with a single line. The training algorithm for multi-layer networks (backpropagation) did not arrive until 1986, which is why the gap between Minsky's proof and modern deep learning is 17 years.

---

## CS Graduate Level — Why the Perceptrons Book Mattered

### 1. The State of the Art Before (1958–1969)

Rosenblatt's perceptron (1958) came with a convergence theorem: for any linearly separable dataset, the perceptron learning rule finds correct weights in a finite number of steps. This was a genuine mathematical result, and it generated significant optimism about the prospects of neural networks.

The optimism outran the mathematics. Researchers made expansive claims about what perceptrons could eventually learn. There was no formal framework for asking: what *can't* a perceptron learn, and why?

### 2. Minsky and Papert's Contribution

The 1969 book *Perceptrons* introduced rigorous analysis of the representational capacity of single-layer networks. The central framework was **predicate analysis**: viewing perceptrons as computing Boolean predicates over their input space.

Their key theorems:

**Linear separability.** A perceptron can learn a function `f` if and only if the positive and negative examples of `f` are linearly separable — i.e., a hyperplane exists that separates the two classes. XOR is not linearly separable. Proof: the four XOR points form a configuration where any hyperplane that correctly classifies two of the positive examples `(0,1)` and `(1,0)` also incorrectly classifies at least one of the two negative examples `(0,0)` or `(1,1)`. The constraints on `w1, w2, b` are inconsistent.

**The parity problem.** A single-layer perceptron cannot compute the parity function (XOR generalised to n inputs) for any n ≥ 2. The proof uses a symmetry argument: parity is invariant under permutation of inputs, but any separating hyperplane has a unique normal vector that breaks this symmetry.

**The connectivity problem.** A single-layer perceptron with bounded-diameter local receptive fields cannot compute whether all lit pixels in a retina form a connected region. The proof showed that any perceptron computing connectivity must have receptive fields that cover the entire input — ruling out the biologically-inspired local architectures that were popular at the time.

These are not computational complexity results (the functions are easy to compute). They are **representational** results: the class of functions computable by single-layer networks is provably limited, and the limitation is geometric.

### 3. Why the Geometry Is the Proof

A perceptron computes the sign of a linear function `w·x + b`. The decision boundary is a hyperplane in the input space. Two-class classification works if and only if the two classes are linearly separable — i.e., a hyperplane exists that puts all class-0 points on one side and all class-1 points on the other.

For XOR, no such hyperplane exists. To see why algebraically: any candidate hyperplane satisfying `w1·0 + w2·1 + b ≥ 0` and `w1·1 + w2·0 + b ≥ 0` (the positive class) must satisfy `w1 + w2 + 2b ≥ 0`. But the negative class requires `w1·1 + w2·1 + b < 0`, i.e., `w1 + w2 + b < 0`. Adding the first inequality to itself: `w1 + w2 + 2b ≥ 0 → w1 + w2 ≥ -2b`. But we also need `w1 + w2 < -b`, so `-2b ≤ w1 + w2 < -b`, which requires `-2b < -b`, i.e., `b > 0`. But `b < 0` is required for the negative case `(0,0)`. Contradiction.

### 4. The Two-Layer Solution

Minsky and Papert knew that adding hidden layers broke the representational limits. The book acknowledged this explicitly but noted that no training algorithm existed for multi-layer networks — the perceptron learning rule applies only to the output layer. Updating hidden layer weights requires knowing how each hidden neuron contributes to the output error, which requires propagating the error signal backward through the network.

That algorithm — backpropagation via the chain rule of calculus — was independently derived by multiple researchers and popularised by Rumelhart, Hinton, and Williams in 1986. The key insight: automatic differentiation through a network of sigmoid units allows gradient descent on any differentiable loss function. The hidden layer of a two-layer network trained on XOR converges to computing two linearly separable features (e.g., OR and NAND) whose combination solves XOR in the output layer.

The **universal approximation theorem** (Hornik, Stinchcombe, White, 1989) later formalised what two-layer networks can do: any continuous function on a compact domain can be approximated arbitrarily closely by a single hidden layer of sufficient width. The Minsky-Papert limitation applies only to the single-layer case.

### 5. What Descended From It

**Multi-layer perceptrons (1980s).** The direct response to the book's implicit challenge. Backpropagation made training possible, and networks with one or two hidden layers began solving practical problems.

**Deep learning (2006+).** Stacking many hidden layers — enabled by GPUs, large datasets, and architectural improvements (ReLU activations, dropout, batch normalisation) — produced the systems that define modern AI. GPT, DALL-E, AlphaFold, and every major neural network system today is a direct descendant.

**Support vector machines (Vapnik, 1995).** An alternative approach to the linearity problem: map the input to a high-dimensional feature space where it becomes linearly separable (the kernel trick). Conceptually similar to what a hidden layer does, but with different training mechanics and theoretical guarantees.

**VC dimension and learning theory.** The Perceptrons book's rigorous approach to representational limits contributed to the development of Vapnik-Chervonenkis theory — the foundational framework for understanding the generalisation capacity of machine learning models.

### 6. The Historical Irony

Minsky and Papert's book is often described as having "killed" neural network research in the 1970s and caused the first AI winter. The characterisation is partially accurate but incomplete. The book correctly identified that single-layer networks are limited. It acknowledged that multi-layer networks are not. The practical obstacle was the training algorithm for multi-layer networks — which took 17 more years to popularise.

The irony is that the most rigorous critique of early neural networks also produced the clearest statement of what a neural network would need to do to be more powerful. When backpropagation arrived, it gave researchers exactly what the Minsky-Papert proof said was missing. Every modern neural network is, in a sense, the answer to their 1969 theorem.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [Perceptrons: An Introduction to Computational Geometry](https://mitpress.mit.edu/books/perceptrons) (Minsky & Papert) | MIT Press | 1969 |
| [The Perceptron: A Probabilistic Model for Information Storage and Organization in the Brain](https://doi.org/10.1037/h0042519) (Rosenblatt) | Psychological Review | 1958 |
| [Learning Representations by Back-propagating Errors](https://doi.org/10.1038/323533a0) (Rumelhart, Hinton, Williams) | Nature | 1986 |
| [Multilayer Feedforward Networks Are Universal Approximators](https://doi.org/10.1016/0893-6080(89)90020-8) (Hornik, Stinchcombe, White) | Neural Networks | 1989 |
| [Steps Toward Artificial Intelligence](https://doi.org/10.1109/JRPROC.1961.287575) (Minsky) | Proceedings of the IRE | 1961 |

---

*Previous: [Week 03 — Richard Hamming (1968)](../03-richard-hamming-1968/)*

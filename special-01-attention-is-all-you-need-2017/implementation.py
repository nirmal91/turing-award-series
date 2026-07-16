"""Attention Is All You Need (Vaswani et al., 2017) — a working Transformer
encoder in pure Python, no dependencies.

Before this paper, translation models were recurrent: they read a sentence
one word at a time, left to right, each step waiting for the one before it.
    BEFORE:  h1 -> h2 -> h3 -> h4 -> h5     (sequential, word 5 sees word 1
                                             only through 4 hops of memory)
The Transformer deleted the recurrence. Every word looks at every other
word directly, in one step, all in parallel:
    AFTER:   every word <-> every word      (one hop, fully parallel)

This file implements the real machinery from the paper:
  - scaled dot-product attention  (Section 3.2.1, Equation 1)
  - multi-head attention          (Section 3.2.2)
  - residual connections + layer norm + feed-forward (Sections 3.1, 3.3)
  - sinusoidal positional encoding (Section 3.5)

The weights are hand-built instead of trained, so you can see exactly WHY
attention does what it does. The demo mirrors the paper's famous example:

    "the animal didn't cross the street because it was too tired"  -> it = animal
    "the animal didn't cross the street because it was too wide"   -> it = street

Layer 1: "it" attends to the property word (tired / wide) and absorbs it.
Layer 2: "it" uses that property to find the noun it belongs to.
Two layers of dot products resolve a pronoun. No grammar rules anywhere.

Run:
    python3 implementation.py                 # demo, then interactive REPL
    python3 implementation.py practice.txt    # run sentences from a file
    python3 implementation.py --test          # test suite
    python3 implementation.py --verbose       # demo + REPL showing Q, K, V,
                                              # raw scores, softmax internals
"""

import math
import sys

# ---------------------------------------------------------------------------
# Matrix helpers. A matrix is a list of rows; a row is a list of floats.
# Written as explicit loops on purpose: you can trace every number.
# ---------------------------------------------------------------------------

def matmul(a, b):
    """Multiply matrix a (n x m) by matrix b (m x p)."""
    n = len(a)
    m = len(b)
    p = len(b[0])
    result = []
    for i in range(n):
        row = []
        for j in range(p):
            total = 0.0
            for k in range(m):
                total = total + a[i][k] * b[k][j]
            row.append(total)
        result.append(row)
    return result


def transpose(a):
    rows = len(a)
    cols = len(a[0])
    result = []
    for j in range(cols):
        new_row = []
        for i in range(rows):
            new_row.append(a[i][j])
        result.append(new_row)
    return result


def add_matrices(a, b):
    result = []
    for row_a, row_b in zip(a, b):
        new_row = []
        for x, y in zip(row_a, row_b):
            new_row.append(x + y)
        result.append(new_row)
    return result


def zeros(rows, cols):
    result = []
    for _ in range(rows):
        result.append([0.0] * cols)
    return result


def softmax(row):
    """Turn scores into weights that are positive and sum to 1.
    Subtracting the max first is the standard trick to avoid overflow;
    it does not change the result."""
    biggest = max(row)
    exps = []
    for x in row:
        exps.append(math.exp(x - biggest))
    total = sum(exps)
    weights = []
    for e in exps:
        weights.append(e / total)
    return weights


# ---------------------------------------------------------------------------
# Scaled dot-product attention — Equation 1 of the paper:
#     Attention(Q, K, V) = softmax(Q K^T / sqrt(d_k)) V
# ---------------------------------------------------------------------------

def scaled_dot_product_attention(Q, K, V, mask=None, scale=True):
    """Returns (output, attention_weights).

    Q: one query per row (what each word is looking for)
    K: one key per row   (what each word advertises)
    V: one value per row (what each word hands over if attended to)
    mask: optional list of rows; mask[i][j] = False forbids i attending to j.
          The decoder uses this so a word cannot look at the future.
    """
    d_k = len(K[0])
    scores = matmul(Q, transpose(K))

    if scale:
        # Why sqrt(d_k)? With big vectors, dot products grow with dimension,
        # softmax saturates to one-hot, and gradients die. Scaling keeps the
        # scores in a range where softmax stays soft. (Section 3.2.1)
        for i in range(len(scores)):
            for j in range(len(scores[i])):
                scores[i][j] = scores[i][j] / math.sqrt(d_k)

    if mask is not None:
        for i in range(len(scores)):
            for j in range(len(scores[i])):
                if not mask[i][j]:
                    scores[i][j] = -1e9   # exp(-1e9) = 0: weight becomes 0

    weights = []
    for row in scores:
        weights.append(softmax(row))

    output = matmul(weights, V)
    return output, weights


def causal_mask(n):
    """Lower-triangular mask: position i may only attend to positions <= i.
    This is what makes the decoder autoregressive — and what GPT still uses."""
    mask = []
    for i in range(n):
        row = []
        for j in range(n):
            row.append(j <= i)
        mask.append(row)
    return mask


# ---------------------------------------------------------------------------
# Multi-head attention — Section 3.2.2.
# Instead of one attention with big vectors, run several small attentions
# ("heads") side by side, each with its own Q/K/V projections, and
# concatenate the results. Each head can learn a different relationship
# (one tracks syntax, another tracks reference, ...).
# ---------------------------------------------------------------------------

def multi_head_attention(x, heads, mask=None):
    """heads: list of (Wq, Wk, Wv) triples. Returns (output, weights_per_head).
    Head outputs are concatenated, as in the paper (we skip the final W^O
    projection; with hand-built weights it would just be identity)."""
    head_outputs = []
    weights_per_head = []
    for (Wq, Wk, Wv) in heads:
        Q = matmul(x, Wq)
        K = matmul(x, Wk)
        V = matmul(x, Wv)
        out, weights = scaled_dot_product_attention(Q, K, V, mask=mask)
        head_outputs.append(out)
        weights_per_head.append(weights)

    combined = []
    for i in range(len(x)):
        row = []
        for out in head_outputs:
            row.extend(out[i])
        combined.append(row)
    return combined, weights_per_head


# ---------------------------------------------------------------------------
# The other blocks of an encoder layer — Sections 3.1 and 3.3.
# ---------------------------------------------------------------------------

def layer_norm(x, eps=1e-6):
    """Normalize each row to mean 0, variance 1. Keeps activations in a
    stable range so deep stacks of layers still train."""
    result = []
    for row in x:
        mean = sum(row) / len(row)
        var = 0.0
        for v in row:
            var = var + (v - mean) ** 2
        var = var / len(row)
        new_row = []
        for v in row:
            new_row.append((v - mean) / math.sqrt(var + eps))
        result.append(new_row)
    return result


def feed_forward(x, W1, b1, W2, b2):
    """Position-wise feed-forward: two linear layers with ReLU between,
    applied to every position independently (Equation 2)."""
    hidden = matmul(x, W1)
    for i in range(len(hidden)):
        for j in range(len(hidden[i])):
            hidden[i][j] = max(0.0, hidden[i][j] + b1[j])   # ReLU
    out = matmul(hidden, W2)
    for i in range(len(out)):
        for j in range(len(out[i])):
            out[i][j] = out[i][j] + b2[j]
    return out


def positional_encoding(n_positions, d_model):
    """Sinusoidal position vectors — Section 3.5.
    Attention is order-blind: shuffle the words and the outputs shuffle with
    them, nothing else changes. So the paper ADDS a position signature to
    each word's vector. Each position gets a unique pattern of sines and
    cosines at different frequencies (think: binary counting, but smooth)."""
    pe = zeros(n_positions, d_model)
    for pos in range(n_positions):
        for i in range(0, d_model, 2):
            angle = pos / (10000 ** (i / d_model))
            pe[pos][i] = math.sin(angle)
            if i + 1 < d_model:
                pe[pos][i + 1] = math.cos(angle)
    return pe


# ---------------------------------------------------------------------------
# The demo model: a 2-layer, hand-built Transformer encoder that resolves
# pronouns. Vector dimensions (d_model = 6):
#     0: animal-ness   1: street-ness   2: pronoun-ness
#     3: tiredness     4: wideness      5: other/filler
# ---------------------------------------------------------------------------

D = 6
ANIMAL, STREET, PRONOUN, TIRED, WIDE, OTHER = range(D)

ANIMAL_WORDS = ["animal", "dog", "cat", "horse", "fox"]
STREET_WORDS = ["street", "road", "bridge", "river"]
PRONOUN_WORDS = ["it"]
TIRED_WORDS = ["tired", "hungry", "scared", "slow"]     # animate properties
WIDE_WORDS = ["wide", "narrow", "busy", "long"]         # inanimate properties


def embed(word):
    """One vector per word. Real transformers learn these; we assign them
    so the mechanics are visible."""
    vector = [0.0] * D
    if word in ANIMAL_WORDS:
        vector[ANIMAL] = 1.0
    elif word in STREET_WORDS:
        vector[STREET] = 1.0
    elif word in PRONOUN_WORDS:
        vector[PRONOUN] = 1.0
    elif word in TIRED_WORDS:
        vector[TIRED] = 1.0
    elif word in WIDE_WORDS:
        vector[WIDE] = 1.0
    else:
        vector[OTHER] = 1.0
    return vector


def single_entry(row, col, value):
    W = zeros(D, D)
    W[row][col] = value
    return W


GAIN = 12.0   # how sharply a matching query locks onto its key

# Layer 1 — "the pronoun absorbs the property".
# Query: a pronoun asks "where is the property word?" (asks in channel OTHER+1
# reused as a scratch direction — we use column PRONOUN as the match channel).
W_Q1 = single_entry(PRONOUN, PRONOUN, GAIN)      # pronoun emits a query
W_K1 = zeros(D, D)
W_K1[TIRED][PRONOUN] = 1.0                       # property words answer it
W_K1[WIDE][PRONOUN] = 1.0
W_V1 = zeros(D, D)
W_V1[TIRED][TIRED] = 1.0                         # and hand over ONLY their
W_V1[WIDE][WIDE] = 1.0                           # property feature

# Layer 2 — "the property finds its noun".
# A word that now carries tiredness asks "who gets tired?" -> animal keys.
# A word that carries wideness asks "what is wide?" -> street keys.
W_Q2 = zeros(D, D)
W_Q2[TIRED][ANIMAL] = GAIN
W_Q2[WIDE][STREET] = GAIN
W_K2 = zeros(D, D)
W_K2[ANIMAL][ANIMAL] = 1.0
W_K2[STREET][STREET] = 1.0
W_V2 = zeros(D, D)
W_V2[ANIMAL][ANIMAL] = 1.0                       # nouns hand over their identity
W_V2[STREET][STREET] = 1.0

LAYERS = [(W_Q1, W_K1, W_V1), (W_Q2, W_K2, W_V2)]


def tokenize(sentence):
    tokens = []
    for raw in sentence.lower().split():
        word = raw.strip(".,!?;:\"'")
        if word:
            tokens.append(word)
    return tokens


def encode(tokens, use_positions=False, verbose=False):
    """Run tokens through the 2-layer encoder.
    Returns (final_vectors, [layer1_weights, layer2_weights])."""
    x = []
    for t in tokens:
        x.append(embed(t))

    if use_positions:
        pe = positional_encoding(len(tokens), D)
        x = add_matrices(x, pe)

    all_weights = []
    for layer_number, (Wq, Wk, Wv) in enumerate(LAYERS, start=1):
        Q = matmul(x, Wq)
        K = matmul(x, Wk)
        V = matmul(x, Wv)
        attended, weights = scaled_dot_product_attention(Q, K, V)
        if verbose:
            print(f"\n--- layer {layer_number} internals ---")
            print_matrix("Q (queries)", tokens, Q)
            print_matrix("K (keys)", tokens, K)
            print_matrix("V (values)", tokens, V)
            print_matrix("attention weights (rows sum to 1)", tokens, weights)
        x = add_matrices(x, attended)   # residual connection (Section 3.1)
        all_weights.append(weights)
    return x, all_weights


def print_matrix(title, tokens, m):
    print(f"{title}:")
    for token, row in zip(tokens, m):
        cells = " ".join(f"{v:6.2f}" for v in row)
        print(f"  {token:>8s} [{cells}]")


def resolve_pronoun(sentence, verbose=False):
    """Run a sentence, then read layer 2's attention row for 'it'."""
    tokens = tokenize(sentence)
    if "it" not in tokens:
        return None, tokens, None
    final, weights = encode(tokens, verbose=verbose)
    it_index = tokens.index("it")
    row = weights[1][it_index]

    best_index = 0
    for j in range(len(row)):
        if row[j] > row[best_index]:
            best_index = j
    return tokens[best_index], tokens, row


def show_attention_row(tokens, row):
    """Text heatmap of one attention row."""
    for token, weight in zip(tokens, row):
        bar = "#" * int(round(weight * 40))
        print(f"    {token:>8s} {weight:.3f} {bar}")


# ---------------------------------------------------------------------------
# Demo and REPL
# ---------------------------------------------------------------------------

DEMO_SENTENCES = [
    "the animal didn't cross the street because it was too tired",
    "the animal didn't cross the street because it was too wide",
]


def run_demo(verbose=False):
    print("=" * 68)
    print("The paper's own example. Same sentence, one word changed.")
    print("Where does 'it' look?  (layer 2 attention row for 'it')")
    print("=" * 68)
    for sentence in DEMO_SENTENCES:
        print(f'\n"{sentence}"')
        referent, tokens, row = resolve_pronoun(sentence, verbose=verbose)
        show_attention_row(tokens, row)
        print(f'  -> "it" means: {referent.upper()}')

    print()
    print("=" * 68)
    print("Order-blindness: why the paper needs positional encoding")
    print("=" * 68)
    def outputs_match(a, b, n):
        """Does word i in a get the same vector as word n-1-i in b?"""
        for i in range(n):
            for x, y in zip(a[i], b[n - 1 - i]):
                if abs(x - y) > 1e-6:
                    return False
        return True

    tokens = tokenize(DEMO_SENTENCES[0])
    reversed_tokens = list(reversed(tokens))
    plain, _ = encode(tokens)
    plain_reversed, _ = encode(reversed_tokens)
    same = outputs_match(plain, plain_reversed, len(tokens))
    print(f"\n  sentence reversed, no positions: every word's output identical? {same}")
    with_pe, _ = encode(tokens, use_positions=True)
    with_pe_reversed, _ = encode(reversed_tokens, use_positions=True)
    same_pe = outputs_match(with_pe, with_pe_reversed, len(tokens))
    print(f"  sentence reversed, with positions: still identical? {same_pe}")
    print("\n  Attention alone cannot see word order. Adding a sine/cosine")
    print("  position signature to each word (Section 3.5) fixes that.")


def run_repl(verbose=False):
    print()
    print("Type a sentence with 'it' in it. Known words:")
    print(f"  animals:    {', '.join(ANIMAL_WORDS)}")
    print(f"  crossables: {', '.join(STREET_WORDS)}")
    print(f"  animate properties:   {', '.join(TIRED_WORDS)}")
    print(f"  inanimate properties: {', '.join(WIDE_WORDS)}")
    print("Anything else becomes a filler word. Ctrl-D or 'quit' to exit.\n")
    while True:
        try:
            line = input("sentence> ").strip()
        except EOFError:
            print()
            break
        if line in ("quit", "exit"):
            break
        if not line:
            continue
        referent, tokens, row = resolve_pronoun(line, verbose=verbose)
        if referent is None:
            print("  no 'it' found — add the word 'it' so there is")
            print("  something to resolve, e.g.: the dog stopped because it was scared")
            continue
        show_attention_row(tokens, row)
        print(f'  -> "it" means: {referent.upper()}\n')


def run_file(path, verbose=False):
    with open(path) as f:
        for line in f:
            sentence = line.strip()
            if not sentence or sentence.startswith("#"):
                continue
            print(f'\n"{sentence}"')
            referent, tokens, row = resolve_pronoun(sentence, verbose=verbose)
            if referent is None:
                continue
            show_attention_row(tokens, row)
            print(f'  -> "it" means: {referent.upper()}')


# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------

def run_tests():
    passed = 0
    failed = 0

    def check(name, condition):
        nonlocal passed, failed
        if condition:
            passed = passed + 1
            print(f"  PASS  {name}")
        else:
            failed = failed + 1
            print(f"  FAIL  {name}")

    # 1. softmax rows are a probability distribution
    w = softmax([1.0, 2.0, 3.0])
    check("softmax sums to 1", abs(sum(w) - 1.0) < 1e-9)

    # 2. softmax is shift-invariant (the overflow trick changes nothing)
    a = softmax([1.0, 2.0, 3.0])
    b = softmax([101.0, 102.0, 103.0])
    check("softmax shift-invariant",
          all(abs(x - y) < 1e-9 for x, y in zip(a, b)))

    # 3. attention with a perfectly matching key retrieves that value
    Q = [[0.0, 10.0]]
    K = [[10.0, 0.0], [0.0, 10.0]]
    V = [[1.0, 0.0], [0.0, 1.0]]
    out, weights = scaled_dot_product_attention(Q, K, V)
    check("matching key wins the lookup", weights[0][1] > 0.99)

    # 4. attention output rows are blends: each weight row sums to 1
    Q = [[1.0, 2.0], [3.0, 1.0]]
    out, weights = scaled_dot_product_attention(Q, K, V)
    ok = True
    for row in weights:
        if abs(sum(row) - 1.0) > 1e-9:
            ok = False
    check("every attention row sums to 1", ok)

    # 5. scaling keeps softmax softer than the unscaled version.
    # With 16-dim vectors the raw dot product is 16 and softmax saturates;
    # divided by sqrt(16) it is 4 and the weights stay usable.
    Q = [[1.0] * 16]
    K = [[1.0] * 16, [0.0] * 16]
    V = [[1.0], [0.0]]
    _, scaled = scaled_dot_product_attention(Q, K, V, scale=True)
    _, unscaled = scaled_dot_product_attention(Q, K, V, scale=False)
    check("sqrt(d_k) scaling softens the weights",
          scaled[0][0] < unscaled[0][0])

    # 6. causal mask: position 0 cannot see position 1
    Q = [[1.0, 0.0], [1.0, 0.0]]
    K = [[1.0, 0.0], [5.0, 0.0]]
    V = [[1.0, 0.0], [0.0, 1.0]]
    _, weights = scaled_dot_product_attention(Q, K, V, mask=causal_mask(2))
    check("causal mask blocks the future", weights[0][1] < 1e-6)

    # 7. causal mask: the last position can still see everything
    check("causal mask keeps the past open", weights[1][0] > 1e-6)

    # 8. layer norm output has mean ~0 and variance ~1
    normed = layer_norm([[1.0, 2.0, 3.0, 4.0]])
    mean = sum(normed[0]) / 4
    var = sum((v - mean) ** 2 for v in normed[0]) / 4
    check("layer norm gives mean 0, var 1",
          abs(mean) < 1e-6 and abs(var - 1.0) < 1e-3)

    # 9. feed-forward ReLU kills negatives
    out = feed_forward([[1.0]], [[-1.0]], [0.0], [[1.0]], [0.0])
    check("ReLU zeroes negative activations", out[0][0] == 0.0)

    # 10. positional encodings are unique per position
    pe = positional_encoding(50, 8)
    unique = True
    for i in range(50):
        for j in range(i + 1, 50):
            if pe[i] == pe[j]:
                unique = False
    check("positional encodings unique per position", unique)

    # 11. multi-head: two heads concatenate to double width
    x = [[1.0, 0.0], [0.0, 1.0]]
    identity = [[1.0, 0.0], [0.0, 1.0]]
    head = (identity, identity, identity)
    out, per_head = multi_head_attention(x, [head, head])
    check("two heads concatenate to double width",
          len(out[0]) == 4 and len(per_head) == 2)

    # 12. without positions, attention is order-blind (permutation-equivariant)
    tokens = tokenize(DEMO_SENTENCES[0])
    fwd, _ = encode(tokens)
    rev, _ = encode(list(reversed(tokens)))
    blind = True
    for i in range(len(tokens)):
        for a_val, b_val in zip(fwd[i], rev[len(tokens) - 1 - i]):
            if abs(a_val - b_val) > 1e-9:
                blind = False
    check("no positions -> order-blind", blind)

    # 13. with positional encoding, order matters
    fwd_pe, _ = encode(tokens, use_positions=True)
    rev_pe, _ = encode(list(reversed(tokens)), use_positions=True)
    differs = False
    for i in range(len(tokens)):
        for a_val, b_val in zip(fwd_pe[i], rev_pe[len(tokens) - 1 - i]):
            if abs(a_val - b_val) > 1e-6:
                differs = True
    check("positional encoding makes order matter", differs)

    # 14. the paper's example: 'tired' -> it = animal
    referent, _, row = resolve_pronoun(DEMO_SENTENCES[0])
    check("'...it was too tired' -> animal",
          referent == "animal" and max(row) > 0.7)

    # 15. the flipped example: 'wide' -> it = street
    referent, _, row = resolve_pronoun(DEMO_SENTENCES[1])
    check("'...it was too wide' -> street",
          referent == "street" and max(row) > 0.7)

    # 16. generalizes to unseen combinations of known words
    referent, _, _ = resolve_pronoun("the fox stopped at the river because it was hungry")
    check("'fox...river...hungry' -> fox", referent == "fox")

    referent, _, _ = resolve_pronoun("the fox stopped at the river because it was long")
    check("'fox...river...long' -> river", referent == "river")

    print(f"\n{passed} passed, {failed} failed")
    return failed == 0


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--test" in args:
        ok = run_tests()
        sys.exit(0 if ok else 1)
    verbose = "--verbose" in args
    if verbose:
        args.remove("--verbose")
    if args:
        run_file(args[0], verbose=verbose)
    else:
        run_demo(verbose=verbose)
        run_repl(verbose=verbose)

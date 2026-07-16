"""The core idea of the Transformer (Vaswani et al., 2017) in one function.

Before 2017, language models read a sentence one word at a time through a
recurrent network. Information about the first word had to survive a long
chain of steps to influence the last word.

The Transformer's move: let every word look at every other word directly,
in one step. That lookup is attention, and it is just a soft dictionary:

    each word asks a question        (its query  vector q)
    each word advertises a label     (its key    vector k)
    each word carries some content   (its value  vector v)

A word compares its query against every key (dot product), turns the
scores into weights that sum to 1 (softmax), and takes that weighted
blend of the values. High score = "you're relevant to me, I'll take
more of your content."

Run: python3 concept.py
"""

import math

# The sentence: "the animal didn't cross the street because it was tired"
# We only model the interesting words. Each has a tiny 4-dim vector:
#     [ animal-ness, street-ness, gets-tired, is-wide ]
words = ["animal", "street", "it"]

keys = {
    "animal": [1.0, 0.0, 1.0, 0.0],   # an animal, and animals get tired
    "street": [0.0, 1.0, 0.0, 1.0],   # a street, and streets are wide
    "it":     [0.0, 0.0, 0.0, 0.0],   # a pronoun advertises nothing
}
values = dict(keys)  # here each word's content is just its own vector

# "it" needs a referent. The sentence says "...because it was TIRED",
# so the question "it" asks is: who around here gets tired?
query_it = [0.0, 0.0, 4.0, 0.0]       # strongly seeking the gets-tired feature


def attention(query, words, keys, values):
    """Scaled dot-product attention for one query. Equation 1 of the paper:
    Attention(q, K, V) = softmax(q . K / sqrt(d_k)) V
    """
    d_k = len(query)

    # 1. score every word: how well does its key answer my question?
    scores = []
    for w in words:
        dot = 0.0
        for i in range(d_k):
            dot = dot + query[i] * keys[w][i]
        scores.append(dot / math.sqrt(d_k))   # scale so softmax stays soft

    # 2. softmax: exponentiate and normalize so the weights sum to 1
    exps = [math.exp(s) for s in scores]
    total = sum(exps)
    weights = [e / total for e in exps]

    # 3. blend the values by those weights
    d_v = len(query)
    blended = [0.0] * d_v
    for w, weight in zip(words, weights):
        for i in range(d_v):
            blended[i] = blended[i] + weight * values[w][i]

    return scores, weights, blended


scores, weights, blended = attention(query_it, words, keys, values)

print('"the animal didn\'t cross the street because it was tired"')
print()
print('the word "it" asks: who around here gets tired?')
print()
for w, s, wt in zip(words, scores, weights):
    print(f"  {w:7s}  score {s:5.2f}  ->  attention weight {wt:.3f}")
print()
print(f"blended vector for 'it': {[round(x, 2) for x in blended]}")
print("mostly animal-ness. 'it' now means the animal. no grammar rules,")
print("no parse tree. just three vectors and a dot product.")

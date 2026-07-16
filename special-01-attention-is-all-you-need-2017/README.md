# Special 01 — Attention Is All You Need (2017)

**The paper:** *Vaswani, Shazeer, Parmar, Uszkoreit, Jones, Gomez, Kaiser, Polosukhin. "Attention Is All You Need." NeurIPS 2017.*

Not a Turing Award chapter. This is the first special edition of the series: papers that changed the field but haven't (yet) collected the award. This one is the architecture behind every modern LLM. The T in GPT stands for Transformer, and this is the paper that introduced it.

---

## My Take

*[Placeholder — written by Nirmal, not AI]*

---

## The Code

[`concept.py`](./concept.py) — attention as a soft dictionary lookup in one function: a query vector, key vectors, a dot product, a softmax, a blend. That is Equation 1 of the paper and the whole core idea.

[`implementation.py`](./implementation.py) — a working Transformer encoder in pure Python: scaled dot-product attention, multi-head attention, residual connections, layer norm, the position-wise feed-forward block, causal masking, and sinusoidal positional encodings. The weights are hand-built instead of trained, so you can see exactly why attention does what it does.

```
sentence
    ↓ tokenize            split into words
    ↓ embed               each word becomes a 6-dim feature vector
    ↓ layer 1 attention   "it" finds the property word (tired / wide) and absorbs it
    ↓ layer 2 attention   the absorbed property finds its noun (animal / street)
    ↓
  "it" now points at its referent
```

The demo mirrors the example Google used to introduce the paper:

- "the animal didn't cross the street because it was too **tired**" → it = the animal
- "the animal didn't cross the street because it was too **wide**" → it = the street

One word changes, and the attention pattern for "it" flips from the animal to the street. No grammar rules anywhere. Two rounds of dot products.

What it supports:
- Scaled dot-product attention with the paper's `1/sqrt(d_k)` scaling (Section 3.2.1)
- Multi-head attention with concatenated heads (Section 3.2.2)
- Causal masking, the thing that makes GPT autoregressive
- Sinusoidal positional encodings, plus a demo of why attention needs them (Section 3.5)
- Residual connections, layer norm, and the feed-forward block (Sections 3.1, 3.3)
- A REPL where you type your own sentences, a 17-case test suite, and a verbose mode that prints Q, K, V, and every attention matrix

```bash
python3 concept.py                    # the core idea, plain
python3 implementation.py             # demo, then interactive REPL
python3 implementation.py practice.txt # run sentences from a file
python3 implementation.py --test      # test suite (17 cases)
python3 implementation.py --verbose   # show Q, K, V, scores, weights
```

Example session:

```
sentence> the dog would not use the bridge because it was scared
         the 0.010
         dog 0.899 ####################################
       would 0.010
         not 0.010
         use 0.010
         the 0.010
      bridge 0.010
     because 0.010
          it 0.010
         was 0.010
      scared 0.010
  -> "it" means: DOG

sentence> the dog would not use the bridge because it was narrow
  -> "it" means: BRIDGE
```

---

## Full Worked Example

Two walkthroughs. First a single attention lookup with every number shown, then the full two-layer pronoun resolution the demo runs.

### Part A — one attention lookup by hand

Attention is Equation 1 of the paper:

```
Attention(Q, K, V) = softmax(Q·Kᵀ / sqrt(d_k)) · V
```

Three words, each with a 4-dim vector. The dimensions mean `[animal-ness, street-ness, gets-tired, is-wide]`:

```
key(animal) = [1, 0, 1, 0]      an animal, and animals get tired
key(street) = [0, 1, 0, 1]      a street, and streets are wide
key(it)     = [0, 0, 0, 0]      a pronoun advertises nothing
```

The sentence ends "...because it was tired", so the query for "it" is: who around here gets tired?

```
query(it) = [0, 0, 4, 0]
```

**Step 1 — score every word.** Dot product of the query with each key:

```
q · key(animal) = 0·1 + 0·0 + 4·1 + 0·0 = 4
q · key(street) = 0·0 + 0·1 + 4·0 + 0·1 = 0
q · key(it)     = 0
```

**Step 2 — scale.** Divide by sqrt(d_k) = sqrt(4) = 2. This is the "scaled" in scaled dot-product attention. Scores: `2, 0, 0`.

**Step 3 — softmax.** Exponentiate, then divide by the total so the weights sum to 1:

```
e² = 7.389    e⁰ = 1    e⁰ = 1        total = 9.389

weight(animal) = 7.389 / 9.389 = 0.787
weight(street) = 1 / 9.389     = 0.107
weight(it)     = 1 / 9.389     = 0.107
```

**Step 4 — blend the values.** Here each word's value is its own vector:

```
0.787·[1,0,1,0] + 0.107·[0,1,0,1] + 0.107·[0,0,0,0] = [0.787, 0.107, 0.787, 0.107]
```

The new vector for "it" is 79% animal. That is the whole mechanism. `concept.py` prints exactly this.

### Part B — the two-layer resolution, real numbers

The catch in Part A: I hand-wrote the query "who gets tired?" for "it". But at the start of a real sentence, "it" doesn't know tiredness is relevant. It has to discover that from the sentence. That takes two layers.

Sentence: `the animal didn't cross the street because it was too tired` (11 tokens, d_model = 6, dims = `[animal, street, pronoun, tired, wide, other]`).

**Layer 1 — the pronoun absorbs the property.**

The query weights make pronouns ask "where is a property word?", and the key weights make property words (tired, wide, hungry, narrow...) answer. The gain is 12, so:

```
score(it → tired) = 12          every other score = 0
scaled: 12 / sqrt(6) = 4.899

softmax over 11 tokens:  e^4.899 = 134.1  vs  ten e⁰ = 1 each
weight(it → tired) = 134.1 / 144.1 = 0.931
```

The value weights hand over only the property feature, and the residual connection adds it to what "it" already was:

```
it = [0, 0, 1, 0, 0, 0]  +  0.931·[0, 0, 0, 1, 0, 0]  =  [0, 0, 1, 0.931, 0, 0]
```

"it" is still a pronoun, but now it carries tiredness. Every other word ran the same computation at the same time; their queries were zero so they got (nearly) nothing.

**Layer 2 — the property finds its noun.**

The layer-2 query weights map tiredness to "who gets tired?" (an animal-channel query) and wideness to "what is wide?" (a street-channel query). Nouns advertise themselves in the key weights.

```
query(it) = 0.931 · 12 = 11.17 in the animal channel

score(it → animal) = 11.17        scaled: 11.17 / sqrt(6) = 4.559
softmax:  e^4.559 = 95.5  vs  ten e⁰ = 1 each
weight(it → animal) = 95.5 / 105.5 = 0.905
```

That 0.905 is exactly what the demo prints. Change "tired" to "wide" and layer 1 hands "it" wideness instead, so layer 2's query fires in the street channel and the 0.905 lands on "street". The flip is the paper's famous figure, reproduced with arithmetic you can check by hand.

**The failure case.** Run `the animal crossed the street and it was there`. There is no property word, so layer 1 hands "it" nothing, layer 2's query is zero, every score is zero, and softmax gives a uniform 1/9 = 0.111 to every word. The model genuinely doesn't know, and you can see it not knowing. Real transformers show the same behavior as spread-out attention on ambiguous sentences.

---

## ELI5

Before, a computer read a sentence like a whisper game: one person hears a word, passes it to the next, and so on down the line. By the end of a long sentence, the beginning was mostly forgotten.

The Transformer sits all the words around one table so every word can just look at every other word, all at once.

Read "the animal didn't cross the street because it was too tired." What does "it" mean? The word "it" looks around the table, sees "tired", and tired things are animals, not streets. So "it" means the animal. If the sentence said "too wide" instead, "it" would look at the street.

And because nobody waits in line anymore, the computer reads the whole sentence at the same time, which is much, much faster.

---

## ELI10

In 2016, Google Translate got a big upgrade. Under the hood it used networks called LSTMs that read a sentence the only way anyone knew how: one word at a time, left to right, keeping a running memory of what they'd seen. That had two problems. Long sentences faded, because word 40 only knew about word 1 through 39 steps of increasingly mushy memory. And it was slow to train, because step 40 could not start until step 39 finished, no matter how many computers you had.

There was already a patch called attention: while translating, the model could peek back at the original sentence and focus on the relevant word. It helped a lot. Then in 2017, eight researchers at Google asked a cheeky question: if the peeking is doing so much of the work, do we need the word-by-word reading at all? Their title was the answer. Attention is all you need.

In a Transformer, every word gets three small vectors: a query (what am I looking for?), a key (what am I?), and a value (what do I pass along if you look at me?). Every word compares its query against every other word's key and takes a weighted blend of their values. Distant words are now one step apart instead of 39, and since no word waits for another, the whole sentence is processed in parallel. Their base model trained in about 12 hours on 8 GPUs and beat translation systems that took far longer, using less compute.

The follow-up is the part you already know. This same architecture turned out to work for almost everything: text, images, protein folding, code. BERT, then GPT, then every chatbot you've used. The T in GPT stands for Transformer. This paper is the reason.

---

## CS Graduate Level

### The state of the art before

Neural machine translation circa 2016 was sequence-to-sequence with recurrence. Sutskever et al. (2014) established the encoder-decoder pattern: an LSTM encoder compresses the source sentence into a fixed vector, an LSTM decoder unrolls the translation from it. The fixed vector was an obvious bottleneck, and Bahdanau et al. (2015) fixed it with attention: at each decoding step, compute a relevance score between the decoder state and every encoder state, and use the resulting weighted average instead of the single squashed vector. Google's production GNMT system (2016) was this design, scaled: 8 encoder layers, 8 decoder layers, all recurrent.

Attention was already there. But it was a decoder-side accessory bolted onto a recurrent backbone, and the backbone had two structural costs:

1. **No parallelism within a sequence.** Computing hidden state h_t requires h_{t-1}. Training time grows with sequence length regardless of hardware. GPUs, which want thousands of independent operations, sit underutilized.
2. **Long gradient paths.** A dependency between tokens i and j must survive |i − j| sequential transformations. LSTMs' gating mitigates the vanishing-gradient problem; it does not eliminate the O(n) path length.

### What was technically new

The Transformer's claim was subtractive: keep attention, delete recurrence entirely. The specific contributions:

**Self-attention as the primary representation builder.** Prior work attended from decoder to encoder. Here each layer attends from the sequence to itself: every token computes query, key, and value projections (Q = XW^Q, K = XW^K, V = XW^V) and updates itself with

```
Attention(Q, K, V) = softmax(QKᵀ / √d_k) V
```

Every token pair interacts directly. Maximum dependency path length drops from O(n) to O(1), and the whole layer is three matrix multiplications plus a softmax, which is exactly what GPUs are good at. Per-layer cost is O(n²·d) versus O(n·d²) for recurrence: worse in sequence length, better in width, and with n < d for typical sentence lengths, cheaper in practice. That n² term is also the reason "context length" is the headline constraint on LLMs today.

**Scaled dot-product attention.** Dot products of d_k-dimensional random vectors have variance that grows with d_k, pushing softmax into saturation where gradients vanish. Dividing by √d_k keeps the score distribution stable. A one-line fix, load-bearing at scale.

**Multi-head attention.** One attention distribution per layer forces a single relational pattern. Instead, project into h = 8 subspaces of d_k = 64 each, attend independently, concatenate, and project back (total cost roughly equal to one full-width head). Different heads specialize: the paper's visualizations show heads tracking syntactic dependencies, coreference, and adjacency separately.

**Positional encoding.** Self-attention is permutation-equivariant: shuffle the tokens and the outputs shuffle identically, so word order is invisible. The fix is additive position signatures: PE(pos, 2i) = sin(pos/10000^(2i/d)) and the cosine counterpart. Frequencies vary geometrically across dimensions, giving each position a unique fingerprint, smooth like an odometer's dials. Sinusoids also make relative offsets linear functions of each other, and learned positional embeddings performed identically in their ablations.

**The full block.** An encoder layer is multi-head self-attention, then a position-wise feed-forward network (d_ff = 2048, two linear maps with ReLU), each wrapped in a residual connection and layer normalization. Six such layers form the encoder. The decoder adds causal masking (position i may attend only to positions ≤ i, implemented as −∞ scores before the softmax) plus cross-attention to the encoder output. Causal masking is what makes autoregressive generation trainable in parallel: all positions predict their next token simultaneously during training, and GPT is exactly this decoder stack.

### Results

On WMT 2014 English-to-German, the big Transformer hit 28.4 BLEU, more than 2 points over the previous best including ensembles. On English-to-French, 41.8 BLEU, at under a quarter of the previous state of the art's training cost. The base model trained in about 12 hours on 8 P100 GPUs. The bitter-lesson reading: the architecture won not by being smarter but by being more parallelizable, which let the same money buy more learning.

### What descended from it

Nearly everything. BERT (2019) is the encoder stack pretrained on masked language modeling. GPT (2018 onward) is the decoder stack pretrained autoregressively; GPT-3 (2020) showed the same architecture scales to 175B parameters with emergent few-shot behavior. Vision Transformers (2021) showed images work too: cut a picture into 16×16 patches and treat them as tokens. AlphaFold 2's Evoformer applies attention to protein residues. Whisper, Codex-style code models, and every production LLM today, including the one that wrote most of this repo, are this paper's architecture with better training recipes. The eight authors have all since left Google, most to found AI companies (Character.AI, Cohere, Essential AI, Sakana AI, NEAR, Inceptive, Adept among them).

The paper's deeper lesson matches this series' recurring theme: the winning move was a deletion. Not recurrence plus attention. Attention only, and make the hardware happy.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [Attention Is All You Need](https://arxiv.org/abs/1706.03762) | NeurIPS | 2017 |
| [Neural Machine Translation by Jointly Learning to Align and Translate](https://arxiv.org/abs/1409.0473) (attention, pre-Transformer) | ICLR | 2015 |
| [Sequence to Sequence Learning with Neural Networks](https://arxiv.org/abs/1409.3215) | NeurIPS | 2014 |
| [Long Short-Term Memory](https://doi.org/10.1162/neco.1997.9.8.1735) | Neural Computation | 1997 |
| [BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding](https://arxiv.org/abs/1810.04805) | NAACL | 2019 |
| [Language Models are Few-Shot Learners](https://arxiv.org/abs/2005.14165) (GPT-3) | NeurIPS | 2020 |
| [An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale](https://arxiv.org/abs/2010.11929) (ViT) | ICLR | 2021 |

The animal/street example is from Google's research blog post introducing the paper: [Transformer: A Novel Neural Network Architecture for Language Understanding](https://research.google/blog/transformer-a-novel-neural-network-architecture-for-language-understanding/) (2017).

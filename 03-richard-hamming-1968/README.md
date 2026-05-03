# Week 03 — Richard Hamming (1968)

**ACM Turing Award citation:** *"For his work on numerical methods, automatic coding systems, and error-detecting and error-correcting codes."*

---

## My Take

Richard Hamming, a mathematician, was trying to do what all of us do today. Submit a bunch of jobs Friday evening, expect the machine to keep running all weekend, and have stuff ready Monday morning. It wasn't as smooth for him and he'd come back with nothing done, because random bits were flipping mid-run, corrupting the computation and stopping it cold.

He decided the data could carry enough extra information to fix itself. A few extra bits added to whatever you're transmitting is all it takes, and if a bit flips in transit, those bits tell you exactly which one flipped so you can fix it without retransmitting or restarting. This is now the foundation of everything we do. Think about RAM, SSDs, hard disks, QR codes, even deep space telemetry. Most error-correcting codes today trace back to this one 1950 paper.

Bit flipping happens way more than you'd expect. RAM is the worst case. [Google published a study](https://dl.acm.org/doi/10.1145/1555349.1555372) showing a typical server sees one to two bit flips a day in memory, and a data center has hundreds of thousands of machines with bits flipping constantly. Without error correction, servers silently compute the wrong answers. It would feel like the servers are hallucinating and giving you wrong answers.

---

## The Code

[`concept.py`](./concept.py) — four data bits in, seven bits out, one flip corrected.

[`implementation.py`](./implementation.py) — full Hamming(7,4) codec with message encoding, error injection, and self-correction:

```
text input
    ↓
split each byte into two 4-bit nibbles
    ↓
encode each nibble → 7-bit codeword (adds 3 parity bits)
    ↓
transmit (errors may be injected here)
    ↓
decode: compute syndrome → locate error → flip bit back
    ↓
reassemble nibbles → recovered text
```

What it supports:
- Encode any ASCII string into Hamming(7,4) codewords
- Inject single-bit errors at random positions
- Auto-correct every injected error, no retransmit needed

```bash
python3 concept.py                      # the core idea, plain
python3 implementation.py               # interactive demo
python3 implementation.py --test        # test suite (20 cases)
python3 implementation.py --verbose     # show syndrome computation
```

Example session:

```
> Hello world
  encoded: 11 bytes → 154 transmitted bits
  injected error: char 2 (hi nibble) bit 3
  injected error: char 5 (lo nibble) bit 6
  injected error: char 9 (hi nibble) bit 1
  recovered: "Hello world"  (3 error(s) auto-corrected)
  result: perfect match
```

With `--verbose`, each decode step shows the syndrome:

```
  char 2:
    syndrome bits: s1=1 s2=1 s3=0  →  3 (0=clean)
    error at position 3 (0-indexed: 2), flipping
    decoded: hi=[1,1,0,0] lo=[0,0,0,0]  byte=0x6C
```

The syndrome is a binary number that names the bad position directly. That's the invention.

---

## Full Worked Example

Data to send: `[1, 0, 1, 1]` — 4 bits.

### Step 1 — Find r (trial and error)

You can't know how many parity bits you need upfront. You try values until the assumption is self-consistent — until the r you assumed equals the number of binary digits needed to address the total codeword length.

```
try r=1:  total = 4+1 = 5.  Largest position = 5 = 101 = 3 digits.  Need 3, have 1. ✗
try r=2:  total = 4+2 = 6.  Largest position = 6 = 110 = 3 digits.  Need 3, have 2. ✗
try r=3:  total = 4+3 = 7.  Largest position = 7 = 111 = 3 digits.  Need 3, have 3. ✓
```

3 parity bits. 7 total positions.

### Step 2 — Assign positions

Powers of 2 get parity bits. Everything else gets data. Each parity bit owns one binary column — the column where its bit is set — and checks every position where that column has a 1.

```
position:  1    2    3    4    5    6    7
binary:   001  010  011  100  101  110  111
type:     p1   p2   d1   p4   d2   d3   d4
```

Place the 4 data bits into the data slots:

```
position:  1    2    3    4    5    6    7
bit:       ?    ?    1    ?    0    1    1
```

### Step 3 — Compute each parity bit

Each parity bit is set so that XOR across everything it covers equals zero.

**p1** owns the rightmost column. Checks positions 1, 3, 5, 7.
Data already at 3, 5, 7: `1, 0, 1`
```
1 XOR 0 XOR 1 = 0  →  p1 = 0
```

**p2** owns the middle column. Checks positions 2, 3, 6, 7.
Data already at 3, 6, 7: `1, 1, 1`
```
1 XOR 1 XOR 1 = 1  →  p2 = 1
```

**p4** owns the leftmost column. Checks positions 4, 5, 6, 7.
Data already at 5, 6, 7: `0, 1, 1`
```
0 XOR 1 XOR 1 = 0  →  p4 = 0
```

Full codeword:

```
position:  1    2    3    4    5    6    7
bit:       0    1    1    0    0    1    1
type:     p1   p2   d1   p4   d2   d3   d4
```

### Step 4 — Send over the network

```
sent:  0  1  1  0  0  1  1
```

### Case A — A data bit flips (position 5)

Position 5 holds d2. It was `0`, arrives as `1`.

```
position:  1    2    3    4    5    6    7
sent:      0    1    1    0    0    1    1
received:  0    1    1    0    1    1    1
                               ↑
                           flipped
```

Receiver recomputes all three groups:

```
p1 checks 1,3,5,7:   0 XOR 1 XOR 1 XOR 1 = 1  ✗  broken
p2 checks 2,3,6,7:   1 XOR 1 XOR 1 XOR 1 = 0  ✓  fine
p4 checks 4,5,6,7:   0 XOR 1 XOR 1 XOR 1 = 1  ✗  broken
```

Stack the results: `p4=1, p2=0, p1=1` → binary `101` → **5**

Flip position 5 back. Extract data from positions 3, 5, 6, 7: `[1, 0, 1, 1]` ✓

### Case B — A parity bit flips (position 2)

Position 2 holds p2. It was `1`, arrives as `0`.

```
position:  1    2    3    4    5    6    7
sent:      0    1    1    0    0    1    1
received:  0    0    1    0    0    1    1
                ↑
            flipped
```

Receiver recomputes:

```
p1 checks 1,3,5,7:   0 XOR 1 XOR 0 XOR 1 = 0  ✓  fine
p2 checks 2,3,6,7:   0 XOR 1 XOR 1 XOR 1 = 1  ✗  broken
p4 checks 4,5,6,7:   0 XOR 0 XOR 1 XOR 1 = 0  ✓  fine
```

Stack: `p4=0, p2=1, p1=0` → binary `010` → **2**

Flip position 2 back. The algorithm doesn't know or care whether a parity bit or a data bit flipped. It just fixes whatever position the syndrome names. Extract data: `[1, 0, 1, 1]` ✓

### Case C — Nothing flips

```
position:  1    2    3    4    5    6    7
received:  0    1    1    0    0    1    1
```

Receiver recomputes:

```
p1 checks 1,3,5,7:   0 XOR 1 XOR 0 XOR 1 = 0  ✓
p2 checks 2,3,6,7:   1 XOR 1 XOR 1 XOR 1 = 0  ✓
p4 checks 4,5,6,7:   0 XOR 0 XOR 1 XOR 1 = 0  ✓
```

Syndrome: `0, 0, 0` → **0** → no error. Extract data: `[1, 0, 1, 1]` ✓

---

## ELI5

Imagine you write a note and send it through a tube. Somewhere in the tube, one letter smudges.

Before Hamming, the reader had no idea which letter smudged. They'd have to send the note back and ask you to write it again.

Hamming added a few extra marks to the note before sending it — computed from the letters themselves. If anything smudges, the marks point to exactly which letter changed. The reader fixes it on the spot. No round-trip.

Those extra marks are the parity bits. The pointing is the syndrome. That's it.

---

## ELI10

In the 1940s, computers at Bell Labs ran on punched cards and electromechanical relays. They were unreliable. Bits would flip. A calculation that ran overnight would finish with a wrong answer, and you'd have no idea where the error crept in. The machine would just halt and wait for an operator to restart the whole job.

Richard Hamming spent his weekends furious about this. He worked weekdays and the machine ran his jobs on nights and weekends — which meant every error cost him a full week of waiting. He decided to make the machine detect and fix its own errors.

His idea: before storing or transmitting data, add a few extra bits whose values are determined by the data bits. These "parity bits" are placed at specific positions so that any single flipped bit disturbs a unique combination of them. The receiver checks all the parity bits and computes a number called the syndrome. If the syndrome is zero, no error. If it's nonzero, the syndrome is literally the position of the bad bit. Flip it back. Done.

A Hamming(7,4) codeword carries 4 bits of data in 7 bits total. Three parity bits buy you full single-error correction. The extra cost is 3 bits per 4-bit message — about 75% overhead. Modern codes do far better, but every error-correcting code in use today traces its lineage to this insight.

---

## CS Graduate Level — Why Hamming Codes Mattered

### 1. The State of the Art Before (1940s)

Error detection existed before Hamming — a single parity bit appended to a byte can tell you that *some* bit flipped, but not which one. To correct an error you need to know its location, which a single parity bit cannot provide.

The only practical response to a detected error was retransmission. For telephone circuits, that meant an expensive round-trip. For batch-processing computers, it meant restarting a job. For magnetic storage, where bit-rot happens silently, you might not even detect the error at all.

The theoretical question — *can you design a code that corrects errors, not just detects them?* — had no worked answer in 1950.

### 2. Hamming's Insight

Hamming's key observation was geometric. Think of each possible n-bit string as a vertex of an n-dimensional hypercube. Two strings differ by one bit if and only if they are adjacent on the hypercube. The Hamming *distance* between two strings is the number of bit positions where they differ.

If you design a code where every valid codeword is at least distance 3 from every other valid codeword, then:
- Any single-bit flip moves you to an invalid codeword, and
- The nearest valid codeword to that invalid one is the original — so you know what it should have been.

The problem reduces to: how do you pack codewords into the hypercube such that the "spheres of radius 1" around each codeword don't overlap? Hamming solved this with a clean algebraic construction.

### 3. How Hamming(7,4) Works

A Hamming(7,4) code encodes 4 data bits as a 7-bit codeword. Bit positions are numbered 1–7. Positions that are powers of 2 (1, 2, 4) are parity bits. Positions 3, 5, 6, 7 carry data.

Each parity bit covers all positions where its bit is set in the binary representation of the position number:
- **p1 (pos 1):** covers positions 1, 3, 5, 7 (binary: `001`, `011`, `101`, `111`)
- **p2 (pos 2):** covers positions 2, 3, 6, 7 (binary: `010`, `011`, `110`, `111`)
- **p4 (pos 4):** covers positions 4, 5, 6, 7 (binary: `100`, `101`, `110`, `111`)

Each parity bit is set so its group has even parity (XOR of all covered bits = 0).

On receipt, recompute all three parity checks. The three results — each 0 or 1 — form a 3-bit binary number called the **syndrome**. If the syndrome is zero, no error. If the syndrome is nonzero, it is the exact position (1-indexed) of the flipped bit.

Example: data `1011`, encoded as `0110011`:

```
pos:  1   2   3   4   5   6   7
      p1  p2  d1  p3  d2  d3  d4
      0   1   1   0   0   1   1
```

Flip bit at position 5:

```
pos:  1   2   3   4   5   6   7
      0   1   1   0   1   1   1   ← bit 5 flipped
```

Syndrome computation:
```
s1 = p1 ⊕ pos3 ⊕ pos5 ⊕ pos7 = 0⊕1⊕1⊕1 = 1
s2 = p2 ⊕ pos3 ⊕ pos6 ⊕ pos7 = 1⊕1⊕1⊕1 = 0
s3 = p3 ⊕ pos5 ⊕ pos6 ⊕ pos7 = 0⊕1⊕1⊕1 = 1

syndrome = s3·4 + s2·2 + s1·1 = 4 + 0 + 1 = 5
```

Syndrome = 5 → flip bit at position 5 → recovered.

### 4. The Hamming Bound (Perfect Codes)

Hamming(7,4) is a *perfect code* — it achieves the theoretical maximum data rate for single-error correction. To see why: a 7-bit codeword has 7 possible single-bit errors plus the no-error state, giving 8 = 2³ syndromes. Three parity bits provide exactly 2³ = 8 distinct patterns. The spheres of radius 1 around each codeword partition the entire 7-dimensional space without gaps or overlaps.

The Hamming bound generalises: for a code with block length n, k data bits, and t-error correction, the minimum n satisfies:

```
2^(n-k) ≥ Σ C(n,i) for i=0..t
```

Hamming codes meet this bound with equality for t=1.

### 5. What Descended From It

**SECDED codes (1961):** IBM extended Hamming codes with a second overall parity bit, enabling *single-error correction, double-error detection* (SECDED). Every ECC RAM module in servers today uses a variant of this.

**Reed-Solomon codes (1960):** Solomon and Reed generalised from bits to symbols over larger finite fields, enabling multi-bit-error correction. Used in CDs, DVDs, QR codes, and deep-space telemetry (Voyager used a Reed-Solomon code over GF(2⁸)).

**LDPC codes (Gallager, 1962):** Low-density parity-check codes achieve capacity approaching the Shannon limit. Used in 5G, Wi-Fi 6, and 10GbE ethernet.

**Turbo codes (1993):** Used in 3G/4G cellular. Approach Shannon capacity for noisy channels.

All of them trace their mathematical lineage to Hamming's 1950 paper. The idea that you can *algebraically locate* a bit error — not just detect that one happened — was genuinely new.

### 6. Lasting Impact

Hamming codes are in ECC memory (every server rack), RAID 2 parity (now obsolete but historically important), barcode checksums, and every flash storage controller. The syndrome technique generalises to burst errors via interleaving. The geometric framing (Hamming distance, Hamming sphere) became the language of coding theory and, later, of nearest-neighbour search in machine learning.

Hamming himself stayed at Bell Labs for 30 years and gave a famous 1986 lecture, *"You and Your Research,"* on what separates important work from ordinary work. The error-correcting code was his answer in practice: he got mad at a machine that wasted his time and wrote the mathematics to make it stop.

---

## Papers and Citations

| Paper | Venue | Year |
|---|---|---|
| [Error Detecting and Error Correcting Codes](https://doi.org/10.1002/j.1538-7305.1950.tb00463.x) | Bell System Technical Journal | 1950 |
| [Error Correcting Codes](https://dl.acm.org/doi/10.5555/578869) *(book, with W. W. Peterson)* | MIT Press | 1961 |
| [Polynomial Codes Over Certain Finite Fields](https://doi.org/10.1137/0108018) *(Reed-Solomon)* | Journal of the Society for Industrial and Applied Mathematics | 1960 |
| [You and Your Research](https://www.cs.virginia.edu/~robins/YouAndYourResearch.html) | Bell Communications Research Colloquium | 1986 |

---

*Previous: [Week 02 — Maurice Wilkes (1967)](../02-maurice-wilkes-1967/)*

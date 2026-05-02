"""
Error-correcting codes — the core idea (Hamming, 1950)

A message can carry its own repair kit.
Add a few extra bits computed from the data, and the receiver
can find and fix any single-bit flip without asking for a retransmit.
That's it.
"""

# ── The insight ────────────────────────────────────────────────────────────────
#
# Before this: if a bit flipped in transmission, you had no idea which one.
#              Retransmit the whole message and hope for the better.
# After this:  parity bits act as a GPS for errors — they triangulate the
#              exact position of the flipped bit so you can correct it.

def encode(data_bits):
    """
    Pack 4 data bits into a 7-bit Hamming(7,4) codeword.
    Positions 1,2,4 are parity; positions 3,5,6,7 carry data.

    Bit numbering is 1-indexed (Hamming's original convention).
    Each parity bit covers all positions where that bit is set in the index.
    """
    d1, d2, d3, d4 = data_bits

    #  pos: 1  2  3  4  5  6  7
    #       p1 p2 d1 p3 d2 d3 d4
    p1 = d1 ^ d2 ^ d4          # covers positions 1,3,5,7
    p2 = d1 ^ d3 ^ d4          # covers positions 2,3,6,7
    p3 = d2 ^ d3 ^ d4          # covers positions 4,5,6,7

    return [p1, p2, d1, p3, d2, d3, d4]


def decode(codeword):
    """
    Receive a 7-bit codeword, compute the syndrome, and correct any single-bit error.
    The syndrome is the binary number formed by the three parity checks.
    If syndrome == 0, no error. Otherwise it names the flipped position.
    """
    p1, p2, r3, p3, r5, r6, r7 = codeword

    s1 = p1 ^ r3 ^ r5 ^ r7     # should be 0 if positions 1,3,5,7 are clean
    s2 = p2 ^ r3 ^ r6 ^ r7     # should be 0 if positions 2,3,6,7 are clean
    s3 = p3 ^ r5 ^ r6 ^ r7     # should be 0 if positions 4,5,6,7 are clean

    syndrome = s3 * 4 + s2 * 2 + s1   # binary: s3 s2 s1

    if syndrome != 0:
        codeword[syndrome - 1] ^= 1    # flip the bit at the named position

    # extract data bits from positions 3,5,6,7
    return [codeword[2], codeword[4], codeword[5], codeword[6]]


# ── Example: before and after ─────────────────────────────────────────────────

data = [1, 0, 1, 1]
codeword = encode(data)
print(f"Data:     {data}")
print(f"Encoded:  {codeword}  (added 3 parity bits)")

# simulate a single-bit error at position 5
corrupted = codeword[:]
corrupted[4] ^= 1
print(f"Corrupt:  {corrupted}  (bit 5 flipped in transit)")

recovered = decode(corrupted)
print(f"Decoded:  {recovered}  ({'OK' if recovered == data else 'FAIL'})")

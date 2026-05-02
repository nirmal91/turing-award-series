"""
Hamming(7,4) error-correcting code — full working implementation
Based on Richard Hamming's 1950 paper in the Bell System Technical Journal.

Usage:
    python implementation.py               # interactive demo
    python implementation.py --test        # run test suite (12 cases)
    python implementation.py --verbose     # show syndrome computation

Before Hamming: a single flipped bit meant retransmitting the whole message.
After Hamming:  the receiver finds and fixes the flipped bit without any retransmit.
"""

import sys
import random


# ── Hamming(7,4) codec ────────────────────────────────────────────────────────
#
# Layout (1-indexed, Hamming's convention):
#   pos  1   2   3   4   5   6   7
#        p1  p2  d1  p3  d2  d3  d4
#
# Each parity bit covers positions where its bit is set in the index:
#   p1 (pos 1): covers 1, 3, 5, 7  (binary: _01, _11, 101, 111)
#   p2 (pos 2): covers 2, 3, 6, 7  (binary: _10, _11, 110, 111)
#   p3 (pos 4): covers 4, 5, 6, 7  (binary: 100, 101, 110, 111)
#
# Syndrome: s = [s3 s2 s1] in binary points to the bad position.

PARITY_MAP = {
    # parity position -> data positions it covers (0-indexed in codeword)
    0: [0, 2, 4, 6],   # p1 covers positions 1,3,5,7
    1: [1, 2, 5, 6],   # p2 covers positions 2,3,6,7
    3: [3, 4, 5, 6],   # p3 covers positions 4,5,6,7
}

DATA_POSITIONS = [2, 4, 5, 6]   # 0-indexed positions that hold data bits


def encode(nibble: list[int]) -> list[int]:
    """Encode 4 data bits into a 7-bit Hamming codeword."""
    if len(nibble) != 4 or any(b not in (0, 1) for b in nibble):
        raise ValueError("encode() expects exactly 4 bits (each 0 or 1)")

    cw = [0] * 7
    for i, pos in enumerate(DATA_POSITIONS):
        cw[pos] = nibble[i]

    for ppos, covered in PARITY_MAP.items():
        cw[ppos] = 0
        for p in covered:
            cw[ppos] ^= cw[p]

    return cw


def decode(codeword: list[int], verbose: bool = False) -> tuple[list[int], int]:
    """
    Decode a 7-bit codeword. Returns (data_bits, error_position).
    error_position is 0 if no error, else the 1-indexed position of the flip.
    Corrects the error in place before extracting data.
    """
    if len(codeword) != 7 or any(b not in (0, 1) for b in codeword):
        raise ValueError("decode() expects exactly 7 bits (each 0 or 1)")

    cw = codeword[:]

    s1 = 0
    for p in PARITY_MAP[0]:
        s1 ^= cw[p]

    s2 = 0
    for p in PARITY_MAP[1]:
        s2 ^= cw[p]

    s3 = 0
    for p in PARITY_MAP[3]:
        s3 ^= cw[p]

    syndrome = s3 * 4 + s2 * 2 + s1

    if verbose:
        print(f"    syndrome bits: s1={s1} s2={s2} s3={s3}  →  {syndrome} (0=clean)")

    if syndrome != 0:
        bad_idx = syndrome - 1
        if verbose:
            print(f"    error at position {syndrome} (0-indexed: {bad_idx}), flipping")
        cw[bad_idx] ^= 1

    data = [cw[p] for p in DATA_POSITIONS]
    return data, syndrome


def bits_to_int(bits: list[int]) -> int:
    result = 0
    for b in bits:
        result = (result << 1) | b
    return result


def int_to_bits(n: int, width: int) -> list[int]:
    return [(n >> (width - 1 - i)) & 1 for i in range(width)]


def encode_byte(byte: int, verbose: bool = False) -> tuple[list[int], list[int]]:
    """Encode a single byte (8 bits) as two Hamming(7,4) codewords."""
    hi = int_to_bits((byte >> 4) & 0xF, 4)
    lo = int_to_bits(byte & 0xF, 4)
    cw_hi = encode(hi)
    cw_lo = encode(lo)
    if verbose:
        print(f"    byte=0x{byte:02X}  hi={hi} → {cw_hi}  lo={lo} → {cw_lo}")
    return cw_hi, cw_lo


def decode_byte(cw_hi: list[int], cw_lo: list[int], verbose: bool = False) -> tuple[int, int, int]:
    """Decode two codewords back to a byte. Returns (byte, err_pos_hi, err_pos_lo)."""
    hi, ep_hi = decode(cw_hi, verbose)
    lo, ep_lo = decode(cw_lo, verbose)
    byte = (bits_to_int(hi) << 4) | bits_to_int(lo)
    if verbose:
        print(f"    decoded: hi={hi} lo={lo}  byte=0x{byte:02X}")
    return byte, ep_hi, ep_lo


# ── Message-level encoding ────────────────────────────────────────────────────

def encode_message(text: str, verbose: bool = False) -> list[list[int]]:
    """Encode a string as a list of (cw_hi, cw_lo) pairs."""
    if verbose:
        print(f"  Encoding {len(text)} bytes...")
    result = []
    for ch in text:
        cw_hi, cw_lo = encode_byte(ord(ch), verbose)
        result.append((cw_hi, cw_lo))
    return result


def decode_message(
    codewords: list[tuple[list[int], list[int]]],
    verbose: bool = False,
) -> tuple[str, list[int]]:
    """Decode a list of (cw_hi, cw_lo) pairs back to a string."""
    chars = []
    errors = []
    for i, (cw_hi, cw_lo) in enumerate(codewords):
        if verbose:
            print(f"  char {i}:")
        byte, ep_hi, ep_lo = decode_byte(cw_hi, cw_lo, verbose)
        chars.append(chr(byte))
        if ep_hi:
            errors.append((i, 'hi', ep_hi))
        if ep_lo:
            errors.append((i, 'lo', ep_lo))
    return ''.join(chars), errors


def inject_errors(codewords, n_errors: int = 1, seed: int = 42):
    """Flip n_errors random bits across the codeword stream (one per codeword max)."""
    rng = random.Random(seed)
    corrupted = [(cw_hi[:], cw_lo[:]) for cw_hi, cw_lo in codewords]
    targets = rng.sample(range(len(corrupted)), min(n_errors, len(corrupted)))
    flipped = []
    for idx in targets:
        which = rng.choice(['hi', 'lo'])
        pos = rng.randint(0, 6)
        if which == 'hi':
            corrupted[idx][0][pos] ^= 1
        else:
            corrupted[idx][1][pos] ^= 1
        flipped.append((idx, which, pos + 1))
    return corrupted, flipped


# ── Interactive demo ──────────────────────────────────────────────────────────

def demo(verbose: bool = False):
    print("Hamming(7,4) — error-correcting code demo")
    print("Encodes text, flips random bits, self-corrects.")
    print("Type a message (or 'quit').\n")

    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in ('quit', 'exit', 'q'):
            break
        if not text:
            continue

        codewords = encode_message(text, verbose)
        total_bits = len(codewords) * 14   # 7 bits × 2 codewords per byte
        print(f"  encoded: {len(text)} bytes → {total_bits} transmitted bits")

        corrupted, flipped = inject_errors(codewords, n_errors=min(len(codewords), 3))
        if flipped:
            for idx, which, pos in flipped:
                print(f"  injected error: char {idx} ({which} nibble) bit {pos}")

        recovered, errors_found = decode_message(corrupted, verbose)
        corrected = len(errors_found)

        print(f"  recovered: \"{recovered}\"  ({corrected} error(s) auto-corrected)")
        if recovered == text:
            print("  result: perfect match")
        else:
            print("  result: MISMATCH (double-bit errors are not correctable)")
        print()


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

    # 1. encode produces correct length
    cw = encode([1, 0, 1, 1])
    check("encode length=7", len(cw), 7)

    # 2. encode all-zeros
    check("encode [0,0,0,0]", encode([0, 0, 0, 0]), [0, 0, 0, 0, 0, 0, 0])

    # 3. encode all-ones (p1=1^1^1=1, p2=1^1^1=1, p3=1^1^1=1)
    check("encode [1,1,1,1]", encode([1, 1, 1, 1]), [1, 1, 1, 1, 1, 1, 1])

    # 4. decode no error
    cw = encode([1, 0, 1, 1])
    data, err = decode(cw)
    check("decode clean: data", data, [1, 0, 1, 1])
    check("decode clean: no error", err, 0)

    # 5. decode with error at each position 1–7
    for flip_pos in range(1, 8):
        cw = encode([1, 1, 0, 1])
        cw[flip_pos - 1] ^= 1
        data, err = decode(cw)
        check(f"correct error at pos {flip_pos}", data, [1, 1, 0, 1])

    # 6. encode/decode round-trip for all 16 nibbles
    all_ok = True
    for n in range(16):
        bits = int_to_bits(n, 4)
        recovered, err = decode(encode(bits))
        if recovered != bits:
            all_ok = False
            break
    check("round-trip all 16 nibbles", all_ok, True)

    # 7. encode_byte / decode_byte round-trip
    byte, ep_hi, ep_lo = decode_byte(*encode_byte(0xA5))
    check("byte round-trip 0xA5", byte, 0xA5)
    check("byte round-trip no error", (ep_hi, ep_lo), (0, 0))

    # 8. message round-trip
    msg = "Hello"
    cw = encode_message(msg)
    recovered, errs = decode_message(cw)
    check("message round-trip 'Hello'", recovered, msg)

    # 9. message round-trip with injected single-bit errors
    cw = encode_message("Hamming")
    corrupted, _ = inject_errors(cw, n_errors=3, seed=7)
    recovered, errs = decode_message(corrupted)
    check("message self-corrects 3 single-bit errors", recovered, "Hamming")

    # 10. syndrome of clean codeword is 0
    for nibble in ([0, 0, 0, 0], [1, 1, 1, 1], [1, 0, 1, 0]):
        _, err = decode(encode(nibble))
        if err != 0:
            check("syndrome=0 for clean codewords", False, True)
            break
    else:
        check("syndrome=0 for clean codewords", True, True)

    # 11. encode raises on wrong input
    try:
        encode([1, 0])
        check("encode rejects short input", False, True)
    except ValueError:
        check("encode rejects short input", True, True)

    # 12. decode raises on wrong input
    try:
        decode([1, 0, 1])
        check("decode rejects short input", False, True)
    except ValueError:
        check("decode rejects short input", True, True)

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

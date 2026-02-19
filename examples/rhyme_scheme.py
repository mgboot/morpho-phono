"""Detect the end-rhyme scheme of a short poem.

Given the lines of a poem, compares every pair of lines using the
rhyme_analysis rime-matching engine and assigns scheme letters
(A, B, C, …) so that lines sharing a letter share a common rime.

Designed for poems under ~50 lines, though there is no hard limit.

Usage:
    python rhyme_scheme.py <poem.txt>
"""

import os
import sys

# Allow imports from the parent directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from morpho_parser import parse
from rhyme_analysis import (
    _line_tail, _find_common_rime, _is_vowel, _stress, _seq_to_ipa,
)


def rime_candidates(line):
    """Generate rime candidates for a single line of poetry.

    Parses the line for context-sensitive phonological transcription,
    then works backwards to find candidate rime segments.

    The main candidate starts at the primarily or secondarily stressed
    vowel closest to the end of the line.  If that vowel carries
    secondary stress, a second candidate is added starting at the
    preceding primary-stressed vowel (if one exists).

    Parameters
    ----------
    line : str
        A single line of poetry.

    Returns
    -------
    list[list[tuple[str, str, str]]]
        Each candidate is a list of ``(phone, morpheme_label, word)``
        tuples running from the stressed vowel to the end of the line.
    """
    parsed = parse(line.strip())

    # Flatten all phones with morpheme and word info
    flat = []
    for entry in parsed:
        for phone_str, label in entry["morphemes"]:
            for phone in phone_str.split():
                flat.append((phone, label, entry["word"]))

    if not flat:
        return []

    # Find the last stressed vowel (primary or secondary)
    last_stressed = None
    for i in range(len(flat) - 1, -1, -1):
        ph = flat[i][0]
        if _is_vowel(ph) and _stress(ph) in ("1", "2"):
            last_stressed = i
            break

    # Fallback: last vowel of any stress
    if last_stressed is None:
        for i in range(len(flat) - 1, -1, -1):
            if _is_vowel(flat[i][0]):
                last_stressed = i
                break

    if last_stressed is None:
        return []

    candidates = []

    # Main candidate: from last stressed vowel to end
    candidates.append(flat[last_stressed:])

    # If secondary stress, add candidate from preceding primary stress
    if _stress(flat[last_stressed][0]) == "2":
        for i in range(last_stressed - 1, -1, -1):
            ph = flat[i][0]
            if _is_vowel(ph) and _stress(ph) == "1":
                candidates.append(flat[i:])
                break

    return candidates


def detect_rhyme_scheme(lines):
    """Detect the end-rhyme scheme of a poem.

    Parameters
    ----------
    lines : list[str]
        Non-blank lines of a poem.

    Returns
    -------
    list[str]
        One uppercase letter per line indicating its rhyme group
        (e.g. ``['A', 'B', 'A', 'B', ...]``).
    """
    parsed = [parse(line.strip()) for line in lines]
    tails = [_line_tail(p) for p in parsed]

    scheme = [None] * len(lines)
    next_label = 0

    for i in range(len(lines)):
        if scheme[i] is not None:
            continue
        scheme[i] = chr(ord('A') + next_label)
        for j in range(i + 1, len(lines)):
            if scheme[j] is not None:
                continue
            slices, _ = _find_common_rime([tails[i], tails[j]])
            if slices[0]:
                scheme[j] = scheme[i]
        next_label += 1

    return scheme


def group_by_scheme(lines, scheme):
    """Group lines by their rhyme-scheme letter.

    Returns
    -------
    dict[str, list[tuple[int, str]]]
        Mapping from scheme letter to a list of ``(line_number, text)``
        pairs (1-indexed line numbers).
    """
    groups = {}
    for i, (line, letter) in enumerate(zip(lines, scheme)):
        groups.setdefault(letter, []).append((i + 1, line.strip()))
    return groups


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python rhyme_scheme.py <poem.txt>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        lines = [l.rstrip() for l in f if l.strip()]

    scheme = detect_rhyme_scheme(lines)

    print(f"Rhyme scheme: {''.join(scheme)}\n")
    for i, (line, letter) in enumerate(zip(lines, scheme)):
        cands = rime_candidates(line)
        phones_str = ""
        if cands:
            phones = [ph for ph, _, _ in cands[0]]
            s = _stress(cands[0][0][0])
            stress_label = "1°" if s == "1" else ("2°" if s == "2" else "0")
            phones_str = f"  rime({stress_label}): /{_seq_to_ipa(phones)}/"
            if len(cands) > 1:
                phones2 = [ph for ph, _, _ in cands[1]]
                phones_str += f"  alt(1°): /{_seq_to_ipa(phones2)}/"
        print(f"  {letter}  {i + 1:3d}  {line.strip()}{phones_str}")

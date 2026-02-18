"""Interlinear gloss display for morphologically parsed English sentences.

Prints a three-row aligned gloss in the style of linguistics journals:
  Row 1: orthographic words
  Row 2: phonemic transcription (IPA) with morpheme boundaries
  Row 3: morpheme labels

Usage:
    python gloss.py "The cats jumped over the tallest fences."
"""

import sys

from morpho_parser import parse

# ── ARPAbet → IPA conversion ────────────────────────────────────────────────

_ARPA_TO_IPA = {
    "AA": "ɑ",  "AE": "æ",  "AH": "ʌ",  "AO": "ɔ",
    "AW": "aʊ", "AY": "aɪ",
    "B": "b",   "CH": "tʃ", "D": "d",   "DH": "ð",
    "EH": "ɛ",  "ER": "ɝ",  "EY": "eɪ",
    "F": "f",   "G": "ɡ",   "HH": "h",
    "IH": "ɪ",  "IY": "i",
    "JH": "dʒ", "K": "k",   "L": "l",   "M": "m",  "N": "n",  "NG": "ŋ",
    "OW": "oʊ", "OY": "ɔɪ",
    "P": "p",   "R": "ɹ",   "S": "s",   "SH": "ʃ", "T": "t",  "TH": "θ",
    "UH": "ʊ",  "UW": "u",
    "V": "v",   "W": "w",   "Y": "j",   "Z": "z",  "ZH": "ʒ",
}


_VOWEL_BASES = {
    "AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY",
    "IH", "IY", "OW", "OY", "UH", "UW",
}

# Valid English syllable onsets (Maximal Onset Principle look-up)
_VALID_ONSETS = {
    # single consonants (all except NG)
    ("B",), ("CH",), ("D",), ("DH",), ("F",), ("G",), ("HH",),
    ("JH",), ("K",), ("L",), ("M",), ("N",), ("P",), ("R",),
    ("S",), ("SH",), ("T",), ("TH",), ("V",), ("W",), ("Y",),
    ("Z",), ("ZH",),
    # stop / fricative + liquid / glide
    ("P","L"), ("P","R"), ("B","L"), ("B","R"), ("T","R"), ("D","R"),
    ("K","L"), ("K","R"), ("G","L"), ("G","R"), ("F","L"), ("F","R"),
    ("TH","R"), ("SH","R"),
    ("S","L"), ("S","M"), ("S","N"), ("S","P"), ("S","T"), ("S","K"),
    ("S","W"), ("S","F"),
    ("T","W"), ("K","W"), ("D","W"), ("G","W"),
    # C + /j/
    ("P","Y"), ("B","Y"), ("T","Y"), ("D","Y"), ("K","Y"), ("G","Y"),
    ("F","Y"), ("V","Y"), ("TH","Y"), ("M","Y"), ("N","Y"), ("HH","Y"),
    # three-consonant onsets
    ("S","P","L"), ("S","P","R"), ("S","T","R"), ("S","K","R"),
    ("S","K","W"), ("S","K","Y"), ("S","T","Y"), ("S","P","Y"),
}


def _arpa_to_ipa(arpa_str):
    """Convert a space-separated ARPAbet string to IPA.

    Stress marks are placed at syllable onset following the Maximal
    Onset Principle, not immediately before the vowel nucleus.
    """
    phones = arpa_str.split()
    parsed = []
    for p in phones:
        base = p.rstrip("012")
        stress = p[len(base):]
        parsed.append((base, stress))

    # Determine where each stress mark should be inserted.
    # For every stressed vowel, walk backwards through preceding consonants
    # and find the longest cluster that forms a valid English onset.
    stress_at = {}  # phone index → mark
    for i, (base, stress) in enumerate(parsed):
        if stress not in ("1", "2"):
            continue
        mark = "ˈ" if stress == "1" else "ˌ"

        # Collect consonants between this vowel and the previous one
        j = i - 1
        consonants = []
        while j >= 0 and parsed[j][0] not in _VOWEL_BASES:
            consonants.insert(0, parsed[j][0])
            j -= 1

        if j < 0:
            # Word-initial: all preceding consonants belong to the onset
            onset_start = 0
        else:
            # Find the longest valid onset by trimming from the left
            onset_start = i  # fallback: right before vowel
            for k in range(len(consonants)):
                if tuple(consonants[k:]) in _VALID_ONSETS:
                    onset_start = (i - len(consonants)) + k
                    break

        stress_at[onset_start] = mark

    # Build IPA string
    ipa = []
    for i, (base, stress) in enumerate(parsed):
        if i in stress_at:
            ipa.append(stress_at[i])

        if base == "AH" and stress == "0":
            ipa.append("ə")
        elif base == "ER" and stress == "0":
            ipa.append("ɚ")
        else:
            ipa.append(_ARPA_TO_IPA.get(base, base))

    return "".join(ipa)


def format_gloss(results):
    """Format parse results as a three-row interlinear gloss."""
    words = []
    phones_col = []
    labels_col = []

    for entry in results:
        words.append(entry["word"])

        morph_phones = []
        morph_labels = []
        for phones, label in entry["morphemes"]:
            morph_phones.append(_arpa_to_ipa(phones))
            morph_labels.append(label)

        phones_col.append("-".join(morph_phones))
        labels_col.append("-".join(morph_labels))

    # Column widths based on the widest cell in each column
    widths = [
        max(len(w), len(p), len(l))
        for w, p, l in zip(words, phones_col, labels_col)
    ]

    pad = "  "
    row_words  = pad.join(w.ljust(n) for w, n in zip(words, widths))
    row_phones = pad.join(p.ljust(n) for p, n in zip(phones_col, widths))
    row_labels = pad.join(l.ljust(n) for l, n in zip(labels_col, widths))

    return f" {row_words}\n/{row_phones.rstrip()}/\n {row_labels}"


if __name__ == "__main__":
    sentence = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else "Time flies."
    )
    results = parse(sentence)
    print(format_gloss(results))

"""Rhyme analysis for lines of poetry.

Parses each line through morpho_parser to get phonological transcriptions
broken down by morpheme, identifies the common rime across lines by
aligning syllable nuclei from the end, and maps each rime phoneme back
to its source morpheme.

The rime can span multiple words (up to the last three syllables of a
line).  Syllable-nucleus alignment matches vowels from the end and
tolerates small consonant differences (voicing, single insertions or
deletions), enabling near-rhyme detection across word boundaries —
e.g. "stayed he" /eɪd hi/ ≈ "lady" /eɪdi/.

Usage:
    python rhyme_analysis.py "Time flies" "The sun will rise"
"""

import sys

from morpho_parser import parse
from gloss import _ARPA_TO_IPA

# ── Phoneme helpers ─────────────────────────────────────────────────────────

_VOWELS = {
    "AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY",
    "IH", "IY", "OW", "OY", "UH", "UW",
}


def _base(phone):
    """Strip stress digit from an ARPAbet phone."""
    return phone.rstrip("012")


def _is_vowel(phone):
    return _base(phone) in _VOWELS


def _stress(phone):
    b = _base(phone)
    return phone[len(b):]


def _to_ipa(phone):
    """Convert one ARPAbet phone to IPA."""
    b = _base(phone)
    if b == "AH" and _stress(phone) == "0":
        return "ə"
    if b == "ER" and _stress(phone) == "0":
        return "ɚ"
    return _ARPA_TO_IPA.get(b, b)


def _seq_to_ipa(phones):
    """Convert a sequence of ARPAbet phones to an IPA string."""
    return "".join(_to_ipa(p) for p in phones)


# ── Fuzzy matching (soundex-like equivalence classes) ───────────────────────

_CONSONANT_CLASS = {
    "P": "LB_STOP", "B": "LB_STOP",
    "T": "AL_STOP", "D": "AL_STOP",
    "K": "VL_STOP", "G": "VL_STOP",
    "F": "LD_FRIC", "V": "LD_FRIC",
    "TH": "DN_FRIC", "DH": "DN_FRIC",
    "S": "AL_FRIC", "Z": "AL_FRIC",
    "SH": "PA_FRIC", "ZH": "PA_FRIC",
    "CH": "AFFR", "JH": "AFFR",
    "M": "LB_NAS", "N": "AL_NAS", "NG": "VL_NAS",
    "L": "LAT", "R": "RHOT",
    "HH": "GLOT", "W": "LB_GLI", "Y": "PL_GLI",
}

_VOWEL_CLASS = {
    "IY": "FRONT_HI", "IH": "FRONT_HI",
    "EY": "FRONT_MD", "EH": "FRONT_MD",
    "AE": "FRONT_LO",
    "AH": "CENTRAL", "ER": "CENTRAL",
    "UW": "BACK_HI", "UH": "BACK_HI",
    "OW": "BACK_MD", "AO": "BACK_MD",
    "AA": "BACK_LO",
    "AY": "DIPH_AY", "AW": "DIPH_AW", "OY": "DIPH_OY",
}


def _soundex(phone):
    b = _base(phone)
    return _VOWEL_CLASS.get(b) or _CONSONANT_CLASS.get(b, b)


def _phones_match(a, b, fuzzy=False):
    """True if two ARPAbet phones are equivalent for rhyme purposes.

    Exact mode compares base phones (ignoring stress).  Fuzzy mode also
    treats voiced/voiceless pairs and nearby vowels as equivalent.
    """
    if _base(a) == _base(b):
        return True
    return fuzzy and _soundex(a) == _soundex(b)


# ── Line-tail extraction ───────────────────────────────────────────────────

_MAX_RIME_SYLLABLES = 3


def _line_tail(parse_results, max_syllables=_MAX_RIME_SYLLABLES):
    """Phone→morpheme mapping for the last *max_syllables* syllables of a line.

    Returns a list of ``(phone, label, word)`` tuples spanning back from the
    end of the line up to *max_syllables* vowels deep.
    """
    flat = []
    for entry in parse_results:
        for phone_str, label in entry["morphemes"]:
            for phone in phone_str.split():
                flat.append((phone, label, entry["word"]))

    vowel_count = 0
    cutoff = 0
    for i in range(len(flat) - 1, -1, -1):
        if _is_vowel(flat[i][0]):
            vowel_count += 1
            if vowel_count >= max_syllables:
                cutoff = i
                break

    return flat[cutoff:]


def _rime_start(phones):
    """Index of the last stressed vowel (primary or secondary) in *phones*.

    Falls back to the last vowel of any stress if none carry 1 or 2.
    """
    for i in range(len(phones) - 1, -1, -1):
        if _is_vowel(phones[i]) and _stress(phones[i]) in ("1", "2"):
            return i
    for i in range(len(phones) - 1, -1, -1):
        if _is_vowel(phones[i]):
            return i
    return 0


def _common_suffix_len(rimes, max_len, fuzzy=False):
    """Longest phone-by-phone suffix shared by every candidate rime."""
    n = 0
    for i in range(1, max_len + 1):
        ref = rimes[0][-i][0]
        if all(_phones_match(ref, r[-i][0], fuzzy=fuzzy) for r in rimes[1:]):
            n = i
        else:
            break
    return n


# ── Syllable-aligned rime matching ─────────────────────────────────────────

def _edit_distance_le_one(a, b):
    """True if *a* and *b* differ by at most one insertion or deletion."""
    if a == b:
        return True
    if abs(len(a) - len(b)) != 1:
        return False
    longer, shorter = (a, b) if len(a) > len(b) else (b, a)
    for i in range(len(longer)):
        if longer[:i] + longer[i + 1:] == shorter:
            return True
    return False


def _consonants_compatible(segments):
    """True if consonant segments from every tail are compatible.

    Allows exact match, soundex-class match, or a single consonant
    insertion / deletion across any pair.

    Returns ``(ok, fuzzy_needed)``.
    """
    if len(segments) < 2:
        return True, False

    ref_base = [_base(c) for c in segments[0]]
    fuzzy_needed = False

    for seg in segments[1:]:
        other_base = [_base(c) for c in seg]
        if ref_base == other_base:
            continue

        # Soundex-class match
        ref_sx = [_soundex(c) for c in segments[0]]
        other_sx = [_soundex(c) for c in seg]
        if ref_sx == other_sx:
            fuzzy_needed = True
            continue

        # Allow one insertion / deletion (base or soundex level)
        if _edit_distance_le_one(ref_base, other_base):
            fuzzy_needed = True
            continue
        if _edit_distance_le_one(ref_sx, other_sx):
            fuzzy_needed = True
            continue

        return False, False

    return True, fuzzy_needed


def _find_common_rime(tails):
    """Longest common rime across *tails* via syllable-nucleus alignment.

    Matches vowel nuclei from the end of each tail outward, checking that
    intervening consonant material is compatible (exact, soundex, or within
    one consonant insertion/deletion).

    Returns ``(slices, fuzzy)`` where *slices[i]* is the rime portion of
    *tails[i]* and *fuzzy* is ``True`` when near-rhyme tolerance was used.
    """
    # Locate vowel positions in each tail
    tail_vi = [
        [i for i, (ph, _, _) in enumerate(tail) if _is_vowel(ph)]
        for tail in tails
    ]
    min_vowels = min((len(v) for v in tail_vi), default=0)
    if min_vowels == 0:
        return [[] for _ in tails], False

    best_n = 0
    is_fuzzy = False

    for n in range(1, min_vowels + 1):
        # ── vowel nuclei must match ──
        vphs = [tails[ti][tail_vi[ti][-n]][0] for ti in range(len(tails))]
        ref = vphs[0]
        exact = all(_base(ref) == _base(v) for v in vphs[1:])
        fuzzy = all(_soundex(ref) == _soundex(v) for v in vphs[1:])
        if not exact and not fuzzy:
            break
        step_fuzzy = not exact

        # ── consonant material must be compatible ──
        if n == 1:
            # trailing consonants (after last vowel to end of tail)
            segs = [
                [tails[ti][j][0]
                 for j in range(tail_vi[ti][-1] + 1, len(tails[ti]))]
                for ti in range(len(tails))
            ]
        else:
            # consonants between the two most-recently matched vowels
            segs = [
                [tails[ti][j][0]
                 for j in range(tail_vi[ti][-n] + 1, tail_vi[ti][-(n - 1)])
                 if not _is_vowel(tails[ti][j][0])]
                for ti in range(len(tails))
            ]

        c_ok, c_fuzzy = _consonants_compatible(segs)
        if not c_ok:
            break

        if step_fuzzy or c_fuzzy:
            is_fuzzy = True
        best_n = n

    if best_n == 0:
        return [[] for _ in tails], False

    slices = [tails[ti][tail_vi[ti][-best_n]:] for ti in range(len(tails))]
    return slices, is_fuzzy


# ── Public API ──────────────────────────────────────────────────────────────

def analyse(lines):
    """Analyse the rime shared by two or more lines of rhyming poetry.

    Parameters
    ----------
    lines : list[str]
        Lines of poetry (≥ 2) assumed to rhyme with each other.

    Returns
    -------
    dict
        ``rime_phones`` – ARPAbet phones of the canonical common rime
                          (taken from the first line).
        ``fuzzy``       – ``True`` if fuzzy matching was needed.
        ``lines``       – per-line dicts, each containing:

            ``text``       – original line text.
            ``parse``      – full ``morpho_parser.parse()`` output.
            ``rhyme_word`` – the last content word.
            ``rime``       – list of ``(phone, morpheme_label, word)``
                             tuples for the rime as realised in this line.
            ``rime_morpheme_count`` – number of distinct morphemes
                             spanned by the rime (identified by
                             ``(label, word)`` pairs).
    """
    parsed = [parse(l.strip()) for l in lines]
    tails = [_line_tail(p) for p in parsed]

    slices, fuzzy = _find_common_rime(tails)

    rime_phones = [p for p, _, _ in slices[0]] if slices[0] else []

    out_lines = []
    for i, line in enumerate(lines):
        seg = slices[i]
        morpheme_count = len({(lbl, w) for _, lbl, w in seg}) if seg else 0
        out_lines.append({
            "text": line.strip(),
            "parse": parsed[i],
            "rhyme_word": parsed[i][-1]["word"] if parsed[i] else "",
            "rime": seg,
            "rime_morpheme_count": morpheme_count,
        })

    return {"rime_phones": rime_phones, "fuzzy": fuzzy, "lines": out_lines}


# ── Formatting ──────────────────────────────────────────────────────────────

def format_analysis(result):
    """Human-readable report of a rime analysis result."""
    buf = []

    rime = result["rime_phones"]
    if rime:
        kind = "fuzzy" if result["fuzzy"] else "exact"
        buf.append(
            f"Common rime: {' '.join(rime)}  [{_seq_to_ipa(rime)}]  ({kind} match)"
        )
    else:
        buf.append("No common rime detected.")
    buf.append("")

    for idx, info in enumerate(result["lines"], 1):
        buf.append(f"── Line {idx}: \"{info['text']}\" ──")

        # Full morphological parse
        for entry in info["parse"]:
            parts = []
            for ph_str, label in entry["morphemes"]:
                parts.append(f"{label}({_seq_to_ipa(ph_str.split())})")
            buf.append(f"  {entry['word']:15s} {' + '.join(parts)}")

        # Rime → morpheme mapping
        if info["rime"]:
            labels = list(dict.fromkeys(
                f"{lbl}({w})" for _, lbl, w in info["rime"]
            ))
            n_morph = info["rime_morpheme_count"]
            buf.append(
                f"  Rime [{_seq_to_ipa([p for p, _, _ in info['rime']])}] "
                f"spans {n_morph} morpheme{'s' if n_morph != 1 else ''}: "
                f"{' + '.join(labels)}"
            )
            for phone, label, word in info["rime"]:
                buf.append(f"    {phone:6s} [{_to_ipa(phone):3s}]  ← {label} ({word})")
        buf.append("")

    return "\n".join(buf)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            'Usage: python rhyme_analysis.py "line 1" "line 2" ["line 3" ...]'
        )
        sys.exit(1)
    result = analyse(sys.argv[1:])
    print(format_analysis(result))

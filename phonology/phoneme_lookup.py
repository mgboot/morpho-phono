"""Phoneme lookup via CMU Pronouncing Dictionary with g2p_en fallback."""

import logging
import re
import urllib.request
from pathlib import Path

import yaml
from g2p_en import G2p

logger = logging.getLogger(__name__)

g2p = G2p()

# ── Phoneme mergers applied at load time ─────────────────────────────────────

# Caught–cot merger: collapse AO → AA (with stress digit preserved).
# Set to False to maintain the AO / AA distinction.
COT_CAUGHT_MERGER = True

_MERGER_RE = re.compile(r"^AO(\d?)$")


def _apply_mergers(phones):
    """Apply active phoneme mergers to a list of ARPAbet phones."""
    if COT_CAUGHT_MERGER:
        phones = [_MERGER_RE.sub(r"AA\1", p) for p in phones]
    return phones

# ── Load CMU Pronouncing Dictionary from source ─────────────────────────────

_CMUDICT_URL = "https://raw.githubusercontent.com/Alexir/CMUdict/master/cmudict-0.7b"
_CMUDICT_CACHE = Path(__file__).with_name(".cmudict-0.7b")


def _load_cmudict(url=_CMUDICT_URL, cache_path=_CMUDICT_CACHE):
    """Download and parse the CMU Pronouncing Dictionary from source.

    The raw file is cached locally so subsequent runs skip the download.
    Returns a dict mapping lowercase words to lists of phoneme lists.
    """
    if not cache_path.exists():
        logger.info("Downloading CMU dict from %s …", url)
        try:
            urllib.request.urlretrieve(url, cache_path)
        except (urllib.error.URLError, OSError) as exc:
            raise RuntimeError(
                f"Failed to download CMU dict from {url}. "
                "Check your network connection or supply the file manually "
                f"at {cache_path}."
            ) from exc

    cmu = {}
    with open(cache_path, encoding="latin-1") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";;;"):
                continue
            parts = line.split("  ", 1)
            if len(parts) != 2:
                continue
            word, phones_str = parts
            # Strip variant markers like "(1)", "(2)"
            if "(" in word:
                word = word[: word.index("(")]
            word = word.lower()
            phones = _apply_mergers(phones_str.strip().split())
            cmu.setdefault(word, []).append(phones)
    return cmu


cmu = _load_cmudict()

# ── Contraction suffixes ────────────────────────────────────────────────────
# spaCy splits contractions (e.g. "wouldn't" → "would" + "n't"), but the
# suffix tokens are absent from CMU Dict or mis-mapped (e.g. "'s" → letter
# name).  These hand-curated entries are checked before the CMU/g2p path.
_CONTRACTION_PHONES = {
    "n't": ["AH0", "N", "T"],
    "'ll": ["AH0", "L"],
    "'re": ["ER0"],
    "'ve": ["AH0", "V"],
    "'d":  ["AH0", "D"],
    "'s":  ["Z"],
    "'m":  ["AH0", "M"],
}

# ── Heteronym disambiguation ────────────────────────────────────────────────
# Loaded from heteronyms.yaml — see that file and extract_heteronyms.py for
# details.  Only entries whose ``tags`` list is non-empty are used.

_HETERONYMS_PATH = Path(__file__).with_name("heteronyms.yaml")


def _load_heteronyms(path=_HETERONYMS_PATH):
    """Load the heteronym table from YAML.

    Returns a dict mapping lowercase words to lists of
    ``(tag_frozenset, phone_list)`` tuples.  Entries with empty tags are
    skipped (they are uncurated placeholders for the user to fill in).
    """
    if not path.exists():
        logger.warning("Heteronym table not found at %s", path)
        return {}
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    table = {}
    for word, entries in raw.items():
        resolved = []
        for entry in entries:
            tags = entry.get("tags", [])
            if not tags:
                continue
            phones = entry["phones"].split()
            resolved.append((frozenset(tags), phones))
        if resolved:
            table[word.lower()] = resolved
    return table


_HETERONYM_TABLE = _load_heteronyms()


def get_phonemes(word, tag=None):
    """Look up ARPAbet phonemes for a word.

    Checks the locally-cached CMU Dict first, then falls back to g2p_en.
    When *tag* (a SpaCy fine-grained POS tag such as ``"NN"`` or ``"VBD"``)
    is provided and the word has multiple CMU Dict entries, the heteronym
    table is consulted to select the correct pronunciation.
    """
    word_lower = word.lower()

    # Contraction suffixes that spaCy splits off
    if word_lower in _CONTRACTION_PHONES:
        return list(_CONTRACTION_PHONES[word_lower])

    # Heteronym disambiguation when a POS tag is available
    if tag and word_lower in _HETERONYM_TABLE:
        entries = cmu.get(word_lower)
        if entries and len(entries) > 1:
            for tag_set, phones in _HETERONYM_TABLE[word_lower]:
                if tag in tag_set:
                    return _apply_mergers(phones)

    result = cmu.get(word_lower)
    if result:
        return result[0]
    # G2P fallback: g2p_en returns a mix of phonemes and spaces; filter to phonemes only
    raw = g2p(word)
    phones = _apply_mergers([p for p in raw if p.strip()])
    if phones:
        return phones
    return ["N/A"]

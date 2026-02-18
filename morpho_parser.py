"""Morphological parser that decomposes English words into morpheme phones.

Takes an English sentence, performs POS tagging and lemmatisation with spaCy,
looks up phonemes via the CMU Pronouncing Dictionary (downloaded directly from
source), then splits each word's phonemes into root + inflectional-suffix
morphemes where applicable.  Words not found in CMU Dict are handled by a
g2p_en grapheme-to-phoneme fallback.

Usage:
    python morpho_parser.py "The quick brown fox jumps over the lazy dog."
"""

import sys
import logging
import urllib.request
from pathlib import Path

import yaml
import spacy
from g2p_en import G2p

logger = logging.getLogger(__name__)

nlp = spacy.load("en_core_web_md")
g2p = G2p()

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
            phones = phones_str.strip().split()
            cmu.setdefault(word, []).append(phones)
    return cmu


cmu = _load_cmudict()

# ── Load inflection rules from YAML ─────────────────────────────────────────

_RULES_PATH = Path(__file__).with_name("inflection_rules.yaml")


def _load_rules(path=_RULES_PATH):
    """Read inflection rules from a YAML file.

    Returns a list of (pos, tag, suffixes, label) tuples matching the
    format expected by decompose_morphemes().
    """
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return [(r["pos"], r["tag"], r["suffixes"], r["label"]) for r in raw]


INFLECTION_RULES = _load_rules()

# ── Core logic ───────────────────────────────────────────────────────────────


def get_phonemes(word):
    """Look up ARPAbet phonemes for a word.

    Checks the locally-cached CMU Dict first, then falls back to g2p_en.
    """
    result = cmu.get(word.lower())
    if result:
        return result[0]
    # G2P fallback: g2p_en returns a mix of phonemes and spaces; filter to phonemes only
    raw = g2p(word)
    phones = [p for p in raw if p.strip()]
    if phones:
        return phones
    return ["N/A"]


def decompose_morphemes(word_phones, lemma_phones, pos, tag):
    """Split a word's phonemes into root morpheme + inflectional suffix.

    Returns a list of (phoneme_string, morpheme_label) tuples.
    If the word is uninflected or irregular, the whole word is returned as one
    morpheme (irregular forms are tagged e.g. "VERB<PAST>").
    """
    word_str = " ".join(word_phones)

    if word_phones == lemma_phones:
        return [(word_str, pos)]

    for rule_pos, rule_tag, candidates, label in INFLECTION_RULES:
        if pos == rule_pos and tag == rule_tag:
            for suffix in candidates:
                n = len(suffix)
                if len(word_phones) > n and word_phones[:-n] == lemma_phones:
                    return [
                        (" ".join(word_phones[:-n]), pos),
                        (" ".join(suffix), label),
                    ]
            # Rule matched but no clean suffix strip → irregular form
            return [(word_str, f"{pos}<{label}>")]

    return [(word_str, pos)]


def parse(sentence):
    """Parse *sentence* and return a list of per-word morpheme breakdowns.

    Returns:
        list of dicts with keys ``word`` and ``morphemes``, where
        ``morphemes`` is a list of ``(phones, label)`` tuples.
    """
    doc = nlp(sentence)
    results = []
    for token in doc:
        if token.is_punct:
            continue
        word = token.text.lower()
        lemma = token.lemma_.lower()
        word_phones = get_phonemes(word)
        lemma_phones = get_phonemes(lemma)
        morphemes = decompose_morphemes(word_phones, lemma_phones, token.pos_, token.tag_)
        results.append({"word": token.text, "morphemes": morphemes})
    return results


def format_results(results):
    """Return a human-readable string for console output."""
    lines = []
    for entry in results:
        lines.append(f"{entry['word']:12} -> {entry['morphemes']}")
    return "\n".join(lines)


if __name__ == "__main__":
    sentence = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Much I marveled this ungainly fowl to hear discourse so plainly."
    results = parse(sentence)
    print(format_results(results))

"""Morphological parser that decomposes English words into morpheme phones.

Takes an English sentence, performs POS tagging and lemmatisation with spaCy,
looks up phonemes via the CMU Pronouncing Dictionary, then splits each word's
phonemes into root + inflectional-suffix morphemes where applicable.

Usage:
    python morpho_parser.py "The quick brown fox jumps over the lazy dog."
"""

import sys
from pathlib import Path

import yaml
import spacy
import nltk
from nltk.corpus import cmudict
from g2p_en import G2p

nltk.download("cmudict", quiet=True)

nlp = spacy.load("en_core_web_md")
cmu = cmudict.dict()
g2p = G2p()

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
    """Look up ARPAbet phonemes for a word. Falls back to g2p_en if not in CMU dict."""
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
    lemma_str = " ".join(lemma_phones)

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
    """Parse *sentence* and return a dict mapping each word to its morpheme list.

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

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

import spacy

from phoneme_lookup import get_phonemes
from inflection import decompose_morphemes

nlp = spacy.load("en_core_web_md")


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
        word_phones = get_phonemes(word, tag=token.tag_)
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

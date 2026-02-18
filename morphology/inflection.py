"""Inflectional morpheme decomposition using suffix-stripping rules."""

from pathlib import Path

import yaml

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

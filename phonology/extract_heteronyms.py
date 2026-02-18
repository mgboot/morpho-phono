#!/usr/bin/env python
"""Extract words with multiple CMU Dict pronunciations into heteronyms.yaml.

Parses the locally-cached CMU Pronouncing Dictionary (.cmudict-0.7b) and
writes every multi-pronunciation word into heteronyms.yaml.  Existing
curated entries (those with non-empty ``tags`` lists) are preserved;
only new words are appended with empty tags for the user to fill in.

Usage:
    python extract_heteronyms.py
"""

from pathlib import Path
import re

import yaml

_CMUDICT_CACHE = Path(__file__).with_name(".cmudict-0.7b")
_HETERONYMS_PATH = Path(__file__).with_name("heteronyms.yaml")

_YAML_HEADER = """\
# Heteronym disambiguation table for words with multiple CMU Dict
# pronunciations.
#
# Each word maps to a list of pronunciation variants.  To enable
# POS-based disambiguation, populate the `tags` field with the SpaCy
# fine-grained POS tags (Penn Treebank tagset) for that pronunciation.
# Variants with empty tags are uncurated and ignored at runtime.
#
# To regenerate uncurated entries from the CMU Dict:
#     python extract_heteronyms.py
#
# Tag groups for reference:
#   Nouns:      NN, NNS, NNP, NNPS
#   Verbs:      VB, VBP, VBZ, VBG, VBD, VBN
#   Adjectives: JJ, JJR, JJS
#   Adverbs:    RB, RBR, RBS
"""


def _parse_cmudict(path=_CMUDICT_CACHE):
    """Return ``{word: [phones_str, ...]}`` for every word in the CMU dict."""
    if not path.exists():
        raise FileNotFoundError(
            f"CMU dict cache not found at {path}. "
            "Run phoneme_lookup.py once to download it."
        )
    entries = {}
    with open(path, encoding="latin-1") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(";;;"):
                continue
            parts = line.split("  ", 1)
            if len(parts) != 2:
                continue
            word, phones = parts
            if "(" in word:
                word = word[: word.index("(")]
            word = word.lower()
            entries.setdefault(word, []).append(phones.strip())
    return entries


def _load_existing(path=_HETERONYMS_PATH):
    """Load existing heteronyms.yaml, preserving curated entries."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _format_tags(tags):
    """Format a tags list as a compact YAML flow sequence."""
    if not tags:
        return "[]"
    return "[" + ", ".join(str(t) for t in tags) + "]"


_YAML_SAFE_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_'-]*$")


def _format_key(word):
    """Quote a YAML key if it contains characters that need escaping."""
    if _YAML_SAFE_KEY.match(word):
        return word
    return f'"{word}"'


def _write_yaml(data, path=_HETERONYMS_PATH):
    """Write the heteronym table as clean, hand-editable YAML."""
    curated = {}
    uncurated = {}
    for word in sorted(data):
        entries = data[word]
        if any(e.get("tags") for e in entries):
            curated[word] = entries
        else:
            uncurated[word] = entries

    with open(path, "w", encoding="utf-8") as f:
        f.write(_YAML_HEADER)

        if curated:
            f.write(
                "\n# ── Curated entries "
                "──────────────────────────────────────────────────────────\n\n"
            )
            for word in sorted(curated):
                f.write(f"{_format_key(word)}:\n")
                for entry in curated[word]:
                    f.write(f"- tags: {_format_tags(entry.get('tags', []))}\n")
                    f.write(f'  phones: "{entry["phones"]}"\n')
                f.write("\n")

        if uncurated:
            f.write(
                "# ── Uncurated entries (fill in tags to enable disambiguation) "
                "────────────\n\n"
            )
            for word in sorted(uncurated):
                f.write(f"{_format_key(word)}:\n")
                for entry in uncurated[word]:
                    f.write("- tags: []\n")
                    f.write(f'  phones: "{entry["phones"]}"\n')
                f.write("\n")


def main():
    cmu = _parse_cmudict()
    multi = {w: phones for w, phones in cmu.items() if len(phones) > 1}

    existing = _load_existing()

    # Merge: preserve curated entries, add new multi-pronunciation words
    merged = dict(existing)
    for word, phone_list in sorted(multi.items()):
        if word not in merged:
            merged[word] = [{"tags": [], "phones": p} for p in phone_list]

    _write_yaml(merged)

    n_curated = sum(
        1 for entries in merged.values() if any(e.get("tags") for e in entries)
    )
    n_total = len(merged)
    print(
        f"Wrote {path.name}: "
        f"{n_curated} curated, {n_total - n_curated} uncurated entries."
    )


if __name__ == "__main__":
    path = _HETERONYMS_PATH
    main()

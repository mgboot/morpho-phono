"""Analyse end-rhyme in a short poem.

Detects the rhyme scheme automatically, groups lines by their scheme
letter, runs rhyme_analysis.analyse() on each group, and writes the
results to a CSV file — the same kind of output that analyse_essay.py
produces for heroic couplets, generalised to any rhyme scheme.

Usage:
    python analyse_poem.py <poem.txt> [output.csv]
"""

import csv
import os
import sys

# Allow imports from the parent directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rhyme_analysis import analyse, _seq_to_ipa
from rhyme_scheme import detect_rhyme_scheme, group_by_scheme

CSV_FIELDS = [
    "scheme_letter",
    "line_num",
    "line_text",
    "rime_phones",
    "rime_ipa",
    "fuzzy",
    "rhyme_words",
    "rime_morphemes",
    "morpheme_count",
]


def _rime_words(rime_seg):
    """Distinct words (in order) that contribute to the rime segment."""
    seen = set()
    words = []
    for _, _, w in rime_seg:
        if w not in seen:
            seen.add(w)
            words.append(w)
    return words


def _rime_morphemes(rime_seg):
    """Distinct (label, word) morpheme tags that the rime spans, in order."""
    seen = set()
    morphemes = []
    for _, lbl, w in rime_seg:
        key = (lbl, w)
        if key not in seen:
            seen.add(key)
            morphemes.append(f"{lbl}({w})")
    return morphemes


def _empty_row(letter, num, text):
    return {
        "scheme_letter": letter,
        "line_num": num,
        "line_text": text,
        "rime_phones": "",
        "rime_ipa": "",
        "fuzzy": "",
        "rhyme_words": "",
        "rime_morphemes": "",
        "morpheme_count": "",
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyse_poem.py <poem.txt> [output.csv]")
        sys.exit(1)

    poem_path = sys.argv[1]
    base = os.path.splitext(os.path.basename(poem_path))[0]
    output_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(__file__), f"{base}_rhymes.csv"
    )

    with open(poem_path, encoding="utf-8") as f:
        lines = [l.rstrip() for l in f if l.strip()]

    print(f"Read {len(lines)} lines from {poem_path}")

    scheme = detect_rhyme_scheme(lines)
    scheme_str = "".join(scheme)
    print(f"Detected rhyme scheme: {scheme_str}")

    groups = group_by_scheme(lines, scheme)
    rhyme_groups = {k: v for k, v in groups.items() if len(v) >= 2}
    print(
        f"Found {len(rhyme_groups)} rhyme group(s), "
        f"{len(groups) - len(rhyme_groups)} unrhymed line(s)"
    )
    print(f"Writing results to {output_path}")

    with open(output_path, "w", newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(fout, fieldnames=CSV_FIELDS)
        writer.writeheader()

        for letter in sorted(groups.keys()):
            group = groups[letter]
            line_texts = [text for _, text in group]

            if len(group) < 2:
                num, text = group[0]
                writer.writerow(_empty_row(letter, num, text))
                continue

            try:
                result = analyse(line_texts)
            except Exception as exc:
                print(f"  ⚠ group {letter} failed: {exc}")
                for num, text in group:
                    writer.writerow(_empty_row(letter, num, text))
                continue

            rime_phones = " ".join(result["rime_phones"])
            rime_ipa = (
                _seq_to_ipa(result["rime_phones"])
                if result["rime_phones"]
                else ""
            )

            for idx, (num, _) in enumerate(group):
                info = result["lines"][idx]
                writer.writerow({
                    "scheme_letter": letter,
                    "line_num": num,
                    "line_text": info["text"],
                    "rime_phones": rime_phones,
                    "rime_ipa": rime_ipa,
                    "fuzzy": result["fuzzy"],
                    "rhyme_words": " | ".join(_rime_words(info["rime"])),
                    "rime_morphemes": " + ".join(
                        _rime_morphemes(info["rime"])
                    ),
                    "morpheme_count": info["rime_morpheme_count"],
                })

    print("Done.")


if __name__ == "__main__":
    main()

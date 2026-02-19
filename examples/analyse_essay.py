"""Analyse rhyming couplets in Pope's Essay on Man.

Reads essay-on-man.txt, pairs consecutive lines as heroic couplets
(AABB rhyme scheme), runs each pair through rhyme_analysis.analyse(),
and writes the results to a CSV file in this directory.
"""

import csv
import os
import sys

# Allow imports from the parent directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rhyme_analysis import analyse, _seq_to_ipa, _to_ipa

ESSAY_PATH = os.path.join(os.path.dirname(__file__), "essay-on-man.txt")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "couplet_rhymes.csv")

CSV_FIELDS = [
    "couplet",
    "line1_num",
    "line2_num",
    "line1_text",
    "line2_text",
    "rime_phones",
    "rime_ipa",
    "fuzzy",
    "line1_rhyme_words",
    "line2_rhyme_words",
    "line1_rime_morphemes",
    "line2_rime_morphemes",
    "line1_morpheme_count",
    "line2_morpheme_count",
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


def read_lines(path):
    """Read the essay, strip trailing whitespace, skip blank lines."""
    with open(path, encoding="utf-8") as f:
        lines = [l.rstrip() for l in f if l.strip()]
    return lines


def main():
    lines = read_lines(ESSAY_PATH)
    n_couplets = len(lines) // 2

    print(f"Read {len(lines)} lines → {n_couplets} couplets")
    print(f"Writing results to {OUTPUT_PATH}")

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(fout, fieldnames=CSV_FIELDS)
        writer.writeheader()

        for i in range(n_couplets):
            line1 = lines[2 * i]
            line2 = lines[2 * i + 1]
            couplet_num = i + 1

            if couplet_num % 50 == 0 or couplet_num == 1:
                print(f"  couplet {couplet_num}/{n_couplets} …")

            try:
                result = analyse([line1, line2])
            except Exception as exc:
                print(f"  ⚠ couplet {couplet_num} failed: {exc}")
                writer.writerow({
                    "couplet": couplet_num,
                    "line1_num": 2 * i + 1,
                    "line2_num": 2 * i + 2,
                    "line1_text": line1.strip(),
                    "line2_text": line2.strip(),
                    "rime_phones": "",
                    "rime_ipa": "",
                    "fuzzy": "",
                    "line1_rhyme_words": "",
                    "line2_rhyme_words": "",
                    "line1_rime_morphemes": "",
                    "line2_rime_morphemes": "",
                    "line1_morpheme_count": "",
                    "line2_morpheme_count": "",
                })
                continue

            info1, info2 = result["lines"]
            rime_phones = " ".join(result["rime_phones"])
            rime_ipa = _seq_to_ipa(result["rime_phones"]) if result["rime_phones"] else ""

            writer.writerow({
                "couplet": couplet_num,
                "line1_num": 2 * i + 1,
                "line2_num": 2 * i + 2,
                "line1_text": info1["text"],
                "line2_text": info2["text"],
                "rime_phones": rime_phones,
                "rime_ipa": rime_ipa,
                "fuzzy": result["fuzzy"],
                "line1_rhyme_words": " | ".join(_rime_words(info1["rime"])),
                "line2_rhyme_words": " | ".join(_rime_words(info2["rime"])),
                "line1_rime_morphemes": " + ".join(_rime_morphemes(info1["rime"])),
                "line2_rime_morphemes": " + ".join(_rime_morphemes(info2["rime"])),
                "line1_morpheme_count": info1["rime_morpheme_count"],
                "line2_morpheme_count": info2["rime_morpheme_count"],
            })

    print("Done.")


if __name__ == "__main__":
    main()

# Morpho Parser

A morphological parser that decomposes English words into morpheme phones. It takes an English sentence, performs POS tagging and lemmatisation with [spaCy](https://spacy.io/), looks up phonemes via the [CMU Pronouncing Dictionary](http://www.speech.cs.cmu.edu/cgi-bin/cmudict) (with a [g2p_en](https://github.com/Kyubyong/g2p) fallback for out-of-vocabulary words), then splits each word's phonemes into root + inflectional-suffix morphemes where applicable.

## Setup

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_md
```

## Usage

```bash
python morpho_parser.py "The quick brown fox jumps over the lazy dogs."
```

Output maps each word to its morpheme breakdown:

```
The          -> [('DH AH0', 'DET')]
quick        -> [('K W IH1 K', 'ADJ')]
brown        -> [('B R AW1 N', 'ADJ')]
fox          -> [('F AA1 K S', 'NOUN')]
jumps        -> [('JH AH1 M P', 'VERB'), ('S', 'PRES')]
over         -> [('OW1 V ER0', 'ADP')]
the          -> [('DH AH0', 'DET')]
lazy         -> [('L EY1 Z IY0', 'ADJ')]
dogs         -> [('D AO1 G', 'NOUN'), ('Z', 'PL')]
```

## Project Structure

| File | Description |
|------|-------------|
| `morpho_parser.py` | Main parser — POS tagging, phoneme lookup, and morpheme decomposition |
| `inflection_rules.yaml` | Inflection rules in editable YAML (see below) |
| `requirements.txt` | Python dependencies: spaCy, NLTK, PyYAML, g2p-en |

## Editing Inflection Rules

Rules live in `inflection_rules.yaml` and are loaded automatically at import time. Each rule has four fields:

| Field | Description |
|-------|-------------|
| `pos` | spaCy coarse POS tag (`VERB`, `NOUN`, `ADJ`, `ADV`) |
| `tag` | Fine-grained Penn Treebank tag (`VBZ`, `VBD`, `NNS`, etc.) |
| `label` | Morpheme label assigned to the stripped suffix (`PRES`, `PAST`, `PL`, etc.) |
| `suffixes` | List of candidate phoneme sequences to try stripping from the inflected form |

Example rule:

```yaml
# 3rd-person singular present: jumps → jump + /S/, flies → fly + /Z/
- pos: VERB
  tag: VBZ
  label: PRES
  suffixes:
    - [Z]
    - [S]
    - [IH0, Z]
    - [AH0, Z]
```

The parser tries each suffix in order. If stripping a suffix from the inflected word's phonemes yields the lemma's phonemes, it splits them into root + suffix morphemes. If a rule matches the POS/tag but no suffix cleanly strips, the word is marked as an irregular form (e.g. `VERB<PAST>`).

Phoneme symbols follow the [ARPAbet](https://en.wikipedia.org/wiki/ARPABET) notation used by the CMU dictionary.

# morpho-phono

Tools for English morpho-phonological analysis: morpheme decomposition,
interlinear glossing, and rhyme analysis.

Takes English text, performs POS tagging and lemmatisation with
[spaCy](https://spacy.io/), looks up phonemes via the
[CMU Pronouncing Dictionary](https://github.com/Alexir/CMUdict)
(downloaded on first run, with a [g2p_en](https://github.com/Kyubyong/g2p)
fallback for out-of-vocabulary words), and splits each word's phonemes
into root + inflectional-suffix morphemes where applicable.

## Setup

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_md
```

## Morphological Parser

`morpho_parser.py` decomposes each word into morpheme phones.

```bash
python morpho_parser.py "The quick brown fox jumps over the lazy dogs."
```

```
The          -> [('DH AH0', 'DET')]
quick        -> [('K W IH1 K', 'ADJ')]
brown        -> [('B R AW1 N', 'ADJ')]
fox          -> [('F AA1 K S', 'NOUN')]
jumps        -> [('JH AH1 M P', 'VERB'), ('Z', 'PRES')]
over         -> [('OW1 V ER0', 'ADP')]
the          -> [('DH AH0', 'DET')]
lazy         -> [('L EY1 Z IY0', 'ADJ')]
dogs         -> [('D AA1 G', 'NOUN'), ('Z', 'PL')]
```

Each tuple is `(ARPAbet phones, morpheme label)`. Inflected words are
split into root + suffix when a clean phoneme decomposition is found
(e.g. *jumps* → VERB + PRES, *dogs* → NOUN + PL); otherwise the
whole form is kept as a single labelled morpheme (e.g. *fox* → NOUN).

## Interlinear Gloss

`gloss.py` formats the parse as a three-row aligned gloss in the
style of linguistics journals: orthographic words, IPA transcription
with morpheme boundaries, and morpheme labels.

```bash
python gloss.py "The cats jumped over the tallest fences."
```

```
 The  cats     jumped     over   the  tallest    fences
/ðə   ˈkæt-z   ˈdʒʌmp-d   ˈoʊvɚ  ðə   ˈtɑl-əst   ˈfɛns-ɪz/
 DET  NOUN-PL  VERB-PAST  ADP    DET  ADJ-SUPER  NOUN-PL
```

## Rhyme Analysis

`rhyme_analysis.py` identifies the common rime shared by two or more
lines of poetry. It aligns syllable nuclei from the end of each line,
tolerating small consonant differences (voicing, single insertions or
deletions) so that near-rhymes across word boundaries are detected.

The rime can span multiple words and up to three syllables. For each
line the output shows the full morphological parse, the rime mapped
back to its source morphemes, and the count of distinct morphemes
spanned.

```bash
python rhyme_analysis.py "Not the least obeisance made he" "Not a minute stopped or stayed he" "But with mien of lord or lady"
```

```
Common rime: EY1 D HH IY1  [eɪdhi]  (fuzzy match)

── Line 1: "Not the least obeisance made he" ──
  made            VERB<PAST>(meɪd)
  he              PRON(hi)
  Rime [eɪdhi] spans 2 morphemes: VERB<PAST>(made) + PRON(he)
    EY1    [eɪ ]  ← VERB<PAST> (made)
    D      [d  ]  ← VERB<PAST> (made)
    HH     [h  ]  ← PRON (he)
    IY1    [i  ]  ← PRON (he)

── Line 2: "Not a minute stopped or stayed he" ──
  stayed          VERB(steɪ) + PAST(d)
  he              PRON(hi)
  Rime [eɪdhi] spans 3 morphemes: VERB(stayed) + PAST(stayed) + PRON(he)
    EY1    [eɪ ]  ← VERB (stayed)
    D      [d  ]  ← PAST (stayed)
    HH     [h  ]  ← PRON (he)
    IY1    [i  ]  ← PRON (he)

── Line 3: "But with mien of lord or lady" ──
  lord            PROPN(lɑɹd)
  or              CCONJ(ɑɹ)
  lady            NOUN(leɪdi)
  Rime [eɪdi] spans 1 morpheme: NOUN(lady)
    EY1    [eɪ ]  ← NOUN (lady)
    D      [d  ]  ← NOUN (lady)
    IY0    [i  ]  ← NOUN (lady)
```

Here "stayed he" and "made he" are detected as a fuzzy (near) rhyme
with "lady" — the /h/ phoneme in "he" is tolerated as a single-consonant
insertion (and in this case might be omitted in speech, anyway). The two-syllable rime /eɪdi/ spans word boundaries, and
each line reports how many morphemes it cuts across.

## Project Structure

| File | Description |
|------|-------------|
| `morpho_parser.py` | Main parser — POS tagging, phoneme lookup, and morpheme decomposition |
| `gloss.py` | Interlinear gloss display (orthography / IPA / labels) |
| `rhyme_analysis.py` | Multi-syllable, cross-word rime detection with near-rhyme support |
| `morphology/inflection.py` | Inflectional suffix stripping |
| `morphology/inflection_rules.yaml` | Editable inflection rules (see below) |
| `phonology/phoneme_lookup.py` | CMU Dict lookup with heteronym disambiguation |
| `phonology/heteronyms.yaml` | POS-keyed heteronym entries |
| `requirements.txt` | Python dependencies: spaCy, PyYAML, g2p-en |

## Editing Inflection Rules

Rules live in `morphology/inflection_rules.yaml` and are loaded
automatically at import time. Each rule has four fields:

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

The parser tries each suffix in order. If stripping a suffix from the
inflected word's phonemes yields the lemma's phonemes, it splits them
into root + suffix morphemes. If a rule matches the POS/tag but no
suffix cleanly strips, the word is marked as an irregular form
(e.g. `VERB<PAST>`).

Phoneme symbols follow the
[ARPAbet](https://en.wikipedia.org/wiki/ARPABET) notation used by the
CMU dictionary.

The CMU dictionary file is downloaded from
[Alexir/CMUdict](https://github.com/Alexir/CMUdict) on first run and
cached locally as `.cmudict-0.7b`.

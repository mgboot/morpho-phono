"""Phoneme lookup via CMU Pronouncing Dictionary with g2p_en fallback."""

import logging
import urllib.request
from pathlib import Path

from g2p_en import G2p

logger = logging.getLogger(__name__)

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

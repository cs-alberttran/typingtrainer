"""
Word provider — loads and randomises word sequences for a session.

Separating word-loading from the engine keeps the engine pure:
it takes a plain list[str] and never cares where words came from.
"""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Optional

from config import WORDS_FILE, WORDS_PER_SESSION

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Built-in fallback word list (used if words.txt is missing)
# ---------------------------------------------------------------------------
_FALLBACK_WORDS: list[str] = [
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "it",
    "for", "not", "on", "with", "he", "as", "you", "do", "at", "this",
    "but", "his", "by", "from", "they", "we", "say", "her", "she", "or",
    "an", "will", "my", "one", "all", "would", "there", "their", "what",
    "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
    "when", "make", "can", "like", "time", "no", "just", "him", "know",
    "take", "people", "into", "year", "your", "good", "some", "could",
    "them", "see", "other", "than", "then", "now", "look", "only", "come",
    "its", "over", "think", "also", "back", "after", "use", "two", "how",
    "our", "work", "first", "well", "way", "even", "new", "want", "any",
]


class WordProvider:
    """
    Loads a word list from disk and produces shuffled word sequences.

    :param words_file: Path to a plain-text word list (one or more words
                       per line, whitespace-separated).  Falls back to the
                       built-in list if the file is absent or unreadable.
    """

    def __init__(self, words_file: Optional[Path] = None) -> None:
        self._source_file = words_file or WORDS_FILE
        self._word_pool: list[str] = self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, count: int = WORDS_PER_SESSION, seed: Optional[int] = None) -> list[str]:
        """
        Return a freshly-shuffled list of `count` words.

        Words are sampled *with* replacement when count > pool size so
        the test never stalls — the same word can appear more than once
        in a long session.

        :param count: Number of words to generate.
        :param seed: Optional RNG seed for reproducible tests.
        :returns: List of lowercase words.
        """
        rng = random.Random(seed)
        pool = self._word_pool or _FALLBACK_WORDS
        if count <= len(pool):
            return rng.sample(pool, count)
        # Sample with replacement
        return [rng.choice(pool) for _ in range(count)]

    @property
    def pool_size(self) -> int:
        """Number of unique words available."""
        return len(self._word_pool)

    def reload(self) -> None:
        """Re-read the word file from disk."""
        self._word_pool = self._load()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load(self) -> list[str]:
        try:
            text = self._source_file.read_text(encoding="utf-8")
            words = [w.strip().lower() for w in text.split() if w.strip().isalpha()]
            if not words:
                raise ValueError("Word file is empty or contains no alphabetic words.")
            logger.info("Loaded %d words from %s", len(words), self._source_file)
            return words
        except FileNotFoundError:
            logger.warning(
                "Word file not found: %s — using built-in fallback list.",
                self._source_file,
            )
            return list(_FALLBACK_WORDS)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load word file (%s) — using fallback. Error: %s", self._source_file, exc)
            return list(_FALLBACK_WORDS)

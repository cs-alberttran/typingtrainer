"""
Adaptive training engine — Phase 1 STUB.

This module defines the interface that the adaptive engine will implement
in Phase 2. Stubs are intentionally minimal but architecturally correct
so that callers can depend on this API today.

Phase 2 will replace the stub bodies with:
  - Weighted word selection based on per-key error rates
  - Spaced-repetition scheduling
  - ML-based difficulty prediction
"""

from __future__ import annotations

import logging
import random
from typing import Optional

from domain.analytics import KeyAnalytics

logger = logging.getLogger(__name__)


class AdaptiveEngine:
    """
    Generates adaptive word / lesson sequences tailored to the user's
    current weakness profile derived from KeyAnalytics.

    Phase 1 — returns random words.  API is stable.
    """

    def __init__(self, analytics: KeyAnalytics, base_word_pool: list[str]) -> None:
        self._analytics = analytics
        self._base_pool = base_word_pool

    # ------------------------------------------------------------------
    # Lesson generation (STUB)
    # ------------------------------------------------------------------

    def generate_lesson(
        self,
        count: int = 50,
        seed: Optional[int] = None,
    ) -> list[str]:
        """
        Generate a targeted word list that reinforces weak keys.

        Phase 1 returns a random sample.

        :param count: Number of words to produce.
        :param seed: Optional RNG seed.
        :returns: Ordered list of words for the session.
        """
        # TODO (Phase 2): filter words containing weak_keys, weight by
        # error rate, apply spaced-repetition spacing.
        logger.debug("AdaptiveEngine.generate_lesson() — stub returning random sample.")
        rng = random.Random(seed)
        pool = self._base_pool or ["the", "be", "to", "of", "and"]
        return [rng.choice(pool) for _ in range(count)]

    def weak_key_report(self) -> dict[str, float]:
        """
        Return a {key: error_rate} mapping of the user's weakest keys.

        Phase 1 — delegates to KeyAnalytics.heatmap_data().
        """
        # TODO (Phase 2): apply decay, confidence intervals, and recency weighting.
        return self._analytics.heatmap_data()

    def should_trigger_adaptive_mode(self) -> bool:
        """
        Returns True when the adaptive engine has enough data to make
        meaningful recommendations.

        Phase 1 — always returns False (feature disabled).
        """
        # TODO (Phase 2): activate when user has > N keystrokes per key.
        return False

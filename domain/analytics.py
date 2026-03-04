"""
Per-key analytics aggregator.

Phase 1 — STUB / SCAFFOLD.

Architecture note: The interface is intentionally stable so the UI heatmap
widget and the adaptive engine can depend on it today; the implementation
will be filled in during Phase 2 when per-key ML training is introduced.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from domain.models import KeyOutcome, KeystrokeEvent, KeyStats


class KeyAnalytics:
    """
    Aggregates keystroke events into per-key performance statistics.

    Usage::

        analytics = KeyAnalytics()
        analytics.ingest(event_list)
        stats = analytics.get_stats("a")
        weak_keys = analytics.weak_keys(threshold=0.85)
    """

    def __init__(self) -> None:
        self._stats: dict[str, KeyStats] = defaultdict(
            lambda: KeyStats(key="")  # key field patched on first access
        )

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest(self, events: list[KeystrokeEvent]) -> None:
        """
        Process a list of keystroke events from a completed session.

        :param events: Ordered list of KeystrokeEvent records.
        """
        for i, event in enumerate(events):
            if event.outcome == KeyOutcome.IGNORED:
                continue
            key = event.expected or event.char
            if not key or key == " ":
                continue
            stats = self._get_or_create(key)
            # Rough inter-key interval from adjacent events
            prev_ms = events[i - 1].elapsed_ms if i > 0 else event.elapsed_ms
            delta_ms = max(0, event.elapsed_ms - prev_ms)
            stats.record(event.outcome, response_time_ms=delta_ms)

    def ingest_single(self, event: KeystrokeEvent) -> None:
        """Ingest a single event (for live session tracking)."""
        self.ingest([event])

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_stats(self, key: str) -> Optional[KeyStats]:
        """Return stats for a specific key, or None if never observed."""
        return self._stats.get(key)

    def all_stats(self) -> dict[str, KeyStats]:
        """Return a snapshot of all per-key stats."""
        return dict(self._stats)

    def weak_keys(self, threshold: float = 0.85) -> list[str]:
        """
        Return keys whose accuracy is below `threshold`.

        These are the candidates for adaptive lesson reinforcement.

        :param threshold: Accuracy cutoff in [0.0, 1.0].  Default 0.85.
        """
        # STUB: returns raw accuracy-filtered keys.
        # Phase 2 will weight by frequency and recency.
        return [
            key
            for key, stats in self._stats.items()
            if stats.total_presses >= 3 and stats.accuracy < threshold
        ]

    def heatmap_data(self) -> dict[str, float]:
        """
        Return a {key: error_rate} mapping suitable for rendering a heatmap.

        Error rate is in [0.0, 1.0] where 1.0 = always wrong.

        STUB: returns computed values with no smoothing or decay.
        """
        result: dict[str, float] = {}
        for key, stats in self._stats.items():
            if stats.total_presses > 0:
                result[key] = 1.0 - stats.accuracy
        return result

    def reset(self) -> None:
        """Clear all accumulated statistics."""
        self._stats.clear()

    # ------------------------------------------------------------------
    # Serialisation helpers (for persistence layer)
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise all stats to a plain dict structure."""
        return {
            key: {
                "total_presses": s.total_presses,
                "correct_presses": s.correct_presses,
                "error_count": s.error_count,
                "total_response_time_ms": s.total_response_time_ms,
            }
            for key, s in self._stats.items()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KeyAnalytics":
        """Restore from a persisted dict."""
        instance = cls()
        for key, values in data.items():
            stats = KeyStats(key=key, **values)
            instance._stats[key] = stats
        return instance

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_or_create(self, key: str) -> KeyStats:
        if key not in self._stats:
            self._stats[key] = KeyStats(key=key)
        return self._stats[key]

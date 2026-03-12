"""
Session manager — application-layer orchestration.

Bridges the domain (TypingEngine) with the infrastructure (persistence)
and exposes a clean API for the UI layer.

The session manager:
  - Creates and configures a TypingEngine for a given game mode
  - Owns the word provider
  - Routes finish callbacks to the persistence layer
  - Holds the current SessionResult after completion
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from application.word_provider import WordProvider
from config import DEFAULT_DURATION, WORDS_PER_SESSION
from domain.analytics import KeyAnalytics
from domain.models import KeyOutcome, SessionResult, TestState
from domain.typing_engine import TypingEngine

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages the lifecycle of a single typing session.

    Typical call sequence::

        manager = SessionManager(on_finish=my_callback)
        manager.new_session(duration=30)
        # ... UI feeds keystrokes:
        manager.process_key("a")
        # When done:
        result = manager.result

    :param on_finish: Called (with the SessionResult) when the session ends.
    :param word_provider: Optional override; defaults to WordProvider().
    :param persistence: Optional callable(SessionResult) for saving results.
    """

    def __init__(
        self,
        on_finish: Optional[Callable[[SessionResult], None]] = None,
        word_provider: Optional[WordProvider] = None,
        persistence: Optional[Callable[[SessionResult], None]] = None,
    ) -> None:
        self._on_finish = on_finish
        self._word_provider = word_provider or WordProvider()
        self._persistence = persistence
        self._engine: Optional[TypingEngine] = None
        self._analytics: KeyAnalytics = KeyAnalytics()
        self._result: Optional[SessionResult] = None
        self._game_mode: str = "typing_test" 

    # ------------------------------------------------------------------
    # Session creation
    # ------------------------------------------------------------------

    def new_session(
        self,
        duration: int = DEFAULT_DURATION,
        game_mode: str = "typing_test",
        seed: Optional[int] = None,
        words: Optional[list] = None,
    ) -> TypingEngine:
        """
        Create and return a fresh TypingEngine, ready to accept keystrokes.

        :param duration: Test length in seconds.
        :param game_mode: Identifier for the current game mode.
        :param seed: Optional RNG seed for reproducible word lists.
        :param words: Optional explicit word list; bypasses the word provider.
        :returns: The configured TypingEngine (also stored internally).
        """
        if words is None:
            words = self._word_provider.generate(count=WORDS_PER_SESSION, seed=seed)
        self._engine = TypingEngine(words=words, duration_seconds=duration)
        self._engine.register_finish_callback(self._handle_finish)
        self._result = None
        self._game_mode = game_mode
        logger.info("New %s session created (%ds, %d words).", game_mode, duration, len(words))
        return self._engine

    # ------------------------------------------------------------------
    # Keystroke routing
    # ------------------------------------------------------------------

    def process_key(self, char: str) -> KeyOutcome:
        """
        Forward a keystroke to the active engine.

        Safe to call even when no engine is active (returns IGNORED).
        """
        if self._engine is None or self._engine.state == TestState.FINISHED:
            return KeyOutcome.IGNORED
        outcome = self._engine.process_key(char)
        return outcome

    # ------------------------------------------------------------------
    # Forced termination (e.g. ESC)
    # ------------------------------------------------------------------

    def abort_session(self) -> None:
        """Immediately end the current session without saving results."""
        if self._engine and self._engine.state == TestState.RUNNING:
            self._engine.finish()

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _handle_finish(self) -> None:
        """Called by the engine when the timer expires."""
        if self._engine is None:
            return
        logger.info("Session finished: game_mode=%s", self._game_mode)
        result = self._engine.build_result()
        result.game_mode = self._game_mode
        self._result = result

        # Ingest events into analytics
        try:
            self._analytics.ingest(self._engine.events)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Analytics ingest failed: %s", exc)

        # Persist
        if self._persistence:
            try:
                self._persistence(result)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to persist result: %s", exc)

        # Notify UI
        if self._on_finish:
            self._on_finish(result)

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def engine(self) -> Optional[TypingEngine]:
        """The active TypingEngine, or None if no session is running."""
        return self._engine

    @property
    def result(self) -> Optional[SessionResult]:
        """The result of the most recently completed session."""
        return self._result

    @property
    def analytics(self) -> KeyAnalytics:
        """Accumulated per-key analytics across all sessions."""
        return self._analytics

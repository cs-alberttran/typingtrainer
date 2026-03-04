"""
Core typing engine — domain logic only, no UI dependencies.

Responsibilities:
- Track per-word state across a sequence of words
- Accumulate correct / incorrect character counts
- Compute WPM and accuracy on demand
- Process keystrokes (characters, backspace)

This class is the single source of truth for what the user has typed.
"""

from __future__ import annotations

import time
from typing import Callable, Optional

from config import CHARS_PER_WORD
from domain.models import (
    KeyOutcome,
    KeystrokeEvent,
    SessionResult,
    TestState,
    WordState,
)


class TypingEngine:
    """
    Processes keystrokes against a pre-loaded word sequence and tracks
    all scoring state for one typing session.

    Design note: The engine is deliberately stateful but self-contained.
    The UI (or any caller) feeds raw characters in; the engine produces
    read-only state that the UI can query at any time to refresh its display.
    """

    def __init__(self, words: list[str], duration_seconds: int) -> None:
        if not words:
            raise ValueError("Word list must not be empty.")
        if duration_seconds <= 0:
            raise ValueError("Duration must be a positive integer.")

        self._words: list[str] = words
        self._duration: int = duration_seconds
        self._word_states: list[WordState] = [WordState(target=w) for w in words]
        self._current_index: int = 0

        self._state: TestState = TestState.IDLE
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None

        # Raw event log — used for future per-key analytics
        self._events: list[KeystrokeEvent] = []

        # Running totals (updated on commit, not on every keystroke,
        # so backspace doesn't double-count)
        self._committed_correct: int = 0
        self._committed_incorrect: int = 0
        self._words_completed: int = 0

        # Callback invoked when the timer expires
        self._on_finish: Optional[Callable[[], None]] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin the session.  Idempotent if already running."""
        if self._state == TestState.RUNNING:
            return
        self._state = TestState.RUNNING
        self._start_time = time.monotonic()

    def finish(self) -> None:
        """Forcibly end the session (e.g. ESC key or timer fired externally)."""
        if self._state == TestState.FINISHED:
            return
        self._state = TestState.FINISHED
        self._end_time = time.monotonic()
        if self._on_finish:
            self._on_finish()

    def register_finish_callback(self, callback: Callable[[], None]) -> None:
        """Register a zero-argument callable invoked when the test ends."""
        self._on_finish = callback

    # ------------------------------------------------------------------
    # Keystroke processing
    # ------------------------------------------------------------------

    def process_key(self, char: str) -> KeyOutcome:
        """
        Process a single character from the user.

        :param char: A single unicode character, 'BackSpace', or any
                     Tkinter keysym string.
        :returns: The outcome of this keystroke.
        """
        # Only a FINISHED session is fully locked.
        if self._state == TestState.FINISHED:
            return KeyOutcome.IGNORED

        # Auto-start on the first real printable character.
        # Space and backspace before any typing are silently ignored so we
        # do not start the timer on an accidental keypress.
        if self._state == TestState.IDLE:
            is_printable = (
                len(char) == 1
                and char.isprintable()
                and char != " "
            )
            if is_printable:
                self.start()
            else:
                return KeyOutcome.IGNORED

        # Check expiry every keystroke (lightweight)
        if self._is_expired():
            self.finish()
            return KeyOutcome.IGNORED

        # --- Backspace ---
        if char in ("BackSpace", "\x08"):
            return self._handle_backspace()

        # --- Ctrl+Backspace (clear whole current word) ---
        if char == "CtrlBackSpace":
            return self._handle_clear_word()

        # --- Word separator (space) ---
        if char == " ":
            return self._handle_space()

        # --- Printable character ---
        if len(char) == 1 and char.isprintable():
            return self._handle_character(char)

        # Non-character key (Shift, Ctrl, arrow keys, etc.)
        return KeyOutcome.IGNORED

    def _handle_character(self, char: str) -> KeyOutcome:
        word_state = self._current_word_state()
        target = word_state.target

        word_state.typed += char
        typed_pos = len(word_state.typed) - 1
        if typed_pos < len(target):
            expected = target[typed_pos]
            outcome = KeyOutcome.CORRECT if char == expected else KeyOutcome.INCORRECT
        else:
            # Overflow — extra character beyond the word end; always incorrect
            expected = ""
            outcome = KeyOutcome.INCORRECT

        self._log_event(char, expected, outcome)
        return outcome

    def _handle_backspace(self) -> KeyOutcome:
        word_state = self._current_word_state()
        if word_state.typed:
            word_state.typed = word_state.typed[:-1]
        self._log_event("", "", KeyOutcome.BACKSPACE)
        return KeyOutcome.BACKSPACE

    def _handle_clear_word(self) -> KeyOutcome:
        """Ctrl+Backspace — erase everything typed for the current word."""
        word_state = self._current_word_state()
        word_state.typed = ""
        self._log_event("", "", KeyOutcome.BACKSPACE)
        return KeyOutcome.BACKSPACE

    def _handle_space(self) -> KeyOutcome:
        word_state = self._current_word_state()

        if not word_state.typed:
            # Do not advance on empty input
            return KeyOutcome.IGNORED

        # Tally the committed word
        correct, incorrect = self._score_word(word_state)
        self._committed_correct += correct
        self._committed_incorrect += incorrect

        if word_state.is_complete and not word_state.has_error:
            self._words_completed += 1

        # Advance to next word
        if self._current_index < len(self._word_states) - 1:
            self._current_index += 1
        # (If the word list is exhausted the session effectively stalls;
        #  the session layer should supply enough words to prevent this.)

        self._log_event(" ", " ", KeyOutcome.CORRECT)
        return KeyOutcome.CORRECT

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_word(ws: WordState) -> tuple[int, int]:
        """Return (correct_chars, incorrect_chars) for a committed word."""
        correct = 0
        incorrect = 0
        for i, ch in enumerate(ws.typed):
            if i < len(ws.target) and ch == ws.target[i]:
                correct += 1
            else:
                incorrect += 1
        return correct, incorrect

    # ------------------------------------------------------------------
    # Read-only state queries (called by UI on every refresh)
    # ------------------------------------------------------------------

    @property
    def state(self) -> TestState:
        return self._state

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def word_states(self) -> list[WordState]:
        """Read-only view of all word states."""
        return self._word_states

    @property
    def current_word_state(self) -> WordState:
        return self._current_word_state()

    def _current_word_state(self) -> WordState:
        return self._word_states[self._current_index]

    @property
    def elapsed_seconds(self) -> float:
        """Seconds since session start, capped at duration."""
        if self._start_time is None:
            return 0.0
        end = self._end_time or time.monotonic()
        return min(end - self._start_time, float(self._duration))

    @property
    def remaining_seconds(self) -> float:
        """Seconds remaining in the test."""
        return max(0.0, self._duration - self.elapsed_seconds)

    @property
    def duration(self) -> int:
        return self._duration

    def _is_expired(self) -> bool:
        return self._start_time is not None and self.remaining_seconds <= 0.0

    # ------------------------------------------------------------------
    # Live WPM / accuracy
    # ------------------------------------------------------------------

    def live_wpm(self) -> float:
        """
        Net WPM based on correctly typed characters committed so far.

        Formula: (correct_chars / CHARS_PER_WORD) / elapsed_minutes
        """
        elapsed = self.elapsed_seconds
        if elapsed < 0.5:
            return 0.0
        minutes = elapsed / 60.0
        return round(self._committed_correct / CHARS_PER_WORD / minutes, 1)

    def live_raw_wpm(self) -> float:
        """Raw WPM including both correct and incorrect characters."""
        elapsed = self.elapsed_seconds
        if elapsed < 0.5:
            return 0.0
        minutes = elapsed / 60.0
        total = self._committed_correct + self._committed_incorrect
        return round(total / CHARS_PER_WORD / minutes, 1)

    def live_accuracy(self) -> float:
        """Current accuracy in [0.0, 1.0]."""
        total = self._committed_correct + self._committed_incorrect
        if total == 0:
            return 1.0
        return self._committed_correct / total

    # ------------------------------------------------------------------
    # Final result
    # ------------------------------------------------------------------

    def build_result(self) -> SessionResult:
        """
        Construct the immutable SessionResult for this session.
        May be called once the session is FINISHED.
        """
        elapsed = self.elapsed_seconds
        minutes = elapsed / 60.0 if elapsed > 0 else 1.0

        wpm = round(self._committed_correct / CHARS_PER_WORD / minutes, 2)
        raw_wpm = round(
            (self._committed_correct + self._committed_incorrect)
            / CHARS_PER_WORD
            / minutes,
            2,
        )

        return SessionResult(
            duration_seconds=self._duration,
            elapsed_seconds=elapsed,
            correct_chars=self._committed_correct,
            incorrect_chars=self._committed_incorrect,
            total_keystrokes=len(self._events),
            words_completed=self._words_completed,
            wpm=wpm,
            raw_wpm=raw_wpm,
            accuracy=self.live_accuracy(),
        )

    # ------------------------------------------------------------------
    # Event log
    # ------------------------------------------------------------------

    def _log_event(
        self,
        char: str,
        expected: str,
        outcome: KeyOutcome,
    ) -> None:
        elapsed_ms = int(self.elapsed_seconds * 1000)
        self._events.append(
            KeystrokeEvent(
                char=char,
                expected=expected,
                outcome=outcome,
                elapsed_ms=elapsed_ms,
            )
        )

    @property
    def events(self) -> list[KeystrokeEvent]:
        """Full keystroke event log (copy-safe read)."""
        return list(self._events)

"""
Core domain data models.

Pure data-carrying classes — no I/O, no Tkinter, no side-effects.
All other layers depend on these; they depend on nothing else.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestState(Enum):
    """Lifecycle states of a typing session."""
    IDLE = auto()      # Not yet started
    RUNNING = auto()   # Test is active
    FINISHED = auto()  # Time expired or user ended session


class KeyOutcome(Enum):
    """Per-keystroke correctness classification."""
    CORRECT = auto()
    INCORRECT = auto()
    BACKSPACE = auto()
    IGNORED = auto()   # Non-character keys (Shift, Ctrl, etc.)


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KeystrokeEvent:
    """
    Immutable record of a single keystroke during a session.

    :param char: The character pressed (empty string for special keys).
    :param expected: The character the user was supposed to press.
    :param outcome: Classification of this keystroke.
    :param timestamp: Wall-clock time (seconds) when the key was pressed.
    :param elapsed_ms: Milliseconds since session start.
    """
    char: str
    expected: str
    outcome: KeyOutcome
    timestamp: float = field(default_factory=time.time)
    elapsed_ms: int = 0


# ---------------------------------------------------------------------------
# Per-key analytics (used by adaptive engine)
# ---------------------------------------------------------------------------

@dataclass
class KeyStats:
    """
    Aggregated performance data for a single key.

    Designed to support future adaptive training decisions.
    """
    key: str
    total_presses: int = 0
    correct_presses: int = 0
    error_count: int = 0
    total_response_time_ms: int = 0   # sum for computing average

    @property
    def accuracy(self) -> float:
        """Returns accuracy in [0.0, 1.0]; returns 1.0 when never pressed."""
        if self.total_presses == 0:
            return 1.0
        return self.correct_presses / self.total_presses

    @property
    def avg_response_time_ms(self) -> float:
        """Average response time in milliseconds."""
        if self.correct_presses == 0:
            return 0.0
        return self.total_response_time_ms / self.correct_presses

    def record(self, outcome: KeyOutcome, response_time_ms: int = 0) -> None:
        """Update stats with a new keystroke observation."""
        if outcome == KeyOutcome.IGNORED:
            return
        if outcome != KeyOutcome.BACKSPACE:
            self.total_presses += 1
        if outcome == KeyOutcome.CORRECT:
            self.correct_presses += 1
            self.total_response_time_ms += response_time_ms
        elif outcome == KeyOutcome.INCORRECT:
            self.error_count += 1


# ---------------------------------------------------------------------------
# Session result
# ---------------------------------------------------------------------------

@dataclass
class SessionResult:
    """
    Immutable summary produced at the end of a typing session.

    This is the object persisted to disk and shown on the results screen.
    """
    duration_seconds: int
    elapsed_seconds: float
    correct_chars: int
    incorrect_chars: int
    total_keystrokes: int
    words_completed: int
    wpm: float
    raw_wpm: float
    accuracy: float          # [0.0, 1.0]
    timestamp: float = field(default_factory=time.time)
    game_mode: str = "monkeytype"

    @property
    def accuracy_pct(self) -> float:
        """Accuracy as a percentage, rounded to one decimal place."""
        return round(self.accuracy * 100, 1)

    def to_dict(self) -> dict:
        """Serialize to a plain dict for JSON persistence."""
        return {
            "duration_seconds": self.duration_seconds,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "correct_chars": self.correct_chars,
            "incorrect_chars": self.incorrect_chars,
            "total_keystrokes": self.total_keystrokes,
            "words_completed": self.words_completed,
            "wpm": round(self.wpm, 2),
            "raw_wpm": round(self.raw_wpm, 2),
            "accuracy": round(self.accuracy, 4),
            "timestamp": self.timestamp,
            "game_mode": self.game_mode,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionResult":
        """Deserialize from a persisted dict."""
        return cls(**data)


# ---------------------------------------------------------------------------
# Word-level state (used by the typing engine)
# ---------------------------------------------------------------------------

@dataclass
class WordState:
    """
    Tracks the user's typing progress on a single word.

    :param target: The word the user must type.
    :param typed: Characters typed so far for this word.
    """
    target: str
    typed: str = ""

    @property
    def is_complete(self) -> bool:
        """True once the user has typed exactly the correct word."""
        return self.typed == self.target

    @property
    def has_error(self) -> bool:
        """True if any typed character differs from the target at that position."""
        for i, ch in enumerate(self.typed):
            if i >= len(self.target) or ch != self.target[i]:
                return True
        return False

    @property
    def correct_prefix_length(self) -> int:
        """Number of characters at the start of `typed` that match `target`."""
        count = 0
        for typed_ch, target_ch in zip(self.typed, self.target):
            if typed_ch == target_ch:
                count += 1
            else:
                break
        return count

    def char_outcomes(self) -> list[Optional[KeyOutcome]]:
        """
        Returns per-character outcome for every position in `target`.
        None means the position has not been reached yet.
        """
        results: list[Optional[KeyOutcome]] = []
        for i, target_ch in enumerate(self.target):
            if i >= len(self.typed):
                results.append(None)
            elif self.typed[i] == target_ch:
                results.append(KeyOutcome.CORRECT)
            else:
                results.append(KeyOutcome.INCORRECT)
        return results

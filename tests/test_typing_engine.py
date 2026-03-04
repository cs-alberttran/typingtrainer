"""
Unit tests for domain/typing_engine.py

Tests cover:
  - WPM and accuracy calculation (industry-standard formula)
  - Correct and incorrect character handling
  - Backspace semantics
  - Space (word commit) behaviour
  - State machine transitions
  - Edge cases: empty typed, very fast typing, non-char keys
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# Make the project root importable regardless of test runner cwd
sys.path.insert(0, str(Path(__file__).parent.parent))

from domain.models import KeyOutcome, TestState
from domain.typing_engine import TypingEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_engine(words: list[str] | None = None, duration: int = 30) -> TypingEngine:
    return TypingEngine(words=words or ["hello", "world", "foo"], duration_seconds=duration)


def type_word(engine: TypingEngine, word: str) -> None:
    """Type each character of word followed by a space."""
    for ch in word:
        engine.process_key(ch)
    engine.process_key(" ")


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestEngineConstruction:
    def test_raises_on_empty_words(self):
        with pytest.raises(ValueError, match="empty"):
            TypingEngine(words=[], duration_seconds=30)

    def test_raises_on_zero_duration(self):
        with pytest.raises(ValueError):
            TypingEngine(words=["hello"], duration_seconds=0)

    def test_raises_on_negative_duration(self):
        with pytest.raises(ValueError):
            TypingEngine(words=["hello"], duration_seconds=-1)

    def test_initial_state_is_idle(self):
        engine = make_engine()
        assert engine.state == TestState.IDLE

    def test_initial_index_is_zero(self):
        engine = make_engine()
        assert engine.current_index == 0


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------

class TestStateTransitions:
    def test_first_char_starts_session(self):
        engine = make_engine()
        engine.process_key("h")
        assert engine.state == TestState.RUNNING

    def test_finish_transitions_to_finished(self):
        engine = make_engine()
        engine.start()
        engine.finish()
        assert engine.state == TestState.FINISHED

    def test_ignore_keys_when_finished(self):
        engine = make_engine()
        engine.start()
        engine.finish()
        outcome = engine.process_key("a")
        assert outcome == KeyOutcome.IGNORED

    def test_ignore_keys_when_idle(self):
        # Keys before start are still processed (auto-start)
        engine = make_engine()
        outcome = engine.process_key("h")
        assert outcome != KeyOutcome.IGNORED  # auto-started


# ---------------------------------------------------------------------------
# Character input
# ---------------------------------------------------------------------------

class TestCharacterInput:
    def test_correct_character_returns_correct(self):
        engine = make_engine(["hello"])
        result = engine.process_key("h")
        assert result == KeyOutcome.CORRECT

    def test_incorrect_character_returns_incorrect(self):
        engine = make_engine(["hello"])
        result = engine.process_key("x")
        assert result == KeyOutcome.INCORRECT

    def test_typed_state_reflects_input(self):
        engine = make_engine(["hello"])
        engine.process_key("h")
        engine.process_key("e")
        assert engine.current_word_state.typed == "he"

    def test_cannot_type_past_word_end(self):
        engine = make_engine(["hi"])
        engine.process_key("h")
        engine.process_key("i")
        outcome = engine.process_key("x")  # would go past word length
        assert outcome == KeyOutcome.IGNORED
        assert engine.current_word_state.typed == "hi"

    def test_non_printable_key_is_ignored(self):
        engine = make_engine(["hello"])
        outcome = engine.process_key("Shift_L")
        assert outcome == KeyOutcome.IGNORED

    def test_space_before_typing_is_ignored(self):
        engine = make_engine(["hello"])
        outcome = engine.process_key(" ")
        # Advancing on empty typed is ignored
        assert outcome == KeyOutcome.IGNORED
        assert engine.current_index == 0


# ---------------------------------------------------------------------------
# Backspace
# ---------------------------------------------------------------------------

class TestBackspace:
    def test_backspace_removes_last_char(self):
        engine = make_engine(["hello"])
        engine.process_key("h")
        engine.process_key("e")
        engine.process_key("BackSpace")
        assert engine.current_word_state.typed == "h"

    def test_backspace_on_empty_word_is_safe(self):
        engine = make_engine(["hello"])
        # Should not raise
        engine.process_key("BackSpace")
        assert engine.current_word_state.typed == ""

    def test_backspace_returns_backspace_outcome(self):
        engine = make_engine(["hello"])
        engine.process_key("h")
        outcome = engine.process_key("BackSpace")
        assert outcome == KeyOutcome.BACKSPACE

    def test_backspace_byte_code(self):
        """Ensure \\x08 (byte 8) is also treated as backspace."""
        engine = make_engine(["hello"])
        engine.process_key("h")
        engine.process_key("\x08")
        assert engine.current_word_state.typed == ""


# ---------------------------------------------------------------------------
# Word advancement (space)
# ---------------------------------------------------------------------------

class TestWordAdvancement:
    def test_space_advances_word_index(self):
        engine = make_engine(["hello", "world"])
        type_word(engine, "hello")
        assert engine.current_index == 1

    def test_space_with_wrong_word_still_advances(self):
        engine = make_engine(["hello", "world"])
        type_word(engine, "hxllo")  # one wrong char
        assert engine.current_index == 1

    def test_correct_word_increments_words_completed(self):
        engine = make_engine(["hello", "world"])
        type_word(engine, "hello")
        result = engine.build_result()
        # build_result requires finish
        engine.finish()
        result = engine.build_result()
        assert result.words_completed == 1

    def test_incorrect_word_does_not_increment_words_completed(self):
        engine = make_engine(["hello", "world"])
        type_word(engine, "hxllo")
        engine.finish()
        result = engine.build_result()
        assert result.words_completed == 0


# ---------------------------------------------------------------------------
# Scoring (WPM / accuracy)
# ---------------------------------------------------------------------------

class TestScoring:
    def test_accuracy_100_percent_all_correct(self):
        engine = make_engine(["ab", "cd"])
        type_word(engine, "ab")
        type_word(engine, "cd")
        assert engine.live_accuracy() == pytest.approx(1.0)

    def test_accuracy_50_percent_half_wrong(self):
        engine = make_engine(["ab"])
        engine.process_key("a")  # correct
        engine.process_key("x")  # incorrect
        engine.process_key(" ")  # commit
        acc = engine.live_accuracy()
        assert acc == pytest.approx(0.5)

    def test_accuracy_100_when_nothing_typed(self):
        engine = make_engine(["hello"])
        assert engine.live_accuracy() == pytest.approx(1.0)

    def test_wpm_zero_before_half_second(self):
        engine = make_engine(["hello"])
        # Engine just started, elapsed is < 0.5s
        engine.start()
        wpm = engine.live_wpm()
        assert wpm == 0.0

    def test_wpm_calculation(self):
        """
        Type 10 correct chars, fake 1 minute elapsed → should yield 2 WPM
        (10 chars / 5 chars_per_word / 1 minute = 2.0 WPM).
        """
        # Use 120s so mocking elapsed=60s doesn't trigger expiry
        engine = make_engine(["hello", "world"], duration=120)
        engine.start()

        # Type both words with the real clock, then query WPM with
        # a patched elapsed_seconds to get a deterministic result.
        type_word(engine, "hello")   # 5 correct chars
        type_word(engine, "world")   # 5 correct chars → 10 total

        # Patch elapsed_seconds as a property returning exactly 60s.
        with patch.object(
            type(engine),
            "elapsed_seconds",
            new=property(lambda self: 60.0),
        ):
            wpm = engine.live_wpm()

        # 10 correct chars / 5 / 1.0 minute = 2.0 WPM
        assert wpm == pytest.approx(2.0, abs=0.1)

    def test_build_result_fields(self):
        engine = make_engine(["hello"])
        type_word(engine, "hello")
        engine.finish()
        result = engine.build_result()
        assert result.correct_chars == 5
        assert result.incorrect_chars == 0
        assert result.duration_seconds == 30
        assert result.game_mode == "monkeytype"

    def test_remaining_seconds_decreases(self):
        engine = make_engine(["hello"], duration=10)
        engine.start()
        time.sleep(0.05)
        assert engine.remaining_seconds < 10.0

    def test_elapsed_capped_at_duration(self):
        engine = make_engine(["hello"], duration=1)
        engine.start()
        time.sleep(1.1)
        assert engine.elapsed_seconds <= 1.0 + 0.01  # small float tolerance


# ---------------------------------------------------------------------------
# Finish callback
# ---------------------------------------------------------------------------

class TestFinishCallback:
    def test_finish_callback_invoked(self):
        called = []
        engine = make_engine()
        engine.register_finish_callback(lambda: called.append(True))
        engine.start()
        engine.finish()
        assert len(called) == 1

    def test_finish_callback_not_invoked_twice(self):
        called = []
        engine = make_engine()
        engine.register_finish_callback(lambda: called.append(True))
        engine.start()
        engine.finish()
        engine.finish()  # second call should be no-op
        assert len(called) == 1

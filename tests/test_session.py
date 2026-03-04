"""
Integration tests for application/session.py

Verifies the session manager correctly orchestrates the engine,
result construction, and callback sequence.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from application.session import SessionManager
from application.word_provider import WordProvider
from domain.models import KeyOutcome, SessionResult, TestState


def _make_manager(**kwargs) -> SessionManager:
    return SessionManager(**kwargs)


def _small_provider() -> WordProvider:
    """Return a WordProvider backed by a static small word list."""
    prov = MagicMock(spec=WordProvider)
    prov.generate.return_value = ["hello", "world", "foo", "bar", "baz"] * 40
    return prov


class TestNewSession:
    def test_returns_engine(self):
        manager = _make_manager(word_provider=_small_provider())
        engine = manager.new_session(duration=15)
        assert engine is not None

    def test_engine_starts_idle(self):
        manager = _make_manager(word_provider=_small_provider())
        engine = manager.new_session(duration=15)
        assert engine.state == TestState.IDLE

    def test_result_is_none_before_finish(self):
        manager = _make_manager(word_provider=_small_provider())
        manager.new_session(duration=15)
        assert manager.result is None


class TestProcessKey:
    def test_correct_key_returns_correct(self):
        manager = _make_manager(word_provider=_small_provider())
        manager.new_session(duration=30)
        # "hello" is first word
        outcome = manager.process_key("h")
        assert outcome == KeyOutcome.CORRECT

    def test_process_key_without_session_returns_ignored(self):
        manager = _make_manager()
        outcome = manager.process_key("a")
        assert outcome == KeyOutcome.IGNORED

    def test_abort_session_stops_engine(self):
        manager = _make_manager(word_provider=_small_provider())
        engine = manager.new_session(duration=30)
        manager.process_key("h")  # starts engine
        manager.abort_session()
        assert engine.state == TestState.FINISHED

    def test_abort_on_idle_session_is_safe(self):
        manager = _make_manager(word_provider=_small_provider())
        manager.new_session(duration=30)
        # Should not raise even though IDLE
        manager.abort_session()


class TestFinishCallback:
    def test_on_finish_called_with_result(self):
        received: list[SessionResult] = []
        manager = _make_manager(
            word_provider=_small_provider(),
            on_finish=lambda r: received.append(r),
        )
        engine = manager.new_session(duration=30)
        manager.process_key("h")  # starts engine
        engine.finish()

        assert len(received) == 1
        assert isinstance(received[0], SessionResult)

    def test_result_available_after_finish(self):
        manager = _make_manager(word_provider=_small_provider())
        engine = manager.new_session(duration=30)
        manager.process_key("h")
        engine.finish()
        assert manager.result is not None

    def test_persistence_called_on_finish(self):
        saved: list[SessionResult] = []
        manager = _make_manager(
            word_provider=_small_provider(),
            persistence=lambda r: saved.append(r),
        )
        engine = manager.new_session(duration=30)
        manager.process_key("h")
        engine.finish()
        assert len(saved) == 1

    def test_persistence_failure_does_not_crash(self):
        def bad_persistence(_result):
            raise OSError("disk full")

        manager = _make_manager(
            word_provider=_small_provider(),
            persistence=bad_persistence,
        )
        engine = manager.new_session(duration=30)
        manager.process_key("h")
        # Should NOT raise
        engine.finish()


class TestMultipleSessions:
    def test_new_session_resets_result(self):
        manager = _make_manager(word_provider=_small_provider())
        engine = manager.new_session(duration=15)
        manager.process_key("h")
        engine.finish()
        assert manager.result is not None

        # Start a new session — result should be cleared
        manager.new_session(duration=30)
        assert manager.result is None

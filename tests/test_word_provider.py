"""
Unit tests for application/word_provider.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from application.word_provider import WordProvider, _FALLBACK_WORDS


class TestWordProviderLoad:
    def test_loads_from_file(self, tmp_path):
        wf = tmp_path / "words.txt"
        wf.write_text("apple banana cherry\n", encoding="utf-8")
        provider = WordProvider(words_file=wf)
        assert provider.pool_size == 3

    def test_falls_back_on_missing_file(self, tmp_path):
        provider = WordProvider(words_file=tmp_path / "nonexistent.txt")
        assert provider.pool_size == len(_FALLBACK_WORDS)

    def test_falls_back_on_empty_file(self, tmp_path):
        wf = tmp_path / "empty.txt"
        wf.write_text("", encoding="utf-8")
        provider = WordProvider(words_file=wf)
        assert provider.pool_size == len(_FALLBACK_WORDS)

    def test_strips_non_alpha_tokens(self, tmp_path):
        wf = tmp_path / "words.txt"
        wf.write_text("hello world 123 foo-bar test", encoding="utf-8")
        provider = WordProvider(words_file=wf)
        # Only "hello", "world", "test" are purely alphabetic
        assert provider.pool_size == 3

    def test_words_are_lowercase(self, tmp_path):
        wf = tmp_path / "words.txt"
        wf.write_text("Hello WORLD Foo", encoding="utf-8")
        provider = WordProvider(words_file=wf)
        words = provider.generate(3)
        assert all(w == w.lower() for w in words)


class TestWordProviderGenerate:
    def _provider_with_words(self, n: int) -> WordProvider:
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix=".txt")
        words = [f"word{i}" for i in range(n)]
        os.write(fd, " ".join(words).encode())
        os.close(fd)
        p = WordProvider(words_file=Path(path))
        os.unlink(path)
        return p

    def test_generate_returns_correct_count(self, tmp_path):
        wf = tmp_path / "w.txt"
        wf.write_text(" ".join([f"w{i}" for i in range(50)]))
        prov = WordProvider(words_file=wf)
        result = prov.generate(count=20)
        assert len(result) == 20

    def test_generate_with_seed_is_reproducible(self, tmp_path):
        wf = tmp_path / "w.txt"
        wf.write_text(" ".join([f"w{i}" for i in range(100)]))
        prov = WordProvider(words_file=wf)
        r1 = prov.generate(count=30, seed=42)
        r2 = prov.generate(count=30, seed=42)
        assert r1 == r2

    def test_generate_different_seeds_differ(self, tmp_path):
        wf = tmp_path / "w.txt"
        wf.write_text(" ".join([f"w{i}" for i in range(100)]))
        prov = WordProvider(words_file=wf)
        r1 = prov.generate(count=30, seed=1)
        r2 = prov.generate(count=30, seed=2)
        assert r1 != r2

    def test_generate_more_than_pool_with_replacement(self, tmp_path):
        wf = tmp_path / "w.txt"
        wf.write_text("alpha beta gamma")
        prov = WordProvider(words_file=wf)
        result = prov.generate(count=10)
        assert len(result) == 10
        assert all(w in {"alpha", "beta", "gamma"} for w in result)

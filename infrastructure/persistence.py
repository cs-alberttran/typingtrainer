"""
Persistence layer — local JSON storage for session results and
per-key analytics.

Design:
  - Appends results to a JSON array file (results.json).
  - Analytics are stored as a separate JSON object (analytics.json).
  - Corrupt or missing files are handled gracefully — the app starts
    cleanly even on its first run or after data corruption.
  - No external dependencies; stdlib json + pathlib only.
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Optional

from config import DATA_DIR, RESULTS_FILE
from domain.analytics import KeyAnalytics
from domain.models import SessionResult

logger = logging.getLogger(__name__)

ANALYTICS_FILE: Path = DATA_DIR / "analytics.json"
_BACKUP_SUFFIX: str = ".bak"


class ResultsRepository:
    """
    Persists and retrieves SessionResult records as a JSON array.

    Thread-safety: single-threaded writes are assumed (Tkinter main thread).
    """

    def __init__(self, results_file: Optional[Path] = None) -> None:
        self._file = results_file or RESULTS_FILE
        self._ensure_data_dir()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save(self, result: SessionResult) -> None:
        """
        Append a result to the persistent store.

        The file is always left in a valid JSON state; on write failure
        the existing data is preserved.
        """
        records = self.load_all()
        records.append(result.to_dict())
        self._write_json(self._file, records)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def load_all(self) -> list[dict]:
        """
        Return all persisted result dicts.

        Returns an empty list if the file is absent or corrupt.
        """
        return self._read_json_list(self._file)

    def load_results(self) -> list[SessionResult]:
        """Return all results as SessionResult objects."""
        out: list[SessionResult] = []
        for record in self.load_all():
            try:
                out.append(SessionResult.from_dict(record))
            except (KeyError, TypeError) as exc:
                logger.warning("Skipping malformed result record: %s — %s", record, exc)
        return out

    def best_wpm(self) -> float:
        """Return the highest WPM ever recorded, or 0.0 if no history."""
        results = self.load_results()
        if not results:
            return 0.0
        return max(r.wpm for r in results)

    def recent_results(self, n: int = 10) -> list[SessionResult]:
        """Return the `n` most recent results, newest first."""
        results = self.load_results()
        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[:n]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_data_dir(self) -> None:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.error("Cannot create data directory %s: %s", DATA_DIR, exc)

    def _write_json(self, path: Path, data: object) -> None:
        """Write data as JSON; makes a backup of the previous file first."""
        try:
            if path.exists():
                shutil.copy2(path, path.with_suffix(_BACKUP_SUFFIX))
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp.replace(path)
        except OSError as exc:
            logger.error("Failed to write %s: %s", path, exc)

    def _read_json_list(self, path: Path) -> list:
        if not path.exists():
            return []
        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            if not isinstance(data, list):
                raise ValueError("Expected JSON array at root.")
            return data
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Corrupt results file (%s): %s — returning empty list.", path, exc)
            return []
        except OSError as exc:
            logger.error("Cannot read %s: %s", path, exc)
            return []


class AnalyticsRepository:
    """
    Persists and restores KeyAnalytics state between sessions.

    Phase 1 — scaffold only.  Fully functional but not yet surfaced in the UI.
    """

    def __init__(self, analytics_file: Optional[Path] = None) -> None:
        self._file = analytics_file or ANALYTICS_FILE
        self._ensure_data_dir()

    def save(self, analytics: KeyAnalytics) -> None:
        """Persist the full analytics state."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            data = analytics.to_dict()
            data["_saved_at"] = time.time()
            self._file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.error("Failed to save analytics: %s", exc)

    def load(self) -> KeyAnalytics:
        """
        Restore analytics from disk.

        Returns an empty KeyAnalytics instance if the file is missing or corrupt.
        """
        if not self._file.exists():
            return KeyAnalytics()
        try:
            data = json.loads(self._file.read_text(encoding="utf-8"))
            data.pop("_saved_at", None)
            return KeyAnalytics.from_dict(data)
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            logger.warning("Corrupt analytics file: %s — starting fresh.", exc)
            return KeyAnalytics()

    def _ensure_data_dir(self) -> None:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.error("Cannot create data directory: %s", exc)

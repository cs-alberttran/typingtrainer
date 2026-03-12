"""Settings manager — loads, persists and applies user preferences."""

from __future__ import annotations

import json
import threading
from typing import Any

import config as _cfg

_SETTINGS_FILE = _cfg.DATA_DIR / "settings.json"

DEFAULTS: dict[str, Any] = {
    "dark_mode": True,
    "font_family": "Tahoma",
    "word_font_size": 18,
    "mute_sound": False,
}

# Light-mode colour overrides applied to the config module
_LIGHT: dict[str, str] = {
    "BG_MAIN":      "#f0f0f0",
    "BG_PANEL":     "#e2e2e2",
    "BG_WORD_BOX":  "#ffffff",
    "BG_INPUT":     "#ffffff",
    "FG_DEFAULT":   "#1a1a1a",
    "FG_MUTED":     "#666666",
    "ACCENT":       "#0078d7",
    "ACCENT_HOVER": "#005fa3",
}


class SettingsManager:
    """Manages user preferences with JSON persistence."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = dict(DEFAULTS)
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if _SETTINGS_FILE.exists():
            try:
                raw = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
                for key, default in DEFAULTS.items():
                    if key in raw and type(raw[key]) is type(default):
                        self._data[key] = raw[key]
            except (json.JSONDecodeError, OSError):
                pass

    def save(self) -> None:
        _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SETTINGS_FILE.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get(self, key: str) -> Any:
        return self._data.get(key, DEFAULTS.get(key))

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    # ------------------------------------------------------------------
    # Apply to config module (call BEFORE importing any view modules)
    # ------------------------------------------------------------------

    def apply_to_config(self) -> None:
        """
        Overwrite ``config`` module constants with current settings.

        Must be called *before* any view module is imported so that their
        ``from config import …`` statements see the updated values.
        """
        if not self.get("dark_mode"):
            for attr, value in _LIGHT.items():
                setattr(_cfg, attr, value)

        _cfg.FONT_UI = self.get("font_family")
        _cfg.FONT_WORD_SIZE = self.get("word_font_size")

    # ------------------------------------------------------------------
    # Sound
    # ------------------------------------------------------------------

    def play_click(self) -> None:
        """Play a short click sound asynchronously. No-op when muted."""
        if self.get("mute_sound"):
            return
        threading.Thread(target=self._click, daemon=True).start()

    @staticmethod
    def _click() -> None:
        try:
            import winsound  # Windows standard library — no install required
            wav = _cfg.BASE_DIR / "assets" / "click.wav"
            if wav.exists():
                winsound.PlaySound(str(wav), winsound.SND_FILENAME)
            else:
                winsound.Beep(1200, 20)
        except Exception:  # noqa: BLE001
            pass

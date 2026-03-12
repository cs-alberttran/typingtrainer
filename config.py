"""
Application-wide configuration constants.

All tuneable values live here so no magic numbers are scattered
throughout the codebase.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).parent
WORDS_FILE: Path = BASE_DIR / "words.txt"
GRAMS_FILE: Path = BASE_DIR / "grams_list.txt"
LEFTHAND_FILE: Path = BASE_DIR / "lefthand.txt"
RIGHTHAND_FILE: Path = BASE_DIR / "righthand.txt"
DATA_DIR: Path = BASE_DIR / "data"
RESULTS_FILE: Path = DATA_DIR / "results.json"

# ---------------------------------------------------------------------------
# Test durations (seconds) presented to the user
# ---------------------------------------------------------------------------
TEST_DURATIONS: list[int] = [15, 30, 60, 120]
DEFAULT_DURATION: int = 30

# ---------------------------------------------------------------------------
# WPM / scoring
# ---------------------------------------------------------------------------
# Industry standard: one "word" = 5 characters (including spaces)
CHARS_PER_WORD: int = 5

# ---------------------------------------------------------------------------
# Word generation
# ---------------------------------------------------------------------------
# How many words to pre-generate per session so the display never runs dry
WORDS_PER_SESSION: int = 200

# ---------------------------------------------------------------------------
# UI geometry
# ---------------------------------------------------------------------------
WINDOW_TITLE: str = "Typing Trainer"
WINDOW_WIDTH: int = 900
WINDOW_HEIGHT: int = 640
WINDOW_MIN_WIDTH: int = 700
WINDOW_MIN_HEIGHT: int = 540

# ---------------------------------------------------------------------------
# UI colours  (dark Windows-classic theme)
# ---------------------------------------------------------------------------
BG_MAIN: str = "#1a1a1a"       # near-black window background
BG_PANEL: str = "#2d2d2d"      # dialog / panel surfaces
BG_KEY: str = "#d0d0d0"        # keyboard key face (stays light)
BG_INPUT: str = "#ffffff"       # typed-text echo bar (stays light)
BG_WORD_BOX: str = "#f8f8f8"   # word display area (stays light)

FG_DEFAULT: str = "#d8d8d8"    # primary text on dark bg
FG_MUTED: str = "#888888"      # secondary / hint text
FG_CORRECT: str = "#2a7a2a"    # green  (shown on light word box)
FG_ERROR: str = "#cc2222"      # red    (shown on light word box)
FG_CURRENT: str = "#000000"    # active word underline (on light word box)
FG_PENDING: str = "#aaaaaa"    # not-yet-typed (on light word box)

ACCENT: str = "#4a90d9"        # blue — buttons / cursor / active key
ACCENT_HOVER: str = "#357abd"

# ---------------------------------------------------------------------------
# Classic border width (XP-style raised/groove elements)
# ---------------------------------------------------------------------------
BD: int = 2

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
FONT_MONO: str = "Courier New"
FONT_UI: str = "Tahoma"

FONT_WORD_SIZE: int = 18
FONT_INPUT_SIZE: int = 14
FONT_STAT_SIZE: int = 13
FONT_TITLE_SIZE: int = 22
FONT_BUTTON_SIZE: int = 11

# ---------------------------------------------------------------------------
# Timer poll interval (ms)
# ---------------------------------------------------------------------------
TIMER_POLL_MS: int = 100

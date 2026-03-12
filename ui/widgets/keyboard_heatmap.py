"""
Keyboard widget — full QWERTY layout with live key highlighting and heatmap support.

Two modes (can be active simultaneously):
  - Live mode  : highlight the *next expected* key via set_active_key(char).
  - Heatmap mode: colour keys by error rate via update_data({key: rate}).
"""

from __future__ import annotations

import tkinter as tk
from typing import Optional

from config import ACCENT, BD, BG_KEY, BG_PANEL, FG_DEFAULT, FG_MUTED, FONT_UI


class KeyboardHeatmap(tk.Frame):
    """
    Full QWERTY keyboard visualisation.

    :param master: Parent widget.
    :param heatmap_data: Optional initial ``{key: error_rate}`` dict.
    """

    # Each entry: (display_text, key_id_or_None, label_width)
    # key_id=None  →  decorative key, not tracked in heatmap / active highlight
    _ROWS: list[list[tuple]] = [
        # ── number row ──────────────────────────────────────────────
        [("1","1",3),("2","2",3),("3","3",3),("4","4",3),("5","5",3),
         ("6","6",3),("7","7",3),("8","8",3),("9","9",3),("0","0",3),
         ("⌫", None, 4)],
        # ── QWERTY ──────────────────────────────────────────────────
        [("Q","q",3),("W","w",3),("E","e",3),("R","r",3),("T","t",3),
         ("Y","y",3),("U","u",3),("I","i",3),("O","o",3),("P","p",3)],
        # ── ASDF ────────────────────────────────────────────────────
        [("CAPS",None,5),("A","a",3),("S","s",3),("D","d",3),("F_","f_",3),
         ("G","g",3),("H","h",3),("_J","_j",3),("K","k",3),("L","l",3),
         (";",";",3),("'","'",3),("ENTER",None,5)],
        # ── ZXCV ────────────────────────────────────────────────────
        [("SHIFT",None,6),("Z","z",3),("X","x",3),("C","c",3),("V","v",3),
         ("B","b",3),("N","n",3),("M","m",3),(",",",",3),(".",  ".",3),
         ("/","/",3),("SHIFT",None,5)],
    ]
    # Numpad layout: (display, key_id, width) — key_id=None means decorative
    # + spans rows 1-2 and Enter spans rows 3-4 (handled via grid rowspan in _build_numpad)
    _NUMPAD_ROWS: list[list[tuple]] = [
        [("Tab", None, 5), ("/", "/", 4), ("*", "*", 4), ("-", "-", 4)],
        [("7", "7", 4), ("8", "8", 4), ("9", "9", 4)],
        [("4", "4", 4), ("5", "5", 4), ("6", "6", 4)],
        [("1", "1", 4), ("2", "2", 4), ("3", "3", 4)],
        [("0", "0", 9), (".", ".", 4)],
    ]
    def __init__(
        self,
        master: tk.Widget,
        heatmap_data: Optional[dict[str, float]] = None,
        key_size: int = 13,
        mode: str = "keyboard",
        **kwargs,
    ) -> None:
        super().__init__(master, bg=BG_KEY, **kwargs)
        self._heatmap_data: dict[str, float] = heatmap_data or {}
        self._key_labels: dict[str, tk.Label] = {}
        self._active_key: Optional[str] = None
        self._key_size: int = key_size
        if mode == "numpad":
            self._build_numpad()
        else:
            self._build_keyboard()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_keyboard(self) -> None:
        for row in self._ROWS:
            row_frame = tk.Frame(self, bg=BG_KEY)
            row_frame.pack(anchor="center", pady=3)

            for display, key_id, width in row:
                is_special = key_id is None
                _pady = max(2, int(8 * self._key_size / 13))
                lbl = tk.Label(
                    row_frame,
                    text=display,
                    font=(FONT_UI, max(7, int(self._key_size * 0.80)) if is_special else self._key_size, "bold" if not is_special else "normal"),
                    width=width,
                    relief=tk.RAISED,
                    bd=BD,
                    bg=BG_KEY,
                    fg="#777777" if is_special else "#1a1a1a",
                    padx=4,
                    pady=_pady,
                )
                lbl.pack(side=tk.LEFT, padx=2)
                if key_id is not None:
                    self._key_labels[key_id] = lbl

        # Space bar
        space_frame = tk.Frame(self, bg=BG_KEY)
        space_frame.pack(anchor="center", pady=3)
        space_lbl = tk.Label(
            space_frame,
            text="SPACE",
            font=(FONT_UI, max(7, int(self._key_size * 0.85))),
            width=20,
            relief=tk.RAISED,
            bd=BD,
            bg=BG_KEY,
            fg="#555555",
            pady=max(2, int(8 * self._key_size / 13)),
        )
        space_lbl.pack()
        self._key_labels[" "] = space_lbl

    def _build_numpad(self) -> None:
        _pady = max(2, int(8 * self._key_size / 13))
        _padx = 2

        grid_frame = tk.Frame(self, bg=BG_KEY)
        grid_frame.pack(anchor="center", pady=3)

        def _make_key(text: str, key_id, width: int) -> tk.Label:
            is_special = key_id is None
            lbl = tk.Label(
                grid_frame,
                text=text,
                font=(FONT_UI, max(7, int(self._key_size * 0.80)) if is_special else self._key_size,
                      "bold" if not is_special else "normal"),
                width=width,
                relief=tk.RAISED,
                bd=BD,
                bg=BG_KEY,
                fg="#777777" if is_special else "#1a1a1a",
                padx=4,
                pady=_pady,
            )
            if key_id is not None:
                self._key_labels[key_id] = lbl
            return lbl

        # Row 0: Tab, /, *, -
        _make_key("Tab", None, 5).grid(row=0, column=0, padx=_padx, pady=3, sticky="nsew")
        _make_key("/",   "/",  4).grid(row=0, column=1, padx=_padx, pady=3, sticky="nsew")
        _make_key("*",   "*",  4).grid(row=0, column=2, padx=_padx, pady=3, sticky="nsew")
        _make_key("-",   "-",  4).grid(row=0, column=3, padx=_padx, pady=3, sticky="nsew")

        # Row 1: 7, 8, 9  |  + tall (spans rows 1-2)
        _make_key("7", "7", 4).grid(row=1, column=0, padx=_padx, pady=3, sticky="nsew")
        _make_key("8", "8", 4).grid(row=1, column=1, padx=_padx, pady=3, sticky="nsew")
        _make_key("9", "9", 4).grid(row=1, column=2, padx=_padx, pady=3, sticky="nsew")
        _make_key("+", "+", 4).grid(row=1, column=3, rowspan=2, padx=_padx, pady=3, sticky="nsew")

        # Row 2: 4, 5, 6
        _make_key("4", "4", 4).grid(row=2, column=0, padx=_padx, pady=3, sticky="nsew")
        _make_key("5", "5", 4).grid(row=2, column=1, padx=_padx, pady=3, sticky="nsew")
        _make_key("6", "6", 4).grid(row=2, column=2, padx=_padx, pady=3, sticky="nsew")

        # Row 3: 1, 2, 3  |  Enter tall (spans rows 3-4)
        _make_key("1", "1", 4).grid(row=3, column=0, padx=_padx, pady=3, sticky="nsew")
        _make_key("2", "2", 4).grid(row=3, column=1, padx=_padx, pady=3, sticky="nsew")
        _make_key("3", "3", 4).grid(row=3, column=2, padx=_padx, pady=3, sticky="nsew")
        _make_key("ENTER", "enter", 4).grid(row=3, column=3, rowspan=2, padx=_padx, pady=3, sticky="nsew")

        # Row 4: 0 wide (spans cols 0-1), .
        _make_key("0", "0", 9).grid(row=4, column=0, columnspan=2, padx=_padx, pady=3, sticky="nsew")
        _make_key(".", ".", 4).grid(row=4, column=2, padx=_padx, pady=3, sticky="nsew")

    # ------------------------------------------------------------------
    # Live key highlighting
    # ------------------------------------------------------------------

    def set_active_key(self, key: Optional[str]) -> None:
        """
        Illuminate ``key`` as the next expected character.

        Pass ``None`` to clear the highlight without setting a new one.
        """
        # Restore the previous active key's background
        if self._active_key is not None:
            prev = self._key_labels.get(self._active_key)
            if prev is not None:
                prev.configure(bg=self._key_bg(self._active_key), fg="#1a1a1a",
                               relief=tk.RAISED)

        self._active_key = key

        if key is None:
            return
        lbl = self._key_labels.get(key)
        if lbl is not None:
            lbl.configure(bg=ACCENT, fg="#ffffff", relief=tk.SUNKEN)

    # ------------------------------------------------------------------
    # Heatmap support
    # ------------------------------------------------------------------

    def update_data(self, heatmap_data: dict[str, float]) -> None:
        """Repaint key backgrounds using ``{key: error_rate}`` data."""
        self._heatmap_data = heatmap_data
        for key, lbl in self._key_labels.items():
            if key == self._active_key:
                continue
            lbl.configure(bg=self._key_bg(key), fg=FG_DEFAULT)

    def reset(self) -> None:
        """Clear active highlight and heatmap; return all keys to default."""
        self.set_active_key(None)
        self._heatmap_data = {}
        for lbl in self._key_labels.values():
            lbl.configure(bg=BG_KEY, fg="#1a1a1a")

    # ------------------------------------------------------------------
    # Colour helpers
    # ------------------------------------------------------------------

    def _key_bg(self, key: str) -> str:
        rate = self._heatmap_data.get(key, 0.0)
        return BG_KEY if rate <= 0.0 else self._error_rate_to_color(rate)

    @staticmethod
    def _error_rate_to_color(rate: float) -> str:
        """0.0 (no errors) → green,  1.0 (all wrong) → red."""
        r_low, g_low, b_low = 0x2a, 0x7a, 0x2a   # green
        r_hi,  g_hi,  b_hi  = 0xcc, 0x22, 0x22   # red
        t = max(0.0, min(1.0, rate))
        r = int(r_low + (r_hi - r_low) * t)
        g = int(g_low + (g_hi - g_low) * t)
        b = int(b_low + (b_hi - b_low) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

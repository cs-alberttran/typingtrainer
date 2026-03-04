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

    _ROWS: list[list[str]] = [
        list("qwertyuiop"),
        list("asdfghjkl"),
        list("zxcvbnm"),
    ]

    # Horizontal pixel offset per row to simulate staggered QWERTY layout
    _ROW_INDENT: list[int] = [0, 14, 26]

    def __init__(
        self,
        master: tk.Widget,
        heatmap_data: Optional[dict[str, float]] = None,
        **kwargs,
    ) -> None:
        super().__init__(master, bg=BG_KEY, **kwargs)
        self._heatmap_data: dict[str, float] = heatmap_data or {}
        self._key_labels: dict[str, tk.Label] = {}
        self._active_key: Optional[str] = None
        self._build_keyboard()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_keyboard(self) -> None:
        for row_idx, row in enumerate(self._ROWS):
            row_frame = tk.Frame(self, bg=BG_KEY)
            row_frame.pack(anchor="center", pady=3)

            indent = self._ROW_INDENT[row_idx]
            if indent:
                tk.Frame(row_frame, width=indent * 3, bg=BG_KEY).pack(side=tk.LEFT)

            for key in row:
                lbl = tk.Label(
                    row_frame,
                    text=key.upper(),
                    font=(FONT_UI, 13, "bold"),
                    width=3,
                    relief=tk.RAISED,
                    bd=BD,
                    bg=BG_KEY,
                    fg="#1a1a1a",
                    padx=4,
                    pady=8,
                )
                lbl.pack(side=tk.LEFT, padx=2)
                self._key_labels[key] = lbl

        # Space bar
        space_frame = tk.Frame(self, bg=BG_KEY)
        space_frame.pack(anchor="center", pady=3)
        space_lbl = tk.Label(
            space_frame,
            text="SPACE",
            font=(FONT_UI, 11),
            width=20,
            relief=tk.RAISED,
            bd=BD,
            bg=BG_KEY,
            fg="#555555",
            pady=8,
        )
        space_lbl.pack()
        self._key_labels[" "] = space_lbl

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

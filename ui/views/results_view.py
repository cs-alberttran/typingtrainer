"""
Results screen — displayed after a completed typing session.

Shows:
  - WPM (large, prominent)
  - Raw WPM
  - Accuracy
  - Correct / incorrect character counts
  - Words completed
  - Elapsed time
  - Navigation back to home or direct retry
"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Optional

from config import (
    ACCENT,
    ACCENT_HOVER,
    BD,
    BG_MAIN,
    BG_PANEL,
    FG_CORRECT,
    FG_DEFAULT,
    FG_ERROR,
    FG_MUTED,
    FONT_BUTTON_SIZE,
    FONT_MONO,
    FONT_STAT_SIZE,
    FONT_TITLE_SIZE,
    FONT_UI,
)
from domain.models import SessionResult

if TYPE_CHECKING:
    from ui.app import App


class ResultsView(tk.Frame):
    """
    Post-session results screen.

    Receives a SessionResult via on_show(result=...) and renders the
    summary statistics.
    """

    def __init__(self, master: "App") -> None:
        super().__init__(master, bg=BG_MAIN)
        self._app = master
        self._last_duration: int = 30
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        wrapper = tk.Frame(self, bg=BG_MAIN)
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        # ---- Heading -------------------------------------------------
        tk.Label(
            wrapper,
            text="Test Complete",
            font=(FONT_UI, FONT_TITLE_SIZE - 2, "bold"),
            bg=BG_MAIN,
            fg=FG_DEFAULT,
        ).pack(pady=(0, 4))

        self._mode_var = tk.StringVar(value="")
        tk.Label(
            wrapper,
            textvariable=self._mode_var,
            font=(FONT_UI, 10),
            bg=BG_MAIN,
            fg=FG_MUTED,
        ).pack(pady=(0, 20))

        # ---- Primary metric (WPM) ------------------------------------
        wpm_frame = tk.Frame(wrapper, bg=BG_MAIN)
        wpm_frame.pack(pady=(0, 8))

        self._wpm_var = tk.StringVar(value="")  
        tk.Label(
            wpm_frame,
            textvariable=self._wpm_var,
            font=(FONT_MONO, 52, "bold"),
            bg=BG_MAIN,
            fg=ACCENT,
        ).pack(side=tk.LEFT)

        tk.Label(
            wpm_frame,
            text=" WPM",
            font=(FONT_UI, 16),
            bg=BG_MAIN,
            fg=FG_MUTED,
        ).pack(side=tk.LEFT, anchor="s", pady=(0, 10))

        # ---- Secondary stats grid -----------------------------------
        stats_panel = tk.Frame(wrapper, bg=BG_PANEL, relief=tk.GROOVE, bd=BD)
        stats_panel.pack(fill=tk.X, pady=(0, 20), ipadx=16, ipady=10)

        self._stat_rows: list[tuple[str, tk.StringVar]] = []
        stat_defs = [
            ("Accuracy", ""),
            ("Raw WPM", ""),
            ("Correct chars", ""),
            ("Incorrect chars", ""),
            ("Words typed", ""),
            ("Elapsed", ""),
        ]
        for i, (label, _) in enumerate(stat_defs):
            var = tk.StringVar(value="")
            self._stat_rows.append((label, var))
            row = tk.Frame(stats_panel, bg=BG_PANEL)
            row.pack(anchor = "center", pady=2)
            tk.Label(
                row,
                text=label,
                font=(FONT_UI, FONT_STAT_SIZE),
                bg=BG_PANEL,
                fg=FG_MUTED,
                width=16,
                anchor="w",
            ).pack(side=tk.LEFT)
            tk.Label(
                row,
                textvariable=var,
                font=(FONT_MONO, FONT_STAT_SIZE, "bold"),
                bg=BG_PANEL,
                fg=FG_DEFAULT,
                anchor="w",
            ).pack(side=tk.LEFT)

        # ---- Action buttons -----------------------------------------
        btn_row = tk.Frame(wrapper, bg=BG_MAIN)
        btn_row.pack()

        retry_btn = tk.Button(
            btn_row,
            text="Retry",
            font=(FONT_UI, FONT_BUTTON_SIZE + 1, "bold"),
            bg="#3c6ea5",
            fg="#ffffff",
            activebackground=ACCENT_HOVER,
            activeforeground="#ffffff",
            relief=tk.RAISED,
            bd=BD,
            cursor="hand2",
            padx=20,
            pady=5,
            command=self._on_retry,
        )
        retry_btn.pack(side=tk.LEFT, padx=(0, 10))
        retry_btn.bind("<Enter>", lambda _e: retry_btn.configure(bg=ACCENT_HOVER))
        retry_btn.bind("<Leave>", lambda _e: retry_btn.configure(bg="#3c6ea5"))

        home_btn = tk.Button(
            btn_row,
            text="Home",
            font=(FONT_UI, FONT_BUTTON_SIZE + 1),
            bg=BG_PANEL,
            fg=FG_DEFAULT,
            activebackground="#4a4a4a",
            activeforeground=FG_DEFAULT,
            relief=tk.RAISED,
            bd=BD,
            cursor="hand2",
            padx=20,
            pady=5,
            command=self._on_home,
        )
        home_btn.pack(side=tk.LEFT)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_show(self, result: Optional[SessionResult] = None, **_kwargs) -> None:
        if result is None:
            return
        self._last_duration = result.duration_seconds
        self._render(result)
        self._app.bind("<Return>", lambda _e: self._on_retry())

    def _render(self, result: SessionResult) -> None:
        self._mode_var.set(
            f"Mode: {result.game_mode.capitalize()}  •  "
            f"Duration: {result.duration_seconds}s  •  "
            f"Elapsed: {result.elapsed_seconds:.1f}s"
        )
        self._wpm_var.set(f"{result.wpm:.1f}")

        values = [
            f"{result.accuracy_pct}%",
            f"{result.raw_wpm:.1f}",
            str(result.correct_chars),
            str(result.incorrect_chars),
            str(result.words_completed),
            f"{result.elapsed_seconds:.1f}s",
        ]
        for (_, var), value in zip(self._stat_rows, values):
            var.set(value)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_retry(self) -> None:
        self._app.raise_view("test", duration=self._last_duration)

    def _on_home(self) -> None:
        self._app.raise_view("home")

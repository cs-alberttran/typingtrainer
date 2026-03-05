"""
Home / menu screen.

Presents:
  - App title
  - Duration selector (radio buttons)
  - Start button
  - Personal best (pulled from ResultsRepository)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from config import (
    ACCENT,
    ACCENT_HOVER,
    BD,
    BG_MAIN,
    BG_PANEL,
    FG_DEFAULT,
    FG_MUTED,
    FONT_MONO,
    FONT_TITLE_SIZE,
    FONT_UI,
    FONT_BUTTON_SIZE,
)

if TYPE_CHECKING:
    from ui.app import App

class HomeView(tk.Frame):
    """
    Landing screen shown at startup and after each completed session.

    :param master: The parent App window.
    """

    def __init__(self, master: "App") -> None:
        super().__init__(master, bg=BG_MAIN)
        self._app = master
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        wrapper = tk.Frame(self, bg=BG_MAIN)
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        # ---- Title ---------------------------------------------------
        tk.Label(
            wrapper,
            text="TypingTrainer",
            font=(FONT_MONO, FONT_TITLE_SIZE + 4, "bold"),
            bg=BG_MAIN,
            fg=ACCENT,
        ).pack(pady=(0, 2))

        tk.Label(
            wrapper,
            text="A classic adaptive typing trainer",
            font=(FONT_UI, 9),
            bg=BG_MAIN,
            fg=FG_MUTED,
        ).pack(pady=(0, 24))

        # ---- Centre panel (XP-style group box) ----------------------
        panel = tk.Frame(
            wrapper,
            bg=BG_PANEL,
            relief=tk.GROOVE,
            bd=BD,
            padx=32,
            pady=20,
        )
        panel.pack(pady=(0, 16))

        tk.Label(
            panel,
            text="Ready to type?",
            font=(FONT_UI, 10, "bold"),
            bg=BG_PANEL,
            fg=FG_DEFAULT,
        ).pack(pady=(0, 14))

        start_btn = tk.Button(
            panel,
            text="Typing Test",
            font=(FONT_UI, FONT_BUTTON_SIZE + 1, "bold"),
            bg="#3c6ea5",
            fg="#ffffff",
            activebackground=ACCENT_HOVER,
            activeforeground="#ffffff",
            relief=tk.RAISED,
            bd=BD,
            cursor="hand2",
            padx=24,
            pady=6,
            command=self._on_start,
        )
        start_btn.pack(pady=(0, 4))
        start_btn.bind("<Enter>", lambda _e: start_btn.configure(bg=ACCENT_HOVER))
        start_btn.bind("<Leave>", lambda _e: start_btn.configure(bg="#3c6ea5"))

        tk.Label(
            panel,
            text="Press ESC to quit",
            font=(FONT_UI, 8),
            bg=BG_PANEL,
            fg=FG_MUTED,
        ).pack(pady=(8, 0))

        # ---- Personal best -------------------------------------------
        self._pb_var = tk.StringVar(value="")
        self._pb_label = tk.Label(
            wrapper,
            textvariable=self._pb_var,
            font=(FONT_UI, 8),
            bg=BG_MAIN,
            fg=FG_MUTED,
        )
        self._pb_label.pack()

        self._app.bind("<Return>", lambda _e: self._on_start())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_show(self, **_kwargs) -> None:
        """Called by the app whenever this view is raised."""
        self._refresh_personal_best()
        # Re-bind Enter (test_view may have unbound it)
        self._app.bind("<Return>", lambda _e: self._on_start())

    def _refresh_personal_best(self) -> None:
        try:
            pb = self._app.results_repository.best_wpm()
            if pb > 0:
                self._pb_var.set(f"Personal best:  {pb:.1f} WPM")
            else:
                self._pb_var.set("No results yet — take your first test!")
        except Exception:  # noqa: BLE001
            self._pb_var.set("")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        self._app.raise_view("test")

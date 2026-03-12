"""
Main application window.

Implements a simple frame-stacking navigator:  only one view is visible
at a time; navigation is handled by raise_view().

This keeps view logic completely separate: no view knows about its siblings.
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import font as tkfont
from typing import Optional

from config import (
    BD,
    BG_MAIN,
    FG_DEFAULT,
    FONT_UI,
    FONT_TITLE_SIZE,
    WINDOW_HEIGHT,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)

logger = logging.getLogger(__name__)


class App(tk.Tk):
    """
    Top-level application window.

    Hosts a stack of views (Frames) and exposes `raise_view(name)` for
    navigating between them.  Views register themselves via `add_view()`.

    :param session_manager: The SessionManager instance shared across all views.
    :param results_repository: ResultsRepository for reading past scores.
    """

    def __init__(self, session_manager, results_repository, settings_manager=None) -> None:
        super().__init__()

        self.session_manager = session_manager
        self.results_repository = results_repository
        self.settings_manager = settings_manager

        self._views: dict[str, tk.Frame] = {}
        self._current_view: Optional[str] = None

        self._configure_window()
        self._configure_fonts()
        self._build_container()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _configure_window(self) -> None:
        self.title(WINDOW_TITLE)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.configure(bg=BG_MAIN)
        self.resizable(True, True)
        # Centre on screen
        self.update_idletasks()
        self._centre()

    def _centre(self) -> None:
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - WINDOW_WIDTH) // 2
        y = (screen_h - WINDOW_HEIGHT) // 2
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")

    def _configure_fonts(self) -> None:
        """Override default widget font so everything uses FONT_UI."""
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family=FONT_UI, size=9)
        text_font = tkfont.nametofont("TkTextFont")
        text_font.configure(family=FONT_UI, size=9)
        # Make default button/widget relief match classic Windows style
        self.option_add("*Button.relief", "raised")
        self.option_add("*Button.borderWidth", str(BD))
        self.option_add("*Label.borderWidth", "0")

    def _build_container(self) -> None:
        self._container = tk.Frame(self, bg=BG_MAIN)
        self._container.pack(fill=tk.BOTH, expand=True)
        self._container.grid_rowconfigure(0, weight=1)
        self._container.grid_columnconfigure(0, weight=1)

    # ------------------------------------------------------------------
    # View management
    # ------------------------------------------------------------------

    def add_view(self, name: str, view: tk.Frame) -> None:
        """Register a view frame under `name`."""
        view.grid(in_=self._container, row=0, column=0, sticky="nsew")
        self._views[name] = view

    def raise_view(self, name: str, **kwargs) -> None:
        """
        Switch the visible view to `name`.

        Any keyword arguments are forwarded to the view's `on_show(**kwargs)`
        method if it exists, allowing the caller to pass context (e.g. results).
        """
        view = self._views.get(name)
        if view is None:
            logger.error("Unknown view: %r", name)
            return
        self._current_view = name
        view.tkraise()
        on_show = getattr(view, "on_show", None)
        if callable(on_show):
            on_show(**kwargs)

    @property
    def current_view(self) -> Optional[str]:
        return self._current_view

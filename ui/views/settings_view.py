"""
Settings view — lets the user configure application preferences.

Changes to theme and font take effect after restarting the app.
The mute toggle takes effect immediately (stored in SettingsManager).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING

from config import (
    ACCENT,
    ACCENT_HOVER,
    BD,
    BG_MAIN,
    BG_PANEL,
    FG_DEFAULT,
    FG_MUTED,
    FONT_UI,
    FONT_BUTTON_SIZE,
)

if TYPE_CHECKING:
    from ui.app import App

_FONTS: list[str] = [
    "Tahoma",
    "Segoe UI",
    "Arial",
    "Calibri",
    "Verdana",
    "Trebuchet MS",
    "Georgia",
    "Times New Roman",
    "Lucida Sans Unicode",
    "Microsoft Sans Serif",
    "Courier New",
]


class SettingsView(tk.Frame):
    """Application settings screen."""

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
            text="\u2699  Settings",
            font=(FONT_UI, 16, "bold"),
            bg=BG_MAIN,
            fg=FG_DEFAULT,
        ).pack(pady=(0, 18))

        panel = tk.Frame(
            wrapper,
            bg=BG_PANEL,
            relief=tk.GROOVE,
            bd=BD,
            padx=30,
            pady=20,
        )
        panel.pack()

        sm = self._app.settings_manager

        # ---- Theme ---------------------------------------------------
        section = tk.Frame(panel, bg=BG_PANEL)
        section.pack(fill=tk.X, pady=(0, 14))

        self._dark_var = tk.BooleanVar(value=sm.get("dark_mode"))
        tk.Checkbutton(
            section,
            text="Dark Mode",
            variable=self._dark_var,
            font=(FONT_UI, 10),
            bg=BG_PANEL,
            fg=FG_DEFAULT,
            selectcolor=BG_PANEL,
            activebackground=BG_PANEL,
            cursor="hand2",
        ).pack(side=tk.LEFT)
        tk.Label(
            section,
            text="(restart to apply)",
            font=(FONT_UI, 8),
            bg=BG_PANEL,
            fg=FG_MUTED,
        ).pack(side=tk.LEFT, padx=(6, 0))

        # ---- Divider -------------------------------------------------
        tk.Frame(panel, bg=FG_MUTED, height=1).pack(fill=tk.X, pady=(0, 12))

        # ---- UI Font -------------------------------------------------
        tk.Label(
            panel,
            text="UI Font",
            font=(FONT_UI, 10, "bold"),
            bg=BG_PANEL,
            fg=FG_DEFAULT,
            anchor="w",
        ).pack(fill=tk.X)
        tk.Label(
            panel,
            text="restart to apply",
            font=(FONT_UI, 8),
            bg=BG_PANEL,
            fg=FG_MUTED,
            anchor="w",
        ).pack(fill=tk.X, pady=(0, 5))

        font_frame = tk.Frame(panel, bg=BG_PANEL)
        font_frame.pack(anchor="w", pady=(0, 14))

        scrollbar = tk.Scrollbar(font_frame, orient=tk.VERTICAL)
        self._font_list = tk.Listbox(
            font_frame,
            font=(FONT_UI, 10),
            height=6,
            width=24,
            exportselection=False,
            yscrollcommand=scrollbar.set,
            bg="#ffffff",
            fg="#1a1a1a",
            selectbackground=ACCENT,
            selectforeground="#ffffff",
            relief=tk.SUNKEN,
            bd=BD,
        )
        scrollbar.config(command=self._font_list.yview)
        self._font_list.pack(side=tk.LEFT)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        current_font = sm.get("font_family")
        for i, f in enumerate(_FONTS):
            self._font_list.insert(tk.END, f)
            if f == current_font:
                self._font_list.selection_set(i)
                self._font_list.see(i)

        # ---- Word display font size ----------------------------------
        tk.Label(
            panel,
            text="Word Display Size",
            font=(FONT_UI, 10, "bold"),
            bg=BG_PANEL,
            fg=FG_DEFAULT,
            anchor="w",
        ).pack(fill=tk.X)
        tk.Label(
            panel,
            text="restart to apply",
            font=(FONT_UI, 8),
            bg=BG_PANEL,
            fg=FG_MUTED,
            anchor="w",
        ).pack(fill=tk.X, pady=(0, 5))

        size_row = tk.Frame(panel, bg=BG_PANEL)
        size_row.pack(anchor="w", pady=(0, 14))

        self._size_var = tk.IntVar(value=sm.get("word_font_size"))
        tk.Spinbox(
            size_row,
            from_=10,
            to=32,
            increment=1,
            textvariable=self._size_var,
            width=5,
            font=(FONT_UI, 10),
            relief=tk.SUNKEN,
            bd=BD,
        ).pack(side=tk.LEFT)
        tk.Label(
            size_row,
            text="pt  (10 – 32)",
            font=(FONT_UI, 9),
            bg=BG_PANEL,
            fg=FG_MUTED,
        ).pack(side=tk.LEFT, padx=(6, 0))

        # ---- Divider -------------------------------------------------
        tk.Frame(panel, bg=FG_MUTED, height=1).pack(fill=tk.X, pady=(0, 12))

        # ---- Sound ---------------------------------------------------
        tk.Label(
            panel,
            text="Sound",
            font=(FONT_UI, 10, "bold"),
            bg=BG_PANEL,
            fg=FG_DEFAULT,
            anchor="w",
        ).pack(fill=tk.X, pady=(0, 6))

        self._mute_var = tk.BooleanVar(value=sm.get("mute_sound"))
        tk.Checkbutton(
            panel,
            text="Mute click sound during tests",
            variable=self._mute_var,
            font=(FONT_UI, 10),
            bg=BG_PANEL,
            fg=FG_DEFAULT,
            selectcolor=BG_PANEL,
            activebackground=BG_PANEL,
            cursor="hand2",
        ).pack(anchor="w")

        tk.Label(
            panel,
            text='Drop assets/click.wav to use a custom sound.',
            font=(FONT_UI, 8),
            bg=BG_PANEL,
            fg=FG_MUTED,
            anchor="w",
        ).pack(fill=tk.X, pady=(2, 16))

        # ---- Buttons -------------------------------------------------
        btn_row = tk.Frame(panel, bg=BG_PANEL)
        btn_row.pack()

        save_btn = tk.Button(
            btn_row,
            text="Save",
            font=(FONT_UI, FONT_BUTTON_SIZE, "bold"),
            bg="#3c6ea5",
            fg="#ffffff",
            activebackground=ACCENT_HOVER,
            activeforeground="#ffffff",
            relief=tk.RAISED,
            bd=BD,
            cursor="hand2",
            padx=22,
            pady=5,
            command=self._on_save,
        )
        save_btn.pack(side=tk.LEFT, padx=(0, 8))
        save_btn.bind("<Enter>", lambda _e: save_btn.configure(bg=ACCENT_HOVER))
        save_btn.bind("<Leave>", lambda _e: save_btn.configure(bg="#3c6ea5"))

        back_btn = tk.Button(
            btn_row,
            text="Back",
            font=(FONT_UI, FONT_BUTTON_SIZE),
            bg=BG_PANEL,
            fg=FG_DEFAULT,
            activebackground="#4a4a4a",
            activeforeground=FG_DEFAULT,
            relief=tk.RAISED,
            bd=BD,
            cursor="hand2",
            padx=22,
            pady=5,
            command=self._on_back,
        )
        back_btn.pack(side=tk.LEFT)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_show(self, **_kwargs) -> None:
        pass

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        sm = self._app.settings_manager

        sm.set("dark_mode", self._dark_var.get())

        sel = self._font_list.curselection()
        if sel:
            sm.set("font_family", _FONTS[sel[0]])

        try:
            size = int(self._size_var.get())
            sm.set("word_font_size", max(10, min(32, size)))
        except (ValueError, tk.TclError):
            pass

        sm.set("mute_sound", self._mute_var.get())
        sm.save()

        messagebox.showinfo(
            "Settings Saved",
            "Settings saved successfully.\n\n"
            "Font and theme changes will take effect\nafter restarting the app.",
            parent=self,
        )

    def _on_back(self) -> None:
        self._app.raise_view("home")

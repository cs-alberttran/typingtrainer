"""
Test view — the main typing experience.

Architecture notes:
  - Word display uses a read-only Text widget with character-level tags.
    Tags created lazily, colored in real-time as the user types.
  - Keyboard capture is done via window-level <Key> binding rather than
    an Entry widget, giving us full control over what reaches the engine.
  - A recurring `after()` loop drives the timer countdown at TIMER_POLL_MS
    resolution without blocking the Tkinter event loop.
  - The view is stateless between sessions; on_show() resets everything.
"""

from __future__ import annotations

import random
import tkinter as tk
from typing import TYPE_CHECKING, Optional
from ui.widgets.keyboard_heatmap import KeyboardHeatmap

from config import (
    ACCENT,
    ACCENT_HOVER,
    BD,
    BG_INPUT,
    BG_MAIN,
    BG_PANEL,
    BG_WORD_BOX,
    DEFAULT_DURATION,
    FG_CORRECT,
    FG_CURRENT,
    FG_DEFAULT,
    FG_ERROR,
    FG_MUTED,
    FG_PENDING,
    FONT_BUTTON_SIZE,
    FONT_MONO,
    FONT_STAT_SIZE,
    FONT_UI,
    FONT_WORD_SIZE,
    TEST_DURATIONS,
    TIMER_POLL_MS,
)
from domain.models import TestState

if TYPE_CHECKING:
    from ui.app import App

# How many words to make visible in the word display at once
_VISIBLE_WORDS: int = 80


class TestView(tk.Frame):
    """
    Typing test screen.

    Accepts a `duration` kwarg via on_show() and starts a fresh session.
    """

    def __init__(self, master: "App") -> None:
        super().__init__(master, bg=BG_MAIN)
        self._app = master
        self._timer_id: Optional[str] = None
        self._selected_duration: tk.IntVar = tk.IntVar(value=DEFAULT_DURATION)
        self._hard_mode: bool = False
        self._dur_buttons: dict[int, tk.Button] = {}
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # ---- Top stats bar ------------------------------------------
        stats_bar = tk.Frame(self, bg=BG_MAIN, padx=10, pady=6,
                             relief=tk.FLAT, bd=0)
        stats_bar.pack(fill=tk.X)

        # Sunken divider panel that holds timer + wpm + acc
        left_info = tk.Frame(stats_bar, bg=BG_PANEL, relief=tk.SUNKEN,
                             bd=BD, padx=8, pady=2)
        left_info.pack(side=tk.LEFT)

        self._timer_var = tk.StringVar(value="")
        self._wpm_var = tk.StringVar(value="")
        self._acc_var = tk.StringVar(value="")

        tk.Label(
            left_info,
            textvariable=self._timer_var,
            font=(FONT_MONO, FONT_STAT_SIZE + 4, "bold"),
            bg=BG_PANEL,
            fg=FG_DEFAULT,
            width=5,
            anchor="w",
        ).pack(side=tk.LEFT)

        tk.Label(
            left_info,
            textvariable=self._wpm_var,
            font=(FONT_UI, FONT_STAT_SIZE),
            bg=BG_PANEL,
            fg=FG_MUTED,
            anchor="center",
        ).pack(side=tk.LEFT, padx=(12, 0))

        tk.Label(
            left_info,
            textvariable=self._acc_var,
            font=(FONT_UI, FONT_STAT_SIZE),
            bg=BG_PANEL,
            fg=FG_MUTED,
            anchor="center",
        ).pack(side=tk.LEFT, padx=(12, 0))

        # ESC hint
        tk.Label(
            stats_bar,
            text="ESC — quit",
            font=(FONT_UI, 8),
            bg=BG_MAIN,
            fg=FG_MUTED,
        ).pack(side=tk.RIGHT, padx=(0, 4))

        tk.Label(
            stats_bar,
            text=" Ctrl + R ",
            font=(FONT_UI, 8),
            bg=BG_MAIN,
            fg=FG_MUTED,
            anchor="center",
            padx=4,
            pady=2,
            relief=tk.FLAT,
            cursor="arrow",
        ).pack(side=tk.RIGHT, padx=(0, 4))

        # ---- Hard Mode button --------------------------------------
        self._hard_btn = tk.Button(
            stats_bar,
            text="Hard Mode",
            font=(FONT_UI, FONT_BUTTON_SIZE - 1),
            relief=tk.RAISED,
            bd=BD,
            cursor="hand2",
            padx=6,
            pady=1,
            bg=BG_PANEL,
            fg=FG_DEFAULT,
            command=self._on_hard_mode_toggle,
        )
        self._hard_btn.pack(side=tk.RIGHT, padx=(0, 6))

        # ---- Duration chips -----------------------------------------
        dur_frame = tk.Frame(stats_bar, bg=BG_PANEL, relief=tk.SUNKEN,
                             bd=BD, padx=4, pady=2)
        dur_frame.pack(side=tk.RIGHT, padx=(0, 6))
        for dur in TEST_DURATIONS:
            btn = tk.Button(
                dur_frame,
                text=f"{dur}s",
                font=(FONT_UI, FONT_BUTTON_SIZE - 1),
                relief=tk.RAISED,
                bd=BD,
                cursor="hand2",
                padx=6,
                pady=1,
                command=lambda d=dur: self._on_duration_select(d),
            )
            btn.pack(side=tk.LEFT, padx=2)
            self._dur_buttons[dur] = btn
        self._refresh_duration_chips()

        # ---- Word display -------------------------------------------
        word_frame = tk.Frame(self, bg=BG_WORD_BOX, relief=tk.SUNKEN, bd=BD)
        word_frame.pack(fill=tk.X, padx=10, pady=(0, 4))

        self._word_text = tk.Text(
            word_frame,
            font=(FONT_MONO, FONT_WORD_SIZE),
            bg=BG_WORD_BOX,
            fg=FG_PENDING,
            relief=tk.FLAT,
            wrap=tk.WORD,
            state=tk.DISABLED,
            cursor="arrow",
            padx=18,
            pady=10,
            spacing1=4,
            spacing3=4,
            height=3,
        )
        self._word_text.pack(fill=tk.X)

        # Configure text tags
        self._word_text.tag_configure("pending", foreground=FG_PENDING)
        self._word_text.tag_configure("correct", foreground=FG_CORRECT)
        self._word_text.tag_configure("error", foreground=FG_ERROR)
        self._word_text.tag_configure(
            "current_word",
            foreground=FG_CURRENT,
            underline=True,
        )
        self._word_text.tag_configure(
            "cursor_char",
            background=ACCENT,
            foreground="#ffffff",
        )
        # cursor_char must win over all other tags on the same character
        self._word_text.tag_raise("cursor_char")

        # ---- Typed input display (echo bar) --------------------------
        input_frame = tk.Frame(self, bg=BG_PANEL, relief=tk.GROOVE, bd=BD,
                               padx=10, pady=4)
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 2))

        tk.Label(
            input_frame,
            text="typing:",
            font=(FONT_UI, 8),
            bg=BG_PANEL,
            fg=FG_MUTED,
        ).pack(side=tk.LEFT, padx=(0, 6))

        self._typed_var = tk.StringVar(value="")
        typed_label = tk.Label(
            input_frame,
            textvariable=self._typed_var,
            font=(FONT_MONO, FONT_WORD_SIZE - 4),
            bg=BG_INPUT,
            fg="#1a1a1a",
            anchor="w",
            relief=tk.SUNKEN,
            bd=BD,
            padx=8,
            pady=3,
            width=40,
        )
        typed_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ---- Keyboard visual ----------------------------------------
        kbd_frame = tk.Frame(self, bg=BG_PANEL, relief=tk.GROOVE, bd=BD,
                             pady=6)
        kbd_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 4))
        self._keyboard = KeyboardHeatmap(kbd_frame)
        self._keyboard.pack(anchor="center", expand=True)

        # ---- Status bar ---------------------------------------------
        status_bar = tk.Frame(self, bg=BG_MAIN, padx=10, pady=3)
        status_bar.pack(fill=tk.X)
        self._status_var = tk.StringVar(value="")
        tk.Label(
            status_bar,
            textvariable=self._status_var,
            font=(FONT_UI, 8),
            bg=BG_MAIN,
            fg=FG_MUTED,
        ).pack(side=tk.LEFT)

    # ------------------------------------------------------------------
    # View lifecycle
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Duration selection
    # ------------------------------------------------------------------

    def _on_hard_mode_toggle(self) -> None:
        """Toggle hard mode on/off and restart the session."""
        if hasattr(self, "_engine") and self._engine.state == TestState.RUNNING:
            return
        self._hard_mode = not self._hard_mode
        if self._hard_mode:
            self._hard_btn.configure(bg=ACCENT, fg="#ffffff", relief=tk.SUNKEN)
        else:
            self._hard_btn.configure(bg=BG_PANEL, fg=FG_DEFAULT, relief=tk.RAISED)
        self.on_show()

    def _on_duration_select(self, duration: int) -> None:
        """Called when the user clicks a duration chip."""
        from domain.models import TestState  # already imported at module level
        if hasattr(self, "_engine") and self._engine.state == TestState.RUNNING:
            return  # ignore while a test is running
        self._selected_duration.set(duration)
        self._refresh_duration_chips()
        # Restart the session with the new duration
        self.on_show()

    def _refresh_duration_chips(self) -> None:
        """Highlight the active duration chip, dim the rest."""
        selected = self._selected_duration.get()
        for dur, btn in self._dur_buttons.items():
            if dur == selected:
                btn.configure(bg=ACCENT, fg="#ffffff", relief=tk.SUNKEN)
            else:
                btn.configure(bg=BG_PANEL, fg=FG_DEFAULT, relief=tk.RAISED)

    def on_show(self, duration: int = 0, **_kwargs) -> None:
        """Initialise a fresh session when this view becomes active."""
        if duration:
            self._selected_duration.set(duration)
            self._refresh_duration_chips()
        self._cancel_timer()
        self._reset_stats_display()
        self._keyboard.reset()

        engine = self._app.session_manager.new_session(
            duration=self._selected_duration.get()
        )
        self._engine = engine
        self._word_chars: list[tuple[str, str]] = []  # (start_idx, end_idx) per word char
        self._word_positions: list[tuple[str, str]] = []  # (word_start, word_end) per word

        if self._hard_mode:
            self._apply_hard_mode(self._engine)

        self._populate_word_display()

        # Highlight the very first key before the user starts
        first_target = self._engine.current_word_state.target
        if first_target:
            self._keyboard.set_active_key(first_target[0])

        self._status_var.set("Start typing to begin the test…")

        # Bind keys to the top-level window so focus doesn't matter
        self._app.bind("<Key>", self._on_key)
        self._app.bind("<Escape>", self._on_escape)
        self._app.unbind("<Return>")
        self._app.bind("<Control-r>", self._on_refresh)
        self._app.bind("<Control-R>", self._on_refresh)

        self._app.focus_force()

    def _reset_stats_display(self) -> None:
        self._timer_var.set("–")
        self._wpm_var.set("")
        self._acc_var.set("")
        self._typed_var.set("")
        self._status_var.set("")

    # ------------------------------------------------------------------
    # Hard mode
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_hard_mode(engine) -> None:
        """Mutate word targets in-place: capitalise ~30% and add punctuation to ~30%."""
        punctuation = ",.?!"
        rng = random.Random()
        for ws in engine.word_states:
            word = ws.target
            if rng.random() < 0.20:
                word = word[0].upper() + word[1:]
            if rng.random() < 0.20:
                word = word + rng.choice(punctuation)
            ws.target = word

    # ------------------------------------------------------------------
    # Word display population
    # ------------------------------------------------------------------

    def _populate_word_display(self) -> None:
        """Insert the first N words into the Text widget and tag them."""
        txt = self._word_text
        txt.configure(state=tk.NORMAL)
        txt.delete("1.0", tk.END)
        self._word_positions.clear()

        words = [ws.target for ws in self._engine.word_states[:_VISIBLE_WORDS]]

        for i, word in enumerate(words):
            if i > 0:
                txt.insert(tk.END, " ")

            start_idx = txt.index(tk.END + "-1c")
            txt.insert(tk.END, word)
            end_idx = txt.index(tk.END + "-1c")

            self._word_positions.append((start_idx, end_idx))
            txt.tag_add("pending", start_idx, end_idx)

        txt.configure(state=tk.DISABLED)
        self._highlight_current_word()

    def _highlight_current_word(self) -> None:
        """Apply the current_word tag to the active word."""
        idx = self._engine.current_index
        if idx >= len(self._word_positions):
            return
        start, end = self._word_positions[idx]
        self._word_text.tag_remove("current_word", "1.0", tk.END)
        self._word_text.tag_add("current_word", start, end)
        # Scroll so the current word is visible
        self._word_text.see(start)

    # ------------------------------------------------------------------
    # Keystroke handler
    # ------------------------------------------------------------------

    def _on_key(self, event: tk.Event) -> None:
        char = self._classify_event(event)
        if char is None:
            return

        outcome = self._app.session_manager.process_key(char)
        engine = self._engine

        if engine.state == TestState.FINISHED and self._timer_id is not None:
            # Session ended mid-keypress
            self._on_session_finish()
            return

        # Start timer loop on first valid key
        if engine.state == TestState.RUNNING and self._timer_id is None:
            self._start_timer_loop()
            self._status_var.set("")

        self._refresh_word_display()
        self._update_stats()

    @staticmethod
    def _classify_event(event: tk.Event) -> Optional[str]:
        """
        Convert a Tkinter key event into a character suitable for the engine.

        Returns None for events that should be completely ignored.
        """
        keysym = event.keysym

        if keysym == "BackSpace":
            if event.state & 4:          # Ctrl held — clear whole word
                return "CtrlBackSpace"
            return "BackSpace"
        if keysym == "space":
            return " "
        if keysym == "Escape":
            return None
        # Ignore modifier-only and navigation keys
        if keysym in (
            "Shift_L", "Shift_R", "Control_L",
            "Alt_L", "Alt_R", "Caps_Lock", "Tab",
            "Return", "Delete", "Up", "Down", "Left", "Right",
            "Home", "End", "Prior", "Next", "Insert", "F1",
            "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9",
            "F10", "F11", "F12", "Super_L", "Super_R",
        ):
            return None
        # Accept printable single characters
        char = event.char
        if char and char.isprintable():
            return char
        return None

    def _on_escape(self, _event: tk.Event) -> None:
        self._cancel_timer()
        self._app.session_manager.abort_session()
        self._cleanup_bindings()
        self._app.raise_view("home")
    
    def _on_refresh(self, _event: tk.Event) -> None:
        self._cancel_timer()
        engine = getattr(self, "_engine", None)
        if engine is None:
            return
        if engine.state == TestState.RUNNING:  
            self._app.session_manager.abort_session()
        new_engine = self._app.session_manager.new_session(
            duration=self._selected_duration.get()
        )

        self._engine = new_engine

        if self._hard_mode:
            self._apply_hard_mode(new_engine)

        self._populate_word_display()

        first_target = new_engine.current_word_state.target
        if first_target:
            self._keyboard.set_active_key(first_target[0])

        self._status_var.set("New test started.")

    # ------------------------------------------------------------------
    # Word display refresh
    # ------------------------------------------------------------------

    def _refresh_word_display(self) -> None:
        """
        Re-colour the current word based on what has been typed so far.
        All committed words keep their final colouring.

        Also:
        - Applies a cursor-block highlight on the next character to type.
        - Colours the whole word red when the user over-types.
        - Updates the keyboard widget to highlight the next expected key.
        """
        engine = self._engine
        idx = engine.current_index

        if idx >= len(self._word_positions):
            return

        word_state = engine.current_word_state
        typed = word_state.typed
        target = word_state.target
        overflow = len(typed) > len(target)

        start_pos, _ = self._word_positions[idx]
        txt = self._word_text
        txt.configure(state=tk.NORMAL)

        # Remove existing colour tags for this word
        word_start, word_end = self._word_positions[idx]
        for tag in ("pending", "correct", "error", "current_word", "cursor_char"):
            txt.tag_remove(tag, word_start, word_end)

        if overflow:
            # Entire word flashes red to indicate over-typing
            txt.tag_add("error", word_start, word_end)
        else:
            # Per-character correct / incorrect / pending colour
            for j, target_ch in enumerate(target):
                char_start = f"{start_pos}+{j}c"
                char_end = f"{start_pos}+{j + 1}c"
                if j < len(typed):
                    tag = "correct" if typed[j] == target_ch else "error"
                else:
                    tag = "pending"
                txt.tag_add(tag, char_start, char_end)

            # Cursor block on the next character the user must type
            cursor_pos = len(typed)
            if cursor_pos < len(target):
                char_start = f"{start_pos}+{cursor_pos}c"
                char_end = f"{start_pos}+{cursor_pos + 1}c"
                txt.tag_add("cursor_char", char_start, char_end)

        # Underline the whole current word
        txt.tag_add("current_word", word_start, word_end)

        # Also colour previously committed words when first advancing past them
        if idx > 0:
            self._colour_committed_word(idx - 1)

        txt.configure(state=tk.DISABLED)

        # Update echo bar
        self._typed_var.set(typed)
        self._highlight_current_word()

        # Keyboard: illuminate next expected key
        if overflow:
            next_key = None          # suggest backspace, no key shown
        elif len(typed) < len(target):
            next_key = target[len(typed)]
        else:
            next_key = " "           # word done — press space to advance
        self._keyboard.set_active_key(next_key)

    def _colour_committed_word(self, idx: int) -> None:
        """Apply final per-character colours to a completed word."""
        if idx >= len(self._word_positions) or idx >= len(self._engine.word_states):
            return

        ws = self._engine.word_states[idx]
        start_pos, _ = self._word_positions[idx]
        txt = self._word_text

        for j, target_ch in enumerate(ws.target):
            char_start = f"{start_pos}+{j}c"
            char_end = f"{start_pos}+{j + 1}c"
            for tag in ("pending", "current_word"):
                txt.tag_remove(tag, char_start, char_end)
            if j < len(ws.typed):
                tag = "correct" if ws.typed[j] == target_ch else "error"
            else:
                tag = "error"  # typed too short
            txt.tag_add(tag, char_start, char_end)

    # ------------------------------------------------------------------
    # Timer loop
    # ------------------------------------------------------------------

    def _start_timer_loop(self) -> None:
        self._tick()

    def _tick(self) -> None:
        engine = self._engine
        if engine.state == TestState.FINISHED:
            self._on_session_finish()
            return

        remaining = engine.remaining_seconds
        self._timer_var.set(f"{remaining:.0f}s")
        self._update_stats()

        if remaining <= 0:
            self._on_session_finish()
        else:
            self._timer_id = self.after(TIMER_POLL_MS, self._tick)

    def _cancel_timer(self) -> None:
        if self._timer_id is not None:
            self.after_cancel(self._timer_id)
            self._timer_id = None

    # ------------------------------------------------------------------
    # Stats display
    # ------------------------------------------------------------------

    def _update_stats(self) -> None:
        engine = self._engine
        if engine.state == TestState.IDLE:
            return
        wpm = engine.live_wpm()
        acc = engine.live_accuracy() * 100
        self._wpm_var.set(f"{wpm:.0f} wpm")
        self._acc_var.set(f"{acc:.0f}%")

    # ------------------------------------------------------------------
    # Session end
    # ------------------------------------------------------------------

    def _on_session_finish(self) -> None:
        self._cancel_timer()
        self._keyboard.set_active_key(None)
        engine = self._engine
        if engine.state != TestState.FINISHED:
            engine.finish()

        result = self._app.session_manager.result
        self._cleanup_bindings()

        if result is not None:
            self._app.raise_view("results", result=result)
        else:
            # Fallback: build result directly if callback missed
            result = engine.build_result()
            self._app.raise_view("results", result=result)

    def _cleanup_bindings(self) -> None:
        self._app.unbind("<Key>")
        self._app.unbind("<Escape>")
        self._app.unbind("<Control-r>")
        self._app.unbind("<Control-R>")
        

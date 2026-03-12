"""
Targeted Practice view — practice common letter n-grams.

Like the standard test view but:
  - No hard mode.
  - Word list sourced from grams_list.txt (All), lefthand.txt (Left),
    or righthand.txt (Right), selectable via a chip bar.
  - Mode description updated accordingly.
"""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING, Optional

from application.word_provider import WordProvider
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
    GRAMS_FILE,
    LEFTHAND_FILE,
    RIGHTHAND_FILE,
    TEST_DURATIONS,
    TIMER_POLL_MS,
    WORDS_PER_SESSION,
)
from domain.models import TestState
from ui.widgets.keyboard_heatmap import KeyboardHeatmap

if TYPE_CHECKING:
    from ui.app import App

_VISIBLE_WORDS: int = 80

# Hand-mode labels → source file
_HAND_FILES = {
    "All":   GRAMS_FILE,
    "Left":  LEFTHAND_FILE,
    "Right": RIGHTHAND_FILE,
}

# Pre-load word providers once so switching hands is instant
_PROVIDERS: dict[str, WordProvider] = {
    hand: WordProvider(path) for hand, path in _HAND_FILES.items()
}


class TargetPracticeView(tk.Frame):
    """
    Targeted practice screen — n-gram drill with hand selector.
    """

    def __init__(self, master: "App") -> None:
        super().__init__(master, bg=BG_MAIN)
        self._app = master
        self._timer_id: Optional[str] = None
        self._selected_duration: tk.IntVar = tk.IntVar(value=DEFAULT_DURATION)
        self._selected_hand: str = "All"
        self._dur_buttons: dict[int, tk.Button] = {}
        self._hand_buttons: dict[str, tk.Button] = {}
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # ---- Top stats bar ------------------------------------------
        stats_bar = tk.Frame(self, bg=BG_MAIN, padx=10, pady=6,
                             relief=tk.FLAT, bd=0)
        stats_bar.pack(fill=tk.X)

        # Left info panel: timer / wpm / acc
        left_info = tk.Frame(stats_bar, bg=BG_PANEL, relief=tk.SUNKEN,
                             bd=BD, padx=8, pady=2)
        left_info.pack(side=tk.LEFT)

        self._timer_var = tk.StringVar(value="")
        self._wpm_var   = tk.StringVar(value="")
        self._acc_var   = tk.StringVar(value="")

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

        # ESC / Ctrl+R hints
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
            padx=4,
            pady=2,
            relief=tk.FLAT,
            cursor="arrow",
        ).pack(side=tk.RIGHT, padx=(0, 4))

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

        # ---- Hand selector chips (All / Left / Right) ---------------
        hand_frame = tk.Frame(stats_bar, bg=BG_PANEL, relief=tk.SUNKEN,
                              bd=BD, padx=4, pady=2)
        hand_frame.pack(side=tk.RIGHT, padx=(0, 6))
        for hand in ("All", "Left", "Right"):
            btn = tk.Button(
                hand_frame,
                text=hand,
                font=(FONT_UI, FONT_BUTTON_SIZE - 1),
                relief=tk.RAISED,
                bd=BD,
                cursor="hand2",
                padx=6,
                pady=1,
                command=lambda h=hand: self._on_hand_select(h),
            )
            btn.pack(side=tk.LEFT, padx=2)
            self._hand_buttons[hand] = btn
        self._refresh_hand_chips()

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

        # Text tags
        self._word_text.tag_configure("pending",      foreground=FG_PENDING)
        self._word_text.tag_configure("correct",      foreground=FG_CORRECT)
        self._word_text.tag_configure("error",        foreground=FG_ERROR)
        self._word_text.tag_configure("current_word", foreground=FG_CURRENT, underline=True)
        self._word_text.tag_configure("cursor_char",  background=ACCENT, foreground="#ffffff")
        self._word_text.tag_raise("cursor_char")

        # ---- Typed input display (echo bar) -------------------------
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
        tk.Label(
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
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ---- Keyboard panel (static background) ---------------------
        kbd_panel = tk.Frame(self, bg=BG_PANEL, relief=tk.GROOVE, bd=BD,
                             pady=6)
        kbd_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 4))

        # Mode description — left of the panel
        mode_desc_frame = tk.Frame(kbd_panel, bg=BG_PANEL, relief=tk.SUNKEN,
                                   bd=BD, padx=8, pady=6)
        mode_desc_frame.pack(side=tk.LEFT, anchor="center", padx=(6, 0))
        tk.Label(
            mode_desc_frame,
            text="Practice common\nletter combinations!",
            font=(FONT_UI, 9),
            bg=BG_PANEL,
            fg=FG_MUTED,
            justify=tk.CENTER,
        ).pack()

        # ---- Floating / draggable keyboard --------------------------
        self._kbd_key_size: int = 13
        self._kbd_float = tk.Frame(self, bg=BG_PANEL, relief=tk.RAISED, bd=2)

        _drag_bar = tk.Frame(self._kbd_float, bg=ACCENT, cursor="fleur")
        _drag_bar.pack(fill=tk.X)
        _drag_lbl = tk.Label(
            _drag_bar,
            text="⌨  Keyboard  —  drag to move  |  drag ⇲ to resize",
            font=(FONT_UI, 8),
            bg=ACCENT,
            fg="#ffffff",
            padx=6,
            pady=3,
        )
        _drag_lbl.pack(side=tk.LEFT)

        self._keyboard = KeyboardHeatmap(self._kbd_float, key_size=self._kbd_key_size)
        self._keyboard.pack(padx=6, pady=(2, 20))

        _resize_grip = tk.Label(
            self._kbd_float,
            text="⇲",
            font=(FONT_UI, 12),
            bg=BG_PANEL,
            fg=FG_MUTED,
            cursor="size_nw_se",
        )
        _resize_grip.place(relx=1.0, rely=1.0, anchor="se", x=-2, y=-2)

        # Drag logic
        _d: dict = {"x": 0, "y": 0}

        def _drag_start(e: tk.Event) -> None:
            _d["x"] = e.x
            _d["y"] = e.y

        def _drag_motion(e: tk.Event) -> None:
            x = self._kbd_float.winfo_x() + (e.x - _d["x"])
            y = self._kbd_float.winfo_y() + (e.y - _d["y"])
            pw = self.winfo_width()
            ph = self.winfo_height()
            fw = self._kbd_float.winfo_width()
            fh = self._kbd_float.winfo_height()
            x = max(0, min(x, pw - fw))
            y = max(0, min(y, ph - fh))
            self._kbd_float.place(x=x, y=y)

        for _w in (_drag_bar, _drag_lbl):
            _w.bind("<ButtonPress-1>", _drag_start)
            _w.bind("<B1-Motion>", _drag_motion)

        # Resize logic
        _r: dict = {"x": 0, "y": 0, "w": 0, "h": 0}

        def _resize_start(e: tk.Event) -> None:
            _r["x"] = e.x_root
            _r["y"] = e.y_root
            _r["w"] = self._kbd_float.winfo_width()
            _r["h"] = self._kbd_float.winfo_height()

        def _resize_motion(e: tk.Event) -> None:
            nw = max(260, _r["w"] + (e.x_root - _r["x"]))
            nh = max(130, _r["h"] + (e.y_root - _r["y"]))
            pw = self.winfo_width()
            ph = self.winfo_height()
            nw = min(nw, pw - self._kbd_float.winfo_x())
            nh = min(nh, ph - self._kbd_float.winfo_y())
            self._kbd_float.place(width=nw, height=nh)

        def _resize_release(_e: tk.Event) -> None:
            nw = self._kbd_float.winfo_width()
            new_ks = max(7, min(24, int(13 * nw / 620)))
            if new_ks != self._kbd_key_size:
                self._kbd_key_size = new_ks
                old_data = self._keyboard._heatmap_data.copy()
                old_active = self._keyboard._active_key
                self._keyboard.destroy()
                self._keyboard = KeyboardHeatmap(
                    self._kbd_float, key_size=self._kbd_key_size,
                    heatmap_data=old_data,
                )
                self._keyboard.pack(padx=6, pady=(2, 20))
                if old_active:
                    self._keyboard.set_active_key(old_active)
                _resize_grip.lift()

        _resize_grip.bind("<ButtonPress-1>", _resize_start)
        _resize_grip.bind("<B1-Motion>",     _resize_motion)
        _resize_grip.bind("<ButtonRelease-1>", _resize_release)

        self.after(150, self._place_kbd_initial)

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
    # Floating keyboard placement
    # ------------------------------------------------------------------

    def _place_kbd_initial(self) -> None:
        self.update_idletasks()
        pw = self.winfo_width()
        ph = self.winfo_height()
        fw = self._kbd_float.winfo_reqwidth()
        fh = self._kbd_float.winfo_reqheight()
        x = max(10, (pw - fw) // 2)
        y = max(10, (ph - fh) // 2)
        self._kbd_float.place(x=x, y=y)

    # ------------------------------------------------------------------
    # Chip selectors
    # ------------------------------------------------------------------

    def _on_duration_select(self, duration: int) -> None:
        if hasattr(self, "_engine") and self._engine.state == TestState.RUNNING:
            return
        self._selected_duration.set(duration)
        self._refresh_duration_chips()
        self.on_show()

    def _refresh_duration_chips(self) -> None:
        selected = self._selected_duration.get()
        for dur, btn in self._dur_buttons.items():
            if dur == selected:
                btn.configure(bg=ACCENT, fg="#ffffff", relief=tk.SUNKEN)
            else:
                btn.configure(bg=BG_PANEL, fg=FG_DEFAULT, relief=tk.RAISED)

    def _on_hand_select(self, hand: str) -> None:
        if hasattr(self, "_engine") and self._engine.state == TestState.RUNNING:
            return
        self._selected_hand = hand
        self._refresh_hand_chips()
        self.on_show()

    def _refresh_hand_chips(self) -> None:
        for hand, btn in self._hand_buttons.items():
            if hand == self._selected_hand:
                btn.configure(bg=ACCENT, fg="#ffffff", relief=tk.SUNKEN)
            else:
                btn.configure(bg=BG_PANEL, fg=FG_DEFAULT, relief=tk.RAISED)

    # ------------------------------------------------------------------
    # View lifecycle
    # ------------------------------------------------------------------

    def on_show(self, **_kwargs) -> None:
        """Initialise a fresh session when this view becomes active."""
        self._cancel_timer()
        self._reset_stats_display()
        self._keyboard.reset()

        provider = _PROVIDERS[self._selected_hand]
        words = provider.generate(count=WORDS_PER_SESSION)

        engine = self._app.session_manager.new_session(
            duration=self._selected_duration.get(),
            game_mode="targeted_practice",
            words=words,
        )
        self._engine = engine
        self._word_positions: list[tuple[str, str]] = []

        self._populate_word_display()

        first_target = self._engine.current_word_state.target
        if first_target:
            self._keyboard.set_active_key(first_target[0])

        self._status_var.set("Start typing to begin targeted practice…")

        self._app.bind("<Key>",       self._on_key)
        self._app.bind("<Escape>",    self._on_escape)
        self._app.unbind("<Return>")
        self._app.bind("<Control-r>", self._on_refresh)
        self._app.bind("<Control-R>", self._on_refresh)

        self._app.focus_force()
        self._kbd_float.lift()

    def _reset_stats_display(self) -> None:
        self._timer_var.set("–")
        self._wpm_var.set("")
        self._acc_var.set("")
        self._typed_var.set("")
        self._status_var.set("")

    # ------------------------------------------------------------------
    # Word display
    # ------------------------------------------------------------------

    def _populate_word_display(self) -> None:
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
        idx = self._engine.current_index
        if idx >= len(self._word_positions):
            return
        start, end = self._word_positions[idx]
        self._word_text.tag_remove("current_word", "1.0", tk.END)
        self._word_text.tag_add("current_word", start, end)
        self._word_text.see(start)

    # ------------------------------------------------------------------
    # Keystroke handler
    # ------------------------------------------------------------------

    def _on_key(self, event: tk.Event) -> None:
        char = self._classify_event(event)
        if char is None:
            return

        self._app.settings_manager.play_click()
        self._app.session_manager.process_key(char)
        engine = self._engine

        if engine.state == TestState.FINISHED and self._timer_id is not None:
            self._on_session_finish()
            return

        if engine.state == TestState.RUNNING and self._timer_id is None:
            self._start_timer_loop()
            self._status_var.set("")

        self._refresh_word_display()
        self._update_stats()

    @staticmethod
    def _classify_event(event: tk.Event) -> Optional[str]:
        keysym = event.keysym
        if keysym == "BackSpace":
            return "CtrlBackSpace" if event.state & 4 else "BackSpace"
        if keysym == "space":
            return " "
        if keysym == "Escape":
            return None
        if keysym in (
            "Shift_L", "Shift_R", "Control_L",
            "Alt_L", "Alt_R", "Caps_Lock", "Tab",
            "Return", "Delete", "Up", "Down", "Left", "Right",
            "Home", "End", "Prior", "Next", "Insert", "F1",
            "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9",
            "F10", "F11", "F12", "Super_L", "Super_R",
        ):
            return None
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
        if engine is not None and engine.state == TestState.RUNNING:
            self._app.session_manager.abort_session()

        provider = _PROVIDERS[self._selected_hand]
        words = provider.generate(count=WORDS_PER_SESSION)
        new_engine = self._app.session_manager.new_session(
            duration=self._selected_duration.get(),
            game_mode="targeted_practice",
            words=words,
        )
        self._engine = new_engine
        self._populate_word_display()

        first_target = new_engine.current_word_state.target
        if first_target:
            self._keyboard.set_active_key(first_target[0])

        self._status_var.set("New session started.")

    # ------------------------------------------------------------------
    # Word display refresh
    # ------------------------------------------------------------------

    def _refresh_word_display(self) -> None:
        engine = self._engine
        idx = engine.current_index
        if idx >= len(self._word_positions):
            return

        word_state = engine.current_word_state
        typed  = word_state.typed
        target = word_state.target
        overflow = len(typed) > len(target)

        start_pos, _ = self._word_positions[idx]
        txt = self._word_text
        txt.configure(state=tk.NORMAL)

        word_start, word_end = self._word_positions[idx]
        for tag in ("pending", "correct", "error", "current_word", "cursor_char"):
            txt.tag_remove(tag, word_start, word_end)

        if overflow:
            txt.tag_add("error", word_start, word_end)
        else:
            for j, target_ch in enumerate(target):
                cs = f"{start_pos}+{j}c"
                ce = f"{start_pos}+{j + 1}c"
                if j < len(typed):
                    tag = "correct" if typed[j] == target_ch else "error"
                else:
                    tag = "pending"
                txt.tag_add(tag, cs, ce)

            cursor_pos = len(typed)
            if cursor_pos < len(target):
                txt.tag_add("cursor_char",
                            f"{start_pos}+{cursor_pos}c",
                            f"{start_pos}+{cursor_pos + 1}c")

        txt.tag_add("current_word", word_start, word_end)

        if idx > 0:
            self._colour_committed_word(idx - 1)

        txt.configure(state=tk.DISABLED)
        self._typed_var.set(typed)
        self._highlight_current_word()

        if overflow:
            next_key = None
        elif len(typed) < len(target):
            next_key = target[len(typed)]
        else:
            next_key = " "
        self._keyboard.set_active_key(next_key)

    def _colour_committed_word(self, idx: int) -> None:
        if idx >= len(self._word_positions) or idx >= len(self._engine.word_states):
            return
        ws = self._engine.word_states[idx]
        start_pos, _ = self._word_positions[idx]
        txt = self._word_text
        for j, target_ch in enumerate(ws.target):
            cs = f"{start_pos}+{j}c"
            ce = f"{start_pos}+{j + 1}c"
            for tag in ("pending", "current_word"):
                txt.tag_remove(tag, cs, ce)
            if j < len(ws.typed):
                tag = "correct" if ws.typed[j] == target_ch else "error"
            else:
                tag = "error"
            txt.tag_add(tag, cs, ce)

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
            result = engine.build_result()
            self._app.raise_view("results", result=result)

    def _cleanup_bindings(self) -> None:
        self._app.unbind("<Key>")
        self._app.unbind("<Escape>")
        self._app.unbind("<Control-r>")
        self._app.unbind("<Control-R>")

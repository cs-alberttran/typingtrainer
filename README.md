# TypeTrainer

A classic, adaptive desktop typing trainer built with Python and Tkinter.

Inspired by [Monkeytype](https://monkeytype.com) and [Keybr](https://keybr.com), TypeTrainer provides a clean, responsive timed typing test with a fully extensible architecture designed to evolve into an ML-powered adaptive trainer.

---

## Screenshots

```
┌──────────────────────────────────────────────────────┐
│  TypeTrainer                              ESC — quit  │
│  28s   87 wpm   94%                                   │
│ ┌────────────────────────────────────────────────────┐│
│ │ the quick brown fox jumps over the lazy dog        ││
│ │ people into year your good some could them see oth ││
│ │ er than then now look only come its over think     ││
│ └────────────────────────────────────────────────────┘│
│  typing: quicK_                                       │
└──────────────────────────────────────────────────────┘
```

---

## Requirements

- Python **3.10+**
- No third-party packages required — Tkinter is included with standard Python

> **Windows users:** Tkinter ships with the official Python installer.  
> **Linux users:** Install via `sudo apt install python3-tk` if missing.

---

## Quick Start

```bash
# 1. Clone / download the repository
git clone https://github.com/cs-alberttran/typetrainer.git
cd typetrainer

# 2. (Optional) create a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 3. Run the app
python main.py
```

The app requires no additional installation steps.

---

## Running Tests

```bash
# From the project root
python -m pytest tests/ -v
```

All tests use only the standard library and pytest. Install pytest if needed:

```bash
pip install pytest
```

---

## Project Structure

```
typetrainer/
│
├── main.py                     # Entry point — wires all layers together
├── config.py                   # All constants and tuneable values
├── words.txt                   # Top-200 common English word list
│
├── domain/                     # Pure business logic — no I/O, no UI
│   ├── models.py               # Data classes: SessionResult, KeystrokeEvent, WordState …
│   ├── typing_engine.py        # Core engine: keystroke processing, WPM, accuracy
│   └── analytics.py            # Per-key stats aggregator (Phase 1 scaffold)
│
├── application/                # Orchestration — coordinates domain + infrastructure
│   ├── session.py              # SessionManager: lifecycle, callback routing
│   ├── word_provider.py        # Word list loading and randomisation
│   └── adaptive_engine.py      # Adaptive lesson generator (Phase 1 stub)
│
├── infrastructure/             # I/O adapters
│   └── persistence.py          # JSON-based local storage for results & analytics
│
├── ui/                         # Tkinter presentation layer
│   ├── app.py                  # Main window with frame-stack navigation
│   ├── views/
│   │   ├── home_view.py        # Start screen with duration selector
│   │   ├── test_view.py        # Live typing test
│   │   └── results_view.py     # Post-test results summary
│   └── widgets/
│       └── keyboard_heatmap.py # Heatmap widget (Phase 1 stub)
│
├── data/                       # Auto-created at runtime
│   ├── results.json            # Persisted session results
│   └── analytics.json          # Per-key performance data
│
└── tests/
    ├── test_typing_engine.py   # Domain engine unit tests
    ├── test_word_provider.py   # Word provider unit tests
    └── test_session.py         # Session manager integration tests
```

---

## Architecture Overview

TypeTrainer follows a strict **layered architecture** with clear dependency rules:

```
UI Layer  →  Application Layer  →  Domain Layer
               ↓
         Infrastructure Layer
```

| Layer          | Responsibility                                    | Dependencies          |
|----------------|---------------------------------------------------|-----------------------|
| `domain/`      | Core rules: scoring, state machine, data models   | None                  |
| `application/` | Session lifecycle, word generation, orchestration | `domain/`             |
| `infrastructure/` | Persistence (JSON read/write)                  | `domain/`             |
| `ui/`          | Tkinter views, event binding, visual rendering    | `application/`, `domain/` |

**Key principle:** The domain and application layers are fully testable without Tkinter.

---

## WPM Calculation

TypeTrainer uses the **industry-standard formula** as used by Monkeytype and TypeRacer:

```
net_WPM = (correct_characters / 5) / elapsed_minutes
raw_WPM = (total_characters / 5) / elapsed_minutes
```

Where one "word" = 5 characters (includes spaces between committed words).

---

## Controls

| Key       | Action                               |
|-----------|--------------------------------------|
| Any char  | Type (auto-starts the timer)         |
| `Space`   | Submit current word, advance to next |
| `Backspace` | Delete last character in current word |
| `Esc`     | Abort test, return to home screen    |
| `Enter`   | On home/results — start / retry test |

---

## Configuration

All constants are centralised in `config.py`:

| Constant         | Default   | Description                              |
|------------------|-----------|------------------------------------------|
| `TEST_DURATIONS` | 15,30,60,120 | Available test lengths (seconds)      |
| `DEFAULT_DURATION` | 30      | Pre-selected duration                    |
| `WORDS_PER_SESSION` | 200    | Words pre-generated per session          |
| `CHARS_PER_WORD` | 5         | Standard WPM word length                 |
| `TIMER_POLL_MS`  | 100       | Timer refresh interval (ms)              |
| `WORDS_FILE`     | words.txt | Path to word list                        |

---

## Roadmap

### Phase 1 (current — MVP)
- [x] Timed typing test (Monkeytype style)
- [x] Real-time WPM and accuracy
- [x] Correct / incorrect character colouring
- [x] Local result persistence
- [x] Personal best tracking
- [x] Modular, extensible architecture

### Phase 2 (planned)
- [ ] Per-key analytics visualisation (heatmap)
- [ ] Keybr-style adaptive lessons based on weak keys
- [ ] Spaced-repetition word scheduling
- [ ] Historical progress graph

### Phase 3 (future)
- [ ] ML-based difficulty prediction per user
- [ ] Custom word lists / code snippets mode
- [ ] Online leaderboard (optional)

---

## Development

```bash
# Run tests with coverage report
pip install pytest pytest-cov
python -m pytest tests/ -v --cov=. --cov-report=term-missing

# Check code style (no config files required)
pip install flake8
flake8 . --max-line-length=100 --exclude=.venv
```

---

## Design Decisions

**Why Tkinter?**  
No external dependencies, ships with Python, lightweight, and perfectly appropriate for a desktop utility application of this scope.

**Why frame-stack navigation?**  
Simpler than a Router or controller pattern for three views. Each view is self-contained; `App.raise_view()` is the only coupling point.

**Why JSON persistence?**  
Zero dependencies, human-readable, and sufficient for a local single-user application. The `ResultsRepository` and `AnalyticsRepository` classes isolate the format so switching to SQLite in Phase 2 requires only changing those classes.

**Why not an Entry widget for input?**  
Binding `<Key>` at the window level gives the engine complete control over which characters reach it, avoids focus management headaches, and prevents characters from appearing in a visible Entry before we've had a chance to process them.

---

## License

MIT — see `LICENSE` for details.

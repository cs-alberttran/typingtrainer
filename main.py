"""
TypingTrainer — entry point.

Wires together all layers and launches the Tkinter application:

  Persistence   →   SessionManager   →   App (views)
  (ResultsRepo)     (WordProvider)        (Home / Test / Results)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
import tkinter as tk
from enum import IntEnum

# Ensure the project root is on sys.path so all subpackages resolve correctly
# regardless of how the script is invoked.
_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Typing Trainer")


def main() -> None:
    """Application entry point — create all objects and start the event loop."""
    # Settings must be created and applied BEFORE any view module is imported
    # so that `from config import …` statements in views see the correct values.
    from application.settings_manager import SettingsManager
    settings_manager = SettingsManager()
    settings_manager.apply_to_config()

    from application.session import SessionManager
    from application.word_provider import WordProvider
    from infrastructure.persistence import AnalyticsRepository, ResultsRepository
    from ui.app import App
    from ui.views.home_view import HomeView
    from ui.views.results_view import ResultsView
    from ui.    views.test_view import TestView
    from ui.views.settings_view import SettingsView
    from ui.views.targetpractice_view import TargetPracticeView
    from ui.views.number_view import NumberView

    # ---- Infrastructure -----------------------------------------------
    results_repo = ResultsRepository()
    analytics_repo = AnalyticsRepository()

    # ---- Persistence callback -----------------------------------------
    def persist_result(result) -> None:
        results_repo.save(result)
        logger.info(
            "Result saved: %.1f WPM  %.0f%% accuracy",
            result.wpm,
            result.accuracy_pct,
        )

    # ---- Application layer --------------------------------------------
    session_manager = SessionManager(
        word_provider=WordProvider(),
        persistence=persist_result,
    )

    # ---- UI layer -----------------------------------------------------
    app = App(
        session_manager=session_manager,
        results_repository=results_repo,
        settings_manager=settings_manager,
    )
    
    home_view = HomeView(master=app)
    test_view = TestView(master=app)
    results_view = ResultsView(master=app)
    settings_view = SettingsView(master=app)
    target_practice_view = TargetPracticeView(master=app)
    number_view = NumberView(master=app)

    app.add_view("home",            home_view)
    app.add_view("test",            test_view)
    app.add_view("results",         results_view)
    app.add_view("settings",        settings_view)
    app.add_view("target_practice",  target_practice_view)
    app.add_view("number",          number_view)

    app.raise_view("home")

    logger.info("TypingTrainer started.")
    app.mainloop()
    logger.info("TypingTrainer exited.")


if __name__ == "__main__":
    main()  
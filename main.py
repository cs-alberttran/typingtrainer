"""
TypeTrainer — entry point.

Wires together all layers and launches the Tkinter application:

  Persistence   →   SessionManager   →   App (views)
  (ResultsRepo)     (WordProvider)        (Home / Test / Results)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

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
logger = logging.getLogger("typetrainer")


def main() -> None:
    """Application entry point — create all objects and start the event loop."""
    from application.session import SessionManager
    from application.word_provider import WordProvider
    from infrastructure.persistence import AnalyticsRepository, ResultsRepository
    from ui.app import App
    from ui.views.home_view import HomeView
    from ui.views.results_view import ResultsView
    from ui.views.test_view import TestView

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
    app = App(session_manager=session_manager, results_repository=results_repo)

    home_view = HomeView(master=app)
    test_view = TestView(master=app)
    results_view = ResultsView(master=app)

    app.add_view("home", home_view)
    app.add_view("test", test_view)
    app.add_view("results", results_view)

    app.raise_view("home")

    logger.info("TypeTrainer started.")
    app.mainloop()
    logger.info("TypeTrainer exited.")


if __name__ == "__main__":
    main()

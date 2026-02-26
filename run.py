"""
Application entrypoint.

Startup sequence:
  1. Initialise DB tables
  2. Train model if no saved artifacts exist
  3. Load inference artifacts
  4. Start APScheduler (collector, preprocessor, inference, nightly retrain)
  5. Start Uvicorn (FastAPI + frontend)
"""
import logging
import sys

import uvicorn

import app_config
from database.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main():
    # 1. Database
    logger.info("Initialising database...")
    init_db()
    logger.info("Database ready.")

    # 2. Model — train if no saved artifacts
    from model.trainer import model_exists, train
    if not model_exists():
        logger.info("No saved model found. Running initial training...")
        result = train(force=False)
        if result["status"] == "failed":
            logger.warning(
                "Initial training skipped: %s. "
                "The collector will gather data and the nightly job will train when enough data is available.",
                result.get("reason"),
            )
        else:
            logger.info("Initial training complete: %s", result)
    else:
        logger.info("Saved model found — skipping initial training.")

    # 3. Load inference artifacts (best-effort; will retry on first score run)
    from model.inference import reload_artifacts
    reload_artifacts()

    # 4. Scheduler
    logger.info("Starting scheduler...")
    from scheduler.tasks import start_scheduler
    scheduler = start_scheduler()
    logger.info("Scheduler running. Jobs: %s", [j.id for j in scheduler.get_jobs()])

    # 5. Uvicorn
    logger.info(
        "Starting server at http://%s:%d  (Ctrl+C to stop)",
        app_config.SERVER_HOST,
        app_config.SERVER_PORT,
    )
    uvicorn.run(
        "api.main:app",
        host=app_config.SERVER_HOST,
        port=app_config.SERVER_PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()

"""
APScheduler job definitions.

Jobs wired here:
  1. collect_jmx      — every POLL_INTERVAL_SECONDS seconds
  2. process_metrics  — every PROCESS_INTERVAL_SECONDS seconds
  3. run_inference    — every INFERENCE_INTERVAL_MINUTES minutes
  4. retrain_model    — nightly via RETRAIN_CRON (default 2 AM)
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

import app_config

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


# --- job callbacks (thin wrappers so imports are deferred until first call) ---

def _job_collect():
    from collector.jmx_collector import collect_once
    try:
        collect_once()
    except Exception as exc:
        logger.error("[collect_jmx] Unhandled error: %s", exc)


def _job_process():
    from processor.metrics_processor import process_pending
    try:
        n = process_pending()
        if n:
            logger.info("[process_metrics] Wrote %d processed rows.", n)
    except Exception as exc:
        logger.error("[process_metrics] Unhandled error: %s", exc)


def _job_inference():
    from model.inference import score_pending
    try:
        n = score_pending()
        if n:
            logger.info("[run_inference] Scored %d timestamps.", n)
    except Exception as exc:
        logger.error("[run_inference] Unhandled error: %s", exc)


def _job_retrain():
    from model.trainer import train
    from model.inference import reload_artifacts
    logger.info("[retrain_model] Starting scheduled retraining...")
    try:
        result = train(force=True)
        logger.info("[retrain_model] Result: %s", result)
        if result.get("status") == "success":
            reload_artifacts()
    except Exception as exc:
        logger.error("[retrain_model] Unhandled error: %s", exc)


def start_scheduler() -> BackgroundScheduler:
    """Create, configure, and start the background scheduler. Returns the instance."""
    global _scheduler

    scheduler = BackgroundScheduler(timezone="UTC")

    # 1. JMX collector
    scheduler.add_job(
        _job_collect,
        trigger=IntervalTrigger(seconds=app_config.POLL_INTERVAL_SECONDS),
        id="collect_jmx",
        name="JMX Collector",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # 2. Preprocessor
    scheduler.add_job(
        _job_process,
        trigger=IntervalTrigger(seconds=app_config.PROCESS_INTERVAL_SECONDS),
        id="process_metrics",
        name="Metrics Preprocessor",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # 3. Inference
    scheduler.add_job(
        _job_inference,
        trigger=IntervalTrigger(minutes=app_config.INFERENCE_INTERVAL_MINUTES),
        id="run_inference",
        name="Anomaly Inference",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # 4. Nightly retraining
    cron_parts = app_config.RETRAIN_CRON.split()  # "0 2 * * *"
    scheduler.add_job(
        _job_retrain,
        trigger=CronTrigger(
            minute=cron_parts[0],
            hour=cron_parts[1],
            day=cron_parts[2],
            month=cron_parts[3],
            day_of_week=cron_parts[4],
            timezone="UTC",
        ),
        id="retrain_model",
        name="Nightly Model Retraining",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()
    _scheduler = scheduler
    logger.info("Scheduler started with %d jobs.", len(scheduler.get_jobs()))
    return scheduler


def get_scheduler() -> BackgroundScheduler | None:
    return _scheduler


def trigger_retrain_now():
    """Trigger an immediate retraining run (called from the API)."""
    if _scheduler:
        _scheduler.modify_job("retrain_model", next_run_time=None)
    _job_retrain()

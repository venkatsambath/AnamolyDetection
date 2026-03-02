"""Database retention cleanup: delete rows older than retention_days."""
from datetime import datetime, timedelta

import app_config
from database.db import SessionLocal
from database.models import AnomalyEvent, ProcessedMetric, RawMetric, ModelVersion


def run_retention_cleanup() -> dict:
    """
    Delete rows older than DATABASE_RETENTION_DAYS from all timestamped tables.
    Returns counts of deleted rows per table.
    """
    cutoff = datetime.utcnow() - timedelta(days=app_config.DATABASE_RETENTION_DAYS)
    db = SessionLocal()
    deleted = {}
    try:
        # raw_metrics: use collected_at
        raw_count = db.query(RawMetric).filter(RawMetric.collected_at < cutoff).delete()
        deleted["raw_metrics"] = raw_count

        # processed_metrics: use timestamp
        proc_count = db.query(ProcessedMetric).filter(ProcessedMetric.timestamp < cutoff).delete()
        deleted["processed_metrics"] = proc_count

        # anomaly_events: use timestamp
        event_count = db.query(AnomalyEvent).filter(AnomalyEvent.timestamp < cutoff).delete()
        deleted["anomaly_events"] = event_count

        # model_versions: use trained_at
        model_count = db.query(ModelVersion).filter(ModelVersion.trained_at < cutoff).delete()
        deleted["model_versions"] = model_count

        db.commit()
    finally:
        db.close()

    return deleted

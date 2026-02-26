"""GET /api/anomalies — return anomaly events for a given time window."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import AnomalyEvent

router = APIRouter()


@router.get("/anomalies")
def get_anomalies(
    from_ts: Optional[str] = Query(None, alias="from"),
    to_ts: Optional[str] = Query(None, alias="to"),
    only_anomalies: bool = Query(False, description="When true, return only flagged anomalies"),
    db: Session = Depends(get_db),
):
    """Return anomaly event rows (reconstruction errors + flags) for the window."""
    query = db.query(AnomalyEvent).order_by(AnomalyEvent.timestamp)

    if from_ts:
        query = query.filter(AnomalyEvent.timestamp >= datetime.fromisoformat(from_ts))
    if to_ts:
        query = query.filter(AnomalyEvent.timestamp <= datetime.fromisoformat(to_ts))
    if only_anomalies:
        query = query.filter(AnomalyEvent.is_anomaly == True)  # noqa: E712

    rows = query.all()
    result = [
        {
            "timestamp": r.timestamp.isoformat(),
            "reconstruction_error": r.reconstruction_error,
            "is_anomaly": r.is_anomaly,
            "explanation": r.explanation_json,
        }
        for r in rows
    ]

    return {
        "count": len(result),
        "anomaly_count": sum(1 for r in result if r["is_anomaly"]),
        "data": result,
    }

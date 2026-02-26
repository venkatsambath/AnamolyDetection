"""GET /api/metrics — return processed metric rows for a given time window."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import ProcessedMetric
from model.constants import METRIC_COLUMNS_AVGTIME

router = APIRouter()


@router.get("/metrics")
def get_metrics(
    from_ts: Optional[str] = Query(None, alias="from", description="ISO-8601 start datetime"),
    to_ts: Optional[str] = Query(None, alias="to", description="ISO-8601 end datetime"),
    db: Session = Depends(get_db),
):
    """Return processed metric rows within the requested window."""
    query = db.query(ProcessedMetric).order_by(ProcessedMetric.timestamp)

    if from_ts:
        query = query.filter(ProcessedMetric.timestamp >= datetime.fromisoformat(from_ts))
    if to_ts:
        query = query.filter(ProcessedMetric.timestamp <= datetime.fromisoformat(to_ts))

    rows = query.all()
    result = []
    for r in rows:
        row = {"timestamp": r.timestamp.isoformat()}
        for col in METRIC_COLUMNS_AVGTIME:
            row[col] = getattr(r, col)
        result.append(row)

    return {"count": len(result), "data": result}

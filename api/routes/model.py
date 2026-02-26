"""
GET  /api/model/status     — return the active model version info.
POST /api/model/train      — train on a specific baseline time window (synchronous).
POST /api/model/retrain    — trigger a full retrain on all data (background thread).
"""
import threading

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import ModelVersion

router = APIRouter()


class TrainRequest(BaseModel):
    from_ts: str
    to_ts: str


@router.get("/model/status")
def model_status(db: Session = Depends(get_db)):
    """Return info about the currently active model version."""
    active = (
        db.query(ModelVersion)
        .filter(ModelVersion.status == "active")
        .order_by(ModelVersion.trained_at.desc())
        .first()
    )
    if not active:
        return {"status": "no_model", "message": "No trained model found yet."}

    return {
        "status": "active",
        "version_id": active.id,
        "trained_at": active.trained_at.isoformat(),
        "threshold": active.threshold,
        "num_rows_trained_on": active.num_rows_trained_on,
        "epochs_run": active.epochs_run,
        "baseline_from": active.baseline_from,
        "baseline_to": active.baseline_to,
    }


@router.post("/model/train")
def train_on_baseline(req: TrainRequest):
    """
    Train the LSTM model using only the rows in the specified baseline window.
    This is a synchronous call — it blocks until training completes and returns
    the result so the UI can confirm success before the engineer proceeds to
    the analysis step.
    """
    from model.trainer import train
    from model.inference import reload_artifacts

    result = train(force=True, from_ts=req.from_ts, to_ts=req.to_ts)

    if result.get("status") == "failed":
        raise HTTPException(status_code=422, detail=result.get("reason", "Training failed."))

    if result.get("status") == "success":
        reload_artifacts()

    return result


@router.post("/model/retrain")
def trigger_retrain():
    """
    Fire off a full retrain (all data, no time window) in a background thread.
    Used by the nightly scheduler and for manual ad-hoc full retrains.
    """
    def _run():
        from model.trainer import train
        from model.inference import reload_artifacts
        result = train(force=True)
        if result.get("status") == "success":
            reload_artifacts()

    thread = threading.Thread(target=_run, daemon=True, name="on-demand-retrain")
    thread.start()
    return {"status": "started", "message": "Retraining started in background. Poll /api/model/status for completion."}

"""
POST /api/report — score the analysis window on-demand against the current model
(trained on the baseline window) and return a full report.

No pre-scored DB rows are required — inference runs fresh on every call so the
results always reflect the model that was just trained on the user's baseline.
"""
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import app_config
from model.inference import artifacts_ready, score_window
from model.trainer import plot_jmx_metrics, plot_reconstruction_error

router = APIRouter()


class ReportRequest(BaseModel):
    from_ts: str
    to_ts: str
    key_metrics: list[str] = [
        "RpcProcessingTimeAvgTime",
        "RpcQueueTimeAvgTime",
        "ThreadsBlocked",
    ]
    threshold_override: float | None = None


@router.post("/report")
def generate_report(req: ReportRequest):
    """
    Score the analysis window against the current model and return charts + explanations.
    The model must have been trained on a baseline window first via POST /api/model/train.
    """
    if not artifacts_ready():
        raise HTTPException(
            status_code=409,
            detail="No model loaded. Complete Step 1: train the model on a baseline window first.",
        )

    result = score_window(req.from_ts, req.to_ts, threshold_override=req.threshold_override)

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    # Build anomaly scores DataFrame for the reconstruction error chart
    anomaly_scores_df = pd.DataFrame(result["anomaly_scores"]).set_index("timestamp")

    recon_chart = plot_reconstruction_error(
        anomaly_scores_df,
        result["threshold"],
        app_config.ANOMALY_THRESHOLD_PERCENTILE,
    )

    # Build key metrics chart from the raw (unscaled) metric values
    metrics_chart = None
    df_metrics = result["df_metrics"]
    valid_key = [m for m in req.key_metrics if m in df_metrics.columns]
    if valid_key:
        metrics_chart = plot_jmx_metrics(df_metrics, valid_key)

    return {
        "status": "ok",
        "window": {"from": req.from_ts, "to": req.to_ts},
        "total_scored": result["total_scored"],
        "anomaly_count": result["anomaly_count"],
        "threshold": result["threshold"],
        "model_threshold": result.get("model_threshold", result["threshold"]),
        "reconstruction_error_chart": recon_chart,
        "metrics_chart": metrics_chart,
        "anomalies": result["anomaly_list"],
    }

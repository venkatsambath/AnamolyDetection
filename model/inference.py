# Copyright 2025 VenkatSambath
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Inference Engine — loads saved artifacts and scores new processed_metrics rows.

Inference pipeline (scaler.transform → model.predict → mse → Is_Anomaly) and
explain_anomaly() are preserved verbatim from the Kaggle notebook.
Results are written to the anomaly_events table.
"""
import json
import logging
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model

import app_config
from database.db import SessionLocal
from database.models import AnomalyEvent, ProcessedMetric
from model.constants import METRIC_COLUMNS_AVGTIME, METRIC_REASONS_AVGTIME
from model.lstm_autoencoder import create_sequences
from model.trainer import MODEL_PATH, SCALER_PATH, THRESHOLD_PATH

logger = logging.getLogger(__name__)

_model = None
_scaler = None
_threshold = None


def _load_artifacts() -> bool:
    """Load model, scaler, threshold from disk. Returns True on success."""
    global _model, _scaler, _threshold
    try:
        _model = load_model(MODEL_PATH)
        _scaler = joblib.load(SCALER_PATH)
        _threshold = joblib.load(THRESHOLD_PATH)
        logger.info("Inference artifacts loaded. Threshold=%.6f", _threshold)
        return True
    except Exception as exc:
        logger.warning("Could not load inference artifacts: %s", exc)
        return False


def reload_artifacts() -> bool:
    """Force-reload artifacts (call after retraining)."""
    return _load_artifacts()


def artifacts_ready() -> bool:
    return _model is not None and _scaler is not None and _threshold is not None


# --- preserved verbatim from Kaggle notebook ---
def explain_anomaly(sequence_scaled, reconstructed_sequence_scaled,
                    metric_columns, metric_reasons, original_df_metrics_at_anomaly,
                    peak_in_window=None, range_in_window=None):
    """
    Compares the original (scaled) and reconstructed (scaled) sequence to
    identify contributing metrics and generates an explanation dict.
    original_df_metrics_at_anomaly: values at the sequence start (timestamp).
    peak_in_window: optional dict of max values across the full sequence window.
    range_in_window: optional dict of (max - min) per metric; used to filter flat metrics.
    """
    diff = np.abs(sequence_scaled - reconstructed_sequence_scaled)
    feature_contributions = np.mean(diff, axis=0)
    sorted_contributions_idx = np.argsort(feature_contributions)[::-1]

    top_contributing_metrics = []
    contribution_threshold = np.mean(feature_contributions) * 1.5

    if np.max(feature_contributions) > 0:
        for idx in sorted_contributions_idx:
            metric_name = metric_columns[idx]
            contribution_score = feature_contributions[idx]
            if contribution_score >= contribution_threshold or (
                not top_contributing_metrics and idx == sorted_contributions_idx[0]
            ):
                top_contributing_metrics.append((metric_name, float(contribution_score)))

    if not top_contributing_metrics:
        return {"summary": "No specific major contributing metrics identified.", "metrics": []}

    result_metrics = []
    actual_values = original_df_metrics_at_anomaly

    # Skip metrics where both actual and peak are zero — high impact is just scaled-space artifact.
    ZERO_EPS = 1e-6
    # Skip metrics with negligible range (e.g. ThreadsWaiting 31-32) — high impact is scaler artifact.
    MIN_RANGE = 2.0

    for metric_name, score in top_contributing_metrics:
        reason_info = metric_reasons.get(metric_name, {})
        actual_value = actual_values.get(metric_name, "N/A")
        if isinstance(actual_value, (int, float, np.floating)):
            actual_value = float(actual_value)
        peak_value = None
        if peak_in_window and metric_name in peak_in_window:
            pv = peak_in_window[metric_name]
            if isinstance(pv, (int, float, np.floating)):
                peak_value = float(pv)

        actual_near_zero = isinstance(actual_value, float) and abs(actual_value) < ZERO_EPS
        peak_near_zero = peak_value is not None and abs(peak_value) < ZERO_EPS
        if actual_near_zero and peak_near_zero:
            continue  # Don't list metrics with no real activity (both 0)

        range_val = range_in_window.get(metric_name) if range_in_window else None
        if range_val is not None and isinstance(range_val, (int, float)) and float(range_val) < MIN_RANGE:
            continue  # Don't list metrics that barely changed (e.g. ThreadsWaiting 31→32)

        entry = {
            "metric": metric_name,
            "actual_value": actual_value,
            "impact_score": round(score, 6),
            "description": reason_info.get("description", ""),
            "high_impact": reason_info.get("high_impact", ""),
            "possible_causes": reason_info.get("possible_causes", []),
        }
        if peak_value is not None:
            entry["peak_in_window"] = peak_value
        result_metrics.append(entry)

    return {
        "summary": "Bad performance detected! Here's why:",
        "metrics": result_metrics,
    }


def score_window(from_ts, to_ts, threshold_override: float | None = None) -> dict:
    """
    Run inference on a specific analysis window on-demand.
    Does NOT write to the DB — returns a result dict the report endpoint can use directly.
    This is the core of the "baseline vs analysis" workflow:
      the model was trained on the baseline; this scores the analysis window against it.

    threshold_override: if provided, use this MSE value instead of the model's learned threshold.
    """
    from datetime import datetime as dt
    from database.models import ProcessedMetric

    if not artifacts_ready():
        if not _load_artifacts():
            return {"error": "Model artifacts not loaded. Train on a baseline window first."}

    db = SessionLocal()
    try:
        query = db.query(ProcessedMetric).order_by(ProcessedMetric.timestamp)
        if from_ts:
            ts = dt.fromisoformat(from_ts) if isinstance(from_ts, str) else from_ts
            query = query.filter(ProcessedMetric.timestamp >= ts)
        if to_ts:
            ts = dt.fromisoformat(to_ts) if isinstance(to_ts, str) else to_ts
            query = query.filter(ProcessedMetric.timestamp <= ts)
        rows = query.all()
    finally:
        db.close()

    if not rows:
        return {"error": "No processed data found in the analysis window."}

    records = []
    for r in rows:
        row = {col: getattr(r, col) for col in METRIC_COLUMNS_AVGTIME}
        row["timestamp"] = r.timestamp
        records.append(row)

    df = pd.DataFrame(records).set_index("timestamp")
    metric_cols = [c for c in METRIC_COLUMNS_AVGTIME if c in df.columns]
    df_metrics = df[metric_cols].copy().fillna(df[metric_cols].median())

    if len(df_metrics) < app_config.SEQUENCE_LENGTH:
        return {
            "error": f"Analysis window has only {len(df_metrics)} data points; "
                     f"need at least {app_config.SEQUENCE_LENGTH} to form one sequence."
        }

    full_data_scaled = _scaler.transform(df_metrics)
    full_data_scaled_df = pd.DataFrame(full_data_scaled, columns=metric_cols, index=df_metrics.index)

    X_full = create_sequences(full_data_scaled_df, app_config.SEQUENCE_LENGTH)
    X_pred = _model.predict(X_full, verbose=0)
    mse = np.mean(np.power(X_full - X_pred, 2), axis=(1, 2))

    # Label each score at the START of its window so the timestamp reflects
    # when the anomalous pattern first appeared, not when the window closed.
    anomaly_timestamps = full_data_scaled_df.index[:len(mse)]

    effective_threshold = float(threshold_override) if threshold_override is not None else float(_threshold)

    anomaly_scores = []
    anomaly_list = []

    for i, (ts, err) in enumerate(zip(anomaly_timestamps, mse)):
        is_anomaly = bool(err > effective_threshold)
        explanation = None
        if is_anomaly:
            # Value at sequence start (matches displayed timestamp).
            actual_vals = {col: float(df_metrics.iloc[i][col]) for col in metric_cols}
            # Peak and range across the full 30-step window.
            window_slice = df_metrics.iloc[i:i + app_config.SEQUENCE_LENGTH]
            peak_vals = {col: float(window_slice[col].max()) for col in metric_cols}
            range_vals = {col: float(window_slice[col].max() - window_slice[col].min()) for col in metric_cols}
            explanation = explain_anomaly(
                X_full[i], X_pred[i], metric_cols, METRIC_REASONS_AVGTIME,
                actual_vals, peak_in_window=peak_vals, range_in_window=range_vals,
            )
            # Add window timestamp range for clarity
            window_end_ts = df_metrics.index[i + app_config.SEQUENCE_LENGTH - 1]
            explanation["window_start"] = ts.isoformat()
            explanation["window_end"] = (
                window_end_ts.isoformat()
                if hasattr(window_end_ts, "isoformat")
                else str(window_end_ts)
            )
        anomaly_scores.append({
            "timestamp": ts,
            "Reconstruction_Error": float(err),
            "Is_Anomaly": is_anomaly,
        })
        if is_anomaly:
            anomaly_list.append({
                "timestamp": ts.isoformat(),
                "reconstruction_error": round(float(err), 6),
                "explanation": explanation,
            })

    return {
        "anomaly_scores": anomaly_scores,  # list of dicts for charting
        "df_metrics": df_metrics,           # DataFrame for metric chart
        "metric_cols": metric_cols,
        "threshold": effective_threshold,
        "model_threshold": float(_threshold),
        "anomaly_list": anomaly_list,
        "total_scored": len(mse),
        "anomaly_count": len(anomaly_list),
    }


def score_pending() -> int:
    """
    Score all unscored processed_metrics rows and write AnomalyEvent rows.
    Returns number of rows scored.
    """
    if not artifacts_ready():
        if not _load_artifacts():
            logger.warning("Skipping inference: artifacts not ready.")
            return 0

    db = SessionLocal()
    scored_count = 0
    try:
        unscored = (
            db.query(ProcessedMetric)
            .filter(ProcessedMetric.scored == False)  # noqa: E712
            .order_by(ProcessedMetric.timestamp)
            .all()
        )

        if not unscored:
            return 0

        # Build DataFrame of all unscored rows for sequence windowing
        records = []
        for r in unscored:
            row = {col: getattr(r, col) for col in METRIC_COLUMNS_AVGTIME}
            row["timestamp"] = r.timestamp
            row["_id"] = r.id
            records.append(row)

        df = pd.DataFrame(records).set_index("timestamp")
        ids = df.pop("_id").tolist()

        metric_cols = [c for c in METRIC_COLUMNS_AVGTIME if c in df.columns]
        df_metrics = df[metric_cols].copy().fillna(df[metric_cols].median())

        if len(df_metrics) < app_config.SEQUENCE_LENGTH:
            logger.info("Not enough rows (%d) to form a sequence of length %d.",
                        len(df_metrics), app_config.SEQUENCE_LENGTH)
            return 0

        # --- Kaggle notebook inference pipeline (preserved verbatim) ---
        full_data_scaled = _scaler.transform(df_metrics)
        full_data_scaled_df = pd.DataFrame(full_data_scaled, columns=metric_cols,
                                            index=df_metrics.index)

        X_full = create_sequences(full_data_scaled_df, app_config.SEQUENCE_LENGTH)
        if X_full.shape[0] == 0:
            return 0

        X_pred = _model.predict(X_full, verbose=0)
        mse = np.mean(np.power(X_full - X_pred, 2), axis=(1, 2))

        # Label each score at the START of its window (same convention as score_window).
        anomaly_timestamps = full_data_scaled_df.index[:len(mse)]

        for i, (ts, err) in enumerate(zip(anomaly_timestamps, mse)):
            is_anomaly = bool(err > _threshold)
            explanation = None
            if is_anomaly:
                actual_vals = {col: float(df_metrics.iloc[i][col]) for col in metric_cols}
                window_slice = df_metrics.iloc[i:i + app_config.SEQUENCE_LENGTH]
                peak_vals = {col: float(window_slice[col].max()) for col in metric_cols}
                range_vals = {col: float(window_slice[col].max() - window_slice[col].min()) for col in metric_cols}
                explanation = explain_anomaly(
                    X_full[i],
                    X_pred[i],
                    metric_cols,
                    METRIC_REASONS_AVGTIME,
                    actual_vals,
                    peak_in_window=peak_vals,
                    range_in_window=range_vals,
                )
                window_end_ts = df_metrics.index[i + app_config.SEQUENCE_LENGTH - 1]
                explanation["window_start"] = ts.isoformat()
                explanation["window_end"] = (
                    window_end_ts.isoformat()
                    if hasattr(window_end_ts, "isoformat")
                    else str(window_end_ts)
                )

            event = AnomalyEvent(
                timestamp=ts,
                reconstruction_error=float(err),
                is_anomaly=is_anomaly,
                explanation_json=explanation,
            )
            db.add(event)

        # Mark all rows as scored
        for rid in ids:
            db.query(ProcessedMetric).filter(ProcessedMetric.id == rid).update({"scored": True})

        db.commit()
        scored_count = len(mse)
        logger.info("Inference complete: scored %d timestamps, %d anomalies detected.",
                    scored_count, int(sum(mse > _threshold)))
    except Exception as exc:
        db.rollback()
        logger.error("Inference error: %s", exc)
    finally:
        db.close()

    return scored_count

"""
Model Trainer — wraps the Kaggle notebook training pipeline.

Training logic (MinMaxScaler → fit_transform → model.fit → np.percentile threshold)
is preserved verbatim. Added: artifact persistence (.keras, scaler.pkl, threshold.pkl)
and DB ModelVersion bookkeeping.
"""
import base64
import io
import logging
import os
from datetime import datetime

import joblib
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for server use
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.callbacks import EarlyStopping

import app_config
from database.db import SessionLocal
from database.models import ModelVersion, ProcessedMetric
from model.constants import METRIC_COLUMNS_AVGTIME
from model.lstm_autoencoder import build_lstm_autoencoder, create_sequences

logger = logging.getLogger(__name__)

SAVED_DIR = os.path.join(os.path.dirname(__file__), "saved")
MODEL_PATH = os.path.join(SAVED_DIR, "lstm_model.keras")
SCALER_PATH = os.path.join(SAVED_DIR, "scaler.pkl")
THRESHOLD_PATH = os.path.join(SAVED_DIR, "threshold.pkl")


def _load_processed_data(from_ts=None, to_ts=None) -> pd.DataFrame:
    """
    Fetch processed metrics from the DB as a time-sorted DataFrame.
    When from_ts/to_ts are provided only rows within that window are returned
    (used to train on a specific baseline period).
    """
    from datetime import datetime as dt
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
        records = []
        for r in rows:
            row = {col: getattr(r, col) for col in METRIC_COLUMNS_AVGTIME}
            row["timestamp"] = r.timestamp
            records.append(row)
    finally:
        db.close()

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df = df.set_index("timestamp")
    return df


def _plot_to_base64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded


def plot_reconstruction_error(anomaly_scores_df: pd.DataFrame, anomaly_threshold: float,
                               anomaly_percentile: int) -> str:
    """
    Plots reconstruction error over time with threshold line and anomaly markers.
    Preserved verbatim from Kaggle notebook; returns base64 PNG string.
    """
    fig, ax = plt.subplots(figsize=(15, 7))
    ax.plot(anomaly_scores_df.index, anomaly_scores_df["Reconstruction_Error"], label="Reconstruction Error")
    ax.axhline(y=anomaly_threshold, color="r", linestyle="--",
               label=f"Anomaly Threshold ({anomaly_percentile}th percentile)")

    anomalies_for_plot = anomaly_scores_df[anomaly_scores_df["Is_Anomaly"]]
    if not anomalies_for_plot.empty:
        ax.scatter(anomalies_for_plot.index, anomalies_for_plot["Reconstruction_Error"],
                   color="red", s=50, label="Anomaly Detected", zorder=5)

    ax.set_title("NameNode JMX AvgTime Reconstruction Error Over Time")
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Reconstruction Error (MSE)")
    ax.legend()
    ax.grid(True)
    fig.tight_layout()
    return _plot_to_base64(fig)


def plot_jmx_metrics(df_metrics: pd.DataFrame, metrics_to_plot: list,
                      title: str = "NameNode JMX AvgTime Metrics Over Time") -> str:
    """
    Plots specified JMX metrics against time.
    Preserved verbatim from Kaggle notebook; returns base64 PNG string.
    """
    fig, ax = plt.subplots(figsize=(15, 7))
    colors = ["blue", "green", "red", "purple", "orange", "brown", "cyan", "magenta"]
    for i, metric in enumerate(metrics_to_plot):
        if metric in df_metrics.columns:
            ax.plot(df_metrics.index, df_metrics[metric], label=metric, color=colors[i % len(colors)])
        else:
            logger.warning("Metric '%s' not found in data for plotting.", metric)

    ax.set_title(title)
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Value (ms or count)")
    ax.legend()
    ax.grid(True)
    fig.tight_layout()
    return _plot_to_base64(fig)


def train(force: bool = False, from_ts=None, to_ts=None) -> dict:
    """
    Full training pipeline from the Kaggle notebook, adapted to read from DB.
    When from_ts/to_ts are provided, only rows in that window are used for training
    (baseline period chosen by the engineer).
    Saves artifacts to model/saved/. Returns a summary dict.
    """
    os.makedirs(SAVED_DIR, exist_ok=True)

    if not force and os.path.exists(MODEL_PATH):
        logger.info("Saved model found — skipping training. Use force=True to retrain.")
        return {"status": "skipped", "reason": "model already exists"}

    window_desc = f"{from_ts} → {to_ts}" if from_ts or to_ts else "all data"
    logger.info("Starting model training on baseline window: %s", window_desc)

    df_metrics = _load_processed_data(from_ts=from_ts, to_ts=to_ts)
    if df_metrics.empty:
        logger.warning("No processed data available for training.")
        return {"status": "failed", "reason": "no data"}

    metric_cols_to_use = [col for col in METRIC_COLUMNS_AVGTIME if col in df_metrics.columns]
    if not metric_cols_to_use:
        return {"status": "failed", "reason": "no valid metric columns"}

    df_metrics = df_metrics[metric_cols_to_use].copy()
    df_metrics = df_metrics.fillna(df_metrics.median())

    if len(df_metrics) < app_config.SEQUENCE_LENGTH + 1:
        return {
            "status": "failed",
            "reason": f"insufficient data: {len(df_metrics)} rows, need {app_config.SEQUENCE_LENGTH + 1}",
        }

    # --- Kaggle notebook training pipeline (preserved verbatim) ---
    scaler = MinMaxScaler()
    train_size = int(len(df_metrics) * 0.8)
    if train_size < app_config.SEQUENCE_LENGTH:
        train_size = app_config.SEQUENCE_LENGTH

    train_data_scaled = scaler.fit_transform(df_metrics.iloc[:train_size])
    train_data_scaled_df = pd.DataFrame(train_data_scaled, columns=metric_cols_to_use,
                                         index=df_metrics.index[:train_size])

    X_train = create_sequences(train_data_scaled_df, app_config.SEQUENCE_LENGTH)
    if X_train.shape[0] == 0:
        return {"status": "failed", "reason": "no training sequences could be created"}

    input_shape = (X_train.shape[1], X_train.shape[2])
    model = build_lstm_autoencoder(input_shape, app_config.LATENT_DIM)
    model.summary(print_fn=logger.info)

    early_stopping = EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)

    history = model.fit(
        X_train, X_train,
        epochs=app_config.EPOCHS,
        batch_size=app_config.BATCH_SIZE,
        validation_split=app_config.VALIDATION_SPLIT,
        callbacks=[early_stopping],
        verbose=0,
    )

    train_pred = model.predict(X_train, verbose=0)
    train_mse = np.mean(np.power(X_train - train_pred, 2), axis=(1, 2))
    threshold = float(np.percentile(train_mse, app_config.ANOMALY_THRESHOLD_PERCENTILE))

    epochs_run = len(history.history["loss"])
    logger.info("Training complete. Epochs run: %d. Threshold: %.6f", epochs_run, threshold)

    # Persist artifacts
    model.save(MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    joblib.dump(threshold, THRESHOLD_PATH)
    logger.info("Artifacts saved to %s", SAVED_DIR)

    # Record in DB
    db = SessionLocal()
    try:
        db.query(ModelVersion).filter(ModelVersion.status == "active").update({"status": "superseded"})
        version = ModelVersion(
            trained_at=datetime.utcnow(),
            threshold=threshold,
            num_rows_trained_on=len(df_metrics),
            epochs_run=epochs_run,
            baseline_from=str(from_ts) if from_ts else None,
            baseline_to=str(to_ts) if to_ts else None,
            status="active",
        )
        db.add(version)
        db.commit()
        version_id = version.id
    finally:
        db.close()

    return {
        "status": "success",
        "version_id": version_id,
        "threshold": threshold,
        "epochs_run": epochs_run,
        "rows_trained_on": len(df_metrics),
    }


def model_exists() -> bool:
    return os.path.exists(MODEL_PATH)

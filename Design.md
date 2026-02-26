# HDFS Namenode Anomaly Detector

A self-contained Python application that continuously monitors a Hadoop HDFS Namenode via JMX, learns what "normal" RPC performance looks like using an LSTM Autoencoder, and lets platform engineers interactively investigate suspected degradation periods through a browser-based report UI.

---

## How it works

The application runs three automated stages in the background and exposes a two-step analysis workflow in the browser.

### Automated background pipeline

```
Namenode JMX (HTTP)
      │  every 10 s
      ▼
┌─────────────────────┐
│  Stage 1 – Collect  │  Polls /jmx endpoint, stores raw JSON
└─────────┬───────────┘
          │  every 60 s
          ▼
┌──────────────────────────┐
│  Stage 2 – Process       │  Extracts 28 AvgTime / thread / GC metrics
└─────────┬────────────────┘
          │  every 5 min
          ▼
┌──────────────────────────┐
│  Stage 3 – Score         │  LSTM Autoencoder scores 30-step sliding windows
└──────────────────────────┘
          │
          ▼
    nightly retrain (2 AM)
```

### Browser workflow

| Step | Action |
|------|--------|
| **1** | Select a **baseline window** (period of known-good performance) → train the LSTM model |
| **2** | Select an **analysis window** (suspected degraded period) → generate an anomaly report |

The report includes a reconstruction-error chart, a key-metric time-series chart, and a ranked anomaly table with per-metric root-cause breakdowns.

---

## Architecture

```
AnamolyDetection/
├── run.py                      # Application entry point
├── config.yaml                 # All tunable parameters
├── app_config.py               # Typed config loader
├── requirements.txt
│
├── collector/
│   └── jmx_collector.py        # Stage 1 – JMX polling
│
├── processor/
│   └── metrics_processor.py    # Stage 2 – metric extraction
│
├── model/
│   ├── lstm_autoencoder.py     # Model architecture (Keras)
│   ├── trainer.py              # Training pipeline
│   ├── inference.py            # Scoring (batch + on-demand)
│   └── constants.py            # Metric names and root-cause definitions
│
├── scheduler/
│   └── tasks.py                # APScheduler job wiring
│
├── api/
│   ├── main.py                 # FastAPI app + static file serving
│   └── routes/
│       ├── model.py            # POST /api/model/train, GET /api/model/status
│       ├── reports.py          # POST /api/report
│       ├── metrics.py          # GET /api/metrics
│       └── anomalies.py        # GET /api/anomalies
│
├── database/
│   ├── db.py                   # SQLAlchemy engine + migrations
│   └── models.py               # ORM models
│
└── frontend/
    ├── index.html
    ├── styles.css
    └── app.js
```

### Monitored metrics (28 total)

| Category | Metrics |
|----------|---------|
| **RPC latency** | `RpcProcessingTimeAvgTime`, `RpcQueueTimeAvgTime` |
| **File operations** | `CreateAvgTime`, `DeleteAvgTime`, `RenameAvgTime`, `MkdirsAvgTime`, `CompleteAvgTime`, `GetFileInfoAvgTime`, `GetBlockLocationsAvgTime`, `GetListingAvgTime`, `GetContentSummaryAvgTime`, `FsyncAvgTime`, `ConcatAvgTime` |
| **Snapshot ops** | `CreateSnapshotAvgTime`, `DeleteSnapshotAvgTime`, `RenameSnapshotAvgTime`, `GetSnapshotDiffReportAvgTime`, `GetSnapshotDiffReportListingAvgTime` |
| **DataNode ops** | `GetDatanodeReportAvgTime`, `GetDatanodeStorageReportAvgTime` |
| **JVM threads** | `ThreadsBlocked`, `ThreadsWaiting`, `ThreadsTimedWaiting` |
| **Garbage collection** | `GcTimeMillisParNew`, `GcTimeMillisConcurrentMarkSweep` |
| **Auth / queue** | `GetGroupsAvgTime`, `CallQueueLength` |

---

## Requirements

- **Python 3.11** (required — TensorFlow does not support 3.12+ on Apple Silicon)
- [Miniconda or Anaconda](https://docs.conda.io/en/latest/miniconda.html)
- A reachable Hadoop Namenode with HTTP JMX enabled (default port `9870`)

---

## Installation

### 1. Clone the repository

```bash
git clone <repo-url>
cd AnamolyDetection
```

### 2. Create the conda environment

```bash
conda create -n anomaly_detection python=3.11 -y
conda activate anomaly_detection
```

### 3. Install Python dependencies

```bash
python -m pip install -r requirements.txt
```

---

## Configuration

Edit **`config.yaml`** before starting the application.

```yaml
namenode:
  jmx_url: "http://<your-namenode-host>:9870/jmx"  # ← required
  poll_interval_seconds: 10                          # collection frequency

scheduler:
  process_interval_seconds: 60      # how often raw → processed ETL runs
  inference_interval_minutes: 5     # how often background scoring runs
  retrain_cron: "0 2 * * *"        # nightly model retrain (cron expression)

model:
  sequence_length: 30               # data points per LSTM window (30 × 10 s = 5 min)
  latent_dim: 10                    # LSTM bottleneck dimension
  epochs: 50                        # training epochs
  batch_size: 32
  validation_split: 0.2
  anomaly_threshold_percentile: 95  # percentile of baseline errors used as threshold

database:
  url: "sqlite:///anomaly_detection.db"  # SQLite file, created automatically

server:
  host: "0.0.0.0"
  port: 8000
```

> **Minimum data before training:** `sequence_length × poll_interval_seconds` = 30 × 10 s = **5 minutes**. A 30–60 minute baseline produces a much better model.

---

## Running the application

```bash
conda activate anomaly_detection
python run.py
```

Startup sequence:

1. Creates / migrates the SQLite database
2. Loads a saved model if one exists; otherwise waits for data
3. Starts the background scheduler (collector → processor → scorer → nightly retrain)
4. Serves the UI at **http://localhost:8000**

---

## Using the browser UI

Open **http://localhost:8000** in your browser.

### Step 1 — Train on baseline

1. Select the **From** and **To** timestamps of a period when the Namenode was running normally (use **Quick Select** presets or type values manually).
2. Click **Train Model on Baseline**.
3. Training takes 1–3 minutes depending on data volume. The result panel shows rows used, epochs run, and the computed anomaly threshold (MSE).

### Step 2 — Analyze a window

1. Select the time range you suspect had performance issues.
2. *(Optional)* Enter a **Threshold Override** to raise or lower the detection sensitivity. The model's computed default is shown next to the field. Leave blank to use it.
3. Click **Analyze for Anomalies**.

### Reading the report

| Element | What it shows |
|---------|---------------|
| **Reconstruction Error chart** | MSE score for each 30-step window starting at that timestamp. Points above the red dashed line are anomalies. |
| **Key Metrics chart** | Raw (unscaled) metric values over time. Select which metrics to plot using the checkboxes. |
| **Detected Anomalies table** | Each flagged timestamp, its MSE score, and the top contributing metric. Click any row to expand the root-cause breakdown. |

---

## REST API

Interactive docs available at **http://localhost:8000/docs** (Swagger UI).

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/model/status` | Current model status, threshold, baseline window |
| `POST` | `/api/model/train` | Train on a specific baseline window |
| `POST` | `/api/report` | Score an analysis window and return charts + anomaly list |
| `GET` | `/api/metrics` | Query processed metrics |
| `GET` | `/api/anomalies` | Query persisted anomaly events |

### Example: train via curl

```bash
curl -X POST http://localhost:8000/api/model/train \
  -H "Content-Type: application/json" \
  -d '{"from_ts": "2026-02-24 21:00:00", "to_ts": "2026-02-24 23:00:00"}'
```

### Example: generate a report

```bash
curl -X POST http://localhost:8000/api/report \
  -H "Content-Type: application/json" \
  -d '{
    "from_ts": "2026-02-24 23:00:00",
    "to_ts": "2026-02-24 23:30:00",
    "threshold_override": 0.5
  }'
```

---

## Resetting to a clean state

Stop the application (`Ctrl+C`), then:

```bash
rm -f anomaly_detection.db
rm -rf model/saved_model model/scaler.pkl model/threshold.pkl
python run.py
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `zsh: segmentation fault python run.py` | Python version incompatible with TensorFlow | Ensure `conda activate anomaly_detection` is active and the env uses Python 3.11 |
| "No processed data available for training" | Not enough data collected yet | Wait at least 5 minutes after starting before training |
| "Actual: 0.00" in root-cause panel | Spike occurred mid-window | "Actual" shows the **peak** value across the 30-step window; if the window starts before the spike, the peak at the start is genuinely 0 |
| Low-severity anomalies flagged | Model threshold is too sensitive | Enter a higher **Threshold Override** in the analysis form and re-run |
| JMX collector `KeyError` | Namenode uses G1GC instead of ParNew/CMS | Already handled — processor falls back to generic `GcTimeMillis` |
| `list index out of range` in collector | JMX window had no top-user activity | Already handled — empty `topUsers` lists are skipped |

---

## Technology stack

| Layer | Technology |
|-------|-----------|
| ML model | TensorFlow / Keras — LSTM Autoencoder |
| Data scaling | scikit-learn `MinMaxScaler` |
| Data manipulation | pandas, NumPy |
| Chart generation | Matplotlib (server-side PNG, base64-encoded) |
| Web framework | FastAPI + Uvicorn |
| Database | SQLite via SQLAlchemy ORM |
| Scheduling | APScheduler |
| Configuration | PyYAML |
| Serialisation | joblib (scaler + threshold), pydantic (API schemas) |
| Frontend | Vanilla HTML / CSS / JavaScript |

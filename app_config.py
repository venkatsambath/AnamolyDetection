"""Central configuration loader — reads config.yaml once and exposes a typed dict."""
import os
import yaml

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

with open(_CONFIG_PATH, "r") as _f:
    _raw = yaml.safe_load(_f)

NAMENODE_JMX_URL: str = _raw["namenode"]["jmx_url"]
POLL_INTERVAL_SECONDS: int = _raw["namenode"]["poll_interval_seconds"]

PROCESS_INTERVAL_SECONDS: int = _raw["scheduler"]["process_interval_seconds"]
INFERENCE_INTERVAL_MINUTES: int = _raw["scheduler"]["inference_interval_minutes"]
RETRAIN_CRON: str = _raw["scheduler"]["retrain_cron"]

SEQUENCE_LENGTH: int = _raw["model"]["sequence_length"]
LATENT_DIM: int = _raw["model"]["latent_dim"]
EPOCHS: int = _raw["model"]["epochs"]
BATCH_SIZE: int = _raw["model"]["batch_size"]
VALIDATION_SPLIT: float = _raw["model"]["validation_split"]
ANOMALY_THRESHOLD_PERCENTILE: int = _raw["model"]["anomaly_threshold_percentile"]

DATABASE_URL: str = _raw["database"]["url"]

SERVER_HOST: str = _raw["server"]["host"]
SERVER_PORT: int = _raw["server"]["port"]

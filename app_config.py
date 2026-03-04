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
EXPLANATION_MIN_RANGE: float = _raw["model"].get("explanation_min_range", 2.0)
EXPLANATION_MIN_RANGE_THREAD: float = _raw["model"].get("explanation_min_range_thread", 4.0)

DATABASE_URL: str = _raw["database"]["url"]
DATABASE_RETENTION_DAYS: int = _raw["database"].get("retention_days", 10)
DATABASE_CLEANUP_INTERVAL_HOURS: int = _raw["database"].get("cleanup_interval_hours", 24)

SERVER_HOST: str = _raw["server"]["host"]
SERVER_PORT: int = _raw["server"]["port"]

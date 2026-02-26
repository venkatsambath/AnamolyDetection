"""SQLAlchemy ORM models for all four database tables."""
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, String, Text, JSON
)

from database.db import Base


class RawMetric(Base):
    """
    One row per JMX poll cycle (every 10 s).
    Stores the full beans JSON blob so the preprocessor can re-parse it
    without hitting the network again.
    """
    __tablename__ = "raw_metrics"

    id = Column(Integer, primary_key=True, index=True)
    collected_at = Column(DateTime, default=datetime.utcnow, index=True)
    beans_json = Column(Text, nullable=False)   # json.dumps(data["beans"])
    processed = Column(Boolean, default=False, index=True)


class ProcessedMetric(Base):
    """
    One row per successfully parsed JMX snapshot after Stage-2 extraction.
    Column names match header_avgtime exactly.
    """
    __tablename__ = "processed_metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, index=True, nullable=False)
    scored = Column(Boolean, default=False, index=True)

    # Shared / JVM metrics
    ThreadsBlocked = Column(Float)
    ThreadsWaiting = Column(Float)
    ThreadsTimedWaiting = Column(Float)
    GcTimeMillisParNew = Column(Float)
    GcTimeMillisConcurrentMarkSweep = Column(Float)
    CallQueueLength = Column(Float)
    RpcProcessingTimeAvgTime = Column(Float)
    RpcQueueTimeAvgTime = Column(Float)

    # UgiMetrics
    GetGroupsAvgTime = Column(Float)

    # File system operations
    CreateAvgTime = Column(Float)
    MkdirsAvgTime = Column(Float)
    DeleteAvgTime = Column(Float)
    RenameAvgTime = Column(Float)
    Rename2AvgTime = Column(Float)
    CompleteAvgTime = Column(Float)
    GetFileInfoAvgTime = Column(Float)
    GetBlockLocationsAvgTime = Column(Float)
    GetListingAvgTime = Column(Float)
    GetContentSummaryAvgTime = Column(Float)
    FsyncAvgTime = Column(Float)
    ConcatAvgTime = Column(Float)

    # Snapshots
    CreateSnapshotAvgTime = Column(Float)
    DeleteSnapshotAvgTime = Column(Float)
    RenameSnapshotAvgTime = Column(Float)
    GetSnapshotDiffReportAvgTime = Column(Float)
    GetSnapshotDiffReportListingAvgTime = Column(Float)

    # Datanode management
    GetDatanodeReportAvgTime = Column(Float)
    GetDatanodeStorageReportAvgTime = Column(Float)


class AnomalyEvent(Base):
    """
    One row per scored time-step produced by the inference engine.
    explanation_json stores the dict returned by explain_anomaly().
    """
    __tablename__ = "anomaly_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, index=True, nullable=False)
    reconstruction_error = Column(Float, nullable=False)
    is_anomaly = Column(Boolean, nullable=False, default=False)
    explanation_json = Column(JSON, nullable=True)


class ModelVersion(Base):
    """
    Tracks each training run so the UI can display model provenance.
    """
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, index=True)
    trained_at = Column(DateTime, default=datetime.utcnow)
    threshold = Column(Float, nullable=False)
    num_rows_trained_on = Column(Integer, nullable=False)
    epochs_run = Column(Integer, nullable=False)
    baseline_from = Column(String(32), nullable=True)   # ISO datetime of baseline window start
    baseline_to = Column(String(32), nullable=True)     # ISO datetime of baseline window end
    status = Column(String(32), default="active")       # active | superseded | failed

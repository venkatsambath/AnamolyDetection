"""
Stage 2 — Metrics Preprocessor.

Reads unprocessed raw_metrics rows from the DB, runs the exact bean-parsing
logic from the original Stage 2 script, and writes completed AvgTime feature
rows to processed_metrics.

All variable initialisations, section-name checks, KeyError/ValueError guards,
and the skip-row condition are preserved verbatim from the original script.
Input changes from os.listdir(directory) → DB query.
Output changes from csv.writer → DB insert.
"""
import json
import logging
from datetime import datetime

from database.db import SessionLocal
from database.models import ProcessedMetric, RawMetric

logger = logging.getLogger(__name__)

# Columns that must ALL be non-(-1) for a row to be accepted — same guard as original
REQUIRED_COLUMNS = [
    "ThreadsBlocked", "ThreadsWaiting", "ThreadsTimedWaiting",
    "GcTimeMillisParNew", "GcTimeMillisConcurrentMarkSweep",
    "CallQueueLength", "RpcProcessingTimeAvgTime", "RpcQueueTimeAvgTime",
    "GetGroupsAvgTime",
    "CreateAvgTime", "MkdirsAvgTime", "DeleteAvgTime", "RenameAvgTime",
    "Rename2AvgTime", "CompleteAvgTime",
    "GetFileInfoAvgTime", "GetBlockLocationsAvgTime", "GetListingAvgTime",
    "GetContentSummaryAvgTime",
    "FsyncAvgTime", "ConcatAvgTime",
    "CreateSnapshotAvgTime", "DeleteSnapshotAvgTime", "RenameSnapshotAvgTime",
    "GetSnapshotDiffReportAvgTime", "GetSnapshotDiffReportListingAvgTime",
    "GetDatanodeReportAvgTime", "GetDatanodeStorageReportAvgTime",
]


def _parse_beans(beans: list) -> dict | None:
    """
    Runs the Stage-2 bean-extraction logic on a single JMX snapshot.
    Returns a dict of metric values, or None if the row should be skipped.
    """
    # --- original Stage 2 variable initialisation (preserved verbatim) ---
    timestamp = ""
    ThreadsBlocked = ThreadsWaiting = ThreadsTimedWaiting = -1
    GcTimeMillisParNew = GcTimeMillisConcurrentMarkSweep = -1
    CallQueueLength = RpcProcessingTimeAvgTime = RpcQueueTimeAvgTime = -1
    GetGroupsAvgTime = -1
    CreateAvgTime = MkdirsAvgTime = DeleteAvgTime = RenameAvgTime = Rename2AvgTime = CompleteAvgTime = -1
    GetFileInfoAvgTime = GetBlockLocationsAvgTime = GetListingAvgTime = GetContentSummaryAvgTime = -1
    FsyncAvgTime = ConcatAvgTime = -1
    CreateSnapshotAvgTime = DeleteSnapshotAvgTime = RenameSnapshotAvgTime = -1
    GetSnapshotDiffReportAvgTime = GetSnapshotDiffReportListingAvgTime = -1
    GetDatanodeReportAvgTime = GetDatanodeStorageReportAvgTime = -1

    # --- original Stage 2 section parsing loop (preserved verbatim) ---
    for section in beans:
        try:
            if section["name"] == "Hadoop:service=NameNode,name=JvmMetrics":
                ThreadsBlocked = json.loads(str(section["ThreadsBlocked"]))
                ThreadsWaiting = json.loads(str(section["ThreadsWaiting"]))
                ThreadsTimedWaiting = json.loads(str(section["ThreadsTimedWaiting"]))
                # ParNew/CMS specific (CDH 5 / CMS GC clusters).
                # G1GC clusters (CDH 6+, Java 11) expose GcTimeMillis + GcCount instead.
                # Fall back to GcTimeMillis for ParNew and 0 for CMS so rows are not skipped.
                gc_total = json.loads(str(section.get("GcTimeMillis", 0)))
                GcTimeMillisParNew = json.loads(str(section.get("GcTimeMillisParNew", gc_total)))
                GcTimeMillisConcurrentMarkSweep = json.loads(str(section.get("GcTimeMillisConcurrentMarkSweep", 0)))

            if section["name"] == "Hadoop:service=NameNode,name=UgiMetrics":
                GetGroupsAvgTime = json.loads(str(section["GetGroupsAvgTime"]))

            if section["name"] == "Hadoop:service=NameNode,name=FSNamesystemState":
                topusers = json.loads(section["TopUserOpCounts"])
                timestamp = topusers["timestamp"][0:19]

            if section["name"] == "Hadoop:service=NameNode,name=RpcActivityForPort9000":
                CallQueueLength = json.loads(str(section["CallQueueLength"]))
                RpcProcessingTimeAvgTime = json.loads(str(section["RpcProcessingTimeAvgTime"]))
                RpcQueueTimeAvgTime = json.loads(str(section["RpcQueueTimeAvgTime"]))

            if section["name"] == "Hadoop:service=NameNode,name=RpcDetailedActivityForPort9000":
                # Use .get(key, 0) so that operations with no calls in this window
                # (metric absent from the bean) are treated as 0 ms rather than -1.
                def _ms(key):
                    return json.loads(str(section.get(key, 0)))

                CreateAvgTime = _ms("CreateAvgTime")
                MkdirsAvgTime = _ms("MkdirsAvgTime")
                DeleteAvgTime = _ms("DeleteAvgTime")
                RenameAvgTime = _ms("RenameAvgTime")
                Rename2AvgTime = _ms("Rename2AvgTime")
                CompleteAvgTime = _ms("CompleteAvgTime")
                GetFileInfoAvgTime = _ms("GetFileInfoAvgTime")
                GetBlockLocationsAvgTime = _ms("GetBlockLocationsAvgTime")
                GetListingAvgTime = _ms("GetListingAvgTime")
                GetContentSummaryAvgTime = _ms("GetContentSummaryAvgTime")
                FsyncAvgTime = _ms("FsyncAvgTime")
                ConcatAvgTime = _ms("ConcatAvgTime")
                CreateSnapshotAvgTime = _ms("CreateSnapshotAvgTime")
                DeleteSnapshotAvgTime = _ms("DeleteSnapshotAvgTime")
                RenameSnapshotAvgTime = _ms("RenameSnapshotAvgTime")
                GetSnapshotDiffReportAvgTime = _ms("GetSnapshotDiffReportAvgTime")
                GetSnapshotDiffReportListingAvgTime = _ms("GetSnapshotDiffReportListingAvgTime")
                GetDatanodeReportAvgTime = _ms("GetDatanodeReportAvgTime")
                GetDatanodeStorageReportAvgTime = _ms("GetDatanodeStorageReportAvgTime")

        except KeyError as e:
            logger.warning("KeyError for metric '%s' in section '%s'. Metric remains -1.", e, section.get("name", "N/A"))
        except (ValueError, TypeError) as e:
            logger.warning("Data conversion error in section '%s': %s. Metric remains -1.", section.get("name", "N/A"), e)

    # --- original Stage 2 skip-row condition (preserved verbatim) ---
    row_values = {
        "ThreadsBlocked": ThreadsBlocked,
        "ThreadsWaiting": ThreadsWaiting,
        "ThreadsTimedWaiting": ThreadsTimedWaiting,
        "GcTimeMillisParNew": GcTimeMillisParNew,
        "GcTimeMillisConcurrentMarkSweep": GcTimeMillisConcurrentMarkSweep,
        "CallQueueLength": CallQueueLength,
        "RpcProcessingTimeAvgTime": RpcProcessingTimeAvgTime,
        "RpcQueueTimeAvgTime": RpcQueueTimeAvgTime,
        "GetGroupsAvgTime": GetGroupsAvgTime,
        "CreateAvgTime": CreateAvgTime,
        "MkdirsAvgTime": MkdirsAvgTime,
        "DeleteAvgTime": DeleteAvgTime,
        "RenameAvgTime": RenameAvgTime,
        "Rename2AvgTime": Rename2AvgTime,
        "CompleteAvgTime": CompleteAvgTime,
        "GetFileInfoAvgTime": GetFileInfoAvgTime,
        "GetBlockLocationsAvgTime": GetBlockLocationsAvgTime,
        "GetListingAvgTime": GetListingAvgTime,
        "GetContentSummaryAvgTime": GetContentSummaryAvgTime,
        "FsyncAvgTime": FsyncAvgTime,
        "ConcatAvgTime": ConcatAvgTime,
        "CreateSnapshotAvgTime": CreateSnapshotAvgTime,
        "DeleteSnapshotAvgTime": DeleteSnapshotAvgTime,
        "RenameSnapshotAvgTime": RenameSnapshotAvgTime,
        "GetSnapshotDiffReportAvgTime": GetSnapshotDiffReportAvgTime,
        "GetSnapshotDiffReportListingAvgTime": GetSnapshotDiffReportListingAvgTime,
        "GetDatanodeReportAvgTime": GetDatanodeReportAvgTime,
        "GetDatanodeStorageReportAvgTime": GetDatanodeStorageReportAvgTime,
    }

    if not timestamp or any(v == -1 for v in row_values.values()):
        return None

    row_values["timestamp"] = timestamp
    return row_values


def process_pending() -> int:
    """
    Process all raw_metrics rows that haven't been processed yet.
    Returns the number of ProcessedMetric rows written.
    """
    db = SessionLocal()
    written = 0
    try:
        pending = db.query(RawMetric).filter(RawMetric.processed == False).all()  # noqa: E712
        logger.info("Preprocessor: %d unprocessed raw rows to handle.", len(pending))

        for raw in pending:
            try:
                beans = json.loads(raw.beans_json)
            except json.JSONDecodeError as exc:
                logger.error("Could not decode beans_json for raw id=%s: %s", raw.id, exc)
                raw.processed = True
                db.commit()
                continue

            parsed = _parse_beans(beans)

            if parsed is None:
                logger.debug("Skipped incomplete row for raw id=%s", raw.id)
            else:
                ts = datetime.fromisoformat(parsed.pop("timestamp"))
                metric = ProcessedMetric(timestamp=ts, **parsed)
                db.add(metric)
                written += 1

            raw.processed = True

        db.commit()
        logger.info("Preprocessor: wrote %d processed metric rows.", written)
    except Exception as exc:
        db.rollback()
        logger.error("Preprocessor error: %s", exc)
    finally:
        db.close()

    return written

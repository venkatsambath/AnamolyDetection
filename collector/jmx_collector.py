"""
Stage 1 — JMX Collector.

Polls the Namenode /jmx endpoint every POLL_INTERVAL_SECONDS and stores
the raw beans JSON into the raw_metrics table so the preprocessor can
extract AvgTime features without hitting the network again.

Original logic (requests.get, data["beans"] loop, windowLenMs filtering)
is preserved verbatim; only the output target changes from data.csv to DB.
"""
import json
import logging

import requests

import app_config
from database.db import SessionLocal
from database.models import RawMetric

logger = logging.getLogger(__name__)


def collect_once() -> None:
    """
    Single poll cycle — equivalent to one iteration of the original while-True loop.
    Called by APScheduler every POLL_INTERVAL_SECONDS seconds.
    """
    url = app_config.NAMENODE_JMX_URL
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            logger.warning("JMX endpoint returned HTTP %s", response.status_code)
            return

        data = response.json()

    except requests.RequestException as exc:
        logger.error("Failed to reach JMX endpoint: %s", exc)
        return

    # --- original Stage 1 parsing logic (preserved verbatim) ---
    for section in data["beans"]:
        if section["name"] == "Hadoop:service=NameNode,name=FSNamesystemState":
            try:
                topusers = json.loads(section["TopUserOpCounts"])
            except (KeyError, json.JSONDecodeError) as exc:
                logger.error("Could not parse TopUserOpCounts: %s", exc)
                continue

            for window in topusers["windows"]:
                if window["windowLenMs"] == 60000:
                    for optype in window["ops"]:
                        # topUsers can be empty when no calls have been made for this opType yet
                        if not optype["topUsers"]:
                            continue
                        ts = topusers["timestamp"][0:19]
                        op = optype["opType"]
                        user = optype["topUsers"][0]["user"]
                        count = optype["topUsers"][0]["count"]
                        logger.debug("%s,%s,%s,%s", ts, op, user, count)

    # Store the full beans JSON for the preprocessor (one row per poll cycle)
    db = SessionLocal()
    try:
        record = RawMetric(beans_json=json.dumps(data["beans"]))
        db.add(record)
        db.commit()
        logger.debug("Stored raw JMX snapshot id=%s", record.id)
    except Exception as exc:
        db.rollback()
        logger.error("DB insert failed: %s", exc)
    finally:
        db.close()

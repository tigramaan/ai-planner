"""Synthetic probe; collected only when explicitly selected by the QA checker."""

import os
import time
from datetime import UTC, datetime

from sqlalchemy.pool import StaticPool

from app.database import engine


def ready():
    assert engine.url.database is None
    assert isinstance(engine.pool, StaticPool)
    resource = engine.get_execution_options()["qa_resource"]
    assert resource["owner"] == resource["project"] == "aiplanner"
    assert resource["run"] == os.environ["QA_RESOURCE_RUN"]
    assert resource["purpose"] == "api-tests"
    assert datetime.fromisoformat(resource["expiry"]) > datetime.now(UTC)
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA database_list").fetchone()[2] == ""
        assert connection.exec_driver_sql(
            "SELECT count(*) FROM sqlite_master WHERE type = 'table'"
        ).scalar() > 0
    fd = int(os.environ["QA_PROBE_READY_FD"])
    os.write(fd, b"ready")
    os.close(fd)


def test_success():
    ready()


def test_failure():
    ready()
    raise AssertionError("intentional synthetic QA failure")


def test_wait():
    ready()
    while True:
        time.sleep(0.1)

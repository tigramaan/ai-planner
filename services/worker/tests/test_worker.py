from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from worker import Worker, readable_vapid_key


def make_worker() -> Worker:
    worker = Worker.__new__(Worker)
    worker.vapid_key_path = "/run/secrets/vapid_private.pem"
    worker.vapid_subject = "mailto:admin@example.com"
    worker.complete = Mock()
    return worker


def reminder(subscriptions=None, channel="push") -> dict:
    return {
        "id": "reminder-1",
        "title": "Проверить встречу",
        "channel": channel,
        "subscriptions": subscriptions or [],
    }


def subscription(endpoint="https://push.example/device") -> dict:
    return {
        "endpoint": endpoint,
        "keys": {"p256dh": "public-key", "auth": "auth-secret"},
    }


def test_in_app_delivery_does_not_call_push():
    worker = make_worker()

    with patch.object(worker, "send_push") as send_push:
        worker.process(reminder(channel="in_app"))

    send_push.assert_not_called()
    worker.complete.assert_called_once_with("reminder-1", "delivered")


def test_missing_push_subscription_schedules_retry():
    worker = make_worker()

    worker.process(reminder())

    worker.complete.assert_called_once_with(
        "reminder-1", "retry", "no push subscription"
    )


def test_malformed_subscription_isolated_from_healthy_subscription():
    worker = make_worker()

    with patch("worker.webpush", side_effect=[ValueError("invalid key"), None]):
        delivered, errors = worker.send_push(
            reminder([subscription("https://push.example/bad"), subscription()])
        )

    assert delivered == 1
    assert errors == ["push:ValueError"]


def test_all_subscription_failures_schedule_retry_without_secret_leak():
    worker = make_worker()
    worker.send_push = Mock(return_value=(0, ["push:ValueError"]))

    worker.process(reminder([subscription()]))

    worker.complete.assert_called_once_with(
        "reminder-1", "retry", "push:ValueError"
    )


def test_worker_rejects_unreadable_vapid_key_before_heartbeat():
    with (
        patch.object(Path, "read_bytes", side_effect=PermissionError("private")),
        pytest.raises(RuntimeError, match="not readable: PermissionError"),
    ):
        readable_vapid_key(Path("/run/secrets/vapid_private.pem"))

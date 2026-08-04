import json
import os
import time
from pathlib import Path

import httpx
import redis
from pywebpush import WebPushException, webpush


def readable_vapid_key(path: Path) -> Path:
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise RuntimeError(
            f"VAPID private key is not readable: {type(exc).__name__}"
        ) from exc
    if not content.strip():
        raise RuntimeError("VAPID private key is empty")
    return path


class Worker:
    def __init__(self) -> None:
        self.redis = redis.from_url(os.environ["REDIS_URL"], socket_timeout=5)
        self.api_url = os.environ.get("API_INTERNAL_URL", "http://api:8000").rstrip("/")
        self.token = os.environ["WORKER_SERVICE_TOKEN"]
        self.vapid_subject = os.environ.get("VAPID_SUBJECT", "mailto:admin@example.com")
        self.vapid_key_path = readable_vapid_key(
            Path(os.environ.get("VAPID_PRIVATE_KEY_PATH", "/run/secrets/vapid_private.pem"))
        )
        self.http = httpx.Client(timeout=15, headers={"X-Worker-Token": self.token})

    def claim(self) -> list[dict]:
        response = self.http.post(f"{self.api_url}/internal/v1/reminders/claim")
        response.raise_for_status()
        return response.json()

    def complete(
        self, reminder_id: str, status: str, error: str | None = None,
        deliveries: list[dict] | None = None,
    ) -> None:
        response = self.http.post(
            f"{self.api_url}/internal/v1/reminders/{reminder_id}/complete",
            json={
                "status": status,
                "error": error[:300] if error else None,
                "deliveries": deliveries or [],
            },
        )
        response.raise_for_status()

    def send_push(self, reminder: dict) -> list[dict]:
        results = []
        payload = json.dumps(
            {
                "web_push": 8030,
                "notification": {
                    "title": "AI Planner",
                    "body": reminder["title"],
                    "navigate": "/today",
                    "tag": f"reminder-{reminder['id']}",
                },
            },
            ensure_ascii=False,
        )
        for subscription in reminder["subscriptions"]:
            try:
                response = webpush(
                    subscription_info={
                        "endpoint": subscription["endpoint"],
                        "keys": subscription["keys"],
                    },
                    data=payload,
                    vapid_private_key=str(self.vapid_key_path),
                    vapid_claims={"sub": self.vapid_subject},
                    timeout=15,
                )
                results.append({
                    "subscription_id": subscription["id"],
                    "status": "delivered",
                    "status_code": response.status_code,
                })
            except WebPushException as exc:
                code = getattr(exc.response, "status_code", None)
                results.append({
                    "subscription_id": subscription["id"],
                    "status": "stale" if code in {404, 410} else "retry",
                    "status_code": code,
                    "error": f"push:{code or 'error'}",
                })
            except Exception as exc:  # noqa: BLE001 - isolate untrusted push clients
                # A malformed or provider-specific subscription must not stop the
                # delivery loop or prevent healthy subscriptions from being tried.
                results.append({
                    "subscription_id": subscription["id"],
                    "status": "retry",
                    "error": f"push:{type(exc).__name__}",
                })
        return results

    def process(self, reminder: dict) -> None:
        if reminder["channel"] == "in_app":
            self.complete(reminder["id"], "delivered")
            return
        if not reminder["subscriptions"]:
            self.complete(reminder["id"], "retry", "no push subscription")
            return
        results = self.send_push(reminder)
        delivered = any(row["status"] == "delivered" for row in results)
        retry = any(row["status"] == "retry" for row in results)
        status = "retry" if retry else "delivered" if delivered else "failed"
        errors = ",".join(row.get("error", "") for row in results if row.get("error"))
        self.complete(reminder["id"], status, errors or None, results)

    def run(self) -> None:
        while True:
            self.redis.set("worker:heartbeat", str(time.time()), ex=60)
            try:
                for reminder in self.claim():
                    self.process(reminder)
            except (httpx.HTTPError, redis.RedisError):
                time.sleep(5)
                continue
            time.sleep(5)


if __name__ == "__main__":
    Worker().run()

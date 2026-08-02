import json
import os
import time
from pathlib import Path

import httpx
import redis
from pywebpush import WebPushException, webpush


class Worker:
    def __init__(self) -> None:
        self.redis = redis.from_url(os.environ["REDIS_URL"], socket_timeout=5)
        self.api_url = os.environ.get("API_INTERNAL_URL", "http://api:8000").rstrip("/")
        self.token = os.environ["WORKER_SERVICE_TOKEN"]
        self.vapid_subject = os.environ.get("VAPID_SUBJECT", "mailto:admin@example.com")
        self.vapid_key_path = Path(
            os.environ.get("VAPID_PRIVATE_KEY_PATH", "/run/secrets/vapid_private.pem")
        )
        self.http = httpx.Client(timeout=15, headers={"X-Worker-Token": self.token})

    def claim(self) -> list[dict]:
        response = self.http.post(f"{self.api_url}/internal/v1/reminders/claim")
        response.raise_for_status()
        return response.json()

    def complete(self, reminder_id: str, status: str, error: str | None = None) -> None:
        response = self.http.post(
            f"{self.api_url}/internal/v1/reminders/{reminder_id}/complete",
            json={"status": status, "error": error[:300] if error else None},
        )
        response.raise_for_status()

    def send_push(self, reminder: dict) -> tuple[int, list[str]]:
        delivered = 0
        errors = []
        payload = json.dumps(
            {
                "title": "AI Planner",
                "body": reminder["title"],
                "url": "/today",
                "tag": f"reminder-{reminder['id']}",
            },
            ensure_ascii=False,
        )
        for subscription in reminder["subscriptions"]:
            try:
                webpush(
                    subscription_info={
                        "endpoint": subscription["endpoint"],
                        "keys": subscription["keys"],
                    },
                    data=payload,
                    vapid_private_key=str(self.vapid_key_path),
                    vapid_claims={"sub": self.vapid_subject},
                    timeout=15,
                )
                delivered += 1
            except WebPushException as exc:
                errors.append(f"push:{getattr(exc.response, 'status_code', 'error')}")
            except Exception as exc:  # noqa: BLE001 - isolate untrusted push clients
                # A malformed or provider-specific subscription must not stop the
                # delivery loop or prevent healthy subscriptions from being tried.
                errors.append(f"push:{type(exc).__name__}")
        return delivered, errors

    def process(self, reminder: dict) -> None:
        if reminder["channel"] == "in_app" or not reminder["subscriptions"]:
            self.complete(reminder["id"], "delivered")
            return
        delivered, errors = self.send_push(reminder)
        if delivered:
            self.complete(reminder["id"], "delivered")
        else:
            self.complete(reminder["id"], "retry", ",".join(errors) or "push failed")

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

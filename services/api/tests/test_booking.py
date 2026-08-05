from datetime import UTC, datetime, timedelta

from app.routers import booking


def configure(logged_in, conference_provider="google"):
    response = logged_in.put(
        "/api/v1/booking/settings",
        json={
            "enabled": True,
            "duration_minutes": 30,
            "workdays": [0, 1, 2, 3, 4, 5, 6],
            "work_start": "00:00",
            "work_end": "23:30",
            "minimum_notice_minutes": 0,
            "horizon_days": 90,
            "buffer_before_minutes": 0,
            "buffer_after_minutes": 0,
            "max_per_day": 20,
            "conference_provider": conference_provider,
            "title_template": "Звонок: {name}",
        },
    )
    assert response.status_code == 200
    key = logged_in.post("/api/v1/booking/keys", json={"name": "Lead site"})
    assert key.status_code == 201
    return key.json()["api_key"]


def next_slot(days=1):
    value = datetime.now(UTC) + timedelta(days=days)
    return value.replace(hour=10, minute=0, second=0, microsecond=0)


def test_key_is_shown_once_and_revocation_blocks_site(logged_in):
    key = configure(logged_in)
    settings = logged_in.get("/api/v1/booking/settings").json()
    assert settings["keys"][0]["prefix"] == key[:12]
    assert "api_key" not in settings["keys"][0]
    key_id = settings["keys"][0]["id"]
    assert logged_in.delete(f"/api/v1/booking/keys/{key_id}").status_code == 204
    response = logged_in.get(
        "/booking/v1/availability",
        params={"from": next_slot().isoformat(), "timezone": "Europe/Moscow"},
        headers={"Authorization": f"Bearer {key}"},
    )
    assert response.status_code == 401


def test_machine_availability_is_bounded_to_14_days_and_24_slots(logged_in, monkeypatch):
    key = configure(logged_in)

    async def token(*_args):
        return "provider-token"

    async def events(*_args):
        return []

    monkeypatch.setattr(booking, "valid_access_token", token)
    monkeypatch.setattr(booking, "list_calendar_events", events)
    requested = datetime.now(UTC).replace(second=0, microsecond=0)
    response = logged_in.get(
        "/booking/v1/availability",
        params={"from": requested.isoformat(), "timezone": "Europe/Moscow"},
        headers={"Authorization": f"Bearer {key}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"timezone", "duration_minutes", "slots"}
    assert 1 <= len(body["slots"]) <= 24
    assert all(set(slot) == {"start", "end"} for slot in body["slots"])
    assert all(datetime.fromisoformat(slot["end"]) <= requested + timedelta(days=14) for slot in body["slots"])


def test_booking_idempotency_and_three_success_limit(logged_in, monkeypatch):
    key = configure(logged_in)

    async def token(*_args):
        return "provider-token"

    async def events(*_args):
        return []

    counter = 0

    async def create(*_args):
        nonlocal counter
        counter += 1
        return {"id": f"event-{counter}", "htmlLink": "https://calendar.test/event"}

    monkeypatch.setattr(booking, "valid_access_token", token)
    monkeypatch.setattr(booking, "list_calendar_events", events)
    monkeypatch.setattr(booking, "create_calendar_event", create)
    headers = {"Authorization": f"Bearer {key}"}
    for attempt in range(3):
        body = {
            "lead_id": "lead-42",
            "name": "Анна",
            "email": "anna@example.com",
            "start": next_slot(attempt + 1).isoformat(),
            "timezone": "Europe/Moscow",
        }
        attempt_headers = {**headers, "Idempotency-Key": f"booking-attempt-{attempt}"}
        response = logged_in.post("/booking/v1/bookings", json=body, headers=attempt_headers)
        assert response.status_code == 201, response.text
        repeated = logged_in.post("/booking/v1/bookings", json=body, headers=attempt_headers)
        assert repeated.status_code == 201
        assert repeated.json()["id"] == response.json()["id"]
    blocked = logged_in.post(
        "/booking/v1/bookings",
        json={
            "lead_id": "lead-42",
            "name": "Анна",
            "email": "wrong@example.com",
            "start": next_slot(5).isoformat(),
            "timezone": "Europe/Moscow",
        },
        headers={**headers, "Idempotency-Key": "booking-attempt-4"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "booking_attempt_limit_reached"
    assert counter == 3


def test_busy_slot_does_not_consume_attempt(logged_in, monkeypatch):
    key = configure(logged_in)
    start = next_slot()

    async def token(*_args):
        return "provider-token"

    busy = True

    async def events(*_args):
        if not busy:
            return []
        return [
            {
                "start": {"dateTime": start.isoformat()},
                "end": {"dateTime": (start + timedelta(minutes=30)).isoformat()},
            }
        ]

    async def create(*_args):
        return {"id": "event-ok"}

    monkeypatch.setattr(booking, "valid_access_token", token)
    monkeypatch.setattr(booking, "list_calendar_events", events)
    monkeypatch.setattr(booking, "create_calendar_event", create)
    body = {
        "lead_id": "retryable",
        "name": "Иван",
        "email": "ivan@example.com",
        "start": start.isoformat(),
        "timezone": "Europe/Moscow",
    }
    headers = {"Authorization": f"Bearer {key}", "Idempotency-Key": "retry-busy-slot"}
    assert logged_in.post("/booking/v1/bookings", json=body, headers=headers).status_code == 409
    busy = False
    assert logged_in.post("/booking/v1/bookings", json=body, headers=headers).status_code == 201


def test_booking_always_checks_google_and_uses_selected_telemost(logged_in, monkeypatch):
    key = configure(logged_in, "yandex")
    assert logged_in.put(
        "/api/v1/preferences",
        json={
            "default_calendar": "microsoft",
            "default_mail": "google",
            "default_conference": "none",
            "default_reminder_minutes": 5,
            "fallback_teams_url": "",
            "fallback_telemost_url": "https://telemost.yandex.ru/j/test-room",
        },
    ).status_code == 200
    providers = []
    created_payload = {}

    async def token(_db, _settings, _user, provider):
        providers.append(provider)
        return "provider-token"

    async def events(provider, *_args):
        providers.append(provider)
        return []

    async def create(provider, _token, payload):
        providers.append(provider)
        created_payload.update(payload)
        return {"id": "google-event", "htmlLink": "https://calendar.google.test/event"}

    monkeypatch.setattr(booking, "valid_access_token", token)
    monkeypatch.setattr(booking, "list_calendar_events", events)
    monkeypatch.setattr(booking, "create_calendar_event", create)
    response = logged_in.post(
        "/booking/v1/bookings",
        json={
            "lead_id": "telemost-lead",
            "name": "Анна",
            "email": "anna@example.com",
            "start": next_slot().isoformat(),
            "timezone": "Europe/Moscow",
        },
        headers={"Authorization": f"Bearer {key}", "Idempotency-Key": "telemost-booking"},
    )
    assert response.status_code == 201, response.text
    assert set(providers) == {"google"}
    assert created_payload["conference"] == "none"
    assert created_payload["external_join_url"] == "https://telemost.yandex.ru/j/test-room"

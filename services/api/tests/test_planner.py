from app.agenda import provider_event


def test_local_task_and_timer(logged_in):
    task = logged_in.post("/api/v1/tasks", json={"title": "Подготовить план"})
    assert task.status_code == 200
    assert task.json()["title"] == "Подготовить план"
    timer = logged_in.post("/api/v1/timers", json={"title": "Фокус", "duration_seconds": 1500})
    assert timer.status_code == 200
    today = logged_in.get("/api/v1/today")
    assert today.status_code == 200
    assert {item["kind"] for item in today.json()["items"]} == {"task", "timer"}
    week = logged_in.get("/api/v1/week")
    assert week.status_code == 200
    assert {item["kind"] for item in week.json()["items"]} == {"task", "timer"}


def test_google_agenda_event_keeps_time_links_attendees_and_reminder():
    item = provider_event("google", {
        "id": "event-1", "summary": "Встреча", "status": "confirmed",
        "start": {"dateTime": "2026-08-03T15:30:00+03:00"},
        "end": {"dateTime": "2026-08-03T16:00:00+03:00"},
        "attendees": [{"email": "guest@example.com"}],
        "location": "https://telemost.yandex.ru/j/123",
        "htmlLink": "https://calendar.google.com/event/1",
        "reminders": {"overrides": [{"method": "popup", "minutes": 5}]},
    })
    assert item["join_url"] == "https://telemost.yandex.ru/j/123"
    assert item["edit_url"].startswith("https://calendar.google.com/")
    assert item["attendees"] == ["guest@example.com"]
    assert item["reminder_minutes"] == 5


def test_requires_login(client):
    for path in ("/api/v1/tasks", "/api/v1/today", "/api/v1/week", "/api/v1/integrations", "/api/v1/audit"):
        assert client.get(path).status_code == 401

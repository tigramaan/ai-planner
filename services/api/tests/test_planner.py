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


def test_requires_login(client):
    for path in ("/api/v1/tasks", "/api/v1/today", "/api/v1/week", "/api/v1/integrations", "/api/v1/audit"):
        assert client.get(path).status_code == 401

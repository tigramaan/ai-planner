def register(client, email):
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "family-member-strong-password",
            "registration_code": "family-registration-code-2026",
        },
    )
    assert response.status_code == 201


def login(client, email):
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "family-member-strong-password"},
    )
    assert response.status_code == 200


def test_owner_and_member_collaborate_on_task(client):
    register(client, "owner@example.com")
    task = client.post("/api/v1/tasks", json={"title": "Покупки"}).json()
    register(client, "wife@example.com")
    login(client, "owner@example.com")

    shared = client.post(
        f"/api/v1/tasks/{task['id']}/participants",
        json={"email": "wife@example.com"},
    )
    assert shared.status_code == 201
    assert shared.json()["participants"][0]["email"] == "wife@example.com"

    login(client, "wife@example.com")
    visible = client.get("/api/v1/tasks").json()
    assert [row["title"] for row in visible] == ["Покупки"]
    assert visible[0]["is_owner"] is False
    assert any(row["id"] == task["id"] for row in client.get("/api/v1/today").json()["items"])
    assert client.post(f"/api/v1/tasks/{task['id']}/checklist", json={"text": " "}).status_code == 422
    item = client.post(
        f"/api/v1/tasks/{task['id']}/checklist", json={"text": "Молоко"}
    )
    assert item.status_code == 201
    item_id = item.json()["checklist"][0]["id"]
    checked = client.put(
        f"/api/v1/tasks/{task['id']}/checklist/{item_id}", json={"completed": True}
    )
    assert checked.status_code == 200
    assert checked.json()["checklist"][0]["completed"] is True
    assert client.put(f"/api/v1/tasks/{task['id']}", json={"description": "На неделю"}).status_code == 200
    assert client.delete(f"/api/v1/tasks/{task['id']}").status_code == 404

    participant_id = checked.json()["participants"][0]["id"]
    left = client.delete(f"/api/v1/tasks/{task['id']}/participants/{participant_id}")
    assert left.status_code == 200
    assert client.get("/api/v1/tasks").json() == []

    login(client, "owner@example.com")
    owner_view = client.get("/api/v1/tasks").json()[0]
    assert owner_view["description"] == "На неделю"
    assert owner_view["checklist"][0]["text"] == "Молоко"
    assert any(row["actor_email"] == "wife@example.com" for row in owner_view["activity"])


def test_only_owner_can_manage_participants(client):
    register(client, "owner2@example.com")
    task = client.post("/api/v1/tasks", json={"title": "Общая"}).json()
    register(client, "member@example.com")
    register(client, "third@example.com")
    login(client, "owner2@example.com")
    client.post(
        f"/api/v1/tasks/{task['id']}/participants", json={"email": "member@example.com"}
    )
    login(client, "member@example.com")
    forbidden = client.post(
        f"/api/v1/tasks/{task['id']}/participants", json={"email": "third@example.com"}
    )
    assert forbidden.status_code == 404
    login(client, "owner2@example.com")
    participant_id = client.get("/api/v1/tasks").json()[0]["participants"][0]["id"]
    assert client.delete(f"/api/v1/tasks/{task['id']}/participants/{participant_id}").status_code == 200
    login(client, "member@example.com")
    assert client.get("/api/v1/tasks").json() == []


def test_member_edits_shared_task_through_chat_action(client):
    register(client, "chat-owner@example.com")
    task = client.post("/api/v1/tasks", json={"title": "Покупки"}).json()
    register(client, "chat-member@example.com")
    login(client, "chat-owner@example.com")
    assert client.post(
        f"/api/v1/tasks/{task['id']}/participants",
        json={"email": "chat-member@example.com"},
    ).status_code == 201

    with SessionLocal() as db:
        member = db.scalar(select(User).where(User.email == "chat-member@example.com"))
        answer = task_action(
            db,
            member,
            Intent(intent="update_task", event_query="Покупки", body="Молоко и кофе"),
            "Добавь молоко и кофе в Покупки",
            True,
        )
        db.commit()
        assert answer == "Задача «Покупки» изменена."
        assert db.get(LocalTask, task["id"]).description == "Молоко и кофе"
        assert db.scalar(
            select(TaskActivity).where(
                TaskActivity.task_id == task["id"],
                TaskActivity.actor_user_id == member.id,
                TaskActivity.action == "updated",
            )
        )

        denied = task_action(
            db,
            member,
            Intent(intent="delete_task", event_query="Покупки"),
            "Удали Покупки",
            True,
        )
        assert denied == "Удалить общую задачу может только её владелец."
        assert db.get(LocalTask, task["id"]) is not None
from sqlalchemy import select

from app.database import SessionLocal
from app.local_chat_actions import task_action
from app.models import LocalTask, TaskActivity, User
from app.schemas import Intent

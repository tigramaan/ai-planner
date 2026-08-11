from app.routers import chat as chat_router


def test_confirmation_without_active_draft_is_not_parsed_as_new_meeting(
    logged_in, monkeypatch
):
    async def unexpected_intent(*args, **kwargs):
        raise AssertionError("confirmation must not be sent to intent extraction")

    monkeypatch.setattr(chat_router, "extract_intent", unexpected_intent)
    response = logged_in.post(
        "/api/v1/chat/messages",
        json={"text": "Подтверждаю"},
        headers={"Accept-Language": "ru"},
    )

    assert response.status_code == 200
    assert "Нет активного черновика" in response.json()["message"]
    assert response.json()["pending_action_id"] is None

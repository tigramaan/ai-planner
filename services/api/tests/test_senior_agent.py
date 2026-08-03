import json

import pytest

from app import senior_agent


@pytest.mark.anyio
async def test_senior_agent_uses_tool_output_in_next_round(monkeypatch):
    requests = []

    class Call:
        type = "function_call"
        name = "inspect_mail"
        call_id = "call-1"
        arguments = json.dumps({"request": "today", "mode": "triage"})

    class Responses:
        async def create(self, **kwargs):
            requests.append(kwargs)
            if len(requests) == 1:
                return type("Response", (), {"output": [Call()], "output_text": ""})()
            return type("Response", (), {"output": [], "output_text": "Готово"})()

    class Client:
        def __init__(self, **kwargs):
            self.responses = Responses()

    async def execute(*args, **kwargs):
        return "Одно важное письмо", None

    monkeypatch.setattr(senior_agent, "AsyncOpenAI", Client)
    monkeypatch.setattr(senior_agent, "_execute_tool", execute)
    user = type("User", (), {})()
    result = await senior_agent.run_senior_agent(
        object(),
        object(),
        user,
        {"api_key": "key", "senior_model": "sol", "senior_reasoning_effort": "medium"},
        "Разбери почту и поставь задачу",
        [],
        "ru",
    )

    assert result.answer == "Готово"
    assert result.pending_action is None
    assert requests[0]["store"] is False
    assert requests[0]["parallel_tool_calls"] is False
    outputs = requests[1]["input"]
    assert any(item.get("output") == "Одно важное письмо" for item in outputs if isinstance(item, dict))


@pytest.mark.anyio
async def test_senior_agent_returns_pending_action_without_executing_it(monkeypatch):
    requests = []
    pending = type("Pending", (), {"id": "pending-1"})()

    class Call:
        type = "function_call"
        name = "prepare_external_action"
        call_id = "call-1"
        arguments = "{}"

    class Responses:
        async def create(self, **kwargs):
            requests.append(kwargs)
            if len(requests) == 1:
                return type("Response", (), {"output": [Call()], "output_text": ""})()
            return type(
                "Response",
                (),
                {"output": [], "output_text": "Черновик готов. Подтвердите отправку."},
            )()

    class Client:
        def __init__(self, **kwargs):
            self.responses = Responses()

    async def execute(*args, **kwargs):
        return '{"status":"awaiting_user_confirmation"}', pending

    monkeypatch.setattr(senior_agent, "AsyncOpenAI", Client)
    monkeypatch.setattr(senior_agent, "_execute_tool", execute)
    result = await senior_agent.run_senior_agent(
        object(),
        object(),
        type("User", (), {})(),
        {"api_key": "key", "senior_model": "sol", "senior_reasoning_effort": "medium"},
        "Изучи письмо и подготовь ответ",
        [],
        "ru",
    )

    assert result.pending_action is pending
    assert "Подтвердите" in result.answer
    assert requests[0]["parallel_tool_calls"] is False
    assert any(tool["name"] == "prepare_external_action" for tool in requests[0]["tools"])

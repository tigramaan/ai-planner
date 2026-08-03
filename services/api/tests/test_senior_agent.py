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
        return "Одно важное письмо"

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

    assert result == "Готово"
    assert requests[0]["store"] is False
    assert requests[0]["parallel_tool_calls"] is False
    outputs = requests[1]["input"]
    assert any(item.get("output") == "Одно важное письмо" for item in outputs if isinstance(item, dict))

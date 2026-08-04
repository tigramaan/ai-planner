import json

import pytest

from app import commitments


@pytest.mark.anyio
async def test_commitment_analysis_is_bounded_grounded_and_not_stored(monkeypatch):
    captured = {}

    class Responses:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return type(
                "Response",
                (),
                {
                    "output_text": json.dumps(
                        {
                            "items": [
                                {
                                    "source": "incoming",
                                    "index": 0,
                                    "category": "awaiting_me",
                                    "title": "Подтвердить договор",
                                    "counterparty": "Анна",
                                    "evidence": "Просит подтвердить договор",
                                    "deadline": None,
                                    "suggested_action": "Ответить",
                                    "covered": False,
                                    "confidence": "high",
                                },
                                {
                                    "source": "incoming",
                                    "index": 99,
                                    "category": "awaiting_me",
                                    "title": "Выдумка",
                                    "counterparty": "",
                                    "evidence": "",
                                    "deadline": None,
                                    "suggested_action": "",
                                    "covered": False,
                                    "confidence": "medium",
                                },
                            ]
                        }
                    )
                },
            )()

    class Client:
        def __init__(self, **kwargs):
            self.responses = Responses()

    monkeypatch.setattr(commitments, "AsyncOpenAI", Client)
    rows = [
        {"id": f"mail-{index}", "from": "anna@example.com", "subject": "Договор", "snippet": "x" * 2000}
        for index in range(20)
    ]
    result = await commitments.analyze_commitments(
        "test-key", "test-model", "low", rows, [], [], [], "ru"
    )

    assert len(result) == 1
    assert result[0]["message_id"] == "mail-0"
    assert captured["store"] is False
    assert captured["reasoning"] == {"effort": "low"}
    supplied = json.loads(captured["input"])
    assert len(supplied["mail"]) == 15
    assert len(supplied["mail"][0]["snippet"]) == 1200
    assert "untrusted data" in captured["instructions"]
    assert captured["text"]["format"]["type"] == "json_schema"

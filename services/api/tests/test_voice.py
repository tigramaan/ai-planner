from app.routers import chat as chat_router


def test_voice_accepts_browser_codec_parameters(logged_in, monkeypatch):
    async def fake_transcribe(api_key, model, filename, content):
        assert filename == "voice.m4a"
        assert content == b"browser-audio"
        return "Поставь встречу завтра"

    monkeypatch.setattr(chat_router, "transcribe", fake_transcribe)
    response = logged_in.post(
        "/api/v1/voice/transcribe",
        files={"audio": ("voice.m4a", b"browser-audio", "audio/mp4;codecs=mp4a.40.2")},
    )
    assert response.status_code == 200
    assert response.json() == {"text": "Поставь встречу завтра"}


def test_voice_accepts_safari_audio_only_mp4(logged_in, monkeypatch):
    async def fake_transcribe(api_key, model, filename, content):
        return "Schedule a meeting tomorrow"

    monkeypatch.setattr(chat_router, "transcribe", fake_transcribe)
    response = logged_in.post(
        "/api/v1/voice/transcribe",
        files={"audio": ("voice.m4a", b"browser-audio", "video/mp4")},
    )
    assert response.status_code == 200

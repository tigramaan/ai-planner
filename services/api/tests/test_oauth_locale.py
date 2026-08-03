from app.config import Settings, get_settings
from app.main import app


def test_oauth_configuration_error_uses_browser_language(logged_in):
    app.dependency_overrides[get_settings] = lambda: Settings(microsoft_client_id="")
    try:
        response = logged_in.post(
            "/api/v1/integrations/microsoft/oauth/start",
            headers={"Accept-Language": "ru"},
            json={"scopes": []},
        )
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 409
    assert response.json()["detail"] == "Клиент Microsoft OAuth не настроен"

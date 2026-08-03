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


def test_zoom_configuration_error_uses_browser_language(logged_in):
    app.dependency_overrides[get_settings] = lambda: Settings(zoom_client_id="")
    try:
        response = logged_in.post(
            "/api/v1/integrations/zoom/oauth/start",
            headers={"Accept-Language": "ru"},
            json={"scopes": ["identity", "meeting"]},
        )
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 409
    assert response.json()["detail"] == "Клиент Zoom OAuth не настроен"


def test_oauth_start_updates_existing_cookies_for_cross_site_return(logged_in):
    app.dependency_overrides[get_settings] = lambda: Settings(google_client_id="client-id")
    try:
        response = logged_in.post(
            "/api/v1/integrations/google/oauth/start",
            json={"scopes": ["identity"]},
        )
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 200
    assert all("SameSite=lax" in value for value in response.headers.get_list("set-cookie"))

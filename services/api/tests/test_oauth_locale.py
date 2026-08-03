def test_oauth_configuration_error_uses_browser_language(logged_in):
    response = logged_in.post(
        "/api/v1/integrations/microsoft/oauth/start",
        headers={"Accept-Language": "ru"},
        json={"scopes": []},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Клиент Microsoft OAuth не настроен"

def test_user_can_select_default_providers(logged_in):
    response = logged_in.put(
        "/api/v1/preferences",
        json={
            "default_calendar": "yandex",
            "default_mail": "yandex",
            "default_conference": "zoom",
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "default_calendar": "yandex",
        "default_mail": "yandex",
        "default_conference": "zoom",
    }
    assert logged_in.get("/api/v1/preferences").json() == response.json()


def test_preferences_reject_unknown_provider(logged_in):
    response = logged_in.put(
        "/api/v1/preferences",
        json={
            "default_calendar": "unknown",
            "default_mail": "google",
            "default_conference": "none",
        },
    )
    assert response.status_code == 422

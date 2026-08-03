def test_user_can_select_default_providers(logged_in):
    response = logged_in.put(
        "/api/v1/preferences",
        json={
            "default_calendar": "yandex",
            "default_mail": "yandex",
            "default_conference": "zoom",
            "fallback_teams_url": "https://teams.microsoft.com/l/meetup-join/example",
            "fallback_telemost_url": "https://telemost.yandex.ru/j/example",
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "default_calendar": "yandex",
        "default_mail": "yandex",
        "default_conference": "zoom",
        "fallback_teams_url": "https://teams.microsoft.com/l/meetup-join/example",
        "fallback_telemost_url": "https://telemost.yandex.ru/j/example",
    }
    assert logged_in.get("/api/v1/preferences").json() == response.json()


def test_preferences_reject_unknown_provider(logged_in):
    response = logged_in.put(
        "/api/v1/preferences",
        json={
            "default_calendar": "unknown",
            "default_mail": "google",
            "default_conference": "none",
            "fallback_teams_url": "",
            "fallback_telemost_url": "",
        },
    )
    assert response.status_code == 422


def test_preferences_reject_untrusted_fallback_url(logged_in):
    response = logged_in.put(
        "/api/v1/preferences",
        json={
            "default_calendar": "google",
            "default_mail": "google",
            "default_conference": "microsoft",
            "fallback_teams_url": "https://evil.example/teams",
            "fallback_telemost_url": "",
        },
    )
    assert response.status_code == 422

from .config import Settings
from .models import User
from .security import decrypt_json, encrypt_json


def _context(user: User, provider: str) -> str:
    return f"conference-fallback:{user.id}:{provider}"


def store_fallback_url(settings: Settings, user: User, provider: str, url: str) -> str | None:
    if not url:
        return None
    return encrypt_json(settings, {"url": url}, _context(user, provider))


def read_fallback_url(settings: Settings, user: User, provider: str) -> str:
    encrypted = (
        user.fallback_teams_url_encrypted
        if provider == "microsoft_teams"
        else user.fallback_telemost_url_encrypted
        if provider == "yandex_telemost"
        else None
    )
    if not encrypted:
        return ""
    return str(decrypt_json(settings, encrypted, _context(user, provider)).get("url", ""))

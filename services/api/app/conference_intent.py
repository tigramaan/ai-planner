import re
from urllib.parse import urlparse


def explicit_conference_provider(text: str) -> str | None:
    normalized = " ".join(text.casefold().replace("ё", "е").split())
    if "телемост" in normalized:
        return "yandex"
    if (
        "яндекс" in normalized
        and "календар" not in normalized
        and any(word in normalized for word in ("встреч", "созвон", "виде"))
    ):
        return "yandex"
    if "zoom" in normalized or "зум" in normalized:
        return "zoom"
    if "teams" in normalized or "тимс" in normalized:
        return "microsoft"
    if "google meet" in normalized or "гугл мит" in normalized:
        return "google"
    return None


def explicit_external_join_url(text: str) -> str | None:
    normalized = text.casefold().replace("ё", "е")
    if not any(marker in normalized for marker in ("ссылк", "подключ", "онлайн", "video", "join")):
        return None
    for match in re.findall(r"https://[^\s<>]+", text, flags=re.IGNORECASE):
        candidate = match.rstrip(".,;:!?)]}»\"")
        parsed = urlparse(candidate)
        if parsed.hostname and not parsed.username and not parsed.password:
            return candidate
    return None


def apply_explicit_conference(intent, text: str) -> None:
    provider = explicit_conference_provider(text)
    external_url = explicit_external_join_url(text)
    if provider:
        intent.conference_requested, intent.conference_provider = True, provider
    if external_url:
        intent.external_join_url = external_url
        intent.conference_requested, intent.conference_provider = False, "none"

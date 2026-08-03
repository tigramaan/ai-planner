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

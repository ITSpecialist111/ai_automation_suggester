"""Language helpers for suggestion prompt localization."""

LANGUAGE_NAMES = {
    "ca": "Catalan",
    "cs": "Czech",
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "it": "Italian",
    "nl": "Dutch",
    "pl": "Polish",
    "pt": "Portuguese",
    "ru": "Russian",
    "tr": "Turkish",
    "zh": "Chinese",
}


def language_name(language_code: str | None) -> str | None:
    """Return a friendly language name from a Home Assistant language code."""

    normalized = str(language_code or "").strip().replace("_", "-").lower()
    if not normalized:
        return None
    base_code = normalized.split("-", 1)[0]
    return LANGUAGE_NAMES.get(base_code, normalized)


def suggestion_language_instruction(language_code: str | None) -> str:
    """Build an instruction that asks providers to localize suggestion text."""

    name = language_name(language_code)
    if not name or name == "English":
        return ""
    return (
        f"Home Assistant configured language: {name}. "
        f"Write suggestion titles, descriptions, and warnings in {name}. "
        "Keep YAML, entity_ids, service names, and code identifiers unchanged."
    )
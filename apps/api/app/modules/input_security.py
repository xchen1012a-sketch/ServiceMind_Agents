import re
from urllib.parse import urlsplit

CONTROL_CHARACTER_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
ALLOWED_STORED_SOURCE_URI_SCHEMES = {"manual", "inline", "kb"}


def validate_business_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise ValueError("text must not be blank")
    if CONTROL_CHARACTER_RE.search(normalized):
        raise ValueError("text contains unsupported control characters")
    return normalized


def validate_stored_source_uri(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = validate_business_text(value)
    if normalized is None:
        return None

    parsed = urlsplit(normalized)
    if parsed.scheme not in ALLOWED_STORED_SOURCE_URI_SCHEMES:
        allowed = ", ".join(sorted(ALLOWED_STORED_SOURCE_URI_SCHEMES))
        raise ValueError(f"source_uri scheme must be one of: {allowed}")
    return normalized

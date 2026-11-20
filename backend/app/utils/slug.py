import re
import unicodedata


def slugify_url_segment(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


def _letters_only_code(value: int) -> str:
    """Encode a positive integer as letters so public links have no numeric tail."""
    if value < 1:
        raise ValueError("value must be positive")
    result = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        result = chr(ord("a") + remainder) + result
    return result


def public_form_duplicate_slug(base: str, ordinal: int) -> str:
    return f"{base}-formulario-{_letters_only_code(ordinal)}"


def public_form_link_slug(public_slug: str, title: str | None = None) -> str:
    """Hide a legacy numeric uniqueness suffix when it is not part of the title."""
    match = re.fullmatch(r"(.+)-([0-9]+)", public_slug)
    if not match:
        return public_slug
    number = int(match.group(2))
    if number < 2:
        return public_slug
    title_slug = slugify_url_segment(title) if title else None
    if title_slug and title_slug != match.group(1):
        return public_slug
    return match.group(1)


def resolve_public_form_link_slug(public_slug: str) -> str | None:
    """Resolve the public-link alias for forms whose stored slug ends in a number."""
    match = re.fullmatch(r"(.+)-formulario-([a-z]+)", public_slug)
    if not match:
        return None
    value = 0
    for character in match.group(2):
        value = value * 26 + ord(character) - ord("a") + 1
    if value < 2:
        return None
    return f"{match.group(1)}-{value}"

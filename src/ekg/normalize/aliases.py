import re


def normalize_name(name: str) -> str:
    return re.sub(r"[^A-Z0-9 ]", "", re.sub(r"\s+", " ", name.upper())).strip()


def apply_alias(name: str, aliases: dict[str, str]) -> str:
    normalized = normalize_name(name)
    mapped = {normalize_name(key): value for key, value in aliases.items()}
    return mapped.get(normalized, name.strip())

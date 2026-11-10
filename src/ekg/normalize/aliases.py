import re


def normalize_name(name: str) -> str:
    return re.sub(r"[^A-Z0-9 ]", "", re.sub(r"\s+", " ", name.upper())).strip()


def apply_alias(name: str, aliases: dict[str, str]) -> str:
    normalized = normalize_name(name)
    mapped = {normalize_name(key): value for key, value in aliases.items()}
    return mapped.get(normalized, name.strip())


def canonical_entity_names(
    name: str, same_as: list[str], aliases: dict[str, str]
) -> tuple[str, list[str]]:
    canonical_name = apply_alias(name, aliases)
    names = {value.strip() for value in [name, canonical_name, *same_as] if value.strip()}
    canonical_labels = {normalize_name(apply_alias(value, aliases)) for value in names}
    names.update(
        alias.strip()
        for alias, target in aliases.items()
        if normalize_name(apply_alias(target, aliases)) in canonical_labels
    )
    return canonical_name, sorted(value for value in names if value != canonical_name)

"""Regex-based parsing for material data (placeholder)."""

from __future__ import annotations

import re

from .exceptions import ParseError
from .models import MaterialData


_MATERIAL_TYPE_LABELS = (
    "material type",
    "typ materialu",
    "rodzaj materialu",
    "nazwa materialu",
    "material",
    "produkt",
)

_DESCRIPTION_LABELS = (
    "description",
    "opis",
)

_FALLBACK_EXCLUDED_LABEL_PREFIXES = (
    "manufacturer",
    "producent",
    "description",
    "opis",
    "material type",
    "typ",
)

_FALLBACK_EXCLUDED_HEADERS = {
    "specyfikacja techniczna",
    "architektura",
    "bezpieczenstwo",
    "bezpieczeństwo",
}


def _normalize_whitespace(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _meaningful_lines(text: str) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not re.search(r"\w", stripped):
            continue
        lines.append(stripped)
    return lines


def _extract_labeled_value(text: str, labels: tuple[str, ...]) -> str | None:
    label_pattern = "|".join(re.escape(label) for label in labels)
    pattern = re.compile(
        rf"(?im)^\s*(?:{label_pattern})\s*[:\-]\s*(.+?)\s*$",
    )
    match = pattern.search(text)
    if not match:
        return None
    value = re.sub(r"\s+", " ", match.group(1)).strip(" .;:-")
    return value or None


def _is_fallback_material_type_candidate(line: str) -> bool:
    lowered = line.strip().lower()
    if not lowered:
        return False

    if lowered in _FALLBACK_EXCLUDED_HEADERS:
        return False

    for prefix in _FALLBACK_EXCLUDED_LABEL_PREFIXES:
        if re.match(rf"^{re.escape(prefix)}\s*[:\-]?\b", lowered):
            return False

    return True


def _extract_material_type(text: str, lines: list[str]) -> str | None:
    labeled = _extract_labeled_value(text, _MATERIAL_TYPE_LABELS)
    if labeled:
        return labeled

    candidates = [line for line in lines if _is_fallback_material_type_candidate(line)]
    if len(candidates) >= 2:
        return candidates[1]
    if candidates:
        return candidates[0]
    return None


def _extract_description(text: str, lines: list[str]) -> str:
    labeled = _extract_labeled_value(text, _DESCRIPTION_LABELS)
    if labeled:
        return labeled

    if lines:
        return " ".join(lines[:3])[:280]

    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return "Brak opisu w dokumentacji"
    return normalized[:280]


def parse_material_from_text(text: str) -> MaterialData:
    """Parse material data from raw text."""

    normalized = _normalize_whitespace(text)
    lines = _meaningful_lines(normalized)

    material_type = _extract_material_type(normalized, lines)

    missing: list[str] = []
    if not material_type:
        missing.append("material_type")
    if missing:
        raise ParseError(
            "Missing required fields: " + ", ".join(missing)
        )

    description = _extract_description(normalized, lines)

    return MaterialData(
        raw_text=normalized,
        material_type=material_type,
        description=description,
    )

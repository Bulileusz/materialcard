"""Regex-based parsing for material data (placeholder)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

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

_MOJIBAKE_MARKERS = (
    "Ã",
    "Å",
    "Ä",
    "â€",
    "â€“",
    "â€”",
)

_COMMON_MOJIBAKE_REPLACEMENTS = {
    "â€”": "—",
    "â€“": "–",
    "â€ž": "„",
    "â€œ": "“",
    "â€": "”",
    "â€™": "’",
    "Å‚": "ł",
    "Å": "Ł",
    "Ä…": "ą",
    "Ä„": "Ą",
    "Ä‡": "ć",
    "Ä†": "Ć",
    "Ä™": "ę",
    "Ä˜": "Ę",
    "Å„": "ń",
    "Åƒ": "Ń",
    "Ã³": "ó",
    "Ã“": "Ó",
    "Å›": "ś",
    "Åš": "Ś",
    "Å¼": "ż",
    "Å»": "Ż",
    "Åº": "ź",
    "Å¹": "Ź",
}


@dataclass(slots=True)
class ParserDiagnosticEvent:
    field_name: str
    step_name: str
    status: str
    matched: bool | None = None
    value_preview: str | None = None
    note: str | None = None


@dataclass(slots=True)
class ParserDiagnostics:
    events: list[ParserDiagnosticEvent] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_event(
        self,
        *,
        field_name: str,
        step_name: str,
        status: str,
        matched: bool | None = None,
        value_preview: str | None = None,
        note: str | None = None,
    ) -> None:
        self.events.append(
            ParserDiagnosticEvent(
                field_name=field_name,
                step_name=step_name,
                status=status,
                matched=matched,
                value_preview=value_preview,
                note=note,
            )
        )

    def add_warning(self, warning: str) -> None:
        self.warnings.append(warning)


def _repair_common_mojibake(text: str) -> str:
    for broken, fixed in _COMMON_MOJIBAKE_REPLACEMENTS.items():
        text = text.replace(broken, fixed)

    if not any(marker in text for marker in _MOJIBAKE_MARKERS):
        return text

    original_score = sum(text.count(marker) for marker in _MOJIBAKE_MARKERS)
    for source_encoding in ("cp1252", "latin-1"):
        try:
            repaired = text.encode(source_encoding).decode("utf-8")
        except UnicodeError:
            continue
        repaired_score = sum(repaired.count(marker) for marker in _MOJIBAKE_MARKERS)
        if repaired_score < original_score:
            return repaired
    return text


def _normalize_parser_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\ufeff", "").replace("\xa0", " ")
    text = _repair_common_mojibake(text)
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


def _preview_value(value: str | None, *, limit: int = 80) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"\s+", " ", value).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


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


def _extract_material_type(
    text: str,
    lines: list[str],
    diagnostics: ParserDiagnostics | None = None,
) -> str | None:
    labeled = _extract_labeled_value(text, _MATERIAL_TYPE_LABELS)
    if diagnostics is not None:
        diagnostics.add_event(
            field_name="material_type",
            step_name="labeled_extraction",
            status="matched" if labeled else "not_matched",
            matched=bool(labeled),
            value_preview=_preview_value(labeled),
        )
    if labeled:
        return labeled

    candidates = [line for line in lines if _is_fallback_material_type_candidate(line)]
    if diagnostics is not None and candidates:
        preview = "; ".join(_preview_value(candidate, limit=40) or "" for candidate in candidates[:3])
        if len(candidates) > 3:
            preview += "; ..."
        diagnostics.add_event(
            field_name="material_type",
            step_name="fallback_candidates",
            status="found",
            matched=True,
            value_preview=preview or None,
            note=f"{len(candidates)} candidate(s)",
        )
    if len(candidates) >= 2:
        if diagnostics is not None:
            diagnostics.add_event(
                field_name="material_type",
                step_name="fallback_selection",
                status="selected",
                matched=True,
                value_preview=_preview_value(candidates[1]),
                note=f"selected candidate 2 of {len(candidates)}",
            )
        return candidates[1]
    if candidates:
        if diagnostics is not None:
            diagnostics.add_event(
                field_name="material_type",
                step_name="fallback_selection",
                status="selected",
                matched=True,
                value_preview=_preview_value(candidates[0]),
                note="selected candidate 1 of 1",
            )
        return candidates[0]
    if diagnostics is not None:
        diagnostics.add_event(
            field_name="material_type",
            step_name="fallback_selection",
            status="no_candidates",
            matched=False,
            note="no fallback candidates available",
        )
    return None


def _extract_description(
    text: str,
    lines: list[str],
    diagnostics: ParserDiagnostics | None = None,
) -> str:
    labeled = _extract_labeled_value(text, _DESCRIPTION_LABELS)
    if diagnostics is not None:
        diagnostics.add_event(
            field_name="description",
            step_name="labeled_extraction",
            status="matched" if labeled else "not_matched",
            matched=bool(labeled),
            value_preview=_preview_value(labeled),
        )
    if labeled:
        return labeled

    if lines:
        fallback = " ".join(lines[:3])[:280]
        if diagnostics is not None:
            diagnostics.add_event(
                field_name="description",
                step_name="fallback_selection",
                status="selected",
                matched=True,
                value_preview=_preview_value(fallback),
                note=f"used first {min(3, len(lines))} meaningful lines",
            )
        return fallback

    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        fallback = "Brak opisu w dokumentacji"
        if diagnostics is not None:
            diagnostics.add_event(
                field_name="description",
                step_name="fallback_selection",
                status="default_placeholder",
                matched=False,
                value_preview=_preview_value(fallback),
                note="input text was empty after normalization",
            )
        return fallback

    fallback = normalized[:280]
    if diagnostics is not None:
        diagnostics.add_event(
            field_name="description",
            step_name="fallback_selection",
            status="selected",
            matched=True,
            value_preview=_preview_value(fallback),
            note="used normalized raw text",
        )
    return fallback


def parse_material_from_text(
    text: str,
    *,
    source_path: str | None = None,
    diagnostics: ParserDiagnostics | None = None,
) -> MaterialData:
    """Parse material data from raw text."""

    normalized = _normalize_parser_text(text)
    lines = _meaningful_lines(normalized)

    material_type = _extract_material_type(normalized, lines, diagnostics=diagnostics)

    missing: list[str] = []
    if not material_type:
        missing.append("material_type")
    if missing:
        if diagnostics is not None:
            diagnostics.add_event(
                field_name="required_fields",
                step_name="missing_required_fields",
                status="failed",
                matched=False,
                note="missing required fields: " + ", ".join(missing),
            )
            diagnostics.add_warning("Missing required fields: " + ", ".join(missing))
        raise ParseError(
            "Missing required fields: " + ", ".join(missing)
        )

    if diagnostics is not None:
        diagnostics.add_event(
            field_name="required_fields",
            step_name="missing_required_fields",
            status="ok",
            matched=True,
            note="all required fields present",
        )

    description = _extract_description(normalized, lines, diagnostics=diagnostics)

    return MaterialData(
        source_path=source_path,
        raw_text=normalized,
        material_type=material_type,
        description=description,
    )

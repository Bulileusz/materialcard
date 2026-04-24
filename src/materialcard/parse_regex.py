"""Regex-based parsing for material data."""

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

_POLISH_DESCRIPTION_SECTION_MARKERS = (
    "opis produktu",
)

_POLISH_DESCRIPTION_SECTION_STOP_MARKERS = (
    "zastosowanie",
    "obrobka",
    "obróbka",
    "dane techniczne",
    "wlasciwosci",
    "właściwości",
)

_POLISH_PRODUCT_TITLE_STOP_MARKERS = (
    "europejska ocena techniczna",
    "deklaracja wlasciwosci uzytkowych",
    "deklaracja właściwości użytkowych",
    "zamierzone zastosowanie",
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

_FALLBACK_NOISE_PHRASES = (
    "karta materialowa",
    "karta produktu",
    "deklaracja właściwości użytkowych",
    "dokumentacja techniczna",
    "strona tytulowa",
    "strona tytułowa",
)

_DECLARATION_PRODUCT_CODE_PREFIX = "niepowtarzalny kod identyfikacyjny typu wyrobu"

_MATERIAL_DESCRIPTION_KEYWORDS = (
    "adhesive",
    "board",
    "cable",
    "cement",
    "facade",
    "fire",
    "insulation",
    "mortar",
    "panel",
    "kabel",
    "plyta",
    "płyta",
    "przewod",
    "przewód",
    "roznicowopradowy",
    "różnicowoprądowy",
    "wylacznik",
    "wyłącznik",
    "zaprawa",
)

_DESCRIPTION_NOISE_PHRASES = (
    *_FALLBACK_NOISE_PHRASES,
    "dane techniczne",
    "technical data",
)

_DESCRIPTION_KEYWORDS = (
    *_MATERIAL_DESCRIPTION_KEYWORDS,
    "assemblies",
    "commercial",
    "elewacyjnych",
    "etics",
    "external",
    "komercyjnych",
    "mieszkaniowych",
    "mocowania",
    "montażu",
    "powierzchniach",
    "rozdzielnicach",
    "stosowania",
    "systems",
    "zatapiania",
)

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
    "Åż": "ż",
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


def _preprocess_parser_input(text: str) -> tuple[str, list[str]]:
    normalized = _normalize_parser_text(text)
    return normalized, _meaningful_lines(normalized)


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
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = pattern.match(line)
        if not match:
            continue

        parts = [match.group(1)]
        for continuation in lines[index + 1 :]:
            if pattern.match(continuation):
                break
            if re.match(r"^\s*[\w /().-]{1,40}\s*[:\-]\s*\S", continuation):
                break
            stripped = continuation.strip()
            if not (
                stripped
                and (stripped[0].islower() or stripped[0].isdigit() or stripped[0] in "(/+")
            ):
                break
            parts.append(stripped)
        value = re.sub(r"\s+", " ", " ".join(parts)).strip(" .;:-")
        return value or None
    return None


def _extract_polish_product_sheet_material_type(text: str) -> str | None:
    lowered = text.lower()
    marker_positions = [
        lowered.find(marker)
        for marker in _POLISH_DESCRIPTION_SECTION_MARKERS
        if lowered.find(marker) != -1
    ]
    if not marker_positions:
        return None

    title_block = re.sub(r"\s+", " ", text[: min(marker_positions)]).strip(" .;:-")
    if not title_block:
        return None

    title_lowered = title_block.lower()
    stop_positions = [
        title_lowered.find(marker)
        for marker in _POLISH_PRODUCT_TITLE_STOP_MARKERS
        if title_lowered.find(marker) != -1
    ]
    if stop_positions:
        title_block = title_block[: min(stop_positions)].strip(" .;:-")

    return title_block or None


def _extract_polish_product_sheet_description(text: str) -> str | None:
    lowered = text.lower()
    marker_matches = [
        (position, marker)
        for marker in _POLISH_DESCRIPTION_SECTION_MARKERS
        if (position := lowered.find(marker)) != -1
    ]
    if not marker_matches:
        return None

    start_position, marker = min(marker_matches, key=lambda item: item[0])
    description_block = text[start_position + len(marker) :]
    description_lowered = description_block.lower()
    stop_positions = [
        description_lowered.find(stop_marker)
        for stop_marker in _POLISH_DESCRIPTION_SECTION_STOP_MARKERS
        if description_lowered.find(stop_marker) != -1
    ]
    if stop_positions:
        description_block = description_block[: min(stop_positions)]

    description = re.sub(r"\s+", " ", description_block).strip(" .;:-")
    return description or None


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


def _score_fallback_material_type_candidate(line: str) -> int:
    stripped = line.strip()
    lowered = stripped.lower()
    words = re.findall(r"\w+", lowered)
    score = 0

    if any(phrase in lowered for phrase in _FALLBACK_NOISE_PHRASES):
        score -= 12
    if re.fullmatch(r"[A-Z0-9][A-Z0-9./+-]*", stripped) and len(stripped) <= 24:
        score -= 8
    if stripped.isupper() and len(words) <= 3:
        score -= 4
    if len(stripped) < 8:
        score -= 3

    if len(words) >= 3:
        score += 4
    if len(stripped) >= 20:
        score += 3
    if any(char.islower() for char in stripped):
        score += 2
    if any(keyword in lowered for keyword in _MATERIAL_DESCRIPTION_KEYWORDS):
        score += 5

    return score


def _extract_declaration_material_type(lines: list[str]) -> str | None:
    if not any("deklaracja właściwości użytkowych" in line.lower() for line in lines[:5]):
        return None

    first_title: str | None = None
    for line in lines[:5]:
        stripped = line.strip()
        lowered = stripped.lower()
        if not stripped:
            continue
        if any(phrase in lowered for phrase in _FALLBACK_NOISE_PHRASES):
            continue
        if lowered.startswith(("nr ", "producent:", "zamierzone zastosowanie")):
            continue
        if ":" in stripped:
            continue
        first_title = stripped
        break

    if first_title is not None:
        return first_title

    for line in lines[:10]:
        lowered = line.lower()
        if lowered.startswith(_DECLARATION_PRODUCT_CODE_PREFIX):
            _, _, value = line.partition(":")
            value = value.strip(" .;:-")
            return value or None

    return None


def _is_catalog_or_product_code(line: str) -> bool:
    stripped = line.strip()
    return bool(re.fullmatch(r"[A-Z0-9][A-Z0-9./+-]*", stripped) and len(stripped) <= 24)


def _score_description_fallback_line(line: str, material_type: str | None) -> int:
    stripped = line.strip()
    lowered = stripped.lower()
    words = re.findall(r"\w+", lowered)
    score = 0

    if not words:
        return -20
    if any(phrase in lowered for phrase in _DESCRIPTION_NOISE_PHRASES):
        score -= 12
    if any(re.match(rf"^{re.escape(prefix)}\s*[:\-]?\b", lowered) for prefix in _FALLBACK_EXCLUDED_LABEL_PREFIXES):
        score -= 10
    if _is_catalog_or_product_code(stripped):
        score -= 10
    if stripped.isupper() and len(words) <= 4:
        score -= 5
    if material_type and lowered == material_type.lower():
        score -= 8
    if len(stripped) < 12:
        score -= 4

    if len(words) >= 5:
        score += 5
    if len(stripped) >= 35:
        score += 3
    if any(char.islower() for char in stripped):
        score += 2
    if any(keyword in lowered for keyword in _DESCRIPTION_KEYWORDS):
        score += 6

    return score


def _select_description_fallback(lines: list[str], material_type: str | None) -> tuple[str, int, int] | None:
    scored = [
        (index, line, _score_description_fallback_line(line, material_type))
        for index, line in enumerate(lines)
    ]
    viable = [(index, line, score) for index, line, score in scored if score > 0]
    if not viable:
        return None

    selected_index, selected_line, selected_score = max(viable, key=lambda item: item[2])
    selected_lines = [selected_line.strip(" .;:-")]
    if selected_index + 1 < len(lines):
        next_line = lines[selected_index + 1]
        next_score = _score_description_fallback_line(next_line, material_type)
        if next_score >= 9:
            selected_lines.append(next_line.strip(" .;:-"))

    fallback = re.sub(r"\s+", " ", " ".join(selected_lines)).strip(" .;:-")
    return fallback, len(viable), selected_score


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

    section_aware = _extract_polish_product_sheet_material_type(text)
    if diagnostics is not None:
        diagnostics.add_event(
            field_name="material_type",
            step_name="section_extraction",
            status="matched" if section_aware else "not_matched",
            matched=bool(section_aware),
            value_preview=_preview_value(section_aware),
            note="activated only for Polish product sheets with 'Opis produktu'",
        )
    if section_aware:
        return section_aware

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
    declaration_material_type = _extract_declaration_material_type(lines)
    if declaration_material_type:
        if diagnostics is not None:
            diagnostics.add_event(
                field_name="material_type",
                step_name="fallback_selection",
                status="selected",
                matched=True,
                value_preview=_preview_value(declaration_material_type),
                note="selected declaration product identifier",
            )
        return declaration_material_type
    if candidates:
        selected = max(candidates, key=_score_fallback_material_type_candidate)
        if diagnostics is not None:
            diagnostics.add_event(
                field_name="material_type",
                step_name="fallback_selection",
                status="selected",
                matched=True,
                value_preview=_preview_value(selected),
                note=(
                    f"selected highest-ranked candidate of {len(candidates)} "
                    f"(score {_score_fallback_material_type_candidate(selected)})"
                ),
            )
        return selected
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
    material_type: str | None = None,
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

    section_aware = _extract_polish_product_sheet_description(text)
    if diagnostics is not None:
        diagnostics.add_event(
            field_name="description",
            step_name="section_extraction",
            status="matched" if section_aware else "not_matched",
            matched=bool(section_aware),
            value_preview=_preview_value(section_aware),
            note="activated only for Polish product sheets with 'Opis produktu'",
        )
    if section_aware:
        return section_aware

    selected = _select_description_fallback(lines, material_type)
    if selected is not None:
        fallback, candidate_count, selected_score = selected
        if diagnostics is not None:
            diagnostics.add_event(
                field_name="description",
                step_name="fallback_selection",
                status="selected",
                matched=True,
                value_preview=_preview_value(fallback),
                note=(
                    f"selected highest-ranked candidate(s) from {candidate_count} "
                    f"line(s) (score {selected_score})"
                ),
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


def _missing_required_fields(*, material_type: str | None) -> list[str]:
    missing: list[str] = []
    if not material_type:
        missing.append("material_type")
    return missing


def _record_missing_required_fields(
    missing: list[str],
    diagnostics: ParserDiagnostics | None,
) -> None:
    if diagnostics is None:
        return
    diagnostics.add_event(
        field_name="required_fields",
        step_name="missing_required_fields",
        status="failed",
        matched=False,
        note="missing required fields: " + ", ".join(missing),
    )
    diagnostics.add_warning("Missing required fields: " + ", ".join(missing))


def _record_required_fields_ok(diagnostics: ParserDiagnostics | None) -> None:
    if diagnostics is None:
        return
    diagnostics.add_event(
        field_name="required_fields",
        step_name="missing_required_fields",
        status="ok",
        matched=True,
        note="all required fields present",
    )


def _require_material_type(
    material_type: str | None,
    diagnostics: ParserDiagnostics | None,
) -> str:
    missing = _missing_required_fields(material_type=material_type)
    if missing:
        _record_missing_required_fields(missing, diagnostics)
        raise ParseError("Missing required fields: " + ", ".join(missing))

    _record_required_fields_ok(diagnostics)
    return material_type


def _extract_material_fields(
    normalized_text: str,
    lines: list[str],
    diagnostics: ParserDiagnostics | None,
) -> tuple[str, str]:
    material_type = _extract_material_type(normalized_text, lines, diagnostics=diagnostics)
    material_type = _require_material_type(material_type, diagnostics)
    description = _extract_description(
        normalized_text,
        lines,
        material_type=material_type,
        diagnostics=diagnostics,
    )
    return material_type, description


def _build_material_data(
    *,
    source_path: str | None,
    raw_text: str,
    material_type: str,
    description: str,
) -> MaterialData:
    return MaterialData(
        source_path=source_path,
        raw_text=raw_text,
        material_type=material_type,
        description=description,
    )


def parse_material_from_text(
    text: str,
    *,
    source_path: str | None = None,
    diagnostics: ParserDiagnostics | None = None,
) -> MaterialData:
    """Parse material data from raw text."""

    normalized, lines = _preprocess_parser_input(text)
    material_type, description = _extract_material_fields(
        normalized,
        lines,
        diagnostics,
    )
    return _build_material_data(
        source_path=source_path,
        raw_text=normalized,
        material_type=material_type,
        description=description,
    )

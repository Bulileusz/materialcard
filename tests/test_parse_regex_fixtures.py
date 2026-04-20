"""Fixture-based parser regression tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from materialcard.exceptions import ParseError
from materialcard.parse_regex import ParserDiagnostics, parse_material_from_text

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "parser"


def _read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("fixture_name", "expected_material_type", "expected_description"),
    [
        (
            "labeled_happy_path.txt",
            "PVC insulation board",
            "Thermal insulation board for foundation walls",
        ),
        (
            "labeled_wrapped_value.txt",
            "Modular fire resistant",
            "Lightweight panel for external wall assemblies",
        ),
        (
            "material_type_fallback.txt",
            "RCBO WyA...cznik rA3A...nicowoprA...dowy z czA...onem nadprA...dowym 1P+N 6kA C 10A/30mA",
            "ADC960D RCBO WyA...cznik rA3A...nicowoprA...dowy z czA...onem nadprA...dowym 1P+N 6kA C 10A/30mA Typ AC",
        ),
        (
            "description_fallback.txt",
            "Cement adhesive mortar",
            "KARTA MATERIALOWA Material type: Cement adhesive mortar Do mocowania plyt termoizolacyjnych i zatapiania siatki",
        ),
    ],
)
def test_parse_material_from_fixture_success_cases(
    fixture_name: str,
    expected_material_type: str,
    expected_description: str,
) -> None:
    result = parse_material_from_text(_read_fixture(fixture_name))

    assert result.material_type == expected_material_type
    assert result.description == expected_description


def test_parse_material_from_fixture_missing_material_type_raises_parse_error() -> None:
    with pytest.raises(ParseError, match="material_type"):
        parse_material_from_text(_read_fixture("missing_material_type.txt"))


def test_parse_material_from_fallback_fixture_records_useful_diagnostics() -> None:
    diagnostics = ParserDiagnostics()

    result = parse_material_from_text(
        _read_fixture("material_type_fallback.txt"),
        diagnostics=diagnostics,
    )

    assert result.material_type
    assert any(
        event.field_name == "material_type"
        and event.step_name == "fallback_candidates"
        and event.status == "found"
        and event.value_preview
        for event in diagnostics.events
    )
    assert any(
        event.field_name == "material_type"
        and event.step_name == "fallback_selection"
        and event.status == "selected"
        and event.value_preview
        for event in diagnostics.events
    )

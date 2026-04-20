"""Parsing tests for deterministic regex parser."""

import pytest

from materialcard.exceptions import ParseError
from materialcard.parse_regex import ParserDiagnostics, parse_material_from_text


def test_parse_material_from_text_happy_path() -> None:
    text = """
    Material type: PVC insulation board
    Description: Thermal insulation board for foundation walls.
    """

    result = parse_material_from_text(text)

    assert result.material_type == "PVC insulation board"
    assert result.description == "Thermal insulation board for foundation walls"


def test_parse_material_from_text_unlabeled_material_type_fallback() -> None:
    text = """
    ADC960D
    RCBO WyÅ‚Ä…cznik rÃ³Å¼nicowoprÄ…dowy z czÅ‚onem nadprÄ…dowym 1P+N 6kA C 10A/30mA
    Typ AC
    Specyfikacja techniczna
    """

    result = parse_material_from_text(text)

    assert result.material_type == "RCBO Wyłącznik różnicowoprądowy z członem nadprądowym 1P+N 6kA C 10A/30mA"
    assert result.description.startswith("ADC960D RCBO Wyłącznik różnicowoprądowy")


def test_parse_material_from_text_missing_material_type() -> None:
    text = """
    Manufacturer: Elektro-Max S.A.
    Description: Power cable for external installation.
    """

    with pytest.raises(ParseError, match="material_type"):
        parse_material_from_text(text)


def test_parse_material_from_text_without_diagnostics_still_works() -> None:
    text = """
    Material type: PVC insulation board
    Description: Thermal insulation board for foundation walls.
    """

    result = parse_material_from_text(text)

    assert result.material_type == "PVC insulation board"
    assert result.description == "Thermal insulation board for foundation walls"


def test_parse_material_from_text_records_labeled_diagnostics() -> None:
    diagnostics = ParserDiagnostics()
    text = """
    Material type: PVC insulation board
    Description: Thermal insulation board for foundation walls.
    """

    result = parse_material_from_text(text, diagnostics=diagnostics)

    assert result.material_type == "PVC insulation board"
    assert any(
        event.field_name == "material_type"
        and event.step_name == "labeled_extraction"
        and event.status == "matched"
        and event.value_preview == "PVC insulation board"
        for event in diagnostics.events
    )
    assert any(
        event.field_name == "description"
        and event.step_name == "labeled_extraction"
        and event.status == "matched"
        for event in diagnostics.events
    )
    assert any(
        event.field_name == "required_fields"
        and event.status == "ok"
        for event in diagnostics.events
    )


def test_parse_material_from_text_records_fallback_diagnostics() -> None:
    diagnostics = ParserDiagnostics()
    text = """
    ADC960D
    RCBO WyÅ‚Ä…cznik rÃ³Å¼nicowoprÄ…dowy z czÅ‚onem nadprÄ…dowym 1P+N 6kA C 10A/30mA
    Typ AC
    Specyfikacja techniczna
    """

    result = parse_material_from_text(text, diagnostics=diagnostics)

    assert result.material_type == "RCBO Wyłącznik różnicowoprądowy z członem nadprądowym 1P+N 6kA C 10A/30mA"
    assert any(
        event.field_name == "material_type"
        and event.step_name == "labeled_extraction"
        and event.status == "not_matched"
        for event in diagnostics.events
    )
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
    assert any(
        event.field_name == "description"
        and event.step_name == "fallback_selection"
        and event.status == "selected"
        for event in diagnostics.events
    )


def test_parse_material_from_text_records_missing_required_field_diagnostics() -> None:
    diagnostics = ParserDiagnostics()
    text = """
    Manufacturer: Elektro-Max S.A.
    Description: Power cable for external installation.
    """

    with pytest.raises(ParseError, match="material_type"):
        parse_material_from_text(text, diagnostics=diagnostics)

    assert any(
        event.field_name == "material_type"
        and event.step_name == "fallback_selection"
        and event.status == "no_candidates"
        for event in diagnostics.events
    )
    assert any(
        event.field_name == "required_fields"
        and event.step_name == "missing_required_fields"
        and event.status == "failed"
        and event.note
        for event in diagnostics.events
    )
    assert diagnostics.warnings == ["Missing required fields: material_type"]


def test_parse_material_from_text_repairs_common_mojibake_input() -> None:
    text = "\ufeffMaterial type: Płyta styropianowa\r\nDescription: Płyta elewacyjna â€” fasadowa.\r\n"

    result = parse_material_from_text(text)

    assert result.material_type == "Płyta styropianowa"
    assert result.description == "Płyta elewacyjna — fasadowa"

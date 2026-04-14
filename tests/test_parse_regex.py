"""Parsing tests for deterministic regex parser."""

import pytest

from materialcard.exceptions import ParseError
from materialcard.parse_regex import parse_material_from_text


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
    RCBO Wyłącznik różnicowoprądowy z członem nadprądowym 1P+N 6kA C 10A/30mA
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

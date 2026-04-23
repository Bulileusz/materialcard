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
    assert result.description == result.material_type


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


def test_parse_material_from_text_handles_wrapped_labeled_values() -> None:
    text = """
    Material type: Modular fire resistant
    insulation panel for facade
    systems
    Description: Lightweight panel for external wall assemblies.
    Catalog no: FR-44
    """

    result = parse_material_from_text(text)

    assert result.material_type == "Modular fire resistant insulation panel for facade systems"
    assert result.description == "Lightweight panel for external wall assemblies"


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


@pytest.mark.parametrize(
    ("text", "expected_material_type"),
    [
        (
            """
            KARTA PRODUKTU
            DOKUMENTACJA TECHNICZNA
            Fire resistant insulation board for facade systems
            Specyfikacja techniczna
            """,
            "Fire resistant insulation board for facade systems",
        ),
        (
            """
            ADC960D
            FR-44
            RCBO Wyłącznik różnicowoprądowy z członem nadprądowym 1P+N 6kA C 10A/30mA
            Typ AC
            """,
            "RCBO Wyłącznik różnicowoprądowy z członem nadprądowym 1P+N 6kA C 10A/30mA",
        ),
        (
            """
            STRONA TYTULOWA
            KARTA MATERIALOWA
            Cement adhesive mortar for ETICS facade systems
            Zuzycie okolo 4,5 kg/m2
            """,
            "Cement adhesive mortar for ETICS facade systems",
        ),
    ],
)
def test_parse_material_from_text_ranks_fallback_candidates(
    text: str,
    expected_material_type: str,
) -> None:
    result = parse_material_from_text(text)

    assert result.material_type == expected_material_type


@pytest.mark.parametrize(
    ("text", "expected_description"),
    [
        (
            """
            KARTA PRODUKTU
            ADC960D
            RCBO Wyłącznik różnicowoprądowy z członem nadprądowym 1P+N 6kA C 10A/30mA
            Specyfikacja techniczna
            Do montażu w rozdzielnicach mieszkaniowych i obiektach komercyjnych.
            Prąd znamionowy 10A
            """,
            "Do montażu w rozdzielnicach mieszkaniowych i obiektach komercyjnych",
        ),
        (
            """
            Material type: Cement adhesive mortar
            Dane techniczne
            AM-22
            Do mocowania płyt termoizolacyjnych i zatapiania siatki.
            Na powierzchniach elewacyjnych w systemach ETICS.
            """,
            (
                "Do mocowania płyt termoizolacyjnych i zatapiania siatki "
                "Na powierzchniach elewacyjnych w systemach ETICS"
            ),
        ),
        (
            """
            KARTA MATERIALOWA
            FR-44
            Lightweight fire resistant insulation panel for external wall assemblies.
            Panel kolor biały.
            """,
            "Lightweight fire resistant insulation panel for external wall assemblies",
        ),
    ],
)
def test_parse_material_from_text_selects_useful_description_fallback(
    text: str,
    expected_description: str,
) -> None:
    result = parse_material_from_text(text)

    assert result.description == expected_description


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


def test_parse_material_from_text_repairs_realistic_polish_mojibake_input() -> None:
    text = (
        "Material type: RCBO Wy\xc5\u201a\xc4\u2026cznik r\xc3\xb3\xc5\xbcnicowopr"
        "\xc4\u2026dowy z cz\xc5\u201aonem nadpr\xc4\u2026dowym\n"
        "Description: Do monta\xc5\u017cu w rozdzielnicach \xe2\u20ac\u201d typ AC.\n"
    )

    result = parse_material_from_text(text)

    assert result.material_type == "RCBO Wyłącznik różnicowoprądowy z członem nadprądowym"
    assert result.description == "Do montażu w rozdzielnicach — typ AC"

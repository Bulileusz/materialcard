"""Parser regression tests for real extracted-text fixtures."""

from __future__ import annotations

from pathlib import Path

from materialcard.parse_regex import ParserDiagnostics, parse_material_from_text

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "parser_real"


def _read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def test_parse_real_kafelki_fixture_single_line_product_sheet() -> None:
    diagnostics = ParserDiagnostics()

    result = parse_material_from_text(
        _read_fixture("kafelki.txt"),
        source_path=str(FIXTURES_DIR / "kafelki.txt"),
        diagnostics=diagnostics,
    )

    assert result.material_type.startswith(
        "TUBADZIN Mono Szare Jasne R Płytka podłogowa 200 x 200 mm"
    )
    assert "Typ produktu: Płytki gresowe uniwersalne" in result.description
    assert any(
        event.field_name == "material_type"
        and event.step_name == "fallback_selection"
        and event.status == "selected"
        for event in diagnostics.events
    )


def test_parse_real_baumit_fixture_expected_product_and_use_description() -> None:
    result = parse_material_from_text(_read_fixture("baumit.txt"))

    assert result.material_type == "Baumit Solido 225"
    assert "Sucha, cementowa mieszanka do wykonywania jastrychów" in result.description


def test_parse_real_dachpodloga_fixture_expected_product_and_use_description() -> None:
    result = parse_material_from_text(_read_fixture("dachpodloga.txt"))

    assert result.material_type == "EPS 100-036 DACH-PODŁOGA"
    assert "Izolacja cieplna w budownictwie" in result.description


def test_parse_real_promatecth_fixture_expected_product_and_description() -> None:
    result = parse_material_from_text(_read_fixture("promatecth.txt"))

    assert result.material_type == "PROMATECT-H płyta ogniochronna"
    assert result.description.startswith(
        "Ogniochronne płyty silikatowo-cementowe, niewrażliwe na wilgoć"
    )

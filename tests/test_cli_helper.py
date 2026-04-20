"""Focused tests for CLI PDF parsing helper."""

from pathlib import Path

from materialcard.cli import _parse_material_from_pdf
from materialcard.models import MaterialData


def test_parse_material_from_pdf_reuses_shared_chain(monkeypatch) -> None:
    pdf_path = Path("docs/input.pdf")
    calls: list[tuple[str, object]] = []

    def fake_extract(path: Path) -> str:
        calls.append(("extract", path))
        return "raw pdf text"

    def fake_ensure(text: str, *, min_chars: int) -> str:
        calls.append(("ensure", text, min_chars))
        return "normalized text"

    def fake_parse(
        text: str,
        *,
        source_path: str | None = None,
        diagnostics=None,
    ) -> MaterialData:
        calls.append(("parse", text, source_path, diagnostics))
        return MaterialData(
            source_path=source_path,
            raw_text=text,
            material_type="Material",
            description="Desc",
        )

    monkeypatch.setattr("materialcard.cli.extract_text_from_pdf", fake_extract)
    monkeypatch.setattr("materialcard.cli.ensure_text_pdf", fake_ensure)
    monkeypatch.setattr("materialcard.cli.parse_material_from_text", fake_parse)

    result = _parse_material_from_pdf(pdf_path, 123)

    assert result.source_path == str(pdf_path)
    assert calls == [
        ("extract", pdf_path),
        ("ensure", "raw pdf text", 123),
        ("parse", "normalized text", str(pdf_path), None),
    ]

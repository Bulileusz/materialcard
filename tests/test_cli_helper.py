"""Focused tests for CLI PDF parsing helper."""

from pathlib import Path

import pytest

from materialcard.cli import (
    _default_context_candidates,
    _default_output_path,
    _parse_material_from_pdf,
    _resolve_context_path,
    _resolve_output_path,
)
from materialcard.exceptions import ContextError
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


def test_default_output_path_reuses_pdf_name_in_same_folder() -> None:
    pdf_path = Path("docs/input.pdf")

    assert _default_output_path(pdf_path) == Path("docs/input.docx")


def test_default_context_candidates_prefer_pdf_folder_then_cwd(monkeypatch, tmp_path) -> None:
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    pdf_path = pdf_dir / "input.pdf"
    monkeypatch.chdir(tmp_path)

    assert _default_context_candidates(pdf_path) == (
        pdf_dir / "context.json",
        tmp_path / "context.json",
    )


def test_resolve_context_path_uses_context_next_to_pdf(monkeypatch, tmp_path) -> None:
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    pdf_path = pdf_dir / "input.pdf"
    local_context = pdf_dir / "context.json"
    local_context.write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert _resolve_context_path(pdf_path, None) == local_context


def test_resolve_context_path_falls_back_to_cwd(monkeypatch, tmp_path) -> None:
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    pdf_path = pdf_dir / "input.pdf"
    cwd_context = tmp_path / "context.json"
    cwd_context.write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert _resolve_context_path(pdf_path, None) == cwd_context


def test_resolve_context_path_raises_clear_error_when_missing(monkeypatch, tmp_path) -> None:
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    pdf_path = pdf_dir / "input.pdf"
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ContextError, match="Add context.json next to the PDF"):
        _resolve_context_path(pdf_path, None)


def test_resolve_output_path_uses_explicit_value_when_provided() -> None:
    pdf_path = Path("docs/input.pdf")
    output_path = Path("custom/result.docx")

    assert _resolve_output_path(pdf_path, output_path) == output_path

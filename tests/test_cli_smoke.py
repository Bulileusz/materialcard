"""CLI smoke tests."""

import json
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

from materialcard.cli import app
from materialcard.exceptions import NonTextPdfError, ParseError
from materialcard.models import ApprovalContext, ApprovalRequestData, MaterialData
from materialcard.parse_regex import ParserDiagnostics


@contextmanager
def _fake_as_file(path: Path):
    yield path


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Options" in result.output


def test_module_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "materialcard", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_parse_debug_emits_diagnostics(monkeypatch) -> None:
    def fake_parse_material_from_pdf(
        pdf_path: Path,
        min_chars: int,
        *,
        diagnostics: ParserDiagnostics | None = None,
    ) -> MaterialData:
        assert pdf_path == Path("input.pdf")
        assert min_chars == 200
        assert diagnostics is not None
        diagnostics.add_event(
            field_name="material_type",
            step_name="labeled_extraction",
            status="matched",
            matched=True,
            value_preview="Material",
            note="debug test",
        )
        return MaterialData(
            source_path=str(pdf_path),
            raw_text="raw",
            material_type="Material",
            description="Desc",
        )

    monkeypatch.setattr("materialcard.cli._parse_material_from_pdf", fake_parse_material_from_pdf)

    runner = CliRunner()
    result = runner.invoke(app, ["parse", "input.pdf", "--debug"])

    assert result.exit_code == 0
    assert '"material_type": "Material"' in result.output
    assert "Parser diagnostics:" in result.output
    assert "material_type.labeled_extraction: matched" in result.output


def test_parse_debug_failure_emits_error_and_diagnostics(monkeypatch) -> None:
    def fake_parse_material_from_pdf(
        pdf_path: Path,
        min_chars: int,
        *,
        diagnostics: ParserDiagnostics | None = None,
    ) -> MaterialData:
        assert pdf_path == Path("input.pdf")
        assert min_chars == 200
        assert diagnostics is not None
        diagnostics.add_event(
            field_name="material_type",
            step_name="fallback_selection",
            status="no_candidates",
            matched=False,
            note="debug failure test",
        )
        raise ParseError("Missing required fields: material_type")

    monkeypatch.setattr("materialcard.cli._parse_material_from_pdf", fake_parse_material_from_pdf)

    runner = CliRunner()
    result = runner.invoke(app, ["parse", "input.pdf", "--debug"])

    assert result.exit_code != 0
    assert "Missing required fields: material_type" in result.output
    assert "Parser diagnostics:" in result.output
    assert "material_type.fallback_selection: no_candidates" in result.output


def test_parse_non_text_pdf_shows_scan_diagnosis_and_writes_extracted_dump(monkeypatch, tmp_path) -> None:
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_text("pdf", encoding="utf-8")

    def fake_parse_material_from_pdf(
        pdf_path: Path,
        min_chars: int,
        *,
        diagnostics: ParserDiagnostics | None = None,
    ) -> MaterialData:
        raise NonTextPdfError(
            "PDF text too short: 5 chars (min 200).",
            extracted_text="abc 123",
        )

    monkeypatch.setattr("materialcard.cli._parse_material_from_pdf", fake_parse_material_from_pdf)

    runner = CliRunner()
    result = runner.invoke(app, ["parse", str(pdf_path)])

    assert result.exit_code == 2
    assert "PDF wygląda na skan (brak warstwy tekstowej)." in result.output
    assert "Zeskanuj do PDF z OCR / użyj wersji programu z OCR (planowane)." in result.output
    assert "scan_extracted.txt" in result.output
    assert (tmp_path / "scan_extracted.txt").read_text(encoding="utf-8") == "abc 123"


def test_generate_non_text_pdf_shows_scan_diagnosis_and_writes_extracted_dump(monkeypatch, tmp_path) -> None:
    pdf_path = tmp_path / "scan.pdf"
    context_path = tmp_path / "context.json"
    default_template = tmp_path / "default.docx"
    pdf_path.write_text("pdf", encoding="utf-8")
    context_path.write_text("{}", encoding="utf-8")
    default_template.write_text("template", encoding="utf-8")

    def fake_generate_docx_from_pdf(
        pdf: Path,
        context: Path,
        template: Path,
        output: Path,
        *,
        min_chars: int = 200,
        context_data=None,
    ) -> ApprovalRequestData:
        raise NonTextPdfError(
            "PDF text too short: 5 chars (min 200).",
            extracted_text="partial text",
        )

    monkeypatch.setattr("materialcard.cli.generate_docx_from_pdf", fake_generate_docx_from_pdf)
    monkeypatch.setattr("materialcard.cli._default_template_resource", lambda: SimpleNamespace())
    monkeypatch.setattr("materialcard.cli.as_file", lambda resource: _fake_as_file(default_template))

    runner = CliRunner()
    result = runner.invoke(app, ["generate", str(pdf_path)])

    assert result.exit_code == 2
    assert "PDF wygląda na skan (brak warstwy tekstowej)." in result.output
    assert "Zeskanuj do PDF z OCR / użyj wersji programu z OCR (planowane)." in result.output
    assert "scan_extracted.txt" in result.output
    assert (tmp_path / "scan_extracted.txt").read_text(encoding="utf-8") == "partial text"


def test_generate_uses_default_paths_for_context_template_and_output(monkeypatch, tmp_path) -> None:
    pdf_path = tmp_path / "input.pdf"
    context_path = tmp_path / "context.json"
    default_template = tmp_path / "default.docx"
    pdf_path.write_text("pdf", encoding="utf-8")
    context_path.write_text("{}", encoding="utf-8")
    default_template.write_text("template", encoding="utf-8")
    calls: list[tuple[Path, Path, Path, Path, int]] = []

    def fake_generate_docx_from_pdf(
        pdf: Path,
        context: Path,
        template: Path,
        output: Path,
        *,
        min_chars: int = 200,
        context_data=None,
    ) -> ApprovalRequestData:
        assert context_data is None
        calls.append((pdf, context, template, output, min_chars))
        return ApprovalRequestData(
            investor_name="Investor",
            project_title="Project",
            contractor_name="Contractor",
            material_type="Material",
            manufacturer="Manufacturer",
            estimated_quantity="10",
            description="Desc",
            planned_delivery_date="2026-03-12",
            planned_installation_date="2026-03-13",
            attachments=[],
            prepared_by_name="Prepared",
            prepared_by_role="Role",
        )

    monkeypatch.setattr("materialcard.cli.generate_docx_from_pdf", fake_generate_docx_from_pdf)
    monkeypatch.setattr("materialcard.cli._default_template_resource", lambda: SimpleNamespace())
    monkeypatch.setattr("materialcard.cli.as_file", lambda resource: _fake_as_file(default_template))

    runner = CliRunner()
    result = runner.invoke(app, ["generate", str(pdf_path)])

    assert result.exit_code == 0
    assert calls == [
        (pdf_path, context_path, default_template, tmp_path / "input.docx", 200),
    ]
    assert str(tmp_path / "input.docx") in result.output


def test_generate_missing_default_context_returns_readable_error(monkeypatch, tmp_path) -> None:
    pdf_path = tmp_path / "input.pdf"
    default_template = tmp_path / "default.docx"
    pdf_path.write_text("pdf", encoding="utf-8")
    default_template.write_text("template", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("materialcard.cli._default_template_resource", lambda: SimpleNamespace())
    monkeypatch.setattr("materialcard.cli.as_file", lambda resource: _fake_as_file(default_template))

    runner = CliRunner()
    result = runner.invoke(app, ["generate", str(pdf_path)])

    assert result.exit_code == 3
    assert "Add context.json next to the PDF" in result.output


def test_batch_loads_context_once(monkeypatch, tmp_path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    template_path = tmp_path / "template.docx"
    context_path = tmp_path / "context.json"
    input_dir.mkdir()
    output_dir.mkdir()
    template_path.write_text("template", encoding="utf-8")
    context_path.write_text("{}", encoding="utf-8")
    (input_dir / "one.pdf").write_text("pdf", encoding="utf-8")
    (input_dir / "two.pdf").write_text("pdf", encoding="utf-8")

    calls: list[tuple[str, object]] = []
    shared_context = ApprovalContext(
        investor_name="Investor",
        project_title="Project",
        contractor_name="Contractor",
        manufacturer="Manufacturer",
        estimated_quantity="10",
        planned_delivery_date="2026-03-12",
        planned_installation_date="2026-03-13",
        prepared_by_name="Prepared",
        prepared_by_role="Role",
        attachments=[],
    )
    shared_material = MaterialData(
        source_path="",
        raw_text="raw",
        material_type="Material",
        description="Desc",
        attachments=[],
    )
    shared_approval = ApprovalRequestData(
        investor_name="Investor",
        project_title="Project",
        contractor_name="Contractor",
        material_type="Material",
        manufacturer="Manufacturer",
        estimated_quantity="10",
        description="Desc",
        planned_delivery_date="2026-03-12",
        planned_installation_date="2026-03-13",
        attachments=[],
        attachments_text="â€”",
        prepared_by_name="Prepared",
        prepared_by_role="Role",
    )

    def fake_load_context(path: Path) -> ApprovalContext:
        calls.append(("load_context", path))
        return shared_context

    def fake_generate_docx_from_pdf(
        pdf_path: Path,
        context_path_arg: Path,
        template: Path,
        output: Path,
        *,
        min_chars: int = 200,
        context_data: ApprovalContext | None = None,
    ) -> ApprovalRequestData:
        calls.append(
            (
                "generate_docx_from_pdf",
                pdf_path,
                context_path_arg,
                template,
                output,
                min_chars,
                context_data,
            )
        )
        output.write_text("docx", encoding="utf-8")
        return shared_approval

    monkeypatch.setattr("materialcard.cli.load_context", fake_load_context)
    monkeypatch.setattr("materialcard.cli.generate_docx_from_pdf", fake_generate_docx_from_pdf)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["batch", str(input_dir), str(output_dir), "--context", str(context_path), "--template", str(template_path)],
    )

    assert result.exit_code == 0
    assert [call for call in calls if call[0] == "load_context"] == [("load_context", context_path)]
    service_calls = [call for call in calls if call[0] == "generate_docx_from_pdf"]
    assert len(service_calls) == 2
    assert all(call[6] is shared_context for call in service_calls)


def test_batch_uses_shared_parse_helper_with_min_chars(monkeypatch, tmp_path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    template_path = tmp_path / "template.docx"
    context_path = tmp_path / "context.json"
    input_dir.mkdir()
    output_dir.mkdir()
    template_path.write_text("template", encoding="utf-8")
    context_path.write_text("{}", encoding="utf-8")
    pdf_path = input_dir / "one.pdf"
    pdf_path.write_text("pdf", encoding="utf-8")

    shared_context = ApprovalContext(
        investor_name="Investor",
        project_title="Project",
        contractor_name="Contractor",
        manufacturer="Manufacturer",
        estimated_quantity="10",
        planned_delivery_date="2026-03-12",
        planned_installation_date="2026-03-13",
        prepared_by_name="Prepared",
        prepared_by_role="Role",
        attachments=[],
    )
    shared_material = MaterialData(
        source_path="",
        raw_text="raw",
        material_type="Material",
        description="Desc",
        attachments=[],
    )
    shared_approval = ApprovalRequestData(
        investor_name="Investor",
        project_title="Project",
        contractor_name="Contractor",
        material_type="Material",
        manufacturer="Manufacturer",
        estimated_quantity="10",
        description="Desc",
        planned_delivery_date="2026-03-12",
        planned_installation_date="2026-03-13",
        attachments=[],
        attachments_text="â€”",
        prepared_by_name="Prepared",
        prepared_by_role="Role",
    )
    service_calls: list[tuple[Path, Path, Path, Path, int, ApprovalContext | None]] = []

    def fake_load_context(path: Path) -> ApprovalContext:
        return shared_context

    def fake_generate_docx_from_pdf(
        pdf_path: Path,
        context_path_arg: Path,
        template: Path,
        output: Path,
        *,
        min_chars: int = 200,
        context_data: ApprovalContext | None = None,
    ) -> ApprovalRequestData:
        service_calls.append((pdf_path, context_path_arg, template, output, min_chars, context_data))
        output.write_text("docx", encoding="utf-8")
        return shared_approval

    monkeypatch.setattr("materialcard.cli.load_context", fake_load_context)
    monkeypatch.setattr("materialcard.cli.generate_docx_from_pdf", fake_generate_docx_from_pdf)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "batch",
            str(input_dir),
            str(output_dir),
            "--context",
            str(context_path),
            "--template",
            str(template_path),
            "--min-chars",
            "321",
        ],
    )

    assert result.exit_code == 0
    assert service_calls == [(pdf_path, context_path, template_path, output_dir / "one.docx", 321, shared_context)]
    report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
    assert report["processed"] == 1

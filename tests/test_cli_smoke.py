"""CLI smoke tests."""

import json
import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from materialcard.cli import app
from materialcard.exceptions import ParseError
from materialcard.models import ApprovalContext, ApprovalRequestData, MaterialData
from materialcard.parse_regex import ParserDiagnostics


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

    def fake_parse_material_from_pdf(
        pdf_path: Path,
        min_chars: int,
        *,
        diagnostics: ParserDiagnostics | None = None,
    ) -> MaterialData:
        calls.append(("parse_material_from_pdf", pdf_path, min_chars))
        return shared_material

    def fake_build_approval_request(material: MaterialData, ctx: ApprovalContext) -> ApprovalRequestData:
        calls.append(("build_approval_request", material, ctx))
        return shared_approval

    def fake_render_docx(data: ApprovalRequestData, template: Path, output: Path) -> None:
        calls.append(("render_docx", data, template, output))
        output.write_text("docx", encoding="utf-8")

    monkeypatch.setattr("materialcard.cli.load_context", fake_load_context)
    monkeypatch.setattr("materialcard.cli._parse_material_from_pdf", fake_parse_material_from_pdf)
    monkeypatch.setattr("materialcard.cli.build_approval_request", fake_build_approval_request)
    monkeypatch.setattr("materialcard.cli.render_docx", fake_render_docx)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["batch", str(input_dir), str(output_dir), "--context", str(context_path), "--template", str(template_path)],
    )

    assert result.exit_code == 0
    assert [call for call in calls if call[0] == "load_context"] == [("load_context", context_path)]
    assert len([call for call in calls if call[0] == "parse_material_from_pdf"]) == 2


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
    parse_calls: list[tuple[Path, int, ParserDiagnostics | None]] = []

    def fake_load_context(path: Path) -> ApprovalContext:
        return shared_context

    def fake_parse_material_from_pdf(
        pdf_path: Path,
        min_chars: int,
        *,
        diagnostics: ParserDiagnostics | None = None,
    ) -> MaterialData:
        parse_calls.append((pdf_path, min_chars, diagnostics))
        return shared_material

    def fake_build_approval_request(material: MaterialData, ctx: ApprovalContext) -> ApprovalRequestData:
        return shared_approval

    def fake_render_docx(data: ApprovalRequestData, template: Path, output: Path) -> None:
        output.write_text("docx", encoding="utf-8")

    monkeypatch.setattr("materialcard.cli.load_context", fake_load_context)
    monkeypatch.setattr("materialcard.cli._parse_material_from_pdf", fake_parse_material_from_pdf)
    monkeypatch.setattr("materialcard.cli.build_approval_request", fake_build_approval_request)
    monkeypatch.setattr("materialcard.cli.render_docx", fake_render_docx)

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
    assert parse_calls == [(pdf_path, 321, None)]
    report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
    assert report["processed"] == 1

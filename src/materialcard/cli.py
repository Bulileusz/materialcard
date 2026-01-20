"""CLI entry point for materialcard."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from .builder import build_approval_request
from .context_io import load_context
from .exceptions import MaterialCardError, NonTextPdfError
from .models import ApprovalRequestData, MaterialData
from .parse_regex import parse_material_from_text
from .pdf_text import ensure_text_pdf, extract_text_from_pdf
from .renderer_docx import render_docx

app = typer.Typer(no_args_is_help=True)


def _echo_json(model: MaterialData | ApprovalRequestData) -> None:
    typer.echo(model.model_dump_json(indent=2))


def _handle_error(exc: Exception, *, exit_code: int = 1) -> None:
    typer.echo(str(exc), err=True)
    raise typer.Exit(code=exit_code)


@app.command()
def parse(pdf: Path, min_chars: int = 200) -> None:
    """Parse material data from a PDF and output JSON."""

    try:
        text = extract_text_from_pdf(pdf)
        text = ensure_text_pdf(text, min_chars=min_chars)
        material = parse_material_from_text(text)
        _echo_json(material)
    except NonTextPdfError as exc:
        _handle_error(exc, exit_code=2)
    except NotImplementedError as exc:
        _handle_error(exc, exit_code=3)
    except MaterialCardError as exc:
        _handle_error(exc)


@app.command("build-approval")
def build_approval(material_path: Path, context_path: Path) -> None:
    """Build approval request data from material and context."""

    try:
        material = MaterialData.model_validate_json(material_path.read_text(encoding="utf-8"))
        context = load_context(context_path)
        data = build_approval_request(material, context)
        _echo_json(data)
    except MaterialCardError as exc:
        _handle_error(exc)


@app.command()
def generate(
    pdf: Path,
    context: Path,
    template: Path,
    output: Path,
    min_chars: int = 200,
) -> None:
    """Generate a DOCX approval request."""

    try:
        text = extract_text_from_pdf(pdf)
        text = ensure_text_pdf(text, min_chars=min_chars)
        material = parse_material_from_text(text)
        ctx = load_context(context)
        data = build_approval_request(material, ctx)
        render_docx(data, template, output)
        typer.echo(str(output))
    except NonTextPdfError as exc:
        _handle_error(exc, exit_code=2)
    except NotImplementedError as exc:
        _handle_error(exc, exit_code=3)
    except MaterialCardError as exc:
        _handle_error(exc)


@app.command()
def batch(
    input_dir: Path,
    output_dir: Path,
    context: Path | None = None,
    template: Path | None = None,
) -> None:
    """Process a batch of PDFs and write a report JSON."""

    output_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {
        "processed": 0,
        "errors": 0,
        "skipped": 0,
        "items": [],
    }

    for pdf_path in input_dir.glob("*.pdf"):
        item = {"pdf": str(pdf_path)}
        if context is None or template is None:
            item["status"] = "skipped"
            item["reason"] = "batch generation not implemented (missing context/template)"
            report["skipped"] = int(report["skipped"]) + 1
            report["items"].append(item)
            continue

        try:
            text = extract_text_from_pdf(pdf_path)
            text = ensure_text_pdf(text)
            material = parse_material_from_text(text)
            ctx = load_context(context)
            data = build_approval_request(material, ctx)
            output_path = output_dir / f"{pdf_path.stem}.docx"
            render_docx(data, template, output_path)
            item["status"] = "ok"
            item["output"] = str(output_path)
            report["processed"] = int(report["processed"]) + 1
        except Exception as exc:  # noqa: BLE001 - report errors
            item["status"] = "error"
            item["error"] = str(exc)
            report["errors"] = int(report["errors"]) + 1
        report["items"].append(item)

    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    typer.echo(str(report_path))


if __name__ == "__main__":
    app()

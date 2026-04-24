"""CLI entry point for materialcard."""

from __future__ import annotations

import json
from contextlib import ExitStack
from importlib.resources import as_file, files
from pathlib import Path

import typer
from pydantic import ValidationError as PydanticValidationError

from .builder import build_approval_request
from .context_io import load_context
from .exceptions import ContextError, DataValidationError, MaterialCardError, NonTextPdfError
from .models import ApprovalRequestData, MaterialData
from .parse_regex import ParserDiagnostics, parse_material_from_text
from .pdf_text import ensure_text_pdf, extract_text_from_pdf
from .services import generate_docx_from_pdf

app = typer.Typer(no_args_is_help=True)


def _echo_json(model: MaterialData | ApprovalRequestData) -> None:
    typer.echo(model.model_dump_json(indent=2))


def _handle_error(exc: Exception, *, exit_code: int = 1) -> None:
    typer.echo(str(exc), err=True)
    raise typer.Exit(code=exit_code)


def _format_validation_error(exc: PydanticValidationError) -> str:
    details: list[str] = []
    for item in exc.errors():
        loc = ".".join(str(part) for part in item.get("loc", []) if part is not None)
        msg = str(item.get("msg", "Invalid value"))
        details.append(f"{loc}: {msg}" if loc else msg)
    if not details:
        return "Invalid or incomplete input data."
    return "Invalid or incomplete input data: " + "; ".join(details)


def _format_parser_diagnostics(diagnostics: ParserDiagnostics) -> str:
    lines = ["Parser diagnostics:"]
    if diagnostics.events:
        for event in diagnostics.events:
            parts = [f"{event.field_name}.{event.step_name}: {event.status}"]
            if event.matched is not None:
                parts.append(f"matched={event.matched}")
            if event.value_preview:
                parts.append(f"value={event.value_preview!r}")
            if event.note:
                parts.append(f"note={event.note}")
            lines.append("- " + " | ".join(parts))
    else:
        lines.append("- no events recorded")
    for warning in diagnostics.warnings:
        lines.append(f"- warning: {warning}")
    return "\n".join(lines)


def _echo_parser_diagnostics_if_any(diagnostics: ParserDiagnostics | None) -> None:
    if diagnostics is None:
        return
    if not diagnostics.events and not diagnostics.warnings:
        return
    typer.echo(_format_parser_diagnostics(diagnostics), err=True)


def _write_extracted_text_debug_file(pdf_path: Path, extracted_text: str) -> Path | None:
    debug_path = pdf_path.with_name(f"{pdf_path.stem}_extracted.txt")
    try:
        debug_path.write_text(extracted_text, encoding="utf-8")
    except OSError:
        return None
    return debug_path


def _handle_non_text_pdf_error(
    pdf_path: Path,
    exc: NonTextPdfError,
    *,
    exit_code: int = 2,
) -> None:
    lines = [
        "PDF wygląda na skan (brak warstwy tekstowej).",
        "Zeskanuj do PDF z OCR / użyj wersji programu z OCR (planowane).",
    ]
    debug_path = _write_extracted_text_debug_file(pdf_path, exc.extracted_text)
    if debug_path is not None:
        lines.append(f"Zapisano podgląd ekstrakcji: {debug_path}")
    _handle_error(NonTextPdfError("\n".join(lines), extracted_text=exc.extracted_text), exit_code=exit_code)


def _parse_material_from_pdf(
    pdf_path: Path,
    min_chars: int,
    *,
    diagnostics: ParserDiagnostics | None = None,
) -> MaterialData:
    text = extract_text_from_pdf(pdf_path)
    text = ensure_text_pdf(text, min_chars=min_chars)
    return parse_material_from_text(
        text,
        source_path=str(pdf_path),
        diagnostics=diagnostics,
    )


def _default_output_path(pdf_path: Path) -> Path:
    return pdf_path.with_suffix(".docx")


def _default_context_candidates(pdf_path: Path) -> tuple[Path, ...]:
    return (
        pdf_path.parent / "context.json",
        Path.cwd() / "context.json",
    )


def _resolve_context_path(pdf_path: Path, context_path: Path | None) -> Path:
    if context_path is not None:
        return context_path

    for candidate in _default_context_candidates(pdf_path):
        if candidate.exists():
            return candidate

    raise ContextError(
        "Context file not found. Add context.json next to the PDF or run the command "
        "from a folder containing context.json."
    )


def _default_template_resource():
    return files("materialcard").joinpath("templates/default.docx")


def _resolve_output_path(pdf_path: Path, output_path: Path | None) -> Path:
    return output_path if output_path is not None else _default_output_path(pdf_path)


@app.command()
def parse(pdf: Path, min_chars: int = 200, debug: bool = False) -> None:
    """Parse material data from a PDF and output JSON."""

    diagnostics = ParserDiagnostics() if debug else None
    try:
        material = _parse_material_from_pdf(pdf, min_chars, diagnostics=diagnostics)
        _echo_json(material)
        _echo_parser_diagnostics_if_any(diagnostics)
    except NonTextPdfError as exc:
        _echo_parser_diagnostics_if_any(diagnostics)
        _handle_non_text_pdf_error(pdf, exc, exit_code=2)
    except PydanticValidationError as exc:
        _echo_parser_diagnostics_if_any(diagnostics)
        _handle_error(DataValidationError(_format_validation_error(exc)))
    except MaterialCardError as exc:
        _echo_parser_diagnostics_if_any(diagnostics)
        _handle_error(exc)


@app.command("build-approval")
def build_approval(material_path: Path, context_path: Path) -> None:
    """Build approval request data from material and context."""

    try:
        material = MaterialData.model_validate_json(material_path.read_text(encoding="utf-8"))
        context = load_context(context_path)
        data = build_approval_request(material, context)
        _echo_json(data)
    except PydanticValidationError as exc:
        _handle_error(DataValidationError(_format_validation_error(exc)))
    except MaterialCardError as exc:
        _handle_error(exc)


@app.command()
def generate(
    pdf: Path,
    context: Path | None = None,
    template: Path | None = None,
    output: Path | None = None,
    min_chars: int = 200,
) -> None:
    """Generate a DOCX approval request."""

    try:
        resolved_context = _resolve_context_path(pdf, context)
        resolved_output = _resolve_output_path(pdf, output)
        with ExitStack() as stack:
            resolved_template = template
            if resolved_template is None:
                resolved_template = stack.enter_context(as_file(_default_template_resource()))
            generate_docx_from_pdf(
                pdf,
                resolved_context,
                resolved_template,
                resolved_output,
                min_chars=min_chars,
            )
        typer.echo(str(resolved_output))
    except NonTextPdfError as exc:
        _handle_non_text_pdf_error(pdf, exc, exit_code=2)
    except ContextError as exc:
        _handle_error(exc, exit_code=3)
    except PydanticValidationError as exc:
        _handle_error(DataValidationError(_format_validation_error(exc)))
    except MaterialCardError as exc:
        _handle_error(exc)


@app.command()
def batch(
    input_dir: Path,
    output_dir: Path,
    context: Path | None = None,
    template: Path | None = None,
    min_chars: int = 200,
) -> None:
    """Process a batch of PDFs and write a report JSON."""

    output_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {
        "processed": 0,
        "errors": 0,
        "skipped": 0,
        "items": [],
    }
    ctx = load_context(context) if context is not None else None

    for pdf_path in input_dir.glob("*.pdf"):
        item = {"pdf": str(pdf_path)}
        if context is None or template is None:
            item["status"] = "skipped"
            item["reason"] = "batch generation not implemented (missing context/template)"
            report["skipped"] = int(report["skipped"]) + 1
            report["items"].append(item)
            continue

        try:
            output_path = output_dir / f"{pdf_path.stem}.docx"
            generate_docx_from_pdf(
                pdf_path,
                context,
                template,
                output_path,
                min_chars=min_chars,
                context_data=ctx,
            )
            item["status"] = "ok"
            item["output"] = str(output_path)
            report["processed"] = int(report["processed"]) + 1
        except PydanticValidationError as exc:
            item["status"] = "error"
            item["error"] = str(DataValidationError(_format_validation_error(exc)))
            report["errors"] = int(report["errors"]) + 1
        except MaterialCardError as exc:
            item["status"] = "error"
            item["error"] = str(exc)
            report["errors"] = int(report["errors"]) + 1
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

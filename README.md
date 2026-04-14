# materialcard

## What it does

CLI, które z dokumentacji PDF generuje gotowy wniosek DOCX.

W skrócie: wyciąga tekst z PDF, parsuje go deterministycznie (regex + heurystyki), łączy z kontekstem projektu i renderuje szablon DOCX.

## Quick start

1. Instalacja zależności:

```bash
poetry install
```

2. Sprawdzenie CLI:

```bash
poetry run materialcard --help
```

3. Parsowanie PDF do JSON (diagnostyka parsera):

```bash
poetry run materialcard parse ./input/karta.pdf
```

4. Generowanie DOCX:

```bash
poetry run materialcard generate \
	./input/karta.pdf \
	./context/wroclaw.json \
	./templates/approvals/wroclaw/template.docx \
	./out/wniosek.docx
```

## Example

Przykładowy plik kontekstu `./context/wroclaw.json`:

```json
{
	"investor_name": "Gmina Wroclaw",
	"project_title": "Modernizacja instalacji",
	"contractor_name": "Firma XYZ",
	"manufacturer": "Schneider Electric",
	"estimated_quantity": "12 szt.",
	"planned_delivery_date": "2026-05-10",
	"planned_installation_date": "2026-05-20",
	"prepared_by_name": "Jan Kowalski",
	"prepared_by_role": "Kierownik robot",
	"attachments": ["Karta katalogowa", "Deklaracja zgodnosci"]
}
```

Pełny przepływ na jednym materiale:

```bash
poetry run materialcard parse ./input/ADC960D.pdf
poetry run materialcard generate \
	./input/ADC960D.pdf \
	./context/wroclaw.json \
	./templates/approvals/wroclaw/template.docx \
	./out/ADC960D-wniosek.docx
```

## How it works

Pipeline działa end-to-end:

```text
PDF -> tekst -> parser -> MaterialData -> ApprovalContext -> ApprovalRequestData -> DOCX
```

- `pdf_text.py`: ekstrakcja tekstu z PDF i walidacja minimalnej długości.
- `parse_regex.py`: parser deterministyczny (bez AI i OCR).
- `builder.py`: składanie danych do kontraktu DOCX.
- `renderer_docx.py`: render szablonu przez `docxtpl`.

## Data model

- `MaterialData`: dane wyciągane z PDF (np. `material_type`, `description`, `raw_text`).
- `ApprovalContext`: dane projektowe podawane z zewnątrz (w tym `manufacturer`, `estimated_quantity`).
- `ApprovalRequestData`: finalny, ścisły kontrakt przekazywany do szablonu DOCX.

Najważniejsze: parser nie zgaduje producenta ani ilości. Te pola zawsze pochodzą z kontekstu.

## Limitations

- Brak OCR: PDF musi mieć warstwę tekstową.
- Brak AI/LLM: tylko regex i jawne heurystyki.
- Zachowanie jest deterministyczne: to samo wejście daje to samo wyjście.
- Narzędzie przygotowuje dokument roboczy, nie podejmuje decyzji administracyjnych.

## Development

Testy:

```bash
poetry run pytest
```

Lint i format:

```bash
poetry run ruff check src/ tests/
poetry run ruff format src/ tests/
```

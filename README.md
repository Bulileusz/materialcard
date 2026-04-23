# materialcard

## What it does

`materialcard` to deterministyczne CLI w Pythonie do generowania wniosków akceptacyjnych DOCX na podstawie dokumentacji produktowej w PDF.

Przepływ jest jawny i bez AI/ML: PDF -> ekstrakcja tekstu -> normalizacja -> parser regex + heurystyki -> dane strukturalne -> render DOCX.

## Current status (MVP)

MVP działa end-to-end:

```text
PDF -> text extraction -> normalization -> regex parser -> MaterialData -> ApprovalContext -> ApprovalRequestData -> DOCX
```

Co działa dzisiaj:
- ekstrakcja tekstu z tekstowych PDF-ów
- normalizacja tekstu wejściowego i podstawowa naprawa typowego mojibake
- deterministyczny parser regex + heurystyki bez AI, OCR i zgadywania runtime
- fallbacki rankingowe dla `material_type` i `description`
- diagnostyka parsera przez `parse --debug`
- budowanie `ApprovalRequestData` z danych z PDF i kontekstu projektu
- render DOCX przez `docxtpl`
- workflow `generate` wydzielony do małej warstwy `services.py`, używanej także przez `batch`
- batch processing z raportem JSON i per-plikową obsługą błędów
- testy jednostkowe, fixture-based parser regression tests i prosty test integracyjny DOCX

To jest działające MVP, nie ogólny parser wszystkich układów kart materiałowych.

## Example usage

Instalacja:

```bash
poetry install
```

Parsowanie PDF do JSON:

```bash
poetry run materialcard parse .\input\karta.pdf
```

Parsowanie z diagnostyką parsera:

```bash
poetry run materialcard parse .\input\karta.pdf --debug
```

`--debug` wypisuje na stderr kroki parsera, m.in. dopasowanie labeli, znalezione fallback candidates, wybraną wartość i ostrzeżenia o brakujących polach.

Budowanie danych wniosku z wcześniej zapisanego `MaterialData` i `context.json`:

```bash
poetry run materialcard build-approval .\material.json .\context.json
```

Generowanie DOCX z użyciem `context.json`:

```bash
poetry run materialcard generate `
  .\input\karta.pdf `
  .\context.json `
  .\templates\approvals\wroclaw\TEMPLATE.docx `
  .\out.docx
```

Przetwarzanie katalogu PDF-ów i zapis `report.json`:

```bash
poetry run materialcard batch `
  .\input `
  .\output `
  --context .\context.json `
  --template .\templates\approvals\wroclaw\TEMPLATE.docx
```

Przykładowy `context.json`:

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

## Architecture

Najważniejsze modele:
- `MaterialData` - dane wyciągnięte z PDF, np. `material_type`, `description`
- `ApprovalContext` - dane projektowe podawane z zewnątrz, np. `manufacturer`, `estimated_quantity`
- `ApprovalRequestData` - końcowy kontrakt danych dla szablonu DOCX

Skrót przepływu:
- `pdf_text.py` - ekstrakcja tekstu z PDF
- `parse_regex.py` - normalizacja tekstu, label-based regex, fallbacki i diagnostyka parsera
- `builder.py` - złożenie `MaterialData` i `ApprovalContext`; kontekst ma pierwszeństwo dla załączników
- `services.py` - workflow `generate_docx_from_pdf(...)`: PDF + kontekst + szablon -> `ApprovalRequestData` + DOCX
- `renderer_docx.py` - render DOCX przez `docxtpl`
- `cli.py` - komendy `parse`, `build-approval`, `generate`, `batch`

Parser działa deterministycznie: najpierw próbuje label-based extraction, potem stosuje proste rankingowe fallbacki dla `material_type` i `description`. Diagnostyka pozwala sprawdzić, które kroki zadziałały i jakie kandydaty fallback były brane pod uwagę.

`ApprovalRequestData` przechowuje strukturalne dane dla szablonu. Tekst załączników (`attachments_text`) jest wyliczany z listy `attachments`, a nie składany w builderze.

Założenie MVP jest celowe: parser nie zgaduje producenta ani ilości. Te pola pochodzą z kontekstu.

## Known limitations

Obecne ograniczenia:
- parser jest heurystyczny i może pomylić się na nietypowych układach dokumentów
- PDF musi zawierać warstwę tekstową; OCR nie jest obsługiwany
- edge cases zależne od layoutu PDF nadal wymagają fixture-based regresji
- `manufacturer` i `estimated_quantity` pochodzą z kontekstu, nie z parsera PDF

## Development

Instalacja zależności:

```bash
poetry install
```

Uruchomienie testów:

```bash
poetry run pytest
```

CLI:

```bash
poetry run materialcard --help
```

Testy obejmują deterministic parser behavior, fixture-based parser regression tests, CLI smoke tests, service orchestration tests, builder tests i prosty render DOCX. Projekt nie używa AI/ML ani OCR w runtime.

Projekt jest prowadzony przez Poetry. Jeśli testy nie startują w "gołym" interpreterze Pythona, najpierw sprawdź środowisko Poetry i zainstalowane zależności.

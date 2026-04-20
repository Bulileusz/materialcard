# materialcard

## What it does

`materialcard` to deterministyczne CLI w Pythonie do generowania wniosków akceptacyjnych DOCX na podstawie dokumentacji produktowej w PDF.

Obecny przepływ jest prosty: narzędzie wyciąga tekst z PDF, parsuje go regułami opartymi o regex i proste heurystyki, łączy wynik z kontekstem projektu i renderuje gotowy plik DOCX.

## Current status (MVP)

MVP jest zakończone i działa end-to-end:

```text
PDF -> text extraction -> regex parser -> MaterialData -> ApprovalContext -> ApprovalRequestData -> DOCX
```

Co działa dzisiaj:
- ekstrakcja tekstu z tekstowych PDF-ów
- deterministyczny parser bez AI, OCR i zgadywania runtime
- budowanie `ApprovalRequestData` z danych z PDF i kontekstu projektu
- render DOCX przez `docxtpl`
- podstawowy zestaw testów jednostkowych i prosty test integracyjny

To nie jest jeszcze system odporny na szeroki przekrój realnych kart materiałowych. To jest działające MVP, nie dojrzały parser dokumentów.

## Example usage

Instalacja:

```bash
poetry install
```

Parsowanie PDF do JSON:

```bash
poetry run materialcard parse .\input\karta.pdf
```

Generowanie DOCX z użyciem `context.json`:

```bash
poetry run materialcard generate `
  .\input\karta.pdf `
  .\context.json `
  .\templates\approvals\wroclaw\TEMPLATE.docx `
  .\out.docx
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
- `ApprovalRequestData` - końcowy, ścisły kontrakt danych dla szablonu DOCX

Skrót przepływu:
- `pdf_text.py` - ekstrakcja tekstu z PDF
- `parse_regex.py` - parser oparty o label-based regex i proste fallbacki liniowe
- `builder.py` - złożenie `MaterialData` i `ApprovalContext`
- `renderer_docx.py` - render DOCX przez `docxtpl`
- `cli.py` - komendy `parse`, `build-approval`, `generate`, `batch`

Założenie MVP jest celowe: parser nie zgaduje producenta ani ilości. Te pola pochodzą z kontekstu.

## Known limitations

Obecne ograniczenia są znane i nie są ukrywane:

- parser jest kruchy dla niespójnych PDF-ów z realnego świata
- fallback logic w parserze jest nadal prosty i może wybrać złą linię
- parser nie ma jeszcze sensownej diagnostyki, więc analiza błędów jest słaba
- CLI powiela część orkiestracji między komendami
- testy są za płytkie względem realnych wejść i mają mało prawdziwych fixture'ów
- w repo są problemy z encodingiem, które trzeba uporządkować
- architektura jest wystarczająca dla MVP, ale nie jest jeszcze gotowa na większy wzrost
- brak OCR: PDF musi zawierać warstwę tekstową
- brak AI/ML: tylko regex + proste heurystyki
- `manufacturer` nie jest wiarygodnie parsowany z PDF i nadal pochodzi z kontekstu
- `estimated_quantity` również pochodzi z kontekstu

Jeśli parser zacznie dostawać więcej wariantów dokumentów bez przebudowy v0.2, pierwszy problem pojawi się w jakości ekstrakcji, nie w renderze DOCX.

## v0.2 direction

v0.2 nie ma przepisywać projektu od zera. Kierunek jest inkrementalny:

- utwardzenie parsera bez odchodzenia od deterministycznych reguł
- rozbicie parsera na czytelniejsze części zamiast dokładania kolejnych regexów do jednego pliku
- dodanie diagnostyki parsera i lepszych komunikatów błędów
- dołożenie realnych fixture'ów regresyjnych
- uproszczenie i odduplikowanie orkiestracji CLI
- wydzielenie małej warstwy serwisowej dla wspólnego przepływu parse/build/generate
- przygotowanie gruntu pod wiele profili parsera i wiele template'ów, ale bez budowania ciężkiego plugin systemu

Nie planujemy w v0.2:
- OCR
- AI w logice runtime
- pełnego przepisywania architektury
- rozbudowanych abstrakcji "na zapas"

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

Projekt jest prowadzony przez Poetry. Jeśli testy nie startują w "gołym" interpreterze Pythona, najpierw sprawdź środowisko Poetry i zainstalowane zależności.

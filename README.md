# materialcard

## Co to jest

`materialcard` to deterministyczne CLI w Pythonie do generowania wniosków akceptacyjnych DOCX na podstawie dokumentacji produktowej w PDF.

Przepływ jest jawny i bez AI/ML:

```text
PDF -> text extraction -> normalization -> regex parser + heuristics -> MaterialData -> ApprovalContext -> ApprovalRequestData -> DOCX
```

Projekt w wersji 1.0 obsługuje PDF z warstwą tekstową. OCR nie jest zaimplementowany.

## Aktualny stan

Co działa dzisiaj:
- ekstrakcja tekstu z tekstowych PDF-ów
- deterministyczny parser regex + heurystyki bez AI, OCR i zgadywania runtime
- fallbacki dla `material_type` i `description`, w tym obsługa dłuższych polskich kart produktowych z sekcją `Opis produktu`
- workflow `generate` z domyślnym template i automatycznym wykrywaniem `context.json`
- czytelny UX dla skanów bez warstwy tekstowej: diagnoza, exit code `2`, zapis `*_extracted.txt`
- build jednoplikowego `materialcard.exe` na Windows
- workflow GitHub Actions budujący Windows EXE jako artifact, a przy tagu `v*` także Release asset

## Szybki start

Instalacja:

```powershell
poetry install
```

Happy path:

```powershell
poetry run materialcard generate .\input\karta.pdf
```

Jeśli `context.json` jest obok PDF albo w bieżącym katalogu, program użyje go automatycznie. Wynik domyślnie zapisuje się jako `.\input\karta.docx`.

## Użycie

Przykłady CLI:

```powershell
poetry run materialcard generate .\input\karta.pdf
poetry run materialcard parse .\input\karta.pdf --debug
poetry run materialcard build-approval .\material.json .\context.json
```

Przykłady dla EXE:

```powershell
.\dist\materialcard.exe generate .\input\karta.pdf
.\dist\materialcard.exe .\input\karta.pdf
```

Druga komenda działa także przy drag & drop PDF na `materialcard.exe`: jeśli program dostanie tylko jedną ścieżkę do pliku `.pdf`, potraktuje to jak `generate <pdf>`.

Domyślne zasady dla `generate`:
- output: `<nazwa_pdf>.docx` obok wejściowego PDF
- template: wbudowany domyślny template bundlowany z pakietem i EXE
- context: najpierw `context.json` obok PDF, potem `context.json` w bieżącym katalogu

## Context

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
  "prepared_by_role": "Kierownik robót",
  "attachments": ["Karta katalogowa", "Deklaracja zgodności"]
}
```

`context` może być zapisany jako JSON. Kod ładowania wspiera też YAML, jeśli zainstalowany jest optional dependency `pyyaml`.

## Obsługa skanów

Jeśli PDF wygląda na skan i nie ma warstwy tekstowej, program:
- wypisze komunikat `PDF wygląda na skan (brak warstwy tekstowej).`
- zasugeruje `Zeskanuj do PDF z OCR / użyj wersji programu z OCR (planowane).`
- zakończy się z exit code `2`
- zapisze obok plik `*_extracted.txt` z tym, co udało się wyciągnąć

## Batch

Komenda `batch` przetwarza katalog PDF-ów i zapisuje `report.json`.

Aktualnie batch wymaga jawnego podania `--context` i `--template`. Bez nich pliki są oznaczane jako `skipped`, a nie przetwarzane domyślnie.

Przykład:

```powershell
poetry run materialcard batch `
  .\input `
  .\output `
  --context .\context.json `
  --template .\templates\approvals\wroclaw\TEMPLATE.docx
```

## Windows EXE build

Wymagania:
- Windows
- Poetry

Build krok po kroku:

```powershell
poetry install --with build --extras docx
.\scripts\build_exe.ps1
```

Alternatywnie ręcznie:

```powershell
poetry install --with build --extras docx
poetry run pyinstaller --noconfirm --clean materialcard.spec
```

Wynik builda:

```text
dist\materialcard.exe
```

Właściwości builda:
- jednoplikowy `materialcard.exe`
- zawiera interpreter i zależności, więc nie wymaga zewnętrznego Pythona na komputerze użytkownika
- zawiera domyślny template DOCX i działa także w trybie PyInstaller `--onefile`

## GitHub Actions artifact

Repo zawiera workflow `Build Windows EXE`, który:
- działa na `workflow_dispatch`
- działa także przy pushu taga `v*`
- buduje `dist/materialcard.exe`
- generuje `dist/materialcard.exe.sha256`
- publikuje artifact `materialcard-windows-exe`
- przy tagu `v*` publikuje też GitHub Release z EXE i checksumą

Jak pobrać artifact:
1. Wejdź w zakładkę `Actions`.
2. Uruchom workflow `Build Windows EXE` albo otwórz zakończony run.
3. Pobierz artifact `materialcard-windows-exe`.

## Development

Instalacja zależności:

```powershell
poetry install
```

Uruchomienie testów:

```powershell
poetry run pytest
```

CLI help:

```powershell
poetry run materialcard --help
```

## Architektura

Najważniejsze moduły:
- `pdf_text.py` - ekstrakcja tekstu z PDF
- `parse_regex.py` - parser regex + heurystyki
- `builder.py` - złożenie `MaterialData` i `ApprovalContext`
- `services.py` - workflow `generate_docx_from_pdf(...)`
- `renderer_docx.py` - render DOCX przez `docxtpl`
- `cli.py` - komendy `parse`, `build-approval`, `generate`, `batch`

## Ograniczenia

- parser jest heurystyczny i może mylić się na nietypowych layoutach
- PDF musi mieć warstwę tekstową
- OCR nie jest zaimplementowany w wersji 1.0
- `manufacturer` i `estimated_quantity` pochodzą z kontekstu, nie z parsera PDF

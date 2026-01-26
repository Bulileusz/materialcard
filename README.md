# materialcard

## Wprowadzenie

`materialcard` automatyzuje tworzenie wniosków o zatwierdzenie materiałów i urządzeń (DOCX) na podstawie dokumentacji produktów dostarczonej w formie plików PDF.

Na budowie wniosek o zatwierdzenie materiału wymaga wypełnienia standardowego formularza danymi technicznymi z kart katalogowych, certyfikatów lub dokumentacji producenta. Ręczne przepisywanie tych danych jest czasochłonne i podatne na błędy przepisania.

Aplikacja wydobywa dane tekstowe z plików PDF, parsuje je deterministycznymi regułami i generuje wypełniony szablon wniosku w formacie DOCX.

Aplikacja służy wyłącznie do przygotowania dokumentu roboczego. 
Odpowiedzialność za poprawność merytoryczną, kompletność oraz decyzje administracyjne 
ponosi osoba zatwierdzająca dokument.

## Zakres i ograniczenia

### Aplikacja realizuje

- Ekstrakcję tekstu z PDF przy użyciu `pypdf`
- Parsowanie danych deterministyczne: regex i heurystyki tekstowe
- Generowanie dokumentów DOCX na podstawie szablonów Jinja (`docxtpl`)
- Obsługę wielu wariantów szablonów wniosków
- Interfejs CLI do przetwarzania pojedynczych plików i przetwarzania wsadowego

### Aplikacja celowo NIE realizuje

- **OCR**: pliki PDF muszą zawierać tekst w warstwie tekstowej
- **AI/LLM**: brak rozumowania, interpretacji kontekstu, ani modeli uczenia maszynowego
- **Decyzji administracyjnych**: aplikacja nie zatwierdza ani nie odrzuca materiałów
- **Podpisów i zatwierdzeń**: pola podpisów, checkboxy i uwagi pozostają puste do wypełnienia ręcznego
- **Walidacji merytorycznej**: aplikacja nie weryfikuje zgodności materiałów z normami, wymaganiami projektu ani dokumentacją techniczną

Jeśli PDF nie zawiera wystarczającej ilości tekstu (mniej niż 200 znaków), aplikacja zgłasza błąd `NonTextPdfError` i wymaga ręcznego opracowania dokumentu.

## Pipeline działania

```
PDF → ekstrakcja tekstu (pypdf) → parsowanie (wyrażenia regularne i heurystyki) → modele danych (Pydantic) → renderowanie (docxtpl) → DOCX
```

1. **Ekstrakcja**: `pypdf` wydobywa tekst z warstwy tekstowej pliku PDF
2. **Walidacja**: sprawdzenie czy tekst zawiera ≥ 200 znaków
3. **Parsowanie**: regex i heurystyki wydobywają dane strukturalne
4. **Modelowanie**: dane trafiają do modeli Pydantic z walidacją typów
5. **Renderowanie**: szablon DOCX wypełniany danymi przez Jinja
6. **Zapis**: dokument zapisywany do pliku wyjściowego DOCX

## Struktura projektu

```
materialcard/
├── src/
│   └── materialcard/
│       ├── cli.py              # interfejs CLI (Typer)
│       ├── pdf_text.py         # ekstrakcja tekstu z PDF
│       ├── parse_regex.py      # parsowanie regex → dane strukturalne
│       ├── builder.py          # budowanie ApprovalRequestData
│       ├── renderer_docx.py    # renderowanie DOCX (docxtpl)
│       ├── context_io.py       # wczytywanie kontekstu projektu
│       ├── models.py           # modele Pydantic
│       └── exceptions.py       # wyjątki domenowe
├── templates/
│   └── approvals/
│       └── <wariant>/          # szablony DOCX dla różnych wariantów wniosków
│           └── TEMPLATE_HERE.docx
├── tests/
│   ├── unit/
│   └── integration/
├── pyproject.toml
└── README.md
```

Layout projektu: `src` (package w katalogu `src/materialcard`).

## Interfejs CLI

Aplikacja udostępnia interfejs wiersza poleceń przez `typer`. Dostępne komendy:

### `parse`

Wydobywa i wyświetla dane z pliku PDF bez generowania dokumentu.

- Cel: diagnostyka ekstrakcji, weryfikacja poprawności parsowania
- Wyjście: dane w formacie JSON lub YAML (zależnie od opcji)
- Nie generuje pliku DOCX

### `build-approval`

Buduje obiekt `ApprovalRequestData` z pliku PDF i kontekstu projektowego.

- Cel: przygotowanie kompletnego zestawu danych do generowania wniosku
- Łączy `MaterialData` (z PDF) z `ApprovalContext` (z parametrów CLI)
- Wyjście: zwalidowany obiekt gotowy do renderowania

### `generate`

Generuje dokument DOCX na podstawie danych z PDF i szablonu.

- Wejście: plik PDF, wariant szablonu, dane kontekstowe (CLI lub plik konfiguracyjny)
- Wyjście: plik DOCX w lokalizacji wskazanej przez użytkownika
- Obsługuje wybór wariantu szablonu z katalogu `templates/approvals/<wariant>/`

### `batch`

Przetwarza wsadowo wiele plików PDF.

- Cel: automatyzacja przetwarzania wielu materiałów jednocześnie
- Wejście: katalog z plikami PDF lub lista plików
- Wyjście: katalog z dokumentami DOCX oraz raport błędów

Nazwy i semantyka komend CLI traktowane są jako stabilny interfejs użytkownika
i nie będą zmieniane bez istotnej przyczyny.

## Modele danych

Wszystkie modele zdefiniowane w Pydantic z automatyczną walidacją typów i wartości.

### `MaterialData`

Reprezentuje dane materiału lub urządzenia wyekstrahowane z pliku PDF:

- Nazwa produktu
- Producent
- Parametry techniczne
- Normy i certyfikaty
- Pozostałe informacje katalogowe

Źródło: bezpośrednio z pliku PDF.

### `ApprovalContext`

Kontekst organizacyjny i projektowy, którego nie ma w pliku PDF:

- Numer projektu
- Nazwa inwestycji
- Dane zamawiającego
- Dane wykonawcy
- Pozostałe informacje administracyjne

Źródło: parametry CLI, pliki konfiguracyjne lub interakcja użytkownika.

### `ApprovalRequestData`

Kompletny model wniosku o zatwierdzenie materiału, łączący `MaterialData` i `ApprovalContext`:

- Podstawa renderowania szablonu DOCX
- Przechowuje wszystkie dane potrzebne do wypełnienia formularza
- Nie zawiera decyzji, podpisów ani zatwierdzeń

`ApprovalRequestData` stanowi **kontrakt danych** między trzema komponentami systemu:
1. **Parserami PDF** — które wydobywają `MaterialData`
2. **Kontekstem projektowym** — który dostarcza `ApprovalContext`
3. **Szablonami DOCX** — które oczekują konkretnych placeholderów Jinja

Kontrakt definiuje pełny zestaw pól wymaganych do wypełnienia szablonu wniosku.
Zmiana kontraktu wymaga synchronicznej aktualizacji:
- parserów (jeśli dodano/zmieniono pola z `MaterialData`),
- szablonów DOCX (jeśli zmieniono nazwy placeholderów),
- buildera `build_approval_request()` (logika składania danych).

## Filozofia szablonów DOCX

Szablony w `templates/approvals/<wariant>/` to pliki DOCX zawierające wyłącznie placeholdery Jinja.

### Zasady projektowania szablonów

- **Brak danych**: szablony nie zawierają żadnych wartości domyślnych, przykładowych ani testowych
- **Brak logiki decyzyjnej**: szablony nie podejmują decyzji o akceptacji lub odrzuceniu materiału
- **Brak zatwierdzeń**: pola podpisów, checkboxy zatwierdzające i pola uwag pozostają puste
- **Wyłącznie placeholdery**: `{{ material.name }}`, `{{ context.project_number }}`, `{{ material.manufacturer }}`

Szablon jest neutralny wobec treści. Wszystkie decyzje administracyjne podejmuje człowiek po wygenerowaniu dokumentu.

Aplikacja wypełnia wyłącznie pola danych (parametry techniczne, nazwy, numery), nie wypełnia pól decyzyjnych (akceptacja, uwagi, podpisy).

## Deterministyczność i obsługa błędów

### Deterministyczność

Aplikacja działa w sposób w pełni deterministyczny:

- Ekstrakcja oparta wyłącznie na regexach i heurystykach tekstowych
- Brak modeli probabilistycznych
- Brak rozumowania kontekstowego
- Identyczne dane wejściowe → identyczne dane wyjściowe

Ten sam plik PDF zawsze wygeneruje ten sam dokument DOCX przy użyciu tego samego szablonu.

### Obsługa błędów

#### `NonTextPdfError`

Rzucany gdy plik PDF zawiera mniej niż 200 znaków tekstu.

- Przyczyna: PDF zeskanowany, obrazowy lub uszkodzony
- Działanie: wymagane ręczne opracowanie lub przetworzenie OCR poza aplikacją
- Aplikacja nie próbuje naprawić ani zgadnąć treści

#### `ParsingError`

Rzucany gdy nie udało się wyekstrahować wymaganych pól z tekstu PDF.

- Przyczyna: nierozpoznany format dokumentacji, brak kluczowych danych
- Działanie: wymagana ręczna interwencja lub rozszerzenie parserów

#### `TemplateNotFoundError`

Rzucany gdy brakuje szablonu dla wskazanego wariantu.

- Przyczyna: nieprawidłowa nazwa wariantu lub brak pliku `template.docx`
- Działanie: sprawdzenie dostępnych wariantów lub utworzenie szablonu

#### `ValidationError`

Rzucany przez Pydantic gdy dane nie przeszły walidacji modelu.

- Przyczyna: nieprawidłowe typy, brakujące pola wymagane, wartości poza zakresem
- Działanie: diagnostyka danych wejściowych, poprawienie parsera

Wszystkie błędy są logowane ze szczegółami i raportowane w interfejsie CLI.

## Rozwój etapowy

Projekt rozwijany jest w iteracjach zakończonych stabilnymi commitami.

Po zakończeniu każdego etapu:
1. Kod jest zsynchronizowany z dokumentacją
2. README.md aktualizowane jako „single source of truth"
3. Testy weryfikują funkcjonalność wprowadzoną w etapie
4. Commit oznaczany tagiem lub komunikatem podsumowującym etap

Dzięki temu każdy commit w historii projektu reprezentuje spójny stan systemu, 
a dokumentacja nie odbiega od rzeczywistego stanu kodu.

Etapy dotychczas zakończone:
- **Kontrakt danych + szablon DOCX** — model `ApprovalRequestData`, builder, szkielet integracji z `docxtpl`

## Roadmapa

### MVP (szkielet funkcjonalny)

- [x] Szkielety ekstrakcji tekstu z PDF (`pypdf`)
- [x] Modele Pydantic (kontrakt danych)
- [x] Kontrakt danych `ApprovalRequestData` (wariant Wrocław)
- [x] Builder `build_approval_request()` (składanie danych z MaterialData + ApprovalContext)
- [x] Szkielet renderowania DOCX (`docxtpl`) — mechanizm działa, brakuje pełnej integracji
- [x] Szkielet CLI: komendy `parse`, `generate`, `build-approval`, `batch` — interfejs istnieje, funkcjonalność częściowa
- [ ] Walidacja długości tekstu (≥ 200 znaków, `NonTextPdfError`)
- [ ] Podstawowy parser regex dla typowych kart katalogowych
- [ ] Pełne wykorzystanie wariantów szablonów (`templates/approvals/<wariant>/`)
- [ ] Testy jednostkowe dla ekstrakcji i parsowania
- [ ] Testy integracyjne dla pełnego pipeline'u

### Po MVP (pełna funkcjonalność)

- [ ] Komenda `build-approval` dla etapowego budowania danych
- [ ] Komenda `batch` dla przetwarzania wsadowego
- [ ] Eksport danych pośrednich do JSON/YAML (diagnostyka)
- [ ] Tryb verbose z szczegółową diagnostyką ekstrakcji
- [ ] Rozszerzenie parserów o dodatkowe formaty dokumentacji (certyfikaty, deklaracje zgodności)
- [ ] Wsparcie dla wielu języków w szablonach (polski, angielski)
- [ ] Dokumentacja użytkownika (instrukcje dla inżynierów budowy)
- [ ] Obsługa plików konfiguracyjnych dla kontekstu projektowego

## Rozwój

### Instalacja

```bash
poetry install
```

### Uruchomienie

```bash
poetry run materialcard --help
```

### Testy

```bash
poetry run pytest
```

### Formatowanie i linting

```bash
poetry run ruff check src/ tests/
poetry run ruff format src/ tests/
```

## Licencja

Projekt wewnętrzny. Licencja do ustalenia.

## Kontakt

Zgłoszenia błędów i propozycje zmian: przez system kontroli wersji projektu.

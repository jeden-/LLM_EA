# Dokumentacja LLM Trading System

W tym katalogu znajduje się pełna dokumentacja systemu LLM Trading. Dokumentacja jest tworzona przy użyciu narzędzia Sphinx.

## Struktura dokumentacji

```
docs/
  ├── sphinx/                  # Dokumentacja w formacie Sphinx
  │   ├── _build/              # Wygenerowana dokumentacja (HTML, PDF itp.)
  │   ├── _static/             # Pliki statyczne (obrazy, CSS, JS)
  │   ├── _templates/          # Szablony Sphinx
  │   ├── api/                 # Dokumentacja API
  │   ├── komponenty/          # Opis poszczególnych komponentów
  │   ├── conf.py              # Konfiguracja Sphinx
  │   ├── index.rst            # Strona główna dokumentacji
  │   ├── instalacja.rst       # Instrukcja instalacji
  │   ├── ...                  # Inne pliki dokumentacji
  ├── metoda_master.md         # Opis metody handlowej (surowy Markdown)
  ├── api_reference.md         # Odniesienia do API (surowy Markdown)
  ├── risk_management.md       # Opis zarządzania ryzykiem (surowy Markdown)
  ├── installation_guide.md    # Instrukcja instalacji (surowy Markdown)
  ├── ...                      # Inne pliki dokumentacji w formacie Markdown
```

## Generowanie dokumentacji

### Wymagania

- Python 3.10 lub nowszy
- Sphinx 7.0.0 lub nowszy
- Sphinx Read the Docs Theme

Instalacja wymaganych pakietów:

```bash
pip install sphinx sphinx-rtd-theme
```

### Generowanie HTML

Aby wygenerować dokumentację w formacie HTML:

```bash
cd docs/sphinx
make html
```

Wygenerowana dokumentacja będzie dostępna w katalogu `docs/sphinx/_build/html/`.

### Generowanie PDF

Aby wygenerować dokumentację w formacie PDF:

```bash
cd docs/sphinx
make latexpdf
```

Wygenerowana dokumentacja w formacie PDF będzie dostępna w katalogu `docs/sphinx/_build/latex/`.

### Otwieranie dokumentacji HTML

Aby otworzyć wygenerowaną dokumentację w przeglądarce:

```bash
# Linux/macOS
open docs/sphinx/_build/html/index.html

# Windows
start docs/sphinx/_build/html/index.html
```

## Aktualizacja dokumentacji

Dokumentacja jest oparta na plikach RST (reStructuredText) w katalogu `docs/sphinx/`. Aby zaktualizować dokumentację:

1. Edytuj odpowiednie pliki RST
2. Wygeneruj dokumentację HTML/PDF za pomocą komend `make html` lub `make latexpdf`
3. Sprawdź wygenerowaną dokumentację

## Dodawanie nowej dokumentacji

Aby dodać nową sekcję dokumentacji:

1. Utwórz nowy plik `.rst` w odpowiednim katalogu
2. Dodaj odniesienie do tego pliku w `index.rst` lub w innym pliku spisu treści
3. Wygeneruj dokumentację aby sprawdzić, czy nowy plik jest poprawnie dołączony

## Ważne pliki

- `conf.py` - konfiguracja Sphinx, włączając motyw, rozszerzenia, itp.
- `index.rst` - strona główna i spis treści
- `Makefile` i `make.bat` - skrypty do generowania dokumentacji

## Automatyczne generowanie dokumentacji API

Dokumentacja API może być generowana automatycznie z komentarzy docstring w kodzie:

```bash
cd docs/sphinx
sphinx-apidoc -o api ../../ ../../tests/ ../../scripts/ ../../*/_pycache_/ -e -M
make html
``` 
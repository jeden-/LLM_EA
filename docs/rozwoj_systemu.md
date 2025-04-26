# Zasady rozwoju i konwencje systemu LLM Trading

Ten dokument zawiera wytyczne dotyczące rozwoju systemu LLM Trading, struktury kodu, konwencji nazewnictwa i zasad organizacji plików.

## Struktura komponentów

System składa się z kilku głównych komponentów, które powinny być traktowane jako odrębne moduły z jasno określonymi granicami i interfejsami. Każdy komponent powinien znajdować się w oddzielnym katalogu głównym projektu.

### Konwencje organizacji modułów

Każdy moduł główny (komponent) powinien mieć następującą strukturę:

```
[Nazwa_Modułu]/
  ├── __init__.py
  ├── [główne klasy modułu].py
  └── run_[nazwa_modułu].py  # Skrypt uruchamiający moduł jako usługę
```

#### Standardowe pliki w modułach

- `__init__.py` - Definiuje interfejs publiczny modułu i dokumentuje jego zawartość
- `run_[nazwa_modułu].py` - Skrypt uruchamiający moduł jako samodzielną usługę

### Konwencje nazewnictwa

1. **Nazwy plików**:
   - Używaj małych liter z podkreśleniami, np. `market_data.py`
   - Skrypty uruchamiające zawsze nazywaj `run_[nazwa_modułu].py`

2. **Nazwy klas**:
   - Używaj CamelCase, np. `MarketAnalyzer`
   - Nazwy klas powinny być rzeczownikami, np. `DatabaseHandler`

3. **Nazwy metod i funkcji**:
   - Używaj małych liter z podkreśleniami, np. `get_market_data()`
   - Metody powinny używać czasowników, np. `calculate_indicators()`

4. **Nazwy zmiennych**:
   - Używaj małych liter z podkreśleniami, np. `price_data`
   - Nazwy powinny być opisowe i jednoznaczne

## Organizacja plików wykonawczych

### Skrypty uruchamiające

Każdy główny komponent systemu powinien mieć swój skrypt uruchamiający:

1. W katalogu głównym komponentu:
   - `Agent_Manager/run_manager.py`
   - `Dashboard/run_dashboard.py`
   - `Database/run_database.py`
   - `LLM_Engine/run_engine.py`
   - `MT5_Connector/run_connector.py`

2. Skrypty pomocnicze i ogólnosystemowe:
   - `scripts/run_system.py` - Główny skrypt uruchamiający cały system
   - `scripts/start_system.py` - Alternatywny skrypt uruchamiający komponenty
   - `scripts/monitoring.py` - Skrypt monitorowania systemu

### Unikanie duplikacji

Należy unikać duplikacji funkcjonalności:

1. Skrypty uruchamiające powinny znajdować się tylko w jednym miejscu
2. Nie należy tworzyć alternatywnych wersji skryptów o podobnej funkcjonalności
3. W przypadku konieczności modyfikacji, modyfikuj istniejące skrypty

## Rozwój systemu

### Dodawanie nowych funkcjonalności

1. **Nowa funkcjonalność w istniejącym komponencie**:
   - Dodaj nowe klasy/metody w odpowiednich plikach
   - Aktualizuj testy jednostkowe
   - Aktualizuj dokumentację

2. **Nowy komponent**:
   - Utwórz nowy katalog w głównym katalogu projektu
   - Utwórz standardową strukturę plików
   - Dodaj komponent do `COMPONENTS` w `scripts/run_system.py`
   - Dodaj testy i dokumentację

### Testy

Każdy komponent powinien mieć odpowiednie testy:

```
tests/
  ├── test_[nazwa_modułu].py     # Testy dla całego modułu
  ├── test_[nazwa_klasy].py      # Testy dla konkretnej klasy
  └── test_end_to_end.py         # Testy integracyjne
```

## Konfiguracja środowiska

System obsługuje trzy główne środowiska:

1. `dev` - Środowisko deweloperskie (domyślne)
2. `test` - Środowisko testowe
3. `prod` - Środowisko produkcyjne

Każde środowisko ma swój plik konfiguracyjny:

```
config/
  ├── config_dev.json
  ├── config_test.json
  └── config_prod.json
```

### Parametry uruchamiania

Wszystkie skrypty uruchamiające powinny obsługiwać następujące parametry:

```bash
python -m [moduł].run_[nazwa] --env [dev|test|prod] [--debug]
```

## Dokumentacja

Dokumentacja powinna być aktualizowana razem z kodem:

```
docs/
  ├── installation_guide.md       # Instrukcja instalacji
  ├── system_structure.md         # Struktura systemu
  ├── rozwoj_systemu.md           # Zasady rozwoju (ten dokument)
  └── [nazwa_modułu]_guide.md     # Dokumentacja poszczególnych modułów
```

## Zasady bezpieczeństwa i protokoły

1. Nigdy nie umieszczaj kluczy API, haseł i innych danych wrażliwych bezpośrednio w kodzie
2. Używaj zmiennych środowiskowych (`.env`) do przechowywania danych wrażliwych
3. W środowisku produkcyjnym, zawsze wyłączaj tryb debugowania
4. Regularnie aktualizuj zależności, aby uniknąć luk bezpieczeństwa 
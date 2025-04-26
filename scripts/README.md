# Skrypty pomocnicze systemu LLM Trading

Ten katalog zawiera skrypty pomocnicze służące do uruchamiania, konfiguracji i zarządzania systemem LLM Trading. Poniżej znajduje się opis poszczególnych skryptów i ich zastosowania.

## Uruchamianie systemu

### run_system.py

Główny skrypt uruchamiający wszystkie komponenty systemu w odpowiedniej kolejności, zgodnie z ich zależnościami.

```bash
python -m scripts.run_system [--env dev|test|prod] [--debug] [--components component1 component2 ...]
```

Parametry:
- `--env` - środowisko uruchomieniowe (dev, test, prod), domyślnie dev
- `--debug` - uruchomienie w trybie debugowania
- `--components` - lista komponentów do uruchomienia (domyślnie wszystkie)

### start_system.py

Alternatywny skrypt uruchamiający system, który skupia się na uruchomieniu dashboardu i agenta handlowego.

```bash
python -m scripts.start_system [--dashboard-only] [--agent-only] [--port PORT] [--debug]
```

Parametry:
- `--dashboard-only` - uruchamia tylko dashboard
- `--agent-only` - uruchamia tylko agenta handlowego
- `--port` - port dla dashboardu (domyślnie 5000)
- `--debug` - uruchomienie w trybie debugowania

## Zarządzanie i monitorowanie

### monitoring.py

Skrypt monitorujący działanie systemu, analizujący logi i wykrywający problemy.

```bash
python -m scripts.monitoring [--interval SEC] [--single] [--env dev|test|prod]
```

### monitor_system.py

Biblioteka funkcji monitorujących używana przez monitoring.py i inne skrypty.

### run_agent.py

Skrypt uruchamiający agenta łączącego system LLM z Expert Advisorem.

```bash
python -m scripts.run_agent [--host HOST] [--req-port PORT] [--pub-port PORT] [--interval SEC] [--symbols SYM1,SYM2] [--debug]
```

## Konfiguracja i instalacja

### setup_environment.py

Skrypt konfigurujący środowisko uruchomieniowe, tworzący katalogi i ustawiający zmienne środowiskowe.

```bash
python -m scripts.setup_environment [--env dev|test|prod] [--db-init] [--verify] [--fix-perms]
```

### setup_database.py

Skrypt inicjalizujący bazę danych, tworzący tabele i dodający przykładowe dane.

```bash
python -m scripts.setup_database [--init] [--update] [--reset] [--demo-data]
```

### setup.sh

Skrypt powłoki dla systemów Unix/Linux do instalacji i konfiguracji środowiska.

```bash
bash scripts/setup.sh [--dev|--prod]
```

## Narzędzia analityczne i testowe

### run_analysis.py

Skrypt do przeprowadzania analizy rynku i generowania sygnałów handlowych.

```bash
python -m scripts.run_analysis --symbol SYMBOL --timeframe TIMEFRAME [--strategy STRATEGY] [--indicators IND1,IND2]
```

### show_analysis.py

Skrypt do wizualizacji wyników analizy rynku.

```bash
python -m scripts.show_analysis --analysis-id ID [--save-chart] [--output DIR]
```

### validate_llm_performance.py

Skrypt do walidacji wydajności modeli LLM w zakresie analizy rynku.

```bash
python -m scripts.validate_llm_performance [--model MODEL] [--test-set SET] [--rounds NUM]
```

### generate_test_data.py

Skrypt do generowania danych testowych do walidacji modeli i algorytmów.

```bash
python -m scripts.generate_test_data [--symbols SYM1,SYM2] [--timeframes TF1,TF2] [--start DATE] [--end DATE]
```

### demo_llm_engine.py

Demonstracja działania silnika LLM z możliwością interaktywnej interakcji.

```bash
python -m scripts.demo_llm_engine [--model MODEL] [--interactive]
```

### mt5_connector_example.py

Przykład użycia konektora MT5 do pobierania danych rynkowych i realizacji zleceń.

```bash
python -m scripts.mt5_connector_example [--symbol SYMBOL] [--timeframe TIMEFRAME] [--demo]
```

## Narzędzia do diagnostyki i naprawy bazy danych

### check_database.py

Skrypt do sprawdzania statusu i integralności bazy danych dla systemu LLM Trader MT5. Umożliwia weryfikację stanu bazy danych i wykrycie potencjalnych problemów takich jak:

- Brakujące tabele
- Nieprawidłowe klucze obce
- Niespójne referencje między tabelami
- Problemy z integralnością danych

**Użycie:**
```bash
python scripts/check_database.py --env dev
python scripts/check_database.py --db-path database/dev.db --output raport.json
python scripts/check_database.py --env prod --fix
```

**Parametry:**
- `--db-path` - Ścieżka do pliku bazy danych (domyślnie: database/dev.db)
- `--env` - Typ środowiska: dev, test, prod (wpływa na ścieżkę bazy danych)
- `--output` - Ścieżka do pliku wyjściowego z raportem (domyślnie: wyświetlenie w konsoli) 
- `--fix` - Próba naprawy bazy danych (wykonuje backup przed naprawą)

### fix_database_issues.py

Skrypt do naprawy typowych problemów z bazą danych systemu LLM Trader MT5, w tym:

- Odbudowa brakujących tabel
- Naprawa kluczy obcych
- Usunięcie zduplikowanych rekordów
- Optymalizacja bazy danych

Skrypt jest komplementarny do check_database.py i koncentruje się na naprawie wykrytych problemów.

**Użycie:**
```bash
python scripts/fix_database_issues.py --env dev
python scripts/fix_database_issues.py --db-path database/dev.db --output raport_naprawy.json
python scripts/fix_database_issues.py --env test --no-backup
```

**Parametry:**
- `--db-path` - Ścieżka do pliku bazy danych (domyślnie: database/dev.db)
- `--env` - Typ środowiska: dev, test, prod (wpływa na ścieżkę bazy danych)
- `--output` - Ścieżka do pliku wyjściowego z raportem (domyślnie: wyświetlenie w konsoli)
- `--no-backup` - Pomiń tworzenie kopii zapasowej (nie zalecane)

## Integracja z systemem monitorowania

Skrypty diagnostyczne i naprawcze są zintegrowane z systemem monitorowania (`monitor_system.py`), umożliwiając:

1. Regularne automatyczne sprawdzanie integralności bazy danych (domyślnie co 2 godziny)
2. Powiadamianie o wykrytych problemach (email)
3. Opcjonalną automatyczną naprawę problemów

Konfiguracja monitorowania bazy danych znajduje się w pliku `config/{env}/monitor_config.json` w sekcji `db_monitoring`:

```json
{
    "db_monitoring": {
        "check_interval": 7200,
        "auto_fix": false,
        "notify_on_issues": true,
        "critical_tables": ["trades", "trade_ideas", "market_analysis"],
        "max_row_limits": {
            "logs": 10000,
            "market_analysis": 5000,
            "statistics": 1000
        }
    }
}
```

Aby uruchomić system monitorowania z diagnostyką bazy danych:

```bash
python scripts/monitor_system.py --env dev --auto-restart --email-notify --db-auto-fix
```

## Uwagi dotyczące użytkowania

1. Skrypty należy uruchamiać z głównego katalogu projektu.
2. Większość skryptów wymaga zainstalowanych zależności wymienionych w `requirements.txt` lub `pyproject.toml`.
3. Przed uruchomieniem skryptów w środowisku produkcyjnym, należy je przetestować w środowisku deweloperskim.
4. Wszystkie skrypty zapisują logi w katalogu `logs/`.
5. W przypadku problemów, warto uruchomić skrypty z parametrem `--debug`.

## Zasady rozwoju skryptów

1. Każdy nowy skrypt powinien zawierać dokumentację w formie komentarzy i opisu w tym pliku.
2. Skrypty powinny być modułowe i możliwe do uruchomienia niezależnie.
3. Skrypty powinny obsługiwać parametry wiersza poleceń z sensownymi wartościami domyślnymi.
4. Każdy skrypt powinien zawierać obsługę błędów i logowanie. 
# LLM Trading System

System LLM Trading to zaawansowana platforma handlowa wykorzystująca modele językowe (LLM) do analizy rynku i generowania sygnałów handlowych. System integruje się z platformą MetaTrader 5 i umożliwia automatyczne podejmowanie decyzji inwestycyjnych.

## Główne funkcjonalności

- Analiza rynku z wykorzystaniem modeli LLM (np. Grok, GPT-4)
- Automatyczne generowanie sygnałów handlowych
- Zarządzanie ryzykiem i kapitałem
- Integracja z platformą MetaTrader 5
- Dashboard do monitorowania wyników i statystyk
- Wsparcie dla wielu instrumentów finansowych i strategii

## Struktura projektu

Projekt składa się z kilku głównych komponentów:

- **Agent_Manager** - Zarządzanie agentami handlowymi i strategiami
- **Database** - Przechowywanie danych rynkowych, analiz i transakcji
- **Dashboard** - Interfejs webowy do monitorowania systemu
- **LLM_Engine** - Silnik modeli językowych do analizy rynku
- **MT5_Connector** - Łącznik z platformą MetaTrader 5
- **Expert_Advisor** - Kody dla MT5 Expert Advisors

Szczegółowy opis struktury znajduje się w pliku [docs/system_structure.md](docs/system_structure.md).

## Uruchamianie systemu

System można uruchomić na kilka sposobów:

### 1. Uruchomienie całego systemu

```bash
python -m scripts.run_system [--env dev|test|prod] [--debug]
```

### 2. Uruchomienie poszczególnych komponentów

```bash
python -m Agent_Manager.run_manager [--env dev|test|prod]
python -m Dashboard.run_dashboard [--port PORT]
python -m MT5_Connector.run_connector
python -m LLM_Engine.run_engine
python -m Database.run_database
```

### 3. Narzędzia analityczne

```bash
python -m scripts.run_analysis --symbol EURUSD --timeframe H1
python -m scripts.show_analysis --analysis-id ID
```

Więcej informacji o dostępnych skryptach znajduje się w pliku [scripts/README.md](scripts/README.md).

## Instalacja

Szczegółowa instrukcja instalacji znajduje się w pliku [docs/installation_guide.md](docs/installation_guide.md).

Szybki start:

```bash
# Klonowanie repozytorium
git clone https://github.com/twoj-username/llm-trader-mt5.git
cd llm-trader-mt5

# Instalacja zależności
pip install -e .
# lub z użyciem Poetry
poetry install

# Konfiguracja środowiska
python -m scripts.setup_environment --env dev

# Inicjalizacja bazy danych
python -m scripts.setup_database --init
```

## Konfiguracja

System używa plików konfiguracyjnych w formacie JSON, znajdujących się w katalogu `config/`:

- `config_dev.json` - konfiguracja dla środowiska deweloperskiego
- `config_test.json` - konfiguracja dla środowiska testowego
- `config_prod.json` - konfiguracja dla środowiska produkcyjnego

Dodatkowo, wrażliwe dane (klucze API, hasła) powinny być przechowywane w pliku `.env`.

## Dokumentacja

- [Instrukcja instalacji](docs/installation_guide.md)
- [Struktura systemu](docs/system_structure.md)
- [Zasady rozwoju](docs/rozwoj_systemu.md)
- [API Reference](docs/api_reference.md)

## Rozwijanie projektu

Informacje dla deweloperów na temat rozwijania projektu znajdują się w pliku [docs/rozwoj_systemu.md](docs/rozwoj_systemu.md).

## Licencja

Ten projekt jest udostępniany na licencji MIT. Szczegóły w pliku [LICENSE](LICENSE). 
# Przegląd systemu handlowego LLM_EA

## Wprowadzenie

System handlowy LLM_EA to zaawansowane narzędzie wykorzystujące modele języka (LLM) do analizy rynków finansowych i automatyzacji handlu na platformie MetaTrader 5. System integruje różne komponenty odpowiedzialne za analizę danych, podejmowanie decyzji handlowych, zarządzanie ryzykiem i wykonywanie zleceń.

## Architektura systemu

System składa się z kilku głównych komponentów, które współpracują ze sobą:

1. **MT5_Connector** - odpowiada za komunikację z platformą MetaTrader 5, pobieranie danych rynkowych i realizację zleceń handlowych.
2. **LLM_Engine** - wykorzystuje modele języka (np. XAI/Grok) do analizy rynku i generowania pomysłów handlowych.
3. **Agent_Manager** - zarządza strategiami handlowymi, koordynuje decyzje i zarządza ryzykiem.
4. **Database** - przechowuje dane historyczne, analizy i wyniki handlowe.
5. **Dashboard** - interfejs użytkownika do monitorowania i zarządzania systemem.
6. **Common** - zawiera współdzielone funkcje i narzędzia używane przez inne komponenty.
7. **Expert_Advisor** - skrypty EA dla platformy MT5, które komunikują się z systemem.

## Sposób funkcjonowania

Proces działania systemu przebiega następująco:

1. **Pobieranie danych** - MT5_Connector pobiera dane rynkowe z platformy MT5.
2. **Analiza danych** - LLM_Engine analizuje dane przy użyciu wskaźników technicznych i modeli LLM.
3. **Generowanie pomysłów handlowych** - na podstawie analizy system generuje propozycje transakcji.
4. **Zarządzanie ryzykiem** - Agent_Manager ocenia ryzyko i dostosowuje wielkość pozycji.
5. **Realizacja zleceń** - zatwierdzone zlecenia są przekazywane do MT5.
6. **Monitorowanie** - system monitoruje otwarte pozycje i ogólny stan komponentów.
7. **Raportowanie** - wyniki i statystyki są dostępne poprzez Dashboard.

## Uruchamianie systemu

Główne skrypty uruchamiające komponenty:

| Komponent | Skrypt uruchomieniowy |
|-----------|------------------------|
| Database | Database/run_database.py |
| MT5_Connector | MT5_Connector/run_connector.py |
| LLM_Engine | LLM_Engine/run_engine.py |
| Agent_Manager | Agent_Manager/run_manager.py |
| Dashboard | Dashboard/run_dashboard.py |

System można uruchomić całościowo przy użyciu skryptu `scripts/run_system.py` lub `scripts/run_demo_test.py` dla środowiska testowego.

### Przykłady uruchomienia:

```bash
# Pełny system
python scripts/run_system.py --env dev

# System testowy na koncie demo
python scripts/run_demo_test.py --env dev --duration 24 --symbols EURUSD,GBPUSD
```

## Monitorowanie systemu

System zawiera narzędzia do monitorowania stanu i wydajności, głównie w postaci skryptu `scripts/monitor_system.py`. Narzędzie to pozwala na:

- Sprawdzanie zasobów systemowych (CPU, RAM, dysk)
- Monitorowanie połączeń sieciowych
- Weryfikację stanu bazy danych
- Kontrolę uruchomionych procesów
- Automatyczne restartowanie niedziałających komponentów

### Przykład uruchomienia monitorowania:

```bash
python scripts/monitor_system.py --env dev --auto-restart --db-check-interval 3600
```

## Konfiguracja

Konfiguracja systemu znajduje się w katalogu `config`, z podziałem na środowiska (dev, test, prod). Kluczowe pliki konfiguracyjne to:

- `config/config_dev.json` - główna konfiguracja dla środowiska deweloperskiego
- `config/config_test.json` - konfiguracja dla środowiska testowego
- `config/config_prod.json` - konfiguracja dla środowiska produkcyjnego

## Testowanie

System zawiera kompleksowy zestaw testów jednostkowych i integracyjnych w katalogu `tests/`. Obejmują one wszystkie główne komponenty i funkcjonalności.

## Rozwój systemu

Podczas rozwoju systemu należy przestrzegać następujących zasad:

1. Utrzymywanie modularnej architektury i przestrzeganie zasad separacji odpowiedzialności
2. Dokumentowanie nowych funkcjonalności i aktualizowanie dokumentacji
3. Tworzenie testów jednostkowych dla nowych komponentów
4. Przestrzeganie standardów kodowania i konwencji nazewniczych
5. Regularne monitorowanie wydajności i optymalizowanie wąskich gardeł
6. Aktualizowanie plików README.md w każdym katalogu komponentu 
# Instrukcja uruchomienia systemu LLM Trading na koncie demo

Ta instrukcja przeprowadzi Cię przez proces konfiguracji i uruchomienia systemu LLM Trading na koncie demo platformy MetaTrader 5. Dzięki temu będziesz mógł przetestować działanie systemu bez ryzyka utraty rzeczywistych środków.

## Przygotowanie środowiska

### 1. Upewnij się, że masz zainstalowane wymagane komponenty:
- Python 3.10 lub nowszy
- MetaTrader 5
- Konto demo w platformie MetaTrader 5
- Klucz API dla modelu Grok (X.AI)

### 2. Konfiguracja zmiennych środowiskowych

Stwórz lub edytuj plik `.env` w głównym katalogu projektu:

```
# Konfiguracja środowiska
ENV=dev
DEBUG=True
LOG_LEVEL=INFO

# Konfiguracja API X.AI (Grok)
X_API_KEY=twój_klucz_api

# Konfiguracja MetaTrader 5
MT5_ACCOUNT=numer_twojego_konta_demo
MT5_PASSWORD=hasło_do_konta_demo
MT5_SERVER=nazwa_brokera
MT5_PATH=ścieżka_do_mt5

# Konfiguracja handlu
TRADING_MODE=DEMO  # Ważne: ustaw tryb na DEMO!
DEFAULT_RISK_PERCENTAGE=1.0
MAX_DAILY_RISK_PERCENTAGE=5.0
MAX_POSITIONS=3
TRADING_SYMBOLS=EURUSD,GBPUSD,USDJPY
```

## Instalacja Expert Advisor w MetaTrader 5

1. Otwórz MetaTrader 5 i zaloguj się na swoje konto demo
2. Przejdź do menu "File" > "Open Data Folder", aby otworzyć katalog danych MT5
3. Przejdź do folderu "MQL5/Experts/"
4. Skopiuj plik `Expert_Advisor/LLM_EA.mq5` i katalog `Expert_Advisor/Include` do tego folderu
5. Otwórz MetaEditor (przycisk F4 w MT5 lub z menu "Tools" > "MetaEditor")
6. W MetaEditor otwórz plik LLM_EA.mq5 i skompiluj go (przycisk F7 lub menu "Program" > "Compile")
7. Po udanej kompilacji plik .ex5 powinien zostać automatycznie utworzony

## Konfiguracja bazy danych

Uruchom skrypt do inicjalizacji bazy danych w trybie deweloperskim:

```bash
python scripts/setup_database.py --env dev --demo-data
```

Komenda ta utworzy bazę danych i wypełni ją przykładowymi danymi do testów.

## Uruchomienie systemu

### 1. Uruchom Expert Advisor w MetaTrader 5

1. W MT5 otwórz wykres wybranej pary walutowej (np. EURUSD) na wybranym interwale
2. Z nawigacji znajdź "Expert Advisors" > "LLM_EA" i przeciągnij go na wykres
3. W oknie konfiguracji eksperta ustaw parametry:
   - `InpMagicNumber` - unikalny numer identyfikujący transakcje EA (np. 123456)
   - `InpZmqServer` - adres serwera ZeroMQ (domyślnie "localhost")
   - `InpZmqReqPort` - port dla REQUEST/REPLY (domyślnie 5555)
   - `InpZmqPubPort` - port dla PUBLISH/SUBSCRIBE (domyślnie 5556)
   - `InpUseExternalSignals` - ustaw na true, aby używać sygnałów z systemu Python
4. Kliknij "OK", aby uruchomić eksperta
5. Upewnij się, że handel algorytmiczny jest włączony (kliknij przycisk "AutoTrading" na górnym pasku narzędzi)

### 2. Uruchom komponenty systemu LLM Trading

Możesz uruchomić cały system za pomocą jednego skryptu:

```bash
python scripts/run_system.py --env dev --debug
```

Alternatywnie możesz uruchamiać komponenty pojedynczo (w oddzielnych oknach terminala):

```bash
# Uruchom bazę danych
python Database/run_database.py --env dev

# Uruchom konektor MT5
python MT5_Connector/run_connector.py --env dev

# Uruchom silnik LLM
python LLM_Engine/run_engine.py --env dev

# Uruchom agenta zarządzającego
python Agent_Manager/run_agent.py --env dev

# Uruchom dashboard
python Dashboard/run_dashboard.py --env dev --port 5000
```

### 3. Uruchom dashboard do monitorowania

Po uruchomieniu komponentów systemu, otwórz przeglądarkę i przejdź pod adres:

```
http://localhost:5000
```

Dashboard pozwala na:
- Monitorowanie stanu systemu
- Przeglądanie analiz rynkowych
- Zarządzanie pomysłami handlowymi
- Sprawdzanie statystyk i wyników handlu

## Monitorowanie systemu

Aby monitorować system pod kątem ewentualnych problemów i błędów, uruchom skrypt monitorujący:

```bash
python scripts/monitor_system.py --env dev --auto-restart --db-check-interval 3600
```

Dodatkowo, możesz regularnie sprawdzać integralność bazy danych:

```bash
python scripts/check_database.py --env dev
```

## Testowanie na koncie demo

1. Po uruchomieniu systemu, obserwuj analizy rynkowe generowane przez silnik LLM
2. Pomysły handlowe z wystarczająco wysokim współczynnikiem pewności są automatycznie realizowane na koncie demo
3. Monitoruj otwarte pozycje w dashboardzie oraz w terminalu MT5
4. Sprawdzaj logi systemu w katalogu `logs/` aby zdiagnozować ewentualne problemy
5. Po 24 godzinach działania przeanalizuj wyniki i dostosuj parametry systemu

## Wyłączanie systemu

Aby wyłączyć system:

1. Zamknij wszystkie uruchomione komponenty (Ctrl+C w terminalu lub zamknij okna)
2. Usuń Expert Advisor z wykresu w MT5 (kliknij prawym przyciskiem myszy na wykresie i wybierz "Expert Advisors" > "Remove")
3. W razie potrzeby wykonaj backup bazy danych:
   ```bash
   cp database/dev.db database/dev.db.backup
   ```

## Rozwiązywanie problemów

### Problem z połączeniem z MT5
- Upewnij się, że Expert Advisor jest poprawnie zainstalowany i uruchomiony na wykresie
- Sprawdź, czy porty ZeroMQ nie są blokowane przez zaporę sieciową
- Upewnij się, że masz odpowiednie uprawnienia dla katalogu, w którym znajduje się terminal MT5

### Brak sygnałów handlowych
- Sprawdź logi silnika LLM (`logs/llm_engine/`) pod kątem błędów komunikacji z API
- Upewnij się, że klucz API jest poprawny i masz wystarczający limit zapytań
- Sprawdź, czy wybrane pary walutowe są dostępne u twojego brokera

### Problemy z bazą danych
- Uruchom diagnostykę bazy danych: `python scripts/check_database.py --env dev`
- W razie wykrycia problemów napraw je: `python scripts/fix_database_issues.py --env dev`
- Sprawdź logi bazy danych w katalogu `logs/database/` 
# MT5_Connector

Moduł do komunikacji z platformą MetaTrader 5, odpowiedzialny za pobieranie danych rynkowych, obliczanie wskaźników technicznych, identyfikację formacji świecowych oraz formatowanie danych dla modelu LLM.

## Struktura

```
MT5_Connector/
├── __init__.py            # Inicjalizacja modułu
├── mt5_client.py          # Klient MT5 do komunikacji z platformą
├── indicators.py          # Wskaźniki techniczne
├── candlestick_patterns.py # Identyfikacja formacji świecowych
├── data_formatter.py      # Formatowanie danych dla LLM
└── connector.py           # Główny interfejs łączący wszystkie komponenty
```

## Główne funkcjonalności

### MT5Client

Klasa odpowiedzialna za bezpośrednią komunikację z platformą MT5:

- Połączenie i autoryzacja z platformą
- Pobieranie danych OHLCV (świece)
- Pobieranie informacji o koncie
- Pobieranie informacji o symbolu

### TechnicalIndicators

Implementacja popularnych wskaźników technicznych:

- SMA, EMA
- ATR
- VWAP
- RSI
- Bollinger Bands
- MACD

### CandlestickPatterns

Rozpoznawanie i identyfikacja formacji świecowych:

- Formacje jednościecowe (Doji, Hammer, Shooting Star, Marubozu)
- Formacje dwuświecowe (Engulfing, Harami)
- Formacje trójświecowe (Morning Star, Evening Star, Three White Soldiers, Three Black Crows)

### DataFormatter

Formatowanie danych dla modelu LLM:

- Formatowanie danych OHLCV
- Formatowanie wskaźników technicznych
- Formatowanie rozpoznanych formacji świecowych
- Tworzenie podsumowania rynku

### MT5Connector

Główny interfejs integrujący wszystkie komponenty:

- Inicjalizacja i zarządzanie połączeniem z MT5
- Pobieranie danych z wskaźnikami i formacjami
- Formatowanie kompleksowych danych dla LLM
- Zarządzanie cache'em danych

## Przykład użycia

```python
from MT5_Connector.connector import MT5Connector

# Inicjalizacja konektora
connector = MT5Connector()
connector.initialize()

# Pobieranie danych świec z wskaźnikami i formacjami
symbol = "EURUSD"
timeframe = 5  # 5 minut
df = connector.get_candles(symbol, timeframe, 100)

# Pobieranie sformatowanych danych dla LLM
formatted_data = connector.get_formatted_data_for_llm(symbol, timeframe, 50)

# Wyświetlenie podsumowania
print(formatted_data.split("\n\n")[0])

# Zakończenie połączenia
connector.shutdown()
```

## Wymagania

- MetaTrader 5 (zainstalowany)
- Python 3.10+
- Pakiety: metatrader5, pandas, numpy, python-dotenv, loguru

## Konfiguracja

Moduł korzysta z następujących zmiennych środowiskowych:

- `MT5_LOGIN` - Login do konta MT5
- `MT5_PASSWORD` - Hasło do konta MT5
- `MT5_SERVER` - Nazwa serwera
- `MT5_SYMBOL` - Domyślny symbol (np. "EURUSD")
- `MT5_TIMEFRAME` - Domyślny timeframe w minutach (np. 1, 5, 15) 
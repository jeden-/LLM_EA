# API Reference - LLM Trading System

Ten dokument zawiera referencję do najważniejszych klas i metod w systemie LLM Trading.

## Spis treści

1. [Agent_Manager](#agent_manager)
2. [Database](#database)
3. [LLM_Engine](#llm_engine)
4. [MT5_Connector](#mt5_connector)
5. [Dashboard](#dashboard)

---

## Agent_Manager

### Klasa `AgentManager`

Główna klasa zarządzająca agentami handlowymi i strategiami.

```python
class AgentManager:
    def __init__(self, db_handler, order_processor, market_analyzer, risk_manager, strategy_manager=None):
        # ...
```

#### Metody publiczne

| Metoda | Opis | Parametry | Zwracana wartość |
|--------|------|-----------|------------------|
| `get_market_data(symbol, timeframe, num_bars)` | Pobiera dane rynkowe | `symbol`: str, `timeframe`: str, `num_bars`: int | dict |
| `analyze_market(symbol, timeframe, price_data, indicators=None, strategy_name=None, risk_level="moderate")` | Analizuje rynek | `symbol`: str, `timeframe`: str, `price_data`: dict, ... | dict |
| `get_open_positions()` | Pobiera otwarte pozycje | - | list[dict] |
| `open_position(symbol, order_type, volume, stop_loss=None, take_profit=None, comment=None)` | Otwiera nową pozycję | `symbol`: str, `order_type`: str, `volume`: float, ... | dict |
| `close_position(position_id, reason=None)` | Zamyka pozycję | `position_id`: int, `reason`: str | dict |
| `modify_position(position_id, stop_loss=None, take_profit=None)` | Modyfikuje istniejącą pozycję | `position_id`: int, `stop_loss`: float, ... | dict |
| `get_account_info()` | Pobiera informacje o koncie | - | dict |

### Klasa `RiskManager`

Zarządza ryzykiem podczas handlu.

```python
class RiskManager:
    def __init__(self):
        # ...
```

#### Metody publiczne

| Metoda | Opis | Parametry | Zwracana wartość |
|--------|------|-----------|------------------|
| `set_daily_risk_limit_pct(limit_pct)` | Ustawia dzienny limit ryzyka | `limit_pct`: float | None |
| `set_position_risk_limit_pct(limit_pct)` | Ustawia limit ryzyka na pozycję | `limit_pct`: float | None |
| `set_max_open_positions(max_positions)` | Ustawia maksymalną liczbę otwartych pozycji | `max_positions`: int | None |
| `calculate_position_size(symbol, risk_pct, stop_loss_pips)` | Oblicza wielkość pozycji | `symbol`: str, `risk_pct`: float, `stop_loss_pips`: float | float |
| `validate_trade(symbol, order_type, volume, stop_loss, take_profit)` | Sprawdza zgodność zlecenia z zasadami zarządzania ryzykiem | `symbol`: str, `order_type`: str, ... | tuple(bool, str) |

### Klasa `StrategyManager`

Zarządza strategiami handlowymi.

```python
class StrategyManager:
    def __init__(self, db_handler):
        # ...
```

#### Metody publiczne

| Metoda | Opis | Parametry | Zwracana wartość |
|--------|------|-----------|------------------|
| `get_active_strategies()` | Pobiera aktywne strategie | - | list[dict] |
| `get_strategy_by_name(name)` | Pobiera strategię po nazwie | `name`: str | dict |
| `add_strategy(strategy_data)` | Dodaje nową strategię | `strategy_data`: dict | int (strategy_id) |
| `update_strategy(strategy_id, strategy_data)` | Aktualizuje strategię | `strategy_id`: int, `strategy_data`: dict | bool |
| `enable_strategy(strategy_id)` | Włącza strategię | `strategy_id`: int | bool |
| `disable_strategy(strategy_id)` | Wyłącza strategię | `strategy_id`: int | bool |

---

## Database

### Klasa `DatabaseHandler`

Zarządza bazą danych i operacjami na danych.

```python
class DatabaseHandler:
    def __init__(self, db_path=None, auto_init=True):
        # ...
```

#### Metody publiczne

| Metoda | Opis | Parametry | Zwracana wartość |
|--------|------|-----------|------------------|
| `initialize_database()` | Inicjalizuje bazę danych | - | bool |
| `add_market_analysis(analysis_data)` | Dodaje analizę rynku | `analysis_data`: dict | int (analysis_id) |
| `get_market_analysis(analysis_id=None, symbol=None, timeframe=None, limit=10)` | Pobiera analizy rynku | `analysis_id`: int, ... | list[dict] |
| `add_trade_idea(trade_idea_data)` | Dodaje pomysł handlowy | `trade_idea_data`: dict | int (idea_id) |
| `get_trade_ideas(idea_id=None, symbol=None, status=None, limit=10)` | Pobiera pomysły handlowe | `idea_id`: int, ... | list[dict] |
| `add_trade(trade_data)` | Dodaje transakcję | `trade_data`: dict | int (trade_id) |
| `get_trades(trade_id=None, symbol=None, status=None, limit=10)` | Pobiera transakcje | `trade_id`: int, ... | list[dict] |
| `add_strategy(strategy_data)` | Dodaje strategię | `strategy_data`: dict | int (strategy_id) |
| `get_strategies(strategy_id=None, active_only=False, limit=10)` | Pobiera strategie | `strategy_id`: int, ... | list[dict] |
| `add_log(log_data)` | Dodaje log | `log_data`: dict | int (log_id) |
| `get_logs(log_level=None, component=None, limit=100)` | Pobiera logi | `log_level`: str, ... | list[dict] |
| `get_statistics(start_date=None, end_date=None)` | Pobiera statystyki | `start_date`: str, `end_date`: str | dict |

---

## LLM_Engine

### Klasa `LLMEngine`

Silnik analizy wykorzystujący modele językowe.

```python
class LLMEngine:
    def __init__(self, db_handler=None, api_key=None, api_url=None, model=None, max_tokens=None, temperature=None):
        # ...
```

#### Metody publiczne

| Metoda | Opis | Parametry | Zwracana wartość |
|--------|------|-----------|------------------|
| `initialize(use_cache=True)` | Inicjalizuje silnik LLM | `use_cache`: bool | bool |
| `analyze_market(symbol, timeframe, price_data, indicators=None, news=None, strategy_name=None, risk_level="moderate", additional_context=None)` | Analizuje rynek | `symbol`: str, ... | dict |
| `validate_analysis(analysis_result)` | Waliduje wynik analizy | `analysis_result`: dict | tuple(bool, str) |
| `shutdown()` | Wyłącza silnik LLM | - | None |

### Klasa `MarketAnalyzer`

Analizuje dane rynkowe.

```python
class MarketAnalyzer:
    def __init__(self, llm_engine, db_handler=None):
        # ...
```

#### Metody publiczne

| Metoda | Opis | Parametry | Zwracana wartość |
|--------|------|-----------|------------------|
| `analyze_market(symbol, timeframe, price_data, indicators=None, news=None, strategy_name=None, risk_level="moderate", additional_context=None)` | Analizuje rynek | `symbol`: str, ... | dict |
| `calculate_indicators(price_data, indicators=None)` | Oblicza wskaźniki techniczne | `price_data`: dict, `indicators`: list[str] | dict |
| `get_market_sentiment(symbol, timeframe="D1")` | Pobiera nastroje rynkowe | `symbol`: str, `timeframe`: str | dict |

---

## MT5_Connector

### Klasa `MT5Connector`

Łączy się z platformą MetaTrader 5.

```python
class MT5Connector:
    def __init__(self, db_handler=None, server=None, login=None, password=None, timeout=None):
        # ...
```

#### Metody publiczne

| Metoda | Opis | Parametry | Zwracana wartość |
|--------|------|-----------|------------------|
| `initialize(use_mock=False)` | Inicjalizuje połączenie z MT5 | `use_mock`: bool | bool |
| `get_account_info()` | Pobiera informacje o koncie | - | dict |
| `get_market_data(symbol, timeframe, num_bars)` | Pobiera dane rynkowe | `symbol`: str, `timeframe`: str, `num_bars`: int | dict |
| `get_symbol_info(symbol)` | Pobiera informacje o instrumencie | `symbol`: str | dict |
| `get_open_positions()` | Pobiera otwarte pozycje | - | list[dict] |
| `get_position_history(start_date=None, end_date=None)` | Pobiera historię pozycji | `start_date`: str, `end_date`: str | list[dict] |
| `open_position(symbol, order_type, volume, stop_loss=None, take_profit=None, comment=None)` | Otwiera pozycję | `symbol`: str, ... | dict |
| `close_position(position_id, reason=None)` | Zamyka pozycję | `position_id`: int, `reason`: str | dict |
| `modify_position(position_id, stop_loss=None, take_profit=None)` | Modyfikuje pozycję | `position_id`: int, ... | dict |
| `shutdown()` | Kończy połączenie z MT5 | - | None |

---

## Dashboard

### Klasa `Dashboard`

Interfejs webowy aplikacji Flask.

```python
# app.py
def create_app(db_handler=None, config=None):
    # ...
    return app
```

#### Główne endpointy

| Endpoint | Metoda HTTP | Opis |
|----------|-------------|------|
| `/` | GET | Strona główna dashboardu |
| `/overview` | GET | Przegląd systemu |
| `/market-analysis` | GET | Lista analiz rynkowych |
| `/market-analysis/<analysis_id>` | GET | Szczegóły analizy |
| `/trades` | GET | Lista transakcji |
| `/trades/<trade_id>` | GET | Szczegóły transakcji |
| `/strategies` | GET | Lista strategii |
| `/strategies/<strategy_id>` | GET, POST | Szczegóły i edycja strategii |
| `/logs` | GET | Logi systemu |
| `/settings` | GET, POST | Ustawienia systemu |
| `/api/v1/market-data/<symbol>/<timeframe>` | GET | API danych rynkowych |
| `/api/v1/analysis` | POST | API analizy rynku |
| `/api/v1/trades` | GET, POST | API transakcji |

## Obsługa błędów i wyjątki

System używa następujących klas wyjątków:

- `DatabaseError` - Błędy związane z bazą danych
- `MT5ConnectorError` - Błędy połączenia z MetaTrader 5
- `LLMEngineError` - Błędy silnika LLM
- `AgentManagerError` - Błędy zarządzania agentami
- `ConfigurationError` - Błędy konfiguracji

Każdy wyjątek zawiera:
- `message` - Opis błędu
- `code` - Kod błędu
- `details` - Dodatkowe szczegóły (opcjonalnie)

## Kody statusu

| Kod | Opis |
|-----|------|
| 0 | Sukces |
| 1 | Błąd ogólny |
| 100-199 | Błędy bazy danych |
| 200-299 | Błędy MT5 |
| 300-399 | Błędy LLM |
| 400-499 | Błędy zarządzania agentami |
| 500-599 | Błędy konfiguracji | 
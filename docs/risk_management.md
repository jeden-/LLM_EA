# Moduł Zarządzania Ryzykiem (RiskManager)

## Wprowadzenie

Moduł Zarządzania Ryzykiem jest kluczowym komponentem systemu handlowego LLM, odpowiedzialnym za ocenę ryzyka potencjalnych transakcji, kalkulację odpowiedniej wielkości pozycji zgodnie z przyjętymi zasadami zarządzania ryzykiem, walidację pomysłów handlowych oraz monitoring dziennego limitu ryzyka.

## Główne funkcjonalności

Moduł `RiskManager` oferuje następujące główne funkcjonalności:

1. **Kalkulacja wielkości pozycji** - obliczanie odpowiedniej wielkości pozycji na podstawie salda konta, akceptowalnego poziomu ryzyka i odległości stop-loss.
2. **Walidacja pomysłów handlowych** - weryfikacja poprawności i zgodności z zasadami zarządzania ryzykiem potencjalnych transakcji.
3. **Monitoring limitu dziennego ryzyka** - kontrola, czy suma ryzyka wszystkich dzisiejszych transakcji (zamkniętych i otwartych) nie przekracza zdefiniowanego limitu.

## Szczegółowy opis funkcji

### Obliczanie wielkości pozycji (calculate_position_size)

Ta funkcja kalkuluje optymalną wielkość pozycji na podstawie:
- Salda konta
- Maksymalnego akceptowalnego procentu ryzyka na transakcję
- Odległości między ceną wejścia a poziomem stop-loss

**Przykładowe użycie:**
```python
position_info = risk_manager.calculate_position_size(
    symbol="EURUSD", 
    entry_price=1.1000, 
    stop_loss=1.0950, 
    risk_percentage=1.0
)
```

**Zwracane dane:**
- `position_size` - zalecana wielkość pozycji w lotach
- `risk_amount` - kwota ryzyka w walucie bazowej
- `risk_percentage` - procent ryzyka
- Dodatkowe informacje (liczba pipsów ryzyka, koszt pipsa, itp.)

### Walidacja pomysłu handlowego (validate_trade_idea)

Ta funkcja sprawdza, czy pomysł handlowy spełnia zasady zarządzania ryzykiem:
- Poprawność kierunku (buy/sell)
- Logiczną relację między ceną wejścia, stop-loss i take-profit
- Minimalny stosunek zysku do ryzyka (domyślnie 1:1)

**Przykładowe użycie:**
```python
validation_result = risk_manager.validate_trade_idea(
    symbol="EURUSD",
    direction="buy",
    entry_price=1.1000,
    stop_loss=1.0950,
    take_profit=1.1100
)
```

**Zwracane dane:**
- `valid` - czy pomysł jest poprawny (True/False)
- `reason` - powód odrzucenia (jeśli pomysł jest niepoprawny)
- Dodatkowe informacje (stosunek zysku do ryzyka, zalecana wielkość pozycji, itp.)

### Sprawdzanie dziennego limitu ryzyka (check_daily_risk_limit)

Ta funkcja kontroluje, czy łączne ryzyko wszystkich dzisiejszych transakcji nie przekracza ustalonego limitu dziennego.

#### Metoda kalkulacji ryzyka:

- **Dla zamkniętych transakcji**: Uwzględniana jest faktyczna strata (jeśli transakcja została zamknięta ze stratą).
- **Dla otwartych transakcji**: Obliczana jest potencjalna strata jako:
  - Liczba pipsów ryzyka: |cena wejścia - stop-loss| / 0.0001
  - Wartość pipsa: 0.1 * wielkość pozycji (w lotach)
  - Potencjalna strata: liczba pipsów ryzyka * wartość pipsa

**Przykładowe użycie:**
```python
risk_result = risk_manager.check_daily_risk_limit(daily_risk_limit_pct=5.0)
```

**Zwracane dane:**
- `limit_exceeded` - czy limit ryzyka został przekroczony (True/False)
- `current_risk` - aktualne ryzyko w procentach
- `risk_limit` - ustawiony limit ryzyka
- `remaining_risk` - pozostały limit ryzyka
- `total_risk_amount` - łączna kwota ryzyka w walucie bazowej
- `account_balance` - saldo konta

## Przykład użycia modułu

```python
from Agent_Manager.risk_manager import RiskManager
from MT5_Connector.connector import MT5Connector
from Database.database import DatabaseHandler

# Inicjalizacja
db_handler = DatabaseHandler()
mt5_connector = MT5Connector()
risk_manager = RiskManager(db_handler=db_handler, max_risk_per_trade=2.0)
risk_manager.set_mt5_connector(mt5_connector)

# Walidacja pomysłu handlowego
validation_result = risk_manager.validate_trade_idea(
    symbol="EURUSD",
    direction="buy",
    entry_price=1.1000,
    stop_loss=1.0950,
    take_profit=1.1100
)

if validation_result["valid"]:
    position_size = validation_result["position_size"]
    print(f"Pomysł handlowy jest poprawny. Zalecana wielkość pozycji: {position_size} lot")
    
    # Sprawdzenie limitu dziennego ryzyka
    risk_check = risk_manager.check_daily_risk_limit(daily_risk_limit_pct=5.0)
    
    if risk_check["limit_exceeded"]:
        print("Dzienny limit ryzyka został przekroczony!")
        print(f"Aktualne ryzyko: {risk_check['current_risk']:.2f}%")
    else:
        print("Dzienny limit ryzyka nie został przekroczony.")
        print(f"Aktualne ryzyko: {risk_check['current_risk']:.2f}%")
        print(f"Pozostały limit: {risk_check['remaining_risk']:.2f}%")
else:
    print(f"Pomysł handlowy jest niepoprawny: {validation_result['reason']}")
```

## Uwagi implementacyjne

- Moduł wymaga poprawnie skonfigurowanego konektora MT5 do pobierania informacji o saldzie konta i danych instrumentów.
- Domyślny maksymalny procent ryzyka na transakcję jest ustawiony na 2.0%.
- Domyślny dzienny limit ryzyka jest ustawiony na 5.0%.
- Moduł zakłada 4-cyfrowe kwotowanie dla par walutowych. 
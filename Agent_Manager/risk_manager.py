"""
Moduł zarządzania ryzykiem dla systemu handlowego LLM.

Odpowiada za:
1. Ocenę ryzyka potencjalnych transakcji
2. Kalkulację wielkości pozycji
3. Weryfikację zgodności potencjalnych transakcji z zasadami zarządzania ryzykiem
4. Monitoring otwartych pozycji pod kątem ryzyka
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta

from MT5_Connector.connector import MT5Connector
from Database.database import DatabaseHandler

logger = logging.getLogger(__name__)

class RiskManager:
    """
    Klasa do zarządzania ryzykiem transakcji w systemie handlowym.
    """
    
    def __init__(self, db_handler: Optional[DatabaseHandler] = None, max_risk_per_trade: float = 2.0):
        """
        Inicjalizacja menedżera ryzyka.
        
        Args:
            db_handler: Handler bazy danych
            max_risk_per_trade: Maksymalne ryzyko na pojedynczą transakcję (w procentach)
        """
        self.db_handler = db_handler if db_handler else DatabaseHandler()
        self.max_risk_per_trade = max_risk_per_trade
        self.mt5_connector = None
        self.daily_risk_limit_pct = 5.0  # Domyślny limit ryzyka dziennego 5%
        
        logger.info(f"Inicjalizacja RiskManager z max ryzykiem na transakcję: {max_risk_per_trade}%")
    
    def set_mt5_connector(self, mt5_connector: MT5Connector) -> None:
        """
        Ustawienie konektora MT5.
        
        Args:
            mt5_connector: Instancja konektora MT5
        """
        self.mt5_connector = mt5_connector
    
    def set_daily_risk_limit_pct(self, limit_pct: float) -> None:
        """
        Ustawienie dziennego limitu ryzyka.
        
        Args:
            limit_pct: Limit ryzyka w procentach konta
        """
        self.daily_risk_limit_pct = limit_pct
        logger.info(f"Ustawiono dzienny limit ryzyka: {limit_pct}%")
    
    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        account_balance: Optional[float] = None,
        risk_percentage: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Kalkulacja wielkości pozycji na podstawie ryzyka.
        
        Args:
            symbol: Symbol instrumentu
            entry_price: Cena wejścia
            stop_loss: Poziom stop-loss
            account_balance: Saldo konta (opcjonalne - jeśli nie podane, pobierane z MT5)
            risk_percentage: Procent ryzyka (opcjonalne - jeśli nie podane, używany domyślny)
            
        Returns:
            Dict[str, Any]: Słownik z wyliczoną wielkością pozycji i szczegółami
        """
        if not self.mt5_connector:
            logger.error("MT5Connector nie został ustawiony. Nie można obliczyć wielkości pozycji.")
            return {
                "position_size": 0.01,  # Minimalna wielkość
                "error": "MT5Connector nie został ustawiony"
            }
        
        # Jeśli nie podano salda, pobierz z MT5
        if account_balance is None:
            account_info = self.mt5_connector.get_account_info()
            account_balance = account_info.get("balance", 0)
            
            if account_balance <= 0:
                logger.error(f"Nieprawidłowe saldo konta: {account_balance}")
                return {
                    "position_size": 0.01,
                    "error": "Nieprawidłowe saldo konta"
                }
        
        # Jeśli nie podano procentu ryzyka, użyj domyślnego
        risk_percentage = risk_percentage if risk_percentage is not None else self.max_risk_per_trade
        
        # Pobierz informacje o symbolu
        symbol_info = self.mt5_connector.get_symbol_info(symbol)
        
        if not symbol_info:
            logger.error(f"Nie można pobrać informacji o symbolu {symbol}")
            return {
                "position_size": 0.01,
                "error": f"Nie można pobrać informacji o symbolu {symbol}"
            }
        
        # Oblicz ryzyko w jednostkach waluty bazowej
        risk_amount = account_balance * (risk_percentage / 100)
        
        # Oblicz różnicę między ceną wejścia a stop-lossem
        price_difference = abs(entry_price - stop_loss)
        
        if price_difference <= 0:
            logger.error(f"Nieprawidłowa różnica cen: {price_difference}")
            return {
                "position_size": 0.01,
                "error": "Nieprawidłowa różnica cen"
            }
        
        # Pobierz informacje o kontrakcie
        contract_size = symbol_info.get("contract_size", 100000)  # Domyślnie dla Forex
        pip_value = symbol_info.get("pip_value", 0.0001)  # Domyślnie dla 4-cyfrowych kwotowań
        
        # Oblicz liczbę pipsów ryzyka
        pips_risk = price_difference / pip_value
        
        # Oblicz wartość jednego pipsa
        pip_cost = contract_size * pip_value
        
        # Oblicz wielkość pozycji
        if pips_risk > 0 and pip_cost > 0:
            lot_size = risk_amount / (pips_risk * pip_cost)
        else:
            lot_size = 0.01  # Minimalna wielkość
        
        # Ogranicz wielkość pozycji do dozwolonych wartości
        min_lot = symbol_info.get("min_lot", 0.01)
        max_lot = symbol_info.get("max_lot", 100.0)
        lot_step = symbol_info.get("lot_step", 0.01)
        
        # Zaokrąglij do kroków lota
        lot_size = round(lot_size / lot_step) * lot_step
        
        # Upewnij się, że lot jest w dozwolonym zakresie
        lot_size = max(min_lot, min(lot_size, max_lot))
        
        return {
            "position_size": lot_size,
            "account_balance": account_balance,
            "risk_amount": risk_amount,
            "risk_percentage": risk_percentage,
            "pips_risk": pips_risk,
            "pip_cost": pip_cost,
            "min_lot": min_lot,
            "max_lot": max_lot,
            "lot_step": lot_step
        }
    
    def validate_trade_idea(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        account_balance: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Walidacja pomysłu handlowego pod kątem zasad zarządzania ryzykiem.
        
        Args:
            symbol: Symbol instrumentu
            direction: Kierunek pozycji ('buy' lub 'sell')
            entry_price: Cena wejścia
            stop_loss: Poziom stop-loss
            take_profit: Poziom take-profit
            account_balance: Saldo konta (opcjonalne)
            
        Returns:
            Dict[str, Any]: Wynik walidacji z szczegółami
        """
        # Sprawdź poprawność kierunku
        if direction not in ["buy", "sell"]:
            return {
                "valid": False,
                "reason": f"Nieprawidłowy kierunek pozycji: {direction}"
            }
        
        # Sprawdź poprawność cen
        if entry_price <= 0 or stop_loss <= 0 or take_profit <= 0:
            return {
                "valid": False,
                "reason": "Ceny muszą być większe od zera"
            }
        
        # Sprawdź logikę stop-loss i take-profit
        is_valid_levels = False
        
        if direction == "buy":
            is_valid_levels = stop_loss < entry_price < take_profit
        else:  # sell
            is_valid_levels = stop_loss > entry_price > take_profit
        
        if not is_valid_levels:
            return {
                "valid": False,
                "reason": "Nieprawidłowe poziomy: stop-loss i take-profit muszą być logiczne dla kierunku pozycji"
            }
        
        # Oblicz stosunek zysku do ryzyka
        price_difference_risk = abs(entry_price - stop_loss)
        price_difference_reward = abs(take_profit - entry_price)
        
        if price_difference_risk <= 0:
            return {
                "valid": False,
                "reason": "Poziom stop-loss jest zbyt blisko ceny wejścia"
            }
        
        risk_reward_ratio = price_difference_reward / price_difference_risk
        
        # Sprawdź, czy stosunek zysku do ryzyka jest akceptowalny (minimalnie 1:1)
        if risk_reward_ratio < 1.0:
            return {
                "valid": False,
                "reason": f"Stosunek zysku do ryzyka jest zbyt niski: {risk_reward_ratio:.2f}"
            }
        
        # Oblicz wielkość pozycji
        position_size_info = self.calculate_position_size(
            symbol=symbol,
            entry_price=entry_price,
            stop_loss=stop_loss,
            account_balance=account_balance
        )
        
        # Jeśli wystąpił błąd w obliczaniu wielkości pozycji
        if "error" in position_size_info:
            return {
                "valid": False,
                "reason": position_size_info["error"]
            }
        
        # Zwróć pełny wynik walidacji
        return {
            "valid": True,
            "risk_reward_ratio": risk_reward_ratio,
            "position_size": position_size_info["position_size"],
            "risk_percentage": position_size_info["risk_percentage"],
            "pips_risk": position_size_info["pips_risk"]
        }
    
    def check_daily_risk_limit(
        self,
        daily_risk_limit_pct: float = 5.0
    ) -> Dict[str, Any]:
        """
        Sprawdzenie, czy dzienny limit ryzyka nie został przekroczony.
        
        Metoda analizuje zamknięte i otwarte transakcje z bieżącego dnia.
        Dla zamkniętych transakcji uwzględnia faktyczną stratę.
        Dla otwartych transakcji oblicza potencjalną stratę jako różnicę między ceną wejścia a poziomem stop-loss:
            - Liczba pipsów ryzyka = |cena wejścia - stop-loss| / 0.0001
            - Wartość pipsa = 0.1 * wielkość pozycji (w lotach)
            - Potencjalna strata = liczba pipsów ryzyka * wartość pipsa
        
        Args:
            daily_risk_limit_pct: Dzienny limit ryzyka w procentach (domyślnie 5.0%)
            
        Returns:
            Dict[str, Any]: Słownik zawierający:
                - limit_exceeded: Czy limit ryzyka został przekroczony (bool)
                - current_risk: Aktualne ryzyko w procentach
                - risk_limit: Ustawiony limit ryzyka w procentach
                - remaining_risk: Pozostały limit ryzyka w procentach
                - total_risk_amount: Łączna kwota ryzyka w walucie bazowej
                - account_balance: Saldo konta
                - reason: Powód przekroczenia limitu (opcjonalnie)
        """
        # Pobierz dzisiejsze transakcje
        today = datetime.now().strftime("%Y-%m-%d")
        today_trades = []
        
        if self.db_handler:
            # Zakładamy, że baza danych ma funkcję do pobierania transakcji z danego dnia
            # Jeśli nie istnieje, trzeba ją zaimplementować
            trades = self.db_handler.get_trades(limit=100)
            
            for trade in trades:
                trade_date = datetime.fromisoformat(trade["entry_time"]).strftime("%Y-%m-%d")
                if trade_date == today:
                    today_trades.append(trade)
        
        # Jeśli nie ma dzisiejszych transakcji, zwróć, że limit nie został przekroczony
        if not today_trades:
            return {
                "limit_exceeded": False,
                "current_risk": 0.0,
                "risk_limit": daily_risk_limit_pct,
                "remaining_risk": daily_risk_limit_pct
            }
        
        # Pobierz saldo konta
        account_balance = 0
        if self.mt5_connector:
            account_info = self.mt5_connector.get_account_info()
            account_balance = account_info.get("balance", 0)
        
        if account_balance <= 0:
            return {
                "limit_exceeded": True,
                "reason": "Nie można pobrać salda konta",
                "current_risk": 0.0,
                "risk_limit": daily_risk_limit_pct,
                "remaining_risk": 0.0
            }
        
        # Oblicz dzisiejsze całkowite ryzyko
        total_risk_amount = 0.0
        
        for trade in today_trades:
            # Jeśli transakcja ma status 'closed', mamy już wynik
            if trade["status"] == "closed" and trade["profit_loss"] is not None:
                if trade["profit_loss"] < 0:
                    total_risk_amount += abs(trade["profit_loss"])
            # Dla otwartych transakcji oblicz potencjalne ryzyko
            elif trade["status"] == "open":
                entry_price = trade["entry_price"]
                stop_loss = trade["stop_loss"]
                volume = trade["volume"]
                
                # Potencjalna strata w pipsach
                pips_risk = abs(entry_price - stop_loss) / 0.0001  # Zakładamy 4-cyfrowe kwotowanie
                
                # Wartość pipsa w walucie bazowej
                # Dla standardowego lota (1.0), wartość pipsa to zazwyczaj 0.1 USD dla par walutowych z USD
                # Skalujemy tę wartość proporcjonalnie do wielkości pozycji
                pip_value = 0.1 * volume  # 0.1 USD na pip dla standardowego lota
                
                # Całkowita potencjalna strata dla tej pozycji
                potential_loss = pips_risk * pip_value
                total_risk_amount += potential_loss
        
        # Oblicz procent ryzyka
        risk_percentage = (total_risk_amount / account_balance) * 100
        remaining_risk = daily_risk_limit_pct - risk_percentage
        
        return {
            "limit_exceeded": risk_percentage >= daily_risk_limit_pct,
            "current_risk": risk_percentage,
            "risk_limit": daily_risk_limit_pct,
            "remaining_risk": max(0, remaining_risk),
            "total_risk_amount": total_risk_amount,
            "account_balance": account_balance
        } 
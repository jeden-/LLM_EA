"""
Testy jednostkowe dla modułu RiskManager.
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from Agent_Manager.risk_manager import RiskManager
from MT5_Connector.connector import MT5Connector
from Database.database import DatabaseHandler


class TestRiskManager(unittest.TestCase):
    """Testy dla klasy RiskManager."""

    def setUp(self):
        """Inicjalizacja przed każdym testem."""
        self.db_handler = MagicMock(spec=DatabaseHandler)
        self.mt5_connector = MagicMock(spec=MT5Connector)
        self.risk_manager = RiskManager(db_handler=self.db_handler, max_risk_per_trade=2.0)
        self.risk_manager.set_mt5_connector(self.mt5_connector)

    def test_initialization(self):
        """Test inicjalizacji klasy RiskManager."""
        self.assertEqual(self.risk_manager.max_risk_per_trade, 2.0)
        self.assertIsNotNone(self.risk_manager.db_handler)
        self.assertIsNotNone(self.risk_manager.mt5_connector)

    def test_calculate_position_size(self):
        """Test obliczania wielkości pozycji."""
        # Mockowanie danych zwracanych przez MT5Connector
        self.mt5_connector.get_account_info.return_value = {"balance": 10000.0}
        self.mt5_connector.get_symbol_info.return_value = {
            "contract_size": 100000,
            "pip_value": 0.0001,
            "min_lot": 0.01,
            "max_lot": 100.0,
            "lot_step": 0.01
        }

        # Test dla pozycji kupna
        result = self.risk_manager.calculate_position_size(
            symbol="EURUSD",
            entry_price=1.1000,
            stop_loss=1.0950,
            risk_percentage=1.0
        )

        # Sprawdzamy, czy wyniki są poprawne
        self.assertIn("position_size", result)
        self.assertIn("risk_amount", result)
        self.assertIn("risk_percentage", result)
        self.assertEqual(result["risk_percentage"], 1.0)
        self.assertEqual(result["risk_amount"], 100.0)  # 1% z 10000

        # Sprawdzamy czy wielkość pozycji jest rozsądna
        self.assertTrue(0.01 <= result["position_size"] <= 100.0)
        
    def test_calculate_position_size_missing_mt5_connector(self):
        """Test obliczania wielkości pozycji bez ustawionego konektora MT5."""
        # Tworzymy nowy RiskManager bez ustawionego konektora
        risk_manager_no_connector = RiskManager(db_handler=self.db_handler)
        
        result = risk_manager_no_connector.calculate_position_size(
            symbol="EURUSD",
            entry_price=1.1000,
            stop_loss=1.0950
        )
        
        # Sprawdzamy czy otrzymujemy błąd i minimalną wielkość pozycji
        self.assertIn("error", result)
        self.assertEqual(result["position_size"], 0.01)
        self.assertEqual(result["error"], "MT5Connector nie został ustawiony")
        
    def test_calculate_position_size_invalid_price_difference(self):
        """Test obliczania wielkości pozycji z nieprawidłową różnicą cen."""
        self.mt5_connector.get_account_info.return_value = {"balance": 10000.0}
        self.mt5_connector.get_symbol_info.return_value = {
            "contract_size": 100000,
            "pip_value": 0.0001,
            "min_lot": 0.01,
            "max_lot": 100.0,
            "lot_step": 0.01
        }
        
        # Cena wejścia równa stop-loss
        result = self.risk_manager.calculate_position_size(
            symbol="EURUSD",
            entry_price=1.1000,
            stop_loss=1.1000,
            risk_percentage=1.0
        )
        
        # Sprawdzamy czy otrzymujemy błąd
        self.assertIn("error", result)
        self.assertEqual(result["position_size"], 0.01)
        self.assertEqual(result["error"], "Nieprawidłowa różnica cen")

    def test_validate_trade_idea_valid(self):
        """Test walidacji poprawnego pomysłu handlowego."""
        # Mockowanie calculate_position_size z wszystkimi wymaganymi polami
        position_size_result = {
            "position_size": 0.1,
            "risk_percentage": 1.0,
            "pips_risk": 50,
            "risk_amount": 100.0,
            "account_balance": 10000.0,
            "pip_cost": 0.1,
            "min_lot": 0.01,
            "max_lot": 100.0,
            "lot_step": 0.01
        }
        
        # Zamiast mockować całą metodę, użyjmy patcha dla konkretnej instancji
        with patch.object(self.risk_manager, 'calculate_position_size', return_value=position_size_result) as mock_calc:
            # Test dla poprawnej pozycji kupna
            result = self.risk_manager.validate_trade_idea(
                symbol="EURUSD",
                direction="buy",
                entry_price=1.1000,
                stop_loss=1.0950,
                take_profit=1.1100
            )
            
            # Sprawdzamy rezultat
            self.assertTrue(result["valid"])
            # Sprawdzamy, że stosunek zysku do ryzyka jest obecny w rezultacie
            self.assertIn("risk_reward_ratio", result)
            # Rozsądny stosunek zysku do ryzyka powinien być większy lub równy 1.0
            self.assertGreaterEqual(result["risk_reward_ratio"], 1.0)
            
    def test_validate_trade_idea_invalid_direction(self):
        """Test walidacji z niepoprawnym kierunkiem."""
        result = self.risk_manager.validate_trade_idea(
            symbol="EURUSD",
            direction="invalid",
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100
        )

        # Sprawdzamy rezultat
        self.assertFalse(result["valid"])
        self.assertIn("kierunek", result["reason"].lower())

    def test_validate_trade_idea_invalid_levels(self):
        """Test walidacji z niepoprawnymi poziomami SL/TP."""
        # Niepoprawne poziomy dla pozycji kupna (SL powyżej ceny wejścia)
        result = self.risk_manager.validate_trade_idea(
            symbol="EURUSD",
            direction="buy",
            entry_price=1.1000,
            stop_loss=1.1050,  # SL powinien być poniżej ceny wejścia dla pozycji kupna
            take_profit=1.1100
        )

        # Sprawdzamy rezultat
        self.assertFalse(result["valid"])
        self.assertIn("poziom", result["reason"].lower())

    def test_validate_trade_idea_low_risk_reward(self):
        """Test walidacji ze zbyt niskim stosunkiem zysku do ryzyka."""
        # Ustawienie poziomu, gdzie stosunek zysku do ryzyka jest mniejszy niż 1
        result = self.risk_manager.validate_trade_idea(
            symbol="EURUSD",
            direction="buy",
            entry_price=1.1000,
            stop_loss=1.0950,  # 50 pipsów ryzyka
            take_profit=1.1025  # tylko 25 pipsów potencjalnego zysku
        )

        # Sprawdzamy rezultat
        self.assertFalse(result["valid"])
        self.assertIn("stosunek zysku do ryzyka", result["reason"].lower())
        
    def test_validate_trade_idea_with_calculation_error(self):
        """Test walidacji gdy wystąpił błąd w obliczaniu wielkości pozycji."""
        # Mockowanie calculate_position_size, aby zwrócił błąd
        self.risk_manager.calculate_position_size = MagicMock(return_value={
            "position_size": 0.01,
            "error": "Testowy błąd kalkulacji"
        })
        
        result = self.risk_manager.validate_trade_idea(
            symbol="EURUSD",
            direction="buy",
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100
        )
        
        # Sprawdzamy rezultat
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "Testowy błąd kalkulacji")

    def test_check_daily_risk_limit_no_trades(self):
        """Test sprawdzania limitu dziennego ryzyka bez żadnych transakcji."""
        # Brak transakcji w bazie danych
        self.db_handler.get_trades.return_value = []
        self.mt5_connector.get_account_info.return_value = {"balance": 10000.0}

        result = self.risk_manager.check_daily_risk_limit(daily_risk_limit_pct=2.0)

        # Sprawdzamy rezultat
        self.assertFalse(result["limit_exceeded"])
        self.assertEqual(result["current_risk"], 0.0)
        self.assertEqual(result["remaining_risk"], 2.0)
        self.assertNotIn("reason", result)

    def test_check_daily_risk_limit_with_closed_trades(self):
        """Test sprawdzania limitu dziennego ryzyka z zamkniętymi transakcjami."""
        # Mockowanie danych zwracanych przez MT5Connector
        self.mt5_connector.get_account_info.return_value = {"balance": 10000.0}

        # Ustawienie dzisiejszej daty
        today = datetime.now().strftime("%Y-%m-%d")
        today_datetime = datetime.now().isoformat()

        # Symulacja dwóch zamkniętych transakcji - jedna ze stratą, jedna z zyskiem
        closed_trade_loss = {
            "status": "closed",
            "entry_time": today_datetime,
            "profit_loss": -200.0  # 2% straty
        }
        
        closed_trade_profit = {
            "status": "closed",
            "entry_time": today_datetime,
            "profit_loss": 150.0  # 1.5% zysku
        }

        # Ustawienie transakcji zwracanych przez bazę danych
        self.db_handler.get_trades.return_value = [closed_trade_loss, closed_trade_profit]

        result = self.risk_manager.check_daily_risk_limit(daily_risk_limit_pct=5.0)

        # Sprawdzamy rezultat
        # Oczekujemy, że current_risk będzie uwzględniał tylko stratę, a nie zysk
        self.assertAlmostEqual(result["current_risk"], 2.0, delta=0.1)  # 2% z powodu straty
        self.assertAlmostEqual(result["remaining_risk"], 3.0, delta=0.1)  # 5% - 2%
        self.assertFalse(result["limit_exceeded"])

    def test_check_daily_risk_limit_with_open_trades(self):
        """Test sprawdzania limitu dziennego ryzyka uwzględniający otwarte pozycje."""
        # Ustawienie poprawnego salda konta
        self.mt5_connector.get_account_info.return_value = {'balance': 10000.0}
        
        # Ustawienie dzisiejszej daty
        today_datetime = datetime.now().isoformat()
        
        # Symulacja otwartych transakcji
        open_trade_1 = {
            "status": "open",
            "entry_time": today_datetime,
            "entry_price": 1.1000,
            "stop_loss": 1.0950,  # 50 pipsów ryzyka
            "volume": 0.1  # 0.1 lota
        }
        
        # Transakcja 2: 30 pipsów ryzyka, 0.2 lota
        open_trade_2 = {
            "status": "open",
            "entry_time": today_datetime,
            "entry_price": 1.2000,
            "stop_loss": 1.1970,  # 30 pipsów ryzyka
            "volume": 0.2  # 0.2 lota
        }
        
        # Ustawienie transakcji zwracanych przez bazę danych
        self.db_handler.get_trades.return_value = [open_trade_1, open_trade_2]
        
        # Oczekiwane obliczenia (po usunięciu mnożnika 100000):
        # Transakcja 1: 50 pipsów * 0.1 lota * 0.1 USD = 0.5 USD (0.005% salda)
        # Transakcja 2: 30 pipsów * 0.2 lota * 0.1 USD = 0.6 USD (0.006% salda)
        # Łącznie: 1.1 USD (0.011% salda)
        expected_total_risk = 1.1  # USD
        expected_risk_percentage = 0.011  # %
        
        result = self.risk_manager.check_daily_risk_limit(daily_risk_limit_pct=5.0)
        
        # Sprawdzamy rezultat
        self.assertFalse(result["limit_exceeded"])  # 0.011% < 5%, więc limit nie przekroczony
        self.assertAlmostEqual(result["current_risk"], expected_risk_percentage, delta=0.001)
        self.assertAlmostEqual(result["remaining_risk"], 5.0 - expected_risk_percentage, delta=0.001)
        self.assertIn("total_risk_amount", result)
        self.assertAlmostEqual(result["total_risk_amount"], expected_total_risk, delta=0.1)

    def test_check_daily_risk_limit_mixed_trades(self):
        """Test sprawdzania limitu dziennego ryzyka z otwartymi i zamkniętymi transakcjami."""
        # Mockowanie danych
        self.mt5_connector.get_account_info.return_value = {'balance': 10000.0}
        
        # Ustawienie dzisiejszej daty
        today_datetime = datetime.now().isoformat()
        
        # Symulacja zamkniętej transakcji ze stratą
        closed_trade = {
            "status": "closed",
            "entry_time": today_datetime,
            "profit_loss": -200.0  # 2% straty
        }
        
        # Symulacja otwartej transakcji
        open_trade = {
            "status": "open",
            "entry_time": today_datetime,
            "entry_price": 1.1000,
            "stop_loss": 1.0950,  # 50 pipsów ryzyka
            "volume": 0.1  # 0.1 lota
        }
        
        # Oczekiwane obliczenia:
        # Zamknięta transakcja: 200 USD straty (2% salda)
        # Otwarta transakcja: 50 pipsów * 0.1 lota * 0.1 USD = 0.5 USD (0.005% salda)
        # Łączne ryzyko: 2% + 0.005% = 2.005% (w dolarach: 200.5 USD)
        
        # Ustawienie transakcji zwracanych przez bazę danych
        self.db_handler.get_trades.return_value = [closed_trade, open_trade]
        
        result = self.risk_manager.check_daily_risk_limit(daily_risk_limit_pct=5.0)
        
        # Sprawdzamy rezultat
        self.assertFalse(result["limit_exceeded"])  # 2.005% < 5%, więc limit nie przekroczony
        self.assertAlmostEqual(result["current_risk"], 2.005, delta=0.01)
        self.assertAlmostEqual(result["remaining_risk"], 5.0 - 2.005, delta=0.01)
        self.assertIn("total_risk_amount", result)
        self.assertAlmostEqual(result["total_risk_amount"], 200.5, delta=0.1)

    def test_check_daily_risk_limit_exceeded(self):
        """Test sprawdzania limitu dziennego ryzyka gdy limit zostaje przekroczony."""
        # Mockowanie danych
        self.mt5_connector.get_account_info.return_value = {'balance': 10000.0}
        
        # Ustawienie dzisiejszej daty
        today_datetime = datetime.now().isoformat()
        
        # Symulacja 3 zamkniętych transakcji z dużymi stratami
        closed_trades = [
            {
                "status": "closed",
                "entry_time": today_datetime,
                "profit_loss": -200.0  # 2% straty
            },
            {
                "status": "closed",
                "entry_time": today_datetime,
                "profit_loss": -300.0  # 3% straty
            },
            {
                "status": "closed",
                "entry_time": today_datetime,
                "profit_loss": -150.0  # 1.5% straty
            }
        ]
        
        # Ustawienie transakcji zwracanych przez bazę danych
        self.db_handler.get_trades.return_value = closed_trades
        
        # Oczekiwane obliczenia:
        # Łączna strata: 200 + 300 + 150 = 650 USD (6.5% salda)
        expected_total_risk = 650.0  # USD
        expected_risk_percentage = 6.5  # %
        
        result = self.risk_manager.check_daily_risk_limit(daily_risk_limit_pct=5.0)
        
        # Sprawdzamy rezultat
        self.assertTrue(result["limit_exceeded"])  # 6.5% > 5%, więc limit przekroczony
        self.assertAlmostEqual(result["current_risk"], expected_risk_percentage, delta=0.01)
        self.assertEqual(result["remaining_risk"], 0.0)  # Limit już przekroczony
        self.assertIn("total_risk_amount", result)
        self.assertAlmostEqual(result["total_risk_amount"], expected_total_risk, delta=0.1)

    def test_check_daily_risk_limit_invalid_account_balance(self):
        """Test sprawdzania limitu dziennego ryzyka gdy saldo konta jest nieprawidłowe."""
        # Mockowanie danych
        self.db_handler.get_trades.return_value = [
            {
                "status": "closed",
                "entry_time": datetime.now().isoformat(),
                "profit_loss": -200.0
            }
        ]
        
        # Ustawienie nieprawidłowego salda konta (0 lub ujemne)
        self.mt5_connector.get_account_info.return_value = {'balance': 0.0}
        
        result = self.risk_manager.check_daily_risk_limit(daily_risk_limit_pct=5.0)
        
        # Sprawdzamy rezultat
        self.assertTrue(result["limit_exceeded"])
        self.assertIn("reason", result)
        self.assertEqual(result["reason"], "Nie można pobrać salda konta")
        self.assertEqual(result["remaining_risk"], 0.0)


if __name__ == "__main__":
    unittest.main() 
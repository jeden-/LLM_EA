"""
Testy jednostkowe dla modułu OrderProcessor.
"""

import unittest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime

from Agent_Manager.order_processor import OrderProcessor
from Agent_Manager.risk_manager import RiskManager
from MT5_Connector.connector import MT5Connector
from Database.database import DatabaseHandler


class TestOrderProcessor(unittest.TestCase):
    """Testy dla klasy OrderProcessor."""

    def setUp(self):
        """Inicjalizacja przed każdym testem."""
        self.db_handler = MagicMock(spec=DatabaseHandler)
        self.mt5_connector = MagicMock(spec=MT5Connector)
        # Dodanie atrybutu send_command do mocka
        self.mt5_connector.send_command = MagicMock()
        self.risk_manager = MagicMock(spec=RiskManager)
        self.order_processor = OrderProcessor(
            db_handler=self.db_handler,
            mt5_connector=self.mt5_connector,
            risk_manager=self.risk_manager
        )

    def test_initialization(self):
        """Test inicjalizacji klasy OrderProcessor."""
        self.assertEqual(self.order_processor.magic_number, 123456)
        self.assertIsNotNone(self.order_processor.db_handler)
        self.assertIsNotNone(self.order_processor.mt5_connector)
        self.assertIsNotNone(self.order_processor.risk_manager)

    def test_process_trade_idea_missing_fields(self):
        """Test przetwarzania pomysłu handlowego z brakującymi polami."""
        # Pomysł handlowy z brakującym polem stop_loss
        trade_idea = {
            "symbol": "EURUSD",
            "direction": "buy",
            "entry_price": 1.1000,
            "take_profit": 1.1100
            # brak stop_loss
        }
        
        result = self.order_processor.process_trade_idea(trade_idea)
        
        # Sprawdzamy rezultat
        self.assertFalse(result["success"])
        self.assertIn("brak", result["error"].lower())
        self.assertIsNone(result["order"])

    def test_process_trade_idea_validation_failed(self):
        """Test przetwarzania pomysłu handlowego, który nie przechodzi walidacji."""
        # Pomysł handlowy
        trade_idea = {
            "symbol": "EURUSD",
            "direction": "buy",
            "entry_price": 1.1000,
            "stop_loss": 1.0950,
            "take_profit": 1.1100
        }
        
        # Ustawienie wyniku walidacji
        self.risk_manager.validate_trade_idea.return_value = {
            "valid": False,
            "reason": "Nieprawidłowy stosunek zysku do ryzyka"
        }
        
        result = self.order_processor.process_trade_idea(trade_idea)
        
        # Sprawdzamy rezultat
        self.assertFalse(result["success"])
        self.assertIn("stosunek", result["error"].lower())
        self.assertIsNone(result["order"])

    def test_process_trade_idea_success(self):
        """Test pomyślnego przetwarzania pomysłu handlowego."""
        # Pomysł handlowy
        trade_idea = {
            "symbol": "EURUSD",
            "direction": "buy",
            "entry_price": 1.1000,
            "stop_loss": 1.0950,
            "take_profit": 1.1100,
            "analysis_id": 123
        }
        
        # Ustawienie wyniku walidacji
        validation_result = {
            "valid": True,
            "position_size": 0.1,
            "risk_reward_ratio": 2.0,
            "risk_percentage": 1.0,
            "pips_risk": 50
        }
        self.risk_manager.validate_trade_idea.return_value = validation_result
        
        # Ustawienie wyniku zapisu do bazy danych
        self.db_handler.insert_trade_idea.return_value = 456  # ID pomysłu handlowego
        
        result = self.order_processor.process_trade_idea(trade_idea)
        
        # Sprawdzamy rezultat
        self.assertTrue(result["success"])
        self.assertIsNotNone(result["order"])
        self.assertEqual(result["order"]["symbol"], "EURUSD")
        self.assertEqual(result["order"]["order_type"], "BUY")
        self.assertEqual(result["order"]["volume"], 0.1)
        self.assertEqual(result["order"]["price"], 1.1000)
        self.assertEqual(result["order"]["stop_loss"], 1.0950)
        self.assertEqual(result["order"]["take_profit"], 1.1100)
        self.assertEqual(result["order"]["magic"], 123456)
        self.assertEqual(result["order"]["trade_id"], 456)
        self.assertEqual(result["order"]["analysis_id"], 123)

    def test_send_order_to_mt5_success(self):
        """Test pomyślnego wysłania zlecenia do MT5."""
        # Przygotowanie zlecenia
        order = {
            "action": "OPEN_POSITION",
            "symbol": "EURUSD",
            "order_type": "BUY",
            "volume": 0.1,
            "price": 1.1000,
            "stop_loss": 1.0950,
            "take_profit": 1.1100,
            "magic": 123456,
            "comment": "Test",
            "trade_id": 456
        }
        
        # Ustawienie odpowiedzi z MT5
        mt5_response = {
            "status": "SUCCESS",
            "ticket": 789,
            "open_price": 1.1002,
            "open_time": "2023-01-01T12:00:00"
        }
        self.mt5_connector.send_command.return_value = mt5_response
        
        # Ustawienie wyniku zapisu do bazy danych
        self.db_handler.insert_trade.return_value = 789  # ID transakcji
        
        result = self.order_processor.send_order_to_mt5(order)
        
        # Sprawdzamy rezultat
        self.assertTrue(result["success"])
        self.assertIn("message", result)
        self.assertEqual(result["response"], mt5_response)
        self.assertEqual(result["order"], order)
        
        # Sprawdzamy, czy zostało wywołane zapisanie transakcji do bazy danych
        self.db_handler.insert_trade.assert_called_once()

    def test_send_order_to_mt5_failed(self):
        """Test nieudanego wysłania zlecenia do MT5."""
        # Przygotowanie zlecenia
        order = {
            "action": "OPEN_POSITION",
            "symbol": "EURUSD",
            "order_type": "BUY",
            "volume": 0.1,
            "price": 1.1000,
            "stop_loss": 1.0950,
            "take_profit": 1.1100,
            "magic": 123456,
            "comment": "Test",
            "trade_id": 456
        }
        
        # Ustawienie odpowiedzi z MT5
        mt5_response = {
            "status": "ERROR",
            "message": "Niewystarczające środki"
        }
        self.mt5_connector.send_command.return_value = mt5_response
        
        result = self.order_processor.send_order_to_mt5(order)
        
        # Sprawdzamy rezultat
        self.assertFalse(result["success"])
        self.assertIn("środki", result["error"].lower())
        self.assertEqual(result["response"], mt5_response)
        self.assertEqual(result["order"], order)
        
        # Sprawdzamy, czy NIE zostało wywołane zapisanie transakcji do bazy danych
        self.db_handler.insert_trade.assert_not_called()

    def test_close_position_success(self):
        """Test pomyślnego zamknięcia pozycji."""
        # Ustawienie odpowiedzi z MT5
        mt5_response = {
            "status": "SUCCESS",
            "ticket": 789,
            "close_price": 1.1050,
            "close_time": "2023-01-01T13:00:00",
            "profit_loss": 50.0,
            "trade_id": 789
        }
        self.mt5_connector.send_command.return_value = mt5_response
        
        result = self.order_processor.close_position(ticket=789, reason="Test")
        
        # Sprawdzamy rezultat
        self.assertTrue(result["success"])
        self.assertIn("message", result)
        self.assertEqual(result["response"], mt5_response)
        
        # Sprawdzamy, czy zostało wywołane aktualizowanie transakcji w bazie danych
        self.db_handler.update_trade.assert_called_once()
        
        # Sprawdzamy czy wysłano poprawne polecenie do MT5
        command = self.mt5_connector.send_command.call_args[0][0]
        self.assertEqual(command["action"], "CLOSE_POSITION")
        self.assertEqual(command["ticket"], 789)
        self.assertEqual(command["magic"], 123456)
        self.assertIn("Test", command["comment"])

    def test_modify_position_success(self):
        """Test pomyślnej modyfikacji pozycji."""
        # Ustawienie odpowiedzi z MT5
        mt5_response = {
            "status": "SUCCESS",
            "ticket": 789
        }
        self.mt5_connector.send_command.return_value = mt5_response
        
        result = self.order_processor.modify_position(
            ticket=789,
            new_stop_loss=1.0970,
            new_take_profit=1.1150
        )
        
        # Sprawdzamy rezultat
        self.assertTrue(result["success"])
        self.assertIn("message", result)
        self.assertEqual(result["response"], mt5_response)
        
        # Sprawdzamy czy wysłano poprawne polecenie do MT5
        command = self.mt5_connector.send_command.call_args[0][0]
        self.assertEqual(command["action"], "MODIFY_POSITION")
        self.assertEqual(command["ticket"], 789)
        self.assertEqual(command["magic"], 123456)
        self.assertEqual(command["stop_loss"], 1.0970)
        self.assertEqual(command["take_profit"], 1.1150)


if __name__ == "__main__":
    unittest.main() 
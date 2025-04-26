"""
Testy jednostkowe dla modułu AgentManager.
"""

import unittest
import json
from unittest.mock import MagicMock, patch, ANY
from datetime import datetime

from Agent_Manager.agent_manager import AgentManager
from Agent_Manager.risk_manager import RiskManager
from Agent_Manager.order_processor import OrderProcessor
from LLM_Engine.llm_engine import LLMEngine
from MT5_Connector.connector import MT5Connector
from Database.database import DatabaseHandler
from Agent_Manager.coordinator import AgentCoordinator


class TestAgentManager(unittest.TestCase):
    """Testy dla klasy AgentManager."""

    def setUp(self):
        """Inicjalizacja przed każdym testem."""
        self.db_handler = MagicMock(spec=DatabaseHandler)
        self.mt5_connector = MagicMock(spec=MT5Connector)
        self.risk_manager = MagicMock(spec=RiskManager)
        self.order_processor = MagicMock(spec=OrderProcessor)
        self.llm_engine = MagicMock(spec=LLMEngine)
        
        self.agent_manager = AgentManager(
            db_handler=self.db_handler,
            mt5_connector=self.mt5_connector,
            risk_manager=self.risk_manager,
            order_processor=self.order_processor,
            llm_engine=self.llm_engine
        )

    def test_initialization(self):
        """Test inicjalizacji klasy AgentManager."""
        self.assertIsNotNone(self.agent_manager.db_handler)
        self.assertIsNotNone(self.agent_manager.mt5_connector)
        self.assertIsNotNone(self.agent_manager.risk_manager)
        self.assertIsNotNone(self.agent_manager.order_processor)
        self.assertIsNotNone(self.agent_manager.llm_engine)

    def test_analyze_market_data(self):
        """Test analizy danych rynkowych."""
        # Przygotowanie danych rynkowych
        market_data = {
            "symbol": "EURUSD",
            "timeframe": "H1",
            "data": [
                {"time": "2023-01-01T12:00:00", "open": 1.1000, "high": 1.1050, "low": 1.0950, "close": 1.1030, "volume": 1000},
                {"time": "2023-01-01T13:00:00", "open": 1.1030, "high": 1.1080, "low": 1.1020, "close": 1.1070, "volume": 1200}
            ]
        }
        
        # Ustawienie odpowiedzi z LLM
        llm_response = {
            "analysis": {
                "trend": "upward",
                "sentiment": "bullish",
                "key_levels": [1.1000, 1.1100],
                "trading_signals": ["golden_cross", "support_test"]
            },
            "trade_idea": {
                "symbol": "EURUSD",
                "direction": "buy",
                "entry_price": 1.1070,
                "stop_loss": 1.1000,
                "take_profit": 1.1150,
                "confidence": 0.8,
                "reason": "Trend wzrostowy, test ważnego poziomu wsparcia"
            }
        }
        self.llm_engine.analyze_market_data.return_value = llm_response
        
        # Ustawienie odpowiedzi z RiskManager
        validation_result = {
            "valid": True,
            "position_size": 0.1,
            "risk_reward_ratio": 2.0,
            "risk_percentage": 1.0,
            "pips_risk": 70
        }
        self.risk_manager.validate_trade_idea.return_value = validation_result
        
        # Ustawienie odpowiedzi z OrderProcessor
        processing_result = {
            "success": True,
            "order": {
                "symbol": "EURUSD",
                "order_type": "BUY",
                "volume": 0.1,
                "price": 1.1070,
                "stop_loss": 1.1000,
                "take_profit": 1.1150,
                "magic": 123456,
                "trade_id": 456
            },
            "message": "Zlecenie pomyślnie przetworzone"
        }
        self.order_processor.process_trade_idea.return_value = processing_result
        
        # Wywołanie funkcji analizy danych rynkowych
        result = self.agent_manager.analyze_market_data(market_data)
        
        # Sprawdzamy rezultat
        self.assertTrue(result["success"])
        self.assertEqual(result["analysis"], llm_response["analysis"])
        self.assertEqual(result["trade_idea"], llm_response["trade_idea"])
        self.assertEqual(result["order"], processing_result["order"])
        
        # Sprawdzamy czy zostały wywołane odpowiednie metody
        self.llm_engine.analyze_market_data.assert_called_once_with(market_data)
        self.risk_manager.validate_trade_idea.assert_called_once()
        self.order_processor.process_trade_idea.assert_called_once()
        
        # Sprawdzamy czy zostało wywołane zapisanie analizy do bazy danych
        self.db_handler.insert_analysis.assert_called_once()

    def test_analyze_market_data_no_trade_idea(self):
        """Test analizy danych rynkowych bez pomysłu handlowego."""
        # Przygotowanie danych rynkowych
        market_data = {
            "symbol": "EURUSD",
            "timeframe": "H1",
            "data": [
                {"time": "2023-01-01T12:00:00", "open": 1.1000, "high": 1.1050, "low": 1.0950, "close": 1.1030, "volume": 1000},
                {"time": "2023-01-01T13:00:00", "open": 1.1030, "high": 1.1080, "low": 1.1020, "close": 1.1070, "volume": 1200}
            ]
        }
        
        # Ustawienie odpowiedzi z LLM (bez trade_idea)
        llm_response = {
            "analysis": {
                "trend": "sideways",
                "sentiment": "neutral",
                "key_levels": [1.1000, 1.1100],
                "trading_signals": []
            }
        }
        self.llm_engine.analyze_market_data.return_value = llm_response
        
        # Wywołanie funkcji analizy danych rynkowych
        result = self.agent_manager.analyze_market_data(market_data)
        
        # Sprawdzamy rezultat
        self.assertTrue(result["success"])
        self.assertEqual(result["analysis"], llm_response["analysis"])
        self.assertIsNone(result.get("trade_idea"))
        self.assertIsNone(result.get("order"))
        
        # Sprawdzamy czy zostały wywołane odpowiednie metody
        self.llm_engine.analyze_market_data.assert_called_once_with(market_data)
        self.risk_manager.validate_trade_idea.assert_not_called()
        self.order_processor.process_trade_idea.assert_not_called()
        
        # Sprawdzamy czy zostało wywołane zapisanie analizy do bazy danych
        self.db_handler.insert_analysis.assert_called_once()

    def test_analyze_market_data_invalid_trade_idea(self):
        """Test analizy danych rynkowych z nieprawidłowym pomysłem handlowym."""
        # Przygotowanie danych rynkowych
        market_data = {
            "symbol": "EURUSD",
            "timeframe": "H1",
            "data": [
                {"time": "2023-01-01T12:00:00", "open": 1.1000, "high": 1.1050, "low": 1.0950, "close": 1.1030, "volume": 1000},
                {"time": "2023-01-01T13:00:00", "open": 1.1030, "high": 1.1080, "low": 1.1020, "close": 1.1070, "volume": 1200}
            ]
        }
        
        # Ustawienie odpowiedzi z LLM
        llm_response = {
            "analysis": {
                "trend": "upward",
                "sentiment": "bullish",
                "key_levels": [1.1000, 1.1100],
                "trading_signals": ["golden_cross", "support_test"]
            },
            "trade_idea": {
                "symbol": "EURUSD",
                "direction": "buy",
                "entry_price": 1.1070,
                "stop_loss": 1.1000,
                "take_profit": 1.1150,
                "confidence": 0.8,
                "reason": "Trend wzrostowy, test ważnego poziomu wsparcia"
            }
        }
        self.llm_engine.analyze_market_data.return_value = llm_response
        
        # Ustawienie odpowiedzi z RiskManager
        validation_result = {
            "valid": False,
            "reason": "Nieprawidłowy stosunek zysku do ryzyka"
        }
        self.risk_manager.validate_trade_idea.return_value = validation_result
        
        # Wywołanie funkcji analizy danych rynkowych
        result = self.agent_manager.analyze_market_data(market_data)
        
        # Sprawdzamy rezultat
        self.assertTrue(result["success"])
        self.assertEqual(result["analysis"], llm_response["analysis"])
        self.assertEqual(result["trade_idea"], llm_response["trade_idea"])
        self.assertIn("validation", result)
        self.assertFalse(result["validation"]["valid"])
        self.assertIsNone(result.get("order"))
        
        # Sprawdzamy czy zostały wywołane odpowiednie metody
        self.llm_engine.analyze_market_data.assert_called_once_with(market_data)
        self.risk_manager.validate_trade_idea.assert_called_once()
        self.order_processor.process_trade_idea.assert_not_called()
        
        # Sprawdzamy czy zostało wywołane zapisanie analizy do bazy danych
        self.db_handler.insert_analysis.assert_called_once()

    def test_manual_trade_idea_processing(self):
        """Test przetwarzania ręcznie wprowadzonego pomysłu handlowego."""
        # Przygotowanie pomysłu handlowego
        trade_idea = {
            "symbol": "EURUSD",
            "direction": "buy",
            "entry_price": 1.1070,
            "stop_loss": 1.1000,
            "take_profit": 1.1150,
            "confidence": 0.8,
            "reason": "Trend wzrostowy, test ważnego poziomu wsparcia"
        }
        
        # Ustawienie odpowiedzi z OrderProcessor
        processing_result = {
            "success": True,
            "order": {
                "symbol": "EURUSD",
                "order_type": "BUY",
                "volume": 0.1,
                "price": 1.1070,
                "stop_loss": 1.1000,
                "take_profit": 1.1150,
                "magic": 123456,
                "trade_id": 456
            },
            "message": "Zlecenie pomyślnie przetworzone"
        }
        self.order_processor.process_trade_idea.return_value = processing_result
        
        # Wywołanie funkcji przetwarzania ręcznego pomysłu handlowego
        result = self.agent_manager.process_manual_trade_idea(trade_idea)
        
        # Sprawdzamy rezultat
        self.assertTrue(result["success"])
        self.assertEqual(result["trade_idea"], trade_idea)
        self.assertEqual(result["order"], processing_result["order"])
        
        # Sprawdzamy czy zostały wywołane odpowiednie metody
        self.order_processor.process_trade_idea.assert_called_once_with(trade_idea)

    def test_get_market_data(self):
        """Test pobierania danych rynkowych."""
        # Ustawienie parametrów
        symbol = "EURUSD"
        timeframe = "H1"
        bars_count = 100
        
        # Ustawienie odpowiedzi z MT5
        mt5_response = {
            "status": "SUCCESS",
            "data": [
                {"time": "2023-01-01T12:00:00", "open": 1.1000, "high": 1.1050, "low": 1.0950, "close": 1.1030, "volume": 1000},
                {"time": "2023-01-01T13:00:00", "open": 1.1030, "high": 1.1080, "low": 1.1020, "close": 1.1070, "volume": 1200}
            ]
        }
        self.mt5_connector.send_command.return_value = mt5_response
        
        # Wywołanie funkcji pobierania danych rynkowych
        result = self.agent_manager.get_market_data(symbol, timeframe, bars_count)
        
        # Sprawdzamy rezultat
        self.assertTrue(result["success"])
        self.assertEqual(result["data"], mt5_response["data"])
        
        # Sprawdzamy czy zostało wysłane poprawne polecenie do MT5
        command = self.mt5_connector.send_command.call_args[0][0]
        self.assertEqual(command["action"], "GET_CANDLES")
        self.assertEqual(command["symbol"], "EURUSD")
        self.assertEqual(command["timeframe"], "H1")
        self.assertEqual(command["count"], 100)

    def test_get_open_positions(self):
        """Test pobierania otwartych pozycji."""
        # Ustawienie odpowiedzi z MT5
        mt5_response = {
            "status": "SUCCESS",
            "positions": [
                {
                    "ticket": 789,
                    "symbol": "EURUSD",
                    "type": "BUY",
                    "volume": 0.1,
                    "open_price": 1.1070,
                    "stop_loss": 1.1000,
                    "take_profit": 1.1150,
                    "profit": 20.0,
                    "open_time": "2023-01-01T12:00:00",
                    "magic": 123456
                },
                {
                    "ticket": 790,
                    "symbol": "GBPUSD",
                    "type": "SELL",
                    "volume": 0.2,
                    "open_price": 1.2500,
                    "stop_loss": 1.2580,
                    "take_profit": 1.2400,
                    "profit": -15.0,
                    "open_time": "2023-01-01T13:00:00",
                    "magic": 123456
                }
            ]
        }
        self.mt5_connector.send_command.return_value = mt5_response
        
        # Wywołanie funkcji pobierania otwartych pozycji
        result = self.agent_manager.get_open_positions()
        
        # Sprawdzamy rezultat
        self.assertTrue(result["success"])
        self.assertEqual(len(result["positions"]), 2)
        self.assertEqual(result["positions"], mt5_response["positions"])
        
        # Sprawdzamy czy zostało wysłane poprawne polecenie do MT5
        command = self.mt5_connector.send_command.call_args[0][0]
        self.assertEqual(command["action"], "GET_POSITIONS")
        self.assertEqual(command["magic"], 123456)

    def test_close_position(self):
        """Test zamykania pozycji."""
        # Ustawienie parametrów
        ticket = 789
        reason = "Realizacja zysku"
        
        # Ustawienie odpowiedzi z OrderProcessor
        order_processor_response = {
            "success": True,
            "response": {
                "status": "SUCCESS",
                "ticket": 789,
                "close_price": 1.1090,
                "close_time": "2023-01-01T14:00:00",
                "profit_loss": 20.0
            },
            "message": "Pozycja zamknięta pomyślnie"
        }
        self.order_processor.close_position.return_value = order_processor_response
        
        # Wywołanie funkcji zamykania pozycji
        result = self.agent_manager.close_position(ticket, reason)
        
        # Sprawdzamy rezultat
        self.assertTrue(result["success"])
        self.assertEqual(result["response"], order_processor_response["response"])
        
        # Sprawdzamy czy zostało wywołane zamknięcie pozycji przez OrderProcessor
        self.order_processor.close_position.assert_called_once_with(ticket, reason)

    def test_modify_position(self):
        """Test modyfikacji pozycji."""
        # Ustawienie parametrów
        ticket = 789
        new_stop_loss = 1.1030
        new_take_profit = 1.1200
        
        # Ustawienie odpowiedzi z OrderProcessor
        order_processor_response = {
            "success": True,
            "response": {
                "status": "SUCCESS",
                "ticket": 789
            },
            "message": "Pozycja zmodyfikowana pomyślnie"
        }
        self.order_processor.modify_position.return_value = order_processor_response
        
        # Wywołanie funkcji modyfikacji pozycji
        result = self.agent_manager.modify_position(ticket, new_stop_loss, new_take_profit)
        
        # Sprawdzamy rezultat
        self.assertTrue(result["success"])
        self.assertEqual(result["response"], order_processor_response["response"])
        
        # Sprawdzamy czy zostało wywołane modyfikowanie pozycji przez OrderProcessor
        self.order_processor.modify_position.assert_called_once_with(ticket, new_stop_loss, new_take_profit)

    def test_process_account_update(self):
        """Test przetwarzania aktualizacji konta."""
        # Przygotowanie danych konta
        account_info = {
            "balance": 10000.0,
            "equity": 10050.0,
            "margin": 200.0,
            "free_margin": 9850.0,
            "margin_level": 5025.0,
            "leverage": 100,
            "currency": "USD"
        }
        
        # Wywołanie funkcji przetwarzania aktualizacji konta
        result = self.agent_manager.process_account_update(account_info)
        
        # Sprawdzamy rezultat
        self.assertTrue(result["success"])
        self.assertEqual(result["account_info"], account_info)
        
        # Sprawdzamy czy zostało wywołane zapisanie informacji o koncie do bazy danych
        self.db_handler.update_account_info.assert_called_once()
        
        # Sprawdzamy czy została wywołana aktualizacja limitu ryzyka
        self.risk_manager.update_account_balance.assert_called_once_with(account_info["balance"])


if __name__ == "__main__":
    unittest.main() 
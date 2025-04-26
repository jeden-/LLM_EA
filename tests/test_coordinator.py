"""
Testy dla klasy AgentCoordinator w module Agent_Manager.

Ten moduł zawiera testy jednostkowe dla klasy AgentCoordinator,
która jest odpowiedzialna za koordynację wszystkich komponentów
systemu handlowego LLM.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import json
from datetime import datetime, timedelta
import pandas as pd

# Dodaj ścieżkę główną projektu do sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Agent_Manager.coordinator import AgentCoordinator
from MT5_Connector.connector import MT5Connector
from LLM_Engine.llm_engine import LLMEngine
from Database.database import DatabaseHandler
from Agent_Manager.risk_manager import RiskManager
from Agent_Manager.order_processor import OrderProcessor


class TestAgentCoordinator(unittest.TestCase):
    """Testy jednostkowe dla klasy AgentCoordinator."""

    def setUp(self):
        """Konfiguracja środowiska przed każdym testem."""
        # Mockowanie komponentów
        self.mock_mt5_connector = MagicMock(spec=MT5Connector)
        self.mock_llm_engine = MagicMock(spec=LLMEngine)
        self.mock_db_handler = MagicMock(spec=DatabaseHandler)
        
        # Konfiguracja odpowiedzi z MT5
        self.mock_mt5_connector.get_account_info.return_value = {
            'login': 12345,
            'balance': 10000.0,
            'equity': 10050.0,
            'margin': 500.0,
            'free_margin': 9550.0,
            'margin_level': 2010.0,
            'leverage': 100
        }
        
        self.mock_mt5_connector.initialize.return_value = True
        
        # Przygotowanie danych testowych dla analizy rynku
        self.mock_analysis_result = {
            'analysis': {
                'trend': 'bullish',
                'strength': 7,
                'support_levels': [1.1000, 1.0950],
                'resistance_levels': [1.1100, 1.1150]
            },
            'recommendation': 'BUY',
            'entry_price': 1.1050,
            'stop_loss': 1.1000,
            'take_profit': 1.1150,
            'risk_reward_ratio': 2.0,
            'explanation': 'Silny trend wzrostowy z wyraźnym wsparciem.'
        }
        
        self.mock_llm_engine.analyze_market.return_value = self.mock_analysis_result
        
        # Tworzenie instancji koordynatora z mockami
        self.coordinator = AgentCoordinator(
            mt5_connector=self.mock_mt5_connector,
            llm_engine=self.mock_llm_engine,
            db_handler=self.mock_db_handler
        )
        
        # Mockowanie risk_manager i order_processor
        self.coordinator.risk_manager = MagicMock(spec=RiskManager)
        self.coordinator.order_processor = MagicMock(spec=OrderProcessor)

    def test_load_config_with_valid_file(self):
        """Test ładowania konfiguracji z poprawnego pliku."""
        test_config = {
            "symbols": ["EURUSD", "GBPUSD"],
            "timeframes": [5, 15, 60],
            "analysis_interval_seconds": 600,
            "max_risk_per_trade_pct": 1.5,
            "daily_risk_limit_pct": 4.0
        }
        
        # Mockowanie open do odczytania pliku konfiguracyjnego
        with patch("builtins.open", mock_open(read_data=json.dumps(test_config))), \
             patch("os.path.exists", return_value=True):
            
            coordinator = AgentCoordinator(config_path="fake_config.json")
            
            # Sprawdzenie czy konfiguracja została poprawnie załadowana
            self.assertEqual(coordinator.symbols, ["EURUSD", "GBPUSD"])
            self.assertEqual(coordinator.timeframes, [5, 15, 60])
            self.assertEqual(coordinator.analysis_interval, 600)
            self.assertEqual(coordinator.config.get("max_risk_per_trade_pct"), 1.5)
            self.assertEqual(coordinator.config.get("daily_risk_limit_pct"), 4.0)

    def test_load_config_with_invalid_file(self):
        """Test ładowania konfiguracji z nieistniejącego pliku."""
        # Mockowanie sprawdzania istnienia pliku
        with patch("os.path.exists", return_value=False):
            coordinator = AgentCoordinator(config_path="nonexistent_config.json")
            
            # Sprawdzenie czy użyto konfiguracji domyślnej
            self.assertEqual(coordinator.symbols, ["EURUSD", "GBPUSD", "USDJPY"])
            self.assertEqual(coordinator.analysis_interval, 300)

    def test_load_config_with_invalid_json(self):
        """Test ładowania konfiguracji z pliku zawierającym nieprawidłowy JSON."""
        # Mockowanie open do odczytania pliku z nieprawidłowym JSON
        with patch("builtins.open", mock_open(read_data="invalid JSON content")), \
             patch("os.path.exists", return_value=True), \
             patch("Agent_Manager.coordinator.logger") as mock_logger:
            
            coordinator = AgentCoordinator(config_path="invalid_json.json")
            
            # Sprawdzenie czy użyto konfiguracji domyślnej
            self.assertEqual(coordinator.symbols, ["EURUSD", "GBPUSD", "USDJPY"])
            self.assertEqual(coordinator.analysis_interval, 300)
            
            # Sprawdzenie czy błąd został zalogowany
            mock_logger.error.assert_called_once()

    def test_initialize_success(self):
        """Test udanej inicjalizacji wszystkich komponentów."""
        self.mock_db_handler.init_database.return_value = True
        
        result = self.coordinator.initialize()
        
        # Sprawdzenie czy komponenty zostały zainicjalizowane
        self.mock_db_handler.init_database.assert_called_once()
        self.mock_mt5_connector.initialize.assert_called_once()
        self.mock_mt5_connector.get_account_info.assert_called_once()
        
        # Sprawdzenie wyniku inicjalizacji
        self.assertTrue(result)
        
        # Sprawdzenie logowania sukcesu
        self.mock_db_handler.insert_log.assert_called_with(
            level="INFO",
            module="AgentCoordinator",
            message=f"System zainicjalizowany. Konto: 12345, Saldo: 10000.0"
        )

    def test_initialize_db_failure(self):
        """Test inicjalizacji z niepowodzeniem bazy danych."""
        self.mock_db_handler.init_database.return_value = False
        
        result = self.coordinator.initialize()
        
        # Sprawdzenie czy komponenty zostały zainicjalizowane
        self.mock_db_handler.init_database.assert_called_once()
        
        # Sprawdzenie wyniku inicjalizacji
        self.assertFalse(result)
        
        # Sprawdzenie że pozostałe komponenty nie były inicjalizowane
        self.mock_mt5_connector.initialize.assert_not_called()

    def test_initialize_mt5_failure(self):
        """Test inicjalizacji z niepowodzeniem konektora MT5."""
        self.mock_db_handler.init_database.return_value = True
        self.mock_mt5_connector.initialize.return_value = False
        
        result = self.coordinator.initialize()
        
        # Sprawdzenie czy komponenty zostały zainicjalizowane
        self.mock_db_handler.init_database.assert_called_once()
        self.mock_mt5_connector.initialize.assert_called_once()
        
        # Sprawdzenie wyniku inicjalizacji
        self.assertFalse(result)
        
        # Sprawdzenie że pozostałe komponenty nie były inicjalizowane
        self.mock_mt5_connector.get_account_info.assert_not_called()

    def test_shutdown(self):
        """Test poprawnego wyłączenia systemu."""
        self.coordinator.shutdown()
        
        # Sprawdzenie czy komponenty zostały poprawnie zamknięte
        self.mock_mt5_connector.shutdown.assert_called_once()
        
        # Sprawdzenie logowania wyłączenia
        self.mock_db_handler.insert_log.assert_called_with(
            level="INFO",
            module="AgentCoordinator",
            message="System został wyłączony"
        )

    def test_analyze_market_success(self):
        """Test udanej analizy rynku."""
        # Przygotowanie danych testowych
        symbol = "EURUSD"
        timeframe = 60
        
        # Przygotowanie danych świec
        test_df = pd.DataFrame({
            'time': pd.date_range(start='2023-01-01', periods=100, freq='H'),
            'open': [1.10 + i*0.0001 for i in range(100)],
            'high': [1.11 + i*0.0001 for i in range(100)],
            'low': [1.09 + i*0.0001 for i in range(100)],
            'close': [1.105 + i*0.0001 for i in range(100)],
            'volume': [1000 + i for i in range(100)],
            'sma_50': [1.12 + i*0.0001 for i in range(100)],
            'ema_20': [1.11 + i*0.0001 for i in range(100)],
            'rsi': [60 + i*0.1 for i in range(100)],
            'macd': [0.001 + i*0.0001 for i in range(100)],
            'macd_signal': [0.0005 + i*0.0001 for i in range(100)],
            'bollinger_upper': [1.13 + i*0.0001 for i in range(100)],
            'bollinger_middle': [1.115 + i*0.0001 for i in range(100)],
            'bollinger_lower': [1.10 + i*0.0001 for i in range(100)],
            'atr': [0.001 + i*0.0001 for i in range(100)],
            'vwap': [1.11 + i*0.0001 for i in range(100)]
        })
        
        self.mock_mt5_connector.get_candles.return_value = test_df
        
        # Wykonanie analizy rynku
        result = self.coordinator.analyze_market(symbol, timeframe)
        
        # Sprawdzenie wywołania metod
        self.mock_mt5_connector.get_candles.assert_called_once_with(
            symbol=symbol,
            timeframe=timeframe,
            count=100,
            include_current=True,
            add_indicators=True,
            add_patterns=True
        )
        
        # Sprawdzenie czy LLM został użyty do analizy
        self.mock_llm_engine.analyze_market.assert_called_once()
        
        # Sprawdzenie wyniku analizy
        self.assertEqual(result, self.mock_analysis_result)
        
        # Sprawdzenie zapisu w bazie danych
        self.mock_db_handler.insert_market_analysis.assert_called_once()

    def test_analyze_market_no_data(self):
        """Test analizy rynku gdy nie można pobrać danych."""
        # Przygotowanie pustego DataFrame jako wyniku
        self.mock_mt5_connector.get_candles.return_value = pd.DataFrame()
        
        # Wykonanie analizy rynku
        result = self.coordinator.analyze_market("EURUSD", 60)
        
        # Sprawdzenie czy pobrano dane
        self.mock_mt5_connector.get_candles.assert_called_once()
        
        # Sprawdzenie wyniku (brak danych)
        self.assertIsNone(result)
        
        # Sprawdzenie że LLM nie został wywołany
        self.mock_llm_engine.analyze_market.assert_not_called()

    def test_process_analysis_result_with_trade_idea(self):
        """Test przetwarzania wyniku analizy z pomysłem handlowym."""
        # Przygotowanie danych testowych
        analysis_result = {
            'analysis': {
                'trend': 'bullish',
                'strength': 7,
                'support_levels': [1.1000, 1.0950],
                'resistance_levels': [1.1100, 1.1150]
            },
            'trade_idea': {
                'action': 'ENTER',
                'direction': 'BUY',
                'entry_price': 1.1050,
                'stop_loss': 1.1000,
                'take_profit': 1.1150,
                'risk_reward_ratio': 2.0,
                'symbol': 'EURUSD'
            }
        }
        
        # Mockowanie order_processor
        order_processing_result = {
            'success': True,
            'order': {
                'symbol': 'EURUSD',
                'type': 'BUY',
                'volume': 0.1,
                'price': 1.1050,
                'sl': 1.1000,
                'tp': 1.1150
            }
        }
        self.coordinator.order_processor.process_trade_idea.return_value = order_processing_result
        
        # Wykonanie przetwarzania analizy
        result = self.coordinator.process_analysis_result(analysis_result)
        
        # Sprawdzenie przetwarzania pomysłu handlowego
        self.coordinator.order_processor.process_trade_idea.assert_called_once_with(analysis_result['trade_idea'])
        
        # Sprawdzenie wyniku
        self.assertTrue(result['success'])
        self.assertEqual(result['action'], 'ENTER_PREPARED')

    def test_process_analysis_result_no_trade_idea(self):
        """Test przetwarzania wyniku analizy bez pomysłu handlowego."""
        # Przygotowanie danych testowych bez pomysłu handlowego
        analysis_result = {
            'analysis': {
                'trend': 'neutral',
                'strength': 3,
                'support_levels': [1.1000, 1.0950],
                'resistance_levels': [1.1100, 1.1150]
            }
        }
        
        # Wykonanie przetwarzania analizy
        result = self.coordinator.process_analysis_result(analysis_result)
        
        # Sprawdzenie że order_processor nie został użyty
        self.coordinator.order_processor.process_trade_idea.assert_not_called()
        
        # Sprawdzenie wyniku
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], 'Analiza nie zawiera pomysłu handlowego')
        self.assertEqual(result['action'], 'NONE')

    def test_process_analysis_result_wait_action(self):
        """Test przetwarzania wyniku analizy z akcją WAIT."""
        # Przygotowanie danych testowych z pomysłem handlowym i akcją WAIT
        analysis_result = {
            'analysis': {
                'trend': 'neutral',
                'strength': 3,
                'support_levels': [1.1000, 1.0950],
                'resistance_levels': [1.1100, 1.1150]
            },
            'trade_idea': {
                'action': 'WAIT',
                'reason': 'Rynek w konsolidacji, brak wyraźnego kierunku'
            }
        }
        
        # Wykonanie przetwarzania analizy
        result = self.coordinator.process_analysis_result(analysis_result)
        
        # Sprawdzenie że order_processor nie został użyty
        self.coordinator.order_processor.process_trade_idea.assert_not_called()
        
        # Sprawdzenie wyniku
        self.assertTrue(result['success'])
        self.assertEqual(result['action'], 'WAIT')
        self.assertEqual(result['reason'], 'Rynek w konsolidacji, brak wyraźnego kierunku')

    def test_process_analysis_result_exit_action(self):
        """Test przetwarzania wyniku analizy z akcją EXIT."""
        # Przygotowanie danych testowych z pomysłem handlowym i akcją EXIT
        analysis_result = {
            'analysis': {
                'trend': 'bearish',
                'strength': 6,
                'support_levels': [1.1000, 1.0950],
                'resistance_levels': [1.1100, 1.1150]
            },
            'trade_idea': {
                'action': 'EXIT',
                'ticket': 123456,
                'reason': 'Zmiana trendu rynkowego na niedźwiedzi'
            }
        }
        
        # Wykonanie przetwarzania analizy
        result = self.coordinator.process_analysis_result(analysis_result)
        
        # Sprawdzenie że order_processor nie został użyty do automatycznego zamknięcia pozycji
        self.coordinator.order_processor.close_position.assert_not_called()
        
        # Sprawdzenie wyniku
        self.assertTrue(result['success'])
        self.assertEqual(result['action'], 'EXIT_PREPARED')
        self.assertEqual(result['ticket'], 123456)

    def test_generate_trade_idea_force_analysis(self):
        """Test generowania pomysłu handlowego z wymuszeniem analizy."""
        # Mockowanie metod wykorzystywanych przez generate_trade_idea
        symbol = "EURUSD"
        timeframe = "H1"
        
        # Mockowanie analizy rynku
        analysis_result = {
            'analysis': {
                'trend': 'bullish',
                'strength': 7,
                'support_levels': [1.1000, 1.0950],
                'resistance_levels': [1.1100, 1.1150]
            },
            'recommendation': 'BUY',
            'direction': 'BUY',
            'entry_price': 1.1050,
            'stop_loss': 1.1000,
            'take_profit': 1.1150,
            'risk_reward_ratio': 2.0,
            'explanation': 'Silny trend wzrostowy z wyraźnym wsparciem.'
        }
        
        # Ustawienie zwracanej wartości dla analyze_market
        original_analyze_market = self.coordinator.analyze_market
        self.coordinator.analyze_market = MagicMock(return_value=analysis_result)
        
        # Mockowanie zapisu analizy w bazie danych
        self.mock_db_handler.insert_market_analysis.return_value = 123
        
        # Wykonanie generowania pomysłu handlowego
        result = self.coordinator.generate_trade_idea(symbol, timeframe, force_analysis=True)
        
        # Sprawdzenie wywołania analizy rynku
        self.coordinator.analyze_market.assert_called_once_with(symbol, 60, force=True)
        
        # Sprawdzenie zapisu analizy w bazie danych
        self.mock_db_handler.insert_market_analysis.assert_called_once()
        
        # Sprawdzenie wyniku
        self.assertTrue('symbol' in result)
        self.assertEqual(result['symbol'], symbol)
        
        # Przywracamy oryginalną metodę
        self.coordinator.analyze_market = original_analyze_market

    def test_run_market_analysis_for_all_symbols(self):
        """Test uruchamiania analizy rynku dla wszystkich symboli."""
        # Mockowanie analizy rynku
        analysis_result = {
            'analysis': {
                'trend': 'bullish',
                'strength': 7,
                'support_levels': [1.1000, 1.0950],
                'resistance_levels': [1.1100, 1.1150]
            },
            'recommendation': 'BUY',
            'entry_price': 1.1050,
            'stop_loss': 1.1000,
            'take_profit': 1.1150,
            'risk_reward_ratio': 2.0,
            'explanation': 'Silny trend wzrostowy z wyraźnym wsparciem.'
        }
        
        # Mockowanie metod używanych przez run_market_analysis
        original_analyze_market = self.coordinator.analyze_market
        self.coordinator.analyze_market = MagicMock(return_value=analysis_result)
        
        original_process_analysis_result = self.coordinator.process_analysis_result
        processing_result = {
            'success': True,
            'message': 'Analiza przetworzona pomyślnie',
            'action': 'NONE'
        }
        self.coordinator.process_analysis_result = MagicMock(return_value=processing_result)
        
        # Ustawienie listy symboli i timeframe'ów
        self.coordinator.symbols = ["EURUSD", "GBPUSD"]
        self.coordinator.timeframes = [60, 240]
        
        # Wykonanie analizy rynku
        results = self.coordinator.run_market_analysis()
        
        # Sprawdzenie liczby wywołań analizy rynku (2 symbole x 2 timeframe'y = 4 wywołania)
        self.assertEqual(self.coordinator.analyze_market.call_count, 4)
        
        # Sprawdzenie liczby wywołań przetwarzania wyników analizy
        self.assertEqual(self.coordinator.process_analysis_result.call_count, 4)
        
        # Sprawdzenie wyników
        self.assertEqual(len(results), 4)
        
        # Przywracamy oryginalne metody
        self.coordinator.analyze_market = original_analyze_market
        self.coordinator.process_analysis_result = original_process_analysis_result

    def test_execute_trade_idea_success(self):
        """Test udanego wykonania pomysłu handlowego."""
        # Mockowanie pobrania pomysłu handlowego
        mock_trade_idea = {
            'id': 123,
            'symbol': 'EURUSD',
            'direction': 'BUY',
            'entry_price': 1.1050,
            'stop_loss': 1.1000,
            'take_profit': 1.1150,
            'status': 'PENDING'
        }
        self.mock_db_handler.get_trade_idea.return_value = mock_trade_idea
        
        # Mockowanie walidacji pomysłu handlowego
        self.coordinator.risk_manager.validate_trade_idea.return_value = {
            'valid': True
        }
        
        # Mockowanie wykonania pomysłu handlowego
        order_result = {
            'success': True,
            'order_id': 456,
            'message': 'Zlecenie wykonane pomyślnie'
        }
        self.coordinator.order_processor.execute_trade_idea.return_value = order_result
        
        # Wykonanie pomysłu handlowego
        result = self.coordinator.execute_trade_idea(123)
        
        # Sprawdzenie pobrania pomysłu handlowego
        self.mock_db_handler.get_trade_idea.assert_called_once_with(123)
        
        # Sprawdzenie walidacji pomysłu handlowego
        self.coordinator.risk_manager.validate_trade_idea.assert_called_once()
        
        # Sprawdzenie wykonania pomysłu handlowego
        self.coordinator.order_processor.execute_trade_idea.assert_called_once_with(123)
        
        # Sprawdzenie aktualizacji statusu pomysłu handlowego
        self.mock_db_handler.update_trade_idea.assert_called_once()
        
        # Sprawdzenie wyniku
        self.assertTrue(result['success'])

    def test_execute_trade_idea_not_found(self):
        """Test wykonania pomysłu handlowego, który nie istnieje."""
        # Mockowanie nieudanego pobrania pomysłu handlowego
        self.mock_db_handler.get_trade_idea.return_value = None
        
        # Wykonanie pomysłu handlowego
        result = self.coordinator.execute_trade_idea(999)
        
        # Sprawdzenie pobrania pomysłu handlowego
        self.mock_db_handler.get_trade_idea.assert_called_once_with(999)
        
        # Sprawdzenie że walidacja pomysłu handlowego nie została wywołana
        self.coordinator.risk_manager.validate_trade_idea.assert_not_called()
        
        # Sprawdzenie że wykonanie pomysłu handlowego nie zostało wywołane
        self.coordinator.order_processor.execute_trade_idea.assert_not_called()
        
        # Sprawdzenie wyniku
        self.assertFalse(result['success'])
        self.assertTrue('error' in result)

    def test_start_stop_monitoring(self):
        """Test uruchamiania i zatrzymywania monitorowania rynku."""
        # Mockowanie klasy Thread
        with patch('threading.Thread') as mock_thread:
            # Mockowanie obiektu Thread, który może być join'owany
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance
            
            # Testowanie na żywym wątku, który nie jest aktywny
            mock_thread_instance.is_alive.return_value = False
            
            # Uruchomienie monitorowania
            result = self.coordinator.start_monitoring()
            
            # Sprawdzenie wyniku
            self.assertTrue(result)
            self.assertTrue(self.coordinator.running)
            
            # Sprawdzenie utworzenia wątku
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()
            
            # Ustawienie stanu wątku jako aktywny
            mock_thread_instance.is_alive.return_value = True
            
            # Po join należy zmienić stan wątku na nieaktywny
            def join_side_effect(timeout=None):
                mock_thread_instance.is_alive.return_value = False
            
            mock_thread_instance.join.side_effect = join_side_effect
            
            # Zatrzymanie monitorowania
            result = self.coordinator.stop_monitoring()
            
            # Sprawdzenie wyniku
            self.assertTrue(result)
            self.assertFalse(self.coordinator.running)
            
            # Sprawdzenie wywołania join
            mock_thread_instance.join.assert_called_once_with(timeout=5)

    def test_process_analysis_result_unknown_action(self):
        """Test przetwarzania wyniku analizy z nieznaną akcją."""
        # Przygotowanie danych testowych z pomysłem handlowym i nieznaną akcją
        analysis_result = {
            'analysis': {
                'trend': 'neutral',
                'strength': 3,
                'support_levels': [1.1000, 1.0950],
                'resistance_levels': [1.1100, 1.1150]
            },
            'trade_idea': {
                'action': 'UNKNOWN_ACTION',
                'symbol': 'EURUSD',
                'direction': 'BUY'
            }
        }
        
        # Wykonanie przetwarzania analizy
        result = self.coordinator.process_analysis_result(analysis_result)
        
        # Sprawdzenie że order_processor nie został użyty
        self.coordinator.order_processor.process_trade_idea.assert_not_called()
        
        # Sprawdzenie wyniku
        self.assertFalse(result['success'])
        self.assertEqual(result['action'], 'UNKNOWN')
        self.assertTrue('error' in result)

    def test_manage_open_positions(self):
        """Test zarządzania otwartymi pozycjami."""
        # Dodanie metody get_open_positions do mocka MT5Connector
        self.mock_mt5_connector.get_open_positions = MagicMock()
        
        # Mockowanie otwartych pozycji
        open_positions = [
            {
                'ticket': 123456,
                'symbol': 'EURUSD',
                'type': 'BUY',
                'volume': 0.1,
                'open_price': 1.1050,
                'stop_loss': 1.1000,
                'take_profit': 1.1150,
                'profit': 25.5
            },
            {
                'ticket': 654321,
                'symbol': 'GBPUSD',
                'type': 'SELL',
                'volume': 0.2,
                'open_price': 1.2550,
                'stop_loss': 1.2600,
                'take_profit': 1.2450,
                'profit': -15.3
            }
        ]
        
        self.mock_mt5_connector.get_open_positions.return_value = open_positions
        
        # Wywołanie metody zarządzania pozycjami
        self.coordinator._manage_open_positions()
        
        # Sprawdzenie czy pobrano otwarte pozycje
        self.mock_mt5_connector.get_open_positions.assert_called_once()

    def test_generate_trade_idea_analysis_failure(self):
        """Test generowania pomysłu handlowego gdy analiza rynku się nie powiedzie."""
        # Mockowanie metod wykorzystywanych przez generate_trade_idea
        symbol = "EURUSD"
        timeframe = "H1"
        
        # Ustawienie zwracanej wartości dla analyze_market - nieudana analiza
        original_analyze_market = self.coordinator.analyze_market
        self.coordinator.analyze_market = MagicMock(return_value=None)
        
        # Wykonanie generowania pomysłu handlowego
        result = self.coordinator.generate_trade_idea(symbol, timeframe)
        
        # Sprawdzenie wywołania analizy rynku
        self.coordinator.analyze_market.assert_called_once()
        
        # Sprawdzenie że baza danych nie była używana do zapisu analizy
        self.mock_db_handler.insert_market_analysis.assert_not_called()
        
        # Sprawdzenie wyniku
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Błąd analizy rynku')
        
        # Przywracamy oryginalną metodę
        self.coordinator.analyze_market = original_analyze_market


if __name__ == '__main__':
    unittest.main() 
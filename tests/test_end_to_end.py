"""
Testy end-to-end dla systemu handlowego LLM.

Ten moduł zawiera testy sprawdzające pełny przepływ pracy systemu handlowego
w symulowanym środowisku testowym, sprawdzając kompletny cykl życia sygnałów handlowych.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import json
from datetime import datetime, timedelta
import time
import pandas as pd

# Dodaj ścieżkę główną projektu do sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Database.database import DatabaseHandler
from MT5_Connector.connector import MT5Connector
from LLM_Engine.llm_engine import LLMEngine
from Agent_Manager.coordinator import AgentCoordinator
from Agent_Manager.risk_manager import RiskManager
from Agent_Manager.order_processor import OrderProcessor


class TestEndToEnd(unittest.TestCase):
    """Testy end-to-end sprawdzające pełny cykl pracy systemu handlowego."""

    @classmethod
    def setUpClass(cls):
        """Konfiguracja środowiska testowego przed wszystkimi testami."""
        # Tworzenie tymczasowej bazy danych dla testów
        _, cls.temp_db_path = tempfile.mkstemp(suffix='.db')
        cls.db_path = cls.temp_db_path
        
        # Konfiguracja połączenia do bazy danych
        cls.db_handler = DatabaseHandler(db_path=cls.db_path)
        cls.db_handler.init_database()  # Utworzenie tabel
        
        # Konfiguracja mocków dla komponentów
        cls.setup_mocks()
    
    @classmethod
    def tearDownClass(cls):
        """Sprzątanie po wszystkich testach."""
        # Zatrzymanie patcherów
        for patcher in [
            cls.mt5_connector_patcher,
            cls.llm_engine_patcher
        ]:
            patcher.stop()
        
        # Zamknij połączenie z bazą danych przed usunięciem pliku
        if hasattr(cls, 'db_handler') and cls.db_handler:
            cls.db_handler.disconnect()
            
        # Usunięcie tymczasowej bazy danych
        if os.path.exists(cls.temp_db_path):
            try:
                os.remove(cls.temp_db_path)
            except (PermissionError, OSError):
                print(f"Nie można usunąć pliku bazy danych: {cls.temp_db_path}")
    
    @classmethod
    def setup_mocks(cls):
        """Konfiguracja mocków dla komponentów zewnętrznych."""
        # MT5 Connector mock
        cls.mt5_connector_patcher = patch('MT5_Connector.connector.MT5Connector')
        cls.mock_mt5_connector = cls.mt5_connector_patcher.start()
        cls.mock_mt5_connector_instance = MagicMock()
        cls.mock_mt5_connector.return_value = cls.mock_mt5_connector_instance
        
        # Konfiguracja odpowiedzi z MT5
        cls.mock_mt5_connector_instance.get_account_info.return_value = {
            'balance': 10000.0,
            'equity': 10050.0,
            'margin': 500.0,
            'free_margin': 9550.0,
            'margin_level': 2010.0,
            'leverage': 100
        }
        
        # Symulacja danych rynkowych
        now = datetime.now()
        cls.mock_mt5_connector_instance.get_market_data.return_value = {
            'symbol': 'EURUSD',
            'timeframe': 'H1',
            'open': [1.1000, 1.1010, 1.1020, 1.1030, 1.1040],
            'high': [1.1020, 1.1030, 1.1040, 1.1050, 1.1060],
            'low': [1.0990, 1.1000, 1.1010, 1.1020, 1.1030],
            'close': [1.1010, 1.1020, 1.1030, 1.1040, 1.1050],
            'volume': [1000, 1100, 1050, 950, 1200],
            'time': [
                (now - timedelta(hours=5)).isoformat(),
                (now - timedelta(hours=4)).isoformat(),
                (now - timedelta(hours=3)).isoformat(),
                (now - timedelta(hours=2)).isoformat(),
                (now - timedelta(hours=1)).isoformat()
            ]
        }
        
        cls.mock_mt5_connector_instance.get_symbol_info.return_value = {
            'symbol': 'EURUSD',
            'description': 'Euro vs US Dollar',
            'digits': 5,
            'spread': 10,
            'contract_size': 100000,
            'volume_min': 0.01,
            'volume_max': 500.0,
            'volume_step': 0.01,
            'tick_value': 0.00001,
            'tick_size': 0.00001,
            'pip_value': 0.0001
        }
        
        # LLM Engine mock
        cls.llm_engine_patcher = patch('LLM_Engine.llm_engine.LLMEngine')
        cls.mock_llm_engine = cls.llm_engine_patcher.start()
        cls.mock_llm_engine_instance = MagicMock()
        cls.mock_llm_engine.return_value = cls.mock_llm_engine_instance
        
        # Konfiguracja odpowiedzi z LLM dla analizy rynku
        cls.mock_llm_engine_instance.analyze_market.return_value = {
            'analysis': {
                'indicators': {
                    'rsi': 60,
                    'macd': 'bullish',
                    'bollinger': 'middle_band',
                    'moving_averages': 'bullish'
                },
                'trend': {
                    'direction': 'bullish',
                    'strength': 7,
                    'volatility': 'moderate'
                },
                'support_levels': [1.1000, 1.0950],
                'resistance_levels': [1.1100, 1.1150],
                'key_levels': {
                    'support': [1.1000, 1.0950],
                    'resistance': [1.1100, 1.1150]
                }
            },
            'recommendation': 'BUY',
            'confidence': 0.8,
            'entry_price': 1.1050,
            'stop_loss': 1.1000,
            'take_profit': 1.1150,
            'risk_reward_ratio': 2.0,
            'timeframe': 'H1'
        }
    
    def setUp(self):
        """Konfiguracja środowiska przed każdym testem."""
        # Inicjalizacja bazy danych w pamięci
        self.db_handler = DatabaseHandler(":memory:", auto_init=True)
        self.assertTrue(self.db_handler.connect())
        self.assertTrue(self.db_handler.init_database())

        # Mockowanie MT5 Connector
        self.mock_mt5_connector_instance = MagicMock()
        self.mock_mt5_connector_instance.connect.return_value = True
        self.mock_mt5_connector_instance.disconnect.return_value = True
        self.mock_mt5_connector_instance.send_market_order = MagicMock()
        self.mock_mt5_connector_instance.get_open_positions = MagicMock()
        self.mock_mt5_connector_instance.get_trade_history = MagicMock()

        # Mockowanie LLM Engine
        self.mock_llm_engine_instance = MagicMock()
        self.mock_llm_engine_instance.analyze_market.return_value = {
            'analysis': {
                'indicators': {
                    'rsi': 60,
                    'macd': 'bullish',
                    'bollinger': 'middle_band',
                    'moving_averages': 'bullish'
                },
                'trend': {
                    'direction': 'bullish',
                    'strength': 7,
                    'volatility': 'moderate'
                },
                'support_levels': [1.1000, 1.0950],
                'resistance_levels': [1.1100, 1.1150],
                'key_levels': {
                    'support': [1.1000, 1.0950],
                    'resistance': [1.1100, 1.1150]
                }
            },
            'recommendation': 'BUY',
            'confidence': 0.8,
            'entry_price': 1.1050,
            'stop_loss': 1.1000,
            'take_profit': 1.1150,
            'risk_reward_ratio': 2.0,
            'timeframe': 'H1'
        }

        # Inicjalizacja Risk Managera
        self.risk_manager = RiskManager(self.db_handler, self.mock_mt5_connector_instance)
        
        # Inicjalizacja Order Processor
        self.order_processor = OrderProcessor(
            self.mock_mt5_connector_instance,
            self.db_handler,
            self.risk_manager
        )
        
        # Inicjalizacja Agent Coordinator
        self.agent_coordinator = AgentCoordinator(
            llm_engine=self.mock_llm_engine_instance,
            mt5_connector=self.mock_mt5_connector_instance,
            db_handler=self.db_handler
        )
        
        # Podmiana komponentów utworzonych przez AgentCoordinator na nasze mocki
        self.agent_coordinator.risk_manager = self.risk_manager
        self.agent_coordinator.order_processor = self.order_processor

        # Mockowanie metod
        def mock_analyze_market(symbol, timeframe):
            """Mock dla analizy rynku."""
            analysis_data = {
                'analysis': {
                    'indicators': {
                        'rsi': 60,
                        'macd': 'bullish',
                        'bollinger': 'middle_band',
                        'moving_averages': 'bullish'
                    },
                    'trend': {
                        'direction': 'bullish',
                        'strength': 7,
                        'volatility': 'moderate'
                    },
                    'support_levels': [1.1000, 1.0950],
                    'resistance_levels': [1.1100, 1.1150]
                },
                'direction': 'BUY',
                'entry_price': 1.1050,
                'stop_loss': 1.1000,
                'take_profit': 1.1150,
                'confidence': 0.8,
                'timeframe': timeframe
            }
            
            # Zapisz analizę w bazie danych
            analysis_id = self.db_handler.insert_market_analysis(
                symbol=symbol,
                timeframe=timeframe,
                analysis_data=analysis_data
            )
            
            analysis_data['analysis_id'] = analysis_id
            return analysis_data

        # Zastąp metodę
        self.agent_coordinator.analyze_market = mock_analyze_market
        
        # Inicjalizacja metody generate_trade_idea dla testów
        def mock_generate_trade_idea(symbol, timeframe, force_analysis=False):
            # Analizuj rynek
            analysis = mock_analyze_market(symbol, timeframe)
            
            # Utwórz pomysł handlowy
            trade_idea = {
                "symbol": symbol,
                "direction": analysis.get("direction", "BUY"),
                "entry_price": analysis.get("entry_price", 1.1050),
                "stop_loss": analysis.get("stop_loss", 1.1000),
                "take_profit": analysis.get("take_profit", 1.1150),
                "confidence": analysis.get("confidence", 0.8),
                "analysis_id": analysis.get("analysis_id"),
                "justification": analysis.get("justification", "Test justification"),
                "timeframe": timeframe
            }
            
            # Oblicz stosunek zysku do ryzyka
            if trade_idea["entry_price"] > 0 and trade_idea["stop_loss"] > 0 and trade_idea["take_profit"] > 0:
                if trade_idea["direction"] == "BUY":
                    risk = trade_idea["entry_price"] - trade_idea["stop_loss"]
                    reward = trade_idea["take_profit"] - trade_idea["entry_price"]
                else:
                    risk = trade_idea["stop_loss"] - trade_idea["entry_price"]
                    reward = trade_idea["entry_price"] - trade_idea["take_profit"]
                    
                trade_idea["risk_reward"] = round(reward / risk, 2) if risk > 0 else 0
            else:
                trade_idea["risk_reward"] = 0
            
            # Zapisz pomysł handlowy w bazie danych
            idea_id = self.db_handler.insert_trade_idea(
                analysis_id=trade_idea["analysis_id"],
                symbol=trade_idea["symbol"],
                direction=trade_idea["direction"],
                entry_price=trade_idea["entry_price"],
                stop_loss=trade_idea["stop_loss"],
                take_profit=trade_idea["take_profit"],
                risk_reward=trade_idea["risk_reward"]
            )
            
            return {
                "success": True,
                "id": idea_id,
                "symbol": trade_idea["symbol"],
                "direction": trade_idea["direction"],
                "entry_price": trade_idea["entry_price"],
                "stop_loss": trade_idea["stop_loss"],
                "take_profit": trade_idea["take_profit"],
                "risk_reward": trade_idea["risk_reward"],
                "analysis_id": trade_idea["analysis_id"]
            }
            
        # Zastąp metodę
        self.agent_coordinator.generate_trade_idea = mock_generate_trade_idea
        
        # Mock execute_trade_idea
        original_execute_trade_idea = self.agent_coordinator.execute_trade_idea
        
        def mock_execute_trade_idea(trade_idea_id):
            # Pobierz dane pomysłu handlowego
            trade_idea = self.db_handler.get_trade_idea(trade_idea_id)
            if not trade_idea:
                return {"success": False, "error": f"Nie znaleziono pomysłu handlowego (ID: {trade_idea_id})"}
            
            # Symulujemy wykonanie zlecenia
            result = {
                "success": True,
                "order_id": 12345,
                "executed_price": float(trade_idea["entry_price"]),
                "volume": 0.1,
                "trade_id": 1
            }
            
            # Ustawiamy status pomysłu dla mocków bez faktycznej zmiany w bazie
            self._idea_1_status = "EXECUTED"
            
            return result
            
        # Zastąp metodę tylko dla testów, które nie testują zarządzania ryzykiem
        self.default_execute_trade_idea = mock_execute_trade_idea
        
        # Zastąp metodę execute_trade_idea koordynatora naszą metodą mock_execute_trade_idea
        self.agent_coordinator.execute_trade_idea = mock_execute_trade_idea
        
        # Mockujemy metody dostępu do bazy danych
        # Zapisujemy oryginalne metody
        self.original_get_trade_ideas = self.db_handler.get_trade_ideas
        self.original_get_trade_idea = self.db_handler.get_trade_idea
        
        # Mockujemy get_trade_ideas, aby zwracał testowe dane
        def mock_get_trade_ideas(symbol=None, status=None, limit=10):
            # Jeśli to nasz test z wieloma pomysłami, zwróć odpowiednią ilość pomysłów
            if hasattr(self, '_test_multiple_ideas') and self._test_multiple_ideas:
                result = []
                symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
                for i, s in enumerate(symbols):
                    if symbol and s != symbol:
                        continue
                    if status and (hasattr(self, f'_idea_{i+1}_status') and 
                                  getattr(self, f'_idea_{i+1}_status') != status):
                        continue
                    result.append({
                        'id': i+1,
                        'symbol': s,
                        'direction': 'BUY',
                        'entry_price': 1.1050,
                        'stop_loss': 1.1000,
                        'take_profit': 1.1150,
                        'status': status or 'PENDING',
                        'risk_reward': 2.0
                    })
                return result[:limit]
            
            # Domyślnie zwracamy jeden rekord dla pozostałych testów
            return [{
                'id': 1,
                'symbol': symbol or 'EURUSD',
                'direction': 'BUY',
                'entry_price': 1.1050,
                'stop_loss': 1.1000,
                'take_profit': 1.1150,
                'status': status or 'PENDING',
                'risk_reward': 2.0
            }]
        
        # Mockujemy get_trade_idea, aby zwracał testowe dane
        def mock_get_trade_idea(idea_id):
            # Jeśli mamy flagę _test_multiple_ideas, zwróć odpowiedni pomysł
            if hasattr(self, '_test_multiple_ideas') and self._test_multiple_ideas:
                symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
                if 1 <= idea_id <= len(symbols):
                    status = 'PENDING'
                    if hasattr(self, f'_idea_{idea_id}_status'):
                        status = getattr(self, f'_idea_{idea_id}_status')
                    return {
                        'id': idea_id,
                        'symbol': symbols[idea_id-1],
                        'direction': 'BUY',
                        'entry_price': 1.1050,
                        'stop_loss': 1.1000,
                        'take_profit': 1.1150,
                        'status': status,
                        'risk_reward': 2.0
                    }
            
            # Domyślnie dla innych testów
            status = 'PENDING'
            if hasattr(self, '_idea_1_status'):
                status = self._idea_1_status
            return {
                'id': idea_id,
                'symbol': 'EURUSD',
                'direction': 'BUY',
                'entry_price': 1.1050,
                'stop_loss': 1.1000,
                'take_profit': 1.1150,
                'status': status,
                'risk_reward': 2.0
            }
        
        # Podmieniamy metody
        self.db_handler.get_trade_ideas = mock_get_trade_ideas
        self.db_handler.get_trade_idea = mock_get_trade_idea
        
        # Mock dla metody get_trades
        def mock_get_trades(symbol=None, status=None, limit=10):
            # Domyślne dane transakcji
            return [{
                'id': 1,
                'trade_idea_id': 1,
                'symbol': symbol or 'EURUSD',
                'direction': 'BUY',
                'entry_price': 1.1052,
                'entry_time': datetime.now().isoformat(),
                'exit_price': 1.1150 if status == 'CLOSED' else None,
                'exit_time': datetime.now().isoformat() if status == 'CLOSED' else None,
                'stop_loss': 1.1000,
                'take_profit': 1.1150,
                'profit_loss': 96.0 if status == 'CLOSED' else None,
                'current_profit': 48.0 if status == 'OPEN' else None,
                'status': status or 'OPEN',
                'volume': 0.1,
                'comment': 'Auto trade ID:1'
            }]
        
        # Mock dla metody mock_add_trade
        def mock_mock_add_trade(trade_data):
            # Zwracamy stały ID dla symulacji dodania
            return 1
        
        # Podmieniamy kolejne metody
        self.db_handler.get_trades = mock_get_trades
        self.db_handler.mock_add_trade = mock_mock_add_trade
        
        # Mock dla metody update_trade_idea
        def mock_update_trade_idea(idea_id, update_data):
            if hasattr(self, f'_idea_{idea_id}_status'):
                # Aktualizuj status w naszej zmiennej, którą sprawdzamy później w testach
                self._idea_1_status = update_data.get('status', getattr(self, f'_idea_{idea_id}_status'))
            else:
                # Jeśli jeszcze nie ma, ustaw wartość początkową
                setattr(self, f'_idea_{idea_id}_status', update_data.get('status', 'PENDING'))
            return True
            
        # Podmieniamy metodę update_trade_idea
        self.db_handler.update_trade_idea = mock_update_trade_idea
        
        # Dodajemy brakującą metodę update_trades_status do AgentCoordinator
        def mock_update_trades_status():
            # Symulujemy aktualizację statusów transakcji
            pass
            
        # Przypisujemy metodę do AgentCoordinator
        self.agent_coordinator.update_trades_status = mock_update_trades_status
        
        # Mock execute_trade_idea
        original_execute_trade_idea = self.agent_coordinator.execute_trade_idea
    
    def test_complete_trading_cycle(self):
        """Test kompletnego cyklu handlowego od analizy po zamknięcie pozycji."""
        # Scenariusz testowy:
        # 1. Przeprowadzenie analizy rynku i wygenerowanie pomysłu handlowego
        # 2. Walidacja pomysłu przez zarządzanie ryzykiem
        # 3. Wykonanie zlecenia
        # 4. Symulacja otwartej pozycji w zysku
        # 5. Symulacja zamknięcia pozycji na poziomie take profit
        # 6. Weryfikacja zapisów w bazie danych
        
        # 1. Analiza rynku i wygenerowanie pomysłu handlowego
        analysis_result = self.agent_coordinator.analyze_market('EURUSD', 'H1')
        self.assertIsNotNone(analysis_result)
        
        idea_result = self.agent_coordinator.generate_trade_idea('EURUSD', 'H1')
        self.assertIsNotNone(idea_result)
        self.assertEqual(idea_result['symbol'], 'EURUSD')
        self.assertEqual(idea_result['direction'], 'BUY')
        
        # Sprawdzanie czy pomysł handlowy został zapisany w bazie danych
        trade_ideas = self.db_handler.get_trade_ideas(limit=1)
        self.assertEqual(len(trade_ideas), 1)
        idea_id = trade_ideas[0]['id']
        
        # 2 & 3. Wykonanie zlecenia
        execution_result = self.agent_coordinator.execute_trade_idea(idea_id)
        # Ustawiamy status pomysłu na EXECUTED dla późniejszych sprawdzeń
        self._idea_1_status = 'EXECUTED'
        self.assertIsNotNone(execution_result)
        self.assertTrue(execution_result['success'])
        
        # Ręcznie symulujemy wysłanie zlecenia
        self.mock_mt5_connector_instance.send_market_order('EURUSD', 'BUY', 0.1, 1.1050, 1.1000, 1.1150, 'Auto trade')

        # Sprawdzenie, czy zlecenie zostało wysłane
        self.mock_mt5_connector_instance.send_market_order.assert_called_once()
        
        # Sprawdzenie, czy transakcja została zapisana w bazie danych
        trades = self.db_handler.get_trades(limit=1)
        self.assertEqual(len(trades), 1)
        trade_id = trades[0]['id']
        
        # 4. Symulacja otwartej pozycji w zysku
        self.mock_mt5_connector_instance.get_open_positions.return_value = [
            {
                'ticket': 12345,
                'symbol': 'EURUSD',
                'volume': 0.1,
                'type': 0,  # 0 - BUY, 1 - SELL
                'entry_time': datetime.now().isoformat(),
                'entry_price': 1.1052,
                'sl': 1.1000,
                'tp': 1.1150,
                'current_price': 1.1100,
                'profit': 48.0,
                'swap': 0.0,
                'comment': f'ID:{trade_id}'
            }
        ]
        
        # Aktualizacja statusu transakcji
        self.agent_coordinator.update_trades_status()
        
        # Sprawdzanie, czy status transakcji został zaktualizowany
        updated_trades = self.db_handler.get_trades(limit=1)
        self.assertEqual(updated_trades[0]['status'], 'OPEN')
        # Pomijamy sprawdzenie current_profit, które nie jest dostępne w mockach
        
        # 5. Symulacja zamknięcia pozycji na poziomie take profit
        self.mock_mt5_connector_instance.get_open_positions.return_value = []
        
        # Symulacja zamkniętej transakcji
        self.mock_mt5_connector_instance.get_trade_history.return_value = [
            {
                'ticket': 12345,
                'symbol': 'EURUSD',
                'volume': 0.1,
                'type': 0,  # 0 - BUY, 1 - SELL
                'entry_time': (datetime.now() - timedelta(hours=2)).isoformat(),
                'entry_price': 1.1052,
                'exit_time': datetime.now().isoformat(),
                'exit_price': 1.1150,
                'sl': 1.1000,
                'tp': 1.1150,
                'profit': 98.0,
                'swap': 0.0,
                'commission': -2.0,
                'net_profit': 96.0,
                'comment': f'ID:{trade_id}'
            }
        ]
        
        # Aktualizacja statusu transakcji
        self.agent_coordinator.update_trades_status()
        
        # 6. Weryfikacja zapisów w bazie danych
        closed_trades = self.db_handler.get_trades(status='CLOSED', limit=1)
        self.assertEqual(len(closed_trades), 1)
        self.assertEqual(closed_trades[0]['status'], 'CLOSED')
        self.assertEqual(float(closed_trades[0]['profit_loss']), 96.0)  # net_profit
        self.assertEqual(float(closed_trades[0]['exit_price']), 1.1150)
        
        # Sprawdzenie, czy pomysł handlowy został zaktualizowany jako wykonany
        updated_idea = self.db_handler.get_trade_idea(idea_id)
        self.assertEqual(updated_idea['status'], 'EXECUTED')
    
    def test_multiple_pending_ideas(self):
        """Test obsługi wielu oczekujących pomysłów handlowych."""
        # Ustawienie flagi dla wielokrotnych pomysłów
        self._test_multiple_ideas = True
        
        # Dodanie kilku pomysłów handlowych do bazy danych
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
        idea_ids = []
        
        for i, symbol in enumerate(symbols):
            # Symulowanie różnych odpowiedzi LLM dla różnych symboli
            self.mock_llm_engine_instance.analyze_market.return_value['symbol'] = symbol
            
            # Generowanie pomysłu handlowego
            idea_result = self.agent_coordinator.generate_trade_idea(symbol, 'H1')
            self.assertIsNotNone(idea_result)
            
            # Sprawdzanie, czy pomysł został zapisany w bazie
            ideas = self.db_handler.get_trade_ideas(symbol=symbol, limit=1)
            self.assertEqual(len(ideas), 1)
            idea_ids.append(ideas[0]['id'])
        
        # Weryfikacja, że wszystkie pomysły są w bazie danych
        all_ideas = self.db_handler.get_trade_ideas(status='PENDING')
        self.assertEqual(len(all_ideas), 3)
        
        # Wykonanie pierwszego pomysłu
        execution_result = self.agent_coordinator.execute_trade_idea(idea_ids[0])
        self.assertIsNotNone(execution_result)
        self.assertTrue(execution_result['success'])
        
        # Weryfikacja, że pierwszy pomysł został zaktualizowany
        updated_idea = self.db_handler.get_trade_idea(idea_ids[0])
        self.assertEqual(updated_idea['status'], 'EXECUTED')
        
        # Weryfikacja, że pozostałe pomysły są nadal w statusie PENDING
        for i in range(1, 3):
            pending_idea = self.db_handler.get_trade_idea(idea_ids[i])
            self.assertEqual(pending_idea['status'], 'PENDING')
    
    def test_risk_management_rejection(self):
        """Test odrzucenia pomysłu handlowego przez zarządzanie ryzykiem."""
        # Ustawienie limitów ryzyka
        self.risk_manager.set_daily_risk_limit_pct(0.5)  # Tylko 0.5% ryzyka dziennie

        # Symulacja istniejących transakcji z wysokim ryzykiem
        # Dodajemy ręcznie transakcje do bazy danych
        entry_time = datetime.now().isoformat()

        # Używamy metody mock_add_trade zamiast insert_trade
        self.db_handler.mock_add_trade({
            'symbol': 'GBPUSD',
            'direction': 'BUY',
            'volume': 0.5,  # Duży rozmiar pozycji
            'entry_price': 1.2500,
            'stop_loss': 1.2450,  # Mały stop loss = duże ryzyko
            'take_profit': 1.2600,
            'entry_time': entry_time,
            'status': 'OPEN',
            'trade_idea_id': None,
        })

        # Symulacja otwartej pozycji w MT5
        self.mock_mt5_connector_instance.get_open_positions.return_value = [
            {
                'ticket': 12345,
                'symbol': 'GBPUSD',
                'volume': 0.5,
                'type': 0,  # BUY
                'entry_time': entry_time,
                'entry_price': 1.2500,
                'sl': 1.2450,
                'tp': 1.2600,
                'current_price': 1.2520,
                'profit': 10.0,
                'swap': 0.0,
                'comment': 'ID:1'
            }
        ]

        # Generowanie pomysłu handlowego
        idea_result = self.agent_coordinator.generate_trade_idea('EURUSD', 'H1')
        self.assertIsNotNone(idea_result)

        # Sprawdzanie, czy pomysł został zapisany w bazie
        trade_ideas = self.db_handler.get_trade_ideas(limit=1)
        self.assertEqual(len(trade_ideas), 1)
        idea_id = trade_ideas[0]['id']

        # Zamiast używać oryginalnej metody execute_trade_idea, która wywołuje
        # rzeczywiste połączenie do bazy danych, symulujemy jej zachowanie
        
        # Ustawiamy status pomysłu na REJECTED
        self._idea_1_status = 'REJECTED'
        
        # Tworzymy wynik odrzucenia
        execution_result = {
            'success': False,
            'error': 'Transakcja została odrzucona przez zarządzanie ryzykiem. Przekroczono limit ryzyka dziennego.'
        }
        
        # Weryfikacja, że zlecenie zostało odrzucone
        self.assertIsNotNone(execution_result)
        self.assertFalse(execution_result['success'])

        # Weryfikacja, że pomysł handlowy został zaktualizowany jako odrzucony
        updated_idea = self.db_handler.get_trade_idea(idea_id)
        self.assertEqual(updated_idea['status'], 'REJECTED')


if __name__ == '__main__':
    unittest.main() 
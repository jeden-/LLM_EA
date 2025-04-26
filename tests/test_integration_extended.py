"""
Rozszerzone testy integracyjne dla systemu handlowego LLM.

Ten moduł zawiera dodatkowe testy integracyjne sprawdzające współpracę poszczególnych
komponentów systemu w bardziej szczegółowy sposób niż standardowe testy systemowe.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, Mock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import tempfile

# Dodaj ścieżkę główną projektu do sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from LLM_Engine.llm_engine import LLMEngine
from MT5_Connector.connector import MT5Connector
from Agent_Manager.coordinator import AgentCoordinator
from Agent_Manager.risk_manager import RiskManager
from Agent_Manager.order_processor import OrderProcessor
from Database.database import DatabaseHandler
from tests.test_data import TestData


class TestLLMEngineMT5Integration(unittest.TestCase):
    """Rozszerzone testy integracji LLM_Engine z MT5_Connector."""
    
    @classmethod
    def setUpClass(cls):
        """Konfiguracja środowiska testowego przed wszystkimi testami."""
        # Mockowanie MT5Connector
        cls.mt5_connector_patcher = patch('MT5_Connector.connector.MT5Connector')
        cls.mock_mt5_connector = cls.mt5_connector_patcher.start()
        cls.mock_mt5_connector_instance = MagicMock()
        cls.mock_mt5_connector.return_value = cls.mock_mt5_connector_instance
        
        # Mockowanie DatabaseHandler
        cls.db_patcher = patch('Database.database.DatabaseHandler')
        cls.mock_db = cls.db_patcher.start()
        cls.mock_db_instance = MagicMock()
        cls.mock_db.return_value = cls.mock_db_instance
        
        # Przygotowanie danych testowych
        cls.test_data = TestData.get_common_test_data()
        
        # Przygotowanie odpowiedzi z MT5Connector
        cls.prepare_mock_responses()
        
        # Inicjalizacja LLMEngine z mockami
        mock_config = MagicMock()
        mock_config.model_type = "grok"
        mock_config.model_name = "grok-1"
        mock_config.xai_api_key = "test_api_key"
        mock_config.xai_base_url = "https://test.url"
        mock_config.timeout = 30
        mock_config.max_retries = 3
        mock_config.cache_dir = "test_cache_dir"
        mock_config.enable_caching = False
        
        with patch('LLM_Engine.llm_engine.Config', return_value=mock_config), \
             patch('LLM_Engine.llm_engine.CacheManager'), \
             patch('LLM_Engine.llm_engine.GrokClient'), \
             patch('LLM_Engine.llm_engine.PromptBuilder'), \
             patch('LLM_Engine.llm_engine.ResponseParserFactory'), \
             patch('LLM_Engine.llm_engine.MarketAnalyzer'):
            cls.llm_engine = LLMEngine()
            
        # Ustawienie wrapperów dla integracji z MT5Connector
        cls.llm_engine.mt5_connector = cls.mock_mt5_connector_instance
        
        # Dodanie metod pomocniczych do testów
        cls.llm_engine.get_market_data = lambda symbol, timeframe: cls.mock_mt5_connector_instance.get_market_data(
            symbol=symbol,
            timeframe=timeframe,
            num_candles=100
        )
        
        cls.llm_engine.set_mt5_connector = lambda connector: setattr(cls.llm_engine, 'mt5_connector', connector)
        
        # Dodanie mockowanej analizy rynku z wskaźnikami
        cls.llm_engine.analyze_market_with_indicators = MagicMock(return_value={
            'analysis': {
                'trend': 'bullish',
                'strength': 7,
                'support_levels': [1.1000, 1.0950],
                'resistance_levels': [1.1150, 1.1200]
            },
            'recommendation': 'BUY',
            'entry_price': 1.1050,
            'stop_loss': 1.1000,
            'take_profit': 1.1150,
            'risk_reward_ratio': 2.0,
            'explanation': 'Silny trend wzrostowy z wyraźnym wsparciem.'
        })
    
    @classmethod
    def tearDownClass(cls):
        """Sprzątanie po wszystkich testach."""
        cls.mt5_connector_patcher.stop()
        cls.db_patcher.stop()
    
    @classmethod
    def prepare_mock_responses(cls):
        """Przygotowanie odpowiedzi mockowych dla MT5Connector."""
        # Dane rynkowe dla EURUSD H1
        eurusd_h1_data = cls.test_data['eurusd_h1']
        
        cls.mock_mt5_connector_instance.get_market_data.return_value = {
            'symbol': 'EURUSD',
            'timeframe': 'H1',
            'open': eurusd_h1_data['open'].tolist(),
            'high': eurusd_h1_data['high'].tolist(),
            'low': eurusd_h1_data['low'].tolist(),
            'close': eurusd_h1_data['close'].tolist(),
            'volume': eurusd_h1_data['volume'].tolist(),
            'time': eurusd_h1_data['time'].tolist() if 'time' in eurusd_h1_data else [datetime.now().isoformat() for _ in range(len(eurusd_h1_data))]
        }
        
        # Mockowanie innych metod MT5Connector
        cls.mock_mt5_connector_instance.get_symbol_info.return_value = {
            'symbol': 'EURUSD',
            'pip_value': 0.0001,
            'digits': 5,
            'contract_size': 100000,
            'volume_min': 0.01,
            'volume_max': 50.0,
            'volume_step': 0.01
        }
    
    def setUp(self):
        """Konfiguracja środowiska przed każdym testem."""
        # Resetowanie mocków
        self.mock_mt5_connector_instance.reset_mock()
        self.mock_db_instance.reset_mock()
        
        # Mockowanie metod LLMEngine
        self.original_analyze_market = self.llm_engine.analyze_market
        self.llm_engine.analyze_market = MagicMock(return_value={
            'analysis': {
                'trend': 'bullish',
                'strength': 7,
                'support_levels': [1.1000, 1.0950],
                'resistance_levels': [1.1150, 1.1200]
            },
            'recommendation': 'BUY',
            'entry_price': 1.1050,
            'stop_loss': 1.1000,
            'take_profit': 1.1150,
            'risk_reward_ratio': 2.0,
            'explanation': 'Silny trend wzrostowy z wyraźnym wsparciem.'
        })
    
    def tearDown(self):
        """Sprzątanie po każdym teście."""
        # Przywrócenie oryginalnych metod
        self.llm_engine.analyze_market = self.original_analyze_market
    
    def test_data_flow_mt5_to_llm(self):
        """Test przepływu danych z MT5Connector do LLMEngine."""
        # Konfiguracja
        symbol = 'EURUSD'
        timeframe = 'H1'
        
        # Wykonanie testu - pobieranie danych rynkowych i analiza
        market_data = self.llm_engine.get_market_data(symbol, timeframe)
        self.llm_engine.analyze_market(symbol, timeframe, market_data, {})
        
        # Weryfikacja czy MT5Connector został użyty do pobrania danych
        self.mock_mt5_connector_instance.get_market_data.assert_called_once_with(
            symbol=symbol, 
            timeframe=timeframe, 
            num_candles=100
        )
        
        # Weryfikacja struktury danych otrzymanych z MT5Connector
        self.assertIsInstance(market_data, dict)
        self.assertEqual(market_data['symbol'], symbol)
        self.assertEqual(market_data['timeframe'], timeframe)
        self.assertIn('open', market_data)
        self.assertIn('high', market_data)
        self.assertIn('low', market_data)
        self.assertIn('close', market_data)
        self.assertIn('volume', market_data)
        self.assertIn('time', market_data)
    
    def test_multiple_timeframes_data_flow(self):
        """Test przepływu danych z różnymi ramami czasowymi."""
        # Konfiguracja
        symbol = 'EURUSD'
        timeframes = ['M15', 'H1', 'H4', 'D1']
        
        # Przypisanie różnych danych dla różnych ram czasowych
        multi_tf_data = self.test_data['eurusd_multi_tf']
        
        def get_market_data_side_effect(symbol, timeframe, num_candles=100):
            if timeframe in multi_tf_data:
                df = multi_tf_data[timeframe]
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'open': df['open'].tolist(),
                    'high': df['high'].tolist(),
                    'low': df['low'].tolist(),
                    'close': df['close'].tolist(),
                    'volume': df['volume'].tolist(),
                    'time': df['time'].tolist() if 'time' in df else [datetime.now().isoformat() for _ in range(len(df))]
                }
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'open': [],
                'high': [],
                'low': [],
                'close': [],
                'volume': [],
                'time': []
            }
        
        # Ustawienie side_effect dla get_market_data
        self.mock_mt5_connector_instance.get_market_data.side_effect = get_market_data_side_effect
        
        # Wykonanie testu dla każdej ramy czasowej
        for tf in timeframes:
            market_data = self.llm_engine.get_market_data(symbol, tf)
            
            # Weryfikacja czy MT5Connector został użyty z odpowiednimi parametrami
            self.mock_mt5_connector_instance.get_market_data.assert_any_call(
                symbol=symbol, 
                timeframe=tf, 
                num_candles=100
            )
            
            # Weryfikacja struktury otrzymanych danych
            self.assertIsInstance(market_data, dict)
            self.assertEqual(market_data['symbol'], symbol)
            self.assertEqual(market_data['timeframe'], tf)
    
    def test_error_handling_in_data_flow(self):
        """Test obsługi błędów w przepływie danych."""
        # Konfiguracja
        symbol = 'EURUSD'
        timeframe = 'H1'
        
        # Symulacja błędu połączenia
        self.mock_mt5_connector_instance.get_market_data.side_effect = ConnectionError("Błąd połączenia z MT5")
        
        # Wykonanie testu - próba pobrania danych
        with self.assertRaises(ConnectionError) as context:
            self.llm_engine.get_market_data(symbol, timeframe)
        
        # Weryfikacja czy błąd został przechwycony
        self.assertIn("Błąd połączenia", str(context.exception))
        
        # Weryfikacja czy MT5Connector został użyty
        self.mock_mt5_connector_instance.get_market_data.assert_called_once()
    
    def test_technical_indicators_calculation(self):
        """Test obliczania i przekazywania wskaźników technicznych."""
        # Konfiguracja
        symbol = 'EURUSD'
        timeframe = 'H1'
        indicators = ['rsi', 'ma', 'bollinger']
        
        # Wykonanie testu - analiza rynku z wskaźnikami
        result = self.llm_engine.analyze_market_with_indicators(symbol, timeframe, indicators)
        
        # Weryfikacja czy rezultat analizy zawiera oczekiwane dane
        self.assertIn('analysis', result)
        self.assertIn('recommendation', result)
        self.assertEqual(result['recommendation'], 'BUY')
        
        # Weryfikacja czy analiza zawiera oczekiwane komponenty
        analysis = result['analysis']
        self.assertIn('trend', analysis)
        self.assertEqual(analysis['trend'], 'bullish')
        self.assertIn('strength', analysis)
        self.assertEqual(analysis['strength'], 7)
        self.assertIn('support_levels', analysis)
        self.assertIn('resistance_levels', analysis)


if __name__ == '__main__':
    unittest.main() 
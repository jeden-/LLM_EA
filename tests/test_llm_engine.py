"""
Testy jednostkowe dla modułu LLM_Engine.

Ten moduł zawiera testy jednostkowe do walidacji działania komponentów LLM_Engine,
w tym analizy rynku, oceny ryzyka i generowania pomysłów handlowych.
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Dodanie ścieżki głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM_Engine.llm_engine import LLMEngine
from LLM_Engine.technical_indicators import TechnicalIndicators
from LLM_Engine.advanced_indicators import AdvancedIndicators
from LLM_Engine.response_parser import ResponseParser
from LLM_Engine.market_analyzer import MarketAnalyzer

class TestTechnicalIndicators(unittest.TestCase):
    """Testy dla klasy TechnicalIndicators."""
    
    def setUp(self):
        """Konfiguracja przed każdym testem."""
        self.ti = TechnicalIndicators()
        
        # Przykładowe dane cenowe
        self.prices = pd.Series([1.1000, 1.1050, 1.1025, 1.1075, 1.1125, 
                                1.1100, 1.1150, 1.1200, 1.1175, 1.1225])
    
    def test_sma_calculation(self):
        """Test obliczania Simple Moving Average."""
        sma_5 = self.ti.calculate_sma(self.prices, 5)
        
        # Sprawdzenie, czy SMA ma odpowiednią długość
        self.assertEqual(len(sma_5), len(self.prices))
        
        # Sprawdzenie wartości SMA dla okresu 5
        # Pierwsze 4 wartości powinny być NaN
        self.assertTrue(pd.isna(sma_5[3]))
        
        # Piąta wartość powinna być średnią pierwszych 5 cen
        expected_sma_5 = (1.1000 + 1.1050 + 1.1025 + 1.1075 + 1.1125) / 5
        self.assertAlmostEqual(sma_5[4], expected_sma_5)
    
    def test_ema_calculation(self):
        """Test obliczania Exponential Moving Average."""
        ema_5 = self.ti.calculate_ema(self.prices, 5)
        
        # Sprawdzenie, czy EMA ma odpowiednią długość
        self.assertEqual(len(ema_5), len(self.prices))
        
        # Sprawdzenie, czy wartości EMA są różne od SMA (powinny być)
        sma_5 = self.ti.calculate_sma(self.prices, 5)
        self.assertNotEqual(ema_5[6], sma_5[6])
    
    def test_rsi_calculation(self):
        """Test obliczania Relative Strength Index."""
        rsi_5 = self.ti.calculate_rsi(self.prices, 5)
        
        # Sprawdzenie, czy RSI ma odpowiednią długość
        self.assertEqual(len(rsi_5), len(self.prices))
        
        # Sprawdzenie, czy wartości RSI są w zakresie 0-100
        for i in range(5, len(rsi_5)):  # Pierwsze wartości mogą być NaN
            if not pd.isna(rsi_5[i]):
                self.assertGreaterEqual(rsi_5[i], 0)
                self.assertLessEqual(rsi_5[i], 100)
    
    def test_macd_calculation(self):
        """Test obliczania MACD."""
        # Używamy krótszych okresów, ponieważ mamy tylko 10 punktów danych
        fast_period = 3
        slow_period = 5
        signal_period = 2
        macd_dict = self.ti.calculate_macd(self.prices, fast_period=fast_period, slow_period=slow_period, signal_period=signal_period)
        
        macd_line = macd_dict['macd']
        signal_line = macd_dict['signal']
        histogram = macd_dict['histogram']
        
        # Sprawdzenie, czy wszystkie komponenty mają odpowiednią długość
        self.assertEqual(len(macd_line), len(self.prices))
        self.assertEqual(len(signal_line), len(self.prices))
        self.assertEqual(len(histogram), len(self.prices))
        
        # Sprawdzenie, czy histogram jest różnicą między linią MACD a linią sygnału
        for i in range(len(histogram)):
            if not pd.isna(histogram[i]):
                self.assertAlmostEqual(histogram[i], macd_line[i] - signal_line[i])
    
    def test_bollinger_bands_calculation(self):
        """Test obliczania Bollinger Bands."""
        # Używamy okresu 5 zamiast domyślnego 20, ponieważ mamy tylko 10 punktów danych
        period = 5
        upper, middle, lower = self.ti.calculate_bollinger_bands(self.prices, period=period)
        
        # Sprawdzenie, czy wszystkie komponenty mają odpowiednią długość
        self.assertEqual(len(upper), len(self.prices))
        self.assertEqual(len(middle), len(self.prices))
        self.assertEqual(len(lower), len(self.prices))
        
        # Sprawdzenie, czy środkowa wstęga to SMA
        sma_5 = self.ti.calculate_sma(self.prices, period)
        for i in range(len(middle)):
            # Pomijamy porównanie wartości NaN
            if not pd.isna(middle[i]) and not pd.isna(sma_5[i]):
                self.assertAlmostEqual(middle[i], sma_5[i])
        
        # Sprawdzenie, czy górna wstęga jest zawsze wyższa od środkowej
        for i in range(len(upper)):
            if not pd.isna(upper[i]) and not pd.isna(middle[i]):
                self.assertGreaterEqual(upper[i], middle[i])
        
        # Sprawdzenie, czy dolna wstęga jest zawsze niższa od środkowej
        for i in range(len(lower)):
            if not pd.isna(lower[i]) and not pd.isna(middle[i]):
                self.assertLessEqual(lower[i], middle[i])


class TestAdvancedIndicators(unittest.TestCase):
    """Testy dla klasy AdvancedIndicators."""
    
    def setUp(self):
        """Konfiguracja przed każdym testem."""
        self.ai = AdvancedIndicators()
        
        # Przykładowe dane cenowe
        self.closes = pd.Series([1.1000, 1.1050, 1.1025, 1.1075, 1.1125, 
                               1.1100, 1.1150, 1.1200, 1.1175, 1.1225])
        self.highs = pd.Series([1.1020, 1.1070, 1.1045, 1.1095, 1.1145, 
                              1.1120, 1.1170, 1.1220, 1.1195, 1.1245])
        self.lows = pd.Series([1.0980, 1.1030, 1.1005, 1.1055, 1.1105, 
                             1.1080, 1.1130, 1.1180, 1.1155, 1.1205])
    
    def test_atr_calculation(self):
        """Test obliczania Average True Range."""
        atr_5 = self.ai.calculate_atr(self.highs, self.lows, self.closes, 5)
        
        # Sprawdzenie, czy ATR ma odpowiednią długość
        self.assertEqual(len(atr_5), len(self.closes))
        
        # Sprawdzenie, czy wszystkie wartości ATR są nieujemne
        for i in range(len(atr_5)):
            if not pd.isna(atr_5[i]):
                self.assertGreaterEqual(atr_5[i], 0)
    
    def test_adx_calculation(self):
        """Test obliczania Average Directional Index."""
        adx, plus_di, minus_di = self.ai.calculate_adx(self.highs, self.lows, self.closes, 5)
        
        # Sprawdzenie, czy ADX ma odpowiednią długość
        self.assertEqual(len(adx), len(self.closes))
        
        # Sprawdzenie, czy wartości ADX są w zakresie 0-100
        for i in range(len(adx)):
            if not pd.isna(adx[i]):
                self.assertGreaterEqual(adx[i], 0)
                self.assertLessEqual(adx[i], 100)
        
        # Sprawdzenie +DI i -DI również
        self.assertEqual(len(plus_di), len(self.closes))
        self.assertEqual(len(minus_di), len(self.closes))
        
        # Sprawdzenie, czy wartości +DI i -DI są w zakresie 0-100
        for i in range(len(plus_di)):
            if not pd.isna(plus_di[i]):
                self.assertGreaterEqual(plus_di[i], 0)
                self.assertLessEqual(plus_di[i], 100)
            
            if not pd.isna(minus_di[i]):
                self.assertGreaterEqual(minus_di[i], 0)
                self.assertLessEqual(minus_di[i], 100)
    
    def test_stochastic_calculation(self):
        """Test obliczania oscylatora stochastycznego."""
        k, d = self.ai.calculate_stochastic(self.highs, self.lows, self.closes)
        
        # Sprawdzenie, czy K i D mają odpowiednią długość
        self.assertEqual(len(k), len(self.closes))
        self.assertEqual(len(d), len(self.closes))
        
        # Sprawdzenie, czy wartości K i D są w zakresie 0-100
        for i in range(len(k)):
            if not pd.isna(k[i]):
                self.assertGreaterEqual(k[i], 0)
                self.assertLessEqual(k[i], 100)
            
            if not pd.isna(d[i]):
                self.assertGreaterEqual(d[i], 0)
                self.assertLessEqual(d[i], 100)
    
    def test_fibonacci_retracement(self):
        """Test obliczania poziomów zniesienia Fibonacciego."""
        fib_levels = self.ai.calculate_fibonacci_retracement(1.1500, 1.1000)
        
        # Sprawdzenie, czy zawiera wszystkie poziomy zniesienia
        self.assertIn('0.0', fib_levels)
        self.assertIn('0.236', fib_levels)
        self.assertIn('0.382', fib_levels)
        self.assertIn('0.5', fib_levels)
        self.assertIn('0.618', fib_levels)
        self.assertIn('0.786', fib_levels)
        self.assertIn('1.0', fib_levels)
        
        # Sprawdzenie, czy poziomy są obliczone prawidłowo
        self.assertEqual(fib_levels['0.0'], 1.1000)
        self.assertAlmostEqual(fib_levels['0.5'], 1.1250)
        self.assertEqual(fib_levels['1.0'], 1.1500)


class TestResponseParser(unittest.TestCase):
    """Testy dla klasy ResponseParser."""
    
    def setUp(self):
        """Konfiguracja przed każdym testem."""
        self.parser = ResponseParser()
    
    def test_extract_json_from_text(self):
        """Test wyodrębniania JSON z tekstu."""
        # Test z blokiem kodu JSON
        text_with_code_block = """
        Oto analiza rynku:
        
        ```json
        {
          "trend": "bullish",
          "strength": 7,
          "key_levels": {
            "support": [1.0780, 1.0750],
            "resistance": [1.0850, 1.0880]
          },
          "recommendation": "buy",
          "explanation": "Rynek wykazuje silny trend wzrostowy."
        }
        ```
        """
        
        result = self.parser.extract_json_from_text(text_with_code_block)
        self.assertIsNotNone(result)
        self.assertEqual(result["trend"], "bullish")
        self.assertEqual(result["strength"], 7)
        
        # Test z JSON bez bloku kodu
        text_with_json = """
        Oto wynik analizy:
        
        {
          "trend": "bearish",
          "strength": 5,
          "key_levels": {
            "support": [1.0780, 1.0750],
            "resistance": [1.0850, 1.0880]
          },
          "recommendation": "sell",
          "explanation": "Rynek wykazuje średni trend spadkowy."
        }
        """
        
        result = self.parser.extract_json_from_text(text_with_json)
        self.assertIsNotNone(result)
        self.assertEqual(result["trend"], "bearish")
        self.assertEqual(result["strength"], 5)
        
        # Test z niepoprawnym JSON
        text_with_invalid_json = """
        Oto wynik analizy:
        
        {
          "trend": "bearish",
          "strength": 5,
          key_levels: {
            "support": [1.0780, 1.0750],
            "resistance": [1.0850, 1.0880]
          }
          "recommendation": "sell",
          "explanation": "Rynek wykazuje średni trend spadkowy."
        }
        """
        
        result = self.parser.extract_json_from_text(text_with_invalid_json)
        self.assertIsNone(result)
    
    def test_validate_schema(self):
        """Test walidacji schematu JSON."""
        # Poprawne dane zgodne ze schematem
        valid_data = {
            "trend": "bullish",
            "strength": 7,
            "key_levels": {
                "support": [1.0780, 1.0750],
                "resistance": [1.0850, 1.0880]
            },
            "recommendation": "buy",
            "explanation": "Rynek wykazuje silny trend wzrostowy."
        }
        
        # Schemat do walidacji
        schema = {
            "type": "object",
            "required": ["trend", "strength", "key_levels", "recommendation", "explanation"],
            "properties": {
                "trend": {
                    "type": "string",
                    "enum": ["bullish", "bearish", "neutral", "sideways", "ranging"]
                },
                "strength": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10
                }
            }
        }
        
        # Walidacja poprawnych danych
        result = self.parser.validate_schema(valid_data, schema)
        self.assertTrue(result)
        
        # Niepoprawne dane niezgodne ze schematem
        invalid_data = {
            "trend": "super_bullish",  # Wartość spoza enum
            "strength": 11,  # Wartość poza zakresem
            "key_levels": {
                "support": [1.0780, 1.0750],
                "resistance": [1.0850, 1.0880]
            },
            "recommendation": "buy",
            "explanation": "Rynek wykazuje silny trend wzrostowy."
        }
        
        # Walidacja niepoprawnych danych
        result = self.parser.validate_schema(invalid_data, schema)
        self.assertFalse(result)


class TestLLMEngine(unittest.TestCase):
    """Testy dla klasy LLMEngine."""
    
    def setUp(self):
        """Konfiguracja przed każdym testem."""
        # Mockowanie klienta Grok
        self.grok_mock = MagicMock()
        self.grok_mock.generate.return_value = """
        {
          "trend": "bullish",
          "strength": 7,
          "key_levels": {
            "support": [1.0780, 1.0750],
            "resistance": [1.0850, 1.0880]
          },
          "recommendation": "buy",
          "explanation": "Rynek wykazuje silny trend wzrostowy."
        }
        """
        
        # Dodanie mockowania metody generate_with_json_output
        self.grok_mock.generate_with_json_output.return_value = """
        {
          "trend": "bullish",
          "strength": 7,
          "key_levels": {
            "support": [1.0780, 1.0750],
            "resistance": [1.0850, 1.0880]
          },
          "recommendation": "buy",
          "explanation": "Rynek wykazuje silny trend wzrostowy."
        }
        """
        
        # Mockowanie MarketAnalyzer
        self.market_analyzer_mock = MagicMock()
        
        # Mockowanie LLMEngine
        with patch('LLM_Engine.llm_engine.GrokClient', return_value=self.grok_mock), \
             patch('LLM_Engine.llm_engine.MarketAnalyzer', return_value=self.market_analyzer_mock):
            self.engine = LLMEngine()
        
        # Przykładowe dane rynkowe
        self.market_data = {
            "symbol": "EURUSD",
            "timeframe": "H1",
            "current_price": 1.0750,
            "price_data": [
                {"time": "2023-06-01 12:00", "open": 1.0750, "high": 1.0765, "low": 1.0745, "close": 1.0760, "tick_volume": 1250},
                {"time": "2023-06-01 13:00", "open": 1.0760, "high": 1.0780, "low": 1.0755, "close": 1.0775, "tick_volume": 1300},
                {"time": "2023-06-01 14:00", "open": 1.0775, "high": 1.0785, "low": 1.0770, "close": 1.0780, "tick_volume": 1150},
            ],
            "indicators": {
                "MA(20)": [1.0720, 1.0725, 1.0730, 1.0735, 1.0740],
                "RSI(14)": [45.5, 48.2, 52.7, 58.3, 62.1],
                "MACD": [0.0012, 0.0015, 0.0018, 0.0022, 0.0025]
            }
        }
    
    @patch('LLM_Engine.llm_engine.GrokClient')
    @patch('LLM_Engine.llm_engine.MarketAnalyzer')
    def test_analyze_market(self, MockMarketAnalyzer, MockGrokClient):
        # Ustaw mock dla GrokClient
        mock_client = MockGrokClient.return_value
        mock_client.generate_with_json_output.return_value = {
            "trend": "bullish",
            "strength": 8,
            "volatility": "average",
            "description": "Trend wzrostowy z silnym momentum",
            "recommendation": "Czekaj na potwierdzenie wzrostowego setupu",
            "support_levels": [1.075, 1.070],
            "resistance_levels": [1.085, 1.090],
            "key_levels": [1.070, 1.075, 1.085, 1.090],
            "buy_signals": [195, 198],
            "sell_signals": [],
            "metadata": {}  # Dodane puste metadane, które zostaną uzupełnione przez LLMEngine
        }

        # Przykładowe dane rynkowe
        symbol = "EURUSD"
        timeframe = "H1"
        
        # Przygotowanie danych cenowych w formie listy słowników
        price_data = [
            {"time": "2023-06-01 12:00", "open": 1.080, "high": 1.082, "low": 1.079, "close": 1.081, "volume": 100},
            {"time": "2023-06-01 13:00", "open": 1.081, "high": 1.083, "low": 1.080, "close": 1.082, "volume": 120},
            {"time": "2023-06-01 14:00", "open": 1.082, "high": 1.084, "low": 1.081, "close": 1.083, "volume": 110},
            {"time": "2023-06-01 15:00", "open": 1.083, "high": 1.085, "low": 1.082, "close": 1.084, "volume": 130}
        ]
        
        # Przygotowanie słownika z wskaźnikami
        indicators = {
            "sma": {"SMA(20)": [1.075, 1.076, 1.077, 1.078]},
            "rsi": {"RSI(14)": [45, 48, 52, 55]},
            "macd": {"MACD(12,26,9)": {"macd": [0.001, 0.002, 0.003, 0.004], "signal": [0.0005, 0.001, 0.0015, 0.002]}}
        }
        
        # Patching metody _generate_cache_key, aby zawsze zwracała pusty wynik z cache
        with patch.object(LLMEngine, '_generate_cache_key', return_value='test_key'), \
             patch('LLM_Engine.llm_engine.CacheManager.get', return_value=None), \
             patch('LLM_Engine.llm_engine.CacheManager.set'):
            
            # Mockowanie ResponseParser
            with patch('LLM_Engine.llm_engine.ResponseParser.validate_market_analysis', 
                       return_value=mock_client.generate_with_json_output.return_value):
                
                # Utwórz instancję LLMEngine
                engine = LLMEngine()
                
                # Wywołaj analizę rynku z odpowiednimi parametrami
                result = engine.analyze_market(
                    symbol=symbol,
                    timeframe=timeframe,
                    price_data=price_data,
                    indicators=indicators
                )
                
                # Sprawdź, czy metoda generate_with_json_output została wywołana
                mock_client.generate_with_json_output.assert_called_once()
                
                # Sprawdź wyniki
                self.assertEqual(result["trend"], "bullish")
                self.assertEqual(result["strength"], 8)
                self.assertEqual(result["volatility"], "average")
                self.assertEqual(len(result["support_levels"]), 2)
                self.assertEqual(len(result["resistance_levels"]), 2)
                self.assertEqual(len(result["key_levels"]), 4)
                
                # Sprawdź, czy wynik zawiera wszystkie oczekiwane klucze
                expected_keys = ["trend", "strength", "volatility", "description", "recommendation", 
                               "support_levels", "resistance_levels", "key_levels", "buy_signals", "sell_signals", "metadata"]
                for key in expected_keys:
                    self.assertIn(key, result)
                
                # Sprawdź, czy metadata zawiera wymagane pola
                self.assertIn("symbol", result["metadata"])
                self.assertEqual(result["metadata"]["symbol"], symbol)
                self.assertIn("timeframe", result["metadata"])
                self.assertEqual(result["metadata"]["timeframe"], timeframe)
    
    def test_calculate_stop_loss(self):
        """Test obliczania poziomu stop loss."""
        # Mockowanie metody analyze_market, aby nie wywoływać jej bezpośrednio
        with patch.object(self.engine, 'analyze_market') as mock_analyze:
            # Ustawiamy wartość zwracaną przez analyze_market
            mock_analyze.return_value = {
                "trend": "bullish",
                "strength": 7,
                "key_levels": {
                    "support": [1.0730, 1.0700],
                    "resistance": [1.0780, 1.0800]
                },
                "recommendation": "buy",
                "explanation": "Rynek wykazuje silny trend wzrostowy."
            }
            
            # Ustawienie mocka dla grok_client
            self.grok_mock.generate_with_json_output.return_value = """
            {
              "stop_loss": 1.0720,
              "take_profit": 1.0800,
              "explanation": "Stop loss ustawiony pod kluczowym poziomem wsparcia."
            }
            """
            
            # Wywołujemy testowaną metodę dla pozycji BUY
            result = self.engine.calculate_stop_loss_take_profit(
                symbol=self.market_data["symbol"],
                position_type="buy",
                entry_price=1.0750,
                market_data=self.market_data
            )
            
            # Sprawdzenie czy wynik zawiera oczekiwane pola
            self.assertIn("stop_loss", result)
            
            # Sprawdzenie wartości
            self.assertIsInstance(result["stop_loss"], float)
    
    def test_calculate_take_profit(self):
        """Test obliczania poziomu take profit."""
        # Mockowanie metody analyze_market, aby nie wywoływać jej bezpośrednio
        with patch.object(self.engine, 'analyze_market') as mock_analyze:
            # Ustawiamy wartość zwracaną przez analyze_market
            mock_analyze.return_value = {
                "trend": "bullish",
                "strength": 7,
                "key_levels": {
                    "support": [1.0730, 1.0700],
                    "resistance": [1.0780, 1.0800]
                },
                "recommendation": "buy",
                "explanation": "Rynek wykazuje silny trend wzrostowy."
            }
            
            # Ustawienie mocka dla grok_client
            self.grok_mock.generate_with_json_output.return_value = """
            {
              "stop_loss": 1.0720,
              "take_profit": 1.0800,
              "explanation": "Take profit ustawiony na kluczowym poziomie oporu."
            }
            """
            
            # Wywołujemy testowaną metodę dla pozycji BUY
            result = self.engine.calculate_stop_loss_take_profit(
                symbol=self.market_data["symbol"],
                position_type="buy",
                entry_price=1.0750,
                market_data=self.market_data
            )
            
            # Sprawdzenie czy wynik zawiera oczekiwane pola
            self.assertIn("take_profit", result)
            
            # Sprawdzenie wartości
            self.assertIsInstance(result["take_profit"], float)
    
    def test_generate_trade_idea(self):
        """Test generowania pomysłu handlowego."""
        # Mockowanie metody analyze_market, aby nie wywoływać jej bezpośrednio
        with patch.object(self.engine, 'analyze_market') as mock_analyze:
            # Ustawiamy wartość zwracaną przez analyze_market
            mock_analyze.return_value = {
                "trend": "bullish",
                "strength": 7,
                "key_levels": {
                    "support": [1.0730, 1.0700],
                    "resistance": [1.0780, 1.0800]
                },
                "recommendation": "buy",
                "explanation": "Rynek wykazuje silny trend wzrostowy."
            }
            
            # Ustawienie mocka dla grok_client
            self.grok_mock.generate_with_json_output.return_value = """
            {
              "direction": "buy",
              "entry_price": 1.0750,
              "stop_loss": 1.0720,
              "take_profit": 1.0800,
              "risk_reward_ratio": 2.0,
              "explanation": "Kupuj ze względu na silny trend wzrostowy.",
              "confidence": "high"
            }
            """
            
            # Wywołujemy testowaną metodę
            result = self.engine.generate_trade_idea(self.market_data)
            
            # Sprawdzenie, czy wynik zawiera oczekiwane pola
            self.assertIn("direction", result)
            self.assertIn("stop_loss", result)
            self.assertIn("take_profit", result)
            self.assertIn("risk_reward_ratio", result)
            self.assertIn("metadata", result)
            
            # Sprawdzenie wartości
            self.assertIn(result["direction"], ["buy", "sell", "hold"])
            self.assertEqual(result["metadata"]["symbol"], "EURUSD")


if __name__ == '__main__':
    unittest.main() 
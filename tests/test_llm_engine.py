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
from typing import Dict, Any

# Dodanie ścieżki głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM_Engine.llm_engine import LLMEngine
from LLM_Engine.technical_indicators import TechnicalIndicators
from LLM_Engine.advanced_indicators import AdvancedIndicators
from LLM_Engine.response_parser import ResponseParserFactory
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


class TestResponseParser(ResponseParserFactory):
    def parse(self, response: str) -> Dict[str, Any]:
        """Implementacja metody parse dla testów."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"text": response}


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
          "explanation": "Rynek wykazuje silny trend wzrostowy.",
          "risk_assessment": {
            "level": "medium",
            "factors": ["Silny trend", "Bliskość oporu"],
            "recommendations": ["Ustaw SL poniżej wsparcia", "Częściowa realizacja zysków na oporze"]
          }
        }
        """
        
        # Mockowanie ResponseParserFactory
        self.parser_mock = MagicMock()
        self.parser_mock.parse.return_value = {
            "trend": "bullish",
            "strength": 7,
            "key_levels": {
                "support": [1.0780, 1.0750],
                "resistance": [1.0850, 1.0880]
            },
            "recommendation": "buy",
            "explanation": "Rynek wykazuje silny trend wzrostowy."
        }
        self.parser_mock.validate.return_value = (True, [])
        
        # Patch dla ResponseParserFactory
        self.parser_factory_patcher = patch('LLM_Engine.response_parser.ResponseParserFactory')
        self.parser_factory_mock = self.parser_factory_patcher.start()
        self.parser_factory_mock.get_parser.return_value = self.parser_mock
        
        # Mockowanie MarketAnalyzer
        self.market_analyzer_mock = MagicMock()
        self.market_analyzer_mock.analyze_trend.return_value = {
            "trend": "bullish",
            "strength": 7
        }
        
        # Patchowanie GrokClient i MarketAnalyzer
        patcher_grok = patch('LLM_Engine.llm_engine.GrokClient', return_value=self.grok_mock)
        patcher_market = patch('LLM_Engine.llm_engine.MarketAnalyzer', return_value=self.market_analyzer_mock)
        self.addCleanup(patcher_grok.stop)
        self.addCleanup(patcher_market.stop)
        patcher_grok.start()
        patcher_market.start()
        
        # Inicjalizacja silnika LLM
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

    def tearDown(self):
        """Czyszczenie po każdym teście."""
        self.parser_factory_patcher.stop()

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
            
            # Mockowanie ResponseParserFactory
            mock_parser = MagicMock()
            mock_parser.validate_market_analysis.return_value = mock_client.generate_with_json_output.return_value
            
            with patch('LLM_Engine.llm_engine.ResponseParserFactory.get_parser', return_value=mock_parser):
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
        # Przygotowanie danych testowych
        entry_price = 1.0800
        risk_level = "medium"
        trend = "bullish"
        support_levels = [1.0750, 1.0720]
        volatility = 0.0025

        # Obliczenie stop loss
        result = self.engine.calculate_stop_loss(
            entry_price=entry_price,
            risk_level=risk_level,
            trend=trend,
            support_levels=support_levels,
            volatility=volatility
        )
        
        # Sprawdzenie wyniku
        self.assertIn("stop_loss", result)
        self.assertIn("reason", result)
        self.assertIn("risk_multiplier", result)
        self.assertIn("based_on_support", result)
        
        # Dla risk_level="medium", mnożnik powinien być 1.5
        expected_atr_stop = entry_price - (volatility * 1.5)
        expected_atr_stop = round(expected_atr_stop, 5)
        
        # Sprawdzamy czy stop loss jest ustawiony na poziomie wsparcia lub ATR
        if result["based_on_support"]:
            self.assertEqual(result["stop_loss"], 1.0750)  # Najbliższy poziom wsparcia
            self.assertEqual(result["reason"], "Stop loss ustawiony na najbliższym poziomie wsparcia")
        else:
            self.assertEqual(result["stop_loss"], expected_atr_stop)
            self.assertEqual(result["reason"], "Stop loss ustawiony na 1.5x ATR poniżej ceny wejścia")
        
        self.assertEqual(result["risk_multiplier"], 1.5)
    
    def test_calculate_take_profit(self):
        """Test obliczania poziomu take profit."""
        # Przygotowanie danych testowych
        entry_price = 1.0800
        risk_reward = 2.0
        stop_loss = 1.0750
        resistance_levels = [1.0850, 1.0880]
        trend = "bullish"

        # Obliczenie take profit
        result = self.engine.calculate_take_profit(
            entry_price=entry_price,
            risk_reward=risk_reward,
            stop_loss=stop_loss,
            resistance_levels=resistance_levels,
            trend=trend
        )
        
        # Sprawdzenie wyniku
        self.assertIn("take_profit", result)
        self.assertIn("reason", result)
        self.assertIn("risk_reward", result)
        self.assertIn("based_on_resistance", result)
        
        # Obliczenie minimalnego take profit na podstawie R:R
        risk = abs(entry_price - stop_loss)  # 0.0050
        expected_min_tp = entry_price + (risk * risk_reward)  # 1.0800 + (0.0050 * 2.0) = 1.0900
        expected_min_tp = round(expected_min_tp, 5)
        
        # Sprawdzamy czy take profit jest ustawiony na poziomie oporu lub minimalnym R:R
        if result["based_on_resistance"]:
            self.assertEqual(result["take_profit"], 1.0880)  # Najbliższy poziom oporu
            self.assertEqual(result["reason"], "Take profit ustawiony na najbliższym poziomie oporu")
        else:
            self.assertEqual(result["take_profit"], expected_min_tp)
            self.assertEqual(result["reason"], "Take profit ustawiony dla R:R 2.0")
        
        # Sprawdzamy czy risk reward jest prawidłowy
        actual_rr = round(abs(result["take_profit"] - entry_price) / risk, 2)
        self.assertEqual(result["risk_reward"], actual_rr)
    
    @patch('LLM_Engine.llm_engine.GrokClient')
    @patch('LLM_Engine.llm_engine.ResponseParserFactory')
    def test_generate_trade_idea_complete_response(self, mock_parser_factory, mock_grok_client):
        """Test generowania pomysłu handlowego z kompletną odpowiedzią"""
        # Przygotowanie danych testowych
        market_analysis = {
            "trend": "bullish",
            "strength": 8,
            "support_levels": [1.0900, 1.0850],
            "resistance_levels": [1.1100, 1.1150],
            "volatility": "medium",
            "market_conditions": {
                "trend_strength": "strong",
                "momentum": "positive"
            }
        }
        
        risk_assessment = {
            "level": "medium",
            "factors": ["Silny trend wzrostowy", "Dobra płynność"],
            "total_risk": "acceptable"
        }
        
        current_price = 1.1000
        
        mock_response = {
            "direction": "buy",
            "entry_price": 1.1000,
            "stop_loss": 1.0900,
            "take_profit": 1.1300,
            "risk_reward": 3.0,
            "metadata": {
                "timestamp": "2024-03-21T10:00:00",
                "model": "grok-v2",
                "market_conditions": {
                    "trend_strength": "strong",
                    "momentum": "positive"
                },
                "risk_level": "medium"
            }
        }
        
        mock_grok_client.return_value.generate_with_json_output.return_value = mock_response
        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_response
        mock_parser_factory.get_parser.return_value = mock_parser
        
        # Wywołanie testowanej metody
        result = self.engine.generate_trade_idea(
            market_analysis=market_analysis,
            risk_assessment=risk_assessment,
            current_price=current_price
        )
        
        # Sprawdzenie wyników
        self.assertEqual(result["direction"], "buy")
        self.assertEqual(result["entry_price"], 1.1000)
        self.assertEqual(result["stop_loss"], 1.0900)
        self.assertEqual(result["take_profit"], 1.1300)
        self.assertEqual(result["risk_reward"], 3.0)
        self.assertEqual(result["metadata"]["market_conditions"]["trend_strength"], "strong")
        self.assertEqual(result["metadata"]["risk_level"], "medium")

    @patch('LLM_Engine.llm_engine.GrokClient')
    @patch('LLM_Engine.llm_engine.ResponseParserFactory')
    def test_generate_trade_idea_incomplete_response(self, mock_parser_factory, mock_grok_client):
        """Test generowania pomysłu handlowego z niekompletną odpowiedzią"""
        # Przygotowanie danych testowych
        market_analysis = {
            "trend": "bearish",
            "strength": 6,
            "support_levels": [1.0900, 1.0850],
            "resistance_levels": [1.1100, 1.1150],
            "volatility": "high",
            "market_conditions": {
                "trend_strength": "moderate",
                "momentum": "negative"
            }
        }
        
        risk_assessment = {
            "level": "medium",
            "factors": ["Podwyższona zmienność"],
            "total_risk": "moderate"
        }
        
        current_price = 1.1000
        
        # Przygotowanie niekompletnej odpowiedzi
        mock_response = {
            "direction": "sell",
            "entry_price": 1.1000,
            "metadata": {
                "timestamp": "2024-03-21T10:00:00",
                "model": "grok-v2",
                "market_conditions": {
                    "trend_strength": "moderate",
                    "momentum": "negative"
                },
                "risk_level": "medium"
            }
        }
        
        mock_grok_client.return_value.generate_with_json_output.return_value = mock_response
        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_response
        mock_parser_factory.get_parser.return_value = mock_parser
        
        # Mockowanie metod calculate_stop_loss_take_profit
        with patch.object(self.engine, 'calculate_stop_loss_take_profit') as mock_calc:
            mock_calc.return_value = {
                "stop_loss": 1.1100,
                "take_profit": 1.0800,
                "atr_value": 0.0050,
                "risk_pips": 100,
                "reward_pips": 200
            }
            
            # Wywołanie testowanej metody
            result = self.engine.generate_trade_idea(
                market_analysis=market_analysis,
                risk_assessment=risk_assessment,
                current_price=current_price
            )
        
        # Sprawdzenie wyników
        self.assertEqual(result["direction"], "sell")
        self.assertEqual(result["entry_price"], 1.1000)
        self.assertEqual(result["stop_loss"], 1.1100)
        self.assertEqual(result["take_profit"], 1.0800)
        self.assertEqual(result["metadata"]["market_conditions"]["trend_strength"], "moderate")
        self.assertEqual(result["metadata"]["risk_level"], "medium")

    @patch('LLM_Engine.llm_engine.GrokClient')
    @patch('LLM_Engine.llm_engine.ResponseParserFactory')
    def test_generate_trade_idea_hold_signal(self, mock_parser_factory, mock_grok_client):
        """Test generowania pomysłu handlowego gdy trend jest neutralny"""
        # Przygotowanie danych testowych
        market_analysis = {
            "trend": "neutral",
            "strength": 3,
            "support_levels": [1.0900, 1.0850],
            "resistance_levels": [1.1100, 1.1150],
            "volatility": "low",
            "market_conditions": {
                "trend_strength": "weak",
                "momentum": "neutral"
            }
        }
        
        risk_assessment = {
            "level": "high",
            "factors": ["Brak wyraźnego trendu", "Niska płynność"],
            "total_risk": "high"
        }
        
        current_price = 1.1000
        
        mock_response = {
            "direction": "hold",
            "entry_price": 0.0,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "risk_reward": 0.0,
            "metadata": {
                "timestamp": "2024-03-21T10:00:00",
                "model": "grok-v2",
                "market_conditions": {
                    "trend_strength": "weak",
                    "momentum": "neutral"
                },
                "risk_level": "high"
            }
        }
        
        mock_grok_client.return_value.generate_with_json_output.return_value = mock_response
        mock_parser = MagicMock()
        mock_parser.parse.return_value = mock_response
        mock_parser_factory.get_parser.return_value = mock_parser
        
        # Wywołanie testowanej metody
        result = self.engine.generate_trade_idea(
            market_analysis=market_analysis,
            risk_assessment=risk_assessment,
            current_price=current_price
        )
        
        # Sprawdzenie wyników
        self.assertEqual(result["direction"], "hold")
        self.assertEqual(result["entry_price"], 0.0)
        self.assertEqual(result["stop_loss"], 0.0)
        self.assertEqual(result["take_profit"], 0.0)
        self.assertEqual(result["risk_reward"], 0.0)
        self.assertEqual(result["metadata"]["market_conditions"]["trend_strength"], "weak")
        self.assertEqual(result["metadata"]["risk_level"], "high")


if __name__ == '__main__':
    unittest.main() 
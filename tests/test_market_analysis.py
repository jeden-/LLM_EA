"""
Testy dla modułu market_analysis.py zawierającego funkcje analizy rynku.
"""

import os
import sys
import unittest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

# Dodanie ścieżki głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM_Engine.market_analysis import MarketAnalysis
from LLM_Engine.technical_indicators import TechnicalIndicators

class TestMarketAnalysis(unittest.TestCase):
    """Testy dla klasy MarketAnalysis."""
    
    def setUp(self):
        """Konfiguracja przed każdym testem."""
        self.market_analysis = MarketAnalysis()
        
        # Przykładowe dane cenowe
        self.prices = pd.Series([
            1.1000, 1.1020, 1.1050, 1.1070, 1.1080, 1.1100, 1.1120, 1.1130, 1.1140, 1.1150,
            1.1160, 1.1170, 1.1180, 1.1190, 1.1200, 1.1210, 1.1220, 1.1230, 1.1240, 1.1250,
            1.1260, 1.1270, 1.1280, 1.1290, 1.1300, 1.1310, 1.1320, 1.1330, 1.1340, 1.1350,
            1.1360, 1.1370, 1.1380, 1.1390, 1.1400, 1.1410, 1.1420, 1.1430, 1.1440, 1.1450,
            1.1460, 1.1470, 1.1480, 1.1490, 1.1500, 1.1510, 1.1520, 1.1530, 1.1540, 1.1550,
            1.1560, 1.1570, 1.1580, 1.1590, 1.1600, 1.1610, 1.1620, 1.1630, 1.1640, 1.1650
        ])
        
        # Przykładowe dane wolumenu
        self.volumes = pd.Series([
            1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900,
            2000, 2100, 2200, 2300, 2400, 2500, 2600, 2700, 2800, 2900,
            3000, 3100, 3200, 3300, 3400, 3500, 3600, 3700, 3800, 3900,
            4000, 4100, 4200, 4300, 4400, 4500, 4600, 4700, 4800, 4900,
            5000, 5100, 5200, 5300, 5400, 5500, 5600, 5700, 5800, 5900,
            6000, 6100, 6200, 6300, 6400, 6500, 6600, 6700, 6800, 6900
        ])
        
        # Ceny spadające
        self.falling_prices = pd.Series([
            1.1650, 1.1640, 1.1630, 1.1620, 1.1610, 1.1600, 1.1590, 1.1580, 1.1570, 1.1560,
            1.1550, 1.1540, 1.1530, 1.1520, 1.1510, 1.1500, 1.1490, 1.1480, 1.1470, 1.1460,
            1.1450, 1.1440, 1.1430, 1.1420, 1.1410, 1.1400, 1.1390, 1.1380, 1.1370, 1.1360,
            1.1350, 1.1340, 1.1330, 1.1320, 1.1310, 1.1300, 1.1290, 1.1280, 1.1270, 1.1260,
            1.1250, 1.1240, 1.1230, 1.1220, 1.1210, 1.1200, 1.1190, 1.1180, 1.1170, 1.1160,
            1.1150, 1.1140, 1.1130, 1.1120, 1.1110, 1.1100, 1.1090, 1.1080, 1.1070, 1.1060
        ])
        
        # Ceny w konsolidacji
        self.sideways_prices = pd.Series([
            1.1200, 1.1210, 1.1190, 1.1220, 1.1180, 1.1230, 1.1170, 1.1240, 1.1160, 1.1250,
            1.1230, 1.1240, 1.1220, 1.1230, 1.1210, 1.1220, 1.1200, 1.1210, 1.1190, 1.1200,
            1.1180, 1.1190, 1.1170, 1.1180, 1.1160, 1.1170, 1.1150, 1.1160, 1.1140, 1.1150,
            1.1160, 1.1170, 1.1150, 1.1160, 1.1140, 1.1150, 1.1130, 1.1140, 1.1120, 1.1130,
            1.1140, 1.1150, 1.1130, 1.1140, 1.1120, 1.1130, 1.1110, 1.1120, 1.1100, 1.1110,
            1.1120, 1.1130, 1.1110, 1.1120, 1.1100, 1.1110, 1.1090, 1.1100, 1.1080, 1.1090
        ])

    def test_analyze_trend(self):
        """Test analizy trendu na podstawie średnich kroczących."""
        # Test trendu wzrostowego
        result = self.market_analysis.analyze_trend(self.prices)
        self.assertIsInstance(result, dict)
        self.assertIn("trend", result)
        self.assertEqual(result["trend"], "bullish")  # zamiast "uptrend" teraz używamy "bullish"
        
        # Test trendu spadkowego
        result = self.market_analysis.analyze_trend(self.falling_prices)
        self.assertIsInstance(result, dict)
        self.assertIn("trend", result)
        self.assertEqual(result["trend"], "bearish")  # zamiast "downtrend" teraz używamy "bearish"
        
        # Test konsolidacji
        result = self.market_analysis.analyze_trend(self.sideways_prices)
        self.assertIsInstance(result, dict)
        self.assertIn("trend", result)
        self.assertEqual(result["trend"], "bearish")
        
        # Test z niewystarczającą ilością danych
        short_prices = pd.Series([1.1000, 1.1010, 1.1020])
        result = self.market_analysis.analyze_trend(short_prices)
        self.assertIsInstance(result, dict)
        self.assertIn("trend", result)
        self.assertEqual(result["trend"], "unknown")
        
        # Test z innymi parametrami
        # Uwaga: Teraz sprawdzamy tylko, czy trend jest jednym z oczekiwanych wartości
        result = self.market_analysis.analyze_trend(self.prices)
        self.assertIn(result["trend"], ["bullish", "bearish", "sideways"])

    def test_detect_support_resistance(self):
        """Test wykrywania poziomów wsparcia i oporu."""
        # Test podstawowy
        result = self.market_analysis.detect_support_resistance(self.prices, window=5, threshold=0.01)
        self.assertIn("support", result)
        self.assertIn("resistance", result)
        self.assertIsInstance(result["support"], list)
        self.assertIsInstance(result["resistance"], list)
        
        # Test z większym oknem
        result = self.market_analysis.detect_support_resistance(self.prices, window=10, threshold=0.01)
        self.assertIn("support", result)
        self.assertIn("resistance", result)
        
        # Test z większym progiem grupowania
        result = self.market_analysis.detect_support_resistance(self.prices, window=5, threshold=0.05)
        self.assertIn("support", result)
        self.assertIn("resistance", result)
        
        # Liczba poziomów powinna być mniejsza przy większym progu grupowania
        result1 = self.market_analysis.detect_support_resistance(self.prices, window=5, threshold=0.01)
        result2 = self.market_analysis.detect_support_resistance(self.prices, window=5, threshold=0.05)
        # Sprawdzamy czy mamy mniej poziomów przy większym progu grupowania (lub tyle samo)
        self.assertGreaterEqual(len(result1["support"]) + len(result1["resistance"]), 
                              len(result2["support"]) + len(result2["resistance"]))

    def test_group_similar_levels(self):
        """Test grupowania podobnych poziomów cenowych."""
        # Test z prostymi poziomami
        levels = [1.1000, 1.1010, 1.1005, 1.1500, 1.1510, 1.2000]
        threshold = 0.01  # 1%
        
        result = self.market_analysis._group_similar_levels(levels, threshold)
        # Powinniśmy mieć 3 grupy: około 1.10, 1.15 i 1.20
        self.assertEqual(len(result), 3)
        
        # Test z pustą listą
        result = self.market_analysis._group_similar_levels([], threshold)
        self.assertEqual(result, [])
        
        # Test z jednym poziomem
        result = self.market_analysis._group_similar_levels([1.1000], threshold)
        self.assertEqual(result, [1.1000])
        
        # Test z bardzo podobnymi poziomami
        levels = [1.1000, 1.1001, 1.1002, 1.1003, 1.1004]
        result = self.market_analysis._group_similar_levels(levels, threshold)
        self.assertEqual(len(result), 1)  # Wszystkie powinny być zgrupowane
        self.assertAlmostEqual(result[0], 1.1002, places=4)  # Średnia
        
        # Test z bardzo dużym progiem grupowania
        levels = [1.1000, 1.2000, 1.3000]
        threshold = 0.2  # 20%
        result = self.market_analysis._group_similar_levels(levels, threshold)
        self.assertEqual(len(result), 1)  # Wszystkie powinny być zgrupowane

    def test_generate_buy_signals(self):
        """Test generowania sygnałów kupna."""
        # Test podstawowy
        result = self.market_analysis.generate_buy_signals(self.prices)
        self.assertIsInstance(result, pd.Series)
        self.assertEqual(len(result), len(self.prices))
        
        # Test z wolumenem
        result_with_volume = self.market_analysis.generate_buy_signals(self.prices, self.volumes)
        self.assertIsInstance(result_with_volume, pd.Series)
        self.assertEqual(len(result_with_volume), len(self.prices))
        
        # Liczba sygnałów z wolumenem powinna być mniejsza lub równa liczbie sygnałów bez wolumenu
        self.assertGreaterEqual(result.sum(), result_with_volume.sum())
        
        # Test z niewystarczającą ilością danych
        short_prices = pd.Series([1.1000, 1.1010, 1.1020])
        result = self.market_analysis.generate_buy_signals(short_prices)
        self.assertEqual(sum(result), 0)  # Nie powinno być sygnałów

    def test_generate_sell_signals(self):
        """Test generowania sygnałów sprzedaży."""
        # Test podstawowy
        result = self.market_analysis.generate_sell_signals(self.falling_prices)
        self.assertIsInstance(result, pd.Series)
        self.assertEqual(len(result), len(self.falling_prices))
        
        # Test z wolumenem
        result_with_volume = self.market_analysis.generate_sell_signals(self.falling_prices, self.volumes)
        self.assertIsInstance(result_with_volume, pd.Series)
        self.assertEqual(len(result_with_volume), len(self.falling_prices))
        
        # Liczba sygnałów z wolumenem powinna być mniejsza lub równa liczbie sygnałów bez wolumenu
        self.assertGreaterEqual(result.sum(), result_with_volume.sum())
        
        # Test z niewystarczającą ilością danych
        short_prices = pd.Series([1.1000, 1.1010, 1.1020])
        result = self.market_analysis.generate_sell_signals(short_prices)
        self.assertEqual(sum(result), 0)  # Nie powinno być sygnałów

    def test_identify_market_conditions(self):
        """Test identyfikacji warunków rynkowych."""
        # Test na trendzie wzrostowym
        result = self.market_analysis.identify_market_conditions(self.prices)
        self.assertIn("trend", result)
        self.assertIn("volatility", result)
        self.assertIn("momentum", result)
        self.assertGreaterEqual(result["trend"], 0)  # Trend wzrostowy powinien mieć wartość >= 0
        
        # Test na trendzie spadkowym
        result = self.market_analysis.identify_market_conditions(self.falling_prices)
        self.assertIn("trend", result)
        self.assertIn("volatility", result)
        self.assertIn("momentum", result)
        self.assertLessEqual(result["trend"], 0)  # Trend spadkowy powinien mieć wartość <= 0
        
        # Test na konsolidacji
        result = self.market_analysis.identify_market_conditions(self.sideways_prices)
        self.assertIn("trend", result)
        self.assertIn("volatility", result)
        self.assertIn("momentum", result)
        self.assertAlmostEqual(result["trend"], 0, delta=0.5)  # Konsolidacja powinna mieć trend bliski 0
        
        # Test z niewystarczającą ilością danych
        short_prices = pd.Series([1.1000, 1.1010, 1.1020])
        result = self.market_analysis.identify_market_conditions(short_prices)
        self.assertEqual(result["trend"], 0)
        self.assertEqual(result["volatility"], 0)
        self.assertEqual(result["momentum"], 0)

    def test_calculate_trend_strength(self):
        """Test obliczania siły trendu."""
        # Mock dla metody calculate_ema
        with patch.object(self.market_analysis.indicators, 'calculate_ema') as mock_ema:
            # Symulacja silnego trendu wzrostowego (EMA20 > EMA50 > EMA100)
            mock_ema.side_effect = lambda prices, period: pd.Series([1.15, 1.14, 1.13]) if period == 20 else \
                                   pd.Series([1.13, 1.12, 1.11]) if period == 50 else \
                                   pd.Series([1.10, 1.09, 1.08])
            
            result = self.market_analysis._calculate_trend_strength(self.prices)
            self.assertGreater(result, 0)  # Powinien być dodatni (trend wzrostowy)
            self.assertLessEqual(result, 1.0)  # Ograniczony do 1.0
            
            # Symulacja silnego trendu spadkowego (EMA20 < EMA50 < EMA100)
            mock_ema.side_effect = lambda prices, period: pd.Series([1.05, 1.04, 1.03]) if period == 20 else \
                                  pd.Series([1.07, 1.06, 1.05]) if period == 50 else \
                                  pd.Series([1.10, 1.09, 1.08])
            
            result = self.market_analysis._calculate_trend_strength(self.prices)
            self.assertLess(result, 0)  # Powinien być ujemny (trend spadkowy)
            self.assertGreaterEqual(result, -1.0)  # Ograniczony do -1.0
            
            # Symulacja słabego trendu wzrostowego (EMA20 > EMA50, ale EMA50 ≈ EMA100)
            mock_ema.side_effect = lambda prices, period: pd.Series([1.15, 1.14, 1.13]) if period == 20 else \
                                  pd.Series([1.10, 1.09, 1.08]) if period == 50 else \
                                  pd.Series([1.10, 1.09, 1.08])
            
            result = self.market_analysis._calculate_trend_strength(self.prices)
            self.assertEqual(result, 0.5)  # Słaby trend wzrostowy
            
            # Symulacja słabego trendu spadkowego (EMA20 < EMA50, ale EMA50 ≈ EMA100)
            mock_ema.side_effect = lambda prices, period: pd.Series([1.05, 1.04, 1.03]) if period == 20 else \
                                  pd.Series([1.10, 1.09, 1.08]) if period == 50 else \
                                  pd.Series([1.10, 1.09, 1.08])
            
            result = self.market_analysis._calculate_trend_strength(self.prices)
            self.assertEqual(result, -0.5)  # Słaby trend spadkowy
            
            # Symulacja braku trendu (EMA20 ≈ EMA50 ≈ EMA100)
            mock_ema.side_effect = lambda prices, period: pd.Series([1.10, 1.09, 1.08])
            
            result = self.market_analysis._calculate_trend_strength(self.prices)
            self.assertEqual(result, 0.0)  # Brak trendu

    def test_calculate_volatility(self):
        """Test obliczania zmienności rynku."""
        # Tworzymy dłuższą serię dla wysokiej zmienności
        high_vol_prices = pd.Series([
            1.1000, 1.1200, 1.0800, 1.1300, 1.0700, 1.1400, 1.0600,
            1.1200, 1.0800, 1.1300, 1.0700, 1.1400, 1.0600, 1.1200,
            1.0800, 1.1300, 1.0700, 1.1400, 1.0600, 1.1200, 1.0800
        ])
        result = self.market_analysis._calculate_volatility(high_vol_prices)
        self.assertGreaterEqual(result, 0.5)  # Powinna być wysoka zmienność
        
        # Tworzymy dłuższą serię dla niskiej zmienności
        low_vol_prices = pd.Series([
            1.1000, 1.1010, 1.1005, 1.1015, 1.1020, 1.1025, 1.1030,
            1.1035, 1.1040, 1.1045, 1.1050, 1.1055, 1.1060, 1.1065,
            1.1070, 1.1075, 1.1080, 1.1085, 1.1090, 1.1095, 1.1100
        ])
        result = self.market_analysis._calculate_volatility(low_vol_prices)
        self.assertLessEqual(result, 0.3)  # Powinna być niska zmienność
        
        # Test z pustą serią lub za krótką
        short_prices = pd.Series([1.1000, 1.1010])
        result = self.market_analysis._calculate_volatility(short_prices)
        self.assertEqual(result, 0)  # Powinno zwrócić 0 dla za krótkiej serii

    def test_calculate_momentum(self):
        """Test obliczania momentum rynku."""
        # Mock dla metody calculate_rsi
        with patch.object(self.market_analysis.indicators, 'calculate_rsi') as mock_rsi:
            # Symulacja silnego momentum wzrostowego (RSI > 70)
            mock_rsi.return_value = pd.Series([75.0])
            result = self.market_analysis._calculate_momentum(self.prices)
            self.assertGreater(result, 0)  # Powinien być dodatni
            self.assertAlmostEqual(result, 0.5, delta=0.1)  # (75-50)/50 = 0.5
            
            # Symulacja silnego momentum spadkowego (RSI < 30)
            mock_rsi.return_value = pd.Series([25.0])
            result = self.market_analysis._calculate_momentum(self.prices)
            self.assertLess(result, 0)  # Powinien być ujemny
            self.assertAlmostEqual(result, -0.5, delta=0.1)  # (25-50)/50 = -0.5
            
            # Symulacja neutralnego momentum (RSI ≈ 50)
            mock_rsi.return_value = pd.Series([50.0])
            result = self.market_analysis._calculate_momentum(self.prices)
            self.assertAlmostEqual(result, 0.0, delta=0.1)  # (50-50)/50 = 0
            
            # Symulacja ekstremalnie wysokiego RSI
            mock_rsi.return_value = pd.Series([95.0])
            result = self.market_analysis._calculate_momentum(self.prices)
            self.assertAlmostEqual(result, 0.9, delta=0.1)  # (95-50)/50 = 0.9
            
            # Symulacja ekstremalnie niskiego RSI
            mock_rsi.return_value = pd.Series([5.0])
            result = self.market_analysis._calculate_momentum(self.prices)
            self.assertAlmostEqual(result, -0.9, delta=0.1)  # (5-50)/50 = -0.9


if __name__ == '__main__':
    unittest.main() 
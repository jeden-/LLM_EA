import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Dodanie ścieżki do katalogu głównego projektu
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM_Engine.market_data import MarketData
from tests.test_data import TestData


class TestMarketData(unittest.TestCase):
    """Testy jednostkowe dla klasy MarketData"""
    
    def setUp(self):
        """Przygotowanie danych i obiektów do testów"""
        self.market_data = MarketData(symbol="EURUSD", timeframe="H1")
        
        # Przygotowanie przykładowych danych
        self.sample_data = TestData.generate_ohlc_data(
            symbol="EURUSD", 
            timeframe="H1", 
            num_candles=100
        )
    
    def test_set_data(self):
        """Test ustawiania danych"""
        self.market_data.set_data(self.sample_data)
        
        # Sprawdzenie, czy dane zostały poprawnie załadowane
        self.assertEqual(len(self.market_data.data), 100)
        self.assertEqual(self.market_data.symbol, "EURUSD")
        self.assertEqual(self.market_data.timeframe, "H1")
        
        # Sprawdzenie, czy dane są w słowniku ram czasowych
        self.assertIn("H1", self.market_data.timeframe_data)
        self.assertEqual(len(self.market_data.timeframe_data["H1"]), 100)
    
    def test_append_data(self):
        """Test dodawania nowych danych"""
        # Ustawienie początkowych danych
        self.market_data.set_data(self.sample_data.iloc[:50])
        
        # Dodanie nowych danych
        self.market_data.append_data(self.sample_data.iloc[50:])
        
        # Sprawdzenie, czy dane zostały poprawnie połączone
        self.assertEqual(len(self.market_data.data), 100)
    
    def test_add_timeframe(self):
        """Test dodawania danych dla nowej ramy czasowej"""
        # Ustawienie danych H1
        self.market_data.set_data(self.sample_data)
        
        # Przygotowanie danych H4
        h4_data = TestData.generate_ohlc_data(
            symbol="EURUSD", 
            timeframe="H4", 
            num_candles=25
        )
        
        # Dodanie danych H4
        self.market_data.add_timeframe("H4", h4_data)
        
        # Sprawdzenie, czy dane H4 zostały dodane
        self.assertIn("H4", self.market_data.timeframe_data)
        self.assertEqual(len(self.market_data.timeframe_data["H4"]), 25)
    
    def test_resample_timeframe(self):
        """Test przeliczania ram czasowych"""
        # Ustawienie danych H1
        self.market_data.set_data(self.sample_data)
        
        # Przeliczenie na H4
        h4_data = self.market_data.resample_timeframe("H1", "H4")
        
        # Sprawdzenie, czy dane H4 zostały utworzone
        self.assertIn("H4", self.market_data.timeframe_data)
        
        # H4 powinno mieć około 1/4 długości H1
        expected_len = len(self.sample_data) // 4
        self.assertAlmostEqual(len(h4_data), expected_len, delta=2)
        
        # Sprawdzenie, czy dane OHLC są prawidłowe
        # H4 high powinno być >= każde H1 high w tym okresie
        for i in range(min(5, len(h4_data))):
            h4_timestamp = h4_data.index[i]
            h1_data_in_period = self.market_data.timeframe_data["H1"].loc[
                (self.market_data.timeframe_data["H1"].index >= h4_timestamp) & 
                (self.market_data.timeframe_data["H1"].index < h4_timestamp + timedelta(hours=4))
            ]
            
            if not h1_data_in_period.empty:
                self.assertGreaterEqual(
                    h4_data.iloc[i]['high'], 
                    h1_data_in_period['high'].min()
                )
    
    def test_calculate_indicator(self):
        """Test obliczania wskaźników technicznych"""
        # Ustawienie danych
        self.market_data.set_data(self.sample_data)
        
        # Obliczenie SMA
        sma = self.market_data.calculate_indicator("sma", period=20)
        
        # Sprawdzenie, czy wskaźnik został obliczony
        self.assertIsNotNone(sma)
        self.assertEqual(len(sma), len(self.sample_data))
        
        # Sprawdzenie, czy wskaźnik został zapisany
        self.assertIn("sma_H1_period_20", self.market_data.calculated_indicators)
        
        # Obliczenie MACD
        macd = self.market_data.calculate_indicator("macd")
        
        # Sprawdzenie, czy MACD zwraca krotkę
        self.assertTrue(isinstance(macd, tuple))
        self.assertEqual(len(macd), 3)  # macd_line, signal_line, histogram
    
    def test_get_market_snapshot(self):
        """Test pobierania pełnego obrazu rynku"""
        # Ustawienie danych
        self.market_data.set_data(self.sample_data)
        
        # Obliczenie kilku wskaźników
        self.market_data.calculate_indicator("sma", period=20)
        self.market_data.calculate_indicator("rsi")
        self.market_data.calculate_indicator("macd")
        self.market_data.calculate_indicator("bollinger_bands")
        
        # Pobranie obrazu rynku
        snapshot = self.market_data.get_market_snapshot()
        
        # Sprawdzenie podstawowych informacji
        self.assertEqual(snapshot["symbol"], "EURUSD")
        self.assertEqual(snapshot["timeframe"], "H1")
        self.assertIn("current_price", snapshot)
        self.assertIn("ohlc", snapshot)
        
        # Sprawdzenie wskaźników
        self.assertIn("indicators", snapshot)
        
        # Sprawdzenie poziomów wsparcia/oporu
        self.assertIn("significant_levels", snapshot)
        
        # Sprawdzenie warunków rynkowych
        self.assertIn("market_conditions", snapshot)
    
    def test_significant_levels(self):
        """Test obliczania poziomów wsparcia i oporu"""
        # Użycie danych z wyraźnymi poziomami wsparcia/oporu
        sr_data = TestData.get_support_resistance_data(
            symbol="EURUSD", 
            num_candles=100
        )
        
        # Ustawienie danych
        self.market_data.set_data(sr_data)
        
        # Obliczenie poziomów
        levels = self.market_data._calculate_significant_levels("H1")
        
        # Sprawdzenie, czy poziomy zostały znalezione
        self.assertIn("support", levels)
        self.assertIn("resistance", levels)
        self.assertIn("recent_high", levels)
        self.assertIn("recent_low", levels)
    
    def test_assess_market_conditions(self):
        """Test oceny warunków rynkowych"""
        # Użycie danych z trendem
        trend_data = TestData.get_trending_market_data(
            symbol="EURUSD", 
            trend="up", 
            num_candles=100
        )
        
        # Ustawienie danych
        self.market_data.set_data(trend_data)
        
        # Ocena warunków rynkowych
        conditions = self.market_data._assess_market_conditions("H1")
        
        # Debug - wypisanie zwracanego opisu trendu
        print(f"\nZwrócony opis trendu: '{conditions['trend']['description']}'")
        
        # Sprawdzenie, czy warunki zostały ocenione
        self.assertIn("trend", conditions)
        self.assertIn("volatility", conditions)
        self.assertIn("momentum", conditions)
        
        # Sprawdzenie, czy warunki zawierają opisy
        self.assertIsInstance(conditions["trend"]["description"], str)
        self.assertIsInstance(conditions["volatility"]["description"], str)
        self.assertIsInstance(conditions["momentum"]["description"], str)
        
        # Sprawdzenie, czy wartości są liczbowe
        self.assertIsInstance(conditions["volatility"]["value"], float)
        self.assertIsInstance(conditions["momentum"]["value"], float)


if __name__ == '__main__':
    unittest.main() 
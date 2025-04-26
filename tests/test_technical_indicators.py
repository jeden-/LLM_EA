import unittest
import pandas as pd
import numpy as np
import sys
import os

# Dodanie ścieżki do katalogu głównego projektu
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM_Engine.technical_indicators import TechnicalIndicators


class TestData:
    """Klasa pomocnicza do generowania danych testowych dla różnych scenariuszy rynkowych"""
    
    @staticmethod
    def generate_uptrend_data(length=50):
        """Generuje dane dla trendu wzrostowego"""
        np.random.seed(42)  # Dla powtarzalności wyników
        base = np.linspace(100, 200, length)
        noise = np.random.normal(0, 5, length)
        prices = pd.Series(base + noise)
        return prices
    
    @staticmethod
    def generate_downtrend_data(length=50):
        """Generuje dane dla trendu spadkowego"""
        np.random.seed(43)  # Dla powtarzalności wyników
        base = np.linspace(200, 100, length)
        noise = np.random.normal(0, 5, length)
        prices = pd.Series(base + noise)
        return prices
    
    @staticmethod
    def generate_ranging_data(length=50):
        """Generuje dane dla rynku bez wyraźnego trendu"""
        np.random.seed(44)  # Dla powtarzalności wyników
        base = np.full(length, 150)
        noise = np.random.normal(0, 10, length)
        prices = pd.Series(base + noise)
        return prices


class TestTechnicalIndicators(unittest.TestCase):
    """Testy jednostkowe dla klasy TechnicalIndicators"""
    
    def setUp(self):
        """Przygotowanie danych i obiektów do testów"""
        self.indicators = TechnicalIndicators()
        
        # Przygotowanie danych testowych dla różnych scenariuszy rynkowych
        self.uptrend_data = TestData.generate_uptrend_data()
        self.downtrend_data = TestData.generate_downtrend_data()
        self.ranging_data = TestData.generate_ranging_data()
    
    def test_sma_calculation(self):
        """Test obliczania Simple Moving Average (SMA)"""
        # Test na danych z trendem wzrostowym
        sma_up = self.indicators.calculate_sma(self.uptrend_data, 10)
        
        # Sprawdzenie, czy pierwszych (period-1) wartości to NaN
        self.assertTrue(np.isnan(sma_up.iloc[0]))
        self.assertTrue(np.isnan(sma_up.iloc[8]))
        self.assertFalse(np.isnan(sma_up.iloc[9]))
        
        # Sprawdzenie, czy SMA podąża za trendem
        self.assertLess(sma_up.iloc[15], sma_up.iloc[30])
        
        # Test na danych z trendem spadkowym
        sma_down = self.indicators.calculate_sma(self.downtrend_data, 10)
        self.assertGreater(sma_down.iloc[15], sma_down.iloc[30])
        
        # Sprawdzenie zgodności SMA z ręczną kalkulacją
        manual_sma = self.uptrend_data.iloc[10:20].mean()
        self.assertAlmostEqual(sma_up.iloc[19], manual_sma, places=5)
    
    def test_ema_calculation(self):
        """Test obliczania Exponential Moving Average (EMA)"""
        # Test na danych z trendem wzrostowym
        ema_up_short = self.indicators.calculate_ema(self.uptrend_data, 5)
        ema_up_long = self.indicators.calculate_ema(self.uptrend_data, 20)
        
        # Sprawdzenie, czy wartości są zdefiniowane
        self.assertFalse(np.isnan(ema_up_short.iloc[4]))
        self.assertFalse(np.isnan(ema_up_long.iloc[19]))
        
        # Sprawdzenie, czy krótszy EMA jest bardziej zmienny niż dłuższy
        ema_short_volatility = ema_up_short.iloc[20:].std()
        ema_long_volatility = ema_up_long.iloc[20:].std()
        self.assertGreater(ema_short_volatility, ema_long_volatility)
        
        # Sprawdzenie zgodności EMA z danymi - czy podąża za trendem
        self.assertLess(ema_up_long.iloc[25], ema_up_long.iloc[40])
    
    def test_rsi_calculation(self):
        """Test obliczania Relative Strength Index (RSI)"""
        # Testy na różnych typach danych
        rsi_up = self.indicators.calculate_rsi(self.uptrend_data)
        rsi_down = self.indicators.calculate_rsi(self.downtrend_data)
        rsi_ranging = self.indicators.calculate_rsi(self.ranging_data)
        
        # Sprawdzenie, czy pierwsze wartości to NaN
        self.assertTrue(np.isnan(rsi_up.iloc[0]))
        self.assertTrue(np.isnan(rsi_up.iloc[13]))
        self.assertFalse(np.isnan(rsi_up.iloc[14]))
        
        # Sprawdzenie, czy RSI jest w odpowiednim zakresie
        self.assertTrue(all(0 <= x <= 100 for x in rsi_up.iloc[14:].values))
        
        # Sprawdzenie, czy RSI odzwierciedla typ rynku
        # W trendzie wzrostowym średni RSI powinien być wyższy
        self.assertGreater(rsi_up.iloc[20:].mean(), rsi_down.iloc[20:].mean())
    
    def test_macd_calculation(self):
        """Test obliczania Moving Average Convergence Divergence (MACD)"""
        # Test MACD na danych z trendem wzrostowym
        macd_result = self.indicators.calculate_macd(self.uptrend_data)
        
        # Pobranie wartości ze słownika
        macd_line = macd_result['macd']
        signal_line = macd_result['signal']
        histogram = macd_result['histogram']
        
        # Sprawdzenie wymiarów
        self.assertEqual(len(macd_line), len(self.uptrend_data))
        self.assertEqual(len(signal_line), len(self.uptrend_data))
        self.assertEqual(len(histogram), len(self.uptrend_data))
        
        # Sprawdzenie, czy wartości są zdefiniowane po wymaganych okresach
        self.assertFalse(np.isnan(macd_line.iloc[26]))
        self.assertFalse(np.isnan(signal_line.iloc[34]))  # 26 + 9 - 1
        
        # Sprawdzenie zgodności histogramu z różnicą między MACD a linią sygnału
        for i in range(35, 45):
            self.assertAlmostEqual(histogram.iloc[i], macd_line.iloc[i] - signal_line.iloc[i], places=5)
    
    def test_bollinger_bands_calculation(self):
        """Test obliczania Bollinger Bands"""
        # Test na danych z trendem wzrostowym
        upper, middle, lower = self.indicators.calculate_bollinger_bands(self.uptrend_data)
        
        # Sprawdzenie wymiarów
        self.assertEqual(len(upper), len(self.uptrend_data))
        self.assertEqual(len(middle), len(self.uptrend_data))
        self.assertEqual(len(lower), len(self.uptrend_data))
        
        # Sprawdzenie, czy wartości są zdefiniowane po wymaganym okresie
        self.assertTrue(np.isnan(upper.iloc[18]))
        self.assertFalse(np.isnan(upper.iloc[19]))
        
        # Sprawdzenie relacji między wstęgami
        for i in range(20, 40):
            self.assertGreater(upper.iloc[i], middle.iloc[i])
            self.assertLess(lower.iloc[i], middle.iloc[i])
            
        # Sprawdzenie szerokości wstęg w różnych typach rynku
        upper_ranging, middle_ranging, lower_ranging = self.indicators.calculate_bollinger_bands(self.ranging_data)
        
        # W danych z trendem wstęgi powinny mieć inną szerokość niż w danych bez wyraźnego trendu
        trend_width = (upper.iloc[30:40] - lower.iloc[30:40]).mean()
        ranging_width = (upper_ranging.iloc[30:40] - lower_ranging.iloc[30:40]).mean()
        
        # Nie sprawdzamy konkretnych wartości, ale upewniamy się, że szerokości są różne
        self.assertNotAlmostEqual(trend_width, ranging_width, places=1)


if __name__ == '__main__':
    unittest.main() 
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from test_data_generator import TestData

class TestTestData(unittest.TestCase):
    """Testy dla klasy TestData generującej dane testowe."""
    
    def test_generate_ohlc_data(self):
        """Test generowania danych OHLC."""
        # Test podstawowej generacji danych
        data = TestData.generate_ohlc_data()
        self.assertIsInstance(data, pd.DataFrame)
        self.assertEqual(len(data), 100)  # domyślna liczba świec
        self.assertTrue(all(col in data.columns for col in ['time', 'open', 'high', 'low', 'close', 'volume']))
        
        # Test z niestandardowymi parametrami
        custom_data = TestData.generate_ohlc_data(
            symbol='BTCUSD',
            timeframe='M15',
            num_candles=50,
            volatility=0.005
        )
        self.assertEqual(len(custom_data), 50)
        self.assertEqual(custom_data['symbol'].iloc[0], 'BTCUSD')
        self.assertEqual(custom_data['timeframe'].iloc[0], 'M15')
    
    def test_get_trending_market_data(self):
        """Test generowania danych z trendem."""
        # Test trendu wzrostowego
        uptrend_data = TestData.get_trending_market_data(trend='up', num_candles=200)  # Więcej świec dla wyraźniejszego trendu
        self.assertTrue(uptrend_data.iloc[-1]['close'] > uptrend_data.iloc[0]['close'])
        
        # Test trendu spadkowego
        downtrend_data = TestData.get_trending_market_data(trend='down', num_candles=200)
        self.assertTrue(downtrend_data.iloc[-1]['close'] < downtrend_data.iloc[0]['close'])
    
    def test_get_ranging_market_data(self):
        """Test generowania danych w konsolidacji."""
        data = TestData.get_ranging_market_data(range_width=0.02)
        
        # Sprawdzenie czy ceny oscylują wokół średniej
        mean_price = data['close'].mean()
        price_range = data['close'].max() - data['close'].min()
        
        # Sprawdzenie czy zakres cen jest w przybliżeniu równy range_width
        initial_price = data.iloc[0]['close']
        expected_range = initial_price * 0.02
        self.assertLess(abs(price_range - expected_range), expected_range * 0.5)
    
    def test_get_volatile_market_data(self):
        """Test generowania danych o wysokiej zmienności."""
        normal_data = TestData.generate_ohlc_data(volatility=0.002)
        volatile_data = TestData.get_volatile_market_data(volatility_factor=3)
        
        # Sprawdzenie czy zmienność jest wyższa
        normal_std = normal_data['close'].std()
        volatile_std = volatile_data['close'].std()
        self.assertTrue(volatile_std > normal_std)
    
    def test_get_support_resistance_data(self):
        """Test generowania danych z poziomami wsparcia/oporu."""
        levels = [1.1000, 1.1500, 1.2000]
        data = TestData.get_support_resistance_data(levels=levels, num_candles=500)  # Więcej świec dla lepszej szansy na reakcje
        
        # Sprawdzenie czy ceny reagują na poziomy
        reactions_found = False
        for level in levels:
            # Znajdź świece blisko poziomu
            near_level = data[abs(data['close'] - level) / level < 0.01]  # Zwiększony próg odległości
            if len(near_level) > 0:
                reactions_found = True
                break
        
        self.assertTrue(reactions_found, "Nie znaleziono żadnych reakcji na poziomy wsparcia/oporu")
    
    def test_get_multi_timeframe_data(self):
        """Test generowania danych dla wielu ram czasowych."""
        timeframes = ['M15', 'H1', 'H4']
        data = TestData.get_multi_timeframe_data(timeframes=timeframes)
        
        # Sprawdzenie czy wszystkie ramy czasowe są obecne
        self.assertEqual(set(data.keys()), set(timeframes))
        
        # Sprawdzenie relacji między liczbą świec
        self.assertTrue(len(data['M15']) > len(data['H1']))
        self.assertTrue(len(data['H1']) > len(data['H4']))
    
    def test_get_common_test_data(self):
        """Test generowania standardowego zestawu danych testowych."""
        data = TestData.get_common_test_data()
        
        # Sprawdzenie czy wszystkie oczekiwane klucze są obecne
        expected_keys = [
            'eurusd_h1', 'eurusd_h1_uptrend', 'eurusd_h1_downtrend',
            'eurusd_h1_range', 'eurusd_h1_volatile', 'eurusd_h1_support_resistance',
            'eurusd_multi_tf', 'btcusd_h1', 'gold_h1'
        ]
        self.assertTrue(all(key in data for key in expected_keys))
        
        # Sprawdzenie czy wszystkie DataFrame'y mają odpowiednią strukturę
        for df in data.values():
            if isinstance(df, pd.DataFrame):
                self.assertTrue(all(col in df.columns for col in ['time', 'open', 'high', 'low', 'close']))
            elif isinstance(df, dict):  # dla multi_tf
                self.assertTrue(all(isinstance(v, pd.DataFrame) for v in df.values()))

if __name__ == '__main__':
    unittest.main() 
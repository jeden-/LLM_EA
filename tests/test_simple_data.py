"""
Prosty test do sprawdzenia dostępności i struktury danych testowych.
"""

import os
import json
import unittest
from pathlib import Path

# Ścieżka do katalogu z danymi testowymi
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')

class TestDataAvailability(unittest.TestCase):
    """Testy sprawdzające dostępność i strukturę danych testowych."""
    
    def test_data_directory_exists(self):
        """Sprawdza, czy katalog test_data istnieje."""
        self.assertTrue(os.path.exists(TEST_DATA_DIR))
        self.assertTrue(os.path.isdir(TEST_DATA_DIR))
    
    def test_all_scenario_files_exist(self):
        """Sprawdza, czy wszystkie wymagane pliki dla scenariuszy istnieją."""
        scenarios = ['bullish_trend', 'bearish_trend', 'consolidation', 
                    'bullish_breakout', 'bearish_breakdown']
        
        for scenario in scenarios:
            # Sprawdzamy pliki metadanych
            metadata_path = os.path.join(TEST_DATA_DIR, f'{scenario}_metadata.json')
            self.assertTrue(os.path.exists(metadata_path), f"Brak pliku {metadata_path}")
            
            # Sprawdzamy pliki oczekiwanych wyników
            expected_path = os.path.join(TEST_DATA_DIR, f'{scenario}_expected.json')
            self.assertTrue(os.path.exists(expected_path), f"Brak pliku {expected_path}")
            
            # Sprawdzamy pliki sformatowanych danych
            formatted_path = os.path.join(TEST_DATA_DIR, f'{scenario}_formatted.json')
            self.assertTrue(os.path.exists(formatted_path), f"Brak pliku {formatted_path}")
    
    def test_formatted_data_structure(self):
        """Sprawdza strukturę plików z danymi w formacie JSON."""
        scenarios = ['bullish_trend', 'bearish_trend', 'consolidation', 
                    'bullish_breakout', 'bearish_breakdown']
        
        for scenario in scenarios:
            formatted_path = os.path.join(TEST_DATA_DIR, f'{scenario}_formatted.json')
            
            with open(formatted_path, 'r') as f:
                data = json.load(f)
            
            # Sprawdzamy podstawową strukturę
            self.assertIn('symbol', data)
            self.assertIn('timeframe', data)
            self.assertIn('data', data)
            self.assertIn('indicators', data)
            
            # Sprawdzamy dane świec
            self.assertGreater(len(data['data']), 0)
            candle = data['data'][0]
            self.assertIn('time', candle)
            self.assertIn('open', candle)
            self.assertIn('high', candle)
            self.assertIn('low', candle)
            self.assertIn('close', candle)
            self.assertIn('volume', candle)
            
            # Sprawdzamy wskaźniki
            indicators = data['indicators']
            self.assertIn('sma_50', indicators)
            self.assertIn('ema_20', indicators)
            self.assertIn('rsi_14', indicators)
    
    def test_expected_output_structure(self):
        """Sprawdza strukturę plików z oczekiwanymi wynikami."""
        scenarios = ['bullish_trend', 'bearish_trend', 'consolidation', 
                    'bullish_breakout', 'bearish_breakdown']
        
        for scenario in scenarios:
            expected_path = os.path.join(TEST_DATA_DIR, f'{scenario}_expected.json')
            
            with open(expected_path, 'r') as f:
                data = json.load(f)
            
            # Sprawdzamy podstawową strukturę
            self.assertIn('trend', data)
            self.assertIn('setup', data)
            
            # Tylko konsolidacja nie ma kierunku
            if scenario != 'consolidation':
                self.assertIn('action', data)
                self.assertIn('direction', data)
    
    def test_print_formatted_data_sample(self):
        """Wyświetla próbkę danych do analizy."""
        # Wyświetlamy jeden zestaw danych do debugowania
        scenario = 'bullish_trend'
        formatted_path = os.path.join(TEST_DATA_DIR, f'{scenario}_formatted.json')
        
        with open(formatted_path, 'r') as f:
            data = json.load(f)
        
        print("\nPrzykładowa struktura danych:")
        print(f"Symbol: {data['symbol']}")
        print(f"Timeframe: {data['timeframe']}")
        print(f"Liczba świec: {len(data['data'])}")
        print("\nOstatnie 3 świece:")
        for i in range(-3, 0):
            print(data['data'][i])
        
        print("\nDostępne wskaźniki:")
        for indicator, values in data['indicators'].items():
            if isinstance(values, list):
                last_three = values[-3:] if len(values) >= 3 else values
                print(f"{indicator}: {len(values)} wartości, ostatnie: {last_three}")
            else:
                print(f"{indicator}: {values}")
        
        # Test nie ma asercji - służy tylko do wyświetlenia danych
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main() 
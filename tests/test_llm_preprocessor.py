"""
Testy dla preprocessora LLM.

Ten moduł zawiera testy jednostkowe dla funkcjonalności związanych 
z preprocessorem przygotowującym dane wejściowe przed wysłaniem ich do modeli językowymi (LLM).
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import datetime

# Dodanie ścieżki głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM_Engine.llm_preprocessor import (
    LLMPreprocessor,
    MarketDataPreprocessor,
    PromptTemplateProcessor,
    HistoricalDataPreprocessor
)

class TestLLMPreprocessor(unittest.TestCase):
    """Testy dla bazowej klasy LLMPreprocessor."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.preprocessor = LLMPreprocessor()
        
    def test_init(self):
        """Test inicjalizacji preprocessora."""
        self.assertIsNotNone(self.preprocessor)
        
    def test_clean_input_data(self):
        """Test czyszczenia danych wejściowych."""
        # Dane testowe zawierające potencjalne problemy
        input_data = {
            "text": "Tekst z \n przeniesieniem linii i  podwójnymi  spacjami",
            "number": 123.45678901234,
            "null_value": None,
            "empty": "",
            "list": [1, 2, None, 3],
            "deep": {"a": None, "b": "   spacje   "}
        }
        
        # Wywołanie metody
        cleaned_data = self.preprocessor.clean_input_data(input_data)
        
        # Weryfikacja
        self.assertEqual(cleaned_data["text"], "Tekst z przeniesieniem linii i podwójnymi spacjami")
        self.assertAlmostEqual(cleaned_data["number"], 123.457)  # Zaokrąglenie do 3 miejsc po przecinku
        self.assertIsNone(cleaned_data["null_value"])
        self.assertEqual(cleaned_data["empty"], "")
        self.assertEqual(cleaned_data["list"], [1, 2, None, 3])
        self.assertIsNone(cleaned_data["deep"]["a"])
        self.assertEqual(cleaned_data["deep"]["b"], "spacje")
        
    def test_validate_input_data(self):
        """Test walidacji danych wejściowych."""
        # Poprawne dane
        valid_data = {
            "pair": "EURUSD",
            "timeframe": "H1",
            "close_prices": [1.1, 1.2, 1.3]
        }
        
        # Wywołanie metody - powinno zwrócić True
        result = self.preprocessor.validate_input_data(valid_data, required_fields=["pair", "timeframe"])
        
        # Weryfikacja
        self.assertTrue(result)
        
        # Niepoprawne dane - brak wymaganych pól
        invalid_data = {
            "pair": "EURUSD"
        }
        
        # Wywołanie metody - powinno zwrócić False
        result = self.preprocessor.validate_input_data(invalid_data, required_fields=["pair", "timeframe"])
        
        # Weryfikacja
        self.assertFalse(result)
        
    def test_normalize_market_data(self):
        """Test normalizacji danych rynkowych."""
        # Dane rynkowe
        market_data = {
            "open": [1.1000, 1.1100, 1.1200],
            "high": [1.1050, 1.1150, 1.1250],
            "low": [1.0950, 1.1050, 1.1150],
            "close": [1.1010, 1.1110, 1.1210],
            "volume": [1000, 1200, 800]
        }
        
        # Wywołanie metody
        normalized_data = self.preprocessor.normalize_market_data(market_data)
        
        # Weryfikacja - dane powinny być znormalizowane do zakresu [0, 1]
        for key in ["open", "high", "low", "close"]:
            self.assertGreaterEqual(min(normalized_data[key]), 0)
            self.assertLessEqual(max(normalized_data[key]), 1)
            
        self.assertGreaterEqual(min(normalized_data["volume"]), 0)
        self.assertLessEqual(max(normalized_data["volume"]), 1)


class TestMarketDataPreprocessor(unittest.TestCase):
    """Testy dla klasy MarketDataPreprocessor."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.preprocessor = MarketDataPreprocessor()
        
    def test_init(self):
        """Test inicjalizacji preprocessora danych rynkowych."""
        self.assertIsNotNone(self.preprocessor)
        self.assertIsNotNone(self.preprocessor.indicators)
        
    def test_add_technical_indicators(self):
        """Test dodawania wskaźników technicznych do danych rynkowych."""
        # Dane rynkowe
        market_data = {
            "open": [1.1000, 1.1100, 1.1200, 1.1300, 1.1400],
            "high": [1.1050, 1.1150, 1.1250, 1.1350, 1.1450],
            "low": [1.0950, 1.1050, 1.1150, 1.1250, 1.1350],
            "close": [1.1010, 1.1110, 1.1210, 1.1310, 1.1410],
            "volume": [1000, 1200, 800, 900, 1100]
        }
        
        # Mock dla CalculateIndicators
        with patch.object(self.preprocessor.indicators, 'calculate_ma', return_value=[None, None, 1.111, 1.121, 1.131]), \
             patch.object(self.preprocessor.indicators, 'calculate_rsi', return_value=[None, None, 55.0, 60.0, 65.0]):
            
            # Wywołanie metody
            result = self.preprocessor.add_technical_indicators(market_data, indicators=["ma", "rsi"])
            
            # Weryfikacja
            self.assertIn("ma", result)
            self.assertIn("rsi", result)
            self.assertEqual(result["ma"], [None, None, 1.111, 1.121, 1.131])
            self.assertEqual(result["rsi"], [None, None, 55.0, 60.0, 65.0])
            
    def test_format_price_data(self):
        """Test formatowania danych cenowych dla modelu LLM."""
        # Dane rynkowe
        market_data = {
            "open": [1.1000, 1.1100],
            "high": [1.1050, 1.1150],
            "low": [1.0950, 1.1050],
            "close": [1.1010, 1.1110],
            "volume": [1000, 1200],
            "ma": [None, 1.105],
            "rsi": [None, 55.0]
        }
        
        # Wywołanie metody
        formatted_data = self.preprocessor.format_price_data(market_data)
        
        # Weryfikacja
        self.assertIsInstance(formatted_data, str)
        self.assertIn("Open", formatted_data)
        self.assertIn("High", formatted_data)
        self.assertIn("Low", formatted_data)
        self.assertIn("Close", formatted_data)
        self.assertIn("Volume", formatted_data)
        self.assertIn("MA", formatted_data)
        self.assertIn("RSI", formatted_data)
        
    def test_process_market_data(self):
        """Test pełnego przetwarzania danych rynkowych."""
        # Dane rynkowe
        market_data = {
            "symbol": "EURUSD",
            "timeframe": "H1",
            "open": [1.1000, 1.1100, 1.1200],
            "high": [1.1050, 1.1150, 1.1250],
            "low": [1.0950, 1.1050, 1.1150],
            "close": [1.1010, 1.1110, 1.1210],
            "volume": [1000, 1200, 800]
        }
        
        # Mock dla metod
        with patch.object(MarketDataPreprocessor, 'add_technical_indicators', return_value={
                "symbol": "EURUSD",
                "timeframe": "H1",
                "open": [1.1000, 1.1100, 1.1200],
                "high": [1.1050, 1.1150, 1.1250],
                "low": [1.0950, 1.1050, 1.1150],
                "close": [1.1010, 1.1110, 1.1210],
                "volume": [1000, 1200, 800],
                "ma": [None, None, 1.111],
                "rsi": [None, None, 55.0]
            }), \
             patch.object(MarketDataPreprocessor, 'format_price_data', return_value="Sformatowane dane"):
            
            # Wywołanie metody
            result = self.preprocessor.process_market_data(market_data)
            
            # Weryfikacja
            self.assertEqual(result["symbol"], "EURUSD")
            self.assertEqual(result["timeframe"], "H1")
            self.assertEqual(result["formatted_data"], "Sformatowane dane")
            self.assertIn("ma", result)
            self.assertIn("rsi", result)


class TestPromptTemplateProcessor(unittest.TestCase):
    """Testy dla klasy PromptTemplateProcessor."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.processor = PromptTemplateProcessor()
        
    def test_init(self):
        """Test inicjalizacji processora szablonów."""
        self.assertIsNotNone(self.processor)
        self.assertIsNotNone(self.processor.template_dir)
        
    def test_load_template(self):
        """Test ładowania szablonu."""
        # Mock dla otwarcia pliku z szablonem
        template_content = "Szablon dla zadania: {{task_type}}\nDane: {{data}}"
        mock_open_func = mock_open(read_data=template_content)
        
        with patch('builtins.open', mock_open_func):
            # Wywołanie metody
            template = self.processor.load_template('trade_signal')
            
            # Weryfikacja
            self.assertEqual(template, template_content)
            
    def test_fill_template(self):
        """Test wypełniania szablonu danymi."""
        # Szablon
        template = "Analizuj parę: {{symbol}} na interwale {{timeframe}}\nDane: {{formatted_data}}"
        
        # Dane
        data = {
            "symbol": "EURUSD",
            "timeframe": "H1",
            "formatted_data": "Open: 1.1000, Close: 1.1010"
        }
        
        # Wywołanie metody
        filled_template = self.processor.fill_template(template, data)
        
        # Weryfikacja
        expected = "Analizuj parę: EURUSD na interwale H1\nDane: Open: 1.1000, Close: 1.1010"
        self.assertEqual(filled_template, expected)
        
    def test_prepare_task_prompt(self):
        """Test przygotowania promptu dla określonego zadania."""
        # Mock dla metod
        template_content = "Szablon dla zadania: {{task_type}}\nDane: {{formatted_data}}"
        
        with patch.object(PromptTemplateProcessor, 'load_template', return_value=template_content), \
             patch.object(PromptTemplateProcessor, 'fill_template', return_value="Wypełniony szablon"):
            
            # Dane
            task_type = "market_analysis"
            data = {
                "symbol": "EURUSD",
                "formatted_data": "Dane cenowe"
            }
            
            # Wywołanie metody
            prompt = self.processor.prepare_task_prompt(task_type, data)
            
            # Weryfikacja
            self.assertEqual(prompt, "Wypełniony szablon")


class TestHistoricalDataPreprocessor(unittest.TestCase):
    """Testy dla klasy HistoricalDataPreprocessor."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.preprocessor = HistoricalDataPreprocessor()
        
    def test_init(self):
        """Test inicjalizacji preprocessora danych historycznych."""
        self.assertIsNotNone(self.preprocessor)
        
    def test_filter_by_date_range(self):
        """Test filtrowania danych według zakresu dat."""
        # Dane historyczne
        historical_data = {
            "dates": [
                "2023-01-01",
                "2023-01-02",
                "2023-01-03",
                "2023-01-04",
                "2023-01-05"
            ],
            "close": [1.1000, 1.1100, 1.1200, 1.1300, 1.1400]
        }
        
        # Wywołanie metody
        filtered_data = self.preprocessor.filter_by_date_range(
            historical_data,
            start_date="2023-01-02",
            end_date="2023-01-04"
        )
        
        # Weryfikacja
        self.assertEqual(len(filtered_data["dates"]), 3)
        self.assertEqual(len(filtered_data["close"]), 3)
        self.assertEqual(filtered_data["dates"][0], "2023-01-02")
        self.assertEqual(filtered_data["dates"][-1], "2023-01-04")
        self.assertEqual(filtered_data["close"][0], 1.1100)
        self.assertEqual(filtered_data["close"][-1], 1.1300)
        
    def test_resample_data(self):
        """Test przewzorcowania danych do innego interwału czasowego."""
        # Dane historyczne (H1)
        historical_data = {
            "dates": [
                "2023-01-01 00:00",
                "2023-01-01 01:00",
                "2023-01-01 02:00",
                "2023-01-01 03:00",
                "2023-01-01 04:00",
                "2023-01-01 05:00"
            ],
            "open": [1.1000, 1.1050, 1.1100, 1.1150, 1.1200, 1.1250],
            "high": [1.1025, 1.1075, 1.1125, 1.1175, 1.1225, 1.1275],
            "low": [1.0990, 1.1040, 1.1090, 1.1140, 1.1190, 1.1240],
            "close": [1.1010, 1.1060, 1.1110, 1.1160, 1.1210, 1.1260],
            "volume": [100, 110, 90, 95, 105, 100]
        }
        
        # Mock dla implementacji resample_data
        def mock_resample(data, target_timeframe):
            # Zwraca dane w interwale H4 (grupy po 4 godziny)
            if target_timeframe == "H4":
                return {
                    "dates": ["2023-01-01 00:00", "2023-01-01 04:00"],
                    "open": [1.1000, 1.1200],
                    "high": [1.1175, 1.1275],
                    "low": [1.0990, 1.1190],
                    "close": [1.1160, 1.1260],
                    "volume": [395, 205]
                }
            return data
            
        with patch.object(self.preprocessor, '_resample_to_target_timeframe', side_effect=mock_resample):
            # Wywołanie metody
            resampled_data = self.preprocessor.resample_data(historical_data, "H1", "H4")
            
            # Weryfikacja
            self.assertEqual(len(resampled_data["dates"]), 2)
            self.assertEqual(resampled_data["open"][0], 1.1000)
            self.assertEqual(resampled_data["high"][0], 1.1175)
            self.assertEqual(resampled_data["close"][0], 1.1160)
            self.assertEqual(resampled_data["volume"][0], 395)
        
    def test_prepare_historical_data(self):
        """Test przygotowania danych historycznych."""
        # Dane testowe
        test_data = {
            "symbol": "EURUSD",
            "source_timeframe": "H1",
            "target_timeframe": "H4",
            "start_date": "2023-01-01",
            "end_date": "2023-01-02",
            "data": {
                "dates": ["2023-01-01 00:00", "2023-01-01 01:00", "2023-01-01 02:00", "2023-01-01 03:00"],
                "open": [1.1000, 1.1100, 1.1200, 1.1300],
                "high": [1.1050, 1.1150, 1.1250, 1.1350],
                "low": [1.0950, 1.1050, 1.1150, 1.1250],
                "close": [1.1010, 1.1110, 1.1210, 1.1310],
                "volume": [1000, 1200, 800, 900]
            }
        }

        # Wywołanie metody
        processed_data = self.preprocessor.prepare_historical_data(test_data)

        # Weryfikacja
        self.assertEqual(processed_data["symbol"], "EURUSD")
        self.assertEqual(processed_data["timeframe"], "H4")
        self.assertEqual(processed_data["start_date"], "2023-01-01")
        self.assertEqual(processed_data["end_date"], "2023-01-02")
        
        # Sprawdzenie struktury danych
        self.assertIn("data", processed_data)
        self.assertIn("dates", processed_data["data"])
        self.assertIn("open", processed_data["data"])
        self.assertIn("close", processed_data["data"])
        
        # Sprawdzenie czy dane zostały przewzorkowane do H4 (powinien być 1 punkt zamiast 4)
        self.assertEqual(len(processed_data["data"]["dates"]), 1)
        self.assertEqual(len(processed_data["data"]["open"]), 1)
        self.assertEqual(len(processed_data["data"]["close"]), 1)
        
        # Sprawdzenie wartości
        self.assertEqual(processed_data["data"]["open"][0], 1.1000)  # Pierwsza wartość z grupy
        self.assertEqual(processed_data["data"]["close"][0], 1.1310)  # Ostatnia wartość z grupy


if __name__ == '__main__':
    unittest.main() 
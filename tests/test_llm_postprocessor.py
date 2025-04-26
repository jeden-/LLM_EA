"""
Testy dla postprocesora LLM.

Ten moduł zawiera testy jednostkowe dla funkcjonalności związanych 
z postprocessingiem danych po otrzymaniu odpowiedzi od modeli językowych (LLM).
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open
import json

# Dodanie ścieżki głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM_Engine.llm_postprocessor import (
    LLMPostprocessor,
    JSONResponsePostprocessor,
    TradingSignalPostprocessor,
    MarketAnalysisPostprocessor
)

class TestLLMPostprocessor(unittest.TestCase):
    """Testy dla bazowej klasy LLMPostprocessor i jej metod."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.postprocessor = LLMPostprocessor()
        
    def test_init(self):
        """Test inicjalizacji postprocesora LLM."""
        self.assertEqual(self.postprocessor.processed_response, None)
        
    def test_extract_text_from_response(self):
        """Test ekstrakcji tekstu z odpowiedzi LLM."""
        # Odpowiedź w formacie JSON
        json_response = {
            "id": "response_1",
            "model": "gpt-4",
            "choices": [
                {
                    "message": {
                        "content": "To jest przykładowa odpowiedź od modelu."
                    }
                }
            ]
        }
        
        # Jako tekst
        json_string = json.dumps(json_response)
        
        # Ekstrakcja tekstu z odpowiedzi JSON
        extracted_text = self.postprocessor.extract_text_from_response(json_string)
        
        # Weryfikacja
        self.assertEqual(extracted_text, "To jest przykładowa odpowiedź od modelu.")
        
        # Test z prostą odpowiedzią tekstową
        simple_text = "To jest prosta odpowiedź tekstowa."
        extracted_text = self.postprocessor.extract_text_from_response(simple_text)
        
        # Weryfikacja
        self.assertEqual(extracted_text, simple_text)
        
    def test_clean_response(self):
        """Test czyszczenia odpowiedzi LLM."""
        # Odpowiedź z dodatkowymi spacjami, znakami nowej linii, itp.
        messy_response = "  To jest \n\n odpowiedź \t z  wieloma   spacjami.  \n\n"
        
        # Czyszczenie odpowiedzi
        cleaned = self.postprocessor.clean_response(messy_response)
        
        # Weryfikacja
        self.assertEqual(cleaned, "To jest odpowiedź z wieloma spacjami.")
        
    def test_postprocess_response(self):
        """Test postprocessingu odpowiedzi LLM."""
        response = "To jest przykładowa odpowiedź od modelu."
        
        # Postprocessing (w klasie bazowej - brak zmian)
        processed = self.postprocessor.postprocess_response(response)
        
        # Weryfikacja
        self.assertEqual(processed, response)
        self.assertEqual(self.postprocessor.processed_response, response)
        
    def test_get_processed_response(self):
        """Test pobierania przetworzonej odpowiedzi."""
        test_response = "Przetworzona odpowiedź"
        self.postprocessor.processed_response = test_response
        
        result = self.postprocessor.get_processed_response()
        
        # Weryfikacja
        self.assertEqual(result, test_response)


class TestJSONResponsePostprocessor(unittest.TestCase):
    """Testy dla klasy JSONResponsePostprocessor."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.postprocessor = JSONResponsePostprocessor()
        
    def test_init(self):
        """Test inicjalizacji postprocesora odpowiedzi JSON."""
        self.assertEqual(self.postprocessor.processed_response, None)
        self.assertEqual(self.postprocessor.expected_schema, {})
        
    def test_set_expected_schema(self):
        """Test ustawiania oczekiwanego schematu JSON."""
        schema = {
            "type": "object",
            "properties": {
                "action": {"type": "string"},
                "confidence": {"type": "number"}
            },
            "required": ["action", "confidence"]
        }
        
        self.postprocessor.set_expected_schema(schema)
        
        # Weryfikacja
        self.assertEqual(self.postprocessor.expected_schema, schema)
        
    def test_extract_json_from_text(self):
        """Test ekstrakcji JSON z tekstu."""
        # Tekst zawierający JSON
        text_with_json = """
        Oto analiza rynku:
        
        ```json
        {
            "trend": "bullish",
            "support": 1.0950,
            "resistance": 1.1050,
            "recommendation": "buy"
        }
        ```
        
        Powyższe dane wskazują na trend wzrostowy.
        """
        
        # Ekstrakcja JSON
        extracted_json = self.postprocessor.extract_json_from_text(text_with_json)
        
        # Weryfikacja
        expected_json = {
            "trend": "bullish",
            "support": 1.0950,
            "resistance": 1.1050,
            "recommendation": "buy"
        }
        
        self.assertEqual(extracted_json, expected_json)
        
        # Test z bezpośrednim JSON (bez znaczników)
        direct_json = '{"trend": "bearish", "support": 1.2300, "resistance": 1.2450}'
        extracted_json = self.postprocessor.extract_json_from_text(direct_json)
        
        # Weryfikacja
        expected_json = {
            "trend": "bearish",
            "support": 1.2300,
            "resistance": 1.2450
        }
        
        self.assertEqual(extracted_json, expected_json)
        
    def test_validate_json_schema(self):
        """Test walidacji schematu JSON."""
        # Ustawienie schematu
        schema = {
            "type": "object",
            "properties": {
                "trend": {"type": "string"},
                "support": {"type": "number"},
                "resistance": {"type": "number"}
            },
            "required": ["trend", "support", "resistance"]
        }
        
        self.postprocessor.set_expected_schema(schema)
        
        # Poprawny JSON
        valid_json = {
            "trend": "bullish",
            "support": 1.0950,
            "resistance": 1.1050
        }
        
        # Walidacja
        is_valid = self.postprocessor.validate_json_schema(valid_json)
        
        # Weryfikacja
        self.assertTrue(is_valid)
        
        # Niepoprawny JSON (brakuje wymaganego pola)
        invalid_json = {
            "trend": "bullish",
            "support": 1.0950
        }
        
        # Walidacja
        is_valid = self.postprocessor.validate_json_schema(invalid_json)
        
        # Weryfikacja
        self.assertFalse(is_valid)
        
    def test_fix_common_json_errors(self):
        """Test naprawiania częstych błędów w JSON."""
        # JSON z błędami składniowymi
        broken_json = '{"trend": "bullish", support: 1.0950, "resistance": 1.1050,}'
        
        # Naprawianie JSON
        fixed_json = self.postprocessor.fix_common_json_errors(broken_json)
        
        # Próba parsowania naprawionego JSON
        try:
            parsed_json = json.loads(fixed_json)
            json_fixed = True
        except json.JSONDecodeError:
            json_fixed = False
            
        # Weryfikacja
        self.assertTrue(json_fixed)
        
    def test_postprocess_response(self):
        """Test postprocessingu odpowiedzi JSON."""
        # Ustawienie schematu
        schema = {
            "type": "object",
            "properties": {
                "trend": {"type": "string"},
                "support": {"type": "number"},
                "resistance": {"type": "number"}
            },
            "required": ["trend", "support", "resistance"]
        }
        
        self.postprocessor.set_expected_schema(schema)
        
        # Odpowiedź z modelu
        response = """
        Analiza techniczna EURUSD wskazuje na:
        
        ```json
        {
            "trend": "bullish",
            "support": 1.0950,
            "resistance": 1.1050,
            "recommendation": "buy"
        }
        ```
        """
        
        # Postprocessing
        processed = self.postprocessor.postprocess_response(response)
        
        # Weryfikacja
        self.assertEqual(processed["trend"], "bullish")
        self.assertEqual(processed["support"], 1.0950)
        self.assertEqual(processed["resistance"], 1.1050)
        self.assertEqual(processed["recommendation"], "buy")


class TestTradingSignalPostprocessor(unittest.TestCase):
    """Testy dla klasy TradingSignalPostprocessor."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.postprocessor = TradingSignalPostprocessor()
        
    def test_init(self):
        """Test inicjalizacji postprocesora sygnałów handlowych."""
        self.assertEqual(self.postprocessor.processed_response, None)
        self.assertIsNotNone(self.postprocessor.expected_schema)
        
        # Sprawdzenie schematu
        schema = self.postprocessor.expected_schema
        self.assertEqual(schema["type"], "object")
        self.assertIn("action", schema["required"])
        self.assertIn("pair", schema["required"])
        self.assertIn("entry_price", schema["required"])
        self.assertIn("stop_loss", schema["required"])
        self.assertIn("take_profit", schema["required"])
        
    def test_extract_trade_parameters_json(self):
        """Test ekstrakcji parametrów transakcji z formatu JSON."""
        response = """
        Analiza wskazuje na sygnał kupna dla EURUSD:
        
        ```json
        {
            "action": "BUY",
            "pair": "EURUSD",
            "entry_price": 1.0950,
            "stop_loss": 1.0900,
            "take_profit": 1.1050,
            "confidence": 0.85,
            "timeframe": "H4",
            "reason": "Przełamanie linii trendu oraz wsparcie RSI"
        }
        ```
        """
        
        params = self.postprocessor.extract_trade_parameters(response)
        
        self.assertEqual(params["action"], "BUY")
        self.assertEqual(params["pair"], "EURUSD")
        self.assertEqual(params["entry_price"], 1.0950)
        self.assertEqual(params["stop_loss"], 1.0900)
        self.assertEqual(params["take_profit"], 1.1050)
        self.assertEqual(params["confidence"], 0.85)
        self.assertEqual(params["timeframe"], "H4")
        self.assertEqual(params["reason"], "Przełamanie linii trendu oraz wsparcie RSI")
        
    def test_extract_trade_parameters_text(self):
        """Test ekstrakcji parametrów transakcji z tekstu."""
        response = """
        Para: EURUSD
        Sygnał: SELL
        Wejście: 1.0950
        Stop Loss: 1.1000
        Take Profit: 1.0850
        Pewność: wysoka
        Uzasadnienie: Silne odrzucenie od oporu
        """
        
        params = self.postprocessor.extract_trade_parameters(response)
        
        self.assertEqual(params["signal"], "SELL")
        self.assertEqual(params["pair"], "EURUSD")
        self.assertEqual(params["entry"], 1.0950)
        self.assertEqual(params["stop_loss"], 1.1000)
        self.assertEqual(params["take_profit"], 1.0850)
        self.assertEqual(params["confidence"], "high")
        self.assertEqual(params["rationale"], "Silne odrzucenie od oporu")
        
    def test_validate_trade_signal_buy(self):
        """Test walidacji sygnału BUY."""
        # Poprawny sygnał BUY
        valid_buy = {
            "signal": "BUY",
            "pair": "EURUSD",
            "entry_price": 1.0950,
            "stop_loss": 1.0900,
            "take_profit": 1.1050
        }
        
        is_valid, errors = self.postprocessor.validate_trade_signal(valid_buy)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Niepoprawne poziomy dla BUY
        invalid_buy = {
            "signal": "BUY",
            "pair": "EURUSD",
            "entry_price": 1.0950,
            "stop_loss": 1.1000,  # SL powyżej entry
            "take_profit": 1.0900  # TP poniżej entry
        }
        
        is_valid, errors = self.postprocessor.validate_trade_signal(invalid_buy)
        self.assertFalse(is_valid)
        self.assertIn("Invalid price levels for BUY signal", errors)
        
    def test_validate_trade_signal_sell(self):
        """Test walidacji sygnału SELL."""
        # Poprawny sygnał SELL
        valid_sell = {
            "signal": "SELL",
            "pair": "EURUSD",
            "entry_price": 1.0950,
            "stop_loss": 1.1000,
            "take_profit": 1.0850
        }
        
        is_valid, errors = self.postprocessor.validate_trade_signal(valid_sell)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Niepoprawne poziomy dla SELL
        invalid_sell = {
            "signal": "SELL",
            "pair": "EURUSD",
            "entry_price": 1.0950,
            "stop_loss": 1.0900,  # SL poniżej entry
            "take_profit": 1.1000  # TP powyżej entry
        }
        
        is_valid, errors = self.postprocessor.validate_trade_signal(invalid_sell)
        self.assertFalse(is_valid)
        self.assertIn("Invalid price levels for SELL signal", errors)
        
    def test_validate_trade_signal_wait(self):
        """Test walidacji sygnału WAIT."""
        wait_signal = {
            "signal": "WAIT",
            "pair": "EURUSD",
            "reason": "Brak wyraźnego trendu"
        }
        
        is_valid, errors = self.postprocessor.validate_trade_signal(wait_signal)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
    def test_calculate_risk_reward_ratio(self):
        """Test obliczania stosunku ryzyka do zysku."""
        # Dla sygnału BUY
        buy_params = {
            "signal": "BUY",
            "entry_price": 1.0950,
            "stop_loss": 1.0900,
            "take_profit": 1.1050
        }
        
        rr_buy = self.postprocessor.calculate_risk_reward_ratio(buy_params)
        expected_rr_buy = (1.1050 - 1.0950) / (1.0950 - 1.0900)
        self.assertAlmostEqual(rr_buy, expected_rr_buy, places=2)
        
        # Dla sygnału SELL
        sell_params = {
            "signal": "SELL",
            "entry_price": 1.0950,
            "stop_loss": 1.1000,
            "take_profit": 1.0850
        }
        
        rr_sell = self.postprocessor.calculate_risk_reward_ratio(sell_params)
        expected_rr_sell = (1.0950 - 1.0850) / (1.1000 - 1.0950)
        self.assertAlmostEqual(rr_sell, expected_rr_sell, places=2)
        
        # Dla niepoprawnych danych
        invalid_params = {
            "signal": "BUY",
            "entry_price": 1.0950
        }
        
        rr_invalid = self.postprocessor.calculate_risk_reward_ratio(invalid_params)
        self.assertEqual(rr_invalid, 0.0)
        
    def test_enrich_trade_signal(self):
        """Test wzbogacania sygnału handlowego."""
        signal = {
            "action": "BUY",
            "pair": "EURUSD",
            "entry_price": 1.0950,
            "stop_loss": 1.0900,
            "take_profit": 1.1050,
            "confidence": 0.85
        }
        
        enriched = self.postprocessor.enrich_trade_signal(signal)
        
        # Sprawdzenie dodanych pól
        self.assertIn("signal", enriched)  # action powinno być skopiowane do signal
        self.assertEqual(enriched["signal"], "BUY")
        self.assertIn("risk_reward_ratio", enriched)
        self.assertIn("pip_value", enriched)
        self.assertEqual(enriched["pip_value"], 0.0001)  # dla EURUSD
        self.assertIn("timestamp", enriched)
        
        # Test dla pary z JPY
        jpy_signal = {
            "action": "SELL",
            "pair": "USDJPY",
            "entry_price": 150.50,
            "stop_loss": 151.00,
            "take_profit": 149.50
        }
        
        enriched_jpy = self.postprocessor.enrich_trade_signal(jpy_signal)
        self.assertEqual(enriched_jpy["pip_value"], 0.01)  # dla par z JPY
        
    def test_postprocess_response(self):
        """Test pełnego przetwarzania odpowiedzi."""
        # Test poprawnej odpowiedzi
        response = """
        Analiza wskazuje na sygnał sprzedaży dla GBPUSD:
        
        ```json
        {
            "action": "SELL",
            "pair": "GBPUSD",
            "entry_price": 1.2500,
            "stop_loss": 1.2550,
            "take_profit": 1.2400,
            "confidence": 0.75,
            "timeframe": "H1",
            "reason": "Silne odrzucenie od oporu oraz sygnał z MACD"
        }
        ```
        """
        
        processed = self.postprocessor.postprocess_response(response)
        
        self.assertEqual(processed["action"], "SELL")
        self.assertEqual(processed["pair"], "GBPUSD")
        self.assertEqual(processed["entry_price"], 1.2500)
        self.assertEqual(processed["stop_loss"], 1.2550)
        self.assertEqual(processed["take_profit"], 1.2400)
        self.assertIn("risk_reward_ratio", processed)
        self.assertIn("pip_value", processed)
        self.assertIn("timestamp", processed)
        
        # Test niepoprawnej odpowiedzi
        invalid_response = """
        ```json
        {
            "action": "INVALID",
            "pair": "GBPUSD"
        }
        ```
        """
        
        processed_invalid = self.postprocessor.postprocess_response(invalid_response)
        self.assertIn("error", processed_invalid)
        self.assertIn("raw_response", processed_invalid)
        self.assertIn("errors", processed_invalid)


class TestMarketAnalysisPostprocessor(unittest.TestCase):
    """Testy dla klasy MarketAnalysisPostprocessor."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.postprocessor = MarketAnalysisPostprocessor()
        
    def test_init(self):
        """Test inicjalizacji postprocesora analizy rynku."""
        self.assertEqual(self.postprocessor.processed_response, None)
        self.assertIsNotNone(self.postprocessor.expected_schema)  # Powinien mieć domyślny schemat
        
    def test_extract_market_sentiment(self):
        """Test ekstrakcji sentymentu rynkowego."""
        # Odpowiedź zawierająca analizę rynku
        response = """
        Analiza rynku EURUSD:
        
        ```json
        {
            "pair": "EURUSD",
            "timeframe": "D1",
            "trend": "bullish",
            "strength": 0.8,
            "key_levels": {
                "support": [1.0900, 1.0950],
                "resistance": [1.1050, 1.1100]
            },
            "sentiment": "bullish",
            "analysis": "Rynek wykazuje silny trend wzrostowy po przebiciu kluczowego poziomu oporu na 1.0950. Wskaźniki techniczne potwierdzają siłę trendu."
        }
        ```
        """
        
        # Ekstrakcja sentymentu
        sentiment = self.postprocessor.extract_market_sentiment(response)
        
        # Weryfikacja
        self.assertEqual(sentiment, "bullish")
        
        # Test z odpowiedzią niestandardową
        non_standard_response = """
        Obecna sytuacja na rynku EURUSD wskazuje na mieszane nastroje, jednak z lekkim nastawieniem na wzrosty.
        """
        
        # Ekstrakcja sentymentu
        sentiment = self.postprocessor.extract_market_sentiment(non_standard_response)
        
        # Weryfikacja (powinno próbować wykryć sentyment z tekstu)
        self.assertIn(sentiment, ["bullish", "bearish", "neutral", "mixed"])
        
    def test_extract_key_levels(self):
        """Test ekstrakcji kluczowych poziomów."""
        # Odpowiedź zawierająca analizę rynku
        response = """
        Analiza rynku GBPUSD:
        
        ```json
        {
            "pair": "GBPUSD",
            "timeframe": "H4",
            "trend": "bearish",
            "key_levels": {
                "support": [1.2400, 1.2350],
                "resistance": [1.2500, 1.2550]
            },
            "sentiment": "bearish"
        }
        ```
        """
        
        # Ekstrakcja poziomów
        levels = self.postprocessor.extract_key_levels(response)
        
        # Weryfikacja
        self.assertIn("support", levels)
        self.assertIn("resistance", levels)
        self.assertEqual(levels["support"], [1.2400, 1.2350])
        self.assertEqual(levels["resistance"], [1.2500, 1.2550])
        
        # Test z odpowiedzią tekstową
        text_response = """
        Kluczowe poziomy dla GBPUSD to wsparcia na 1.2400 i 1.2350, oraz opory na 1.2500 i 1.2550.
        """
        
        # Ekstrakcja poziomów (może nie zadziałać idealnie, ale powinno próbować)
        levels = self.postprocessor.extract_key_levels(text_response)
        
        # Weryfikacja
        self.assertIsNotNone(levels)
        
    def test_summarize_analysis(self):
        """Test podsumowania analizy rynku."""
        # Długa analiza rynku
        analysis = """
        Rynek EURUSD wykazuje silny trend wzrostowy po przebiciu kluczowego poziomu oporu na 1.0950. 
        Wskaźniki techniczne potwierdzają siłę trendu - RSI na poziomie 68 wskazuje na momentum wzrostowe, 
        choć zbliża się do poziomów wykupienia. MACD pozostaje powyżej linii sygnałowej, co potwierdza siłę trendu.
        Bollinger Bands rozszerzają się, wskazując na kontynuację trendu. Najbliższe poziomy wsparcia znajdują się 
        na 1.0950 (dawny opór, teraz wsparcie) oraz 1.0900 (50-dniowa średnia krocząca). Opory natomiast 
        zlokalizowane są na 1.1050 (psychologiczny poziom) oraz 1.1100 (szczyt z marca). W kontekście fundamentalnym, 
        ostatnie wypowiedzi przedstawicieli Fed oraz ECB wskazują na możliwe zawężenie różnic w stopach procentowych, 
        co wspiera euro. Nadchodzące dane o inflacji w USA mogą wprowadzić zmienność na rynek.
        """
        
        # Podsumowanie
        summary = self.postprocessor.summarize_analysis(analysis, max_length=150)
        
        # Weryfikacja
        self.assertLessEqual(len(summary), 150)  # Powinno być skrócone
        self.assertIn("EURUSD", summary)  # Powinno zawierać kluczowe informacje
        
    def test_postprocess_response(self):
        """Test postprocessingu odpowiedzi analizy rynku."""
        # Odpowiedź z modelu
        response = """
        Analiza rynku USDJPY:
        
        ```json
        {
            "pair": "USDJPY",
            "timeframe": "H1",
            "trend": "bearish",
            "strength": 0.7,
            "key_levels": {
                "support": [140.00, 139.50],
                "resistance": [141.00, 141.50]
            },
            "sentiment": "bearish",
            "analysis": "Rynek USDJPY znajduje się w krótkoterminowym trendzie spadkowym po nieudanej próbie przebicia oporu na poziomie 141.50. Wskaźniki techniczne wskazują na dalsze spadki."
        }
        ```
        """
        
        # Postprocessing
        processed = self.postprocessor.postprocess_response(response)
        
        # Weryfikacja
        self.assertEqual(processed["pair"], "USDJPY")
        self.assertEqual(processed["trend"], "bearish")
        self.assertEqual(processed["sentiment"], "bearish")
        self.assertEqual(processed["key_levels"]["support"], [140.00, 139.50])
        self.assertEqual(processed["key_levels"]["resistance"], [141.00, 141.50])
        self.assertIn("summary", processed)  # Powinno dodać podsumowanie
        self.assertIn("timestamp", processed)  # Powinno dodać timestamp


if __name__ == '__main__':
    unittest.main() 
"""
Testy dla parsera odpowiedzi LLM.

Ten moduł zawiera testy jednostkowe dla funkcji parsowania i analizy
odpowiedzi z modeli językowych (LLM).
"""

import os
import sys
import unittest
import json
from typing import Dict, Any
from unittest.mock import patch, MagicMock

# Dodanie ścieżki głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM_Engine.response_parser import (
    ResponseParser,
    JSONResponseParser,
    TradeSignalParser,
    MarketAnalysisParser,
    RiskAssessmentParser,
    ResponseParserFactory,
    extract_json_from_response,
    extract_trading_signals,
    parse_market_analysis,
    parse_risk_assessment,
    validate_trade_idea,
    TradeIdeaParser
)

class TestResponseParser(unittest.TestCase):
    """Testy dla funkcji parsujących odpowiedzi z LLM."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Tworzymy konkretną implementację klasy abstrakcyjnej do testów
        class ConcreteResponseParser(ResponseParser):
            def parse(self, response: str) -> Dict[str, Any]:
                return {"parsed": response}
                
        self.parser = ConcreteResponseParser()
    
    def test_clean_response(self):
        """Test czyszczenia odpowiedzi."""
        # Test usuwania nadmiarowych znaków nowej linii
        response = "Linia 1\n\n\n\nLinia 2\n\n\nLinia 3"
        cleaned = self.parser.clean_response(response)
        self.assertEqual(cleaned, "Linia 1\n\nLinia 2\n\nLinia 3")
        
        # Test zachowania bloków kodu
        response = """
        Tekst przed
        ```
        kod
        wewnątrz
        bloku
        ```
        Tekst po
        """
        cleaned = self.parser.clean_response(response)
        # Sprawdzamy czy blok kodu jest zachowany (z możliwymi spacjami)
        self.assertRegex(cleaned, r'```\s*\n\s*kod\s*\n\s*wewnątrz\s*\n\s*bloku\s*\n\s*```')
        
        # Test usuwania nadmiarowych spacji
        response = "  Tekst    z    wieloma    spacjami  "
        cleaned = self.parser.clean_response(response)
        self.assertEqual(cleaned, "Tekst z wieloma spacjami")
        
        # Test pustej odpowiedzi
        self.assertEqual(self.parser.clean_response(""), "")
        self.assertEqual(self.parser.clean_response(None), "")
    
    def test_extract_json_from_response_valid(self):
        """Test ekstraktowania poprawnego formatu JSON z odpowiedzi."""
        # Przykładowa odpowiedź zawierająca JSON
        response = """
        Oto moja analiza rynku:
        
        ```json
        {
            "trend": "bullish",
            "support": 1.2345,
            "resistance": 1.2500,
            "recommendation": "buy"
        }
        ```
        
        Powyższa analiza sugeruje, że warto rozważyć pozycję długą.
        """
        
        # Wywołanie testowanej funkcji
        result = extract_json_from_response(response)
        
        # Weryfikacja
        self.assertIsInstance(result, dict)
        self.assertEqual(result["trend"], "bullish")
        self.assertEqual(result["support"], 1.2345)
        self.assertEqual(result["resistance"], 1.2500)
        self.assertEqual(result["recommendation"], "buy")
    
    def test_extract_json_from_response_invalid(self):
        """Test ekstraktowania niepoprawnego formatu JSON z odpowiedzi."""
        # Odpowiedź z uszkodzonym formatem JSON
        response = """
        Oto moja analiza rynku:
        
        ```json
        {
            "trend": "bullish",
            "support": 1.2345,
            "resistance": 1.2500,
            "recommendation": "buy"
        ```
        
        Powyższa analiza sugeruje, że warto rozważyć pozycję długą.
        """
        
        # Wywołanie testowanej funkcji
        result = extract_json_from_response(response)
        
        # Weryfikacja - powinien zwrócić pusty słownik
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 0)
    
    def test_extract_json_from_response_alternative_format(self):
        """Test ekstraktowania JSON z alternatywnych znaczników."""
        # Odpowiedź z JSON w alternatywnym formacie
        response = """
        Oto moja analiza rynku:
        
        ```
        {
            "trend": "bearish",
            "support": 1.1000,
            "resistance": 1.1500,
            "recommendation": "sell"
        }
        ```
        
        Powyższa analiza sugeruje, że warto rozważyć pozycję krótką.
        """
        
        # Wywołanie testowanej funkcji
        result = extract_json_from_response(response)
        
        # Weryfikacja
        self.assertIsInstance(result, dict)
        self.assertEqual(result["trend"], "bearish")
        self.assertEqual(result["recommendation"], "sell")
    
    def test_extract_trading_signals_valid(self):
        """Test ekstraktowania sygnałów handlowych z odpowiedzi w formacie JSON."""
        response = """
        Bazując na analizie technicznej EURUSD, można zidentyfikować następujące sygnały:
        
        ```json
        {
            "pair": "EURUSD",
            "signal": "buy",
            "entry": 1.0750,
            "stop_loss": 1.0700,
            "take_profit": 1.0850,
            "risk_reward": 2.0,
            "timeframe": "H4",
            "confidence": "high"
        }
        ```
        
        Ten sygnał wynika z przełamania ważnego poziomu oporu.
        """
        
        result = extract_trading_signals(response)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        signal = result[0]
        self.assertEqual(signal["pair"], "EURUSD")
        self.assertEqual(signal["signal"], "buy")
        self.assertEqual(signal["entry"], 1.0750)
        self.assertEqual(signal["stop_loss"], 1.0700)
        self.assertEqual(signal["take_profit"], 1.0850)
        self.assertEqual(signal["confidence"], "high")
        self.assertEqual(signal["timeframe"], "H4")
        self.assertEqual(signal["risk_reward"], 2.0)

    def test_extract_trading_signals_text(self):
        """Test ekstraktowania sygnałów handlowych z tekstu."""
        response = """
        Para: EURUSD
        Sygnał: BUY
        Wejście: 1.0750
        Stop Loss: 1.0700
        Take Profit: 1.0850
        """
        
        result = extract_trading_signals(response)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        signal = result[0]
        self.assertEqual(signal["pair"], "EURUSD")
        self.assertEqual(signal["signal"], "buy")
        self.assertEqual(signal["entry"], 1.0750)
        self.assertEqual(signal["stop_loss"], 1.0700)
        self.assertEqual(signal["take_profit"], 1.0850)

    def test_extract_trading_signals_multiple(self):
        """Test ekstraktowania wielu sygnałów handlowych z odpowiedzi."""
        response = """
        Oto lista sygnałów handlowych na dziś:
        
        Pierwszy sygnał:
        ```json
        {
            "pair": "EURUSD",
            "signal": "buy",
            "entry": 1.0750,
            "stop_loss": 1.0700,
            "take_profit": 1.0850
        }
        ```
        
        Drugi sygnał:
        ```json
        {
            "pair": "GBPUSD",
            "signal": "sell",
            "entry": 1.2600,
            "stop_loss": 1.2650,
            "take_profit": 1.2500
        }
        ```
        """
        
        result = extract_trading_signals(response)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        
        # Sprawdzenie pierwszego sygnału
        self.assertEqual(result[0]["pair"], "EURUSD")
        self.assertEqual(result[0]["signal"], "buy")
        self.assertEqual(result[0]["entry"], 1.0750)
        self.assertEqual(result[0]["stop_loss"], 1.0700)
        self.assertEqual(result[0]["take_profit"], 1.0850)
        
        # Sprawdzenie drugiego sygnału
        self.assertEqual(result[1]["pair"], "GBPUSD")
        self.assertEqual(result[1]["signal"], "sell")
        self.assertEqual(result[1]["entry"], 1.2600)
        self.assertEqual(result[1]["stop_loss"], 1.2650)
        self.assertEqual(result[1]["take_profit"], 1.2500)

    def test_extract_trading_signals_symbol_field(self):
        """Test ekstraktowania sygnałów z polem 'symbol' zamiast 'pair'."""
        response = """
        ```json
        {
            "symbol": "EURUSD",
            "signal": "buy",
            "entry": 1.0750,
            "stop_loss": 1.0700,
            "take_profit": 1.0850
        }
        ```
        """
        
        result = extract_trading_signals(response)
        
        self.assertEqual(len(result), 1)
        signal = result[0]
        self.assertEqual(signal["pair"], "EURUSD")  # Powinno być skonwertowane na 'pair'
        self.assertEqual(signal["signal"], "buy")

    def test_extract_trading_signals_no_signals(self):
        """Test braku sygnałów handlowych w odpowiedzi."""
        response = """
        Obecnie nie ma wyraźnych sygnałów handlowych.
        Rynek znajduje się w fazie konsolidacji.
        """
        
        result = extract_trading_signals(response)
        self.assertEqual(len(result), 0)

    def test_extract_trading_signals_invalid_json(self):
        """Test obsługi niepoprawnego formatu JSON."""
        response = """
        ```json
        {
            "pair": "EURUSD",
            "signal": "buy",
            "entry": 1.0750,  # Niepoprawny JSON z komentarzem
        }
        ```
        """
        
        result = extract_trading_signals(response)
        self.assertEqual(len(result), 0)

    def test_extract_trading_signals_mixed_format(self):
        """Test ekstraktowania sygnałów w mieszanym formacie (JSON + tekst)."""
        response = """
        ```json
        {
            "pair": "EURUSD",
            "signal": "buy",
            "entry": 1.0750,
            "stop_loss": 1.0700,
            "take_profit": 1.0850
        }
        ```
        
        Dodatkowy sygnał:
        Para: GBPUSD
        Sygnał: SELL
        Wejście: 1.2600
        Stop Loss: 1.2650
        Take Profit: 1.2500
        """
        
        result = extract_trading_signals(response)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["pair"], "EURUSD")
        self.assertEqual(result[0]["signal"], "buy")
        self.assertEqual(result[1]["pair"], "GBPUSD")
        self.assertEqual(result[1]["signal"], "sell")
    
    def test_parse_market_analysis(self):
        """Test parsowania analizy rynku."""
        parser = MarketAnalysisParser()
        response = """
        ```json
        {
            "pair": "EURUSD",
            "timeframe": "H4",
            "trend": "bullish",
            "strength": 7,
            "support_levels": [1.0700, 1.0650],
            "resistance_levels": [1.0800, 1.0850],
            "key_levels": {
                "support": [1.0700],
                "resistance": [1.0800]
            },
            "indicators": {
                "rsi": 65,
                "macd": "positive",
                "moving_averages": "uptrend"
            },
            "recommendation": "buy",
            "analysis": "Rynek wykazuje silny trend wzrostowy z potencjałem do dalszych wzrostów."
        }
        ```
        """
        result = parser.parse(response)
        self.assertEqual(result["market"], "EURUSD")
        self.assertEqual(result["trend"], "bullish")
        self.assertEqual(result["strength"], 7)
        self.assertIn("support_levels", result)
        self.assertIn("resistance_levels", result)
        self.assertEqual(len(result["support_levels"]), 2)
        self.assertEqual(len(result["resistance_levels"]), 2)
    
    def test_parse_risk_assessment(self):
        """Test parsowania oceny ryzyka."""
        # Przykładowa odpowiedź zawierająca ocenę ryzyka
        response = """
        ## Ocena ryzyka dla pozycji EURUSD
        
        ```json
        {
            "pair": "EURUSD",
            "position_type": "long",
            "risk_level": "medium",
            "max_loss_percent": 2.5,
            "risk_reward_ratio": 1.8,
            "probability_of_success": 65,
            "market_volatility": "moderate",
            "recommended_position_size": 0.05
        }
        ```
        
        Biorąc pod uwagę aktualną zmienność, zalecam ostrożność.
        """
        
        # Wywołanie testowanej funkcji
        result = parse_risk_assessment(response)
        
        # Weryfikacja
        self.assertIsInstance(result, dict)
        self.assertEqual(result["pair"], "EURUSD")
        self.assertEqual(result["position_type"], "long")
        self.assertEqual(result["risk_level"], "medium")
        self.assertEqual(result["max_loss_percent"], 2.5)
        self.assertEqual(result["probability_of_success"], 65)
    
    def test_validate_trade_idea_valid(self):
        """Test walidacji poprawnej idei handlowej."""
        # Przykładowa poprawna idea handlowa
        trade_idea = {
            "pair": "EURUSD",
            "direction": "buy",
            "entry_price": 1.0750,
            "stop_loss": 1.0700,
            "take_profit": 1.0850,
            "timeframe": "H4",
            "rationale": "Przełamanie linii trendu z potwierdzeniem RSI."
        }
        
        # Wywołanie testowanej funkcji
        result, message = validate_trade_idea(trade_idea)
        
        # Weryfikacja
        self.assertTrue(result)
        self.assertIn("valid", message.lower())
    
    def test_validate_trade_idea_missing_fields(self):
        """Test walidacji idei handlowej z brakującymi polami."""
        # Idea handlowa z brakującymi istotnymi polami
        trade_idea = {
            "pair": "EURUSD",
            "direction": "buy",
            # Brak entry_price
            "stop_loss": 1.0700,
            "take_profit": 1.0850
            # Brak timeframe i rationale
        }
        
        # Wywołanie testowanej funkcji
        result, message = validate_trade_idea(trade_idea)
        
        # Weryfikacja
        self.assertFalse(result)
        self.assertIn("missing", message.lower())
    
    def test_validate_trade_idea_invalid_values(self):
        """Test walidacji idei handlowej z nieprawidłowymi wartościami."""
        # Idea handlowa z nieprawidłowymi wartościami
        trade_idea = {
            "pair": "EURUSD",
            "direction": "invalid_direction",  # Nieprawidłowy kierunek
            "entry_price": "nieprawidłowa cena",  # Nieprawidłowy format ceny
            "stop_loss": 1.0700,
            "take_profit": 1.0850,
            "timeframe": "H4",
            "rationale": "Przełamanie linii trendu."
        }
        
        # Wywołanie testowanej funkcji
        result, message = validate_trade_idea(trade_idea)
        
        # Weryfikacja
        self.assertFalse(result)
        self.assertIn("invalid", message.lower())

class TestResponseParserFactory(unittest.TestCase):
    """Testy dla fabryki parserów odpowiedzi."""
    
    def test_get_json_parser(self):
        """Test tworzenia parsera JSON."""
        parser = ResponseParserFactory.get_parser("json")
        self.assertIsInstance(parser, JSONResponseParser)
    
    def test_get_trade_signal_parser(self):
        """Test tworzenia parsera sygnałów handlowych."""
        parser = ResponseParserFactory.get_parser("trade_signal")
        self.assertIsInstance(parser, TradeSignalParser)
    
    def test_get_market_analysis_parser(self):
        """Test tworzenia parsera analizy rynku."""
        parser = ResponseParserFactory.get_parser("market_analysis")
        self.assertIsInstance(parser, MarketAnalysisParser)
    
    def test_get_risk_assessment_parser(self):
        """Test tworzenia parsera oceny ryzyka."""
        parser = ResponseParserFactory.get_parser("risk_assessment")
        self.assertIsInstance(parser, RiskAssessmentParser)
    
    def test_get_trade_idea_parser(self):
        """Test tworzenia parsera pomysłów handlowych."""
        parser = ResponseParserFactory.get_parser("trade_idea")
        self.assertIsInstance(parser, TradeIdeaParser)
    
    def test_get_invalid_parser_type(self):
        """Test obsługi nieprawidłowego typu parsera."""
        with self.assertRaises(ValueError):
            ResponseParserFactory.get_parser("invalid_type")

class TestJSONResponseParser(unittest.TestCase):
    """Testy dla parsera odpowiedzi JSON."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.parser = JSONResponseParser()
        self.schema = {
            "required": ["type", "data"],
            "properties": {
                "type": "string",
                "data": "object"
            }
        }
    
    def test_parse_valid_json(self):
        """Test parsowania poprawnego JSON."""
        response = '{"type": "analysis", "data": {"value": 42}}'
        result = self.parser.parse(response)
        self.assertEqual(result["type"], "analysis")
        self.assertEqual(result["data"]["value"], 42)
    
    def test_parse_json_in_code_block(self):
        """Test parsowania JSON z bloku kodu."""
        response = """
        ```json
        {
            "type": "analysis",
            "data": {"value": 42}
        }
        ```
        """
        result = self.parser.parse(response)
        self.assertEqual(result["type"], "analysis")
        self.assertEqual(result["data"]["value"], 42)
    
    def test_parse_invalid_json(self):
        """Test parsowania niepoprawnego JSON."""
        response = '{"type": "analysis", "data": {invalid}'
        result = self.parser.parse(response)
        self.assertEqual(result, {})
    
    def test_validate_with_schema(self):
        """Test walidacji JSON ze schematem."""
        parser = JSONResponseParser(schema=self.schema)
        valid_data = {"type": "analysis", "data": {"value": 42}}
        invalid_data = {"type": "analysis"}  # brak wymaganego pola data
        
        # Test poprawnych danych
        valid, errors = parser.validate(valid_data)
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)
        
        # Test niepoprawnych danych
        valid, errors = parser.validate(invalid_data)
        self.assertFalse(valid)
        self.assertGreater(len(errors), 0)
    
    def test_extract_metadata(self):
        """Test ekstrakcji metadanych."""
        response = """
        ```json
        {
            "type": "analysis",
            "data": {"value": 42}
        }
        ```
        """
        metadata = self.parser.extract_metadata(response)
        self.assertIn("timestamp", metadata)
        self.assertIn("length", metadata)
        self.assertTrue(metadata["has_json"])
        self.assertTrue(metadata["has_code_blocks"])

class TestTradeSignalParser(unittest.TestCase):
    """Testy dla klasy TradeSignalParser."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.parser = TradeSignalParser()
        
    def test_parse_valid_json_signal(self):
        """Test parsowania poprawnego sygnału w formacie JSON."""
        response = """
        Analiza techniczna wskazuje na:
        ```json
        {
            "direction": "buy",
            "pair": "EURUSD",
            "entry_price": 1.0950,
            "stop_loss": 1.0900,
            "take_profit": 1.1050,
            "timeframe": "H4",
            "rationale": "Przełamanie linii trendu",
            "additional_conditions": ["RSI > 50", "Trend wzrostowy"]
        }
        ```
        """
        
        result = self.parser.parse(response)
        
        self.assertEqual(len(result), 1)
        signal = result[0]
        self.assertEqual(signal["direction"], "buy")
        self.assertEqual(signal["pair"], "EURUSD")
        self.assertEqual(signal["entry_price"], 1.0950)
        self.assertEqual(signal["stop_loss"], 1.0900)
        self.assertEqual(signal["take_profit"], 1.1050)
        
    def test_parse_valid_text_signal(self):
        """Test parsowania poprawnego sygnału z tekstu."""
        response = """
        Para: EURUSD
        Kierunek: BUY
        Cena wejścia: 1.0950
        Stop Loss: 1.0900
        Take Profit: 1.1050
        Timeframe: H4
        Uzasadnienie: Przełamanie linii trendu
        """
        
        result = self.parser.parse(response)
        
        self.assertEqual(len(result), 1)
        signal = result[0]
        self.assertEqual(signal["signal"], "buy")
        self.assertEqual(signal["pair"], "EURUSD")
        self.assertEqual(signal["entry"], 1.0950)
        self.assertEqual(signal["stop_loss"], 1.0900)
        self.assertEqual(signal["take_profit"], 1.1050)
        self.assertEqual(signal["timeframe"], "H4")
        self.assertEqual(signal["rationale"], "Przełamanie linii trendu")
        
    def test_parse_invalid_signal(self):
        """Test parsowania niepoprawnego sygnału."""
        response = """
        ```json
        {
            "direction": "invalid",
            "symbol": "EURUSD"
        }
        ```
        """
        
        result = self.parser.parse(response)
        self.assertEqual(len(result), 0)
        
    def test_parse_multiple_signals(self):
        """Test parsowania wielu sygnałów."""
        response = """
        ```json
        {
            "direction": "buy",
            "pair": "EURUSD",
            "entry_price": 1.0950,
            "stop_loss": 1.0900,
            "take_profit": 1.1050,
            "timeframe": "H4",
            "rationale": "Przełamanie linii trendu"
        }
        ```
        
        ```json
        {
            "direction": "sell",
            "pair": "GBPUSD",
            "entry_price": 1.2500,
            "stop_loss": 1.2550,
            "take_profit": 1.2400,
            "timeframe": "H4",
            "rationale": "Odrzucenie od oporu"
        }
        ```
        """
        
        result = self.parser.parse(response)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["pair"], "EURUSD")
        self.assertEqual(result[1]["pair"], "GBPUSD")
        
    def test_parse_with_symbol_instead_of_pair(self):
        """Test parsowania sygnału z polem 'symbol' zamiast 'pair'."""
        response = """
        ```json
        {
            "direction": "buy",
            "symbol": "EURUSD",
            "entry_price": 1.0950,
            "stop_loss": 1.0900,
            "take_profit": 1.1050,
            "timeframe": "H4",
            "rationale": "Przełamanie linii trendu"
        }
        ```
        """
        
        result = self.parser.parse(response)
        
        self.assertEqual(len(result), 1)
        signal = result[0]
        self.assertEqual(signal["pair"], "EURUSD")  # Powinno być skonwertowane na 'pair'
        self.assertEqual(signal["direction"], "buy")

class TestMarketAnalysisParser(unittest.TestCase):
    """Testy dla parsera analizy rynku."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.parser = MarketAnalysisParser()
    
    def test_parse_market_analysis(self):
        """Test parsowania analizy rynku."""
        response = """
        ```json
        {
            "market": "EURUSD",
            "timeframe": "H4",
            "trend": "bullish",
            "strength": 7,
            "support_levels": [1.0700, 1.0650],
            "resistance_levels": [1.0800, 1.0850],
            "key_levels": {
                "support": [1.0700],
                "resistance": [1.0800]
            },
            "indicators": {
                "rsi": 65,
                "macd": "positive",
                "moving_averages": "uptrend"
            },
            "recommendation": "buy",
            "analysis": "Rynek wykazuje silny trend wzrostowy z potencjałem do dalszych wzrostów."
        }
        ```
        """
        result = self.parser.parse(response)
        self.assertEqual(result["market"], "EURUSD")
        self.assertEqual(result["trend"], "bullish")
        self.assertEqual(result["strength"], 7)
        self.assertIn("support_levels", result)
        self.assertIn("resistance_levels", result)
        self.assertEqual(len(result["support_levels"]), 2)
        self.assertEqual(len(result["resistance_levels"]), 2)
        
    def test_validate_analysis(self):
        """Test walidacji analizy rynku."""
        valid_analysis = {
            "market": "EURUSD",
            "timeframe": "H4",
            "trend": "bullish",
            "strength": 7,
            "support_levels": [1.0700, 1.0650],
            "resistance_levels": [1.0800, 1.0850],
            "key_levels": {
                "support": [1.0700],
                "resistance": [1.0800]
            },
            "indicators": {
                "rsi": 65,
                "macd": "positive",
                "moving_averages": "uptrend"
            },
            "recommendation": "buy",
            "analysis": "Rynek wykazuje silny trend wzrostowy."
        }
        invalid_analysis = {
            "market": "EURUSD",
            "trend": "invalid"
        }

        # Test poprawnej analizy
        valid, errors = self.parser.validate(valid_analysis)
        self.assertTrue(valid)
        
        # Test niepoprawnej analizy
        valid, errors = self.parser.validate(invalid_analysis)
        self.assertFalse(valid)
        self.assertTrue(len(errors) > 0)
    
    def test_extract_metadata(self):
        """Test ekstrakcji metadanych."""
        response = """
        ```json
        {
            "market": "EURUSD",
            "timeframe": "H4",
            "trend": "bullish"
        }
        ```
        """
        metadata = self.parser.extract_metadata(response)
        self.assertIn("timestamp", metadata)
        self.assertIn("length", metadata)
        self.assertTrue(metadata["has_json"])
        self.assertTrue(metadata["has_code_blocks"])

    def test_standardize_keys_market_mapping(self):
        """Test mapowania różnych kluczy na 'market'."""
        test_cases = [
            ({"pair": "EURUSD"}, "market", "EURUSD"),
            ({"symbol": "EURUSD"}, "market", "EURUSD"),
            ({"instrument": "EURUSD"}, "market", "EURUSD"),
            ({"market": "EURUSD"}, "market", "EURUSD")
        ]
        
        for input_data, expected_key, expected_value in test_cases:
            result = self.parser._standardize_keys(input_data)
            self.assertIn(expected_key, result)
            self.assertEqual(result[expected_key], expected_value)
            
    def test_standardize_keys_trend_conversion(self):
        """Test konwersji trendu na małe litery."""
        test_cases = [
            {"trend": "BULLISH"},
            {"trend": "Bearish"},
            {"trend": "NEUTRAL"},
            {"trend": "SideWays"}
        ]
        
        for input_data in test_cases:
            result = self.parser._standardize_keys(input_data)
            self.assertEqual(result["trend"], input_data["trend"].lower())
            
    def test_standardize_keys_strength_conversion(self):
        """Test konwersji siły trendu."""
        test_cases = [
            ({"strength": "7"}, 7),
            ({"strength": 8}, 8),
            ({"strength": "invalid"}, None),
            ({"strength": "9.5"}, None)
        ]
        
        for input_data, expected_value in test_cases:
            result = self.parser._standardize_keys(input_data)
            if expected_value is None:
                self.assertNotIn("strength", result)
            else:
                self.assertEqual(result["strength"], expected_value)
                
    def test_standardize_keys_levels_conversion(self):
        """Test konwersji poziomów wsparcia i oporu."""
        test_cases = [
            # Pojedyncze wartości
            ({"support": 1.0700}, {"support_levels": [1.0700]}),
            ({"resistance": 1.0800}, {"resistance_levels": [1.0800]}),
            
            # Stringi z wartościami
            ({"support": "1.0700, 1.0650"}, {"support_levels": [1.0700, 1.0650]}),
            ({"resistance": "1.0800,1.0850"}, {"resistance_levels": [1.0800, 1.0850]}),
            
            # Nieprawidłowe wartości
            ({"support": "invalid"}, {"support_levels": []}),
            ({"resistance": "1.0800,invalid"}, {"resistance_levels": []})
        ]
        
        for input_data, expected_output in test_cases:
            result = self.parser._standardize_keys(input_data)
            for key, value in expected_output.items():
                self.assertIn(key, result)
                self.assertEqual(result[key], value)
                
    def test_standardize_keys_combined(self):
        """Test kombinacji różnych konwersji."""
        input_data = {
            "pair": "EURUSD",
            "trend": "BULLISH",
            "strength": "8",
            "support": "1.0700,1.0650",
            "resistance": 1.0800
        }
        
        expected_output = {
            "market": "EURUSD",
            "trend": "bullish",
            "strength": 8,
            "support_levels": [1.0700, 1.0650],
            "resistance_levels": [1.0800]
        }
        
        result = self.parser._standardize_keys(input_data)
        self.assertEqual(result, expected_output)

class TestRiskAssessmentParser(unittest.TestCase):
    """Testy dla parsera oceny ryzyka."""
    
    def setUp(self):
        """Przygotowanie testów."""
        self.parser = RiskAssessmentParser()
        
        self.valid_assessment = {
            "trade_id": "TRADE123",
            "risk_level": "medium",
            "risk_reward_ratio": 2.5,
            "risk_factors": [
                {"factor": "Wysoka zmienność", "impact": "high"},
                {"factor": "Słabe wsparcie", "impact": "medium"}
            ],
            "recommendations": [
                "Zmniejszyć wielkość pozycji",
                "Ustawić szerszy stop loss"
            ]
        }
        
        self.valid_json_response = """```json
        {
            "trade_id": "TRADE123",
            "risk_level": "medium",
            "risk_reward_ratio": 2.5,
            "risk_factors": [
                {"factor": "Wysoka zmienność", "impact": "high"},
                {"factor": "Słabe wsparcie", "impact": "medium"}
            ],
            "recommendations": [
                "Zmniejszyć wielkość pozycji",
                "Ustawić szerszy stop loss"
            ]
        }
        ```"""
    
    def test_parse_valid_json(self):
        """Test parsowania poprawnej odpowiedzi JSON."""
        result = self.parser.parse(self.valid_json_response)
        self.assertEqual(result["trade_id"], "TRADE123")
        self.assertEqual(result["risk_level"], "medium")
        self.assertEqual(result["risk_reward_ratio"], 2.5)
        self.assertEqual(len(result["risk_factors"]), 2)
        self.assertEqual(len(result["recommendations"]), 2)
    
    def test_validate_valid_assessment(self):
        """Test walidacji poprawnej oceny ryzyka."""
        valid, errors = self.parser.validate(self.valid_assessment)
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_missing_required_fields(self):
        """Test walidacji brakujących wymaganych pól."""
        invalid_assessment = {
            "risk_level": "medium"
        }
        valid, errors = self.parser.validate(invalid_assessment)
        self.assertFalse(valid)
        self.assertIn("Brak wymaganego pola: trade_id", errors)
        self.assertIn("Brak wymaganego pola: risk_reward_ratio", errors)
    
    def test_validate_invalid_risk_level(self):
        """Test walidacji nieprawidłowego poziomu ryzyka."""
        invalid_assessment = self.valid_assessment.copy()
        invalid_assessment["risk_level"] = "very_high"
        valid, errors = self.parser.validate(invalid_assessment)
        self.assertFalse(valid)
        self.assertTrue(any("Nieprawidłowy poziom ryzyka" in error for error in errors))
    
    def test_validate_invalid_risk_reward_ratio(self):
        """Test walidacji nieprawidłowego współczynnika risk/reward."""
        invalid_assessment = self.valid_assessment.copy()
        invalid_assessment["risk_reward_ratio"] = -1
        valid, errors = self.parser.validate(invalid_assessment)
        self.assertFalse(valid)
        self.assertIn("risk_reward_ratio musi być dodatnią liczbą", errors)
    
    def test_validate_invalid_risk_factors(self):
        """Test walidacji nieprawidłowych czynników ryzyka."""
        invalid_assessment = self.valid_assessment.copy()
        invalid_assessment["risk_factors"] = [
            {"factor": "Test", "impact": "invalid_impact"}
        ]
        valid, errors = self.parser.validate(invalid_assessment)
        self.assertFalse(valid)
        self.assertTrue(any("impact" in error for error in errors))
    
    def test_validate_invalid_recommendations(self):
        """Test walidacji nieprawidłowych zaleceń."""
        invalid_assessment = self.valid_assessment.copy()
        invalid_assessment["recommendations"] = [123, 456]
        valid, errors = self.parser.validate(invalid_assessment)
        self.assertFalse(valid)
        self.assertIn("każde zalecenie musi być tekstem", errors)
    
    def test_parse_invalid_json(self):
        """Test parsowania nieprawidłowego JSON."""
        invalid_json = "Invalid JSON data"
        result = self.parser.parse(invalid_json)
        self.assertEqual(result, {})

class TestTradeIdeaParser(unittest.TestCase):
    """Testy dla parsera pomysłów handlowych."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.parser = TradeIdeaParser()
        
    def test_parse_valid_trade_idea(self):
        """Test parsowania poprawnego pomysłu handlowego."""
        response = json.dumps({
            "action": "BUY",
            "symbol": "EURUSD",
            "entry_price": 1.0850,
            "stop_loss": 1.0800,
            "take_profit": 1.0950,
            "risk_reward_ratio": 2.0,
            "confidence": 80,
            "timeframe": "H1",
            "reasoning": "Silny trend wzrostowy"
        })
        
        result = self.parser.parse(response)
        
        self.assertEqual(result["action"], "BUY")
        self.assertEqual(result["symbol"], "EURUSD")
        self.assertEqual(result["entry_price"], 1.0850)
        self.assertEqual(result["stop_loss"], 1.0800)
        self.assertEqual(result["take_profit"], 1.0950)
        self.assertEqual(result["risk_reward_ratio"], 2.0)
        self.assertEqual(result["confidence"], 80)
        self.assertEqual(result["timeframe"], "H1")
        self.assertEqual(result["reasoning"], "Silny trend wzrostowy")
        self.assertIn("metadata", result)
        self.assertIn("timestamp", result["metadata"])
        self.assertEqual(result["metadata"]["source"], "trade_idea_parser")
        
    def test_parse_minimal_trade_idea(self):
        """Test parsowania minimalnego pomysłu handlowego."""
        response = json.dumps({
            "action": "HOLD",
            "symbol": "EURUSD"
        })
        
        result = self.parser.parse(response)
        
        self.assertEqual(result["action"], "HOLD")
        self.assertEqual(result["symbol"], "EURUSD")
        self.assertEqual(result["entry_price"], 0)
        self.assertEqual(result["stop_loss"], 0)
        self.assertEqual(result["take_profit"], 0)
        self.assertEqual(result["risk_reward_ratio"], 0)
        self.assertEqual(result["confidence"], 0)
        self.assertEqual(result["timeframe"], "")
        self.assertEqual(result["reasoning"], "")
        
    def test_parse_invalid_trade_idea(self):
        """Test parsowania niepoprawnego pomysłu handlowego."""
        response = json.dumps({
            "action": "INVALID",
            "symbol": "EURUSD"
        })
        
        result = self.parser.parse(response)
        self.assertEqual(result, {})
        
    def test_parse_missing_required_fields(self):
        """Test parsowania pomysłu handlowego bez wymaganych pól."""
        response = json.dumps({
            "entry_price": 1.0850,
            "stop_loss": 1.0800
        })
        
        result = self.parser.parse(response)
        self.assertEqual(result, {})
        
    def test_parse_invalid_numeric_values(self):
        """Test parsowania pomysłu handlowego z nieprawidłowymi wartościami liczbowymi."""
        response = json.dumps({
            "action": "BUY",
            "symbol": "EURUSD",
            "entry_price": "invalid",
            "stop_loss": "invalid"
        })
        
        result = self.parser.parse(response)
        self.assertEqual(result, {})
        
    def test_parse_invalid_confidence(self):
        """Test parsowania pomysłu handlowego z nieprawidłowym poziomem pewności."""
        response = json.dumps({
            "action": "BUY",
            "symbol": "EURUSD",
            "confidence": 150  # Powyżej 100
        })
        
        result = self.parser.parse(response)
        self.assertEqual(result, {})

if __name__ == '__main__':
    unittest.main() 
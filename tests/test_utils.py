"""
Testy dla modułu utils.py zawierającego funkcje pomocnicze dla silnika LLM.
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, mock_open, MagicMock
import tempfile
from pathlib import Path

# Dodanie ścieżki głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM_Engine.utils import (
    load_prompt_template, 
    format_prompt, 
    extract_json_from_response, 
    parse_llm_response,
    prepare_conversation_history,
    get_token_count,
    truncate_text,
    parse_trading_advice
)

class TestUtils(unittest.TestCase):
    """Testy dla funkcji pomocniczych z modułu utils.py."""
    
    def test_load_prompt_template(self):
        """Test ładowania szablonu promptu z pliku."""
        # Test z użyciem mock dla funkcji open
        with patch("builtins.open", mock_open(read_data="To jest szablon promptu.")) as mock_file:
            template = load_prompt_template("template.txt")
            mock_file.assert_called_once_with("template.txt", 'r', encoding='utf-8')
            self.assertEqual(template, "To jest szablon promptu.")
        
        # Test z prawdziwym plikiem tymczasowym
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as temp_file:
            temp_file.write("To jest testowy szablon promptu.")
            temp_path = temp_file.name
        
        try:
            template = load_prompt_template(temp_path)
            self.assertEqual(template, "To jest testowy szablon promptu.")
        finally:
            # Zawsze czyścimy po sobie
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
        # Test z nieistniejącym plikiem
        with self.assertRaises(FileNotFoundError):
            load_prompt_template("nieistniejacy_plik.txt")
    
    def test_format_prompt(self):
        """Test formatowania promptu z podstawieniem zmiennych."""
        # Test podstawowy
        template = "Analizuj rynek {symbol} na interwale {timeframe}."
        variables = {"symbol": "EURUSD", "timeframe": "H1"}
        result = format_prompt(template, variables)
        self.assertEqual(result, "Analizuj rynek EURUSD na interwale H1.")
        
        # Test z brakującymi zmiennymi
        template = "Analizuj rynek {symbol} na interwale {timeframe}."
        variables = {"symbol": "EURUSD"}
        with self.assertRaises(KeyError):
            format_prompt(template, variables)
        
        # Test z dodatkowymi zmiennymi (powinno działać)
        template = "Analizuj rynek {symbol}."
        variables = {"symbol": "EURUSD", "timeframe": "H1"}
        result = format_prompt(template, variables)
        self.assertEqual(result, "Analizuj rynek EURUSD.")
    
    def test_extract_json_from_response(self):
        """Test wyciągania JSON z tekstu odpowiedzi."""
        # Test z blokiem kodu JSON w formacie markdown
        text_with_md_code = """
        Oto analiza rynku:
        
        ```json
        {
          "trend": "bullish",
          "strength": 7
        }
        ```
        """
        result = extract_json_from_response(text_with_md_code)
        self.assertIsNotNone(result)
        self.assertEqual(result["trend"], "bullish")
        self.assertEqual(result["strength"], 7)
        
        # Test z blokiem kodu bez oznaczenia json
        text_with_code = """
        Oto analiza rynku:
        
        ```
        {
          "trend": "bearish",
          "strength": 5
        }
        ```
        """
        result = extract_json_from_response(text_with_code)
        self.assertIsNotNone(result)
        self.assertEqual(result["trend"], "bearish")
        self.assertEqual(result["strength"], 5)
        
        # Test z JSON bezpośrednio w tekście
        text_with_json = """
        Oto wynik:
        
        {
          "trend": "neutral",
          "strength": 3
        }
        """
        result = extract_json_from_response(text_with_json)
        self.assertIsNotNone(result)
        self.assertEqual(result["trend"], "neutral")
        self.assertEqual(result["strength"], 3)
        
        # Test z tablicą JSON
        text_with_array = """
        Oto wynik:
        
        [
          {"symbol": "EURUSD", "trend": "bullish"},
          {"symbol": "GBPUSD", "trend": "bearish"}
        ]
        """
        result = extract_json_from_response(text_with_array)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["symbol"], "EURUSD")
        
        # Test z niepoprawnym JSON
        text_with_invalid_json = """
        Oto wynik analizy:
        
        {
          "trend": "bearish",
          strength: 5,
          "key_levels: {
            "support": [1.0780, 1.0750]
          }
        }
        """
        result = extract_json_from_response(text_with_invalid_json)
        self.assertIsNone(result)
    
    def test_parse_llm_response(self):
        """Test parsowania odpowiedzi z różnych modeli LLM."""
        # Test odpowiedzi Ollama
        ollama_response = {"response": "To jest odpowiedź z Ollama."}
        result = parse_llm_response(ollama_response)
        self.assertEqual(result, "To jest odpowiedź z Ollama.")
        
        # Test odpowiedzi OpenAI (format ChatCompletion)
        openai_chat_response = {
            "choices": [
                {
                    "message": {
                        "content": "To jest odpowiedź z OpenAI Chat."
                    }
                }
            ]
        }
        result = parse_llm_response(openai_chat_response)
        self.assertEqual(result, "To jest odpowiedź z OpenAI Chat.")
        
        # Test odpowiedzi OpenAI (format Completion)
        openai_completion_response = {
            "choices": [
                {
                    "text": "To jest odpowiedź z OpenAI Completion."
                }
            ]
        }
        result = parse_llm_response(openai_completion_response)
        self.assertEqual(result, "To jest odpowiedź z OpenAI Completion.")
        
        # Test odpowiedzi Claude/Anthropic
        claude_response = {"content": "To jest odpowiedź z Claude."}
        result = parse_llm_response(claude_response)
        self.assertEqual(result, "To jest odpowiedź z Claude.")
        
        # Test nieznany format
        unknown_response = {"unknown_field": "unknown_value"}
        result = parse_llm_response(unknown_response)
        self.assertEqual(result, "")
    
    def test_prepare_conversation_history(self):
        """Test przygotowania historii konwersacji w formacie tekstowym."""
        # Test podstawowy
        messages = [
            {"role": "system", "content": "Jesteś pomocnym asystentem tradingowym."},
            {"role": "user", "content": "Jak wygląda rynek EURUSD?"},
            {"role": "assistant", "content": "Rynek EURUSD wykazuje trend wzrostowy."}
        ]
        expected = "System: Jesteś pomocnym asystentem tradingowym.\n\nUżytkownik: Jak wygląda rynek EURUSD?\n\nAsystent: Rynek EURUSD wykazuje trend wzrostowy."
        result = prepare_conversation_history(messages)
        self.assertEqual(result, expected)
        
        # Test z nieznana rolą
        messages = [
            {"role": "custom", "content": "To jest niestandardowa wiadomość."}
        ]
        expected = "Custom: To jest niestandardowa wiadomość."
        result = prepare_conversation_history(messages)
        self.assertEqual(result, expected)
        
        # Test z brakującymi polami
        messages = [
            {"role": "user"},
            {"content": "Brak roli"}
        ]
        expected = "Użytkownik: \n\n: Brak roli"
        result = prepare_conversation_history(messages)
        self.assertEqual(result, expected)
    
    def test_get_token_count(self):
        """Test szacowania liczby tokenów w tekście."""
        # Test podstawowy
        text = "To jest test liczenia tokenów."
        # ~6-7 tokenów (przy założeniu 4 znaki na token)
        estimated_tokens = get_token_count(text)
        self.assertGreaterEqual(estimated_tokens, 5)
        self.assertLessEqual(estimated_tokens, 10)
        
        # Test z długim tekstem
        long_text = "A" * 400  # 400 znaków
        estimated_tokens = get_token_count(long_text)
        self.assertEqual(estimated_tokens, 100)  # 400 / 4 = 100
    
    def test_truncate_text(self):
        """Test obcinania tekstu do określonej liczby tokenów."""
        # Test gdy tekst jest krótszy niż limit
        text = "To jest krótki tekst."
        max_tokens = 10
        result = truncate_text(text, max_tokens)
        self.assertEqual(result, text)  # Tekst nie powinien być zmieniony
        
        # Test gdy tekst jest dłuższy niż limit
        text = "To jest dłuższy tekst, który powinien zostać obcięty po przekroczeniu limitu tokenów."
        max_tokens = 5
        result = truncate_text(text, max_tokens)
        self.assertTrue(len(result) < len(text))
        self.assertTrue(result.endswith("..."))
    
    def test_parse_trading_advice_json(self):
        """Test parsowania porady tradingowej w formacie JSON."""
        # Test z kompletnym JSON
        json_response = """
        {
          "action": "BUY",
          "symbol": "EURUSD",
          "entry_price": 1.0750,
          "stop_loss": 1.0700,
          "take_profit": 1.0850,
          "timeframe": "H1",
          "confidence": 80,
          "reasoning": "Trend wzrostowy potwierdzony przez RSI i MACD."
        }
        """
        result = parse_trading_advice(json_response)
        self.assertEqual(result["action"], "BUY")
        self.assertEqual(result["symbol"], "EURUSD")
        self.assertEqual(result["entry_price"], 1.0750)
        
        # Test z minimalnym JSON
        minimal_json = """
        {
          "action": "SELL",
          "symbol": "GBPUSD"
        }
        """
        result = parse_trading_advice(minimal_json)
        self.assertEqual(result["action"], "SELL")
        self.assertEqual(result["symbol"], "GBPUSD")
        self.assertIsNone(result["entry_price"])
    
    def test_parse_trading_advice_text(self):
        """Test parsowania porady tradingowej z tekstu."""
        # Test parsowania z tekstu
        text_advice = """
        Analiza rynku EURUSD na interwale H4
        
        Akcja: KUPUJ
        Symbol: EURUSD
        Cena wejścia: 1.0750
        Stop Loss: 1.0700
        Take Profit: 1.0850
        Pewność: 75%
        
        Uzasadnienie: Rynek wykazuje silne oznaki wzrostu, RSI w strefie wykupienia.
        """
        result = parse_trading_advice(text_advice)
        self.assertEqual(result["action"], "BUY")  # KUPUJ zmapowane na BUY
        self.assertEqual(result["symbol"], "EURUSD")
        self.assertEqual(result["entry_price"], 1.0750)
        self.assertEqual(result["stop_loss"], 1.0700)
        self.assertEqual(result["take_profit"], 1.0850)
        self.assertEqual(result["confidence"], 75)
        
        # Test niepoprawnej odpowiedzi
        invalid_text = "Nie mam wystarczających informacji, aby udzielić rekomendacji tradingowej."
        with self.assertRaises(ValueError):
            parse_trading_advice(invalid_text)


if __name__ == '__main__':
    unittest.main() 
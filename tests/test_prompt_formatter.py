"""
Testy dla formatera promptów LLM.

Ten moduł zawiera testy jednostkowe dla funkcjonalności związanych 
z formatowaniem promptów dla modeli językowych (LLM).
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Dodanie ścieżki głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM_Engine.prompt_formatter import (
    PromptFormatter,
    TradingPromptFormatter,
    ConversationFormatter,
    JSONOutputFormatter
)

class TestPromptFormatter(unittest.TestCase):
    """Testy dla bazowej klasy PromptFormatter i jej metod."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.formatter = PromptFormatter()
        
    def test_init(self):
        """Test inicjalizacji formatera promptów."""
        self.assertEqual(self.formatter.system_template, "")
        self.assertEqual(self.formatter.user_template, "")
        self.assertEqual(self.formatter.template_variables, {})
        
    def test_set_system_template(self):
        """Test ustawiania szablonu systemowego."""
        system_template = "Jesteś ekspertem od analizy rynków finansowych."
        self.formatter.set_system_template(system_template)
        self.assertEqual(self.formatter.system_template, system_template)
        
    def test_set_user_template(self):
        """Test ustawiania szablonu użytkownika."""
        user_template = "Przeanalizuj aktualną sytuację na rynku {market}."
        self.formatter.set_user_template(user_template)
        self.assertEqual(self.formatter.user_template, user_template)
        
    def test_add_variable(self):
        """Test dodawania zmiennej do szablonu."""
        self.formatter.add_variable("market", "forex")
        self.assertEqual(self.formatter.template_variables["market"], "forex")
        
    def test_add_variables(self):
        """Test dodawania wielu zmiennych do szablonu."""
        variables = {"market": "forex", "pair": "EURUSD"}
        self.formatter.add_variables(variables)
        self.assertEqual(self.formatter.template_variables["market"], "forex")
        self.assertEqual(self.formatter.template_variables["pair"], "EURUSD")
        
    def test_format(self):
        """Test formatowania promptu."""
        # Konfiguracja formatera
        self.formatter.set_system_template("Jesteś ekspertem od {market}.")
        self.formatter.set_user_template("Przeanalizuj parę {pair} na interwale {timeframe}.")
        self.formatter.add_variables({
            "market": "forex",
            "pair": "EURUSD",
            "timeframe": "H4"
        })
        
        # Formatowanie promptu
        prompt = self.formatter.format()
        
        # Weryfikacja
        self.assertEqual(prompt["system"], "Jesteś ekspertem od forex.")
        self.assertEqual(prompt["user"], "Przeanalizuj parę EURUSD na interwale H4.")
        
    def test_format_with_missing_variables(self):
        """Test formatowania promptu z brakującymi zmiennymi."""
        # Konfiguracja formatera
        self.formatter.set_system_template("Jesteś ekspertem od {market}.")
        self.formatter.set_user_template("Przeanalizuj parę {pair} na interwale {timeframe}.")
        self.formatter.add_variable("market", "forex")
        self.formatter.add_variable("pair", "EURUSD")
        # Brak zmiennej timeframe
        
        # Próba formatowania promptu
        with self.assertRaises(KeyError):
            self.formatter.format()
    
    def test_reset(self):
        """Test resetowania formatera promptów."""
        # Konfiguracja formatera
        self.formatter.set_system_template("Jesteś ekspertem od analizy rynków.")
        self.formatter.set_user_template("Przeanalizuj sytuację na rynku.")
        self.formatter.add_variable("market", "forex")
        
        # Reset formatera
        self.formatter.reset()
        
        # Weryfikacja
        self.assertEqual(self.formatter.system_template, "")
        self.assertEqual(self.formatter.user_template, "")
        self.assertEqual(self.formatter.template_variables, {})


class TestTradingPromptFormatter(unittest.TestCase):
    """Testy dla klasy TradingPromptFormatter."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.formatter = TradingPromptFormatter()
        
    def test_init(self):
        """Test inicjalizacji formatera promptów handlowych."""
        # Sprawdzenie domyślnych wartości
        self.assertIn("trading expert", self.formatter.system_template.lower())
        
    def test_format_market_analysis_prompt(self):
        """Test formatowania promptu analizy rynku."""
        # Konfiguracja formatera
        self.formatter.add_variables({
            "pair": "EURUSD",
            "timeframe": "H4",
            "context": "Rynek znajduje się w trendzie wzrostowym."
        })
        
        # Formatowanie promptu analizy rynku
        prompt = self.formatter.format_market_analysis_prompt()
        
        # Weryfikacja
        self.assertIn("EURUSD", prompt["user"])
        self.assertIn("H4", prompt["user"])
        self.assertIn("Rynek znajduje się w trendzie wzrostowym", prompt["user"])
        
    def test_format_trade_signal_prompt(self):
        """Test formatowania promptu sygnału handlowego."""
        # Konfiguracja formatera
        self.formatter.add_variables({
            "pair": "EURUSD",
            "timeframe": "H4",
            "rsi": 65,
            "macd": "bullish crossover"
        })
        
        # Formatowanie promptu sygnału handlowego
        prompt = self.formatter.format_trade_signal_prompt()
        
        # Weryfikacja
        self.assertIn("EURUSD", prompt["user"])
        self.assertIn("H4", prompt["user"])
        self.assertIn("RSI", prompt["user"].upper())
        self.assertIn("65", prompt["user"])
        self.assertIn("MACD", prompt["user"].upper())
        self.assertIn("bullish crossover", prompt["user"].lower())
        
    def test_format_risk_assessment_prompt(self):
        """Test formatowania promptu oceny ryzyka."""
        # Konfiguracja formatera
        self.formatter.add_variables({
            "pair": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.0950,
            "stop_loss": 1.0900,
            "take_profit": 1.1050,
            "account_balance": 10000,
            "risk_percentage": 2
        })
        
        # Formatowanie promptu oceny ryzyka
        prompt = self.formatter.format_risk_assessment_prompt()
        
        # Weryfikacja
        self.assertIn("EURUSD", prompt["user"])
        self.assertIn("BUY", prompt["user"])
        self.assertIn("1.095", prompt["user"])
        self.assertIn("1.09", prompt["user"])
        self.assertIn("1.105", prompt["user"])
        self.assertIn("10000", prompt["user"])
        self.assertIn("2", prompt["user"])
        self.assertIn("risk", prompt["user"].lower())


class TestConversationFormatter(unittest.TestCase):
    """Testy dla klasy ConversationFormatter."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.formatter = ConversationFormatter()
        
    def test_init(self):
        """Test inicjalizacji formatera konwersacji."""
        self.assertEqual(self.formatter.system_template, "")
        self.assertEqual(self.formatter.messages, [])
        
    def test_set_system_message(self):
        """Test ustawiania wiadomości systemowej."""
        system_message = "Jesteś ekspertem od analizy rynków finansowych."
        self.formatter.set_system_message(system_message)
        self.assertEqual(self.formatter.system_template, system_message)
        
    def test_add_user_message(self):
        """Test dodawania wiadomości użytkownika."""
        message = "Przeanalizuj parę EURUSD."
        self.formatter.add_user_message(message)
        
        # Weryfikacja
        self.assertEqual(len(self.formatter.messages), 1)
        self.assertEqual(self.formatter.messages[0]["role"], "user")
        self.assertEqual(self.formatter.messages[0]["content"], message)
        
    def test_add_assistant_message(self):
        """Test dodawania wiadomości asystenta."""
        message = "EURUSD jest obecnie w trendzie wzrostowym."
        self.formatter.add_assistant_message(message)
        
        # Weryfikacja
        self.assertEqual(len(self.formatter.messages), 1)
        self.assertEqual(self.formatter.messages[0]["role"], "assistant")
        self.assertEqual(self.formatter.messages[0]["content"], message)
        
    def test_format_conversation(self):
        """Test formatowania konwersacji."""
        # Konfiguracja formatera
        system_message = "Jesteś ekspertem od analizy rynków finansowych."
        self.formatter.set_system_message(system_message)
        
        # Dodanie wiadomości
        self.formatter.add_user_message("Przeanalizuj parę EURUSD.")
        self.formatter.add_assistant_message("EURUSD jest obecnie w trendzie wzrostowym.")
        self.formatter.add_user_message("Jakie są perspektywy?")
        
        # Formatowanie konwersacji
        conversation = self.formatter.format_conversation()
        
        # Weryfikacja
        self.assertEqual(len(conversation), 4)  # system + 3 wiadomości
        self.assertEqual(conversation[0]["role"], "system")
        self.assertEqual(conversation[0]["content"], system_message)
        self.assertEqual(conversation[1]["role"], "user")
        self.assertEqual(conversation[1]["content"], "Przeanalizuj parę EURUSD.")
        self.assertEqual(conversation[2]["role"], "assistant")
        self.assertEqual(conversation[2]["content"], "EURUSD jest obecnie w trendzie wzrostowym.")
        self.assertEqual(conversation[3]["role"], "user")
        self.assertEqual(conversation[3]["content"], "Jakie są perspektywy?")
        
    def test_get_last_n_messages(self):
        """Test pobierania ostatnich n wiadomości."""
        # Konfiguracja formatera
        system_message = "Jesteś ekspertem od analizy rynków finansowych."
        self.formatter.set_system_message(system_message)
        
        # Dodanie wiadomości
        self.formatter.add_user_message("Wiadomość 1")
        self.formatter.add_assistant_message("Odpowiedź 1")
        self.formatter.add_user_message("Wiadomość 2")
        self.formatter.add_assistant_message("Odpowiedź 2")
        self.formatter.add_user_message("Wiadomość 3")
        
        # Pobranie ostatnich 2 wiadomości
        last_messages = self.formatter.get_last_n_messages(2)
        
        # Weryfikacja
        self.assertEqual(len(last_messages), 2)
        self.assertEqual(last_messages[0]["content"], "Odpowiedź 2")
        self.assertEqual(last_messages[1]["content"], "Wiadomość 3")
    
    def test_clear_messages(self):
        """Test czyszczenia wiadomości."""
        # Konfiguracja formatera
        self.formatter.set_system_message("Wiadomość systemowa")
        self.formatter.add_user_message("Wiadomość użytkownika")
        self.formatter.add_assistant_message("Odpowiedź asystenta")
        
        # Czyszczenie wiadomości
        self.formatter.clear_messages()
        
        # Weryfikacja
        self.assertEqual(len(self.formatter.messages), 0)
        self.assertNotEqual(self.formatter.system_template, "")  # System message powinien pozostać


class TestJSONOutputFormatter(unittest.TestCase):
    """Testy dla klasy JSONOutputFormatter."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.formatter = JSONOutputFormatter()
        
    def test_init(self):
        """Test inicjalizacji formatera wyjścia JSON."""
        # Weryfikacja domyślnych wartości
        self.assertIn("json", self.formatter.system_template.lower())
        self.assertEqual(self.formatter.json_schema, {})
        
    def test_set_json_schema(self):
        """Test ustawiania schematu JSON."""
        schema = {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["BUY", "SELL"]},
                "entry_price": {"type": "number"},
                "stop_loss": {"type": "number"},
                "take_profit": {"type": "number"}
            },
            "required": ["direction", "entry_price", "stop_loss", "take_profit"]
        }
        
        self.formatter.set_json_schema(schema)
        
        # Weryfikacja
        self.assertEqual(self.formatter.json_schema, schema)
        
    def test_format_json_prompt(self):
        """Test formatowania promptu JSON."""
        # Konfiguracja formatera
        schema = {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["BUY", "SELL"]},
                "entry_price": {"type": "number"},
                "stop_loss": {"type": "number"},
                "take_profit": {"type": "number"}
            },
            "required": ["direction", "entry_price", "stop_loss", "take_profit"]
        }
        self.formatter.set_json_schema(schema)
        
        self.formatter.add_variables({
            "pair": "EURUSD",
            "timeframe": "H4",
            "context": "Rynek znajduje się w trendzie wzrostowym."
        })
        
        # Formatowanie promptu JSON
        prompt = self.formatter.format_json_prompt("Wygeneruj sygnał handlowy dla pary {pair} na interwale {timeframe}. Kontekst: {context}")
        
        # Weryfikacja
        self.assertIn("json", prompt["system"].lower())
        self.assertIn("EURUSD", prompt["user"])
        self.assertIn("H4", prompt["user"])
        self.assertIn("Rynek znajduje się w trendzie wzrostowym", prompt["user"])
        
        # Sprawdzenie, czy schemat jest w promptie systemowym
        for key in schema["properties"]:
            self.assertIn(key, prompt["system"])
        
    def test_format_json_prompt_with_custom_system_template(self):
        """Test formatowania promptu JSON z niestandardowym szablonem systemowym."""
        # Konfiguracja formatera
        custom_system_template = "Jesteś ekspertem od analizy rynków. Odpowiadaj wyłącznie w formacie JSON."
        self.formatter.set_system_template(custom_system_template)
        
        schema = {
            "type": "object",
            "properties": {
                "trend": {"type": "string", "enum": ["bullish", "bearish", "sideways"]},
                "strength": {"type": "number", "minimum": 1, "maximum": 10}
            },
            "required": ["trend", "strength"]
        }
        self.formatter.set_json_schema(schema)
        
        # Formatowanie promptu JSON
        prompt = self.formatter.format_json_prompt("Przeanalizuj trend rynku.")
        
        # Weryfikacja
        self.assertEqual(prompt["user"], "Przeanalizuj trend rynku.")
        self.assertIn(custom_system_template, prompt["system"])
        for key in schema["properties"]:
            self.assertIn(key, prompt["system"])


if __name__ == '__main__':
    unittest.main() 
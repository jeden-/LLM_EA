"""
Testy dla menedżera promptów LLM.

Ten moduł zawiera testy jednostkowe dla funkcjonalności związanych
z zarządzaniem promptami dla modeli językowych (LLM).
"""

import os
import sys
import unittest
import json
from unittest.mock import patch, MagicMock, mock_open
from typing import List, Dict, Any

# Dodanie ścieżki głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM_Engine.prompt_manager import (
    PromptManager,
    load_prompt_template,
    save_prompt_template,
    get_available_templates,
    format_system_prompt,
    create_chat_messages
)

class TestPromptManager(unittest.TestCase):
    """Testy dla klasy PromptManager i powiązanych funkcji."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Utworzenie katalogu tymczasowego na szablony promptów
        self.test_templates_dir = os.path.join(os.path.dirname(__file__), 'test_data', 'templates')
        os.makedirs(self.test_templates_dir, exist_ok=True)
        
        # Utworzenie przykładowego szablonu prompt
        self.sample_template = {
            "name": "market_analysis",
            "description": "Szablon do analizy rynku",
            "system_prompt": "Jesteś ekspertem od analizy rynku forex.",
            "user_prompt": "Przeanalizuj parę walutową {pair} na interwale {timeframe}.",
            "version": "1.0",
            "tags": ["forex", "analiza"]
        }
        
        # Zapisanie przykładowego szablonu do pliku
        template_path = os.path.join(self.test_templates_dir, "market_analysis.json")
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(self.sample_template, f, ensure_ascii=False, indent=2)
        
        # Inicjalizacja PromptManager z testowym katalogiem
        self.prompt_manager = PromptManager(templates_dir=self.test_templates_dir)
    
    def tearDown(self):
        """Czyszczenie po testach."""
        # Usunięcie testowych plików szablonów
        for filename in os.listdir(self.test_templates_dir):
            file_path = os.path.join(self.test_templates_dir, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)
    
    def test_init(self):
        """Test inicjalizacji menedżera promptów."""
        # Sprawdzenie, czy menedżer został poprawnie zainicjalizowany
        self.assertEqual(self.prompt_manager.templates_dir, self.test_templates_dir)
        self.assertIsInstance(self.prompt_manager.templates_cache, dict)
        
        # Sprawdzenie, czy cache został załadowany
        self.assertIn("market_analysis", self.prompt_manager.templates_cache)
    
    def test_load_template(self):
        """Test ładowania szablonu promptu."""
        # Załadowanie szablonu
        template = self.prompt_manager.load_template("market_analysis")
        
        # Weryfikacja
        self.assertEqual(template["name"], "market_analysis")
        self.assertEqual(template["description"], "Szablon do analizy rynku")
        self.assertEqual(template["system_prompt"], "Jesteś ekspertem od analizy rynku forex.")
    
    def test_load_template_not_found(self):
        """Test ładowania nieistniejącego szablonu."""
        # Próba załadowania nieistniejącego szablonu
        with self.assertRaises(ValueError):
            self.prompt_manager.load_template("nonexistent_template")
    
    def test_save_template(self):
        """Test zapisywania szablonu promptu."""
        # Utworzenie nowego szablonu
        new_template = {
            "name": "trade_idea",
            "description": "Szablon do generowania pomysłów handlowych",
            "system_prompt": "Jesteś ekspertem od tradingu.",
            "user_prompt": "Podaj pomysł handlowy dla pary {pair}.",
            "parameters": ["pair"],
            "version": "1.0",
            "tags": ["trading", "pomysły"]
        }
        
        # Zapisanie szablonu
        self.prompt_manager.save_template(new_template)
        
        # Weryfikacja zapisu
        template_path = os.path.join(self.test_templates_dir, "trade_idea.json")
        self.assertTrue(os.path.exists(template_path))
        
        # Odczyt zapisanego szablonu
        with open(template_path, 'r', encoding='utf-8') as f:
            loaded_template = json.load(f)
        
        # Weryfikacja zawartości
        self.assertEqual(loaded_template["name"], "trade_idea")
        self.assertEqual(loaded_template["description"], "Szablon do generowania pomysłów handlowych")
    
    def test_update_template(self):
        """Test aktualizacji istniejącego szablonu."""
        # Modyfikacja istniejącego szablonu
        updated_template = dict(self.sample_template)
        updated_template["description"] = "Zaktualizowany opis szablonu"
        updated_template["version"] = "1.1"
        
        # Aktualizacja szablonu
        self.prompt_manager.save_template(updated_template)
        
        # Weryfikacja aktualizacji
        template = self.prompt_manager.load_template("market_analysis")
        self.assertEqual(template["description"], "Zaktualizowany opis szablonu")
        self.assertEqual(template["version"], "1.1")
    
    def test_list_templates(self):
        """Test listowania dostępnych szablonów."""
        # Dodanie drugiego szablonu
        new_template = {
            "name": "risk_assessment",
            "description": "Szablon do oceny ryzyka",
            "system_prompt": "Jesteś ekspertem od zarządzania ryzykiem.",
            "user_prompt": "Oceń ryzyko dla transakcji {direction} na parze {pair}.",
            "parameters": ["pair", "direction"],
            "version": "1.0",
            "tags": ["ryzyko", "zarządzanie"]
        }
        self.prompt_manager.save_template(new_template)
        
        # Listowanie szablonów
        templates = self.prompt_manager.list_templates()
        
        # Weryfikacja
        self.assertIsInstance(templates, list)
        self.assertEqual(len(templates), 2)
        template_names = [t["name"] for t in templates]
        self.assertIn("market_analysis", template_names)
        self.assertIn("risk_assessment", template_names)
    
    def test_format_prompt(self):
        """Test formatowania promptu z parametrami."""
        # Formatowanie promptu
        formatted_prompt = self.prompt_manager.format_prompt(
            "market_analysis",
            pair="EURUSD",
            timeframe="H4"
        )
        
        # Weryfikacja
        self.assertIn("Przeanalizuj parę walutową EURUSD na interwale H4", formatted_prompt["user_prompt"])
        self.assertEqual(formatted_prompt["system_prompt"], "Jesteś ekspertem od analizy rynku forex.")
    
    def test_format_prompt_missing_params(self):
        """Test formatowania promptu z brakującymi parametrami."""
        # Próba formatowania promptu z brakującym parametrem
        with self.assertRaises(ValueError):
            self.prompt_manager.format_prompt(
                "market_analysis",
                pair="EURUSD"
                # Brak timeframe
            )
    
    def test_delete_template(self):
        """Test usuwania szablonu promptu."""
        # Usunięcie szablonu
        self.prompt_manager.delete_template("market_analysis")
        
        # Weryfikacja usunięcia
        template_path = os.path.join(self.test_templates_dir, "market_analysis.json")
        self.assertFalse(os.path.exists(template_path))
        
        # Weryfikacja usunięcia z cache
        self.assertNotIn("market_analysis", self.prompt_manager.templates_cache)
    
    def test_delete_nonexistent_template(self):
        """Test usuwania nieistniejącego szablonu."""
        # Próba usunięcia nieistniejącego szablonu
        with self.assertRaises(ValueError):
            self.prompt_manager.delete_template("nonexistent_template")
    
    def test_create_template(self):
        """Test tworzenia nowego szablonu promptu."""
        # Dane do utworzenia szablonu
        template_data = {
            "name": "sentiment_analysis",
            "description": "Analiza sentymentu rynku",
            "system_prompt": "Jesteś ekspertem od analizy sentymentu rynku.",
            "user_prompt": "Przeanalizuj sentyment rynku dla {instrument} na podstawie {data_source}.",
            "metadata": {
                "parameters": ["instrument", "data_source"],
                "tags": ["sentyment", "analiza"]
            }
        }
        
        # Utworzenie szablonu
        self.prompt_manager.create_template(**template_data)
        
        # Weryfikacja utworzenia
        template = self.prompt_manager.get_template("sentiment_analysis")
        self.assertIsNotNone(template)
        self.assertEqual(template.description, "Analiza sentymentu rynku")
        self.assertEqual(template.metadata.get("parameters"), ["instrument", "data_source"])
        self.assertEqual(template.metadata.get("tags"), ["sentyment", "analiza"])
    
    def test_search_templates(self):
        """Test wyszukiwania szablonów po tagach."""
        # Dodanie kilku szablonów z różnymi tagami
        templates = [
            {
                "name": "technical_analysis",
                "description": "Analiza techniczna",
                "system_prompt": "Jesteś ekspertem od analizy technicznej.",
                "user_prompt": "Wykonaj analizę techniczną dla {pair}.",
                "version": "1.0",
                "metadata": {"tags": ["forex", "analiza", "techniczna"]}
            },
            {
                "name": "fundamental_analysis",
                "description": "Analiza fundamentalna",
                "system_prompt": "Jesteś ekspertem od analizy fundamentalnej.",
                "user_prompt": "Wykonaj analizę fundamentalną dla {pair}.",
                "version": "1.0",
                "metadata": {"tags": ["forex", "analiza", "fundamentalna"]}
            }
        ]
        
        for template in templates:
            self.prompt_manager.save_template(template)
        
        # Wyszukiwanie szablonów po tagu
        results = self.prompt_manager.search_templates(tags=["forex"])
        self.assertEqual(len(results), 2)  # 2 szablony z tagiem "forex"
        
        results = self.prompt_manager.search_templates(tags=["fundamentalna"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "fundamental_analysis")
        
        results = self.prompt_manager.search_templates(tags=["analiza", "techniczna"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "technical_analysis")
    
    def test_standalone_load_prompt_template(self):
        """Test samodzielnej funkcji load_prompt_template."""
        # Wywołanie funkcji
        template = load_prompt_template("market_analysis", self.test_templates_dir)
        
        # Weryfikacja
        self.assertEqual(template["name"], "market_analysis")
        self.assertEqual(template["description"], "Szablon do analizy rynku")
        self.assertEqual(template["system_prompt"], "Jesteś ekspertem od analizy rynku forex.")
    
    def test_standalone_save_prompt_template(self):
        """Test samodzielnej funkcji save_prompt_template."""
        # Przygotowanie nowego szablonu
        new_template = {
            "name": "test_template",
            "description": "Test template",
            "system_prompt": "Test system prompt",
            "user_prompt": "Test user prompt",
            "version": "1.0",
            "tags": ["test"]
        }
        
        # Wywołanie funkcji
        result = save_prompt_template(new_template, self.test_templates_dir)
        
        # Weryfikacja
        self.assertTrue(result)
        template_path = os.path.join(self.test_templates_dir, "test_template.json")
        self.assertTrue(os.path.exists(template_path))
        
        # Sprawdzenie zawartości zapisanego pliku
        with open(template_path, 'r', encoding='utf-8') as f:
            loaded_template = json.load(f)
            self.assertEqual(loaded_template, new_template)
    
    def test_standalone_get_available_templates(self):
        """Test samodzielnej funkcji get_available_templates."""
        # Wywołanie funkcji
        templates = get_available_templates(self.test_templates_dir)
        
        # Weryfikacja
        self.assertIsInstance(templates, list)
        self.assertTrue(len(templates) > 0)
        template_names = [t["name"] for t in templates]
        self.assertIn("market_analysis", template_names)
    
    def test_format_system_prompt(self):
        """Test funkcji formatującej prompt systemowy."""
        # Przykładowy prompt systemowy z parametrami
        system_prompt = "Jesteś ekspertem od analizy {market_type}. Twój styl to {style}."
        params = {"market_type": "forex", "style": "techniczny"}
        
        # Wywołanie funkcji
        formatted = format_system_prompt(system_prompt, **params)
        
        # Weryfikacja
        self.assertEqual(formatted, "Jesteś ekspertem od analizy forex. Twój styl to techniczny.")
    
    def test_create_chat_messages(self):
        """Test funkcji tworzącej wiadomości do czatu."""
        # Dane wejściowe
        system_prompt = "Jesteś ekspertem od analizy rynku."
        user_prompt = "Przeanalizuj EURUSD."
        
        # Wywołanie funkcji
        messages = create_chat_messages(system_prompt, user_prompt)
        
        # Weryfikacja
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], system_prompt)
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[1]["content"], user_prompt)
    
    def test_create_chat_messages_with_history(self):
        """Test funkcji tworzącej wiadomości do czatu z historią."""
        # Dane wejściowe
        system_prompt = "Jesteś ekspertem od analizy rynku."
        user_prompt = "Przeanalizuj EURUSD."
        history = [
            {"role": "user", "content": "Jaki jest trend?"},
            {"role": "assistant", "content": "Trend jest wzrostowy."}
        ]
        
        # Wywołanie funkcji
        messages = create_chat_messages(system_prompt, user_prompt, history)
        
        # Weryfikacja
        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[1]["content"], "Jaki jest trend?")
        self.assertEqual(messages[2]["role"], "assistant")
        self.assertEqual(messages[2]["content"], "Trend jest wzrostowy.")
        self.assertEqual(messages[3]["role"], "user")
        self.assertEqual(messages[3]["content"], "Przeanalizuj EURUSD.")


if __name__ == '__main__':
    unittest.main() 
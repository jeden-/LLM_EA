"""
Testy dla klienta LLM.

Ten moduł zawiera testy jednostkowe do sprawdzenia funkcjonalności klienta 
komunikującego się z lokalnym modelem LLM przez API Ollama.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
from pathlib import Path
import requests
import logging
import pytest

# Dodanie ścieżki głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM_Engine.llm_client import LLMClient

class TestLLMClient(unittest.TestCase):
    """Testy dla klienta LLM."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Wyłączenie logowania na czas testów
        logging.disable(logging.CRITICAL)
        
        self.client = LLMClient(
            base_url="http://localhost:11434",
            model_name="test-model",
            temperature=0.5,
            max_tokens=100,
            max_retries=2,
            timeout=30
        )
        
        # Domyślnie włączamy cache
        self.client.use_cache = True
        self.client.aggressive_caching = False

    def tearDown(self):
        """Czyszczenie po testach."""
        logging.disable(logging.NOTSET)

    def test_init(self):
        """Test inicjalizacji klienta."""
        self.assertEqual(self.client.base_url, "http://localhost:11434")
        self.assertEqual(self.client.model_name, "test-model")
        self.assertEqual(self.client.temperature, 0.5)
        self.assertEqual(self.client.max_tokens, 100)
        self.assertEqual(self.client.max_retries, 2)
        self.assertEqual(self.client.timeout, 30)

    @patch('LLM_Engine.llm_client.requests.post')
    def test_generate(self, mock_post):
        """Test generowania odpowiedzi bez cache."""
        # Konfiguracja mocka
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': 'Testowa odpowiedź',
            'model': 'test-model'
        }
        mock_post.return_value = mock_response

        # Wyłączenie cache
        self.client.use_cache = False

        # Wywołanie testowanej metody
        result = self.client.generate("Testowy prompt")

        # Weryfikacja
        self.assertEqual(result['response'], 'Testowa odpowiedź')
        mock_post.assert_called_once()
        
        # Sprawdzenie parametrów wywołania
        call_args = mock_post.call_args
        self.assertIn('json', call_args[1])
        self.assertEqual(call_args[1]['json']['prompt'], 'Testowy prompt')

    @patch('LLM_Engine.llm_client.requests.post')
    @patch('LLM_Engine.llm_client.os.path.exists')
    @patch('LLM_Engine.llm_client.Path.mkdir')
    @patch('builtins.open', new_callable=mock_open)
    @patch('LLM_Engine.llm_client.json.load')
    def test_generate_cache_hit(self, mock_json_load, mock_file_open, mock_mkdir, mock_exists, mock_post):
        """Test trafienia w cache."""
        # Konfiguracja mocków
        mock_exists.return_value = True
        cached_response = {
            'response': 'Odpowiedź z cache',
            'model': 'test-model',
            '_metadata': {
                'cache_hit': True,
                'cache_time': '2023-01-01T12:00:00'
            }
        }
        mock_json_load.return_value = cached_response

        # Konfiguracja mocka dla requests.post (na wszelki wypadek)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': 'Odpowiedź z API',
            'model': 'test-model'
        }
        mock_post.return_value = mock_response

        # Wywołanie testowanej metody
        result = self.client.generate(
            prompt="Testowy prompt",
            system_prompt="System prompt"
        )

        # Weryfikacja
        self.assertEqual(result['response'], 'Odpowiedź z cache')
        self.assertTrue(result['_metadata']['cache_hit'])
        mock_exists.assert_called()
        mock_json_load.assert_called_once()
        mock_post.assert_not_called()
        self.assertEqual(self.client.cache_hits, 1)

    @patch('LLM_Engine.llm_client.requests.post')
    @patch('LLM_Engine.llm_client.os.path.exists')
    @patch('LLM_Engine.llm_client.Path.mkdir')
    @patch('builtins.open', new_callable=mock_open)
    @patch('LLM_Engine.llm_client.json.dump')
    def test_generate_cache_miss(self, mock_json_dump, mock_file_open, mock_mkdir, mock_exists, mock_post):
        """Test pudła w cache."""
        # Konfiguracja mocków
        mock_exists.return_value = False
        mock_response = MagicMock()
        mock_response.status_code = 200
        api_response = {
            'response': 'Nowa odpowiedź z API',
            'model': 'test-model'
        }
        mock_response.json.return_value = api_response
        mock_post.return_value = mock_response

        # Wywołanie testowanej metody
        result = self.client.generate(
            prompt="Nowy prompt",
            system_prompt="System prompt"
        )

        # Weryfikacja
        self.assertEqual(result['response'], 'Nowa odpowiedź z API')
        mock_exists.assert_called_once()  # Sprawdzamy dokładnie jedno wywołanie
        mock_post.assert_called_once()
        mock_json_dump.assert_called_once_with(
            api_response, 
            mock_file_open(),
            ensure_ascii=False,
            indent=2
        )
        self.assertEqual(self.client.cache_misses, 1)

    @patch('LLM_Engine.llm_client.requests.get')
    def test_get_models(self, mock_get):
        """Test pobierania listy modeli."""
        # Ustawienie mock odpowiedzi
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'llama2', 'size': '7B'},
                {'name': 'mistral', 'size': '7B'}
            ]
        }
        mock_get.return_value = mock_response

        # Wywołanie testowanej metody
        result = self.client.get_models()

        # Weryfikacja
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'llama2')
        self.assertEqual(result[1]['name'], 'mistral')

    @patch('LLM_Engine.llm_client.requests.post')
    def test_handle_request_error(self, mock_post):
        """Test obsługi błędów żądań."""
        # Ustawienie błędu połączenia
        mock_post.side_effect = requests.exceptions.RequestException("Test connection error")

        # Wyłączenie cache
        self.client.use_cache = False

        # Wywołanie testowanej metody powinno zgłosić wyjątek
        with self.assertRaises(Exception) as context:
            self.client.generate("Testowy prompt")

        # Sprawdzenie, czy próbowano ponowić próbę odpowiednią liczbę razy
        self.assertEqual(mock_post.call_count, self.client.max_retries + 1)  # Pierwsza próba + ponowienia
        self.assertIn("Nie udało się połączyć z API LLM", str(context.exception))

    def test_generate_cache_key(self):
        """Test generowania kluczy cache dla różnych przypadków"""
        client = LLMClient()
        
        # Test podstawowego promptu
        key1 = client._generate_cache_key("gpt-4", "test prompt")
        key2 = client._generate_cache_key("gpt-4", "test   prompt")  # dodatkowe spacje
        self.assertEqual(key1, key2, "Klucze powinny być identyczne po normalizacji białych znaków")
        
        # Test z opcjami
        options1 = {
            "system": "system   prompt",
            "temperature": 0.7,
            "max_tokens": 100
        }
        options2 = {
            "system": "system prompt",  # mniej spacji
            "temperature": 0.700001,  # zaokrąglenie
            "max_tokens": 100
        }
        key3 = client._generate_cache_key("gpt-4", "test prompt", options1)
        key4 = client._generate_cache_key("gpt-4", "test prompt", options2)
        self.assertEqual(key3, key4, "Klucze powinny być identyczne po normalizacji opcji")
        
        # Test różnych promptów
        key5 = client._generate_cache_key("gpt-4", "inny prompt", options1)
        self.assertNotEqual(key3, key5, "Klucze dla różnych promptów powinny być różne")
        
        # Test różnych modeli
        key6 = client._generate_cache_key("gpt-3.5-turbo", "test prompt", options1)
        self.assertNotEqual(key3, key6, "Klucze dla różnych modeli powinny być różne")
        
        # Test bez opcji
        key7 = client._generate_cache_key("gpt-4", "test prompt")
        key8 = client._generate_cache_key("gpt-4", "test prompt", None)
        self.assertEqual(key7, key8, "Klucze bez opcji powinny być identyczne")

def test_generate_cache_key_basic():
    client = LLMClient()
    client.aggressive_caching = False
    
    model = "gpt-4"
    prompt = "Test prompt"
    options = {
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    key1 = client._generate_cache_key(model, prompt, options)
    
    # Ten sam prompt powinien dać ten sam klucz
    key2 = client._generate_cache_key(model, prompt, options)
    assert key1 == key2
    
    # Różne prompty powinny dać różne klucze
    key3 = client._generate_cache_key(model, "Inny prompt", options)
    assert key1 != key3

def test_generate_cache_key_aggressive():
    client = LLMClient()
    client.aggressive_caching = True
    
    model = "gpt-4"
    prompt = "Test prompt"
    options = {
        "temperature": 0.7123,
        "max_tokens": 100,
        "num_ctx": 2048,
        "repeat_penalty": 1.1,
        "seed": 42,
        "system": "  System prompt  "
    }
    
    key1 = client._generate_cache_key(model, prompt, options)
    
    # Zmiana nieistotnych parametrów nie powinna zmienić klucza
    options2 = options.copy()
    options2["num_ctx"] = 4096
    options2["repeat_penalty"] = 1.2
    options2["seed"] = 123
    
    key2 = client._generate_cache_key(model, prompt, options2)
    assert key1 == key2
    
    # Temperatura powinna być zaokrąglona do 0.7
    options3 = options.copy()
    options3["temperature"] = 0.7499  # zaokrągli się do 0.7
    
    key3 = client._generate_cache_key(model, prompt, options3)
    assert key1 == key3
    
    # Temperatura 0.75 powinna dać inny klucz (zaokrągli się do 0.8)
    options4 = options.copy()
    options4["temperature"] = 0.75
    
    key4 = client._generate_cache_key(model, prompt, options4)
    assert key1 != key4

def test_generate_cache_key_whitespace():
    client = LLMClient()
    
    model = "gpt-4"
    prompt = "  Test prompt  "
    options = {"temperature": 0.7}
    
    key1 = client._generate_cache_key(model, prompt, options)
    key2 = client._generate_cache_key(model, "Test prompt", options)
    
    assert key1 == key2  # białe znaki w prompcie powinny być usunięte

if __name__ == '__main__':
    unittest.main() 
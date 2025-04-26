"""
Testy dla interfejsu LLM.

Ten moduł zawiera testy jednostkowe do sprawdzenia funkcjonalności interfejsu
umożliwiającego komunikację z różnymi modelami LLM.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import json
from pathlib import Path

# Dodanie ścieżki głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM_Engine.llm_interface import LLMInterface

class TestLLMInterface(unittest.TestCase):
    """Testy dla interfejsu LLM."""
    
    def setUp(self):
        """Konfiguracja dla każdego testu."""
        # Symulacja zmiennych środowiskowych
        self.env_patcher = patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test_openai_key',
            'ANTHROPIC_API_KEY': 'test_anthropic_key',
            'LOCAL_LLM_API_URL': 'http://localhost:8080/generate'
        })
        self.env_patcher.start()
        
        # Patchowanie inicjalizacji klientów
        self.openai_patcher = patch('LLM_Engine.llm_interface.OpenAI')
        self.mock_openai = self.openai_patcher.start()
        
        self.anthropic_patcher = patch('LLM_Engine.llm_interface.Anthropic')
        self.mock_anthropic = self.anthropic_patcher.start()
        
        # Utworzenie interfejsu LLM z testowymi parametrami
        self.interface = LLMInterface(
            default_provider="openai",
            cache_enabled=True,
            cache_dir=".test_cache",
            max_retries=2,
            timeout=30
        )
    
    def tearDown(self):
        """Czyszczenie po każdym teście."""
        # Zatrzymanie patcherów
        self.env_patcher.stop()
        self.openai_patcher.stop()
        self.anthropic_patcher.stop()
        
        # Usunięcie tymczasowych plików cache jeśli istnieją
        cache_path = Path(".test_cache")
        if cache_path.exists():
            import shutil
            shutil.rmtree(str(cache_path), ignore_errors=True)
    
    def test_init(self):
        """Test inicjalizacji interfejsu."""
        # Weryfikacja parametrów
        self.assertEqual(self.interface.default_provider, "openai")
        self.assertTrue(self.interface.cache_enabled)
        self.assertEqual(self.interface.cache_dir, ".test_cache")
        self.assertEqual(self.interface.max_retries, 2)
        self.assertEqual(self.interface.timeout, 30)
        
        # Weryfikacja inicjalizacji klientów
        self.mock_openai.assert_called_once_with(api_key='test_openai_key')
        self.mock_anthropic.assert_called_once_with(api_key='test_anthropic_key')
    
    def test_update_provider_config(self):
        """Test aktualizacji konfiguracji dostawcy."""
        # Początkowa konfiguracja
        initial_temp = self.interface.provider_configs["openai"]["temperature"]
        
        # Aktualizacja konfiguracji
        self.interface.update_provider_config("openai", {"temperature": 0.8, "max_tokens": 2000})
        
        # Weryfikacja
        self.assertEqual(self.interface.provider_configs["openai"]["temperature"], 0.8)
        self.assertEqual(self.interface.provider_configs["openai"]["max_tokens"], 2000)
        self.assertNotEqual(self.interface.provider_configs["openai"]["temperature"], initial_temp)
        
        # Test dla nieprawidłowego dostawcy
        with self.assertRaises(ValueError):
            self.interface.update_provider_config("invalid_provider", {"temperature": 0.8})
    
    @patch('LLM_Engine.llm_interface.LLMInterface._call_openai')
    def test_generate_with_openai(self, mock_call_openai):
        """Test generowania tekstu z OpenAI."""
        # Ustawienie mock odpowiedzi
        mock_call_openai.return_value = ("To jest testowa odpowiedź od OpenAI.", {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        })
        
        # Wywołanie testowanej metody
        result = self.interface.generate(
            prompt="Testowy prompt",
            system_prompt="Jesteś pomocnym asystentem",
            provider="openai"
        )
        
        # Weryfikacja
        self.assertEqual(result, "To jest testowa odpowiedź od OpenAI.")
        mock_call_openai.assert_called_once()
        
        # Sprawdzenie, czy użyto poprawnego promptu i parametrów
        args, kwargs = mock_call_openai.call_args
        self.assertEqual(args[0], "Testowy prompt")
        self.assertEqual(args[1], "Jesteś pomocnym asystentem")
        self.assertEqual(args[2], "gpt-4o")
    
    @patch('LLM_Engine.llm_interface.LLMInterface._call_anthropic')
    def test_generate_with_anthropic(self, mock_call_anthropic):
        """Test generowania tekstu z Anthropic."""
        # Ustawienie mock odpowiedzi
        mock_call_anthropic.return_value = ("To jest testowa odpowiedź od Claude.", {
            "input_tokens": 15,
            "output_tokens": 25
        })
        
        # Wywołanie testowanej metody
        result = self.interface.generate(
            prompt="Testowy prompt",
            system_prompt="Jesteś pomocnym asystentem",
            provider="anthropic",
            model="claude-3-opus-20240229"
        )
        
        # Weryfikacja
        self.assertEqual(result, "To jest testowa odpowiedź od Claude.")
        mock_call_anthropic.assert_called_once()
        
        # Sprawdzenie, czy użyto poprawnego promptu i parametrów
        args, kwargs = mock_call_anthropic.call_args
        self.assertEqual(args[0], "Testowy prompt")
        self.assertEqual(args[1], "Jesteś pomocnym asystentem")
        self.assertEqual(args[2], "claude-3-opus-20240229")
    
    @patch('LLM_Engine.llm_interface.requests.post')
    def test_call_local_api(self, mock_post):
        """Test wywołania lokalnego API."""
        # Ustawienie mock odpowiedzi
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "To jest testowa odpowiedź z lokalnego API.",
            "usage": {"total_tokens": 50}
        }
        mock_post.return_value = mock_response
        
        # Wywołanie testowanej metody poprzez metodę prywatną
        response, usage = self.interface._call_local_api(
            prompt="Testowy prompt",
            system_prompt="Jesteś pomocnym asystentem",
            model="default"
        )
        
        # Weryfikacja
        self.assertEqual(response, "To jest testowa odpowiedź z lokalnego API.")
        self.assertEqual(usage["total_tokens"], 50)
        mock_post.assert_called_once()
        
        # Sprawdzenie, czy użyto poprawnego endpointu i payload
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["prompt"], "Testowy prompt")
        self.assertEqual(kwargs["json"]["system_prompt"], "Jesteś pomocnym asystentem")
        self.assertEqual(kwargs["timeout"], 30)
    
    def test_generate_with_invalid_provider(self):
        """Test generowania z nieprawidłowym dostawcą."""
        # Mockowanie metody _call_openai aby uniknąć rzeczywistego wywołania API
        with patch('LLM_Engine.llm_interface.LLMInterface._call_openai') as mock_call_openai, \
             self.assertLogs('LLM_Engine.llm_interface', level='WARNING') as log:
            
            # Ustawienie mock odpowiedzi dla OpenAI (fallback)
            mock_call_openai.return_value = ("Odpowiedź z OpenAI (fallback)", {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            })
            
            # Wywołanie testowanej metody z nieprawidłowym dostawcą
            result = self.interface.generate(
                prompt="Testowy prompt",
                provider="invalid_provider"
            )
            
            # Sprawdzenie czy zostało zalogowane ostrzeżenie
            self.assertTrue(any("Unknown provider: invalid_provider, falling back to openai" in msg for msg in log.output))
            
            # Sprawdzenie czy użyto fallbacku do OpenAI
            mock_call_openai.assert_called_once()
            
            # Sprawdzenie czy otrzymaliśmy odpowiedź z fallbacku
            self.assertEqual(result, "Odpowiedź z OpenAI (fallback)")
    
    def test_get_provider_stats(self):
        """Test pobierania statystyk użycia dostawcy."""
        # Ustaw przykładowe statystyki
        self.interface.usage_stats["total_requests"] = 10
        self.interface.usage_stats["total_tokens"] = 500
        self.interface.usage_stats["provider_usage"] = {
            "openai": {"requests": 7, "tokens": 350},
            "anthropic": {"requests": 3, "tokens": 150}
        }
        
        # Wywołanie testowanej metody
        stats = self.interface.get_usage_stats()
        
        # Weryfikacja
        self.assertEqual(stats["total_requests"], 10)
        self.assertEqual(stats["total_tokens"], 500)
        self.assertEqual(stats["provider_usage"]["openai"]["requests"], 7)
        self.assertEqual(stats["provider_usage"]["anthropic"]["tokens"], 150)


if __name__ == '__main__':
    unittest.main() 
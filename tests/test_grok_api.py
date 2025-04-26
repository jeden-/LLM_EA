"""
Testy dla klienta Grok API.

Ten moduł zawiera testy jednostkowe do sprawdzenia funkcjonalności klienta 
komunikującego się z modelem Grok przez API X.AI.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import json

# Dodanie ścieżki głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM_Engine.grok_client import GrokClient

class TestGrokClient(unittest.TestCase):
    """Testy dla klienta Grok API."""
    
    def setUp(self):
        """Konfiguracja dla każdego testu."""
        self.api_key = "test_api_key"
        
        # Utworzenie klienta z testowym kluczem API
        self.client = GrokClient(api_key=self.api_key)
    
    @patch('LLM_Engine.grok_client.requests.post')
    def test_check_api_availability(self, mock_post):
        """Test sprawdzania dostępności API."""
        # Ustawienie mock odpowiedzi
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Wywołanie testowanej metody
        result = self.client._check_api_availability()
        
        # Weryfikacja
        self.assertTrue(result)
        mock_post.assert_called_once()
        
        # Sprawdzenie, czy użyto poprawnego endpointu i nagłówków
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['headers']['Authorization'], f'Bearer {self.api_key}')
        self.assertEqual(kwargs['json']['model'], 'grok-3-mini-fast-beta')
    
    @patch('LLM_Engine.grok_client.requests.post')
    def test_generate(self, mock_post):
        """Test generowania tekstu."""
        # Ustawienie mock odpowiedzi
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [
                {
                    'message': {
                        'content': 'To jest testowa odpowiedź od modelu Grok.'
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # Wywołanie testowanej metody
        result = self.client.generate(
            prompt="Testowy prompt",
            system_prompt="System prompt"
        )
        
        # Weryfikacja
        self.assertEqual(result, 'To jest testowa odpowiedź od modelu Grok.')
        mock_post.assert_called_once()
        
        # Sprawdzenie, czy użyto poprawnego promptu i parametrów
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['messages'][0]['role'], 'system')
        self.assertEqual(kwargs['json']['messages'][0]['content'], 'System prompt')
        self.assertEqual(kwargs['json']['messages'][1]['role'], 'user')
        self.assertEqual(kwargs['json']['messages'][1]['content'], 'Testowy prompt')
    
    @patch('LLM_Engine.grok_client.requests.post')
    def test_generate_with_json_output(self, mock_post):
        """Test generowania odpowiedzi w formacie JSON."""
        # Ustawienie mock odpowiedzi
        json_content = """
        {
          "analysis": {
            "trend": "bullish",
            "key_levels": {
              "support": [1.0780, 1.0750],
              "resistance": [1.0850, 1.0880]
            }
          },
          "recommendation": "buy"
        }
        """
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [
                {
                    'message': {
                        'content': json_content
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # Wywołanie testowanej metody
        result = self.client.generate_with_json_output(
            prompt="Analizuj rynek",
            system_prompt="Jesteś analitykiem rynku"
        )
        
        # Weryfikacja
        self.assertEqual(result['analysis']['trend'], 'bullish')
        self.assertEqual(result['recommendation'], 'buy')
        self.assertEqual(len(result['analysis']['key_levels']['support']), 2)
        mock_post.assert_called_once()
    
    @patch('LLM_Engine.grok_client.requests.post')
    def test_extract_json_from_text(self, mock_post):
        """Test ekstrahowania JSON z tekstu."""
        # Przykładowy tekst z zagnieżdżonym JSON
        text = """
        Oto moja analiza rynku:
        
        ```json
        {
          "trend": "bullish",
          "strength": 8,
          "setup": "Trend Following"
        }
        ```
        
        Mam nadzieję, że to pomoże!
        """
        
        # Wywołanie testowanej metody
        json_str = self.client._extract_json_from_text(text)
        parsed_json = json.loads(json_str)
        
        # Weryfikacja
        self.assertEqual(parsed_json['trend'], 'bullish')
        self.assertEqual(parsed_json['strength'], 8)
        self.assertEqual(parsed_json['setup'], 'Trend Following')
    
    def test_extract_json_handles_none(self):
        """Test, czy metoda ekstrahowania JSON obsługuje None."""
        # Wywołanie testowanej metody z None
        result = self.client._extract_json_from_text(None)
        
        # Weryfikacja
        self.assertEqual(result, '')
    
    def test_parse_number_list(self):
        """Test parsowania listy liczb z tekstu."""
        # Przykładowy tekst z liczbami
        text = "1.0780, 1.0750, 1.0820"
        
        # Wywołanie testowanej metody
        result = self.client._parse_number_list(text)
        
        # Weryfikacja
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], 1.0780)
        self.assertEqual(result[1], 1.0750)
        self.assertEqual(result[2], 1.0820)


if __name__ == '__main__':
    unittest.main() 
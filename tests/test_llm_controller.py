"""
Testy dla kontrolera LLM.

Ten moduł zawiera testy jednostkowe dla funkcjonalności związanych 
z kontrolerem zarządzającym komunikacją z modelami językowymi (LLM).
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, PropertyMock, mock_open, AsyncMock
import json
import asyncio
import pytest
import aiohttp

# Konfiguracja pytest dla testów asynchronicznych
pytest_plugins = ('pytest_asyncio',)

# Dodanie ścieżki głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM_Engine.llm_controller import (
    LLMController,
    ModelSelector,
    RequestManager,
    ResponseHandler
)

class TestLLMController(unittest.TestCase):
    """Testy dla głównej klasy LLMController."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.config = {
            'model_selector': {
                'model_mapping': {
                    'gpt-4': {
                        'tasks': ['trade_signal', 'market_analysis', 'risk_assessment'],
                        'max_tokens': 8000,
                        'cost_per_1k': 0.03
                    },
                    'gpt-3.5-turbo': {
                        'tasks': ['trade_signal', 'market_analysis'],
                        'max_tokens': 4000,
                        'cost_per_1k': 0.002
                    }
                },
                'fallback_model': 'gpt-3.5-turbo'
            },
            'request_manager': {
                'templates_dir': 'LLM_Engine/templates',
                'timeout': 30
            }
        }
        self.controller = LLMController(config=self.config)
        
    def test_init(self):
        """Test inicjalizacji kontrolera LLM."""
        self.assertIsNotNone(self.controller.model_selector)
        self.assertIsNotNone(self.controller.request_manager)
        self.assertIsNotNone(self.controller.response_handler)
        self.assertIsNone(self.controller.active_model)
        
    def test_select_model(self):
        """Test wyboru modelu LLM."""
        # Mock dla ModelSelector.select_model
        with patch.object(ModelSelector, 'select_model', return_value='gpt-4') as mock_select:
            # Wywołanie metody
            model = self.controller.select_model(task_type='market_analysis')
            
            # Weryfikacja
            mock_select.assert_called_once_with(task_type='market_analysis')
            self.assertEqual(model, 'gpt-4')
            self.assertEqual(self.controller.active_model, 'gpt-4')
            
    def test_prepare_prompt(self):
        """Test przygotowania promptu dla modelu."""
        # Mock dla RequestManager.prepare_prompt
        with patch.object(RequestManager, 'prepare_prompt', return_value='Przygotowany prompt') as mock_prepare:
            # Dane
            market_data = {'price': 1.1000, 'volume': 1000}
            task_type = 'trade_signal'
            
            # Wywołanie metody
            prompt = self.controller.prepare_prompt(task_type, market_data)
            
            # Weryfikacja
            mock_prepare.assert_called_once_with(task_type=task_type, data=market_data)
            self.assertEqual(prompt, 'Przygotowany prompt')
            
    @patch('asyncio.run')
    def test_send_request(self, mock_run):
        """Test wysyłania zapytania do API modelu."""
        # Mock dla RequestManager.send_request i asyncio.run
        mock_response = {"choices": [{"message": {"content": "Odpowiedź od modelu"}}]}
        mock_run.return_value = mock_response
        
        # Ustawienie aktywnego modelu
        self.controller.active_model = 'gpt-4'
        
        # Mock dla build_request_payload i send_request_async
        mock_payload = {"messages": [{"content": "Prompt testowy"}]}
        
        # Tworzymy mock dla metody asynchronicznej
        async def mock_async_send(url, payload, headers=None):
            return mock_response
            
        with patch.object(RequestManager, 'build_request_payload', return_value=mock_payload) as mock_build, \
             patch.object(RequestManager, 'send_request_async', side_effect=mock_async_send) as mock_send:
            
            # Wywołanie metody
            prompt = "Prompt testowy"
            response = self.controller.send_request(prompt)
            
            # Weryfikacja
            mock_build.assert_called_once_with(self.controller.active_model, prompt)
            mock_send.assert_called_once_with(mock_payload)
            self.assertEqual(response, mock_response)
            
    def test_handle_response(self):
        """Test przetwarzania odpowiedzi od modelu."""
        # Mock dla ResponseHandler.process_response
        processed_response = {"action": "BUY", "pair": "EURUSD"}
        
        with patch.object(ResponseHandler, 'process_response', return_value=processed_response) as mock_process:
            # Dane
            raw_response = {"choices": [{"message": {"content": "Odpowiedź od modelu"}}]}
            
            # Wywołanie metody
            result = self.controller.handle_response(raw_response)
            
            # Weryfikacja
            mock_process.assert_called_once_with(raw_response)
            self.assertEqual(result, processed_response)
            
    def test_execute_llm_task(self):
        """Test pełnego cyklu wykonania zadania LLM."""
        # Mocki dla poszczególnych metod kontrolera
        with patch.object(LLMController, 'select_model', return_value='gpt-4') as mock_select, \
             patch.object(LLMController, 'prepare_prompt', return_value='Przygotowany prompt') as mock_prepare, \
             patch.object(LLMController, 'send_request', return_value={"choices": [{"message": {"content": "Odpowiedź"}}]}) as mock_send, \
             patch.object(LLMController, 'handle_response', return_value={"action": "BUY"}) as mock_handle:
                
            # Dane
            task_type = 'trade_signal'
            data = {'price': 1.1000}
            
            # Wywołanie metody
            result = self.controller.execute_llm_task(task_type, data)
            
            # Weryfikacja
            mock_select.assert_called_once_with(task_type=task_type)
            mock_prepare.assert_called_once_with(task_type=task_type, data=data)
            mock_send.assert_called_once_with('Przygotowany prompt')
            mock_handle.assert_called_once_with({"choices": [{"message": {"content": "Odpowiedź"}}]})
            self.assertEqual(result, {"action": "BUY"})


class TestModelSelector(unittest.TestCase):
    """Testy dla klasy ModelSelector."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.config = {
            'model_mapping': {
                'gpt-4': {
                    'tasks': ['trade_signal', 'market_analysis', 'risk_assessment'],
                    'max_tokens': 8000,
                    'cost_per_1k': 0.03
                },
                'gpt-3.5-turbo': {
                    'tasks': ['trade_signal', 'market_analysis'],
                    'max_tokens': 4000,
                    'cost_per_1k': 0.002
                }
            },
            'fallback_model': 'gpt-3.5-turbo'
        }
        self.selector = ModelSelector(self.config)
        
    def test_init(self):
        """Test inicjalizacji selektora modeli."""
        self.assertEqual(self.selector.model_mapping, self.config['model_mapping'])
        self.assertEqual(self.selector.fallback_model, self.config['fallback_model'])
        
    def test_get_available_models(self):
        """Test pobierania dostępnych modeli."""
        models = self.selector.get_available_models()
        
        # Weryfikacja
        self.assertIsInstance(models, list)
        self.assertEqual(len(models), 2)
        self.assertIn('gpt-4', models)
        self.assertIn('gpt-3.5-turbo', models)
        
    def test_select_model_existing_task(self):
        """Test wyboru modelu dla istniejącego typu zadania."""
        # Test dla zadania obsługiwanego przez oba modele
        model = self.selector.select_model(task_type='trade_signal')
        self.assertEqual(model, 'gpt-3.5-turbo')  # Powinien wybrać tańszy model
        
        # Test dla zadania obsługiwanego tylko przez gpt-4
        model = self.selector.select_model(task_type='risk_assessment')
        self.assertEqual(model, 'gpt-4')
        
    def test_select_model_nonexistent_task(self):
        """Test wyboru modelu dla nieistniejącego typu zadania."""
        model = self.selector.select_model(task_type='nieistniejący_typ')
        self.assertEqual(model, self.selector.fallback_model)
        
    def test_select_model_by_params(self):
        """Test wyboru modelu na podstawie parametrów."""
        # Test z ograniczeniem tokenów
        model = self.selector.select_model_by_params(
            task_type='trade_signal',
            max_tokens=5000
        )
        self.assertEqual(model, 'gpt-4')
        
        # Test z ograniczeniem kosztu
        model = self.selector.select_model_by_params(
            task_type='trade_signal',
            max_cost=0.01
        )
        self.assertEqual(model, 'gpt-3.5-turbo')
        
        # Test z oboma ograniczeniami
        model = self.selector.select_model_by_params(
            task_type='trade_signal',
            max_tokens=3000,
            max_cost=0.01
        )
        self.assertEqual(model, 'gpt-3.5-turbo')
        
        # Test z nieistniejącym typem zadania
        model = self.selector.select_model_by_params(
            task_type='nieistniejący_typ',
            max_tokens=5000,
            max_cost=0.01
        )
        self.assertEqual(model, self.selector.fallback_model)
        
        # Test z niemożliwymi do spełnienia ograniczeniami
        model = self.selector.select_model_by_params(
            task_type='trade_signal',
            max_tokens=10000,  # Za duże dla obu modeli
            max_cost=0.001  # Za małe dla obu modeli
        )
        self.assertEqual(model, self.selector.fallback_model)


class TestRequestManager(unittest.TestCase):
    """Testy dla klasy RequestManager."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.config = {
            'templates_dir': 'LLM_Engine/templates',
            'timeout': 30
        }
        self.request_manager = RequestManager(config=self.config)
        
    def test_init(self):
        """Test inicjalizacji menedżera zapytań."""
        self.assertIsNotNone(self.request_manager.env)
        self.assertEqual(self.request_manager.timeout.total, 30)
        
    def test_prepare_prompt(self):
        """Test przygotowania promptu na podstawie szablonu."""
        # Mock dla metody load_template
        mock_template = MagicMock()
        mock_template.render.return_value = "Analizuj dane: 1.0950 dla pary EURUSD"
        
        with patch.object(self.request_manager, 'load_template', return_value=mock_template):
            # Dane
            task_type = 'market_analysis'
            data = {'price': 1.0950, 'pair': 'EURUSD'}
            
            # Wywołanie metody
            prompt = self.request_manager.prepare_prompt(task_type=task_type, data=data)
            
            # Weryfikacja
            self.assertEqual(prompt, "Analizuj dane: 1.0950 dla pary EURUSD")
            
    def test_build_request_payload(self):
        """Test budowania payloadu zapytania."""
        # Dane
        model = 'gpt-4'
        prompt = "Testowy prompt"
        options = {"system_prompt": "System prompt", "temperature": 0.7}
        
        # Wywołanie metody
        payload = self.request_manager.build_request_payload(model, prompt, options)
        
        # Weryfikacja
        self.assertEqual(payload['model'], model)
        self.assertIn('messages', payload)
        self.assertEqual(len(payload['messages']), 2)
        self.assertEqual(payload['messages'][0]['content'], "System prompt")
        self.assertEqual(payload['messages'][1]['content'], prompt)
        self.assertEqual(payload['temperature'], 0.7)
        
    @pytest.mark.asyncio
    async def test_send_request_retry_and_fail(self):
        """Test wysyłania żądania z ponowieniami i ostatecznym niepowodzeniem."""
        # Zachowanie oryginalnej wartości max_retries
        original_max_retries = self.request_manager.max_retries
        # Ustawienie mniejszej liczby ponowień dla szybszego testowania
        self.request_manager.max_retries = 3
        
        try:
            # Przygotowanie mockowanej odpowiedzi
            mock_response = MagicMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value="Internal Server Error")
            
            # Mockowanie aiohttp.ClientSession
            mock_session = AsyncMock()
            # Ustawiamy mock_response jako wartość zwracaną przez post
            mock_session.post.return_value = mock_response
            
            # Dane testowe
            url = "https://api.openai.com/v1/chat/completions"
            payload = {"messages": [{"content": "Testowy prompt"}]}
            headers = {"Authorization": "Bearer test_key"}
            
            # Patching metody sleep, aby nie czekać podczas testu
            with patch('asyncio.sleep', new_callable=AsyncMock):
                # Wywołanie metody - powinno wyrzucić wyjątek po próbach
                with pytest.raises(Exception):
                    # Używamy własnej mockowanej sesji
                    await self.request_manager.send_request_async(url, payload, headers, session=mock_session)
                
                # Sprawdzenie czy metoda post została wywołana odpowiednią liczbę razy
                # Metoda post powinna być wywołana raz, ponieważ retry jest implementowany w send_request, a nie w send_request_async
                assert mock_session.post.call_count == 1
        finally:
            # Przywrócenie oryginalnej wartości max_retries
            self.request_manager.max_retries = original_max_retries

    @pytest.mark.asyncio
    async def test_send_request_async_error(self):
        """Test obsługi błędów przy wysyłaniu zapytania."""
        # Przygotowanie mockowanej odpowiedzi z błędem
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="Bad Request")
        
        # Mockowanie aiohttp.ClientSession
        mock_session = AsyncMock()
        # Ustawiamy mock_response jako wartość zwracaną przez post
        mock_session.post.return_value = mock_response
        
        # Dane testowe
        url = "https://api.openai.com/v1/chat/completions"
        payload = {"messages": [{"content": "Testowy prompt"}]}
        headers = {"Authorization": "Bearer test_key"}
        
        # Wywołanie metody - powinno wyrzucić wyjątek dla statusu 400
        with pytest.raises(Exception) as excinfo:
            await self.request_manager.send_request_async(url, payload, headers, session=mock_session)
        
        # Sprawdzenie czy wyjątek zawiera informacje o błędzie
        assert "Błąd API (status 400)" in str(excinfo.value)
        
        # Sprawdzenie czy metoda post została wywołana z odpowiednimi argumentami
        mock_session.post.assert_called_once_with(
            url,
            json=payload,
            headers={"Authorization": "Bearer test_key", "Content-Type": "application/json"}
        )
            
    def test_load_template(self):
        """Test ładowania szablonu promptu."""
        # Mock dla Jinja2 Environment
        mock_env = MagicMock()
        mock_template = MagicMock()
        mock_env.get_template.return_value = mock_template
        
        with patch.object(self.request_manager, 'env', mock_env):
            # Wywołanie metody
            template = self.request_manager.load_template('trade_signal')
            
            # Weryfikacja
            mock_env.get_template.assert_called_once_with('trade_signal.j2')
            self.assertEqual(template, mock_template)

    def test_validate_request_valid(self):
        """Test walidacji poprawnego żądania."""
        request_data = {
            'model': 'gpt-4',
            'messages': [
                {'role': 'system', 'content': 'You are a helpful assistant'},
                {'role': 'user', 'content': 'Hello'}
            ]
        }
        
        self.assertTrue(self.request_manager.validate_request(request_data))
        
    def test_validate_request_missing_field(self):
        """Test walidacji żądania z brakującym polem."""
        request_data = {
            'messages': [
                {'role': 'user', 'content': 'Hello'}
            ]
        }
        
        with self.assertRaises(ValueError) as context:
            self.request_manager.validate_request(request_data)
        self.assertIn('Brak wymaganego pola: model', str(context.exception))
        
    def test_validate_request_invalid_messages(self):
        """Test walidacji żądania z niepoprawnym formatem wiadomości."""
        request_data = {
            'model': 'gpt-4',
            'messages': 'not a list'
        }
        
        with self.assertRaises(ValueError) as context:
            self.request_manager.validate_request(request_data)
        self.assertIn("Pole 'messages' musi być listą", str(context.exception))
        
    def test_validate_request_invalid_message_format(self):
        """Test walidacji żądania z niepoprawnym formatem pojedynczej wiadomości."""
        request_data = {
            'model': 'gpt-4',
            'messages': [
                {'role': 'user'}  # brak content
            ]
        }
        
        with self.assertRaises(ValueError) as context:
            self.request_manager.validate_request(request_data)
        self.assertIn("Wiadomość musi zawierać pola 'role' i 'content'", str(context.exception))
        
    def test_prepare_request(self):
        """Test przygotowania żądania."""
        model = 'gpt-4'
        messages = [
            {'role': 'system', 'content': 'You are a helpful assistant'},
            {'role': 'user', 'content': 'Hello'}
        ]
        temperature = 0.7
        
        request = self.request_manager.prepare_request(
            model=model,
            messages=messages,
            temperature=temperature
        )
        
        self.assertEqual(request['model'], model)
        self.assertEqual(request['messages'], messages)
        self.assertEqual(request['temperature'], temperature)
        
        # Sprawdź czy dodano konfigurację providera
        self.assertIn('headers', request)
        self.assertIn('Authorization', request['headers'])


class TestResponseHandler(unittest.TestCase):
    """Testy dla klasy ResponseHandler."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.mock_parser_factory = MagicMock()
        self.response_handler = ResponseHandler(parser_factory=self.mock_parser_factory)

    def test_process_response_valid(self):
        """Test przetwarzania poprawnej odpowiedzi z API."""
        # Przygotowanie danych testowych
        response = {
            "choices": [{
                "message": {
                    "content": "{'trend': 'bullish', 'support_levels': [1.0800, 1.0750]}"
                }
            }]
        }
        task_type = "market_analysis"

        # Przygotowanie mocka dla parsera
        mock_parser = MagicMock()
        parsed_data = {
            "trend": "bullish",
            "support_levels": [1.0800, 1.0750]
        }
        mock_parser.parse.return_value = parsed_data
        mock_parser.validate.return_value = (True, None)  # (valid, errors)
        
        # Ustawienie mocka factory
        self.mock_parser_factory.get_parser.return_value = mock_parser

        # Wywołanie metody
        result = self.response_handler.process_response(response, task_type)

        # Sprawdzenie czy parser został użyty poprawnie
        self.mock_parser_factory.get_parser.assert_called_once_with(task_type)
        mock_parser.parse.assert_called_once_with("{'trend': 'bullish', 'support_levels': [1.0800, 1.0750]}")
        mock_parser.validate.assert_called_once_with(parsed_data)
        
        # Sprawdzenie wyniku
        self.assertEqual(result["trend"], "bullish")
        self.assertEqual(result["support_levels"], [1.0800, 1.0750])

    def test_process_response_invalid_format(self):
        """Test przetwarzania odpowiedzi w nieprawidłowym formacie."""
        # Przygotowanie danych testowych z nieprawidłową strukturą
        response = "Nieprawidłowa odpowiedź"
        task_type = "market_analysis"

        # Wywołanie metody
        result = self.response_handler.process_response(response, task_type)

        # Sprawdzenie czy parser nie został użyty
        self.mock_parser_factory.get_parser.assert_not_called()
        
        # Sprawdzenie wyniku
        self.assertEqual(result, {})

    def test_process_response_validation_failed(self):
        """Test przetwarzania odpowiedzi, która nie przechodzi walidacji."""
        # Przygotowanie danych testowych
        response = {
            "choices": [{
                "message": {
                    "content": "{'trend': 'invalid_trend'}"
                }
            }]
        }
        task_type = "market_analysis"

        # Przygotowanie mocka dla parsera
        mock_parser = MagicMock()
        mock_parser.parse.return_value = {"trend": "invalid_trend"}
        mock_parser.validate.return_value = False
        
        # Ustawienie mocka factory
        self.mock_parser_factory.get_parser.return_value = mock_parser

        # Wywołanie metody
        result = self.response_handler.process_response(response, task_type)

        # Sprawdzenie czy parser został użyty
        self.mock_parser_factory.get_parser.assert_called_once_with(task_type)
        mock_parser.parse.assert_called_once()
        mock_parser.validate.assert_called_once()
        
        # Sprawdzenie wyniku
        self.assertEqual(result, {})

    def test_process_response_parser_exception(self):
        """Test obsługi wyjątku podczas parsowania."""
        # Przygotowanie danych testowych
        response = {
            "choices": [{
                "message": {
                    "content": "{'invalid': json"
                }
            }]
        }
        task_type = "market_analysis"

        # Przygotowanie mocka dla parsera
        mock_parser = MagicMock()
        mock_parser.parse.side_effect = Exception("Błąd parsowania")
        
        # Ustawienie mocka factory
        self.mock_parser_factory.get_parser.return_value = mock_parser

        # Wywołanie metody
        result = self.response_handler.process_response(response, task_type)

        # Sprawdzenie czy parser został użyty
        self.mock_parser_factory.get_parser.assert_called_once_with(task_type)
        mock_parser.parse.assert_called_once()
        
        # Sprawdzenie wyniku
        self.assertEqual(result, {})


if __name__ == '__main__':
    unittest.main() 
"""
Testy dla managera żądań.
"""

import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
import aiohttp
from LLM_Engine.request_manager import RequestManager
from typing import Optional, Dict
import pytest
import time

class MockResponse:
    def __init__(self, status: int, json_data: Optional[Dict] = None, text: str = ""):
        self.status = status
        self._json = json_data
        self._text = text
        
    async def json(self):
        return self._json
        
    async def text(self):
        return self._text

# Używamy pytest zamiast unittest dla testów asynchronicznych
class TestRequestManager:
    @pytest.fixture
    def request_manager(self):
        config = {
            "providers": {
                "gpt-4": {
                    "url": "https://api.openai.com/v1/chat/completions",
                    "headers": {"Authorization": "Bearer test"}
                }
            }
        }
        return RequestManager(config)
        
    def test_init_with_config(self, request_manager):
        """
        Test inicjalizacji z konfiguracją.
        """
        assert "providers" in request_manager.config
        
    def test_init_without_config(self):
        """
        Test inicjalizacji bez konfiguracji.
        """
        request_manager = RequestManager()
        assert request_manager.config == {}
        
    def test_prepare_request(self, request_manager):
        """
        Test przygotowania żądania.
        """
        model = "gpt-4"
        messages = [{"role": "user", "content": "Test"}]
        
        request = request_manager.prepare_request(model, messages)
        
        assert request["model"] == model
        assert request["messages"] == messages
        
    @pytest.mark.asyncio
    async def test_send_request_success(self, request_manager):
        """Test udanego wysłania żądania."""
        model = "gpt-4"
        prompt = "Analyze BTC market"
        
        # Tworzenie mocka sesji z poprawną odpowiedzią
        mock_response = MockResponse(
            status=200,
            json_data={"choices": [{"message": {"content": "Test response"}}]}
        )
        
        async def mock_post(*args, **kwargs):
            return mock_response
        
        # Tworzenie kontekstu menedżera kontekstu dla sesji
        mock_session = AsyncMock()
        mock_session.post = mock_post
        mock_session.close = AsyncMock()
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            response = await request_manager.send_request_async(
                "https://api.openai.com/v1/chat/completions",
                {"model": model, "messages": [{"role": "user", "content": prompt}]},
                {"Authorization": "Bearer test"}
            )
            
            assert response["choices"][0]["message"]["content"] == "Test response"
            assert mock_session.close.called
        
    def test_send_request_retry_and_fail(self, request_manager):
        """Test nieudanego wysłania żądania z ponowieniem próby."""
        # Zmień liczbę prób ponowienia na mniejszą wartość dla szybszego testowania
        request_manager.max_retries = 3
        request_manager.retry_delay = 0.01
        
        model = "gpt-4"
        prompt = "Test prompt"
        
        # Mockowanie get_provider_config
        request_manager.get_provider_config = Mock(return_value={
            "url": "https://api.openai.com/v1/chat/completions",
            "headers": {"Authorization": "Bearer test"}
        })
        
        # Mockowanie build_request_payload
        request_manager.build_request_payload = Mock(return_value={
            "model": model,
            "messages": [{"role": "user", "content": prompt}]
        })
        
        # Tworzenie mocka sesji z odpowiedzią błędu
        error_response = MockResponse(
            status=500,
            text="API Error"
        )
        
        # Mock dla asyncio.get_event_loop
        mock_loop = Mock()
        
        # Mock dla send_request_async, aby zawsze rzucał wyjątek
        async def mock_send_request_async(*args, **kwargs):
            raise Exception("API Error")
            
        request_manager.send_request_async = mock_send_request_async
        
        with patch('time.sleep') as mock_sleep, \
             patch('asyncio.get_event_loop', return_value=mock_loop):
            
            mock_loop.is_running = Mock(return_value=False)
            mock_loop.run_until_complete = Mock(side_effect=Exception("API Error"))
            
            with pytest.raises(Exception):
                request_manager.send_request(model, prompt)
            
            # Powinno być 3 wywołania sleep - tyle, ile mamy ponownych prób (max_retries = 3)
            assert mock_sleep.call_count == 2, "Funkcja sleep powinna być wywołana 2 razy (dla retries = 0, 1, 2)"
        
    def test_validate_request_valid(self, request_manager):
        """
        Test walidacji poprawnego żądania.
        """
        request_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Test"}]
        }
        assert request_manager.validate_request(request_data) == True
        
    def test_validate_request_invalid_missing_fields(self, request_manager):
        """
        Test walidacji żądania z brakującymi polami.
        """
        request_data = {"model": "gpt-4"}
        with pytest.raises(ValueError):
            request_manager.validate_request(request_data)
            
    def test_validate_request_invalid_empty_messages(self, request_manager):
        """
        Test walidacji żądania z pustą listą wiadomości.
        """
        request_data = {
            "model": "gpt-4",
            "messages": []
        }
        with pytest.raises(ValueError):
            request_manager.validate_request(request_data)
            
    def test_validate_request_invalid_message_format(self, request_manager):
        """
        Test walidacji żądania z niepoprawnym formatem wiadomości.
        """
        request_data = {
            "model": "gpt-4",
            "messages": [{"content": "Test"}]  # Brak pola role
        }
        with pytest.raises(ValueError):
            request_manager.validate_request(request_data) 
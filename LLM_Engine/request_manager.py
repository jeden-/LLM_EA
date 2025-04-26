"""
Moduł zarządzający żądaniami do modeli LLM.
"""
import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from jinja2 import Template, Environment, FileSystemLoader
import aiohttp
from aiohttp import ClientTimeout
import asyncio

logger = logging.getLogger(__name__)

class RequestManager:
    """Klasa zarządzająca żądaniami do modeli LLM."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Inicjalizacja managera żądań.
        
        Args:
            config: Słownik z konfiguracją
        """
        self.config = config or {}
        
        # Konfiguracja parametrów
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 1)
        
        # Konfiguracja katalogów z szablonami
        self.templates_dir = self.config.get('templates_dir') or os.path.join(
            os.path.dirname(__file__), "templates"
        )
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Konfiguracja providerów
        self.providers = {
            "openai": {
                "url": "https://api.openai.com/v1/chat/completions",
                "headers": {
                    "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"
                }
            },
            "anthropic": {
                "url": "https://api.anthropic.com/v1/messages",
                "headers": {
                    "x-api-key": f"{os.getenv('ANTHROPIC_API_KEY')}"
                }
            }
        }
        
        # Timeout dla żądań
        self.timeout = ClientTimeout(total=self.config.get('timeout', 30))
        
    def get_provider_config(self, model: str) -> Dict[str, Any]:
        """Pobiera konfigurację providera dla danego modelu.
        
        Args:
            model: Nazwa modelu
            
        Returns:
            Dict[str, Any]: Konfiguracja providera
            
        Raises:
            ValueError: Gdy model nie jest obsługiwany
        """
        if isinstance(model, dict):
            model = model.get("model", "")
            
        if model.startswith("gpt"):
            return self.providers["openai"]
        elif model.startswith("claude"):
            return self.providers["anthropic"]
        else:
            raise ValueError(f"Nieobsługiwany model: {model}")
            
    def load_template(self, task_type: str) -> Template:
        """Ładuje szablon promptu dla danego typu zadania.
        
        Args:
            task_type: Typ zadania
            
        Returns:
            Template: Obiekt szablonu Jinja2
        """
        try:
            return self.env.get_template(f"{task_type}.j2")
        except Exception as e:
            logger.warning(f"Błąd podczas ładowania szablonu {task_type}: {e}")
            return Template("{{prompt}}")
            
    def prepare_prompt(self, task_type: str, data: Dict[str, Any]) -> str:
        """Przygotowuje prompt na podstawie szablonu i danych.
        
        Args:
            task_type: Typ zadania
            data: Dane do wypełnienia szablonu
            
        Returns:
            str: Przygotowany prompt
        """
        try:
            template = self.load_template(task_type)
            context = {
                "data": data,
                "task_type": task_type,
                "system_prompt": self.config.get("system_prompts", {}).get(task_type, "")
            }
            return template.render(**context)
        except Exception as e:
            logger.error(f"Błąd podczas przygotowywania promptu: {e}")
            return self._get_fallback_prompt(task_type, data)
            
    def _get_fallback_prompt(self, task_type: str, data: Dict[str, Any]) -> str:
        """Tworzy awaryjny prompt gdy szablon jest niedostępny.
        
        Args:
            task_type: Typ zadania
            data: Dane wejściowe
            
        Returns:
            str: Awaryjny prompt
        """
        return (
            f"Wykonaj zadanie typu {task_type} na podstawie następujących danych:\n"
            f"{json.dumps(data, indent=2, ensure_ascii=False)}"
        )
            
    def build_request_payload(self, model: str, prompt: str, 
                            options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Buduje payload żądania do API.
        
        Args:
            model: Nazwa modelu
            prompt: Treść promptu
            options: Dodatkowe opcje żądania
            
        Returns:
            Dict[str, Any]: Payload żądania
        """
        options = options or {}
        
        if model.startswith("gpt"):
            return {
                "model": model,
                "messages": [
                    {"role": "system", "content": options.get("system_prompt", "")},
                    {"role": "user", "content": prompt}
                ],
                "temperature": options.get("temperature", 0.7),
                "max_tokens": options.get("max_tokens", 1000),
                "top_p": options.get("top_p", 1.0),
                "frequency_penalty": options.get("frequency_penalty", 0.0),
                "presence_penalty": options.get("presence_penalty", 0.0)
            }
        elif model.startswith("claude"):
            return {
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "system": options.get("system_prompt", ""),
                "max_tokens": options.get("max_tokens", 1000),
                "temperature": options.get("temperature", 0.7),
                "top_p": options.get("top_p", 1.0)
            }
        else:
            raise ValueError(f"Nieobsługiwany model: {model}")
            
    async def send_request_async(self, url: str, payload: Dict[str, Any], 
                               headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Wysyła asynchroniczne żądanie do API.
        
        Args:
            url: URL endpointu API
            payload: Payload żądania
            headers: Nagłówki żądania
            
        Returns:
            Dict[str, Any]: Odpowiedź od API
            
        Raises:
            Exception: Gdy wystąpi błąd podczas żądania
        """
        headers = headers or {}
        headers["Content-Type"] = "application/json"
        
        try:
            session = aiohttp.ClientSession(timeout=self.timeout)
            response = await session.post(url, json=payload, headers=headers)
            
            if response.status != 200:
                error_body = await response.text()
                await session.close()
                raise Exception(
                    f"Błąd API (status {response.status}): {error_body}"
                )
                
            result = await response.json()
            await session.close()
            return result
            
        except aiohttp.ClientError as e:
            logger.error(f"Błąd podczas wysyłania żądania: {e}")
            raise
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd: {e}")
            raise
            
    def prepare_request(self, model: str, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Przygotowanie żądania do API.
        
        Args:
            model: Nazwa modelu
            messages: Lista wiadomości
            **kwargs: Dodatkowe parametry
            
        Returns:
            Dict[str, Any]: Przygotowane żądanie
            
        Raises:
            ValueError: Gdy żądanie jest nieprawidłowe
        """
        request_data = {
            'model': model,
            'messages': messages,
            **kwargs
        }
        
        # Walidacja żądania
        self.validate_request(request_data)
        
        # Dodaj konfigurację providera
        provider_config = self.get_provider_config(model)
        if provider_config:
            request_data.update(provider_config)
            
        return request_data

    def validate_request(self, request_data: Dict[str, Any]) -> bool:
        """Walidacja parametrów żądania.
        
        Args:
            request_data: Dane żądania do walidacji
            
        Returns:
            bool: True jeśli żądanie jest poprawne
            
        Raises:
            ValueError: Jeśli brakuje wymaganych pól lub są niepoprawne
        """
        required_fields = ['model', 'messages']
        
        # Sprawdź wymagane pola
        for field in required_fields:
            if field not in request_data:
                raise ValueError(f"Brak wymaganego pola: {field}")
                
        # Sprawdź poprawność messages
        if not isinstance(request_data['messages'], list):
            raise ValueError("Pole 'messages' musi być listą")
            
        if not request_data['messages']:
            raise ValueError("Lista wiadomości nie może być pusta")
            
        for msg in request_data['messages']:
            if not isinstance(msg, dict):
                raise ValueError("Każda wiadomość musi być słownikiem")
            if 'role' not in msg or 'content' not in msg:
                raise ValueError("Wiadomość musi zawierać pola 'role' i 'content'")
                
        return True

    def send_request(self, model: str, prompt: str) -> Dict[str, Any]:
        """Wysyła synchroniczne żądanie do API.
        
        Args:
            model: Nazwa modelu
            prompt: Treść promptu
            
        Returns:
            Dict[str, Any]: Odpowiedź od API
            
        Raises:
            Exception: Gdy wystąpi błąd podczas żądania
        """
        provider_config = self.get_provider_config(model)
        
        messages = [{"role": "user", "content": prompt}]
        payload = self.build_request_payload(model, prompt)
        
        retries = 0
        while retries < self.max_retries:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    response = loop.create_task(self.send_request_async(
                        provider_config["url"],
                        payload,
                        provider_config["headers"]
                    ))
                    return loop.run_until_complete(response)
                else:
                    return loop.run_until_complete(self.send_request_async(
                        provider_config["url"],
                        payload,
                        provider_config["headers"]
                    ))
            except Exception as e:
                retries += 1
                if retries < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    raise 
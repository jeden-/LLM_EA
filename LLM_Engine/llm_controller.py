"""
Moduł kontrolera LLM odpowiedzialnego za zarządzanie komunikacją z modelami.
"""
import asyncio
import logging
from typing import Dict, Any, Optional

from .model_selector import ModelSelector
from .request_manager import RequestManager
from .response_handler import ResponseHandler

logger = logging.getLogger(__name__)

class LLMController:
    """Kontroler zarządzający komunikacją z modelami LLM."""
    
    def __init__(self, config: Dict[str, Any]):
        """Inicjalizacja kontrolera LLM.
        
        Args:
            config: Słownik z konfiguracją dla kontrolera i jego komponentów
        """
        self.model_selector = ModelSelector(config.get('model_selector', {}))
        self.request_manager = RequestManager(config.get('request_manager', {}))
        self.response_handler = ResponseHandler()
        self.active_model = None
        
    def select_model(self, task_type: str) -> str:
        """Wybiera odpowiedni model LLM dla danego zadania.
        
        Args:
            task_type: Typ zadania do wykonania
            
        Returns:
            Nazwa wybranego modelu
        """
        self.active_model = self.model_selector.select_model(task_type=task_type)
        return self.active_model
        
    def prepare_prompt(self, task_type: str, data: Dict[str, Any]) -> str:
        """Przygotowuje prompt dla modelu na podstawie szablonu.
        
        Args:
            task_type: Typ zadania
            data: Dane do wykorzystania w prompcie
            
        Returns:
            Przygotowany prompt
        """
        return self.request_manager.prepare_prompt(task_type=task_type, data=data)
        
    def send_request(self, prompt: str) -> Dict[str, Any]:
        """Wysyła zapytanie do API modelu.
        
        Args:
            prompt: Przygotowany prompt dla modelu
            
        Returns:
            Odpowiedź od API modelu
            
        Raises:
            ValueError: Gdy nie wybrano aktywnego modelu
        """
        if not self.active_model:
            raise ValueError("Nie wybrano aktywnego modelu. Użyj najpierw metody select_model.")
            
        payload = self.request_manager.build_request_payload(self.active_model, prompt)
        response = asyncio.run(self.request_manager.send_request_async(payload))
        return response
        
    def handle_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Przetwarza odpowiedź od modelu.
        
        Args:
            response: Surowa odpowiedź od API
            
        Returns:
            Przetworzona odpowiedź
        """
        return self.response_handler.process_response(response)
        
    def execute_llm_task(self, task_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Wykonuje pełen cykl zadania LLM.
        
        Args:
            task_type: Typ zadania do wykonania
            data: Dane wejściowe dla zadania
            
        Returns:
            Przetworzona odpowiedź od modelu
        """
        self.select_model(task_type=task_type)
        prompt = self.prepare_prompt(task_type=task_type, data=data)
        response = self.send_request(prompt)
        return self.handle_response(response) 
"""
Moduł obsługujący przetwarzanie odpowiedzi od modeli LLM.
"""
import logging
from typing import Dict, Any, Optional
from LLM_Engine.response_parser import ResponseParserFactory

logger = logging.getLogger(__name__)

class ResponseHandler:
    """
    Klasa odpowiedzialna za przetwarzanie odpowiedzi od modeli LLM.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, parser_factory: Optional[ResponseParserFactory] = None):
        """Inicjalizacja handlera odpowiedzi.
        
        Args:
            config: Słownik z konfiguracją handlera
            parser_factory: Fabryka parserów odpowiedzi
        """
        self.config = config or {}
        self.parser_factory = parser_factory or ResponseParserFactory()
        
    def extract_content(self, response: Dict[str, Any]) -> Optional[str]:
        """
        Ekstrahuje treść z odpowiedzi API.
        
        Args:
            response: Odpowiedź od API w formacie słownika
            
        Returns:
            str: Wyekstrahowana treść lub None w przypadku błędu
        """
        try:
            if not isinstance(response, dict):
                logger.warning("Nieprawidłowy format odpowiedzi")
                return None
                
            if "choices" not in response:
                logger.warning("Brak pola 'choices' w odpowiedzi")
                return None
                
            choices = response["choices"]
            if not choices or not isinstance(choices, list):
                logger.warning("Puste lub nieprawidłowe pole 'choices'")
                return None
                
            first_choice = choices[0]
            if not isinstance(first_choice, dict):
                logger.warning("Nieprawidłowy format pierwszego wyboru")
                return None
                
            if "message" in first_choice:
                message = first_choice["message"]
                if isinstance(message, dict) and "content" in message:
                    return message["content"]
            elif "text" in first_choice:
                return first_choice["text"]
                
            logger.warning("Nieprawidłowa odpowiedź od API")
            return None
            
        except Exception as e:
            logger.error(f"Błąd podczas ekstrakcji treści: {str(e)}")
            return None
            
    def process_response(self, response: Dict[str, Any], task_type: str) -> Dict[str, Any]:
        """
        Przetwarza odpowiedź zgodnie z typem zadania.
        
        Args:
            response: Odpowiedź od API
            task_type: Typ zadania
            
        Returns:
            Dict[str, Any]: Przetworzona odpowiedź
        """
        content = self.extract_content(response)
        if content is None:
            logger.warning(f"Nie udało się wyekstrahować treści dla zadania {task_type}")
            return {}
            
        try:
            # Użycie fabryki parserów do uzyskania odpowiedniego parsera
            parser = self.parser_factory.get_parser(task_type)
            
            # Parsowanie i walidacja odpowiedzi
            parsed_data = parser.parse(content)
            valid, errors = parser.validate(parsed_data)
            
            if not valid:
                logger.warning(f"Walidacja odpowiedzi nie powiodła się: {errors}")
                return {}
                
            return parsed_data
            
        except Exception as e:
            logger.error(f"Błąd podczas przetwarzania odpowiedzi: {str(e)}")
            return {} 
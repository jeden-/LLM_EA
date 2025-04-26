"""
Klient X.AI do komunikacji z modelem Grok-3.

Ten moduł implementuje komunikację z API X.AI (Grok), umożliwiając:
1. Inicjalizację i konfigurację modelu
2. Wysyłanie promptów
3. Odbieranie i przetwarzanie odpowiedzi
4. Obsługę błędów i ponowne próby
"""

import os
import time
import json
import logging
import requests
from typing import Dict, Any, Optional, Union, List
import re

logger = logging.getLogger(__name__)

class GrokClient:
    """
    Klient do komunikacji z X.AI API dla modelu Grok.
    
    Umożliwia konfigurację i używanie modelu Grok
    do analizy danych rynkowych i podejmowania decyzji handlowych.
    """
    
    def __init__(
        self, 
        api_key: str,
        model_name: str = "grok-3-mini-fast-beta",
        base_url: str = "https://api.x.ai/v1",
        timeout: int = 180,
        max_retries: int = 3,
        retry_delay: int = 2
    ):
        """
        Inicjalizuje klienta Grok.
        
        Args:
            api_key: Klucz API X.AI
            model_name: Nazwa modelu do użycia (domyślnie "grok-3-mini-fast-beta")
            base_url: Bazowy URL API X.AI (domyślnie "https://api.x.ai/v1")
            timeout: Maksymalny czas oczekiwania na odpowiedź w sekundach
            max_retries: Maksymalna liczba ponownych prób w przypadku błędu
            retry_delay: Opóźnienie między próbami w sekundach
        """
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.api_endpoint = f"{self.base_url}/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Sprawdzenie dostępności modelu
        self._check_api_availability()
    
    def _check_api_availability(self) -> bool:
        """
        Sprawdza, czy API jest dostępne.
        
        Returns:
            bool: True jeśli API jest dostępne, w przeciwnym wypadku zgłasza wyjątek
        
        Raises:
            ConnectionError: Jeśli nie można połączyć się z API
        """
        try:
            # Wysyłamy bardzo prosty request, aby sprawdzić połączenie
            test_payload = {
                "messages": [
                    {"role": "user", "content": "Test connection"}
                ],
                "model": self.model_name,
                "max_tokens": 10
            }
            
            response = requests.post(
                self.api_endpoint, 
                headers=self.headers,
                json=test_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Połączenie z API X.AI działa, model {self.model_name} jest dostępny.")
                return True
            else:
                logger.warning(f"API X.AI zwróciło kod statusu {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Nie można połączyć się z API X.AI: {str(e)}"
            logger.error(error_msg)
            # Nie zgłaszamy wyjątku, tylko zwracamy False
            return False
    
    def generate(
        self, 
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        top_p: float = 0.9,
        max_tokens: int = 2048
    ) -> str:
        """
        Generuje odpowiedź z modelu Grok na podstawie promptu.
        
        Args:
            prompt: Główny prompt z zapytaniem
            system_prompt: Opcjonalny prompt systemowy (kontekst)
            temperature: Parametr losowości (0.0-1.0)
            top_p: Parametr różnorodności (0.0-1.0)
            max_tokens: Maksymalna liczba tokenów odpowiedzi
            
        Returns:
            str: Wygenerowana odpowiedź
            
        Raises:
            ConnectionError: Jeśli nie można połączyć się z API
            RuntimeError: Jeśli generowanie odpowiedzi się nie powiodło
        """
        messages = []
        
        # Dodanie promptu systemowego, jeśli istnieje
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Dodanie głównego promptu
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        # Mierzenie czasu całego procesu generowania
        total_start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Wysyłanie promptu do modelu {self.model_name} (próba {attempt + 1}/{self.max_retries})")
                start_time = time.time()
                
                response = requests.post(
                    self.api_endpoint,
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                elapsed_time = time.time() - start_time
                logger.info(f"Otrzymano odpowiedź w {elapsed_time:.2f} sekundach")
                
                result = response.json()
                response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                total_elapsed = time.time() - total_start_time
                logger.info(f"Całkowity czas generowania: {total_elapsed:.2f}s")
                
                return response_text
                
            except requests.exceptions.RequestException as e:
                elapsed = time.time() - total_start_time
                logger.warning(f"Błąd podczas generowania odpowiedzi po {elapsed:.2f}s (próba {attempt + 1}/{self.max_retries}): {str(e)}")
                
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Ponowna próba za {wait_time} sekund...")
                    time.sleep(wait_time)
                else:
                    error_msg = f"Wszystkie próby generowania odpowiedzi nie powiodły się po {elapsed:.2f}s: {str(e)}"
                    logger.error(error_msg)
                    
                    # Zwróć awaryjną odpowiedź zamiast zgłaszania wyjątku
                    return f"""{{
                      "error": "api_error",
                      "message": "Nie udało się wygenerować odpowiedzi: {str(e)}",
                      "action": "hold",
                      "explanation": "Ze względu na błąd API, zalecam powstrzymanie się od działania."
                    }}"""
    
    def _extract_json_from_text(self, text: str) -> str:
        """
        Extract JSON object from text using various methods.
        
        Args:
            text: Text containing a JSON object
            
        Returns:
            str: Extracted JSON string or empty string if not found
        """
        # Obsługa przypadku, gdy text jest None
        if text is None:
            logger.warning("Received None text in _extract_json_from_text")
            return ""
            
        # Method 1: Look for standard JSON between curly braces
        json_start = text.find('{')
        json_end = text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            # Found potential JSON
            json_str = text[json_start:json_end]
            
            # Simple validation check
            try:
                json.loads(json_str)
                return json_str
            except json.JSONDecodeError:
                # Try fixing common JSON issues
                logger.debug("Initial JSON parse failed, trying to fix common issues")
                
                # Replace single quotes with double quotes (common issue)
                fixed_json = json_str.replace("'", '"')
                
                # Ensure property names are double-quoted
                fixed_json = re.sub(r'([{,])\s*([a-zA-Z0-9_]+):', r'\1"\2":', fixed_json)
                
                try:
                    json.loads(fixed_json)
                    return fixed_json
                except json.JSONDecodeError:
                    logger.debug("Failed to fix JSON with regex")
        
        # Method 2: Look for JSON in code blocks (common model output format)
        code_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        for block in code_blocks:
            if '{' in block and '}' in block:
                json_start = block.find('{')
                json_end = block.rfind('}') + 1
                
                json_str = block[json_start:json_end]
                try:
                    json.loads(json_str)
                    return json_str
                except json.JSONDecodeError:
                    # Try fixing common JSON issues
                    fixed_json = json_str.replace("'", '"')
                    fixed_json = re.sub(r'([{,])\s*([a-zA-Z0-9_]+):', r'\1"\2":', fixed_json)
                    
                    try:
                        json.loads(fixed_json)
                        return fixed_json
                    except json.JSONDecodeError:
                        pass
        
        # Last resort: Create a minimal JSON with whatever we can extract
        # Look for key-value patterns in the text
        trend_match = re.search(r'trend["\']?\s*:\s*["\']?([a-zA-Z]+)["\']?', text, re.IGNORECASE)
        support_match = re.findall(r'support["\']?\s*:\s*\[([^\]]+)\]', text, re.IGNORECASE)
        resistance_match = re.findall(r'resistance["\']?\s*:\s*\[([^\]]+)\]', text, re.IGNORECASE)
        
        if any([trend_match, support_match, resistance_match]):
            logger.info("Creating minimal JSON from extracted patterns")
            minimal_json = {
                "analysis": {
                    "trend": trend_match.group(1) if trend_match else "unknown",
                    "key_levels": {
                        "support": self._parse_number_list(support_match[0] if support_match else ""),
                        "resistance": self._parse_number_list(resistance_match[0] if resistance_match else "")
                    }
                },
                "extracted_from_text": True
            }
            return json.dumps(minimal_json)
        
        # Could not extract valid JSON
        return ""
    
    def _parse_number_list(self, text: str) -> List[float]:
        """
        Parse a list of numbers from text.
        
        Args:
            text: Text containing numbers separated by commas
            
        Returns:
            List[float]: List of parsed numbers
        """
        if not text:
            return []
            
        # Extract all numbers from the text
        number_matches = re.findall(r'[-+]?\d*\.\d+|\d+', text)
        return [float(n) for n in number_matches]
        
    def generate_with_json_output(
        self, 
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generates a response from the Grok model in JSON format.
        
        Args:
            prompt: Main prompt
            system_prompt: Optional system prompt (context)
            temperature: Randomness parameter (0.0-1.0)
            schema: Optional JSON schema defining the expected response structure
            
        Returns:
            Dict[str, Any]: Response in JSON format
            
        Raises:
            ValueError: If the response is not valid JSON
        """
        # Use English instructions for better model response
        json_instruction = (
            "Your response MUST be in JSON format. "
            "Do not add any text before or after the JSON object. "
            "Your answer should contain only a valid JSON object."
        )
        
        if schema:
            json_instruction += f" The response structure should follow this schema: {json.dumps(schema, ensure_ascii=False)}"
        
        # Add JSON example to help model format correctly
        json_instruction += """
Example of correct response format:
{
  "analysis": {
    "trend": "bullish",
    "key_levels": {
      "support": [1.0720, 1.0705],
      "resistance": [1.0780, 1.0800]
    }
  },
  "recommendation": "buy"
}
"""
        
        if system_prompt:
            enhanced_system_prompt = f"{system_prompt}\n\n{json_instruction}"
        else:
            enhanced_system_prompt = json_instruction
        
        # Use a more explicit JSON-focused prompt
        json_prompt = f"Generate a JSON response with the following format: {json_instruction}\n\nQuery: {prompt}"
        
        # Generating response
        try:
            # First attempt - standard approach
            raw_response = self.generate(
                prompt=json_prompt,
                system_prompt="You are a JSON API. Respond ONLY with a valid JSON object.",
                temperature=temperature
            )
            
            # Sprawdzenie czy odpowiedź nie jest None
            if raw_response is None:
                logger.warning("Received None response from generate method, returning error JSON")
                return {
                    "error": "timeout",
                    "message": "Model timed out or failed to generate a response"
                }
            
            # Log the raw response for debugging
            logger.debug(f"Raw JSON response: {raw_response[:100]}...")
            
            # Extract JSON from the response
            json_str = self._extract_json_from_text(raw_response)
            
            if not json_str:
                # Second attempt with more explicit instructions
                logger.warning("No JSON object found in response, trying fallback generation")
                fallback_prompt = (
                    "Generate a JSON object with the following structure:\n"
                    "{\n"
                    '  "analysis": {\n'
                    '    "trend": "bullish/bearish/sideways",\n'
                    '    "key_levels": {\n'
                    '      "support": [number, number],\n'
                    '      "resistance": [number, number]\n'
                    '    }\n'
                    '  },\n'
                    '  "recommendation": "buy/sell/hold"\n'
                    "}\n\n"
                    f"Query: {prompt}"
                )
                
                raw_response = self.generate(
                    prompt=fallback_prompt,
                    system_prompt="You are a JSON API. Your output will be parsed by a machine. Respond ONLY with a valid JSON object. No explanations.",
                    temperature=0.1
                )
                
                # Sprawdzenie czy odpowiedź fallbackowa nie jest None
                if raw_response is None:
                    logger.warning("Received None response from fallback generate method, returning error JSON")
                    return {
                        "error": "timeout",
                        "message": "Fallback model timed out or failed to generate a response"
                    }
                
                json_str = self._extract_json_from_text(raw_response)
                
                if not json_str:
                    # Last resort - create a minimal valid JSON
                    logger.warning("Still no valid JSON found, creating a minimal response")
                    json_str = json.dumps({
                        "error": "Could not generate proper JSON response",
                        "extracted_text": raw_response[:200] + "..." if len(raw_response) > 200 else raw_response
                    })
            
            logger.info(f"Extracted JSON string of length {len(json_str)}")
            return json.loads(json_str)
            
        except Exception as e:
            # Obsługa wyjątku w bezpieczny sposób, unikając odwoływania się do raw_response
            # jeśli może być None
            error_msg = f"Unable to parse response as JSON: {str(e)}"
            if raw_response is not None:
                error_msg += f"\nReceived response: {raw_response[:500]}..."
            logger.error(error_msg)
            
            # Return a valid JSON with error information instead of raising an exception
            return {
                "error": "Failed to generate proper JSON",
                "error_details": str(e),
                "partial_response": raw_response[:200] + "..." if raw_response and len(raw_response) > 200 else str(raw_response)
            }


# Przykład użycia
if __name__ == "__main__":
    # Konfiguracja logowania
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Inicjalizacja klienta (wymaga klucza API)
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        print("Ustaw zmienną środowiskową XAI_API_KEY z kluczem API X.AI")
    else:
        client = GrokClient(api_key=api_key)
        
        # Przykładowy prompt
        test_prompt = "Wyjaśnij, jak działa strategia handlowa oparta na VWAP."
        
        # Generowanie odpowiedzi
        response = client.generate(test_prompt)
        print("Odpowiedź:")
        print(response) 
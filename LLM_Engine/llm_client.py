"""
Klient LLM do komunikacji z silnikiem Ollama.
"""
import os
import requests
import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Union, Optional
from datetime import datetime

from .utils import parse_llm_response

# Konfiguracja loggera
logger = logging.getLogger(__name__)

class LLMClient:
    """
    Klient do komunikacji z silnikiem LLM (Ollama).
    
    Umożliwia generowanie odpowiedzi, zarządzanie modelami oraz cachowanie wyników.
    """
    
    def __init__(self, 
                 model_name: str = "deepseek-coder:1.3b", 
                 base_url: str = "http://localhost:11434", 
                 timeout: int = 180,
                 max_retries: int = 3,
                 use_cache: bool = True,
                 cache_dir: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: Optional[int] = None,
                 aggressive_caching: bool = True):
        """
        Inicjalizuje klienta LLM.
        
        Args:
            model_name: Nazwa modelu do użycia (domyślnie "deepseek-coder:1.3b")
            base_url: Bazowy URL API (domyślnie "http://localhost:11434")
            timeout: Timeout dla żądań HTTP w sekundach (domyślnie 180)
            max_retries: Maksymalna liczba prób przy niepowodzeniu (domyślnie 3)
            use_cache: Czy używać cachowania odpowiedzi (domyślnie True)
            cache_dir: Ścieżka do katalogu cache (domyślnie zostanie utworzony w .llm_cache)
            temperature: Temperatura generowania (0.0-1.0, domyślnie 0.7)
            max_tokens: Maksymalna liczba tokenów do wygenerowania (domyślnie None)
            aggressive_caching: Czy używać bardziej agresywnego cachowania (ignoruje niektóre parametry)
        """
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.use_cache = use_cache
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.aggressive_caching = aggressive_caching
        
        # Inicjalizacja katalogu cache
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # Domyślnie używamy katalogu .llm_cache w głównym folderze projektu
            root_dir = Path(__file__).parent.parent
            self.cache_dir = root_dir / ".llm_cache"
        
        # Upewnij się, że katalog cache istnieje
        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Używanie cache w katalogu: {self.cache_dir}")
            
            # Statystyki cache
            self.cache_hits = 0
            self.cache_misses = 0
    
    def _generate_cache_key(self, model: str, prompt: str, options: dict = None) -> str:
        """
        Generuje unikalny klucz cache dla danego zapytania.
        
        Args:
            model: Nazwa modelu
            prompt: Tekst promptu
            options: Dodatkowe opcje (system prompt, temperatura, etc.)
            
        Returns:
            str: Unikalny klucz cache
        """
        # Normalizacja promptu - usunięcie nadmiarowych białych znaków
        normalized_prompt = " ".join(prompt.split())
        
        # Przygotowanie podstawowych danych do hasha
        data = {
            "model": model,
            "prompt": normalized_prompt
        }
        
        # Dodanie znormalizowanych opcji
        if options:
            normalized_options = {}
            
            # Normalizacja system promptu
            if "system" in options and options["system"]:
                normalized_options["system"] = " ".join(options["system"].split())
                
            # Zaokrąglenie temperatury do 1 miejsca po przecinku w trybie agresywnym
            # lub do 2 miejsc w trybie normalnym
            if "temperature" in options:
                temp = float(options["temperature"])
                if self.aggressive_caching:
                    normalized_options["temperature"] = round(temp, 1)
                else:
                    normalized_options["temperature"] = round(temp, 2)
                
            # W trybie agresywnym ignorujemy niektóre parametry
            if not self.aggressive_caching:
                # Dodanie max_tokens bez normalizacji
                if "max_tokens" in options and options["max_tokens"]:
                    normalized_options["max_tokens"] = options["max_tokens"]
                    
                # Dodanie innych parametrów
                for key in options:
                    if key not in ["system", "temperature", "max_tokens"]:
                        normalized_options[key] = options[key]
                
            data["options"] = normalized_options
            
        # Generowanie hasha
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """
        Zwraca ścieżkę do pliku cache.
        
        Args:
            cache_key: Klucz cache
            
        Returns:
            Ścieżka do pliku cache
        """
        return self.cache_dir / f"{cache_key}.json"
    
    def _save_to_cache(self, cache_key: str, response: Dict[str, Any]) -> None:
        """
        Zapisuje odpowiedź do cache.
        
        Args:
            cache_key: Klucz cache
            response: Odpowiedź do zapisania
        """
        if not self.use_cache:
            return
            
        cache_path = self._get_cache_path(cache_key)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(response, f, ensure_ascii=False, indent=2)
            logger.debug(f"Zapisano odpowiedź do cache: {cache_path}")
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania do cache: {e}")
    
    def _load_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Ładuje odpowiedź z cache.
        
        Args:
            cache_key: Klucz cache
            
        Returns:
            Zapisana odpowiedź lub None, jeśli nie znaleziono
        """
        if not self.use_cache:
            return None
            
        cache_path = self._get_cache_path(cache_key)
        if not os.path.exists(str(cache_path)):
            # Cache miss
            self.cache_misses += 1
            return None
            
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                response = json.load(f)
            logger.debug(f"Załadowano odpowiedź z cache: {cache_path}")
            
            # Cache hit
            self.cache_hits += 1
            
            # Dodanie informacji o cache
            if isinstance(response, dict):
                if "_metadata" not in response:
                    response["_metadata"] = {}
                response["_metadata"]["cache_hit"] = True
                response["_metadata"]["cache_time"] = datetime.now().isoformat()
            
            return response
        except Exception as e:
            logger.error(f"Błąd podczas ładowania z cache: {e}")
            self.cache_misses += 1
            return None
    
    def generate(self, 
                prompt: str, 
                model: Optional[str] = None, 
                system_prompt: Optional[str] = None,
                temperature: Optional[float] = None,
                max_tokens: Optional[int] = None,
                stream: bool = False) -> Dict[str, Any]:
        """
        Generuje odpowiedź na podstawie promptu.
        
        Args:
            prompt: Tekst promptu
            model: Nazwa modelu (opcjonalnie, domyślnie używa model_name z inicjalizacji)
            system_prompt: Prompt systemowy (opcjonalnie)
            temperature: Temperatura generowania (opcjonalnie)
            max_tokens: Maksymalna liczba tokenów (opcjonalnie)
            stream: Czy używać streamowania (domyślnie False)
            
        Returns:
            Słownik z odpowiedzią i metadanymi
        """
        # Użyj domyślnych wartości, jeśli nie podano
        model = model or self.model_name
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens
        
        # Sprawdzenie rozmiaru promptu
        prompt_size = len(prompt)
        logger.info(f"Rozmiar promptu: {prompt_size} znaków")

        # Przygotuj payload
        payload = {
            "model": model,
            "prompt": prompt,
            "options": {
                "temperature": temperature,
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
            
        if system_prompt:
            payload["options"]["system"] = system_prompt
            
        # Sprawdź cache przed generowaniem
        if self.use_cache and not stream:
            cache_key = self._generate_cache_key(model, prompt, {
                "system": system_prompt,
                "temperature": temperature,
                "max_tokens": max_tokens
            })
            cached_response = self._load_from_cache(cache_key)
            if cached_response:
                return cached_response
            
            logger.info(f"Brak odpowiedzi w cache, generowanie nowej (klucz: {cache_key[:8]}...)")

        # Inicjalizacja zmiennych dla ponowień
        total_start_time = time.time()
        retry_count = 0
        
        while True:
            try:
                # Wysłanie żądania do API
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=self.timeout,
                    stream=stream
                )
                response.raise_for_status()
                
                # Parsowanie odpowiedzi
                result = response.json()
                
                # Zapisz do cache jeśli włączone
                if self.use_cache and not stream and 'cache_key' in locals():
                    self._save_to_cache(cache_key, result)
                
                return result
                
            except requests.exceptions.Timeout:
                total_elapsed = time.time() - total_start_time
                logger.warning(f"Timeout po {total_elapsed:.2f}s. Prompt zbyt długi ({prompt_size} znaków)")
                retry_count += 1
                wait_time = 2 ** retry_count  # Exponential backoff
                
                if retry_count <= self.max_retries:
                    logger.warning(f"Ponawianie za {wait_time}s... (próba {retry_count}/{self.max_retries})")
                    time.sleep(wait_time)
                else:
                    error_msg = f"Timeout - nie udało się uzyskać odpowiedzi w ciągu {self.timeout}s"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
            except requests.exceptions.RequestException as e:
                retry_count += 1
                wait_time = 2 ** retry_count  # Exponential backoff
                
                if retry_count <= self.max_retries:
                    logger.warning(f"Błąd żądania: {e}. Ponawianie za {wait_time}s... (próba {retry_count}/{self.max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Maksymalna liczba prób wyczerpana: {e}")
                    raise Exception(f"Nie udało się połączyć z API LLM: {e}")
            
            except json.JSONDecodeError:
                logger.error("Nie udało się sparsować odpowiedzi JSON")
                if response:
                    logger.error(f"Otrzymana odpowiedź: {response.text}")
                raise Exception("Nieprawidłowa odpowiedź z API LLM")
    
    def get_models(self) -> List[Dict[str, Any]]:
        """
        Pobiera listę dostępnych modeli.
        
        Returns:
            Lista dostępnych modeli
            
        Raises:
            Exception: W przypadku błędu komunikacji z API
        """
        url = f"{self.base_url}/api/tags"
        
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            return result.get("models", [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Błąd podczas pobierania modeli: {e}")
            raise Exception(f"Nie udało się pobrać listy modeli: {e}")
        
        except json.JSONDecodeError:
            logger.error("Nie udało się sparsować odpowiedzi JSON")
            raise Exception("Nieprawidłowa odpowiedź z API modeli")

    def get_model_info(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Pobiera informacje o modelu.
        
        Args:
            model_name: Nazwa modelu (opcjonalnie, domyślnie używa modelu skonfigurowanego w kliencie)
            
        Returns:
            Informacje o modelu
            
        Raises:
            Exception: W przypadku błędu komunikacji z API
        """
        model = model_name or self.model_name
        url = f"{self.base_url}/api/show"
        
        try:
            response = requests.post(
                url, 
                json={"name": model},
                timeout=self.timeout
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Błąd podczas pobierania informacji o modelu: {e}")
            raise Exception(f"Nie udało się pobrać informacji o modelu: {e}")
        
        except json.JSONDecodeError:
            logger.error("Nie udało się sparsować odpowiedzi JSON")
            raise Exception("Nieprawidłowa odpowiedź z API modelu")

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Zwraca statystyki cache.
        
        Returns:
            Dict[str, int]: Statystyki cache (hits, misses, hit_ratio)
        """
        total = self.cache_hits + self.cache_misses
        hit_ratio = (self.cache_hits / total) * 100 if total > 0 else 0
        return {
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "total": total,
            "hit_ratio": hit_ratio
        } 
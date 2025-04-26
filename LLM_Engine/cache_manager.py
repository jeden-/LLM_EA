"""
Moduł zarządzania cache dla silnika LLM.

Ten moduł odpowiada za:
1. Zapisywanie i odczytywanie wyników z cache
2. Zarządzanie kluczami cache
3. Optymalizację użycia pamięci
"""

import os
import json
import time
import logging
import hashlib
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Klasa zarządzająca cache'owaniem zapytań i odpowiedzi modelu LLM.
    
    Pozwala na zapisywanie i odczytywanie wyników w celu uniknięcia
    ponownego generowania odpowiedzi na te same zapytania.
    """
    
    def __init__(self, cache_dir: str, enabled: bool = True, max_age_seconds: int = 86400):
        """
        Inicjalizuje menedżera cache.
        
        Args:
            cache_dir: Ścieżka do katalogu przechowującego pliki cache
            enabled: Czy cache jest włączony
            max_age_seconds: Maksymalny wiek plików cache w sekundach (domyślnie 24h)
        """
        self.cache_dir = cache_dir
        self.enabled = enabled
        self.max_age_seconds = max_age_seconds
        
        if self.enabled:
            os.makedirs(self.cache_dir, exist_ok=True)
            logger.info(f"Zainicjalizowano cache w katalogu {self.cache_dir}")
            
            # Czyszczenie starego cache przy inicjalizacji
            self._clean_old_cache()
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Pobiera dane z cache na podstawie klucza.
        
        Args:
            key: Klucz identyfikujący zapytanie
            
        Returns:
            Optional[Dict[str, Any]]: Znalezione dane lub None jeśli nie znaleziono
        """
        if not self.enabled:
            return None
            
        cache_file = self._get_cache_file_path(key)
        
        if not os.path.exists(cache_file):
            return None
            
        try:
            # Sprawdzenie wieku pliku
            file_age = time.time() - os.path.getmtime(cache_file)
            if file_age > self.max_age_seconds:
                logger.debug(f"Plik cache {cache_file} jest zbyt stary ({file_age:.1f}s), usuwanie...")
                os.remove(cache_file)
                return None
                
            # Odczyt danych
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                
            logger.debug(f"Znaleziono dane w cache dla klucza {key}")
            return cached_data
            
        except Exception as e:
            logger.warning(f"Błąd podczas odczytu cache: {str(e)}")
            # W przypadku błędu, lepiej usunąć uszkodzony plik
            if os.path.exists(cache_file):
                os.remove(cache_file)
            return None
    
    def set(self, key: str, data: Dict[str, Any]) -> bool:
        """
        Zapisuje dane do cache.
        
        Args:
            key: Klucz identyfikujący zapytanie
            data: Dane do zapisania
            
        Returns:
            bool: True jeśli udało się zapisać, False w przeciwnym wypadku
        """
        if not self.enabled:
            return False
            
        cache_file = self._get_cache_file_path(key)
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"Zapisano dane do cache dla klucza {key}")
            return True
            
        except Exception as e:
            logger.warning(f"Błąd podczas zapisu do cache: {str(e)}")
            return False
    
    def invalidate(self, key: str) -> bool:
        """
        Usuwa dane z cache na podstawie klucza.
        
        Args:
            key: Klucz identyfikujący zapytanie
            
        Returns:
            bool: True jeśli udało się usunąć, False w przeciwnym wypadku
        """
        if not self.enabled:
            return False
            
        cache_file = self._get_cache_file_path(key)
        
        if not os.path.exists(cache_file):
            return False
            
        try:
            os.remove(cache_file)
            logger.debug(f"Usunięto dane z cache dla klucza {key}")
            return True
            
        except Exception as e:
            logger.warning(f"Błąd podczas usuwania z cache: {str(e)}")
            return False
    
    def clear(self) -> bool:
        """
        Czyści całe cache.
        
        Returns:
            bool: True jeśli udało się wyczyścić, False w przeciwnym wypadku
        """
        if not self.enabled:
            return False
            
        try:
            for file_name in os.listdir(self.cache_dir):
                if file_name.endswith('.json'):
                    file_path = os.path.join(self.cache_dir, file_name)
                    os.remove(file_path)
                    
            logger.info(f"Wyczyszczono wszystkie pliki cache")
            return True
            
        except Exception as e:
            logger.warning(f"Błąd podczas czyszczenia cache: {str(e)}")
            return False
    
    def _get_cache_file_path(self, key: str) -> str:
        """
        Generuje ścieżkę do pliku cache na podstawie klucza.
        
        Args:
            key: Klucz identyfikujący zapytanie
            
        Returns:
            str: Ścieżka do pliku cache
        """
        # Haszowanie klucza, aby uniknąć problemów z nazwami plików
        hashed_key = hashlib.md5(key.encode('utf-8')).hexdigest()
        return os.path.join(self.cache_dir, f"{hashed_key}.json")
    
    def _clean_old_cache(self) -> None:
        """
        Czyści stare pliki cache.
        """
        try:
            current_time = time.time()
            count = 0
            
            for file_name in os.listdir(self.cache_dir):
                if file_name.endswith('.json'):
                    file_path = os.path.join(self.cache_dir, file_name)
                    file_age = current_time - os.path.getmtime(file_path)
                    
                    if file_age > self.max_age_seconds:
                        os.remove(file_path)
                        count += 1
                        
            if count > 0:
                logger.info(f"Usunięto {count} przestarzałych plików cache")
                
        except Exception as e:
            logger.warning(f"Błąd podczas czyszczenia starego cache: {str(e)}")


# Przykład użycia
if __name__ == "__main__":
    # Konfiguracja logowania
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Inicjalizacja managera cache
    cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
    cache_manager = CacheManager(cache_dir=cache_dir, enabled=True)
    
    # Przykład użycia
    key = "test_key"
    data = {"result": "test_value", "timestamp": time.time()}
    
    # Zapis do cache
    cache_manager.set(key, data)
    
    # Odczyt z cache
    cached_data = cache_manager.get(key)
    print(f"Dane z cache: {cached_data}")
    
    # Usunięcie z cache
    cache_manager.invalidate(key) 
"""
Moduł konfiguracyjny dla silnika LLM.

Odpowiada za:
1. Ładowanie konfiguracji z pliku
2. Przechowywanie globalnych ustawień
3. Dostarczanie parametrów dostępu do API
"""

import os
import json
import logging
import datetime
from typing import Dict, Any, Optional

# Domyślna konfiguracja dla LLM
DEFAULT_LLM_CONFIG = {
    "model_name": "grok-3-mini-fast-beta",
    "model_type": "grok",
    "xai_api_key": "",
    "xai_base_url": "https://api.x.ai/v1",
    "timeout": 60,
    "max_retries": 3,
    "cache_dir": os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache"),
    "enable_caching": True
}

logger = logging.getLogger(__name__)

class Config:
    """
    Przechowuje i zarządza konfiguracją dla komponentów systemu.
    
    Odpowiada za ładowanie, zapisywanie i udostępnianie 
    parametrów konfiguracyjnych dla silnika LLM i innych komponentów.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Inicjalizuje obiekt konfiguracyjny.
        
        Args:
            config_file: Opcjonalna ścieżka do pliku konfiguracyjnego. 
                         Jeśli nie podano, użyte zostaną domyślne wartości.
        """
        # Inicjalizacja z domyślną konfiguracją
        self.config_data = DEFAULT_LLM_CONFIG.copy()
        
        # Ścieżka do pliku konfiguracyjnego
        self.config_file = config_file
        
        # Ładowanie konfiguracji z pliku, jeśli podano
        if self.config_file and os.path.exists(self.config_file):
            self.load_config()
            logger.info(f"Załadowano konfigurację z pliku: {self.config_file}")
        else:
            logger.info("Używanie domyślnej konfiguracji")
            
        # Upewnienie się, że katalog cache istnieje
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
            logger.info(f"Utworzono katalog cache: {self.cache_dir}")
            
        # Konfiguracja logowania
        self._setup_logging()
        
    def load_config(self):
        """Ładuje konfigurację z pliku."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                
            # Aktualizacja tylko tych wartości, które są w pliku
            for key, value in loaded_config.items():
                if key in self.config_data:
                    self.config_data[key] = value
                    
            logger.info(f"Załadowano konfigurację z {self.config_file}")
            
        except Exception as e:
            logger.error(f"Błąd podczas ładowania konfiguracji: {str(e)}")
    
    def save_config(self):
        """Zapisuje aktualną konfigurację do pliku."""
        if not self.config_file:
            logger.warning("Nie określono pliku konfiguracyjnego, konfiguracja nie zostanie zapisana")
            return
            
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
                
            logger.info(f"Zapisano konfigurację do {self.config_file}")
            
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania konfiguracji: {str(e)}")
    
    def update_config(self, config_updates: Dict[str, Any]):
        """
        Aktualizuje konfigurację nowymi wartościami.
        
        Args:
            config_updates: Słownik z nowymi wartościami konfiguracyjnymi
        """
        for key, value in config_updates.items():
            if key in self.config_data:
                self.config_data[key] = value
            else:
                logger.warning(f"Nieznany klucz konfiguracyjny: {key}")
                
        logger.info("Zaktualizowano konfigurację")
    
    def get_config(self) -> Dict[str, Any]:
        """
        Zwraca kopię całej konfiguracji.
        
        Returns:
            Dict[str, Any]: Kopia słownika konfiguracyjnego
        """
        return self.config_data.copy()
    
    def display_config(self) -> str:
        """
        Zwraca sformatowaną reprezentację tekstową aktualnej konfiguracji.
        
        Returns:
            str: Sformatowana konfiguracja
        """
        config_str = "Aktualna konfiguracja:\n"
        for key, value in self.config_data.items():
            if key in ["xai_api_key"] and value:
                value = value[:4] + "****" if len(value) > 4 else "****"
            config_str += f"  - {key}: {value}\n"
            
        return config_str
    
    def _setup_logging(self):
        """Konfiguruje logowanie dla modułu LLM Engine."""
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(log_dir, f"llm_engine_{today}.log")
        
        # Podstawowa konfiguracja logowania - tylko jeśli nie jest jeszcze skonfigurowana
        root_logger = logging.getLogger()
        if not root_logger.handlers:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler()
                ]
            )
            logger.info(f"Skonfigurowano logowanie do pliku: {log_file}")
    
    # Właściwości dla łatwego dostępu do wartości konfiguracyjnych
    
    @property
    def model_name(self) -> str:
        """Zwraca nazwę modelu LLM."""
        return self.config_data.get("model_name", DEFAULT_LLM_CONFIG["model_name"])
    
    @property
    def model_type(self) -> str:
        """Zwraca typ modelu LLM (np. grok)."""
        return self.config_data.get("model_type", DEFAULT_LLM_CONFIG["model_type"])
    
    @property
    def xai_api_key(self) -> str:
        """Zwraca klucz API X.AI."""
        return self.config_data.get("xai_api_key", DEFAULT_LLM_CONFIG["xai_api_key"])
    
    @property
    def xai_base_url(self) -> str:
        """Zwraca bazowy URL API X.AI."""
        return self.config_data.get("xai_base_url", DEFAULT_LLM_CONFIG["xai_base_url"])
    
    @property
    def timeout(self) -> int:
        """Zwraca timeout dla zapytań do API."""
        return self.config_data.get("timeout", DEFAULT_LLM_CONFIG["timeout"])
    
    @property
    def max_retries(self) -> int:
        """Zwraca maksymalną liczbę ponownych prób przy błędach."""
        return self.config_data.get("max_retries", DEFAULT_LLM_CONFIG["max_retries"])
    
    @property
    def cache_dir(self) -> str:
        """Zwraca ścieżkę do katalogu cache."""
        return self.config_data.get("cache_dir", DEFAULT_LLM_CONFIG["cache_dir"])
    
    @property
    def enable_caching(self) -> bool:
        """Zwraca flagę włączenia cache."""
        return self.config_data.get("enable_caching", DEFAULT_LLM_CONFIG["enable_caching"])
    

# Przykładowe użycie
if __name__ == "__main__":
    config = Config()
    print(config.display_config()) 
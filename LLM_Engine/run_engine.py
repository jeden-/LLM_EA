#!/usr/bin/env python
"""
Moduł uruchamiający silnik LLM.

Ten moduł odpowiada za:
1. Inicjalizację silnika LLM
2. Uruchomienie serwisu przetwarzania zapytań
3. Obsługę komunikacji z LLM API
"""

import os
import sys
import time
import json
import signal
import logging
import argparse
from pathlib import Path

# Dodaj główny katalog projektu do ścieżki importu
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from LLM_Engine.llm_engine import LLMEngine

# Konfiguracja ścieżek
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_DIR, "config")
LOG_DIR = os.path.join(PROJECT_DIR, "logs")

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "llm_engine.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("llm_engine_service")

# Flaga zatrzymania
stop_flag = False


def load_config(env: str):
    """
    Ładuje konfigurację z pliku.
    
    Args:
        env: Nazwa środowiska (dev, test, prod)
        
    Returns:
        Słownik z konfiguracją
    """
    config_path = os.path.join(CONFIG_DIR, f"config_{env}.json")
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"Załadowano konfigurację z: {config_path}")
                return config
        except Exception as e:
            logger.error(f"Błąd ładowania konfiguracji: {e}")
    else:
        logger.warning(f"Nie znaleziono pliku konfiguracyjnego: {config_path}")
    
    # Zwracamy podstawową konfigurację
    return {
        "llm_engine": {
            "api_key": "dummy_key_dev",
            "api_url": "https://api.x.ai",
            "model": "gpt-4o",
            "max_tokens": 4096,
            "temperature": 0.7,
            "debug": True
        }
    }


def run_llm_service(config, args):
    """
    Uruchamia serwis silnika LLM.
    
    Args:
        config: Konfiguracja
        args: Argumenty wiersza poleceń
    """
    global stop_flag
    
    # Ustaw poziom logowania
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    logger.info("Uruchamianie serwisu silnika LLM...")
    
    # Pobierz konfigurację silnika LLM
    llm_config = config.get("llm_engine", {})
    
    # Inicjalizacja silnika LLM
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        
        # Utwórz instancję silnika LLM
        engine = LLMEngine(
            api_key=llm_config.get("api_key", "dummy_key"),
            api_url=llm_config.get("api_url", "https://api.x.ai"),
            model=llm_config.get("model", "gpt-4o"),
            max_tokens=llm_config.get("max_tokens", 4096),
            temperature=llm_config.get("temperature", 0.7)
        )
        
        # Inicjalizacja silnika
        if llm_config.get("debug", False):
            # W trybie debug używamy cache'owania
            engine.initialize(use_cache=True)
        else:
            engine.initialize(use_cache=False)
        
        logger.info(f"Silnik LLM zainicjalizowany: {llm_config.get('model')}")
        
        # Główna pętla serwisu
        while not stop_flag:
            # W przyszłości tutaj możemy dodać obsługę kolejki zapytań
            time.sleep(1)
        
        # Zamknięcie silnika
        engine.shutdown()
        logger.info("Silnik LLM zatrzymany")
    
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania serwisu silnika LLM: {e}")
        sys.exit(1)


def signal_handler(signum, frame):
    """
    Obsługuje sygnały systemowe.
    
    Args:
        signum: Numer sygnału
        frame: Bieżąca ramka stosu
    """
    global stop_flag
    logger.info(f"Otrzymano sygnał {signum}, zatrzymywanie serwisu...")
    stop_flag = True


def main():
    """Główna funkcja programu."""
    # Parsowanie argumentów wiersza poleceń
    parser = argparse.ArgumentParser(description="Uruchamia serwis silnika LLM")
    parser.add_argument("--env", choices=["dev", "test", "prod"], default="dev",
                        help="Środowisko (dev, test, prod)")
    parser.add_argument("--debug", action="store_true",
                        help="Uruchom w trybie debugowania")
    args = parser.parse_args()
    
    # Rejestracja obsługi sygnałów
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Ładowanie konfiguracji
    config = load_config(args.env)
    
    # Uruchomienie serwisu
    run_llm_service(config, args)


if __name__ == "__main__":
    main() 
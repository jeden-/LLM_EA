#!/usr/bin/env python
"""
Moduł uruchamiający serwis bazodanowy.

Ten moduł odpowiada za:
1. Inicjalizację bazy danych
2. Uruchomienie serwisu bazodanowego
3. Obsługę zapytań do bazy danych
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

from Database.database import DatabaseHandler

# Konfiguracja ścieżek
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_DIR, "config")
LOG_DIR = os.path.join(PROJECT_DIR, "logs")

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "database.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("database_service")

# Flaga zatrzymania dla obsługi wyjątków
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
        "database": {
            "url": "sqlite:///llm_trader.db",
            "debug": True
        }
    }


def run_database_service(config, args):
    """
    Uruchamia serwis bazodanowy.
    
    Args:
        config: Konfiguracja
        args: Argumenty wiersza poleceń
    """
    global stop_flag
    
    # Ustaw poziom logowania
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    logger.info("Uruchamianie serwisu bazodanowego...")
    
    # Pobierz konfigurację bazy danych
    db_config = config.get("database", {})
    db_url = db_config.get("url", "sqlite:///llm_trader.db")
    
    # Inicjalizacja bazy danych
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        
        # Utwórz instancję obsługi bazy danych
        db_handler = DatabaseHandler(db_url, auto_init=True)
        logger.info(f"Baza danych zainicjalizowana: {db_url}")
        
        # Główna pętla serwisu
        while not stop_flag:
            # W przyszłości tutaj może być logika obsługi żądań
            # w wersji multiprocesorowej
            time.sleep(1)
        
        logger.info("Zatrzymanie serwisu bazodanowego...")
    
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania serwisu bazodanowego: {e}")
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
    parser = argparse.ArgumentParser(description="Uruchamia serwis bazodanowy")
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
    run_database_service(config, args)


if __name__ == "__main__":
    main() 
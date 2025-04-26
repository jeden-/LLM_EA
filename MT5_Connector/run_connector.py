#!/usr/bin/env python
"""
Moduł uruchamiający serwis MT5 Connector.

Ten moduł odpowiada za:
1. Inicjalizację połączenia z platformą MetaTrader 5
2. Uruchomienie serwisu komunikacyjnego
3. Synchronizację danych rynkowych
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

from MT5_Connector.connector import MT5Connector

# Konfiguracja ścieżek
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_DIR, "config")
LOG_DIR = os.path.join(PROJECT_DIR, "logs")

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "mt5_connector.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("mt5_connector_service")

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
        "mt5_connector": {
            "server": "Demo.MetaQuotes.net",
            "login": 12345,
            "password": "demo_password",
            "timeout": 60000,
            "debug": True
        }
    }


def run_connector_service(config, args):
    """
    Uruchamia serwis MT5 Connector.
    
    Args:
        config: Konfiguracja
        args: Argumenty wiersza poleceń
    """
    global stop_flag
    
    # Ustaw poziom logowania
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    logger.info("Uruchamianie serwisu MT5 Connector...")
    
    # Pobierz konfigurację konektora MT5
    mt5_config = config.get("mt5_connector", {})
    
    # Inicjalizacja konektora
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        
        # Utwórz instancję konektora bez parametrów
        connector = MT5Connector()
        
        # Inicjalizacja konektora bez parametrów
        success = connector.initialize()
        if not success:
            logger.error("Nie udało się zainicjalizować konektora MT5")
            sys.exit(1)
        
        logger.info(f"Konektor MT5 zainicjalizowany")
        
        # Główna pętla serwisu
        while not stop_flag:
            time.sleep(1)
        
        # Zakończenie konektora
        connector.shutdown()
        logger.info("Konektor MT5 zatrzymany")
    
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania serwisu MT5 Connector: {e}")
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
    parser = argparse.ArgumentParser(description="Uruchamia serwis MT5 Connector")
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
    run_connector_service(config, args)


if __name__ == "__main__":
    main() 
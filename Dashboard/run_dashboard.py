#!/usr/bin/env python
"""
Moduł inicjalizacji dashboardu.

Ten skrypt uruchamia dashboard systemu handlowego LLM. 
Odpowiada za:
- Inicjalizację interfejsu webowego
- Konfigurację i uruchomienie serwera
- Prezentację danych i statystyk systemu
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path

from Dashboard.app import create_app
from Database.database import DatabaseHandler

# Ścieżki konfiguracji
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_DIR, "config")
LOG_DIR = os.path.join(PROJECT_DIR, "logs", "dashboard")

# Konfiguracja logowania
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "dashboard.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("dashboard")


def load_config(env="dev"):
    """
    Ładuje konfigurację z pliku JSON na podstawie środowiska.
    
    Args:
        env (str): Środowisko (dev, test, prod)
        
    Returns:
        dict: Konfiguracja
    """
    config_path = os.path.join(CONFIG_DIR, f"{env}_config.json")
    
    # Sprawdź czy plik konfiguracyjny istnieje
    if not os.path.exists(config_path):
        logger.warning(f"Plik konfiguracyjny nie istnieje: {config_path}. Używanie konfiguracji domyślnej.")
        return {
            "environment": env,
            "dashboard": {
                "host": "localhost",
                "port": 5000,
                "debug": env == "dev",
                "log_level": "INFO" if env != "dev" else "DEBUG"
            },
            "database": {
                "url": "sqlite:///data/llm_trader.db"
            }
        }
    
    try:
        with open(config_path, 'r') as file:
            config = json.load(file)
            logger.info(f"Załadowano konfigurację dla środowiska: {env}")
            return config
    except Exception as e:
        logger.error(f"Błąd podczas ładowania konfiguracji: {e}")
        sys.exit(1)


def run_dashboard_service(env, host=None, port=None, debug=None):
    """
    Inicjalizuje serwis dashboardu.
    
    Args:
        env (str): Środowisko (dev, test, prod)
        host (str, optional): Host dla serwera Flask
        port (int, optional): Port dla serwera Flask
        debug (bool, optional): Tryb debugowania
    """
    try:
        # Załaduj konfigurację
        config = load_config(env)
        
        # Ustaw poziom logowania
        log_level = config.get("dashboard", {}).get("log_level", "INFO")
        if log_level == "DEBUG":
            logger.setLevel(logging.DEBUG)
        elif log_level == "INFO":
            logger.setLevel(logging.INFO)
        elif log_level == "WARNING":
            logger.setLevel(logging.WARNING)
        elif log_level == "ERROR":
            logger.setLevel(logging.ERROR)
        
        logger.info("Inicjalizacja serwisu Dashboard")
        
        # Ustaw wartości domyślne, jeśli nie zostały podane
        host = host or config.get("dashboard", {}).get("host", "localhost")
        port = port or config.get("dashboard", {}).get("port", 5000)
        
        # Tryb debug jest domyślnie włączony dla środowiska dev
        if debug is None:
            debug = config.get("dashboard", {}).get("debug", env == "dev")
        
        # Połączenie z bazą danych
        db_url = config.get("database", {}).get("url", "sqlite:///data/llm_trader.db")
        db_handler = DatabaseHandler(db_url)
        
        # Tworzenie aplikacji Flask
        app = create_app(db_handler=db_handler, config=config)
        
        logger.info(f"Uruchamianie serwera dashboard na {host}:{port} (debug={debug})")
        app.run(host=host, port=port, debug=debug)
        
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania dashboardu: {e}")
        sys.exit(1)


def main():
    """Funkcja główna skryptu."""
    parser = argparse.ArgumentParser(description="Uruchamia dashboard systemu handlowego LLM")
    parser.add_argument("--env", "-e", type=str, default="dev", 
                        choices=["dev", "test", "prod"],
                        help="Środowisko (dev, test, prod)")
    parser.add_argument("--host", type=str, help="Host serwera Flask")
    parser.add_argument("--port", type=int, help="Port serwera Flask")
    parser.add_argument("--debug", action="store_true", help="Włącza tryb debug")
    
    args = parser.parse_args()
    
    # Uruchom serwis dashboard
    run_dashboard_service(args.env, args.host, args.port, args.debug)


if __name__ == "__main__":
    main() 
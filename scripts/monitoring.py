#!/usr/bin/env python
"""
Moduł uruchamiający monitoring systemu.

Ten moduł odpowiada za:
1. Uruchomienie monitorowania komponentów systemu
2. Zbieranie informacji o stanie systemu
3. Wykrywanie anomalii i problemów
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path

# Dodaj główny katalog projektu do ścieżki importu
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.monitor_system import SystemMonitor

# Konfiguracja ścieżek
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_DIR, "config")
LOG_DIR = os.path.join(PROJECT_DIR, "logs")

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "monitoring.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("monitoring_service")


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
        "monitoring": {
            "interval": 300,
            "debug": True
        }
    }


def run_monitoring_service(config, args):
    """
    Uruchamia serwis monitorowania.
    
    Args:
        config: Konfiguracja
        args: Argumenty wiersza poleceń
    """
    # Ustaw poziom logowania
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    logger.info("Uruchamianie serwisu monitorowania...")
    
    # Pobierz konfigurację monitorowania
    monitoring_config = config.get("monitoring", {})
    db_config = config.get("database", {})
    
    # Określenie interwału monitorowania
    interval = args.interval or monitoring_config.get("interval", 300)  # domyślnie co 5 minut
    
    # Określenie ścieżki do bazy danych
    db_url = db_config.get("url", "sqlite:///llm_trader.db")
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
    else:
        db_path = None
    
    # Inicjalizacja monitorowania
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        os.makedirs(os.path.join(LOG_DIR, "monitoring"), exist_ok=True)
        
        # Utwórz instancję monitora systemu
        monitor = SystemMonitor(interval=interval, db_path=db_path)
        
        logger.info(f"Monitor systemu zainicjalizowany (interwał: {interval}s)")
        
        # Uruchom monitoring w trybie pętli lub pojedynczego sprawdzenia
        if args.single:
            logger.info("Wykonywanie pojedynczego sprawdzenia systemu...")
            monitor.run_single_check()
            logger.info("Sprawdzenie systemu zakończone")
        else:
            logger.info(f"Uruchamianie monitorowania ciągłego co {interval} sekund...")
            monitor.run_monitor_loop()
    
    except KeyboardInterrupt:
        logger.info("Otrzymano sygnał przerwania, zatrzymywanie monitorowania...")
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania monitorowania: {e}")
        sys.exit(1)


def main():
    """Główna funkcja programu."""
    # Parsowanie argumentów wiersza poleceń
    parser = argparse.ArgumentParser(description="Uruchamia serwis monitorowania systemu")
    parser.add_argument("--env", choices=["dev", "test", "prod"], default="dev",
                        help="Środowisko (dev, test, prod)")
    parser.add_argument("--debug", action="store_true",
                        help="Uruchom w trybie debugowania")
    parser.add_argument("--interval", type=int,
                        help="Interwał sprawdzania w sekundach (nadpisuje konfigurację)")
    parser.add_argument("--single", action="store_true",
                        help="Wykonaj pojedyncze sprawdzenie i zakończ")
    parser.add_argument("--db-path",
                        help="Ścieżka do pliku bazy danych (nadpisuje konfigurację)")
    args = parser.parse_args()
    
    # Ładowanie konfiguracji
    config = load_config(args.env)
    
    # Uruchomienie serwisu
    run_monitoring_service(config, args)


if __name__ == "__main__":
    main() 
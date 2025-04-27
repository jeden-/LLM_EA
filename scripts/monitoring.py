#!/usr/bin/env python
"""
Moduł uruchamiający monitoring systemu.

Ten moduł jest interfejsem do pełnego modułu monitoringu monitor_system.py.
Zapewnia kompatybilność z modułem monitoringu zdefiniowanym w run_system.py.
"""

import os
import sys
import time
import argparse
import logging
import signal
from pathlib import Path
from threading import Event

# Dodanie katalogu głównego projektu do ścieżki, aby móc importować moduły
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Konfiguracja ścieżek
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, '..'))
LOG_DIR = os.path.join(PROJECT_DIR, 'logs')
CONFIG_DIR = os.path.join(PROJECT_DIR, 'config')

# Konfiguracja logowania
os.makedirs(os.path.join(LOG_DIR, "monitoring"), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(LOG_DIR, 'monitoring', 'monitoring.log'), mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Flaga zatrzymania
stop_event = Event()

def signal_handler(signum, frame):
    """Obsługa sygnałów systemowych."""
    logger.info(f"Otrzymano sygnał {signum}, zatrzymywanie...")
    stop_event.set()

def run_monitoring_loop(interval=60, debug=False, env="dev"):
    """
    Uruchamia monitoring w nieskończonej pętli
    
    Args:
        interval: Interwał sprawdzania w sekundach
        debug: Czy uruchomić w trybie debug
        env: Środowisko (dev, test, prod)
    """
    # Importuj funkcje monitorowania
    try:
        from scripts.monitor_system import (
            check_system_status, 
            COMPONENTS, 
            check_database_health,
            fix_database_issues
        )
    except ImportError as e:
        logger.error(f"Nie można zaimportować funkcji z monitor_system.py: {e}")
        return

    logger.info(f"Uruchomiono monitoring systemu (środowisko: {env}, interwał: {interval}s)")
    
    # Główna pętla monitorowania
    while not stop_event.is_set():
        try:
            # 1. Sprawdź status systemu
            logger.info("Sprawdzanie statusu systemu...")
            system_status = check_system_status(COMPONENTS)
            
            # 2. Sprawdź zdrowie bazy danych (co 10 iteracji)
            if hasattr(globals(), '_monitoring_counter'):
                globals()['_monitoring_counter'] += 1
            else:
                globals()['_monitoring_counter'] = 1
                
            if globals()['_monitoring_counter'] % 10 == 0:
                logger.info("Sprawdzanie zdrowia bazy danych...")
                db_status = check_database_health()
                
                if not db_status.get('ok', False):
                    logger.warning("Wykryto problemy z bazą danych!")
                    # Opcjonalnie możesz dodać automatyczne naprawianie
                    # fix_database_issues()
            
            # Czekaj przed następnym sprawdzeniem
            logger.debug(f"Oczekiwanie {interval} sekund do następnego sprawdzenia...")
            
            # Podziel oczekiwanie na krótsze odcinki, aby lepiej reagować na sygnały
            for _ in range(interval):
                if stop_event.is_set():
                    break
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Otrzymano przerwanie, zatrzymywanie...")
            stop_event.set()
        except Exception as e:
            logger.error(f"Błąd podczas monitorowania: {e}")
            # Czekaj trochę krócej przed ponowną próbą po błędzie
            time.sleep(10)

def main():
    """Główna funkcja monitoringu systemu."""
    # Rejestracja obsługi sygnałów
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    parser = argparse.ArgumentParser(description="Uruchamia monitoring systemu LLM Trader")
    parser.add_argument("--env", choices=["dev", "test", "prod"], default="dev",
                        help="Środowisko (dev, test, prod)")
    parser.add_argument("--debug", action="store_true",
                        help="Włącz tryb debugowania")
    parser.add_argument("--interval", type=int, default=60,
                        help="Interwał sprawdzania w sekundach (domyślnie 60)")
    args = parser.parse_args()
    
    # Ustaw poziom logowania
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Włączono tryb debugowania")
    
    logger.info(f"Uruchamianie modułu monitoringu w środowisku: {args.env}")
    
    try:
        # Uruchom monitoring w pętli
        run_monitoring_loop(
            interval=args.interval,
            debug=args.debug,
            env=args.env
        )
    except KeyboardInterrupt:
        logger.info("Otrzymano przerwanie, zatrzymywanie...")
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania monitoringu: {e}")
        sys.exit(1)
    
    logger.info("Monitoring zatrzymany")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do uruchamiania agenta łączącego system LLM z Expert Advisorem.
Umożliwia konfigurację parametrów połączenia oraz wybór symboli do analizy.
"""

import os
import sys
import argparse
import logging
import json
import time
from datetime import datetime

# Dodajemy główny katalog projektu do ścieżki
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import agenta
from Expert_Advisor.agent_connector import AgentConnector

def configure_logging(level_name: str, log_file: str = None):
    """
    Konfiguracja systemu logowania.
    
    Args:
        level_name: Poziom logowania (debug, info, warning, error, critical)
        log_file: Ścieżka do pliku z logami (opcjonalnie)
    """
    # Mapowanie nazw poziomów na stałe logging
    levels = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }
    level = levels.get(level_name.lower(), logging.INFO)
    
    # Podstawowa konfiguracja
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Logger główny
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Czyszczenie istniejących handlerów
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Handler dla konsoli
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler dla pliku (jeśli podano)
    if log_file:
        # Upewnij się, że katalog istnieje
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def parse_arguments():
    """
    Parsowanie argumentów linii poleceń.
    
    Returns:
        argparse.Namespace: Sparsowane argumenty
    """
    parser = argparse.ArgumentParser(description="Agent łączący system LLM z Expert Advisorem")
    
    # Parametry połączenia
    parser.add_argument("--host", type=str, default="localhost",
                        help="Adres hosta (domyślnie: localhost)")
    parser.add_argument("--req-port", type=int, default=5555,
                        help="Port dla komunikacji REQUEST/REPLY (domyślnie: 5555)")
    parser.add_argument("--pub-port", type=int, default=5556,
                        help="Port dla komunikacji PUBLISH/SUBSCRIBE (domyślnie: 5556)")
    
    # Parametry działania
    parser.add_argument("--interval", type=int, default=60,
                        help="Interwał aktualizacji w sekundach (domyślnie: 60)")
    parser.add_argument("--symbols", type=str, default="EURUSD",
                        help="Symbole do analizy, oddzielone przecinkami (domyślnie: EURUSD)")
    parser.add_argument("--debug", action="store_true",
                        help="Tryb debugowania (bez rzeczywistego handlu)")
    
    # Parametry logowania
    parser.add_argument("--log-level", type=str, default="info",
                        choices=["debug", "info", "warning", "error", "critical"],
                        help="Poziom logowania (domyślnie: info)")
    parser.add_argument("--log-file", type=str, 
                        default=f"logs/agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                        help="Ścieżka do pliku z logami (domyślnie: logs/agent_[data].log)")
    
    return parser.parse_args()

def main():
    """Główna funkcja programu."""
    # Parsowanie argumentów
    args = parse_arguments()
    
    # Konfiguracja logowania
    logger = configure_logging(args.log_level, args.log_file)
    logger.info(f"Uruchamianie agenta w trybie {'debugowania' if args.debug else 'produkcyjnym'}")
    
    # Lista symboli
    symbols = [s.strip() for s in args.symbols.split(",")]
    logger.info(f"Symbole do analizy: {', '.join(symbols)}")
    
    try:
        # Utworzenie i konfiguracja agenta
        agent = AgentConnector(
            server_address=args.host,
            req_port=args.req_port,
            pub_port=args.pub_port,
            update_interval=args.interval,
            debug_mode=args.debug
        )
        
        # Ustawienie aktywnych symboli
        agent.active_symbols = symbols
        
        # Uruchomienie agenta
        logger.info("Uruchamianie agenta...")
        agent.start()
        
    except KeyboardInterrupt:
        logger.info("Przerwano działanie agenta przez użytkownika")
    except Exception as e:
        logger.critical(f"Krytyczny błąd: {e}", exc_info=True)
    finally:
        # Wyświetlenie statystyk na koniec
        try:
            if 'agent' in locals() and agent:
                stats = agent.get_stats()
                logger.info("Statystyki działania agenta:")
                logger.info(json.dumps(stats, indent=2))
                agent.stop()
        except Exception as e:
            logger.error(f"Błąd podczas zamykania agenta: {e}")

if __name__ == "__main__":
    main() 
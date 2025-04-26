#!/usr/bin/env python
"""
Moduł uruchamiający Agent Manager jako usługę.

Odpowiada za inicjalizację i zarządzanie komponentami związanymi z
zarządzaniem strategiami handlowymi, agentami i zleceniami.
"""

import os
import sys
import time
import json
import signal
import logging
import argparse
from pathlib import Path
from threading import Event

# Konfiguracja ścieżek projektu
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_DIR)

from Agent_Manager.agent_manager import AgentManager
from Agent_Manager.strategy_manager import StrategyManager
from Agent_Manager.risk_manager import RiskManager
from Database.database import DatabaseHandler
from MT5_Connector.connector import MT5Connector
from LLM_Engine.llm_engine import LLMEngine

# Konfiguracja logowania
LOG_DIR = os.path.join(PROJECT_DIR, "logs", "agent_manager")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "agent_manager.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("agent_manager")

# Flaga zatrzymania
stop_event = Event()


def load_config(env="dev"):
    """
    Ładuje konfigurację z pliku.
    
    Args:
        env: Środowisko (dev, test, prod)
        
    Returns:
        Słownik z konfiguracją
    """
    config_path = os.path.join(PROJECT_DIR, "config", f"config_{env}.json")
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"Załadowano konfigurację z {config_path}")
                return config
        except Exception as e:
            logger.error(f"Błąd ładowania konfiguracji: {e}")
    
    logger.warning(f"Plik konfiguracyjny nie istnieje: {config_path}. Używanie konfiguracji domyślnej.")
    
    # Konfiguracja domyślna
    return {
        "database": {
            "path": os.path.join(PROJECT_DIR, "data", "trading.db")
        },
        "agent_manager": {
            "check_interval": 60,  # sekundy
            "max_agents": 5,
            "default_risk_level": "moderate"
        },
        "risk_manager": {
            "daily_risk_limit_pct": 2.0,
            "position_risk_limit_pct": 1.0,
            "max_open_positions": 5
        }
    }


def signal_handler(signum, frame):
    """
    Obsługuje sygnały systemowe.
    """
    logger.info(f"Otrzymano sygnał {signum}, zatrzymywanie...")
    stop_event.set()


def setup_manager(config, debug=False):
    """
    Inicjalizuje i konfiguruje Agent Manager.
    
    Args:
        config: Słownik z konfiguracją
        debug: Czy uruchomić w trybie debug
        
    Returns:
        Skonfigurowany AgentManager
    """
    # Inicjalizacja komponentów
    db_config = config.get("database", {})
    db_path = db_config.get("path", os.path.join(PROJECT_DIR, "data", "trading.db"))
    
    # Inicjalizacja bazy danych
    logger.info(f"Inicjalizacja bazy danych: {db_path}")
    db_handler = DatabaseHandler(db_path=db_path)
    
    # Inicjalizacja MT5 Connector
    logger.info("Inicjalizacja MT5 Connector")
    mt5_connector = MT5Connector(db_handler=db_handler)
    
    # Inicjalizacja LLM Engine
    logger.info("Inicjalizacja LLM Engine")
    llm_engine = LLMEngine(db_handler=db_handler)
    
    # Inicjalizacja Risk Manager
    risk_config = config.get("risk_manager", {})
    logger.info("Inicjalizacja Risk Manager")
    risk_manager = RiskManager()
    risk_manager.set_daily_risk_limit_pct(risk_config.get("daily_risk_limit_pct", 2.0))
    risk_manager.set_position_risk_limit_pct(risk_config.get("position_risk_limit_pct", 1.0))
    risk_manager.set_max_open_positions(risk_config.get("max_open_positions", 5))
    
    # Inicjalizacja Strategy Manager
    logger.info("Inicjalizacja Strategy Manager")
    strategy_manager = StrategyManager(db_handler=db_handler)
    
    # Inicjalizacja Agent Manager
    agent_config = config.get("agent_manager", {})
    logger.info("Inicjalizacja Agent Manager")
    agent_manager = AgentManager(
        db_handler=db_handler,
        order_processor=mt5_connector,
        market_analyzer=llm_engine,
        risk_manager=risk_manager,
        strategy_manager=strategy_manager
    )
    
    return agent_manager


def run_manager(config, debug=False):
    """
    Główna funkcja uruchamiająca Agent Manager.
    
    Args:
        config: Słownik z konfiguracją
        debug: Czy uruchomić w trybie debug
    """
    # Inicjalizacja Agent Manager
    agent_manager = setup_manager(config, debug)
    
    # Konfiguracja częstotliwości sprawdzania
    check_interval = config.get("agent_manager", {}).get("check_interval", 60)
    
    logger.info(f"Agent Manager uruchomiony. Sprawdzanie co {check_interval} sekund")
    
    # Główna pętla
    while not stop_event.is_set():
        try:
            # Sprawdź i wykonaj zadania
            logger.info("Wykonywanie cyklu zarządzania")
            
            # Aktualizacja informacji o koncie
            account_info = agent_manager.get_account_info()
            logger.info(f"Stan konta: {account_info.get('balance', 0)}")
            
            # Sprawdzenie otwartych pozycji
            open_positions = agent_manager.get_open_positions()
            logger.info(f"Liczba otwartych pozycji: {len(open_positions)}")
            
            # Sprawdzenie aktywnych strategii
            active_strategies = agent_manager.strategy_manager.get_active_strategies()
            logger.info(f"Liczba aktywnych strategii: {len(active_strategies)}")
            
            # Analiza rynku dla aktywnych strategii
            for strategy in active_strategies:
                try:
                    strategy_name = strategy.get("name", "Nieznana")
                    symbol = strategy.get("symbol", "EURUSD")
                    timeframe = strategy.get("timeframe", "H1")
                    
                    logger.info(f"Analiza rynku dla strategii: {strategy_name}, {symbol}, {timeframe}")
                    
                    # Pobierz dane rynkowe
                    market_data = agent_manager.get_market_data(symbol, timeframe, 100)
                    
                    # Analizuj rynek
                    analysis = agent_manager.analyze_market(
                        symbol=symbol,
                        timeframe=timeframe,
                        price_data=market_data,
                        strategy_name=strategy_name
                    )
                    
                    # Jeśli jest sygnał handlowy, przetwórz go
                    if analysis and "action" in analysis:
                        action = analysis["action"]
                        logger.info(f"Otrzymano sygnał: {action} dla {symbol}")
                        
                        if action in ["BUY", "SELL"]:
                            # Sprawdź zgodność z zarządzaniem ryzykiem
                            volume = agent_manager.risk_manager.calculate_position_size(
                                symbol=symbol,
                                risk_pct=1.0,  # 1% ryzyka na pozycję
                                stop_loss_pips=analysis.get("stop_loss_pips", 50)
                            )
                            
                            # Otwórz pozycję
                            result = agent_manager.open_position(
                                symbol=symbol,
                                order_type=action,
                                volume=volume,
                                stop_loss=analysis.get("stop_loss"),
                                take_profit=analysis.get("take_profit"),
                                comment=f"Strategy: {strategy_name}"
                            )
                            
                            logger.info(f"Wynik otwarcia pozycji: {result}")
                
                except Exception as e:
                    logger.error(f"Błąd podczas przetwarzania strategii {strategy.get('name', 'Nieznana')}: {e}")
            
            # Zarządzanie otwartymi pozycjami
            for position in open_positions:
                try:
                    position_id = position.get("ticket")
                    symbol = position.get("symbol")
                    
                    # Sprawdź, czy pozycja powinna być zamknięta lub zmodyfikowana
                    # Tu można dodać logikę zarządzania pozycjami
                except Exception as e:
                    logger.error(f"Błąd podczas zarządzania pozycją {position.get('ticket')}: {e}")
            
        except Exception as e:
            logger.error(f"Błąd w głównej pętli: {e}")
        
        # Sprawdź, czy należy zakończyć działanie
        if stop_event.is_set():
            break
        
        # Czekaj przed następnym cyklem
        time.sleep(check_interval)
    
    logger.info("Agent Manager zatrzymany")


def main():
    """Główna funkcja programu."""
    # Parsowanie argumentów wiersza poleceń
    parser = argparse.ArgumentParser(description="Uruchamia Agent Manager")
    parser.add_argument("--env", choices=["dev", "test", "prod"], default="dev",
                        help="Środowisko (dev, test, prod)")
    parser.add_argument("--debug", action="store_true",
                        help="Uruchom w trybie debugowania")
    args = parser.parse_args()
    
    # Konfiguracja poziomu logowania
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Tryb debugowania włączony")
    
    # Obsługa sygnałów
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Ładowanie konfiguracji
    config = load_config(args.env)
    
    try:
        # Uruchomienie Agent Manager
        run_manager(config, args.debug)
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania Agent Manager: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 
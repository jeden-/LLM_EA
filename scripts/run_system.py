#!/usr/bin/env python
"""
Główny skrypt uruchamiający wszystkie komponenty systemu handlowego.

Uruchamia poszczególne komponenty w odpowiedniej kolejności, 
zgodnie z ich zależnościami i monitoruje ich działanie.
"""

import os
import sys
import time
import json
import signal
import logging
import argparse
import subprocess
from pathlib import Path
from threading import Event, Thread
import platform

# Konfiguracja ścieżek
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_DIR, "config")
LOG_DIR = os.path.join(PROJECT_DIR, "logs")

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "system.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("system")

# Definicja komponentów i ich zależności
COMPONENTS = {
    "database": {
        "module": "Database.run_database",
        "dependencies": []
    },
    "mt5_connector": {
        "module": "MT5_Connector.run_connector",
        "dependencies": ["database"]
    },
    "llm_engine": {
        "module": "LLM_Engine.run_engine",
        "dependencies": ["database"]
    },
    "agent_manager": {
        "module": "Agent_Manager.run_manager",
        "dependencies": ["database", "mt5_connector", "llm_engine"]
    },
    "dashboard": {
        "module": "Dashboard.run_dashboard",
        "dependencies": ["database"]
    },
    "monitoring": {
        "module": "scripts.monitoring",
        "dependencies": []
    }
}

# Flaga zatrzymania systemu
stop_event = Event()
processes = {}


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
        "system": {
            "debug": True
        }
    }


def prepare_components():
    """Przygotowuje komponenty do uruchomienia."""
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Sprawdź czy istnieją katalogi dla logów
    for component in COMPONENTS:
        os.makedirs(os.path.join(LOG_DIR, component), exist_ok=True)
    
    logger.info("Katalogi logów przygotowane")


def start_component(component_name, env, debug):
    """
    Uruchamia pojedynczy komponent systemu.
    
    Args:
        component_name: Nazwa komponentu
        env: Środowisko (dev, test, prod)
        debug: Czy uruchomić w trybie debug
    
    Returns:
        Uruchomiony proces
    """
    if component_name not in COMPONENTS:
        logger.error(f"Nieznany komponent: {component_name}")
        return None
    
    # Przygotowanie ścieżki logu
    log_file = os.path.join(LOG_DIR, f"{component_name}.log")
    
    # Przygotowanie argumentów dla skryptu
    cmd = [sys.executable, "-m", COMPONENTS[component_name]["module"], 
           "--env", env]
    
    if debug:
        cmd.append("--debug")
    
    logger.info(f"Uruchamianie komponentu: {component_name} {' '.join(cmd)}")
    
    try:
        # Otwórz plik logu
        log_fd = open(log_file, "w")
        
        # Uruchom proces
        process = subprocess.Popen(
            cmd,
            stdout=log_fd,
            stderr=subprocess.STDOUT,
            cwd=PROJECT_DIR,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if platform.system() == 'Windows' else 0
        )
        
        logger.info(f"Uruchomiono komponent {component_name} (PID: {process.pid})")
        return process
    
    except Exception as e:
        logger.error(f"Błąd uruchamiania komponentu {component_name}: {e}")
        return None


def topological_sort():
    """
    Sortuje komponenty topologicznie zgodnie z ich zależnościami.
    
    Returns:
        Lista komponentów w kolejności uruchamiania
    """
    # Inicjalizacja
    visited = set()
    temp_mark = set()
    order = []
    
    def visit(node):
        if node in visited:
            return
        if node in temp_mark:
            logger.error(f"Wykryto cykliczną zależność zawierającą komponent {node}")
            return
        
        temp_mark.add(node)
        
        # Odwiedź wszystkie zależności
        for dependency in COMPONENTS[node]["dependencies"]:
            visit(dependency)
        
        temp_mark.remove(node)
        visited.add(node)
        order.append(node)
    
    # Odwiedź wszystkie komponenty
    for component in COMPONENTS:
        if component not in visited:
            visit(component)
    
    return order


def start_system(env, components, debug):
    """
    Uruchamia cały system handlowy.
    
    Args:
        env: Środowisko (dev, test, prod)
        components: Lista komponentów do uruchomienia
        debug: Czy uruchomić w trybie debug
    """
    logger.info(f"Uruchamianie systemu w środowisku: {env}")
    
    # Przygotuj komponenty
    prepare_components()
    
    # Określ kolejność uruchamiania
    if not components:
        components = list(COMPONENTS.keys())
    
    # Sortuj komponenty zgodnie z zależnościami
    component_order = topological_sort()
    
    # Uruchom tylko wybrane komponenty, zachowując kolejność zależności
    components_to_start = [c for c in component_order if c in components]
    
    logger.info(f"Komponenty zostaną uruchomione w kolejności: {components_to_start}")
    
    # Uruchom komponenty
    for component in components_to_start:
        if stop_event.is_set():
            logger.info("Przerwano uruchamianie systemu")
            break
        
        process = start_component(component, env, debug)
        if process:
            processes[component] = process
            # Odczekaj chwilę po uruchomieniu komponentu
            time.sleep(2)
    
    logger.info(f"Uruchomiono {len(processes)} z {len(components_to_start)} komponentów")


def stop_system():
    """Zatrzymuje wszystkie uruchomione komponenty systemu."""
    logger.info("Zatrzymywanie systemu...")
    
    for component, process in list(processes.items()):
        try:
            logger.info(f"Zatrzymywanie komponentu: {component} (PID: {process.pid})")
            
            if platform.system() == 'Windows':
                # Na Windowsie używamy funkcji terminate, bo nie ma SIGTERM
                process.terminate()
            else:
                # Na Linuxie i MacOS używamy SIGTERM
                os.kill(process.pid, signal.SIGTERM)
            
            # Poczekaj na zakończenie procesu (z timeout)
            try:
                process.wait(timeout=5)
                logger.info(f"Komponent {component} zatrzymany")
            except subprocess.TimeoutExpired:
                logger.warning(f"Komponent {component} nie zatrzymał się, wymuszanie zamknięcia")
                process.kill()
            
            del processes[component]
        
        except Exception as e:
            logger.error(f"Błąd zatrzymywania komponentu {component}: {e}")
    
    logger.info("System zatrzymany")


def monitor_processes():
    """Monitoruje uruchomione procesy i restartuje je w razie potrzeby."""
    logger.info("Uruchomiono monitoring procesów")
    
    while not stop_event.is_set():
        for component, process in list(processes.items()):
            # Sprawdź czy proces nadal działa
            if process.poll() is not None:
                exit_code = process.returncode
                logger.warning(f"Proces {component} zakończył działanie (kod: {exit_code})")
                
                # Usuń proces z listy
                del processes[component]
                
                if not stop_event.is_set():
                    # Uruchom ponownie proces
                    logger.info(f"Restartowanie komponentu: {component}")
                    new_process = start_component(component, "dev", True)  # TODO: Parametryzuj
                    if new_process:
                        processes[component] = new_process
        
        # Poczekaj przed następnym sprawdzeniem
        time.sleep(5)


def signal_handler(signum, frame):
    """Obsługuje sygnały systemowe do zatrzymania systemu."""
    logger.info(f"Otrzymano sygnał {signum}, zatrzymywanie systemu...")
    stop_event.set()


def main():
    """Główna funkcja programu."""
    # Parsowanie argumentów wiersza poleceń
    parser = argparse.ArgumentParser(description="Uruchamia system handlowy LLM-MT5")
    parser.add_argument("--env", choices=["dev", "test", "prod"], default="dev",
                      help="Środowisko (dev, test, prod)")
    parser.add_argument("--debug", action="store_true",
                      help="Uruchom komponenty w trybie debugowania")
    parser.add_argument("--components", nargs="+", choices=list(COMPONENTS.keys()),
                      help="Lista komponentów do uruchomienia (domyślnie wszystkie)")
    args = parser.parse_args()
    
    # Rejestracja obsługi sygnałów
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Ładowanie konfiguracji
    config = load_config(args.env)
    
    try:
        # Sprawdź środowisko
        if args.env == "prod" and not args.debug:
            logger.warning("Uruchamianie w środowisku produkcyjnym bez debugowania")
        
        # Uruchom system
        start_system(args.env, args.components, args.debug)
        
        # Uruchom wątek monitorujący
        monitor_thread = Thread(target=monitor_processes, daemon=True)
        monitor_thread.start()
        
        # Czekaj aż otrzymamy sygnał zatrzymania
        while not stop_event.is_set():
            time.sleep(1)
        
        # Zatrzymaj system
        stop_system()
    
    except KeyboardInterrupt:
        logger.info("Otrzymano przerwanie, zatrzymywanie systemu...")
        stop_event.set()
        stop_system()
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania systemu: {e}")
        stop_event.set()
        stop_system()
        sys.exit(1)


if __name__ == "__main__":
    main() 
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
running_processes = {}

# Klasa reprezentująca komponent systemu
class SystemComponent:
    """Klasa reprezentująca pojedynczy komponent systemu."""
    
    def __init__(self, name, command, required=True, depends_on=None, startup_time=5, check_alive=None):
        """
        Inicjalizuje komponent systemu.
        
        Args:
            name: Nazwa komponentu
            command: Lista poleceń do uruchomienia
            required: Czy komponent jest wymagany
            depends_on: Lista nazw komponentów od których zależy
            startup_time: Czas oczekiwania na uruchomienie w sekundach
            check_alive: Funkcja sprawdzająca czy komponent działa
        """
        self.name = name
        self.command = command
        self.required = required
        self.depends_on = depends_on or []
        self.startup_time = startup_time
        self.check_alive = check_alive
        self.process = None
        self.exit_code = None
        self.log_file = None
        
    def is_alive(self):
        """Sprawdza czy proces jest uruchomiony."""
        if self.process is None:
            return False
        
        # Sprawdź czy proces działa
        return self.process.poll() is None

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
    
    # Zwracamy pustą konfigurację dla testu
    return {}


def prepare_components(config, args):
    """
    Przygotowuje komponenty do uruchomienia na podstawie konfiguracji.
    
    Args:
        config: Konfiguracja systemu
        args: Argumenty wiersza poleceń
        
    Returns:
        Słownik z komponentami
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Sprawdź czy istnieją katalogi dla logów
    for component in COMPONENTS:
        os.makedirs(os.path.join(LOG_DIR, component), exist_ok=True)
    
    logger.info("Katalogi logów przygotowane")
    
    # Przygotowanie komponentów na podstawie konfiguracji
    components = {}
    
    # Dodaj wszystkie wymagane komponenty
    for name, component_config in COMPONENTS.items():
        # Pomiń dashboard jeśli ustawiono flagę --no-dashboard
        if name == 'dashboard' and args.no_dashboard:
            continue
            
        command = [sys.executable, "-m", component_config["module"], 
                  "--env", args.env]
        
        if args.debug:
            command.append("--debug")
        
        component = SystemComponent(
            name=name,
            command=command,
            required=True,  # Wszystkie komponenty są domyślnie wymagane
            depends_on=component_config["dependencies"],
            startup_time=5  # Domyślny czas uruchomienia
        )
        
        components[name] = component
    
    return components


def start_component(component, log_dir):
    """
    Uruchamia pojedynczy komponent systemu.
    
    Args:
        component: Obiekt komponentu SystemComponent
        log_dir: Katalog na logi
    
    Returns:
        bool: True jeśli komponent został uruchomiony pomyślnie
    """
    if not isinstance(component, SystemComponent):
        logger.error(f"Nieprawidłowy typ komponentu: {type(component)}")
        return False
    
    # Przygotowanie ścieżki logu
    log_file_path = os.path.join(log_dir, f"{component.name}.log")
    
    logger.info(f"Uruchamianie komponentu: {component.name}")
    
    try:
        # Otwórz plik logu
        log_fd = open(log_file_path, "w")
        component.log_file = log_fd
        
        # Uruchom proces
        process = subprocess.Popen(
            component.command,
            stdout=log_fd,
            stderr=subprocess.STDOUT,
            cwd=PROJECT_DIR,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if platform.system() == 'Windows' else 0
        )
        
        # Ustaw proces w komponencie
        component.process = process
        
        logger.info(f"Uruchomiono komponent {component.name} (PID: {process.pid})")
        
        # Poczekaj na uruchomienie
        time.sleep(component.startup_time)
        
        # Sprawdź czy proces nadal działa
        if process.poll() is not None:
            component.exit_code = process.returncode
            logger.error(f"Komponent {component.name} zakończył działanie z kodem {process.returncode}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Błąd uruchamiania komponentu {component.name}: {e}")
        return False


def topological_sort(components):
    """
    Sortuje komponenty topologicznie zgodnie z ich zależnościami.
    
    Args:
        components: Słownik komponentów {nazwa: obiekt SystemComponent}
        
    Returns:
        Lista nazw komponentów w kolejności uruchamiania
    """
    # Inicjalizacja
    visited = set()
    temp_mark = set()
    order = []
    
    def visit(name):
        # Jeśli komponent już odwiedzony, pomiń
        if name in visited:
            return
        
        # Wykryj cykle
        if name in temp_mark:
            logger.error(f"Wykryto cykliczną zależność zawierającą komponent {name}")
            raise ValueError(f"Wykryto cykliczną zależność zawierającą komponent {name}")
        
        # Oznacz jako tymczasowo odwiedzony
        temp_mark.add(name)
        
        # Odwiedź wszystkie zależności
        if name in components:
            component = components[name]
            for dependency in component.depends_on:
                visit(dependency)
        
        # Oznacz jako odwiedzony i dodaj do wyniku
        temp_mark.remove(name)
        visited.add(name)
        order.append(name)
    
    # Odwiedź wszystkie komponenty
    for name in components:
        if name not in visited:
            visit(name)
    
    return order


def start_system(components, log_dir=LOG_DIR):
    """
    Uruchamia cały system handlowy.
    
    Args:
        components: Słownik komponentów {nazwa: obiekt SystemComponent}
        log_dir: Katalog na logi
        
    Returns:
        bool: True jeśli system został uruchomiony pomyślnie
    """
    logger.info("Uruchamianie systemu...")
    
    # Utwórz katalogi logów
    os.makedirs(log_dir, exist_ok=True)
    
    # Posortuj komponenty
    sorted_components = topological_sort(components)
    
    # Uruchom komponenty w odpowiedniej kolejności
    for component_name in sorted_components:
        if component_name not in components:
            logger.warning(f"Brak komponentu {component_name} do uruchomienia")
            continue
            
        # Sprawdź czy komponent jest już uruchomiony
        if component_name in running_processes:
            component = components[component_name]
            component.process = running_processes[component_name]
            logger.info(f"Komponent {component_name} jest już uruchomiony")
            continue
            
        component = components[component_name]
        logger.info(f"Uruchamianie komponentu {component_name}...")
        
        # Sprawdź czy wszystkie zależności są uruchomione
        all_deps_running = True
        for dep_name in component.depends_on:
            # Sprawdź czy zależność istnieje
            if dep_name not in components:
                logger.error(f"Brak zależności {dep_name} dla {component_name}")
                all_deps_running = False
                break
            
            # Sprawdź czy zależność jest uruchomiona
            dep_component = components[dep_name]
            if dep_name not in running_processes and not dep_component.process:
                logger.error(f"Zależność {dep_name} nie jest uruchomiona dla {component_name}")
                all_deps_running = False
                break
                
        if not all_deps_running:
            logger.error(f"Nie można uruchomić {component_name} - brak zależności")
            if component.required:
                logger.error(f"Komponent {component_name} jest wymagany - przerwanie uruchamiania systemu")
                return False
            continue
        
        # Uruchom komponent
        success = start_component(component, log_dir)
        if success:
            running_processes[component_name] = component.process
        else:
            logger.error(f"Nie udało się uruchomić komponentu {component_name}")
            if component.required:
                logger.error(f"Komponent {component_name} jest wymagany - przerwanie uruchamiania systemu")
                return False
    
    # Weryfikacja czy wszystkie wymagane komponenty zostały uruchomione
    for component_name, component in components.items():
        if component.required:
            if component_name not in running_processes and not component.process:
                logger.error(f"Wymagany komponent {component_name} nie jest uruchomiony")
                return False
    
    logger.info("System został uruchomiony pomyślnie")
    return True


def stop_system():
    """
    Zatrzymuje wszystkie uruchomione komponenty systemu.
    
    Returns:
        bool: True jeśli wszystkie komponenty zostały zatrzymane
    """
    logger.info("Zatrzymywanie systemu...")
    
    success = True
    for component_name, component in list(running_processes.items()):
        try:
            if component.is_alive():
                logger.info(f"Zatrzymywanie komponentu: {component_name} (PID: {component.process.pid})")
                
                # Wysłanie sygnału zakończenia
                if platform.system() == 'Windows':
                    # W Windows wysyłamy CTRL+C do grupy procesów
                    os.kill(component.process.pid, signal.CTRL_C_EVENT)
                else:
                    # W Linux/Mac wysyłamy SIGTERM
                    os.kill(component.process.pid, signal.SIGTERM)
                
                # Dajemy czas na zakończenie
                for _ in range(5):
                    if not component.is_alive():
                        break
                    time.sleep(1)
                
                # Jeśli proces nadal działa, wymuszamy zakończenie
                if component.is_alive():
                    logger.warning(f"Wymuszanie zakończenia komponentu: {component_name}")
                    component.process.kill()
                
                # Zamknięcie pliku logu
                if component.log_file:
                    component.log_file.close()
                
                del running_processes[component_name]
            
        except Exception as e:
            logger.error(f"Błąd podczas zatrzymywania komponentu {component_name}: {e}")
            success = False
    
    return success


def monitor_processes():
    """
    Monitoruje uruchomione procesy i restartuje upadłe.
    
    Uruchamiany jako osobny wątek.
    """
    logger.info("Uruchomiono monitorowanie procesów")
    
    try:
        while not stop_event.is_set():
            for component_name, component in list(running_processes.items()):
                # Sprawdź czy proces nadal działa
                current_status = component.poll()
                if current_status is not None:
                    # Pobierz kod wyjścia
                    exit_code = component.returncode
                    
                    logger.warning(f"Komponent {component_name} zakończył działanie z kodem {exit_code}")
                    
                    # Usuń proces z listy
                    del running_processes[component_name]
                    
                    if not stop_event.is_set():
                        # Sprawdź czy komponent jest wymagany
                        if hasattr(component, 'required') and component.required:
                            # Uruchom ponownie proces
                            logger.info(f"Restartowanie komponentu: {component_name}")
                            success = start_component(component, LOG_DIR)
                            if success:
                                running_processes[component_name] = component.process
                            else:
                                logger.error(f"Nie udało się zrestartować komponentu {component_name}")
                        else:
                            logger.info(f"Komponent {component_name} nie jest wymagany - nie restartuję")
            
            # Poczekaj przed następnym sprawdzeniem
            time.sleep(5)
            
    except Exception as e:
        logger.error(f"Błąd w monitorowaniu procesów: {e}")
    
    logger.info("Zakończono monitorowanie procesów")


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
        start_system(COMPONENTS)
        
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
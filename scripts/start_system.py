#!/usr/bin/env python
"""
Skrypt do uruchamiania wszystkich komponentów systemu LLM Trader MT5.

Ten skrypt uruchamia jednocześnie agenta handlowego i dashboard,
zarządzając procesami w tle i zapewniając poprawne zamknięcie
wszystkich komponentów przy zakończeniu.
"""

import os
import sys
import signal
import argparse
import logging
import subprocess
import time
from pathlib import Path
from threading import Thread
from datetime import datetime
import atexit

# Dodaj główny katalog projektu do ścieżki, aby umożliwić importy
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("start_system")

# Lista aktywnych procesów
processes = []

def signal_handler(sig, frame):
    """Obsługa sygnałów zakończenia (Ctrl+C)."""
    logger.info("Otrzymano sygnał zakończenia. Zamykanie systemu...")
    stop_all_processes()
    sys.exit(0)

def stop_all_processes():
    """Zatrzymuje wszystkie uruchomione procesy."""
    for proc in processes:
        if proc.poll() is None:  # Jeśli proces nadal działa
            logger.info(f"Zamykanie procesu {proc.args}")
            try:
                proc.terminate()
                proc.wait(timeout=5)  # Daj procesowi 5 sekund na zamknięcie
            except subprocess.TimeoutExpired:
                logger.warning(f"Proces {proc.args} nie odpowiada, wymuszenie zakończenia")
                proc.kill()
            except Exception as e:
                logger.error(f"Błąd podczas zamykania procesu {proc.args}: {e}")

def launch_process(command, name, log_file=None):
    """Uruchamia nowy proces z przekierowaniem wyjścia do pliku."""
    # Przygotuj log_file jeśli podano
    if log_file:
        log_path = Path("logs")
        log_path.mkdir(exist_ok=True)
        
        log_file_path = log_path / log_file
        log_file_handle = open(log_file_path, 'a')
        
        # Zapisz nagłówek uruchomienia
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file_handle.write(f"\n{'='*50}\n")
        log_file_handle.write(f"Uruchomienie {name} o {timestamp}\n")
        log_file_handle.write(f"Komenda: {' '.join(command)}\n")
        log_file_handle.write(f"{'='*50}\n\n")
        log_file_handle.flush()
        
        stdout = log_file_handle
        stderr = subprocess.STDOUT
    else:
        stdout = sys.stdout
        stderr = sys.stderr
        log_file_handle = None
    
    # Uruchom proces
    try:
        logger.info(f"Uruchamianie {name}: {' '.join(command)}")
        process = subprocess.Popen(
            command,
            stdout=stdout,
            stderr=stderr,
            universal_newlines=True,
            bufsize=1  # Line buffered
        )
        processes.append(process)
        
        # Zapisz informacje do logu
        logger.info(f"Proces {name} uruchomiony, PID: {process.pid}")
        return process
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania {name}: {e}")
        if log_file_handle:
            log_file_handle.close()
        return None

def start_dashboard(port=5000, debug=False):
    """Uruchamia dashboard Flask."""
    python_executable = sys.executable
    command = [
        python_executable,
        "-m", "Dashboard.run_dashboard",
        "--port", str(port),
    ]
    
    if debug:
        command.append("--debug")
    
    return launch_process(command, "Dashboard", "dashboard.log")

def start_agent():
    """Uruchamia agenta handlowego."""
    python_executable = sys.executable
    command = [
        python_executable,
        "-m", "scripts.run_agent"
    ]
    return launch_process(command, "Agent handlowy", "agent.log")

def monitor_processes():
    """Monitoruje uruchomione procesy i restartuje je w razie potrzeby."""
    while True:
        for i, proc in enumerate(processes[:]):
            if proc.poll() is not None:  # Proces się zakończył
                logger.warning(f"Proces {proc.args} zakończył się z kodem {proc.returncode}")
                
                # Usuń zakończony proces z listy
                processes.remove(proc)
                
                # Określ typ procesu na podstawie argumentów
                if "run_dashboard" in " ".join(proc.args):
                    logger.info("Ponowne uruchamianie dashboardu...")
                    start_dashboard()
                elif "run_agent" in " ".join(proc.args):
                    logger.info("Ponowne uruchamianie agenta handlowego...")
                    start_agent()
        
        time.sleep(5)  # Sprawdzaj co 5 sekund

def main():
    """Główna funkcja skryptu."""
    parser = argparse.ArgumentParser(description="Uruchamianie systemu LLM Trader MT5")
    parser.add_argument("--dashboard-only", action="store_true", help="Uruchom tylko dashboard")
    parser.add_argument("--agent-only", action="store_true", help="Uruchom tylko agenta handlowego")
    parser.add_argument("--port", type=int, default=5000, help="Port dla dashboardu (domyślnie: 5000)")
    parser.add_argument("--debug", action="store_true", help="Uruchom w trybie debugowania")
    args = parser.parse_args()
    
    # Załaduj zmienne środowiskowe
    load_dotenv()
    
    # Zarejestruj obsługę sygnałów
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Zarejestruj funkcję zamykającą procesy przy wyjściu
    atexit.register(stop_all_processes)
    
    # Uruchom tylko określone komponenty lub wszystkie
    if args.dashboard_only:
        start_dashboard(port=args.port, debug=args.debug)
    elif args.agent_only:
        start_agent()
    else:
        # Uruchom wszystkie komponenty
        start_dashboard(port=args.port, debug=args.debug)
        start_agent()
    
    # Monitoruj procesy w osobnym wątku
    monitor_thread = Thread(target=monitor_processes, daemon=True)
    monitor_thread.start()
    
    try:
        # Utrzymuj główny wątek aktywnym
        logger.info("System LLM Trader uruchomiony. Naciśnij Ctrl+C, aby zakończyć.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Otrzymano przerwanie klawiatury. Kończenie pracy...")
    finally:
        stop_all_processes()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
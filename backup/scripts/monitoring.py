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
import time
import socket
import logging
import argparse
import datetime
import psutil
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional

# Dodaj główny katalog projektu do ścieżki importu
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importy z projektu
try:
    from Database.database import DatabaseHandler
except ImportError:
    print("Nie można zaimportować modułu DatabaseHandler. Upewnij się, że jesteś w katalogu głównym projektu.")

# Konfiguracja ścieżek
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_DIR, "config")
LOG_DIR = os.path.join(PROJECT_DIR, "logs")
project_dir = PROJECT_DIR  # Dla kompatybilności z testami

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


class SystemMonitor:
    """
    Klasa do monitorowania stanu całego systemu LLM Trader.
    
    Odpowiada za:
    1. Monitorowanie zasobów systemowych (CPU, RAM, dysk)
    2. Sprawdzanie połączeń sieciowych
    3. Weryfikację stanu bazy danych
    4. Monitorowanie uruchomionych procesów
    5. Wykrywanie anomalii
    """
    
    def __init__(self, interval: int = 300, db_path: Optional[str] = None):
        """
        Inicjalizuje monitor systemu.
        
        Args:
            interval: Częstotliwość sprawdzania w sekundach
            db_path: Ścieżka do pliku bazy danych (opcjonalnie)
        """
        self.interval = interval
        self.db_path = db_path
        self.start_time = datetime.datetime.now()
        self.monitor_dir = os.path.join(project_dir, "data", "monitoring")
        os.makedirs(self.monitor_dir, exist_ok=True)
        
        # Inicjalizacja bazy danych
        try:
            self.db = DatabaseHandler(db_path=db_path)
        except Exception as e:
            logger.warning(f"Nie można połączyć z bazą danych: {e}")
            self.db = None
        
        # Inicjalizacja metryk
        self.metrics = {
            "start_time": self.start_time.isoformat(),
            "uptime_seconds": 0,
            "checks_performed": 0,
            "api_errors": 0,
            "db_errors": 0,
            "mt5_connection_errors": 0
        }
    
    def check_system_resources(self) -> Dict[str, Any]:
        """
        Sprawdza zasoby systemowe (CPU, RAM, dysk).
        
        Returns:
            Dict: Informacje o stanie zasobów
        """
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu": {
                "usage_percent": cpu_percent,
                "cores": cpu_count,
                "load_per_core": cpu_percent / cpu_count if cpu_count else 0
            },
            "memory": {
                "total_mb": memory.total / (1024 * 1024),
                "used_mb": memory.used / (1024 * 1024),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": disk.total / (1024 * 1024 * 1024),
                "used_gb": disk.used / (1024 * 1024 * 1024),
                "percent": disk.percent
            }
        }
    
    def check_network_connectivity(self) -> Dict[str, Any]:
        """
        Sprawdza połączenia sieciowe.
        
        Returns:
            Dict: Informacje o stanie połączeń
        """
        results = {}
        
        # Sprawdzenie połączenia z API X.AI (Grok)
        xai_url = "https://api.x.ai/v1/health"
        try:
            start_time = time.time()
            response = requests.get(xai_url, timeout=10)
            latency = (time.time() - start_time) * 1000  # ms
            
            results["X.AI API"] = {
                "status": response.status_code,
                "ok": response.status_code == 200,
                "latency_ms": round(latency, 2)
            }
        except Exception as e:
            results["X.AI API"] = {
                "status": "Error",
                "ok": False,
                "error": str(e)
            }
            self.metrics["api_errors"] += 1
        
        # Sprawdzenie połączenia z Google
        google_url = "https://www.google.com"
        try:
            start_time = time.time()
            response = requests.get(google_url, timeout=5)
            latency = (time.time() - start_time) * 1000  # ms
            
            results["Google"] = {
                "status": response.status_code,
                "ok": response.status_code == 200,
                "latency_ms": round(latency, 2)
            }
        except Exception as e:
            results["Google"] = {
                "status": "Error",
                "ok": False,
                "error": str(e)
            }
        
        # Sprawdzenie połączenia z GitHub
        github_url = "https://github.com"
        try:
            start_time = time.time()
            response = requests.get(github_url, timeout=5)
            latency = (time.time() - start_time) * 1000  # ms
            
            results["GitHub"] = {
                "status": response.status_code,
                "ok": response.status_code == 200,
                "latency_ms": round(latency, 2)
            }
        except Exception as e:
            results["GitHub"] = {
                "status": "Error",
                "ok": False,
                "error": str(e)
            }
        
        # Sprawdzenie połączenia z MT5
        mt5_server = os.getenv("MT5_SERVER", "")
        if mt5_server:
            try:
                # Sprawdzenie czy port 443 jest otwarty
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((mt5_server, 443))
                sock.close()
                
                results["MT5 Server"] = {
                    "status": "Open" if result == 0 else "Closed",
                    "ok": result == 0,
                    "port": 443
                }
                
                if result != 0:
                    self.metrics["mt5_connection_errors"] += 1
            except Exception as e:
                results["MT5 Server"] = {
                    "status": "Error",
                    "ok": False,
                    "error": str(e)
                }
                self.metrics["mt5_connection_errors"] += 1
        
        return results
    
    def check_database_status(self) -> Dict[str, Any]:
        """
        Sprawdza stan bazy danych.
        
        Returns:
            Dict: Informacje o stanie bazy danych
        """
        result = {
            "status": "Unknown",
            "ok": False,
            "tables": [],
            "row_counts": {}
        }
        
        # Sprawdzanie czy plik bazy danych istnieje (pomijamy dla bazy :memory:)
        if self.db_path and self.db_path != ":memory:" and os.path.exists(self.db_path):
            result["db_exists"] = True
            result["db_size_mb"] = os.path.getsize(self.db_path) / (1024 * 1024)
        elif self.db_path == ":memory:":
            result["db_exists"] = True
            result["db_size_mb"] = 0  # Baza w pamięci nie ma rozmiaru dyskowego
        else:
            result["db_exists"] = False
        
        # Sprawdzanie połączenia z bazą danych
        if self.db:
            if self.db.connect():
                result["status"] = "Connected"
                result["ok"] = True
                
                # Sprawdzanie struktury bazy danych
                try:
                    # Pobieranie listy tabel
                    if hasattr(self.db, 'connection'):
                        cursor = self.db.connection.cursor()
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                        tables = [row[0] for row in cursor.fetchall()]
                        result["tables"] = tables
                        
                        # Pobieranie liczby wierszy w każdej tabeli
                        for table in tables:
                            cursor.execute(f"SELECT COUNT(*) FROM {table};")
                            count = cursor.fetchone()[0]
                            result["row_counts"][table] = count
                except Exception as e:
                    result["schema_error"] = str(e)
            else:
                result["status"] = "Error"
                result["ok"] = False
                self.metrics["db_errors"] += 1
        
        # Dodanie statystyk z bazy danych
        if self.db and result["ok"]:
            try:
                stats = self.db.get_statistics()
                result["statistics"] = stats
            except:
                result["statistics"] = "Error getting statistics"
        
        return result
    
    def check_system_processes(self) -> Dict[str, Any]:
        """
        Sprawdza uruchomione procesy systemu.
        
        Returns:
            Dict: Informacje o procesach
        """
        result = {
            "agent_running": False,
            "dashboard_running": False,
            "mt5_running": False,
            "system_processes": []
        }
        
        # Sprawdzenie procesów Python
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                process_info = proc.info
                
                if process_info['name'] in ('python', 'python3', 'python.exe') and process_info['cmdline']:
                    cmdline = ' '.join(process_info['cmdline'])
                    
                    # Dodanie informacji o procesie
                    process_data = {
                        'pid': process_info['pid'],
                        'name': process_info['name'],
                        'cmdline': cmdline,
                        'cpu_percent': proc.cpu_percent(),
                        'memory_percent': proc.memory_percent()
                    }
                    
                    result["system_processes"].append(process_data)
                    
                    # Sprawdzenie czy to agent
                    if 'run_agent' in cmdline:
                        result["agent_running"] = True
                    
                    # Sprawdzenie czy to dashboard
                    if 'run_dashboard' in cmdline:
                        result["dashboard_running"] = True
            except:
                pass
        
        # Sprawdzenie procesu MT5
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                process_info = proc.info
                if process_info['name'] in ('terminal64.exe', 'metatrader.exe', 'mt5.exe'):
                    result["mt5_running"] = True
                    break
            except:
                pass
        
        return result
    
    def run_single_check(self) -> Dict[str, Any]:
        """
        Wykonuje pojedyncze sprawdzenie systemu.
        
        Returns:
            Dict: Wyniki wszystkich sprawdzeń
        """
        check_time = datetime.datetime.now()
        results = {
            "timestamp": check_time.isoformat(),
            "system_resources": self.check_system_resources(),
            "network_connectivity": self.check_network_connectivity(),
            "database_status": self.check_database_status(),
            "system_processes": self.check_system_processes()
        }
        
        # Aktualizacja metryk
        self.metrics["uptime_seconds"] = (check_time - self.start_time).total_seconds()
        self.metrics["checks_performed"] += 1
        results["metrics"] = self.metrics
        
        # Zapisanie wyników do pliku
        self.save_results(results)
        
        return results
    
    def save_results(self, results: Dict[str, Any]) -> bool:
        """
        Zapisuje wyniki sprawdzenia do pliku.
        
        Args:
            results: Wyniki sprawdzenia
            
        Returns:
            bool: True jeśli zapis się powiódł, False w przeciwnym wypadku
        """
        try:
            # Zapisanie wyników w folderze monitoringu
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"system_check_{timestamp}.json"
            filepath = os.path.join(self.monitor_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=4, ensure_ascii=False)
            
            # Zapisanie najnowszych wyników jako current
            current_filepath = os.path.join(self.monitor_dir, "current_status.json")
            with open(current_filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=4, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania wyników: {e}")
            return False
    
    def save_metrics(self) -> bool:
        """
        Zapisuje metryki do pliku.
        
        Returns:
            bool: True jeśli zapis się powiódł, False w przeciwnym wypadku
        """
        try:
            metrics_file = os.path.join(self.monitor_dir, "metrics.json")
            with open(metrics_file, 'w', encoding='utf-8') as f:
                json.dump(self.metrics, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania metryk: {e}")
            return False
    
    def run_monitor_loop(self) -> None:
        """
        Uruchamia pętlę monitorowania.
        """
        try:
            while True:
                logger.info(f"Wykonywanie sprawdzenia systemu (próba {self.metrics['checks_performed'] + 1})...")
                self.run_single_check()
                logger.info(f"Sprawdzenie zakończone. Następne za {self.interval} sekund.")
                time.sleep(self.interval)
        except KeyboardInterrupt:
            logger.info("Otrzymano sygnał przerwania, zatrzymywanie monitorowania...")
        except Exception as e:
            logger.error(f"Błąd podczas pętli monitorowania: {e}")
            raise


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
    db_path = args.db_path
    if not db_path and "url" in db_config:
        db_url = db_config.get("url")
        if db_url.startswith("sqlite:///"):
            db_path = db_url.replace("sqlite:///", "")
    
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
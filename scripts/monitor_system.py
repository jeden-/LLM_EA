#!/usr/bin/env python
"""
Skrypt do monitorowania i zarządzania systemem LLM Trader MT5.

Ten skrypt umożliwia:
1. Monitorowanie stanu wszystkich komponentów systemu
2. Automatyczne restartowanie upadłych procesów
3. Zbieranie i analizę statystyk systemu
4. Diagnostykę i naprawę problemów bazy danych
5. Powiadamianie o problemach
"""

import os
import sys
import time
import json
import logging
import argparse
import subprocess
import platform
import datetime
import signal
import threading
import psutil
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

# Dodanie katalogu głównego projektu do ścieżki, aby móc importować moduły
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from Database.database import DatabaseHandler
except ImportError:
    print("Nie można zaimportować modułu DatabaseHandler. Upewnij się, że jesteś w katalogu głównym projektu.")
    sys.exit(1)

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join('logs', 'monitoring', 'monitor_system.log'), mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Konfiguracja ścieżek
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, '..'))
DATA_DIR = os.path.join(PROJECT_DIR, 'data')
LOG_DIR = os.path.join(PROJECT_DIR, 'logs')
CONFIG_DIR = os.path.join(PROJECT_DIR, 'config')

# Komponenty systemu
COMPONENTS = {
    "database": {
        "script": "Database/run_database.py",
        "required": True,
        "restart_attempts": 3,
        "restart_cooldown": 30,  # sekundy
    },
    "llm_engine": {
        "script": "LLM_Engine/run_engine.py",
        "required": True,
        "restart_attempts": 3,
        "restart_cooldown": 60,  # sekundy
    },
    "mt5_connector": {
        "script": "MT5_Connector/run_connector.py",
        "required": True,
        "restart_attempts": 3,
        "restart_cooldown": 30,  # sekundy
    },
    "agent_manager": {
        "script": "Agent_Manager/run_manager.py",
        "required": True,
        "restart_attempts": 3,
        "restart_cooldown": 30,  # sekundy
    },
    "dashboard": {
        "script": "Dashboard/run_dashboard.py",
        "required": False,
        "restart_attempts": 2,
        "restart_cooldown": 60,  # sekundy
    }
}

# Konfiguracja monitorowania bazy danych
DB_MONITORING = {
    "check_interval": 3600,  # co ile sekund sprawdzać bazę danych (domyślnie co godzinę)
    "auto_fix": False,       # czy automatycznie naprawiać wykryte problemy
    "notify_on_issues": True # czy powiadamiać o wykrytych problemach
}

# Konfiguracja powiadomień email
EMAIL_CONFIG = {
    "enabled": False,
    "smtp_server": "smtp.example.com",
    "smtp_port": 587,
    "username": "",
    "password": "",
    "from_email": "",
    "to_email": "",
    "use_tls": True
}

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Wczytywanie konfiguracji z pliku JSON.
    
    Args:
        config_path: Ścieżka do pliku konfiguracyjnego
        
    Returns:
        Dict: Słownik z konfiguracją
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Błąd podczas wczytywania konfiguracji: {e}")
        return {}

def save_config(config: Dict[str, Any], config_path: str) -> bool:
    """
    Zapisywanie konfiguracji do pliku JSON.
    
    Args:
        config: Słownik z konfiguracją
        config_path: Ścieżka do pliku konfiguracyjnego
        
    Returns:
        bool: True jeśli zapis się powiódł, False w przeciwnym wypadku
    """
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Błąd podczas zapisywania konfiguracji: {e}")
        return False

def get_process_info(process_name: str) -> List[Dict[str, Any]]:
    """
    Pobieranie informacji o procesach o podanej nazwie.
    
    Args:
        process_name: Nazwa procesu do znalezienia
        
    Returns:
        List: Lista słowników z informacjami o procesach
    """
    processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status', 'cpu_percent', 'memory_info']):
        try:
            # Jeśli nazwa procesu zawiera szukaną nazwę
            if process_name.lower() in ' '.join(proc.info['cmdline']).lower():
                mem_info = proc.info['memory_info']
                processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'status': proc.info['status'],
                    'cpu_percent': proc.info['cpu_percent'],
                    'memory_mb': round(mem_info.rss / (1024 * 1024), 2) if mem_info else 0,
                    'cmdline': ' '.join(proc.info['cmdline'])
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    return processes

def check_component_status(component_name: str, component_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sprawdzenie statusu komponentu systemu.
    
    Args:
        component_name: Nazwa komponentu
        component_config: Konfiguracja komponentu
        
    Returns:
        Dict: Słownik ze statusem komponentu
    """
    script_path = component_config["script"]
    processes = get_process_info(script_path)
    
    if not processes:
        return {
            "name": component_name,
            "status": "NOT_RUNNING",
            "processes": []
        }
    
    return {
        "name": component_name,
        "status": "RUNNING",
        "processes": processes
    }

def restart_component(component_name: str, component_config: Dict[str, Any]) -> bool:
    """
    Restart komponentu systemu.
    
    Args:
        component_name: Nazwa komponentu
        component_config: Konfiguracja komponentu
        
    Returns:
        bool: True jeśli restart się powiódł, False w przeciwnym wypadku
    """
    script_path = os.path.join(PROJECT_DIR, component_config["script"])
    
    # Zatrzymanie istniejących procesów
    processes = get_process_info(component_config["script"])
    for proc_info in processes:
        try:
            proc = psutil.Process(proc_info["pid"])
            proc.terminate()
            
            # Poczekaj na zakończenie procesu
            proc.wait(timeout=10)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired) as e:
            logger.error(f"Błąd podczas zatrzymywania procesu {proc_info['pid']}: {e}")
    
    # Uruchomienie procesu
    try:
        # Przygotowanie ścieżki i argumentów
        python_exe = sys.executable
        cmd = [python_exe, script_path]
        
        # Uruchomienie procesu
        if platform.system() == "Windows":
            # W Windows używamy CREATE_NEW_CONSOLE, aby proces nie dzielił konsoli z monitor_system
            from subprocess import CREATE_NEW_CONSOLE
            process = subprocess.Popen(
                cmd, 
                creationflags=CREATE_NEW_CONSOLE,
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
        else:
            # W Linux/Mac uruchamiamy w tle
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
        
        logger.info(f"Uruchomiono komponent {component_name} (PID: {process.pid})")
        return True
        
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania komponentu {component_name}: {e}")
        return False

def check_system_status(components: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Sprawdzenie statusu całego systemu.
    
    Args:
        components: Słownik z konfiguracją komponentów
        
    Returns:
        Dict: Słownik ze statusem systemu
    """
    system_status = {
        "timestamp": datetime.now().isoformat(),
        "components": {},
        "overall_status": "OK"
    }
    
    for component_name, component_config in components.items():
        status = check_component_status(component_name, component_config)
        system_status["components"][component_name] = status
        
        # Jeśli wymagany komponent nie działa, oznacz status systemu jako ERROR
        if component_config["required"] and status["status"] != "RUNNING":
            system_status["overall_status"] = "ERROR"
    
    return system_status

def monitor_system(components: Dict[str, Dict[str, Any]], interval: int, notify_email: bool = False, auto_restart: bool = False) -> None:
    """
    Ciągłe monitorowanie systemu.
    
    Args:
        components: Słownik z konfiguracją komponentów
        interval: Interwał sprawdzania w sekundach
        notify_email: Czy wysyłać powiadomienia email
        auto_restart: Czy automatycznie restartować upadłe komponenty
    """
    restart_counters = {component: 0 for component in components}
    last_restart_time = {component: datetime.min for component in components}
    
    # Czas ostatniego sprawdzenia bazy danych
    last_db_check_time = datetime.min
    
    try:
        while True:
            logger.info("Sprawdzanie statusu systemu...")
            system_status = check_system_status(components)
            
            # Zapis statusu do pliku
            status_file = os.path.join(DATA_DIR, 'system_status.json')
            os.makedirs(os.path.dirname(status_file), exist_ok=True)
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(system_status, f, indent=4, ensure_ascii=False)
            
            # Sprawdzenie każdego komponentu i podjęcie działań
            for component_name, status in system_status["components"].items():
                component_config = components[component_name]
                
                # Jeśli komponent nie działa, a powinien być automatycznie restartowany
                if status["status"] != "RUNNING" and auto_restart and component_config["required"]:
                    # Sprawdzenie, czy można zrestartować (czy nie przekroczono limitu prób lub upłynął czas cooldown)
                    current_time = datetime.now()
                    cooldown_expired = (current_time - last_restart_time[component_name]).total_seconds() > component_config["restart_cooldown"]
                    
                    if cooldown_expired and restart_counters[component_name] < component_config["restart_attempts"]:
                        logger.warning(f"Komponent {component_name} nie działa. Próba restartu...")
                        restart_success = restart_component(component_name, component_config)
                        
                        if restart_success:
                            restart_counters[component_name] += 1
                            last_restart_time[component_name] = current_time
                            logger.info(f"Restart komponentu {component_name} powiódł się. Liczba prób: {restart_counters[component_name]}")
                            
                            # Wysłanie powiadomienia o restarcie
                            if notify_email and EMAIL_CONFIG["enabled"]:
                                send_email_notification(
                                    subject=f"[LLM Trader] Restart komponentu {component_name}",
                                    message=f"Komponent {component_name} został zrestartowany.\nLiczba prób: {restart_counters[component_name]}\nCzas: {current_time.isoformat()}"
                                )
                        else:
                            logger.error(f"Restart komponentu {component_name} nie powiódł się")
                            
                            # Wysłanie powiadomienia o nieudanym restarcie
                            if notify_email and EMAIL_CONFIG["enabled"]:
                                send_email_notification(
                                    subject=f"[LLM Trader] BŁĄD: Nieudany restart {component_name}",
                                    message=f"Nie udało się zrestartować komponentu {component_name}.\nLiczba prób: {restart_counters[component_name]}\nCzas: {current_time.isoformat()}"
                                )
                    elif restart_counters[component_name] >= component_config["restart_attempts"]:
                        logger.error(f"Komponent {component_name} nie działa i przekroczono limit prób restartu ({component_config['restart_attempts']})")
                        
                        # Wysłanie powiadomienia o przekroczeniu limitu prób
                        if notify_email and EMAIL_CONFIG["enabled"] and cooldown_expired:
                            # Resetowanie licznika po wysłaniu powiadomienia, aby nie spamować
                            restart_counters[component_name] = 0
                            send_email_notification(
                                subject=f"[LLM Trader] KRYTYCZNY: Komponent {component_name} nie działa",
                                message=f"Komponent {component_name} nie działa i przekroczono limit {component_config['restart_attempts']} prób restartu.\nWymagana interwencja manualna.\nCzas: {current_time.isoformat()}"
                            )
                
                # Jeśli komponent działa, resetuj licznik prób restartu
                elif status["status"] == "RUNNING" and restart_counters[component_name] > 0:
                    logger.info(f"Komponent {component_name} działa prawidłowo. Resetowanie licznika prób restartu.")
                    restart_counters[component_name] = 0
            
            # Sprawdzenie czy należy przeprowadzić diagnostykę bazy danych
            current_time = datetime.now()
            if (current_time - last_db_check_time).total_seconds() >= DB_MONITORING["check_interval"]:
                logger.info("Wykonywanie diagnostyki bazy danych...")
                db_check_result = check_database_health()
                last_db_check_time = current_time
                
                # Jeśli wykryto problemy i włączono automatyczną naprawę
                if db_check_result.get("issues_count", 0) > 0:
                    logger.warning(f"Wykryto {db_check_result['issues_count']} problemów z bazą danych")
                    
                    # Powiadomienie o problemach
                    if DB_MONITORING["notify_on_issues"] and notify_email and EMAIL_CONFIG["enabled"]:
                        issues_text = "\n".join(db_check_result.get("issues", []))
                        send_email_notification(
                            subject=f"[LLM Trader] Problemy z bazą danych",
                            message=f"Wykryto {db_check_result['issues_count']} problemów z bazą danych:\n\n{issues_text}\n\nCzas: {current_time.isoformat()}"
                        )
                    
                    # Automatyczna naprawa
                    if DB_MONITORING["auto_fix"]:
                        logger.info("Próba automatycznej naprawy bazy danych...")
                        fix_result = fix_database_issues()
                        
                        if fix_result.get("status") == "FIXED":
                            logger.info(f"Naprawiono {fix_result.get('fixed_issues_count', 0)} problemów z bazą danych")
                            
                            # Powiadomienie o naprawie
                            if notify_email and EMAIL_CONFIG["enabled"]:
                                fixed_text = "\n".join(fix_result.get("fixed_issues", []))
                                send_email_notification(
                                    subject=f"[LLM Trader] Naprawa bazy danych",
                                    message=f"Naprawiono {fix_result.get('fixed_issues_count', 0)} problemów z bazą danych:\n\n{fixed_text}\n\nCzas: {current_time.isoformat()}"
                                )
                        else:
                            logger.error(f"Nie udało się naprawić bazy danych: {fix_result.get('error', 'Nieznany błąd')}")
                            
                            # Powiadomienie o nieudanej naprawie
                            if notify_email and EMAIL_CONFIG["enabled"]:
                                send_email_notification(
                                    subject=f"[LLM Trader] BŁĄD: Nieudana naprawa bazy danych",
                                    message=f"Nie udało się naprawić bazy danych: {fix_result.get('error', 'Nieznany błąd')}\n\nCzas: {current_time.isoformat()}"
                                )
            
            # Czekaj określony interwał przed kolejnym sprawdzeniem
            time.sleep(interval)
            
    except KeyboardInterrupt:
        logger.info("Przerwano monitorowanie systemu")
    except Exception as e:
        logger.error(f"Błąd podczas monitorowania systemu: {e}")
        
        # Wysłanie powiadomienia o błędzie
        if notify_email and EMAIL_CONFIG["enabled"]:
            send_email_notification(
                subject=f"[LLM Trader] KRYTYCZNY: Błąd monitorowania",
                message=f"Wystąpił błąd podczas monitorowania systemu:\n\n{str(e)}\n\nCzas: {datetime.now().isoformat()}"
            )

def check_database_health() -> Dict[str, Any]:
    """
    Sprawdzenie stanu bazy danych.
    
    Returns:
        Dict: Wyniki sprawdzenia bazy danych
    """
    try:
        logger.info("Uruchamianie skryptu check_database.py...")
        
        # Wyznaczenie ścieżki do skryptu check_database.py
        check_script = os.path.join(PROJECT_DIR, "scripts", "check_database.py")
        
        # Uruchomienie skryptu i przechwycenie jego wyjścia
        result = subprocess.run(
            [sys.executable, check_script, "--env", "dev"],
            capture_output=True,
            text=True
        )
        
        # Parsowanie wyników ze standardowego wyjścia
        try:
            output = result.stdout.strip()
            results = json.loads(output)
            return results
        except json.JSONDecodeError:
            logger.error(f"Nie można sparsować wyjścia skryptu check_database.py: {output}")
            return {"status": "ERROR", "error": "Nieprawidłowy format wyjścia", "issues_count": 0}
            
    except Exception as e:
        logger.error(f"Błąd podczas sprawdzania bazy danych: {e}")
        return {"status": "ERROR", "error": str(e), "issues_count": 0}

def fix_database_issues() -> Dict[str, Any]:
    """
    Naprawa problemów z bazą danych.
    
    Returns:
        Dict: Wyniki naprawy bazy danych
    """
    try:
        logger.info("Uruchamianie skryptu fix_database_issues.py...")
        
        # Wyznaczenie ścieżki do skryptu fix_database_issues.py
        fix_script = os.path.join(PROJECT_DIR, "scripts", "fix_database_issues.py")
        
        # Uruchomienie skryptu i przechwycenie jego wyjścia
        result = subprocess.run(
            [sys.executable, fix_script, "--env", "dev"],
            capture_output=True,
            text=True
        )
        
        # Parsowanie wyników ze standardowego wyjścia
        try:
            output = result.stdout.strip()
            results = json.loads(output)
            return results
        except json.JSONDecodeError:
            logger.error(f"Nie można sparsować wyjścia skryptu fix_database_issues.py: {output}")
            return {"status": "ERROR", "error": "Nieprawidłowy format wyjścia"}
            
    except Exception as e:
        logger.error(f"Błąd podczas naprawy bazy danych: {e}")
        return {"status": "ERROR", "error": str(e)}

def send_email_notification(subject: str, message: str) -> bool:
    """
    Wysłanie powiadomienia email.
    
    Args:
        subject: Temat wiadomości
        message: Treść wiadomości
        
    Returns:
        bool: True jeśli wysłanie się powiodło, False w przeciwnym wypadku
    """
    if not EMAIL_CONFIG["enabled"]:
        logger.warning("Powiadomienia email są wyłączone")
        return False
    
    try:
        # Przygotowanie wiadomości
        msg = EmailMessage()
        msg.set_content(message)
        msg['Subject'] = subject
        msg['From'] = EMAIL_CONFIG["from_email"]
        msg['To'] = EMAIL_CONFIG["to_email"]
        
        # Wysłanie email
        server = smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"])
        
        if EMAIL_CONFIG["use_tls"]:
            server.starttls()
        
        if EMAIL_CONFIG["username"] and EMAIL_CONFIG["password"]:
            server.login(EMAIL_CONFIG["username"], EMAIL_CONFIG["password"])
        
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Wysłano powiadomienie email: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"Błąd podczas wysyłania powiadomienia email: {e}")
        return False

def main():
    """Główna funkcja skryptu."""
    parser = argparse.ArgumentParser(description="Monitorowanie i zarządzanie systemem LLM Trader MT5")
    
    parser.add_argument("--interval", type=int, default=60,
                       help="Interwał sprawdzania stanu systemu w sekundach (domyślnie: 60)")
    
    parser.add_argument("--env", choices=["dev", "test", "prod"], default="dev",
                       help="Typ środowiska (wpływa na konfigurację)")
    
    parser.add_argument("--auto-restart", action="store_true",
                       help="Automatyczne restartowanie upadłych komponentów")
    
    parser.add_argument("--email-notify", action="store_true",
                       help="Wysyłanie powiadomień email o problemach")
    
    parser.add_argument("--check-only", action="store_true",
                       help="Tylko jednorazowe sprawdzenie stanu systemu, bez ciągłego monitorowania")
    
    parser.add_argument("--config", default=None,
                       help="Ścieżka do pliku konfiguracyjnego (domyślnie: config/{env}/monitor_config.json)")
    
    parser.add_argument("--db-check-interval", type=int, default=3600,
                       help="Interwał sprawdzania bazy danych w sekundach (domyślnie: 3600)")
    
    parser.add_argument("--db-auto-fix", action="store_true",
                       help="Automatyczna naprawa wykrytych problemów z bazą danych")
    
    args = parser.parse_args()
    
    # Ustawienie ścieżki do pliku konfiguracyjnego
    if args.config:
        config_path = args.config
    else:
        config_path = os.path.join(CONFIG_DIR, args.env, "monitor_config.json")
    
    # Wczytanie konfiguracji, jeśli plik istnieje
    config = {}
    if os.path.exists(config_path):
        config = load_config(config_path)
        
        # Aktualizacja konfiguracji komponentów
        if "components" in config:
            COMPONENTS.update(config["components"])
        
        # Aktualizacja konfiguracji email
        if "email" in config:
            EMAIL_CONFIG.update(config["email"])
        
        # Aktualizacja konfiguracji monitorowania bazy danych
        if "db_monitoring" in config:
            DB_MONITORING.update(config["db_monitoring"])
    
    # Zastąpienie konfiguracji argumentami wiersza poleceń
    if args.db_check_interval != 3600:
        DB_MONITORING["check_interval"] = args.db_check_interval
    
    if args.db_auto_fix:
        DB_MONITORING["auto_fix"] = True
    
    # Jednorazowe sprawdzenie stanu systemu
    if args.check_only:
        system_status = check_system_status(COMPONENTS)
        print(json.dumps(system_status, indent=4, ensure_ascii=False))
        
        # Jednorazowe sprawdzenie bazy danych
        db_status = check_database_health()
        print("\nStatus bazy danych:")
        print(json.dumps(db_status, indent=4, ensure_ascii=False))
        
        return 0
    
    # Ciągłe monitorowanie systemu
    logger.info(f"Rozpoczęcie monitorowania systemu. Interwał: {args.interval}s")
    monitor_system(
        components=COMPONENTS,
        interval=args.interval,
        notify_email=args.email_notify,
        auto_restart=args.auto_restart
    )
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Skrypt do konfiguracji środowiska pracy dla systemu LLM Trader MT5.

Ten skrypt pozwala na:
1. Konfigurację ustawień środowiska (dev, test, prod)
2. Zarządzanie uprawnieniami
3. Ustawienie zmiennych środowiskowych
4. Tworzenie niezbędnych katalogów
5. Weryfikację konfiguracji

Użycie:
    python setup_environment.py --env [dev|test|prod] [--init-db] [--verify] [--fix-permissions]
"""

import os
import sys
import json
import shutil
import logging
import argparse
import platform
import subprocess
from pathlib import Path

# Ścieżki plików
DEFAULT_ENV_FILE = '.env.template'
ENV_FILE = '.env'
CONFIG_DIR = 'config'
LOG_DIR = 'logs'

# Konfiguracje dla różnych środowisk
ENVIRONMENT_CONFIGS = {
    'dev': {
        'LOG_LEVEL': 'DEBUG',
        'DEBUG_MODE': 'True',
        'SERVER_URL': 'http://localhost:5000',
        'DATABASE_URL': 'sqlite:///data/dev_trading.db',
        'DASHBOARD_PORT': '5000',
        'API_KEY': 'dev_api_key_change_me',
        'ENABLE_MOCK_DATA': 'True',
        'MOCK_MT5_SERVER': 'True',
    },
    'test': {
        'LOG_LEVEL': 'INFO',
        'DEBUG_MODE': 'False',
        'SERVER_URL': 'http://localhost:5001',
        'DATABASE_URL': 'sqlite:///data/test_trading.db',
        'DASHBOARD_PORT': '5001',
        'API_KEY': 'test_api_key_change_me',
        'ENABLE_MOCK_DATA': 'True',
        'MOCK_MT5_SERVER': 'True',
    },
    'prod': {
        'LOG_LEVEL': 'WARNING',
        'DEBUG_MODE': 'False',
        'SERVER_URL': 'https://your-trading-server.com',
        'DATABASE_URL': 'sqlite:///data/trading.db',
        'DASHBOARD_PORT': '8080',
        'API_KEY': 'change_me_in_prod',
        'ENABLE_MOCK_DATA': 'False',
        'MOCK_MT5_SERVER': 'False',
    }
}

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('setup_environment')


def check_os():
    """Sprawdza system operacyjny."""
    system = platform.system().lower()
    logger.info(f"Wykryto system operacyjny: {system}")
    return system


def run_command(command, shell=True):
    """Uruchamia polecenie w systemie."""
    logger.info(f"Wykonywanie polecenia: {command}")
    try:
        result = subprocess.run(
            command,
            shell=shell,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.info(f"Polecenie wykonane z kodem: {result.returncode}")
        return result.returncode == 0, result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Błąd podczas wykonywania polecenia: {e}")
        return False, e.stderr


def set_permissions_linux(directory):
    """Ustawia uprawnienia dla katalogów na systemie Linux."""
    if not os.path.exists(directory):
        logger.warning(f"Katalog {directory} nie istnieje!")
        return False
    
    logger.info(f"Ustawianie uprawnień dla katalogu: {directory}")
    # Ustaw uprawnienia odczytu i zapisu dla właściciela i grupy
    run_command(f"chmod -R 775 {directory}")
    # Ustaw właściciela i grupę (tutaj zakładamy że wykonujemy jako obecny użytkownik)
    current_user = os.environ.get('USER', os.environ.get('USERNAME'))
    if current_user:
        run_command(f"chown -R {current_user}:{current_user} {directory}")
    return True


def create_directories():
    """Tworzy niezbędne katalogi, jeśli nie istnieją."""
    directories = [
        CONFIG_DIR,
        LOG_DIR,
        'data',
        os.path.join(LOG_DIR, 'agent_manager'),
        os.path.join(LOG_DIR, 'dashboard'),
        os.path.join(LOG_DIR, 'database'),
        os.path.join(LOG_DIR, 'errors'),
        os.path.join(LOG_DIR, 'llm_engine'),
        os.path.join(LOG_DIR, 'monitoring'),
        os.path.join(LOG_DIR, 'mt5_connector'),
        os.path.join(LOG_DIR, 'performance'),
        os.path.join(LOG_DIR, 'trades'),
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            logger.info(f"Tworzenie katalogu: {directory}")
            os.makedirs(directory, exist_ok=True)
    
    return True


def setup_env_file(env_type):
    """Konfiguruje plik .env na podstawie szablonu i wybranego środowiska."""
    if not os.path.exists(DEFAULT_ENV_FILE):
        logger.warning(f"Plik szablonu {DEFAULT_ENV_FILE} nie istnieje. Tworzę nowy plik .env")
        with open(ENV_FILE, 'w', encoding='utf-8') as f:
            for key, value in ENVIRONMENT_CONFIGS[env_type].items():
                f.write(f"{key}={value}\n")
        return True
    
    logger.info(f"Konfiguracja pliku .env dla środowiska: {env_type}")
    try:
        # Kopiuj szablon
        shutil.copy2(DEFAULT_ENV_FILE, ENV_FILE)
        
        # Wczytaj zawartość pliku
        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Zastąp zmienne środowiskowymi dla wybranego typu
        for key, value in ENVIRONMENT_CONFIGS[env_type].items():
            # Szukamy klucza w formacie KEY=wartość lub # KEY=wartość
            if f"{key}=" in content:
                content = content.replace(f"{key}=", f"{key}={value}\n#")
            elif f"# {key}=" in content:
                content = content.replace(f"# {key}=", f"{key}={value}\n#")
            else:
                # Jeśli klucza nie ma w szablonie, dodajemy go na końcu
                content += f"\n{key}={value}"
        
        # Zapisz zmodyfikowaną zawartość
        with open(ENV_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Plik .env został skonfigurowany dla środowiska {env_type}")
        return True
    
    except Exception as e:
        logger.error(f"Błąd podczas konfiguracji pliku .env: {e}")
        return False


def create_config_files(env_type):
    """Tworzy pliki konfiguracyjne dla wybranego środowiska."""
    config_files = {
        'database_config.json': {
            'connection_string': ENVIRONMENT_CONFIGS[env_type]['DATABASE_URL'],
            'pool_size': 5,
            'max_overflow': 10,
            'pool_timeout': 30,
            'pool_recycle': 1800,
        },
        'llm_engine_config.json': {
            'model': 'gpt-3.5-turbo' if env_type != 'prod' else 'gpt-4',
            'temperature': 0.2,
            'max_tokens': 1000,
            'timeout': 60,
            'retry_attempts': 3,
            'api_key': '${API_KEY}',
        },
        'dashboard_config.json': {
            'port': int(ENVIRONMENT_CONFIGS[env_type]['DASHBOARD_PORT']),
            'host': '0.0.0.0',
            'debug': env_type == 'dev',
            'secret_key': 'zmień_mnie_w_produkcji' if env_type != 'prod' else '${API_KEY}',
            'session_lifetime': 3600,
        },
    }
    
    for filename, config in config_files.items():
        filepath = os.path.join(CONFIG_DIR, filename)
        logger.info(f"Tworzenie pliku konfiguracyjnego: {filepath}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    
    return True


def verify_configuration():
    """Weryfikuje czy konfiguracja jest poprawna."""
    issues = []
    
    # Sprawdź plik .env
    if not os.path.exists(ENV_FILE):
        issues.append(f"Brak pliku {ENV_FILE}")
    
    # Sprawdź czy katalogi istnieją
    directories = [CONFIG_DIR, LOG_DIR, 'data']
    for directory in directories:
        if not os.path.exists(directory):
            issues.append(f"Brak katalogu {directory}")
    
    # Sprawdź pliki konfiguracyjne
    config_files = [
        os.path.join(CONFIG_DIR, 'database_config.json'),
        os.path.join(CONFIG_DIR, 'llm_engine_config.json'),
        os.path.join(CONFIG_DIR, 'dashboard_config.json')
    ]
    for config_file in config_files:
        if not os.path.exists(config_file):
            issues.append(f"Brak pliku konfiguracyjnego {config_file}")
    
    if issues:
        logger.warning("Znaleziono problemy z konfiguracją:")
        for issue in issues:
            logger.warning(f"- {issue}")
        return False
    
    logger.info("Konfiguracja zweryfikowana poprawnie.")
    return True


def setup_database(env_type):
    """Inicjalizuje bazę danych dla wybranego środowiska."""
    db_path = ENVIRONMENT_CONFIGS[env_type]['DATABASE_URL'].replace('sqlite:///', '')
    db_dir = os.path.dirname(db_path)
    
    if not os.path.exists(db_dir):
        logger.info(f"Tworzenie katalogu dla bazy danych: {db_dir}")
        os.makedirs(db_dir, exist_ok=True)
    
    if os.path.exists(db_path):
        backup_path = f"{db_path}.bak"
        logger.warning(f"Baza danych już istnieje. Tworzenie kopii zapasowej: {backup_path}")
        shutil.copy2(db_path, backup_path)
    
    logger.info("Inicjalizacja bazy danych...")
    
    try:
        # Tutaj można dodać kod do inicjalizacji schematu bazy danych
        # Dla uproszczenia, importujemy moduł DatabaseHandler i używamy jego metod
        sys.path.insert(0, os.path.abspath('.'))
        from Database.database import DatabaseHandler
        
        db_handler = DatabaseHandler(db_url=ENVIRONMENT_CONFIGS[env_type]['DATABASE_URL'])
        db_handler.initialize_database()
        
        logger.info("Baza danych została zainicjalizowana.")
        return True
    except Exception as e:
        logger.error(f"Błąd podczas inicjalizacji bazy danych: {e}")
        return False


def main():
    """Funkcja główna skryptu."""
    parser = argparse.ArgumentParser(description='Konfiguracja środowiska dla systemu LLM Trader MT5')
    parser.add_argument('--env', choices=['dev', 'test', 'prod'], default='dev',
                        help='Typ środowiska (dev, test, prod)')
    parser.add_argument('--init-db', action='store_true',
                        help='Inicjalizacja bazy danych')
    parser.add_argument('--verify', action='store_true',
                        help='Weryfikacja konfiguracji')
    parser.add_argument('--fix-permissions', action='store_true',
                        help='Napraw uprawnienia (tylko Linux)')
    
    args = parser.parse_args()
    
    # Ustawienie poziomu logowania
    logger.setLevel(logging.INFO)
    
    # Sprawdź system operacyjny
    system = check_os()
    
    # Tworzenie katalogów
    create_directories()
    
    # Konfiguracja pliku .env
    setup_env_file(args.env)
    
    # Tworzenie plików konfiguracyjnych
    create_config_files(args.env)
    
    # Inicjalizacja bazy danych jeśli potrzebna
    if args.init_db:
        setup_database(args.env)
    
    # Napraw uprawnienia jeśli potrzebne
    if args.fix_permissions and system == 'linux':
        for directory in [CONFIG_DIR, LOG_DIR, 'data']:
            set_permissions_linux(directory)
    
    # Weryfikacja konfiguracji
    if args.verify:
        verify_configuration()
    
    logger.info(f"Konfiguracja środowiska {args.env} zakończona.")
    return 0


if __name__ == "__main__":
    sys.exit(main()) 
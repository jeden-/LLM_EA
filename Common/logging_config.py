#!/usr/bin/env python
"""
Moduł konfiguracyjny dla systemu logowania.

Ten moduł dostarcza funkcje pozwalające skonfigurować logger dostosowany
do potrzeb systemu handlowego LLM Trader MT5 w różnych środowiskach 
(dev, test, prod).
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Ścieżka do katalogu logów
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")

# Upewnij się, że katalog logów istnieje
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Format logów
DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
SIMPLE_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"

# Słownik mapujący nazwy poziomów logowania na wartości numeryczne
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

def get_logger(name: str, 
               level: str = "INFO", 
               log_to_file: bool = True, 
               log_to_console: bool = True,
               log_to_db: bool = True,
               log_file: Optional[str] = None,
               format_string: str = DEFAULT_FORMAT) -> logging.Logger:
    """
    Konfiguruje i zwraca logger z podaną nazwą.
    
    Args:
        name: Nazwa loggera
        level: Poziom logowania (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Czy zapisywać logi do pliku
        log_to_console: Czy wyświetlać logi w konsoli
        log_to_db: Czy zapisywać logi do bazy danych
        log_file: Nazwa pliku logu (domyślnie generowana z nazwy modułu)
        format_string: Format komunikatów logowania
        
    Returns:
        logging.Logger: Skonfigurowany logger
    """
    # Pobierz poziom logowania
    log_level = LOG_LEVELS.get(level.upper(), logging.INFO)
    
    # Utwórz logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Wyczyść istniejące handlery
    logger.handlers = []
    
    # Dodaj handler do konsoli
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter(format_string)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # Dodaj handler do pliku
    if log_to_file:
        if not log_file:
            # Generowanie nazwy pliku z nazwy modułu
            module_name = name.split('.')[-1]
            log_file = f"{module_name}.log"
        
        file_path = os.path.join(LOG_DIR, log_file)
        
        # Konfiguracja rotującego logu (10 plików po 5MB)
        file_handler = logging.handlers.RotatingFileHandler(
            file_path, maxBytes=5 * 1024 * 1024, backupCount=10, encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(format_string)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Dodaj handler do bazy danych
    if log_to_db:
        db_handler = DatabaseLogHandler()
        db_handler.setLevel(logging.INFO)  # Zapisujemy tylko INFO i wyższe poziomy
        logger.addHandler(db_handler)
    
    return logger


class DatabaseLogHandler(logging.Handler):
    """
    Handler do zapisywania logów w bazie danych.
    
    Ten handler zapisuje komunikaty logowania w tabeli system_logs
    w bazie danych aplikacji.
    """
    
    def __init__(self):
        """Inicjalizacja handlera."""
        super().__init__()
        self.db_handler = None
    
    def emit(self, record):
        """
        Zapisuje rekord logowania do bazy danych.
        
        Args:
            record: Rekord logowania
        """
        # Lazy loading modułu DatabaseHandler, aby uniknąć cyklicznych importów
        if self.db_handler is None:
            try:
                # Próba importu DatabaseHandler
                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from Database.database import DatabaseHandler
                self.db_handler = DatabaseHandler(auto_init=False)
            except ImportError:
                # W przypadku braku dostępu do bazy danych, logujemy błąd i nie zapisujemy
                print(f"Nie można zaimportować DatabaseHandler: {sys.exc_info()[1]}")
                return
        
        try:
            # Formatowanie komunikatu
            msg = self.format(record)
            
            # Określenie nazwy modułu
            module = record.name
            
            # Określenie poziomu logowania
            level = record.levelname
            
            # Zapisanie logu do bazy danych
            self.db_handler.insert_log(level=level, module=module, message=msg)
        except Exception as e:
            # W przypadku błędu podczas zapisywania do bazy, ignorujemy błąd
            # aby nie powodować błędów w głównej aplikacji
            print(f"Błąd podczas zapisywania logu do bazy danych: {e}")


def configure_loggers(config: Dict[str, Any]) -> None:
    """
    Konfiguruje wszystkie loggery w aplikacji na podstawie konfiguracji.
    
    Args:
        config: Słownik z konfiguracją (z pliku .env lub innego źródła)
    """
    # Pobierz globalny poziom logowania
    global_level = config.get("LOG_LEVEL", "INFO").upper()
    
    # Konfiguruj główny logger
    root_logger = get_logger(
        name="root",
        level=global_level,
        log_to_file=True,
        log_to_console=True,
        log_to_db=True,
        log_file="system.log"
    )
    
    # Konfiguruj loggery dla poszczególnych modułów
    module_loggers = {
        "LLM_Engine": config.get("LOG_LEVEL_LLM", global_level),
        "MT5_Connector": config.get("LOG_LEVEL_MT5", global_level),
        "Agent_Manager": config.get("LOG_LEVEL_AGENT", global_level),
        "Database": config.get("LOG_LEVEL_DB", global_level),
        "Dashboard": config.get("LOG_LEVEL_DASHBOARD", global_level)
    }
    
    for module, level in module_loggers.items():
        get_logger(
            name=module,
            level=level,
            log_to_file=True,
            log_to_console=True,
            log_to_db=True,
            log_file=f"{module.lower()}.log"
        )


def setup_monitoring_logger() -> logging.Logger:
    """
    Konfiguruje specjalny logger do monitorowania systemu.
    
    Returns:
        logging.Logger: Logger do monitorowania
    """
    monitoring_dir = os.path.join(LOG_DIR, "monitoring")
    if not os.path.exists(monitoring_dir):
        os.makedirs(monitoring_dir)
    
    # Nazwa pliku logu zawiera datę
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(monitoring_dir, f"monitoring_{today}.log")
    
    # Konfiguracja loggera
    logger = logging.getLogger("monitoring")
    logger.setLevel(logging.INFO)
    logger.handlers = []  # Wyczyść istniejące handlery
    
    # Handler do pliku
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter("%(asctime)s | %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Handler do konsoli
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s | MONITORING | %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


if __name__ == "__main__":
    # Przykład użycia
    logger = get_logger("test_logger", level="DEBUG", log_file="test.log")
    logger.debug("To jest testowy komunikat DEBUG")
    logger.info("To jest testowy komunikat INFO")
    logger.warning("To jest testowy komunikat WARNING")
    logger.error("To jest testowy komunikat ERROR")
    logger.critical("To jest testowy komunikat CRITICAL")
    
    # Przykład konfiguracji wszystkich loggerów
    config = {
        "LOG_LEVEL": "INFO",
        "LOG_LEVEL_LLM": "DEBUG"
    }
    configure_loggers(config)
    
    # Przykład użycia loggera monitorującego
    monitoring_logger = setup_monitoring_logger()
    monitoring_logger.info("System uruchomiony")
    monitoring_logger.info("Status konta: Saldo: 10000 USD, Equity: 10500 USD") 
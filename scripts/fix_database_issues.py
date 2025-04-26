#!/usr/bin/env python
"""
Skrypt do naprawy typowych problemów z bazą danych systemu LLM Trader MT5.

Ten skrypt pozwala na naprawę najczęstszych problemów z bazą danych, w tym:
- Odbudowę brakujących tabel
- Naprawę kluczy obcych
- Usunięcie zduplikowanych rekordów
- Optymalizację bazy danych

Skrypt jest komplementarny do check_database.py i koncentruje się na naprawie wykrytych problemów.
"""

import os
import sys
import json
import sqlite3
import logging
import argparse
import time
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

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
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Oczekiwane tabele w bazie danych wraz z ich definicjami
SCHEMA_DEFINITIONS = {
    "market_analysis": """
        CREATE TABLE IF NOT EXISTS market_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            analysis_time TIMESTAMP NOT NULL,
            analysis_type TEXT NOT NULL,
            analysis_data TEXT NOT NULL,
            agent_id TEXT,
            confidence REAL
        )
    """,
    "trade_ideas": """
        CREATE TABLE IF NOT EXISTS trade_ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL,
            stop_loss REAL,
            take_profit REAL,
            creation_time TIMESTAMP NOT NULL,
            expiration_time TIMESTAMP,
            status TEXT NOT NULL,
            agent_id TEXT,
            confidence REAL,
            analysis_summary TEXT,
            executed INTEGER DEFAULT 0,
            position_id TEXT
        )
    """,
    "trades": """
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            open_time TIMESTAMP NOT NULL,
            close_time TIMESTAMP,
            open_price REAL NOT NULL,
            close_price REAL,
            volume REAL NOT NULL,
            stop_loss REAL,
            take_profit REAL,
            profit_loss REAL,
            status TEXT NOT NULL,
            position_id TEXT,
            idea_id INTEGER,
            agent_id TEXT,
            reason TEXT,
            FOREIGN KEY (idea_id) REFERENCES trade_ideas (id)
        )
    """,
    "account_info": """
        CREATE TABLE IF NOT EXISTS account_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP NOT NULL,
            balance REAL NOT NULL,
            equity REAL NOT NULL,
            free_margin REAL NOT NULL,
            margin REAL NOT NULL,
            profit REAL,
            account_number TEXT,
            leverage INTEGER
        )
    """,
    "logs": """
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP NOT NULL,
            level TEXT NOT NULL,
            module TEXT NOT NULL,
            message TEXT NOT NULL,
            details TEXT
        )
    """,
    "statistics": """
        CREATE TABLE IF NOT EXISTS statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP NOT NULL,
            stat_name TEXT NOT NULL,
            stat_value REAL,
            stat_text TEXT,
            period TEXT,
            symbol TEXT
        )
    """
}

class DatabaseFixer:
    """Klasa odpowiedzialna za naprawę problemów w bazie danych."""
    
    def __init__(self, db_path: str):
        """
        Inicjalizacja obiektu DatabaseFixer.
        
        Args:
            db_path: Ścieżka do pliku bazy danych SQLite
        """
        self.db_path = db_path
        self.connection = None
        self.fixed_issues = []
        self.backup_path = None
    
    def create_backup(self) -> bool:
        """
        Tworzenie kopii zapasowej bazy danych przed naprawą.
        
        Returns:
            bool: True jeśli utworzenie kopii zapasowej się powiodło, False w przeciwnym wypadku
        """
        try:
            # Tworzenie nazwy pliku kopii zapasowej z timestampem
            timestamp = int(time.time())
            backup_dir = os.path.dirname(self.db_path)
            backup_name = f"{os.path.basename(self.db_path)}.bak.{timestamp}"
            self.backup_path = os.path.join(backup_dir, backup_name)
            
            # Kopiowanie pliku bazy danych
            shutil.copy2(self.db_path, self.backup_path)
            logger.info(f"Utworzono kopię zapasową: {self.backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia kopii zapasowej: {e}")
            return False
    
    def connect(self) -> bool:
        """
        Nawiązanie połączenia z bazą danych.
        
        Returns:
            bool: True jeśli połączenie udane, False w przeciwnym wypadku
        """
        try:
            if not os.path.exists(self.db_path):
                logger.error(f"Plik bazy danych nie istnieje: {self.db_path}")
                return False
            
            self.connection = sqlite3.connect(self.db_path)
            # Ustawienie connection.row_factory na sqlite3.Row, aby móc odwoływać się do kolumn po nazwach
            self.connection.row_factory = sqlite3.Row
            
            logger.info(f"Połączono z bazą danych: {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd podczas łączenia z bazą danych: {e}")
            return False
    
    def disconnect(self):
        """Zamknięcie połączenia z bazą danych."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Rozłączono z bazą danych")
    
    def fix_missing_tables(self) -> Dict[str, Any]:
        """
        Naprawa brakujących tabel poprzez ich utworzenie.
        
        Returns:
            Dict: Informacje o naprawionych tabelach
        """
        if not self.connection:
            return {"error": "Brak połączenia z bazą danych"}
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            fixed_tables = []
            
            for table_name, create_statement in SCHEMA_DEFINITIONS.items():
                if table_name not in existing_tables:
                    logger.info(f"Tworzenie brakującej tabeli: {table_name}")
                    cursor.execute(create_statement)
                    self.connection.commit()
                    fixed_tables.append(table_name)
                    self.fixed_issues.append(f"Utworzono brakującą tabelę: {table_name}")
            
            return {
                "fixed_tables": fixed_tables,
                "fixed_count": len(fixed_tables)
            }
            
        except Exception as e:
            logger.error(f"Błąd podczas naprawy brakujących tabel: {e}")
            return {"error": str(e)}
    
    def fix_foreign_keys(self) -> Dict[str, Any]:
        """
        Naprawa problemów z kluczami obcymi.
        
        Returns:
            Dict: Informacje o naprawionych kluczach obcych
        """
        if not self.connection:
            return {"error": "Brak połączenia z bazą danych"}
        
        try:
            cursor = self.connection.cursor()
            
            # Włączenie sprawdzania integralności kluczy obcych
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Sprawdzenie i naprawienie nieprawidłowych referencji w tabeli trades
            cursor.execute("""
                SELECT COUNT(*) FROM trades 
                WHERE idea_id IS NOT NULL 
                AND idea_id NOT IN (SELECT id FROM trade_ideas)
            """)
            invalid_refs_count = cursor.fetchone()[0]
            
            if invalid_refs_count > 0:
                logger.warning(f"Znaleziono {invalid_refs_count} transakcji z nieprawidłowymi referencjami do trade_ideas")
                
                # Naprawienie referencji poprzez ustawienie idea_id na NULL
                cursor.execute("""
                    UPDATE trades
                    SET idea_id = NULL
                    WHERE idea_id IS NOT NULL 
                    AND idea_id NOT IN (SELECT id FROM trade_ideas)
                """)
                self.connection.commit()
                
                self.fixed_issues.append(f"Naprawiono {invalid_refs_count} nieprawidłowych referencji do trade_ideas")
            
            return {
                "fixed_foreign_keys": invalid_refs_count
            }
            
        except Exception as e:
            logger.error(f"Błąd podczas naprawy kluczy obcych: {e}")
            return {"error": str(e)}
    
    def remove_duplicates(self) -> Dict[str, Any]:
        """
        Usunięcie zduplikowanych rekordów z tabel.
        
        Returns:
            Dict: Informacje o usuniętych duplikatach
        """
        if not self.connection:
            return {"error": "Brak połączenia z bazą danych"}
        
        try:
            cursor = self.connection.cursor()
            results = {}
            
            # Szukanie i usuwanie duplikatów w tabeli market_analysis
            cursor.execute("""
                DELETE FROM market_analysis
                WHERE id NOT IN (
                    SELECT MIN(id)
                    FROM market_analysis
                    GROUP BY symbol, timeframe, analysis_time, analysis_type
                )
            """)
            results["market_analysis"] = cursor.rowcount
            
            # Szukanie i usuwanie duplikatów w tabeli trade_ideas
            cursor.execute("""
                DELETE FROM trade_ideas
                WHERE id NOT IN (
                    SELECT MIN(id)
                    FROM trade_ideas
                    GROUP BY symbol, direction, creation_time, entry_price
                )
            """)
            results["trade_ideas"] = cursor.rowcount
            
            # Szukanie i usuwanie duplikatów w tabeli trades
            cursor.execute("""
                DELETE FROM trades
                WHERE id NOT IN (
                    SELECT MIN(id)
                    FROM trades
                    GROUP BY symbol, direction, open_time, position_id
                )
            """)
            results["trades"] = cursor.rowcount
            
            # Szukanie i usuwanie duplikatów w tabeli account_info
            cursor.execute("""
                DELETE FROM account_info
                WHERE id NOT IN (
                    SELECT MIN(id)
                    FROM account_info
                    GROUP BY timestamp
                )
            """)
            results["account_info"] = cursor.rowcount
            
            # Zapisanie zmian
            self.connection.commit()
            
            total_removed = sum(results.values())
            if total_removed > 0:
                self.fixed_issues.append(f"Usunięto {total_removed} zduplikowanych rekordów")
            
            return {
                "removed_duplicates": results,
                "total_removed": total_removed
            }
            
        except Exception as e:
            logger.error(f"Błąd podczas usuwania duplikatów: {e}")
            return {"error": str(e)}
    
    def optimize_database(self) -> Dict[str, Any]:
        """
        Optymalizacja bazy danych.
        
        Returns:
            Dict: Informacje o przeprowadzonej optymalizacji
        """
        if not self.connection:
            return {"error": "Brak połączenia z bazą danych"}
        
        try:
            cursor = self.connection.cursor()
            
            # Pobranie rozmiaru bazy danych przed optymalizacją
            size_before = os.path.getsize(self.db_path)
            
            # Wykonanie VACUUM
            logger.info("Wykonywanie operacji VACUUM...")
            cursor.execute("VACUUM")
            self.connection.commit()
            
            # Wykonanie ANALYZE
            logger.info("Wykonywanie operacji ANALYZE...")
            cursor.execute("ANALYZE")
            self.connection.commit()
            
            # Pobranie rozmiaru bazy danych po optymalizacji
            size_after = os.path.getsize(self.db_path)
            size_diff = size_before - size_after
            
            if size_diff > 0:
                self.fixed_issues.append(f"Zoptymalizowano bazę danych, zmniejszenie rozmiaru o {size_diff/1024:.2f} KB")
            
            return {
                "size_before_bytes": size_before,
                "size_after_bytes": size_after,
                "size_diff_bytes": size_diff,
                "size_diff_kb": round(size_diff/1024, 2)
            }
            
        except Exception as e:
            logger.error(f"Błąd podczas optymalizacji bazy danych: {e}")
            return {"error": str(e)}
    
    def fix_database(self) -> Dict[str, Any]:
        """
        Przeprowadzenie pełnej naprawy bazy danych.
        
        Returns:
            Dict: Wyniki wszystkich operacji naprawczych
        """
        start_time = time.time()
        
        self.fixed_issues = []
        results = {
            "timestamp": datetime.now().isoformat(),
            "db_path": self.db_path,
            "fixes": {}
        }
        
        # Utworzenie kopii zapasowej
        if not self.create_backup():
            results["status"] = "ERROR"
            results["error"] = "Nie udało się utworzyć kopii zapasowej"
            return results
        
        results["backup_path"] = self.backup_path
        
        # Połączenie z bazą danych
        if not self.connect():
            results["status"] = "ERROR"
            results["error"] = "Nie udało się połączyć z bazą danych"
            return results
        
        try:
            # Naprawa brakujących tabel
            results["fixes"]["missing_tables"] = self.fix_missing_tables()
            
            # Naprawa kluczy obcych
            results["fixes"]["foreign_keys"] = self.fix_foreign_keys()
            
            # Usunięcie zduplikowanych rekordów
            results["fixes"]["duplicates"] = self.remove_duplicates()
            
            # Optymalizacja bazy danych
            results["fixes"]["optimization"] = self.optimize_database()
            
            # Podsumowanie
            results["duration_seconds"] = round(time.time() - start_time, 2)
            results["fixed_issues_count"] = len(self.fixed_issues)
            results["fixed_issues"] = self.fixed_issues
            
            if self.fixed_issues:
                results["status"] = "FIXED"
                logger.info(f"Naprawiono {len(self.fixed_issues)} problemów z bazą danych.")
            else:
                results["status"] = "NO_ISSUES"
                logger.info("Nie znaleziono problemów do naprawy.")
            
            return results
            
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd podczas naprawy bazy danych: {e}")
            results["status"] = "ERROR"
            results["error"] = str(e)
            return results
            
        finally:
            self.disconnect()

def main():
    """Główna funkcja skryptu."""
    parser = argparse.ArgumentParser(description="Naprawa problemów z bazą danych dla systemu LLM Trader MT5")
    
    parser.add_argument("--db-path", default="database/dev.db",
                       help="Ścieżka do pliku bazy danych (domyślnie: database/dev.db)")
    
    parser.add_argument("--env", choices=["dev", "test", "prod"], default="dev",
                       help="Typ środowiska (wpływa na ścieżkę bazy danych)")
    
    parser.add_argument("--output", default=None,
                       help="Ścieżka do pliku wyjściowego z raportem (domyślnie: wyświetlenie w konsoli)")
    
    parser.add_argument("--no-backup", action="store_true",
                       help="Pomiń tworzenie kopii zapasowej (nie zalecane)")
    
    args = parser.parse_args()
    
    # Jeśli podano argument --env, użyj odpowiedniej ścieżki
    if args.env and args.db_path == "database/dev.db":
        args.db_path = f"database/{args.env}.db"
    
    # Sprawdzenie czy plik bazy danych istnieje
    if not os.path.exists(args.db_path):
        logger.error(f"Plik bazy danych nie istnieje: {args.db_path}")
        return 1
    
    # Ostrzeżenie przy próbie naprawy produkcyjnej bazy danych
    if args.env == "prod":
        logger.warning("UWAGA: Próbujesz naprawić produkcyjną bazę danych!")
        confirmation = input("Czy na pewno chcesz kontynuować? (tak/nie): ")
        if confirmation.lower() != "tak":
            logger.info("Operacja anulowana przez użytkownika.")
            return 0
    
    # Utworzenie obiektu DatabaseFixer i przeprowadzenie naprawy
    fixer = DatabaseFixer(args.db_path)
    results = fixer.fix_database()
    
    # Zapisanie wyników do pliku lub wyświetlenie w konsoli
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"Raport zapisany do pliku: {args.output}")
    else:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    
    # Zwrócenie odpowiedniego kodu wyjścia
    if results["status"] in ["FIXED", "NO_ISSUES"]:
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
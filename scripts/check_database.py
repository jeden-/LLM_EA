#!/usr/bin/env python
"""
Skrypt do sprawdzania statusu i integralności bazy danych dla systemu LLM Trader MT5.

Ten skrypt pozwala na weryfikację stanu bazy danych, sprawdzenie poprawności struktury
oraz wykonanie podstawowych testów integralności danych.
"""

import os
import sys
import json
import sqlite3
import logging
import argparse
import time
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

# Oczekiwane tabele w bazie danych
EXPECTED_TABLES = [
    "market_analysis",
    "trade_ideas",
    "trades",
    "account_info",
    "logs",
    "statistics"
]

class DatabaseChecker:
    """Klasa odpowiedzialna za sprawdzanie statusu i integralności bazy danych."""
    
    def __init__(self, db_path: str):
        """
        Inicjalizacja obiektu DatabaseChecker.
        
        Args:
            db_path: Ścieżka do pliku bazy danych SQLite
        """
        self.db_path = db_path
        self.connection = None
        self.issues = []
    
    def connect(self) -> bool:
        """
        Nawiązanie połączenia z bazą danych.
        
        Returns:
            bool: True jeśli połączenie udane, False w przeciwnym wypadku
        """
        try:
            if not os.path.exists(self.db_path):
                self.issues.append(f"Plik bazy danych nie istnieje: {self.db_path}")
                return False
            
            self.connection = sqlite3.connect(self.db_path)
            # Ustawienie connection.row_factory na sqlite3.Row, aby móc odwoływać się do kolumn po nazwach
            self.connection.row_factory = sqlite3.Row
            
            logger.info(f"Połączono z bazą danych: {self.db_path}")
            return True
            
        except Exception as e:
            self.issues.append(f"Błąd podczas łączenia z bazą danych: {str(e)}")
            logger.error(f"Błąd podczas łączenia z bazą danych: {e}")
            return False
    
    def disconnect(self):
        """Zamknięcie połączenia z bazą danych."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Rozłączono z bazą danych")
    
    def check_file_size(self) -> Dict[str, Any]:
        """
        Sprawdzenie rozmiaru pliku bazy danych.
        
        Returns:
            Dict: Informacje o rozmiarze pliku
        """
        try:
            size_bytes = os.path.getsize(self.db_path)
            size_kb = size_bytes / 1024
            size_mb = size_kb / 1024
            
            result = {
                "size_bytes": size_bytes,
                "size_kb": round(size_kb, 2),
                "size_mb": round(size_mb, 2)
            }
            
            # Sprawdzenie czy rozmiar nie jest podejrzanie duży
            if size_mb > 100:
                self.issues.append(f"Baza danych jest bardzo duża: {result['size_mb']} MB")
                result["warning"] = "Baza danych jest bardzo duża"
            
            return result
            
        except Exception as e:
            self.issues.append(f"Błąd podczas sprawdzania rozmiaru pliku: {str(e)}")
            logger.error(f"Błąd podczas sprawdzania rozmiaru pliku: {e}")
            return {"error": str(e)}
    
    def check_tables(self) -> Dict[str, Any]:
        """
        Sprawdzenie czy wszystkie oczekiwane tabele istnieją w bazie danych.
        
        Returns:
            Dict: Informacje o tabelach
        """
        if not self.connection:
            return {"error": "Brak połączenia z bazą danych"}
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            missing_tables = [table for table in EXPECTED_TABLES if table not in existing_tables]
            extra_tables = [table for table in existing_tables if table not in EXPECTED_TABLES and not table.startswith('sqlite_')]
            
            result = {
                "existing_tables": existing_tables,
                "missing_tables": missing_tables,
                "extra_tables": extra_tables,
                "ok": len(missing_tables) == 0
            }
            
            if missing_tables:
                self.issues.append(f"Brakujące tabele: {', '.join(missing_tables)}")
                result["error"] = "Brakujące tabele"
            
            return result
            
        except Exception as e:
            self.issues.append(f"Błąd podczas sprawdzania tabel: {str(e)}")
            logger.error(f"Błąd podczas sprawdzania tabel: {e}")
            return {"error": str(e)}
    
    def check_table_structure(self, table_name: str) -> Dict[str, Any]:
        """
        Sprawdzenie struktury tabeli.
        
        Args:
            table_name: Nazwa tabeli do sprawdzenia
            
        Returns:
            Dict: Informacje o strukturze tabeli
        """
        if not self.connection:
            return {"error": "Brak połączenia z bazą danych"}
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [{"name": row[1], "type": row[2], "notnull": row[3], "pk": row[5]} for row in cursor.fetchall()]
            
            return {
                "table": table_name,
                "columns": columns,
                "column_count": len(columns)
            }
            
        except Exception as e:
            self.issues.append(f"Błąd podczas sprawdzania struktury tabeli {table_name}: {str(e)}")
            logger.error(f"Błąd podczas sprawdzania struktury tabeli {table_name}: {e}")
            return {"error": str(e)}
    
    def check_foreign_keys(self) -> Dict[str, Any]:
        """
        Sprawdzenie czy wszystkie klucze obce są prawidłowe.
        
        Returns:
            Dict: Informacje o kluczach obcych
        """
        if not self.connection:
            return {"error": "Brak połączenia z bazą danych"}
        
        try:
            cursor = self.connection.cursor()
            
            # Włączenie sprawdzania kluczy obcych (domyślnie wyłączone w SQLite)
            cursor.execute("PRAGMA foreign_key_check")
            violations = cursor.fetchall()
            
            result = {
                "violations_count": len(violations),
                "ok": len(violations) == 0
            }
            
            if violations:
                # Konwersja wyników do bardziej czytelnej formy
                formatted_violations = []
                for v in violations:
                    formatted_violations.append({
                        "table": v[0],
                        "rowid": v[1],
                        "parent_table": v[2],
                        "fk_index": v[3]
                    })
                
                result["violations"] = formatted_violations
                self.issues.append(f"Znaleziono {len(violations)} naruszeń integralności kluczy obcych")
            
            return result
            
        except Exception as e:
            self.issues.append(f"Błąd podczas sprawdzania kluczy obcych: {str(e)}")
            logger.error(f"Błąd podczas sprawdzania kluczy obcych: {e}")
            return {"error": str(e)}
    
    def check_row_counts(self) -> Dict[str, Any]:
        """
        Sprawdzenie liczby wierszy w każdej tabeli.
        
        Returns:
            Dict: Informacje o liczbie wierszy w tabelach
        """
        if not self.connection:
            return {"error": "Brak połączenia z bazą danych"}
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            
            counts = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                counts[table] = count
                
                # Sprawdzenie czy liczba wierszy nie jest podejrzanie duża
                if count > 1000000:
                    self.issues.append(f"Tabela {table} zawiera bardzo dużo wierszy: {count}")
            
            return counts
            
        except Exception as e:
            self.issues.append(f"Błąd podczas liczenia wierszy: {str(e)}")
            logger.error(f"Błąd podczas liczenia wierszy: {e}")
            return {"error": str(e)}
    
    def check_integrity(self) -> Dict[str, Any]:
        """
        Wykonanie testu integralności bazy danych.
        
        Returns:
            Dict: Wyniki testu integralności
        """
        if not self.connection:
            return {"error": "Brak połączenia z bazą danych"}
        
        try:
            cursor = self.connection.cursor()
            
            # Wykonanie testu integralności
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchall()
            
            # Jeśli wszystko OK, powinien być tylko jeden wiersz z wartością "ok"
            is_ok = (len(integrity_result) == 1 and integrity_result[0][0] == "ok")
            
            result = {
                "integrity_ok": is_ok,
                "details": [row[0] for row in integrity_result]
            }
            
            if not is_ok:
                self.issues.append("Test integralności bazy danych wykazał problemy")
            
            return result
            
        except Exception as e:
            self.issues.append(f"Błąd podczas testu integralności: {str(e)}")
            logger.error(f"Błąd podczas testu integralności: {e}")
            return {"error": str(e)}
    
    def check_consistency(self) -> Dict[str, Any]:
        """
        Sprawdzenie spójności danych pomiędzy powiązanymi tabelami.
        
        Returns:
            Dict: Wyniki sprawdzenia spójności
        """
        if not self.connection:
            return {"error": "Brak połączenia z bazą danych"}
        
        results = {}
        
        try:
            cursor = self.connection.cursor()
            
            # Sprawdzenie czy wszystkie trade_ideas mają poprawne analysis_id
            cursor.execute("""
                SELECT COUNT(*) FROM trade_ideas 
                WHERE analysis_id IS NOT NULL 
                AND analysis_id NOT IN (SELECT analysis_id FROM market_analysis)
            """)
            invalid_analysis_count = cursor.fetchone()[0]
            
            if invalid_analysis_count > 0:
                self.issues.append(f"Znaleziono {invalid_analysis_count} pomysłów handlowych z nieprawidłowym analysis_id")
            
            results["invalid_analysis_refs"] = invalid_analysis_count
            
            # Sprawdzenie czy wszystkie trades mają poprawne idea_id
            cursor.execute("""
                SELECT COUNT(*) FROM trades 
                WHERE idea_id IS NOT NULL 
                AND idea_id NOT IN (SELECT id FROM trade_ideas)
            """)
            invalid_idea_count = cursor.fetchone()[0]
            
            if invalid_idea_count > 0:
                self.issues.append(f"Znaleziono {invalid_idea_count} transakcji z nieprawidłowym idea_id")
            
            results["invalid_idea_refs"] = invalid_idea_count
            
            return results
            
        except Exception as e:
            self.issues.append(f"Błąd podczas sprawdzania spójności: {str(e)}")
            logger.error(f"Błąd podczas sprawdzania spójności: {e}")
            return {"error": str(e)}
    
    def run_check(self) -> Dict[str, Any]:
        """
        Przeprowadzenie pełnego sprawdzenia bazy danych.
        
        Returns:
            Dict: Wyniki wszystkich testów
        """
        start_time = time.time()
        
        self.issues = []
        results = {
            "timestamp": datetime.now().isoformat(),
            "db_path": self.db_path,
            "checks": {}
        }
        
        # Połączenie z bazą danych
        if not self.connect():
            results["status"] = "ERROR"
            results["errors"] = self.issues
            return results
        
        try:
            # Sprawdzenie rozmiaru pliku
            results["checks"]["file_size"] = self.check_file_size()
            
            # Sprawdzenie tabel
            results["checks"]["tables"] = self.check_tables()
            
            # Tylko jeśli tabele są poprawne, kontynuuj pozostałe testy
            if results["checks"]["tables"].get("ok", False):
                # Sprawdzenie struktury każdej tabeli
                table_structures = {}
                for table in EXPECTED_TABLES:
                    table_structures[table] = self.check_table_structure(table)
                results["checks"]["table_structures"] = table_structures
                
                # Sprawdzenie kluczy obcych
                results["checks"]["foreign_keys"] = self.check_foreign_keys()
                
                # Sprawdzenie liczby wierszy
                results["checks"]["row_counts"] = self.check_row_counts()
                
                # Test integralności
                results["checks"]["integrity"] = self.check_integrity()
                
                # Sprawdzenie spójności
                results["checks"]["consistency"] = self.check_consistency()
            
            # Podsumowanie
            results["duration_seconds"] = round(time.time() - start_time, 2)
            results["issues_count"] = len(self.issues)
            results["issues"] = self.issues
            
            if not self.issues:
                results["status"] = "OK"
                logger.info("Baza danych przeszła wszystkie testy pomyślnie.")
            else:
                results["status"] = "WARNING"
                logger.warning(f"Znaleziono {len(self.issues)} problemów z bazą danych.")
            
            return results
            
        except Exception as e:
            self.issues.append(f"Nieoczekiwany błąd podczas sprawdzania bazy danych: {str(e)}")
            logger.error(f"Nieoczekiwany błąd podczas sprawdzania bazy danych: {e}")
            results["status"] = "ERROR"
            results["issues"] = self.issues
            return results
            
        finally:
            self.disconnect()

def attempt_fix_database(db_path: str) -> bool:
    """
    Próba naprawy bazy danych.
    
    Args:
        db_path: Ścieżka do pliku bazy danych
        
    Returns:
        bool: True jeśli naprawa się powiodła, False w przeciwnym wypadku
    """
    logger.info(f"Próba naprawy bazy danych: {db_path}")
    
    try:
        # Tworzenie kopii zapasowej
        backup_path = f"{db_path}.bak.{int(time.time())}"
        logger.info(f"Tworzenie kopii zapasowej bazy danych: {backup_path}")
        
        import shutil
        shutil.copy2(db_path, backup_path)
        
        # Próba otwarcia i naprawy bazy
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Uruchomienie akcji VACUUM, która może pomóc naprawić niektóre problemy
        logger.info("Wykonywanie operacji VACUUM...")
        cursor.execute("VACUUM")
        conn.commit()
        
        # Zamknięcie połączenia
        conn.close()
        
        logger.info("Operacja naprawy zakończona. Sprawdź ponownie bazę danych.")
        return True
        
    except Exception as e:
        logger.error(f"Błąd podczas próby naprawy bazy danych: {e}")
        return False

def main():
    """Główna funkcja skryptu."""
    parser = argparse.ArgumentParser(description="Sprawdzanie statusu i integralności bazy danych dla systemu LLM Trader MT5")
    
    parser.add_argument("--db-path", default="database/dev.db",
                       help="Ścieżka do pliku bazy danych (domyślnie: database/dev.db)")
    
    parser.add_argument("--env", choices=["dev", "test", "prod"], default="dev",
                       help="Typ środowiska (wpływa na ścieżkę bazy danych)")
    
    parser.add_argument("--output", default=None,
                       help="Ścieżka do pliku wyjściowego z raportem (domyślnie: wyświetlenie w konsoli)")
    
    parser.add_argument("--fix", action="store_true",
                       help="Próba naprawy bazy danych (wykonuje backup przed naprawą)")
    
    args = parser.parse_args()
    
    # Jeśli podano argument --env, użyj odpowiedniej ścieżki
    if args.env and args.db_path == "database/dev.db":
        args.db_path = f"database/{args.env}.db"
    
    # Sprawdzenie czy plik bazy danych istnieje
    if not os.path.exists(args.db_path):
        logger.error(f"Plik bazy danych nie istnieje: {args.db_path}")
        return 1
    
    # Utworzenie obiektu DatabaseChecker i przeprowadzenie testów
    checker = DatabaseChecker(args.db_path)
    results = checker.run_check()
    
    # Zapisanie wyników do pliku lub wyświetlenie w konsoli
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"Raport zapisany do pliku: {args.output}")
    else:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    
    # Jeśli znaleziono problemy i wybrano opcję naprawy, próbuj naprawić
    if results["issues_count"] > 0 and args.fix:
        logger.warning(f"Znaleziono {results['issues_count']} problemów z bazą danych. Próba naprawy...")
        fixed = attempt_fix_database(args.db_path)
        if fixed:
            # Ponowne sprawdzenie po naprawie
            logger.info("Ponowne sprawdzanie bazy danych po naprawie...")
            results_after_fix = checker.run_check()
            
            if args.output:
                fix_output = f"{os.path.splitext(args.output)[0]}_after_fix{os.path.splitext(args.output)[1]}"
                with open(fix_output, 'w', encoding='utf-8') as f:
                    json.dump(results_after_fix, f, ensure_ascii=False, indent=2)
                logger.info(f"Raport po naprawie zapisany do pliku: {fix_output}")
            else:
                print("\nWyniki po naprawie:")
                print(json.dumps(results_after_fix, ensure_ascii=False, indent=2))
            
            if results_after_fix["issues_count"] == 0:
                logger.info("Naprawa zakończyła się sukcesem! Wszystkie problemy zostały rozwiązane.")
            else:
                logger.warning(f"Naprawa częściowo skuteczna. Pozostało {results_after_fix['issues_count']} problemów.")
    
    # Zwrócenie odpowiedniego kodu wyjścia
    if results["status"] == "OK":
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
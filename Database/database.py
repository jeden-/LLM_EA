#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moduł database.py - główny moduł bazodanowy systemu handlowego LLM.
Implementuje klasę DatabaseHandler do zarządzania bazą danych i operacjami CRUD.
"""

import os
import json
import sqlite3
import logging
import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

# Konfiguracja loggera
logger = logging.getLogger(__name__)

class DatabaseHandler:
    """
    Klasa DatabaseHandler do zarządzania bazą danych SQLite.
    
    Zapewnia:
    - Tworzenie i inicjalizację bazy danych
    - Zapisywanie analiz rynkowych
    - Zapisywanie historii transakcji
    - Zapisywanie logów systemowych
    - Dostęp do danych historycznych
    """
    
    def __init__(self, db_path: str = None, auto_init: bool = True):
        """
        Inicjalizacja handlera bazy danych.
        
        Args:
            db_path: Ścieżka do pliku bazy danych (domyślnie: "cache/trading_data.db")
            auto_init: Czy automatycznie inicjalizować bazę danych
        """
        # Ustawienie domyślnej ścieżki do bazy danych
        if db_path is None:
            # Ścieżka względna do katalogu projektu
            project_root = Path(__file__).resolve().parent.parent
            db_dir = project_root / "cache"
            
            # Upewnij się, że katalog istnieje
            if not db_dir.exists():
                os.makedirs(db_dir)
                
            db_path = str(db_dir / "trading_data.db")
        
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
        logger.info(f"Inicjalizacja DatabaseHandler z bazą danych: {self.db_path}")
        
        # Automatyczna inicjalizacja bazy danych
        if auto_init:
            self.init_database()
    
    def connect(self) -> bool:
        """
        Nawiązanie połączenia z bazą danych.
        
        Returns:
            True, jeśli połączenie zostało nawiązane pomyślnie, False w przeciwnym razie
        """
        # Jeśli połączenie już istnieje, zwróć True
        if self.conn is not None and self.cursor is not None:
            return True
            
        try:
            self.conn = sqlite3.connect(self.db_path)
            # Włączenie obsługi klucza obcego
            self.conn.execute("PRAGMA foreign_keys = ON")
            # Ustawienie zwracania wyników w formie słowników
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            return True
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas łączenia z bazą danych: {e}")
            return False
    
    def disconnect(self):
        """Zakończenie połączenia z bazą danych."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
    
    def update_schema(self) -> bool:
        """
        Aktualizacja schematu bazy danych.
        
        Ta metoda wykonuje migracje schematu bazy danych, dodając nowe tabele
        lub kolumny w miarę rozwoju aplikacji. Jest używana przez skrypt setup_database.py
        podczas aktualizacji systemu.
        
        Returns:
            bool: True jeśli aktualizacja przebiegła pomyślnie, False w przeciwnym razie
        """
        if not self.connect():
            return False
            
        try:
            # Odczytanie obecnej wersji bazy danych (tabela może nie istnieć przy pierwszym uruchomieniu)
            try:
                self.cursor.execute("SELECT version FROM schema_version")
                current_version = self.cursor.fetchone()[0]
            except sqlite3.OperationalError:
                # Tabela nie istnieje, utwórz ją i ustaw wersję na 0
                self.cursor.execute('''
                CREATE TABLE schema_version (
                    version INTEGER PRIMARY KEY,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                self.cursor.execute("INSERT INTO schema_version (version) VALUES (0)")
                current_version = 0
                self.conn.commit()
                
            logger.info(f"Obecna wersja schematu bazy danych: {current_version}")
            
            # Sekcje migracji - każda sekcja zwiększa wersję o 1
            # Migracje są wykonywane tylko jeśli obecna wersja jest niższa niż numer migracji
            
            # Migracja #1: Dodanie tabeli trade_ideas_extended (jeśli jeszcze nie istnieje)
            if current_version < 1:
                logger.info("Wykonywanie migracji #1: Dodawanie tabeli trade_ideas_extended")
                
                self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS trade_ideas_extended (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    risk_percentage REAL,
                    status TEXT DEFAULT 'PENDING',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    valid_until TEXT,
                    executed_at TEXT,
                    ticket TEXT,
                    rejection_reason TEXT,
                    timeframe TEXT,
                    strategy TEXT,
                    source TEXT,
                    technical_analysis TEXT,
                    fundamental_analysis TEXT,
                    additional_notes TEXT,
                    risk_analysis TEXT,
                    chart_image_path TEXT,
                    author TEXT
                )
                ''')
                
                # Aktualizacja wersji
                self.cursor.execute("UPDATE schema_version SET version = 1, updated_at = CURRENT_TIMESTAMP")
                logger.info("Migracja #1 zakończona pomyślnie")
                current_version = 1
                
            # Migracja #2: Dodanie tabeli account_history
            if current_version < 2:
                logger.info("Wykonywanie migracji #2: Dodawanie tabeli account_history")
                
                self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS account_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    balance REAL NOT NULL,
                    equity REAL NOT NULL,
                    margin REAL,
                    margin_level REAL,
                    profit_day REAL,
                    profit_week REAL,
                    profit_month REAL,
                    profit_total REAL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                # Aktualizacja wersji
                self.cursor.execute("UPDATE schema_version SET version = 2, updated_at = CURRENT_TIMESTAMP")
                logger.info("Migracja #2 zakończona pomyślnie")
                current_version = 2
                
            # Migracja #3: Dodanie tabeli system_parameters
            if current_version < 3:
                logger.info("Wykonywanie migracji #3: Dodawanie tabeli system_parameters")
                
                self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_parameters (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                # Wstawienie domyślnych parametrów
                default_params = [
                    ('risk_percentage', '1.0', 'Domyślny procent ryzyka na transakcję'),
                    ('max_daily_risk', '5.0', 'Maksymalny dzienny procent ryzyka'),
                    ('max_positions', '5', 'Maksymalna liczba otwartych pozycji'),
                    ('default_timeframe', 'H1', 'Domyślny timeframe analizy'),
                    ('trading_symbols', 'EURUSD,GBPUSD,USDJPY,USDCHF,AUDUSD', 'Lista par walutowych do analizy')
                ]
                
                for param in default_params:
                    self.cursor.execute('''
                    INSERT OR IGNORE INTO system_parameters (key, value, description)
                    VALUES (?, ?, ?)
                    ''', param)
                
                # Aktualizacja wersji
                self.cursor.execute("UPDATE schema_version SET version = 3, updated_at = CURRENT_TIMESTAMP")
                logger.info("Migracja #3 zakończona pomyślnie")
                
            # Zapisz zmiany
            self.conn.commit()
            logger.info(f"Zaktualizowano schemat bazy danych do wersji {current_version}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas aktualizacji schematu bazy danych: {e}")
            self.conn.rollback()
            return False
        finally:
            self.disconnect()
    
    def init_database(self) -> bool:
        """
        Inicjalizacja struktury bazy danych.
        
        Returns:
            True, jeśli inicjalizacja przebiegła pomyślnie, False w przeciwnym razie
        """
        if not self.connect():
            return False
        
        try:
            # Tabela z analizami rynkowymi
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                analysis_data TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Tabela z pomysłami handlowymi (trade ideas)
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id INTEGER,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                risk_reward REAL,
                timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'new',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (analysis_id) REFERENCES market_analyses (id)
            )
            ''')
            
            # Tabela z transakcjami (trades)
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_idea_id INTEGER,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                entry_time TEXT NOT NULL,
                exit_price REAL,
                exit_time TEXT,
                stop_loss REAL,
                take_profit REAL,
                profit_loss REAL,
                status TEXT NOT NULL,
                volume REAL NOT NULL,
                comment TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trade_idea_id) REFERENCES trade_ideas (id)
            )
            ''')
            
            # Tabela z logami systemu
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                module TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            self.conn.commit()
            logger.info("Struktura bazy danych została zainicjalizowana")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas inicjalizacji bazy danych: {e}")
            self.conn.rollback()
            self.disconnect()
            return False
    
    def insert_market_analysis(self, symbol: str, timeframe: str, analysis_data: Dict[str, Any]) -> int:
        """
        Zapisanie analizy rynkowej do bazy danych.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Timeframe analizy
            analysis_data: Słownik z danymi analizy
            
        Returns:
            ID zapisanego rekordu lub -1 w przypadku błędu
        """
        # Walidacja typów danych
        if not isinstance(symbol, str):
            raise TypeError("Symbol musi być typu string")
        if not isinstance(timeframe, str):
            raise TypeError("Timeframe musi być typu string")
        if not isinstance(analysis_data, dict):
            raise TypeError("Analysis data musi być słownikiem")
            
        try:
            # Konwersja danych analizy do formatu JSON
            analysis_json = json.dumps(analysis_data, ensure_ascii=False)
            
            # Wstawienie rekordu
            self.cursor.execute('''
            INSERT INTO market_analyses (symbol, timeframe, analysis_data)
            VALUES (?, ?, ?)
            ''', (symbol, timeframe, analysis_json))
            
            self.conn.commit()
            record_id = self.cursor.lastrowid
            
            logger.info(f"Zapisano analizę rynkową dla {symbol} ({timeframe}), ID: {record_id}")
            return record_id
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas zapisywania analizy rynkowej: {e}")
            self.conn.rollback()
            return -1

    def insert_trade_idea(self, analysis_id: int, symbol: str, direction: str,
                      entry_price: float, stop_loss: float, take_profit: float,
                      risk_reward: float) -> int:
        """
        Zapisanie idei handlowej do bazy danych.
        
        Args:
            analysis_id: ID powiązanej analizy rynkowej
            symbol: Symbol instrumentu
            direction: Kierunek transakcji (buy/sell)
            entry_price: Cena wejścia
            stop_loss: Poziom stop loss
            take_profit: Poziom take profit
            risk_reward: Stosunek zysku do ryzyka
            
        Returns:
            ID zapisanego rekordu lub -1 w przypadku błędu
        """
        try:
            # Wstawienie rekordu
            self.cursor.execute('''
            INSERT INTO trade_ideas (analysis_id, symbol, direction, entry_price, stop_loss, take_profit, risk_reward)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (analysis_id, symbol, direction, entry_price, stop_loss, take_profit, risk_reward))
            
            self.conn.commit()
            record_id = self.cursor.lastrowid
            
            logger.info(f"Zapisano ideę handlową dla {symbol} ({direction}), ID: {record_id}")
            return record_id
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas zapisywania idei handlowej: {e}")
            self.conn.rollback()
            return -1

    def insert_trade(self, trade_idea_id: int, symbol: str, direction: str, 
                 entry_price: float, entry_time: str, stop_loss: float,
                 take_profit: float, volume: float, comment: str = None) -> int:
        """
        Zapisanie transakcji do bazy danych.
        
        Args:
            trade_idea_id: ID powiązanej idei handlowej
            symbol: Symbol instrumentu
            direction: Kierunek transakcji (buy/sell)
            entry_price: Cena wejścia
            entry_time: Czas wejścia
            stop_loss: Poziom stop loss
            take_profit: Poziom take profit
            volume: Wielkość pozycji
            comment: Komentarz do transakcji
            
        Returns:
            ID zapisanego rekordu lub -1 w przypadku błędu
        """
        if not self.connect():
            return -1
        
        try:
            # Wstawienie rekordu
            self.cursor.execute('''
            INSERT INTO trades (trade_idea_id, symbol, direction, entry_price, entry_time, stop_loss, take_profit, volume, status, comment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (trade_idea_id, symbol, direction, entry_price, entry_time, stop_loss, take_profit, volume, 'open', comment))
            
            self.conn.commit()
            record_id = self.cursor.lastrowid
            
            logger.info(f"Zapisano transakcję dla {symbol} ({direction}), ID: {record_id}")
            return record_id
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas zapisywania transakcji: {e}")
            self.conn.rollback()
            return -1

    def insert_log(self, level: str, module: str, message: str) -> int:
        """
        Zapisanie logu do bazy danych.
        
        Args:
            level: Poziom logu (INFO, WARNING, ERROR, etc.)
            module: Nazwa modułu
            message: Treść wiadomości
            
        Returns:
            ID zapisanego rekordu lub -1 w przypadku błędu
        """
        try:
            # Wstawienie rekordu
            self.cursor.execute('''
            INSERT INTO system_logs (level, module, message)
            VALUES (?, ?, ?)
            ''', (level, module, message))
            
            self.conn.commit()
            record_id = self.cursor.lastrowid
            
            logger.info(f"Zapisano log: {level} - {module} - {message}")
            return record_id
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas zapisywania logu: {e}")
            self.conn.rollback()
            return -1
    
    def get_latest_analyses(self, symbol: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Pobranie ostatnich analiz rynkowych.
        
        Args:
            symbol: Symbol instrumentu (opcjonalnie)
            limit: Maksymalna liczba rekordów
            
        Returns:
            Lista słowników z danymi analiz
        """
        if not self.connect():
            return []
        
        try:
            if symbol:
                # Zapytanie dla konkretnego symbolu
                self.cursor.execute('''
                SELECT id, symbol, timeframe, timestamp, analysis_data, created_at
                FROM market_analyses
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT ?
                ''', (symbol, limit))
            else:
                # Zapytanie dla wszystkich symboli
                self.cursor.execute('''
                SELECT id, symbol, timeframe, timestamp, analysis_data, created_at
                FROM market_analyses
                ORDER BY timestamp DESC
                LIMIT ?
                ''', (limit,))
            
            # Konwersja wyników do listy słowników
            results = []
            for row in self.cursor.fetchall():
                data = dict(row)
                # Konwersja JSON do słownika
                data['analysis_data'] = json.loads(data['analysis_data'])
                results.append(data)
            
            return results
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas pobierania analiz: {e}")
            return []
        finally:
            self.disconnect()
    
    def get_trade_ideas(self, symbol: Optional[str] = None, status: Optional[str] = None, 
                     limit: int = 10) -> List[Dict[str, Any]]:
        """
        Pobranie idei handlowych.
        
        Args:
            symbol: Symbol instrumentu (opcjonalnie)
            status: Status idei handlowej (opcjonalnie)
            limit: Maksymalna liczba rekordów
            
        Returns:
            Lista słowników z danymi idei handlowych
        """
        if not self.connect():
            return []
        
        try:
            query = '''
            SELECT id, analysis_id, symbol, direction, entry_price, stop_loss, take_profit, risk_reward, timestamp, status, created_at
            FROM trade_ideas
            '''
            params = []
            
            # Dodanie filtrów
            conditions = []
            if symbol:
                conditions.append("symbol = ?")
                params.append(symbol)
            if status:
                conditions.append("status = ?")
                params.append(status)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            self.cursor.execute(query, params)
            
            # Konwersja wyników do listy słowników
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(row))
            
            return results
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas pobierania idei handlowych: {e}")
            return []
        finally:
            self.disconnect()
    
    def get_trades(self, symbol: Optional[str] = None, status: Optional[str] = None, 
               limit: int = 10) -> List[Dict[str, Any]]:
        """
        Pobranie transakcji.
        
        Args:
            symbol: Symbol instrumentu (opcjonalnie)
            status: Status transakcji (opcjonalnie)
            limit: Maksymalna liczba rekordów
            
        Returns:
            Lista słowników z danymi transakcji
        """
        if not self.connect():
            return []
        
        try:
            query = '''
            SELECT id, trade_idea_id, symbol, direction, entry_price, entry_time, exit_price, exit_time, stop_loss, take_profit, profit_loss, status, volume, comment, created_at
            FROM trades
            '''
            params = []
            
            # Dodanie filtrów
            conditions = []
            if symbol:
                conditions.append("symbol = ?")
                params.append(symbol)
            if status:
                conditions.append("status = ?")
                params.append(status)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY entry_time DESC LIMIT ?"
            params.append(limit)
            
            self.cursor.execute(query, params)
            
            # Konwersja wyników do listy słowników
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(row))
            
            return results
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas pobierania transakcji: {e}")
            return []
        finally:
            self.disconnect()
    
    def get_logs(self, level: Optional[str] = None, module: Optional[str] = None, 
             limit: int = 100) -> List[Dict[str, Any]]:
        """
        Pobranie logów systemowych.
        
        Args:
            level: Poziom logu (opcjonalnie)
            module: Nazwa modułu (opcjonalnie)
            limit: Maksymalna liczba rekordów
            
        Returns:
            Lista słowników z danymi logów
        """
        if not self.connect():
            return []
        
        try:
            query = '''
            SELECT id, level, module, message, timestamp, created_at
            FROM system_logs
            '''
            params = []
            
            # Dodanie filtrów
            conditions = []
            if level:
                conditions.append("level = ?")
                params.append(level)
            if module:
                conditions.append("module = ?")
                params.append(module)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            self.cursor.execute(query, params)
            
            # Konwersja wyników do listy słowników
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(row))
            
            return results
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas pobierania logów: {e}")
            return []
        finally:
            self.disconnect()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Pobranie statystyk z bazy danych.
        
        Returns:
            Słownik ze statystykami
        """
        if not self.connect():
            return {}
        
        try:
            stats = {}
            
            # Liczba analiz
            self.cursor.execute("SELECT COUNT(*) as count FROM market_analyses")
            stats['analyses_count'] = self.cursor.fetchone()['count']
            
            # Liczba idei handlowych
            self.cursor.execute("SELECT COUNT(*) as count FROM trade_ideas")
            stats['trade_ideas_count'] = self.cursor.fetchone()['count']
            
            # Statystyki transakcji
            self.cursor.execute('''
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open_trades,
                SUM(CASE WHEN status != 'open' THEN 1 ELSE 0 END) as closed_trades,
                SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as profitable_trades,
                SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
                SUM(profit_loss) as total_profit_loss
            FROM trades
            ''')
            
            trade_stats = dict(self.cursor.fetchone())
            stats.update(trade_stats)
            
            # Statystyki per symbol
            self.cursor.execute('''
            SELECT symbol, COUNT(*) as trades_count, SUM(profit_loss) as symbol_pnl
            FROM trades
            WHERE status != 'open'
            GROUP BY symbol
            ''')
            
            symbol_stats = {}
            for row in self.cursor.fetchall():
                symbol_stats[row['symbol']] = {
                    'trades_count': row['trades_count'],
                    'profit_loss': row['symbol_pnl']
                }
                
            stats['symbol_stats'] = symbol_stats
            
            return stats
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas pobierania statystyk: {e}")
            return {}
        finally:
            self.disconnect()
    
    def clear_database(self) -> bool:
        """
        Czyści zawartość bazy danych (używać tylko w środowisku testowym!).
        
        Returns:
            True, jeśli operacja przebiegła pomyślnie, False w przeciwnym razie
        """
        if not self.connect():
            return False
        
        try:
            # Usunięcie danych z tabel
            tables = ['trades', 'trade_ideas', 'market_analyses', 'system_logs']
            for table in tables:
                self.cursor.execute(f"DELETE FROM {table}")
            
            self.conn.commit()
            logger.warning("Zawartość bazy danych została wyczyszczona")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas czyszczenia bazy danych: {e}")
            self.conn.rollback()
            return False
        finally:
            self.disconnect()
    
    def add_trade_idea(self, trade_idea_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dodaje nowy pomysł handlowy do bazy danych.
        
        Args:
            trade_idea_data: Dane nowego pomysłu handlowego
            
        Returns:
            Dict[str, Any]: Wynik operacji z ID nowego pomysłu lub błędem
        """
        try:
            # Sprawdź czy tabela istnieje, jeśli nie - utwórz
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS trade_ideas_extended (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    risk_percentage REAL,
                    status TEXT DEFAULT 'PENDING',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    valid_until TEXT,
                    executed_at TEXT,
                    ticket TEXT,
                    rejection_reason TEXT,
                    timeframe TEXT,
                    strategy TEXT,
                    source TEXT,
                    technical_analysis TEXT,
                    fundamental_analysis TEXT,
                    additional_notes TEXT,
                    risk_analysis TEXT,
                    chart_image_path TEXT,
                    author TEXT
                )
            ''')
            
            # Dodaj pole created_at i updated_at jeśli nie ma
            now = datetime.datetime.now().isoformat()
            if "created_at" not in trade_idea_data:
                trade_idea_data["created_at"] = now
            if "updated_at" not in trade_idea_data:
                trade_idea_data["updated_at"] = now
            if "status" not in trade_idea_data:
                trade_idea_data["status"] = "PENDING"
                
            # Odrzuć pola, które nie istnieją w tabeli
            self.cursor.execute("PRAGMA table_info(trade_ideas_extended)")
            table_columns = [column[1] for column in self.cursor.fetchall()]
            
            # Przygotuj dane do wstawienia
            filtered_data = {k: v for k, v in trade_idea_data.items() if k in table_columns}
            
            # Przygotuj zapytanie SQL
            columns = ", ".join(filtered_data.keys())
            placeholders = ", ".join(["?" for _ in filtered_data.keys()])
            values = tuple(filtered_data.values())
            
            self.cursor.execute(f'''
                INSERT INTO trade_ideas_extended ({columns})
                VALUES ({placeholders})
            ''', values)
            
            # Pobierz ID nowego rekordu
            idea_id = self.cursor.lastrowid
            self.conn.commit()
            
            logger.info(f"Dodano nowy pomysł handlowy o ID: {idea_id}")
            return {
                "success": True,
                "id": idea_id,
                "message": "Pomysł handlowy dodany pomyślnie"
            }
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Błąd podczas dodawania pomysłu handlowego: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def update_trade_idea(self, idea_id: int, update_data: Dict[str, Any]) -> bool:
        """
        Aktualizuje pomysł handlowy w bazie danych.
        
        Args:
            idea_id: ID pomysłu handlowego do aktualizacji
            update_data: Dane do aktualizacji
            
        Returns:
            bool: True jeśli aktualizacja się powiodła, False w przeciwnym razie
        """
        try:
            # Dodaj pole updated_at
            if "updated_at" not in update_data:
                update_data["updated_at"] = datetime.datetime.now().isoformat()
                
            # Przygotuj zapytanie SQL
            set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
            values = list(update_data.values())
            values.append(idea_id)  # Dla warunku WHERE
            
            self.cursor.execute(f'''
                UPDATE trade_ideas_extended 
                SET {set_clause}
                WHERE id = ?
            ''', values)
            
            # Sprawdź, czy rekord został zaktualizowany
            if self.cursor.rowcount == 0:
                logger.warning(f"Nie znaleziono pomysłu handlowego o ID: {idea_id}")
                return False
                
            self.conn.commit()
            logger.info(f"Zaktualizowano pomysł handlowy o ID: {idea_id}")
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Błąd podczas aktualizacji pomysłu handlowego: {e}")
            return False
            
    def delete_trade_idea(self, idea_id: int) -> bool:
        """
        Usuwa pomysł handlowy i powiązane komentarze z bazy danych.
        
        Args:
            idea_id: ID pomysłu handlowego do usunięcia
            
        Returns:
            bool: True jeśli usunięcie się powiodło, False w przeciwnym razie
        """
        try:
            # Usuń powiązane komentarze
            self.cursor.execute('''
                DELETE FROM trade_idea_comments
                WHERE trade_idea_id = ?
            ''', (idea_id,))
            
            # Usuń pomysł handlowy
            self.cursor.execute('''
                DELETE FROM trade_ideas_extended
                WHERE id = ?
            ''', (idea_id,))
            
            # Sprawdź, czy rekord został usunięty
            if self.cursor.rowcount == 0:
                logger.warning(f"Nie znaleziono pomysłu handlowego o ID: {idea_id}")
                return False
                
            self.conn.commit()
            logger.info(f"Usunięto pomysł handlowy o ID: {idea_id} wraz z powiązanymi komentarzami")
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Błąd podczas usuwania pomysłu handlowego: {e}")
            return False
            
    def get_trade_idea(self, idea_id: int) -> Optional[Dict[str, Any]]:
        """
        Pobiera szczegóły pomysłu handlowego.
        
        Args:
            idea_id: ID pomysłu handlowego
            
        Returns:
            Optional[Dict[str, Any]]: Dane pomysłu handlowego lub None, jeśli nie znaleziono
        """
        try:
            self.cursor.execute('''
                SELECT * FROM trade_ideas_extended
                WHERE id = ?
            ''', (idea_id,))
            
            result = self.cursor.fetchone()
            if not result:
                logger.warning(f"Nie znaleziono pomysłu handlowego o ID: {idea_id}")
                return None
                
            # Konwersja do słownika
            columns = [column[0] for column in self.cursor.description]
            trade_idea = {columns[i]: result[i] for i in range(len(columns))}
            
            return trade_idea
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania pomysłu handlowego: {e}")
            return None
            
    def get_trade_ideas_paginated(
        self,
        page: int = 1,
        items_per_page: int = 10,
        filters: Dict[str, Any] = None,
        sort_by: str = "created_at",
        sort_order: str = "DESC"
    ) -> Dict[str, Any]:
        """
        Pobiera stronicowaną listę pomysłów handlowych z możliwością filtrowania i sortowania.
        
        Args:
            page: Numer strony (domyślnie 1)
            items_per_page: Liczba elementów na stronę (domyślnie 10)
            filters: Filtry do zastosowania (np. {'status': 'PENDING', 'symbol': 'EURUSD'})
            sort_by: Pole do sortowania (domyślnie 'created_at')
            sort_order: Kolejność sortowania - ASC lub DESC (domyślnie DESC)
            
        Returns:
            Dict[str, Any]: Wynik zapytania zawierający listę pomysłów i metadane
        """
        try:
            # Walidacja parametrów
            if page < 1:
                page = 1
            if items_per_page < 1:
                items_per_page = 10
            if sort_order not in ["ASC", "DESC"]:
                sort_order = "DESC"
                
            # Przygotowanie klauzuli WHERE
            where_clause = ""
            params = []
            
            if filters:
                # Buduj klauzulę WHERE na podstawie filtrów
                conditions = []
                for key, value in filters.items():
                    if key == "date_range" and isinstance(value, dict):
                        # Obsługa filtrowania po zakresie dat
                        if "start" in value:
                            conditions.append("created_at >= ?")
                            params.append(value["start"])
                        if "end" in value:
                            conditions.append("created_at <= ?")
                            params.append(value["end"])
                    elif isinstance(value, list):
                        # Obsługa filtrowania po wielu wartościach (IN)
                        placeholders = ", ".join(["?" for _ in value])
                        conditions.append(f"{key} IN ({placeholders})")
                        params.extend(value)
                    else:
                        # Standardowe filtrowanie
                        conditions.append(f"{key} = ?")
                        params.append(value)
                
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)
            
            # Pobierz całkowitą liczbę pasujących rekordów
            count_query = f"SELECT COUNT(*) FROM trade_ideas_extended {where_clause}"
            self.cursor.execute(count_query, params)
            total_count = self.cursor.fetchone()[0]
            
            # Obliczanie offsetu dla stronicowania
            offset = (page - 1) * items_per_page
            
            # Pobierz dane z paginacją
            main_query = f'''
                SELECT * FROM trade_ideas_extended
                {where_clause}
                ORDER BY {sort_by} {sort_order}
                LIMIT ? OFFSET ?
            '''
            self.cursor.execute(main_query, params + [items_per_page, offset])
            
            # Konwersja wyników do listy słowników
            columns = [column[0] for column in self.cursor.description]
            results = []
            for row in self.cursor.fetchall():
                results.append({columns[i]: row[i] for i in range(len(columns))})
            
            # Obliczanie metadanych stronicowania
            total_pages = (total_count + items_per_page - 1) // items_per_page  # Zaokrąglanie w górę
            
            return {
                "success": True,
                "data": results,
                "pagination": {
                    "page": page,
                    "items_per_page": items_per_page,
                    "total_items": total_count,
                    "total_pages": total_pages
                }
            }
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania listy pomysłów handlowych: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "pagination": {
                    "page": page,
                    "items_per_page": items_per_page,
                    "total_items": 0,
                    "total_pages": 0
                }
            }
            
    def get_trade_ideas_stats(self) -> Dict[str, Any]:
        """
        Pobiera statystyki pomysłów handlowych.
        
        Returns:
            Dict[str, Any]: Statystyki pomysłów handlowych
        """
        try:
            # Statystyki według statusu
            self.cursor.execute('''
                SELECT status, COUNT(*) as count
                FROM trade_ideas_extended
                GROUP BY status
            ''')
            status_stats = {row[0]: row[1] for row in self.cursor.fetchall()}
            
            # Statystyki według symbolu
            self.cursor.execute('''
                SELECT symbol, COUNT(*) as count
                FROM trade_ideas_extended
                GROUP BY symbol
                ORDER BY count DESC
                LIMIT 10
            ''')
            symbol_stats = {row[0]: row[1] for row in self.cursor.fetchall()}
            
            # Statystyki według kierunku
            self.cursor.execute('''
                SELECT direction, COUNT(*) as count
                FROM trade_ideas_extended
                GROUP BY direction
            ''')
            direction_stats = {row[0]: row[1] for row in self.cursor.fetchall()}
            
            # Statystyki według source
            self.cursor.execute('''
                SELECT source, COUNT(*) as count
                FROM trade_ideas_extended
                WHERE source IS NOT NULL
                GROUP BY source
                ORDER BY count DESC
                LIMIT 10
            ''')
            source_stats = {row[0]: row[1] for row in self.cursor.fetchall()}
            
            # Pobierz całkowitą liczbę pomysłów
            self.cursor.execute('SELECT COUNT(*) FROM trade_ideas_extended')
            total_count = self.cursor.fetchone()[0]
            
            return {
                "success": True,
                "total_count": total_count,
                "by_status": status_stats,
                "by_symbol": symbol_stats,
                "by_direction": direction_stats,
                "by_source": source_stats
            }
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania statystyk pomysłów handlowych: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def get_trades_by_idea_id(self, idea_id: int) -> List[Dict[str, Any]]:
        """
        Pobiera listę transakcji związanych z danym pomysłem handlowym.
        
        Args:
            idea_id: ID pomysłu handlowego
            
        Returns:
            List[Dict[str, Any]]: Lista transakcji
        """
        try:
            # Sprawdź, czy tabela trades istnieje
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
            if not self.cursor.fetchone():
                logger.warning("Tabela 'trades' nie istnieje")
                return []
            
            # Pobierz transakcje powiązane z pomysłem handlowym
            # Zakładamy, że pole comment w tabeli trades może zawierać "LLM_TradeIdea_{idea_id}"
            self.cursor.execute('''
                SELECT * FROM trades
                WHERE comment LIKE ?
                ORDER BY open_time DESC
            ''', (f'%LLM_TradeIdea_{idea_id}%',))
            
            # Konwersja wyników do listy słowników
            columns = [column[0] for column in self.cursor.description]
            trades = []
            for row in self.cursor.fetchall():
                trades.append({columns[i]: row[i] for i in range(len(columns))})
            
            return trades
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania transakcji dla pomysłu handlowego: {e}")
            return []
            
    def add_trade_idea_comment(self, comment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dodaje komentarz do pomysłu handlowego.
        
        Args:
            comment_data: Dane komentarza (zawiera trade_idea_id, content, author, itd.)
            
        Returns:
            Dict[str, Any]: Wynik operacji z ID komentarza lub informacją o błędzie
        """
        if not self.connect():
            return {"success": False, "error": "Nie można połączyć z bazą danych"}
            
        try:
            # Sprawdź czy tabela istnieje, jeśli nie - utwórz
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS trade_idea_comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_idea_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    author TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (trade_idea_id) REFERENCES trade_ideas_extended (id)
                )
            ''')
            
            # Dodaj pole created_at jeśli nie ma
            now = datetime.datetime.now().isoformat()
            if "created_at" not in comment_data:
                comment_data["created_at"] = now
                
            # Odrzuć pola, które nie istnieją w tabeli
            self.cursor.execute("PRAGMA table_info(trade_idea_comments)")
            table_columns = [column[1] for column in self.cursor.fetchall()]
            
            # Przygotuj dane do wstawienia
            filtered_data = {k: v for k, v in comment_data.items() if k in table_columns}
            
            # Przygotuj zapytanie SQL
            columns = ", ".join(filtered_data.keys())
            placeholders = ", ".join(["?" for _ in filtered_data.keys()])
            values = tuple(filtered_data.values())
            
            self.cursor.execute(f'''
                INSERT INTO trade_idea_comments ({columns})
                VALUES ({placeholders})
            ''', values)
            
            # Pobierz ID nowego rekordu
            comment_id = self.cursor.lastrowid
            self.conn.commit()
            
            logger.info(f"Dodano nowy komentarz o ID: {comment_id} do pomysłu handlowego o ID: {comment_data['trade_idea_id']}")
            return {
                "success": True,
                "id": comment_id,
                "message": "Komentarz dodany pomyślnie"
            }
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Błąd podczas dodawania komentarza: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            self.disconnect()
            
    def mock_add_trade(self, trade_data: Dict[str, Any]) -> int:
        """
        Dodaje transakcję bezpośrednio do bazy danych - metoda pomocnicza dla testów.
        
        Args:
            trade_data: Dane transakcji
            
        Returns:
            int: ID nowej transakcji lub -1 w przypadku błędu
        """
        if not self.connect():
            return -1
            
        try:
            # Upewnij się, że tabela istnieje
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_idea_id INTEGER,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    entry_time TEXT NOT NULL,
                    exit_price REAL,
                    exit_time TEXT,
                    stop_loss REAL,
                    take_profit REAL,
                    profit_loss REAL,
                    status TEXT NOT NULL,
                    volume REAL NOT NULL,
                    comment TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (trade_idea_id) REFERENCES trade_ideas (id)
                )
            ''')
            
            # Przygotowanie podstawowych danych
            from datetime import datetime
            now = datetime.now().isoformat()
            if 'created_at' not in trade_data:
                trade_data['created_at'] = now
                
            if 'status' not in trade_data:
                trade_data['status'] = 'OPEN'
                
            # Tworzenie pól i wartości dla zapytania
            fields = []
            values = []
            
            for key, value in trade_data.items():
                fields.append(key)
                values.append(value)
                
            # Tworzenie zapytania SQL
            placeholders = ', '.join(['?' for _ in fields])
            fields_str = ', '.join(fields)
            
            query = f"INSERT INTO trades ({fields_str}) VALUES ({placeholders})"
            
            # Wykonanie zapytania
            self.cursor.execute(query, values)
            trade_id = self.cursor.lastrowid
            self.conn.commit()
            
            logger.info(f"Dodano transakcję testową z ID: {trade_id}")
            return trade_id
            
        except Exception as e:
            logger.error(f"Błąd podczas dodawania transakcji testowej: {e}")
            self.conn.rollback()
            return -1
        finally:
            self.disconnect()

    def update_trade(self, trade_id: int, update_data: Dict[str, Any]) -> bool:
        """
        Aktualizuje dane transakcji w bazie danych.
        
        Args:
            trade_id: ID transakcji do aktualizacji
            update_data: Słownik z danymi do aktualizacji
            
        Returns:
            bool: True jeśli aktualizacja się powiodła, False w przeciwnym razie
        """
        if not self.connect():
            return False
        
        try:
            # Przygotuj zapytanie SQL
            set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
            values = list(update_data.values())
            values.append(trade_id)  # Dla warunku WHERE
            
            self.cursor.execute(f'''
                UPDATE trades 
                SET {set_clause}
                WHERE id = ?
            ''', values)
            
            # Sprawdź, czy rekord został zaktualizowany
            if self.cursor.rowcount == 0:
                logger.warning(f"Nie znaleziono transakcji o ID: {trade_id}")
                return False
                
            self.conn.commit()
            logger.info(f"Zaktualizowano transakcję o ID: {trade_id}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas aktualizacji transakcji: {e}")
            self.conn.rollback()
            return False


if __name__ == "__main__":
    # Przykład użycia
    logging.basicConfig(level=logging.INFO,
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    db = DatabaseHandler()
    
    # Inicjalizacja bazy danych
    db.init_database()
    
    # Przykład zapisu analizy rynkowej
    analysis_data = {
        "trend": {"name": "bullish", "strength": 7, "volatility": "medium"},
        "support_resistance": {"support": [1.2500, 1.2450], "resistance": [1.2600, 1.2650]},
        "recommendation": "Oczekiwanie na wybicie z konsolidacji w górę"
    }
    
    analysis_id = db.insert_market_analysis("EURUSD", "H1", analysis_data)
    
    if analysis_id > 0:
        # Przykład zapisu idei handlowej
        trade_idea_id = db.insert_trade_idea(
            analysis_id=analysis_id,
            symbol="EURUSD",
            direction="buy",
            entry_price=1.2580,
            stop_loss=1.2520,
            take_profit=1.2680,
            risk_reward=1.67
        )
        
        # Przykład zapisu transakcji
        if trade_idea_id > 0:
            trade_id = db.insert_trade(
                trade_idea_id=trade_idea_id,
                symbol="EURUSD",
                direction="buy",
                entry_price=1.2582,
                entry_time=datetime.datetime.now().isoformat(),
                stop_loss=1.2520,
                take_profit=1.2680,
                volume=0.1,
                comment="Test transakcji"
            )
    
    # Pobranie ostatnich analiz
    analyses = db.get_latest_analyses(limit=5)
    print(f"Liczba pobranych analiz: {len(analyses)}")
    
    # Statystyki
    stats = db.get_statistics()
    print(f"Statystyki: {stats}") 
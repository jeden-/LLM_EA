#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt testowy do walidacji działania modułu Database.
Pozwala na weryfikację poprawności działania klasy DatabaseHandler.
"""

import os
import sys
import logging
import datetime
import sqlite3
from pathlib import Path

# Dodajemy główny katalog projektu do ścieżki importów
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import modułu Database
from Database.database import DatabaseHandler

# Konfiguracja loggera
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestDatabaseHandler(DatabaseHandler):
    """
    Rozszerzona klasa DatabaseHandler do testów - utrzymuje połączenie dla bazy w pamięci.
    """
    
    def __init__(self, db_path=":memory:", auto_init=True):
        """
        Inicjalizacja handlera testowej bazy danych.
        
        Args:
            db_path: Ścieżka do pliku bazy danych (domyślnie: ":memory:")
            auto_init: Czy automatycznie inicjalizować bazę danych
        """
        super().__init__(db_path=db_path, auto_init=False)
        
        # Utrzymujemy stałe połączenie dla bazy w pamięci
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        # Inicjalizacja bazy danych
        if auto_init:
            self.init_database_internal()
    
    def connect(self) -> bool:
        """
        W testach nie łączymy się ponownie, bo utrzymujemy stałe połączenie.
        
        Returns:
            True, połączenie jest już nawiązane
        """
        return True
    
    def disconnect(self):
        """W testach nie rozłączamy się, aby utrzymać bazę w pamięci."""
        pass
    
    def init_database_internal(self) -> bool:
        """
        Wewnętrzna metoda inicjalizacji struktury bazy danych (bez connect/disconnect).
        
        Returns:
            True, jeśli inicjalizacja przebiegła pomyślnie, False w przeciwnym razie
        """
        try:
            # Tabela z analizami rynkowymi
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp TEXT NOT NULL,
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
                timestamp TEXT NOT NULL,
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
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            self.conn.commit()
            logger.info("Struktura bazy danych została zainicjalizowana")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas inicjalizacji bazy danych: {e}")
            self.conn.rollback()
            return False
    
    def init_database(self) -> bool:
        """
        Przesłania metodę bazową, używając wewnętrznej metody inicjalizacji.
        
        Returns:
            True, jeśli inicjalizacja przebiegła pomyślnie, False w przeciwnym razie
        """
        return self.init_database_internal()
    
    def __del__(self):
        """
        Destruktor - zamyka połączenie z bazą danych.
        """
        if self.conn:
            self.conn.close()

def test_database_init():
    """Test inicjalizacji bazy danych."""
    print("  - Testowanie inicjalizacji bazy danych")
    db_handler = TestDatabaseHandler()
    result = db_handler.init_database_internal()
    print(f"  - Inicjalizacja bazy danych: {result}")
    return result

def test_market_analysis():
    """Test zapisywania i odczytu analizy rynkowej."""
    print("  - Testowanie zapisywania i odczytu analizy rynkowej")
    db_handler = TestDatabaseHandler()
    db_handler.init_database_internal()
    
    # Dane testowe
    symbol = "EURUSD"
    timeframe = "H1"
    analysis_data = {
        "trend": "bullish",
        "trend_strength": 7,
        "support_levels": [1.0800, 1.0750],
        "resistance_levels": [1.0900, 1.0950],
        "volatility": "medium",
        "momentum": "increasing",
        "timestamp": "2023-10-15 12:00:00"
    }
    
    # Zapisz analizę
    insert_success = db_handler.insert_market_analysis(symbol, timeframe, analysis_data)
    print(f"  - Zapisanie analizy: {insert_success}")
    
    # Pobierz analizę
    analyses = db_handler.get_latest_analyses(symbol, limit=1)
    print(f"  - Pobrano analiz: {len(analyses)}")
    
    success = insert_success and len(analyses) > 0
    
    if success:
        analysis = analyses[0]
        print(f"  - Pobrano analizę: {analysis['symbol']} {analysis['timestamp']} ({analysis['analysis_data']['trend']})")
    
    return success

def test_trade_idea():
    """Test zapisywania i odczytu pomysłów handlowych."""
    print("  - Testowanie zapisywania i odczytu pomysłów handlowych")
    db_handler = TestDatabaseHandler()
    db_handler.init_database_internal()
    
    # Najpierw dodajemy analizę, żeby mieć analysis_id
    symbol = "EURUSD"
    timeframe = "H1"
    analysis_data = {
        "trend": "bullish",
        "trend_strength": 7,
        "support_levels": [1.0800, 1.0750],
        "resistance_levels": [1.0900, 1.0950],
        "volatility": "medium",
        "momentum": "increasing",
        "timestamp": "2023-10-15 12:00:00"
    }
    
    analysis_id = db_handler.insert_market_analysis(symbol, timeframe, analysis_data)
    
    # Dane testowe dla pomysłu handlowego
    direction = "buy"
    entry_price = 1.0850
    stop_loss = 1.0800
    take_profit = 1.0950
    risk_reward = 2.0
    
    # Zapisz pomysł handlowy
    insert_success = db_handler.insert_trade_idea(analysis_id, symbol, direction, entry_price, stop_loss, take_profit, risk_reward)
    print(f"  - Zapisanie pomysłu handlowego: {insert_success}")
    
    # Pobierz pomysły handlowe
    ideas = db_handler.get_trade_ideas("EURUSD", limit=1)
    print(f"  - Pobrano pomysłów handlowych: {len(ideas)}")
    
    success = insert_success > 0 and len(ideas) > 0
    
    if success:
        idea = ideas[0]
        print(f"  - Pobrano pomysł: {idea['symbol']} {idea['timestamp']} ({idea['direction']})")
    
    return success

def test_trade():
    """Test zapisywania i odczytu transakcji."""
    print("  - Testowanie zapisywania i odczytu transakcji")
    db_handler = TestDatabaseHandler()
    db_handler.init_database_internal()
    
    # Najpierw dodajemy analizę i pomysł handlowy
    symbol = "EURUSD"
    timeframe = "H1"
    analysis_data = {
        "trend": "bullish",
        "trend_strength": 7,
        "support_levels": [1.0800, 1.0750],
        "resistance_levels": [1.0900, 1.0950],
        "volatility": "medium",
        "momentum": "increasing"
    }
    
    analysis_id = db_handler.insert_market_analysis(symbol, timeframe, analysis_data)
    
    # Dodajemy pomysł handlowy
    direction = "buy"
    entry_price = 1.0850
    stop_loss = 1.0800
    take_profit = 1.0950
    risk_reward = 2.0
    
    trade_idea_id = db_handler.insert_trade_idea(analysis_id, symbol, direction, entry_price, stop_loss, take_profit, risk_reward)
    
    # Dane testowe dla transakcji
    entry_time = "2023-10-15 12:00:00"
    volume = 0.1
    comment = "Test transaction"
    
    # Zapisz transakcję
    insert_success = db_handler.insert_trade(trade_idea_id, symbol, direction, entry_price, entry_time, stop_loss, take_profit, volume, comment)
    print(f"  - Zapisanie transakcji: {insert_success}")
    
    # Pobierz transakcje
    trades = db_handler.get_trades("EURUSD", limit=1)
    print(f"  - Pobrano transakcji: {len(trades)}")
    
    success = insert_success > 0 and len(trades) > 0
    
    if success:
        trade = trades[0]
        print(f"  - Pobrano transakcję: {trade['id']} {trade['symbol']} ({trade['status']})")
    
    return success

def test_logs():
    """Test zapisywania i odczytu logów systemowych."""
    print("  - Testowanie zapisywania i odczytu logów")
    db_handler = TestDatabaseHandler()
    db_handler.init_database_internal()
    
    # Dane testowe
    level = "INFO"
    module = "LLM_Engine"
    message = "Test message"
    
    # Zapisz log
    insert_success = db_handler.insert_log(level, module, message)
    print(f"  - Zapisanie logu: {insert_success}")
    
    # Pobierz logi
    logs = db_handler.get_logs(level="INFO", module="LLM_Engine", limit=1)
    print(f"  - Pobrano logów: {len(logs)}")
    
    success = insert_success > 0 and len(logs) > 0
    
    if success:
        log = logs[0]
        print(f"  - Pobrano log: {log['timestamp']} {log['level']} ({log['module']})")
    
    return success

def test_statistics():
    """Test pobierania statystyk handlowych."""
    print("  - Testowanie pobierania statystyk")
    db_handler = TestDatabaseHandler()
    db_handler.init_database_internal()
    
    # Najpierw dodajemy kilka analiz i pomysłów handlowych
    symbol = "EURUSD"
    timeframe = "H1"
    analysis_data = {
        "trend": "bullish",
        "trend_strength": 7,
        "support_levels": [1.0800, 1.0750],
        "resistance_levels": [1.0900, 1.0950],
        "volatility": "medium",
        "momentum": "increasing"
    }
    
    analysis_id = db_handler.insert_market_analysis(symbol, timeframe, analysis_data)
    
    # Dodajemy pomysł handlowy
    direction = "buy"
    entry_price = 1.0850
    stop_loss = 1.0800
    take_profit = 1.0950
    risk_reward = 2.0
    
    trade_idea_id = db_handler.insert_trade_idea(analysis_id, symbol, direction, entry_price, stop_loss, take_profit, risk_reward)
    
    # Dane transakcji
    trades_data = [
        {
            "trade_idea_id": trade_idea_id,
            "symbol": "EURUSD",
            "direction": "buy",
            "entry_price": 1.0800,
            "entry_time": "2023-10-01 10:00:00",
            "stop_loss": 1.0750,
            "take_profit": 1.0900,
            "volume": 0.1,
            "comment": "Test trade 1"
        },
        {
            "trade_idea_id": trade_idea_id,
            "symbol": "EURUSD",
            "direction": "sell",
            "entry_price": 1.0850,
            "entry_time": "2023-10-02 10:00:00",
            "stop_loss": 1.0900,
            "take_profit": 1.0750,
            "volume": 0.1,
            "comment": "Test trade 2"
        },
        {
            "trade_idea_id": trade_idea_id,
            "symbol": "EURUSD",
            "direction": "buy",
            "entry_price": 1.0750,
            "entry_time": "2023-10-03 10:00:00",
            "stop_loss": 1.0700,
            "take_profit": 1.0850,
            "volume": 0.1,
            "comment": "Test trade 3"
        }
    ]
    
    # Zapisz wszystkie transakcje
    trade_ids = []
    for trade_data in trades_data:
        trade_id = db_handler.insert_trade(
            trade_data["trade_idea_id"], 
            trade_data["symbol"], 
            trade_data["direction"],
            trade_data["entry_price"], 
            trade_data["entry_time"], 
            trade_data["stop_loss"],
            trade_data["take_profit"], 
            trade_data["volume"], 
            trade_data["comment"]
        )
        trade_ids.append(trade_id)
    
    # Aktualizujemy transakcje, aby miały status zamknięty
    db_handler.update_trade(trade_ids[0], 1.0850, "2023-10-01 14:00:00", 50.0, "closed")
    db_handler.update_trade(trade_ids[1], 1.0800, "2023-10-02 16:00:00", 50.0, "closed")
    db_handler.update_trade(trade_ids[2], 1.0700, "2023-10-03 12:00:00", -50.0, "closed")
    
    print("  - Zapisano testowe transakcje do statystyk")
    
    # Pobierz statystyki
    stats = db_handler.get_statistics()
    
    if stats:
        print(f"  - Statystyki: Zyskowność: {stats.get('win_rate', 'N/A')}%, Średni zysk: {stats.get('avg_profit_loss', 'N/A')}")
    
    # Sprawdź, czy statystyki zawierają dane
    success = stats is not None
    
    return success

def run_all_tests():
    """Uruchomienie wszystkich testów."""
    print("\n===== TESTY MODUŁU DATABASE =====\n")
    
    tests = [
        test_database_init,
        test_market_analysis,
        test_trade_idea,
        test_trade,
        test_logs,
        test_statistics
    ]
    
    success_count = 0
    total_count = len(tests)
    
    for test_func in tests:
        print(f"\n>> Uruchamianie testu: {test_func.__name__}")
        try:
            result = test_func()
            print(f"   Wynik: {'POMYŚLNY ✅' if result else 'NIEPOMYŚLNY ❌'}")
            if result:
                success_count += 1
        except Exception as e:
            print(f"   Nieoczekiwany błąd: {str(e)}")
            logger.error(f"❌ Nieoczekiwany błąd w teście {test_func.__name__}: {str(e)}")
    
    print(f"\n===== PODSUMOWANIE TESTÓW =====")
    print(f"Przeprowadzono testów: {total_count}")
    print(f"Pomyślnych testów: {success_count}")
    print(f"Niepomyślnych testów: {total_count - success_count}")
    print(f"Wynik: {'✅ POMYŚLNY' if success_count == total_count else '❌ NIEPOMYŚLNY'}")
    
    return success_count == total_count

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 
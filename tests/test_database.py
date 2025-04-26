#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt testowy do walidacji działania modułu Database.
Pozwala na weryfikację poprawności działania klasy DatabaseHandler.
"""

import os
import sys
import logging
from datetime import datetime
import sqlite3
from pathlib import Path
import unittest

# Dodajemy główny katalog projektu do ścieżki importów
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import modułu Database
from Database.database import DatabaseHandler

# Konfiguracja loggera
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestDatabaseHandler(unittest.TestCase):
    """Klasa testowa dla obsługi bazy danych."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Używamy bazy danych w pamięci dla testów
        self.db = DatabaseHandler(":memory:", auto_init=False)
        self.assertTrue(self.db.connect())
        self.assertTrue(self.db.init_database())
        # Nie rozłączamy się po inicjalizacji

    def tearDown(self):
        """Sprzątanie po testach."""
        if hasattr(self, 'db'):
            self.db.disconnect()

    def test_database_structure(self):
        """Test sprawdzający czy wszystkie wymagane tabele zostały utworzone."""
        required_tables = [
            'market_analyses',
            'trade_ideas',
            'trades',
            'system_logs'
        ]
        
        self.db.connect()
        self.cursor = self.db.cursor
        
        # Pobierz listę wszystkich tabel
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in self.cursor.fetchall()]
        
        # Sprawdź czy wszystkie wymagane tabele istnieją
        for table in required_tables:
            self.assertIn(table, existing_tables, f"Brak wymaganej tabeli: {table}")
            
        # Sprawdź strukturę tabel
        self.cursor.execute("PRAGMA table_info(market_analyses)")
        columns = {row[1] for row in self.cursor.fetchall()}
        required_columns = {'id', 'symbol', 'timeframe', 'timestamp', 'analysis_data', 'created_at'}
        self.assertTrue(required_columns.issubset(columns), 
                       f"Brak wymaganych kolumn w tabeli market_analyses: {required_columns - columns}")

    def test_connection(self):
        """Test połączenia z bazą danych."""
        self.assertTrue(self.db.connect())
        self.assertIsNotNone(self.db.conn)
        self.assertIsNotNone(self.db.cursor)

    def test_market_analysis(self):
        """Test zapisu i odczytu analizy rynkowej."""
        # Zapis analizy
        analysis_id = self.db.insert_market_analysis(
            symbol='EURUSD',
            timeframe='H1',
            analysis_data={
                'trend': 'bullish',
                'strength': 0.8
            }
        )
        self.assertGreater(analysis_id, 0)
        
        # Odczyt analizy
        results = self.db.get_latest_analyses(symbol='EURUSD', limit=1)
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result['symbol'], 'EURUSD')
        self.assertEqual(result['analysis_data']['trend'], 'bullish')
        self.assertEqual(result['analysis_data']['strength'], 0.8)

    def test_trade_idea(self):
        """Test zapisu i odczytu pomysłu na handel."""
        # Najpierw zapisujemy analizę
        analysis_id = self.db.insert_market_analysis(
            symbol='EURUSD',
            timeframe='H1',
            analysis_data={'trend': 'bullish'}
        )
        
        # Zapis pomysłu handlowego
        idea_id = self.db.insert_trade_idea(
            analysis_id=analysis_id,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            risk_reward=2.0
        )
        self.assertGreater(idea_id, 0)
        
        # Odczyt pomysłu
        results = self.db.get_trade_ideas(symbol='EURUSD')
        self.assertGreater(len(results), 0)
        result = results[0]
        self.assertEqual(result['direction'], 'buy')
        self.assertEqual(result['entry_price'], 1.1000)

    def test_trade(self):
        """Test zapisu i odczytu transakcji."""
        # Najpierw zapisujemy analizę i pomysł handlowy
        analysis_id = self.db.insert_market_analysis(
            symbol='EURUSD',
            timeframe='H1',
            analysis_data={'trend': 'bullish'}
        )
        idea_id = self.db.insert_trade_idea(
            analysis_id=analysis_id,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            risk_reward=2.0
        )
        
        # Zapis transakcji
        trade_id = self.db.insert_trade(
            trade_idea_id=idea_id,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.1000,
            entry_time=datetime.now().isoformat(),
            stop_loss=1.0950,
            take_profit=1.1100,
            volume=0.1,
            comment='Test trade'
        )
        self.assertGreater(trade_id, 0)
        
        # Odczyt transakcji
        results = self.db.get_trades(symbol='EURUSD')
        self.assertGreater(len(results), 0)
        result = results[0]
        self.assertEqual(result['direction'], 'buy')
        self.assertEqual(result['entry_price'], 1.1000)

    def test_logs(self):
        """Test zapisu i odczytu logów."""
        # Zapis logu
        log_id = self.db.insert_log(
            level='INFO',
            module='test',
            message='Test log'
        )
        self.assertGreater(log_id, 0)
        
        # Odczyt logów
        results = self.db.get_logs(limit=1)
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result['level'], 'INFO')
        self.assertEqual(result['module'], 'test')
        self.assertEqual(result['message'], 'Test log')

    def test_statistics(self):
        """Test pobierania statystyk."""
        # Najpierw dodajemy kilka transakcji
        analysis_id = self.db.insert_market_analysis(
            symbol='EURUSD',
            timeframe='H1',
            analysis_data={'trend': 'bullish'}
        )
        idea_id = self.db.insert_trade_idea(
            analysis_id=analysis_id,
            symbol='EURUSD',
            direction='buy',
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            risk_reward=2.0
        )

        # Dodajemy kilka transakcji
        for i in range(3):
            self.db.insert_trade(
                trade_idea_id=idea_id,
                symbol='EURUSD',
                direction='buy',
                entry_price=1.1000,
                entry_time=datetime.now().isoformat(),
                stop_loss=1.0950,
                take_profit=1.1100,
                volume=0.1,
                comment=f'Test trade {i}'
            )

        # Pobieramy statystyki
        stats = self.db.get_statistics()
        self.assertIsInstance(stats, dict)
        self.assertIn('total_trades', stats)
        self.assertEqual(stats['total_trades'], 3)

    def test_error_handling(self):
        """Test obsługi błędów."""
        # Test błędu połączenia
        invalid_db = DatabaseHandler("invalid/path/db.sqlite", auto_init=False)
        self.assertFalse(invalid_db.connect())
        
        # Test błędu wstawiania nieprawidłowych danych
        with self.assertRaises(sqlite3.Error):
            self.db.cursor.execute("INSERT INTO invalid_table (col) VALUES (?)", (1,))
            
        # Test błędu przy nieprawidłowym typie danych
        with self.assertRaises(TypeError):
            self.db.insert_market_analysis(
                symbol=123,  # powinien być string
                timeframe="H1",
                analysis_data={"trend": "bullish"}
            )
            
        # Test błędu przy braku wymaganych danych
        with self.assertRaises(sqlite3.Error):
            self.db.cursor.execute("INSERT INTO market_analyses (symbol) VALUES (?)", ("EURUSD",))
            
        # Test rollbacku przy błędzie
        self.db.connect()
        try:
            self.db.cursor.execute("INSERT INTO invalid_table VALUES (1)")
        except sqlite3.Error:
            pass
        # Sprawdzamy czy połączenie jest nadal aktywne
        self.assertIsNotNone(self.db.conn)

    def test_edge_cases(self):
        """Test przypadków skrajnych."""
        # Test pustych wartości
        analysis_id = self.db.insert_market_analysis(
            symbol="",
            timeframe="",
            analysis_data={}
        )
        self.assertGreater(analysis_id, 0)
        
        # Test bardzo długich wartości
        long_string = "x" * 1000
        log_id = self.db.insert_log(
            level="INFO",
            module="test",
            message=long_string
        )
        self.assertGreater(log_id, 0)
        
        # Test specjalnych znaków w danych
        special_chars = "!@#$%^&*()_+{}[]|\\:;\"'<>,.?/~`"
        analysis_id = self.db.insert_market_analysis(
            symbol="EURUSD",
            timeframe="H1",
            analysis_data={"comment": special_chars}
        )
        self.assertGreater(analysis_id, 0)
        
        # Test wartości granicznych
        idea_id = self.db.insert_trade_idea(
            analysis_id=analysis_id,
            symbol="EURUSD",
            direction="buy",
            entry_price=sys.float_info.max,
            stop_loss=sys.float_info.min,
            take_profit=sys.float_info.max,
            risk_reward=sys.float_info.max
        )
        self.assertGreater(idea_id, 0)

    def test_concurrent_access(self):
        """Test współbieżnego dostępu do bazy danych."""
        import threading
        import queue
        
        results = queue.Queue()
        errors = queue.Queue()
        
        def worker(worker_id):
            try:
                # Każdy wątek tworzy własne połączenie
                db = DatabaseHandler(":memory:", auto_init=True)
                db.connect()
                
                # Wykonaj operacje na bazie
                analysis_id = db.insert_market_analysis(
                    symbol=f"EURUSD_{worker_id}",
                    timeframe="H1",
                    analysis_data={"worker": worker_id}
                )
                
                idea_id = db.insert_trade_idea(
                    analysis_id=analysis_id,
                    symbol=f"EURUSD_{worker_id}",
                    direction="buy",
                    entry_price=1.1000,
                    stop_loss=1.0950,
                    take_profit=1.1100,
                    risk_reward=2.0
                )
                
                results.put((worker_id, analysis_id, idea_id))
                db.disconnect()
                
            except Exception as e:
                errors.put((worker_id, str(e)))
        
        # Uruchom 5 wątków jednocześnie
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        # Poczekaj na zakończenie wszystkich wątków
        for t in threads:
            t.join()
        
        # Sprawdź czy nie było błędów
        self.assertTrue(errors.empty(), f"Wystąpiły błędy: {list(errors.queue)}")
        
        # Sprawdź czy wszystkie operacje się powiodły
        self.assertEqual(results.qsize(), 5, "Nie wszystkie operacje zostały wykonane")

    def test_update_trade_success(self):
        """Test aktualizacji danych transakcji."""
        # Najpierw dodaj transakcję
        trade_id = self.db.insert_trade(
            trade_idea_id=None,
            symbol='EURUSD',
            direction='BUY',
            entry_price=1.1000,
            entry_time=datetime.now().isoformat(),
            stop_loss=1.0900,
            take_profit=1.1100,
            volume=0.1,
            comment='Test trade'
        )
        self.assertIsNotNone(trade_id)
        
        # Przygotuj dane do aktualizacji
        update_data = {
            'status': 'CLOSED',
            'exit_price': 1.1050,
            'profit_loss': 50
        }
        
        # Wykonaj aktualizację
        result = self.db.update_trade(trade_id, update_data)
        self.assertTrue(result)
        
        # Sprawdź, czy dane zostały zaktualizowane
        trades = self.db.get_trades()
        self.assertEqual(len(trades), 1)
        updated_trade = trades[0]
        self.assertEqual(updated_trade['status'], 'CLOSED')
        self.assertEqual(updated_trade['exit_price'], 1.1050)
        self.assertEqual(updated_trade['profit_loss'], 50)

    def test_update_trade_nonexistent(self):
        """Test aktualizacji nieistniejącej transakcji."""
        update_data = {
            'status': 'CLOSED',
            'exit_price': 1.1050
        }
        result = self.db.update_trade(999, update_data)
        self.assertFalse(result)

    def test_update_trade_invalid_data(self):
        """Test aktualizacji z nieprawidłowymi danymi."""
        # Najpierw dodaj transakcję
        trade_id = self.db.insert_trade(
            trade_idea_id=None,
            symbol='EURUSD',
            direction='BUY',
            entry_price=1.1000,
            entry_time=datetime.now().isoformat(),
            stop_loss=1.0900,
            take_profit=1.1100,
            volume=0.1,
            comment='Test trade'
        )
        self.assertIsNotNone(trade_id)
        
        # Próba aktualizacji z nieprawidłowymi danymi
        update_data = {
            'nonexistent_column': 'value'  # Kolumna nie istnieje w tabeli
        }
        result = self.db.update_trade(trade_id, update_data)
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main() 
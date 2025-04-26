"""
Moduł mock_database - zawiera implementację MockDatabaseHandler do testów.
Klasa ta jest używana w testach do imitowania DatabaseHandler w pamięci.
"""

import sqlite3
import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class MockDatabaseHandler:
    """
    Klasa MockDatabaseHandler - implementacja handlera bazy danych do testów.
    Używa bazy danych SQLite w pamięci i imituje funkcjonalność DatabaseHandler.
    """
    
    def __init__(self):
        """
        Inicjalizacja mock handlera bazy danych w pamięci.
        """
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        # Inicjalizacja bazy danych
        self.init_database()
    
    def connect(self) -> bool:
        """
        W mocku nie musimy łączyć się ponownie, baza jest zawsze połączona.
        
        Returns:
            True - połączenie jest już nawiązane
        """
        return True
    
    def disconnect(self):
        """
        W mocku nie rozłączamy się.
        """
        pass
    
    def init_database(self) -> bool:
        """
        Inicjalizacja struktury bazy danych w pamięci.
        
        Returns:
            True, jeśli inicjalizacja przebiegła pomyślnie
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
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Tabela z rozszerzonymi pomysłami handlowymi
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
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
            logger.info("Struktura bazy danych mock została zainicjalizowana")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas inicjalizacji bazy danych mock: {e}")
            return False
    
    def clear_database(self) -> bool:
        """
        Czyści zawartość bazy danych.
        
        Returns:
            True, jeśli operacja przebiegła pomyślnie, False w przeciwnym razie
        """
        try:
            # Usunięcie danych z tabel
            tables = ['trades', 'trade_ideas', 'market_analyses', 'system_logs', 'trade_ideas_extended']
            for table in tables:
                self.cursor.execute(f"DELETE FROM {table}")
            
            self.conn.commit()
            logger.warning("Zawartość bazy danych mock została wyczyszczona")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas czyszczenia bazy danych mock: {e}")
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
        try:
            timestamp = datetime.now().isoformat()
            
            # Konwersja danych analizy do formatu JSON
            analysis_json = json.dumps(analysis_data, ensure_ascii=False)
            
            # Wstawienie rekordu
            self.cursor.execute('''
            INSERT INTO market_analyses (symbol, timeframe, timestamp, analysis_data)
            VALUES (?, ?, ?, ?)
            ''', (symbol, timeframe, timestamp, analysis_json))
            
            self.conn.commit()
            record_id = self.cursor.lastrowid
            
            logger.info(f"Zapisano analizę rynkową dla {symbol} ({timeframe}), ID: {record_id}")
            return record_id
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas zapisywania analizy rynkowej: {e}")
            return -1
    
    def insert_trade_idea(self, analysis_id: int, symbol: str, direction: str,
                    entry_price: float, stop_loss: float, take_profit: float,
                    risk_reward: float) -> int:
        """
        Zapisanie pomysłu handlowego do bazy danych.
        
        Args:
            analysis_id: ID analizy rynkowej
            symbol: Symbol instrumentu
            direction: Kierunek transakcji (BUY/SELL)
            entry_price: Cena wejścia
            stop_loss: Poziom stop loss
            take_profit: Poziom take profit
            risk_reward: Stosunek zysk/ryzyko
            
        Returns:
            ID zapisanego rekordu lub -1 w przypadku błędu
        """
        try:
            timestamp = datetime.now().isoformat()
            
            # Wstawienie rekordu
            self.cursor.execute('''
            INSERT INTO trade_ideas (analysis_id, symbol, direction, entry_price, stop_loss, take_profit, risk_reward, timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (analysis_id, symbol, direction, entry_price, stop_loss, take_profit, risk_reward, timestamp, 'PENDING'))
            
            self.conn.commit()
            record_id = self.cursor.lastrowid
            
            # Dodaj również do rozszerzonej tabeli
            self.cursor.execute('''
            INSERT INTO trade_ideas_extended (symbol, direction, entry_price, stop_loss, take_profit, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, direction, entry_price, stop_loss, take_profit, 'PENDING', timestamp, timestamp))
            
            self.conn.commit()
            
            return record_id
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas zapisywania pomysłu handlowego: {e}")
            return -1
    
    def get_latest_analyses(self, symbol: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Pobranie najnowszych analiz rynkowych.
        
        Args:
            symbol: Symbol instrumentu (opcjonalnie)
            limit: Maksymalna liczba rekordów
            
        Returns:
            Lista słowników z danymi analiz
        """
        try:
            query = '''
            SELECT id, symbol, timeframe, timestamp, analysis_data, created_at
            FROM market_analyses
            '''
            params = []
            
            # Dodanie filtrów
            if symbol:
                query += " WHERE symbol = ?"
                params.append(symbol)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            self.cursor.execute(query, params)
            
            # Konwersja wyników do listy słowników
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(row))
            
            return results
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas pobierania analiz rynkowych: {e}")
            return []
    
    def add_trade_idea(self, trade_idea_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dodaje nowy pomysł handlowy do bazy danych.
        
        Args:
            trade_idea_data: Dane nowego pomysłu handlowego
            
        Returns:
            Dict[str, Any]: Wynik operacji z ID nowego pomysłu lub błędem
        """
        try:
            # Dodaj pole created_at i updated_at jeśli nie ma
            now = datetime.now().isoformat()
            if "created_at" not in trade_idea_data:
                trade_idea_data["created_at"] = now
            if "updated_at" not in trade_idea_data:
                trade_idea_data["updated_at"] = now
            if "status" not in trade_idea_data:
                trade_idea_data["status"] = "PENDING"
                
            # Przygotuj dane do wstawienia
            fields = [
                "symbol", "direction", "entry_price", "stop_loss", "take_profit",
                "status", "created_at", "updated_at", "timeframe"
            ]
            
            filtered_data = {}
            for field in fields:
                if field in trade_idea_data:
                    filtered_data[field] = trade_idea_data[field]
            
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
            logger.error(f"Błąd podczas dodawania pomysłu handlowego: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_trade_ideas(self, symbol: Optional[str] = None, status: Optional[str] = None, 
                 limit: int = 10) -> List[Dict[str, Any]]:
        """
        Pobranie pomysłów handlowych.
        
        Args:
            symbol: Symbol instrumentu (opcjonalnie)
            status: Status pomysłu (opcjonalnie)
            limit: Maksymalna liczba rekordów
            
        Returns:
            Lista słowników z danymi pomysłów handlowych
        """
        try:
            query = '''
            SELECT *
            FROM trade_ideas_extended
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
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            self.cursor.execute(query, params)
            
            # Konwersja wyników do listy słowników
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(row))
            
            return results
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas pobierania pomysłów handlowych: {e}")
            return []
    
    def get_trade_idea(self, idea_id: int) -> Optional[Dict[str, Any]]:
        """
        Pobranie szczegółów pojedynczego pomysłu handlowego po ID.
        
        Args:
            idea_id: ID pomysłu handlowego
            
        Returns:
            Słownik z danymi pomysłu handlowego lub None, jeśli nie znaleziono
        """
        try:
            self.cursor.execute('''
            SELECT * FROM trade_ideas_extended
            WHERE id = ?
            ''', (idea_id,))
            
            row = self.cursor.fetchone()
            if not row:
                return None
                
            return dict(row)
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas pobierania pomysłu handlowego: {e}")
            return None
    
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
        try:
            query = '''
            SELECT id, trade_idea_id, symbol, direction, entry_price, entry_time,
                   exit_price, exit_time, stop_loss, take_profit, profit_loss,
                   status, volume, comment, created_at
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
            
    def get_trade_ideas_paginated(
        self,
        page: int = 1,
        per_page: int = 10,
        filters: Dict[str, Any] = None,
        sort_by: str = "created_at",
        order: str = "DESC"
    ) -> tuple[int, List[Dict[str, Any]]]:
        """
        Pobranie pomysłów handlowych z paginacją.
        
        Args:
            page: Numer strony
            per_page: Liczba elementów na stronę
            filters: Filtry do zastosowania
            sort_by: Pole, po którym sortować
            order: Kierunek sortowania (ASC lub DESC)
            
        Returns:
            Krotka (całkowita liczba rekordów, lista słowników z danymi pomysłów)
        """
        try:
            # Filtry
            filters = filters or {}
            conditions = []
            params = []
            
            for key, value in filters.items():
                if value:
                    conditions.append(f"{key} = ?")
                    params.append(value)
                    
            # Zapytanie zliczające rekordy
            count_query = "SELECT COUNT(*) as count FROM trade_ideas_extended"
            if conditions:
                count_query += " WHERE " + " AND ".join(conditions)
                
            self.cursor.execute(count_query, params)
            total_count = self.cursor.fetchone()["count"]
            
            # Jeśli nie ma wyników, zwróć pustą listę
            if total_count == 0:
                return 0, []
                
            # Obliczenie offsetu
            offset = (page - 1) * per_page
            
            # Zapytanie główne
            query = "SELECT * FROM trade_ideas_extended"
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                
            # Przyjmowanie argumentu sort_order jako order dla kompatybilności z Dashboard
            sort_order = order.upper()
            
            query += f" ORDER BY {sort_by} {sort_order} LIMIT ? OFFSET ?"
            self.cursor.execute(query, params + [per_page, offset])
            
            # Konwersja wyników do listy słowników
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(row))
                
            return total_count, results
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas pobierania pomysłów handlowych: {e}")
            return 0, []
            
    def get_trades_by_idea_id(self, idea_id: int) -> List[Dict[str, Any]]:
        """
        Pobranie transakcji dla danego pomysłu handlowego.
        
        Args:
            idea_id: ID pomysłu handlowego
            
        Returns:
            Lista słowników z danymi transakcji
        """
        try:
            self.cursor.execute('''
            SELECT * FROM trades
            WHERE trade_idea_id = ?
            ORDER BY entry_time DESC
            ''', (idea_id,))
            
            # Konwersja wyników do listy słowników
            results = []
            for row in self.cursor.fetchall():
                results.append(dict(row))
                
            return results
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas pobierania transakcji dla pomysłu: {e}")
            return []
            
    def get_trade_ideas_stats(self) -> Dict[str, Any]:
        """
        Pobranie statystyk pomysłów handlowych.
        
        Returns:
            Słownik ze statystykami
        """
        try:
            # Pobierz liczbę pomysłów wg statusu
            self.cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM trade_ideas_extended
            GROUP BY status
            ''')
            
            status_counts = {}
            for row in self.cursor.fetchall():
                status_counts[row['status']] = row['count']
                
            # Pobierz liczbę pomysłów wg symbolu
            self.cursor.execute('''
            SELECT symbol, COUNT(*) as count
            FROM trade_ideas_extended
            GROUP BY symbol
            ''')
            
            symbol_counts = {}
            for row in self.cursor.fetchall():
                symbol_counts[row['symbol']] = row['count']
                
            # Pobierz liczbę pomysłów wg kierunku
            self.cursor.execute('''
            SELECT direction, COUNT(*) as count
            FROM trade_ideas_extended
            GROUP BY direction
            ''')
            
            direction_counts = {}
            for row in self.cursor.fetchall():
                direction_counts[row['direction']] = row['count']
                
            # Całkowita liczba pomysłów
            self.cursor.execute('SELECT COUNT(*) FROM trade_ideas_extended')
            total_ideas = self.cursor.fetchone()['COUNT(*)']
            
            return {
                'total': total_ideas,
                'by_status': status_counts,
                'by_symbol': symbol_counts,
                'by_direction': direction_counts
            }
            
        except sqlite3.Error as e:
            logger.error(f"Błąd podczas pobierania statystyk pomysłów handlowych: {e}")
            return {
                'total': 0,
                'by_status': {},
                'by_symbol': {},
                'by_direction': {}
            }
    
    def get_trade_idea_comments(self, idea_id: int) -> List[Dict[str, Any]]:
        """
        Pobiera komentarze do pomysłu handlowego.
        
        Args:
            idea_id: ID pomysłu handlowego
            
        Returns:
            List[Dict[str, Any]]: Lista komentarzy
        """
        # W wersji mock zwracamy pustą listę
        return []
        
    def mock_add_trade(self, trade_data: Dict[str, Any]) -> int:
        """
        Dodaje transakcję bezpośrednio do bazy danych w pamięci.
        Metoda pomocnicza dla testów.
        
        Args:
            trade_data: Dane transakcji
            
        Returns:
            int: ID nowej transakcji lub -1 w przypadku błędu
        """
        try:
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
            
            logger.info(f"Dodano transakcję testową (mock) z ID: {trade_id}")
            return trade_id
            
        except Exception as e:
            logger.error(f"Błąd podczas dodawania transakcji testowej: {e}")
            return -1 
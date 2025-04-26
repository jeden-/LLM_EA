#!/usr/bin/env python
"""
Skrypt do inicjalizacji i zarządzania bazą danych dla systemu LLM Trader MT5.

Ten skrypt tworzy strukturę bazy danych, tabele i przykładowe dane dla
różnych środowisk (dev, test, prod).
"""

import os
import sys
import sqlite3
import logging
import argparse
from datetime import datetime

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Schemat bazy danych - definicje tabel
SCHEMA = {
    "market_analysis": """
        CREATE TABLE IF NOT EXISTS market_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            analysis_text TEXT NOT NULL,
            direction TEXT,
            strength REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            llm_model TEXT,
            strategy_name TEXT,
            indicators_used TEXT,
            analysis_id TEXT UNIQUE
        )
    """,
    
    "trade_ideas": """
        CREATE TABLE IF NOT EXISTS trade_ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id TEXT,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL,
            stop_loss REAL,
            take_profit REAL,
            risk_reward_ratio REAL,
            confidence_score REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            FOREIGN KEY (analysis_id) REFERENCES market_analysis(analysis_id)
        )
    """,
    
    "trades": """
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id INTEGER,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            lot_size REAL NOT NULL,
            entry_price REAL NOT NULL,
            stop_loss REAL,
            take_profit REAL,
            open_time DATETIME NOT NULL,
            close_time DATETIME,
            close_price REAL,
            profit_loss REAL,
            status TEXT DEFAULT 'open',
            strategy TEXT,
            risk_amount REAL,
            position_id INTEGER UNIQUE,
            FOREIGN KEY (idea_id) REFERENCES trade_ideas(id)
        )
    """,
    
    "account_info": """
        CREATE TABLE IF NOT EXISTS account_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            balance REAL NOT NULL,
            equity REAL NOT NULL,
            profit REAL,
            margin REAL,
            margin_level REAL,
            positions_count INTEGER,
            orders_count INTEGER
        )
    """,
    
    "logs": """
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            level TEXT NOT NULL,
            component TEXT NOT NULL,
            message TEXT NOT NULL,
            additional_data TEXT
        )
    """,
    
    "statistics": """
        CREATE TABLE IF NOT EXISTS statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            period_start DATETIME NOT NULL,
            period_end DATETIME NOT NULL,
            total_trades INTEGER,
            winning_trades INTEGER,
            losing_trades INTEGER,
            win_rate REAL,
            profit_factor REAL,
            avg_win REAL,
            avg_loss REAL,
            largest_win REAL,
            largest_loss REAL,
            sharpe_ratio REAL,
            drawdown_max REAL,
            strategy TEXT
        )
    """
}

# Przykładowe dane do generowania w środowisku dev i test
SAMPLE_DATA = {
    "market_analysis": [
        {
            "symbol": "EURUSD",
            "timeframe": "H1",
            "analysis_text": "Trend wzrostowy z silnym wsparciem na poziomie 1.0850.",
            "direction": "buy",
            "strength": 0.75,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "llm_model": "gpt-4",
            "strategy_name": "Trend Following",
            "indicators_used": "MA, RSI, MACD",
            "analysis_id": "AN12345"
        },
        {
            "symbol": "GBPUSD",
            "timeframe": "H4",
            "analysis_text": "Formacja podwójnego szczytu, spodziewany spadek.",
            "direction": "sell",
            "strength": 0.65,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "llm_model": "gpt-4",
            "strategy_name": "Price Action",
            "indicators_used": "Support/Resistance, Bollinger Bands",
            "analysis_id": "AN12346"
        }
    ],
    
    "trade_ideas": [
        {
            "analysis_id": "AN12345",
            "symbol": "EURUSD",
            "direction": "buy",
            "entry_price": 1.0880,
            "stop_loss": 1.0840,
            "take_profit": 1.0950,
            "risk_reward_ratio": 1.75,
            "confidence_score": 0.8,
            "status": "pending",
            "notes": "Czekam na potwierdzenie wybicia"
        },
        {
            "analysis_id": "AN12346",
            "symbol": "GBPUSD",
            "direction": "sell",
            "entry_price": 1.2540,
            "stop_loss": 1.2590,
            "take_profit": 1.2440,
            "risk_reward_ratio": 2.0,
            "confidence_score": 0.7,
            "status": "executed",
            "notes": "Wejście po ukształtowaniu świecy"
        }
    ],
    
    "account_info": [
        {
            "balance": 10000.0,
            "equity": 10050.0,
            "profit": 50.0,
            "margin": 200.0,
            "margin_level": 50.25,
            "positions_count": 2,
            "orders_count": 1
        }
    ]
}

def initialize_database(db_path, add_sample_data=False):
    """Inicjalizuje bazę danych z odpowiednim schematem."""
    try:
        # Upewnij się, że katalog bazy danych istnieje
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            logging.info(f"Utworzono katalog {db_dir}")
        
        # Połącz z bazą danych
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Tworzenie tabel
        for table_name, create_statement in SCHEMA.items():
            cursor.execute(create_statement)
            logging.info(f"Utworzono lub zweryfikowano tabelę {table_name}")
        
        # Dodawanie przykładowych danych (tylko dla dev i test)
        if add_sample_data:
            # Dodaj analizy rynkowe
            for analysis in SAMPLE_DATA["market_analysis"]:
                cursor.execute("""
                    INSERT INTO market_analysis 
                    (symbol, timeframe, analysis_text, direction, strength, timestamp, 
                     llm_model, strategy_name, indicators_used, analysis_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    analysis["symbol"], analysis["timeframe"], analysis["analysis_text"],
                    analysis["direction"], analysis["strength"], analysis["timestamp"],
                    analysis["llm_model"], analysis["strategy_name"], 
                    analysis["indicators_used"], analysis["analysis_id"]
                ))
            
            # Dodaj pomysły handlowe
            for idea in SAMPLE_DATA["trade_ideas"]:
                cursor.execute("""
                    INSERT INTO trade_ideas 
                    (analysis_id, symbol, direction, entry_price, stop_loss, 
                     take_profit, risk_reward_ratio, confidence_score, status, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    idea["analysis_id"], idea["symbol"], idea["direction"],
                    idea["entry_price"], idea["stop_loss"], idea["take_profit"],
                    idea["risk_reward_ratio"], idea["confidence_score"],
                    idea["status"], idea["notes"]
                ))
            
            # Dodaj informacje o koncie
            for account in SAMPLE_DATA["account_info"]:
                cursor.execute("""
                    INSERT INTO account_info 
                    (balance, equity, profit, margin, margin_level, 
                     positions_count, orders_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    account["balance"], account["equity"], account["profit"],
                    account["margin"], account["margin_level"],
                    account["positions_count"], account["orders_count"]
                ))
            
            logging.info("Dodano przykładowe dane do bazy")
        
        # Zatwierdzenie zmian
        conn.commit()
        logging.info(f"Baza danych pomyślnie zainicjalizowana: {db_path}")
        
        return True
    
    except Exception as e:
        logging.error(f"Błąd podczas inicjalizacji bazy danych: {e}")
        return False
    
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Główna funkcja skryptu."""
    parser = argparse.ArgumentParser(description="Inicjalizacja bazy danych dla systemu LLM Trader MT5")
    
    parser.add_argument("--db-path", default="database/dev.db",
                       help="Ścieżka do pliku bazy danych (domyślnie: database/dev.db)")
    
    parser.add_argument("--sample-data", action="store_true",
                       help="Dodaj przykładowe dane (zalecane tylko dla środowisk dev i test)")
    
    parser.add_argument("--env", choices=["dev", "test", "prod"], default="dev",
                       help="Typ środowiska (wpływa na ścieżkę bazy danych)")
    
    args = parser.parse_args()
    
    # Jeśli podano argument --env, użyj odpowiedniej ścieżki
    if args.env and args.db_path == "database/dev.db":
        args.db_path = f"database/{args.env}.db"
    
    # Inicjalizacja bazy danych
    success = initialize_database(args.db_path, args.sample_data)
    
    if success:
        logging.info(f"Baza danych {args.db_path} została pomyślnie zainicjalizowana")
        return 0
    else:
        logging.error(f"Nie udało się zainicjalizować bazy danych {args.db_path}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
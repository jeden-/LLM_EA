import sqlite3
import datetime
import logging
import json

# Konfiguracja loggera
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def dodaj_pomysl_handlowy():
    """Dodaje nowy pomysł handlowy oparty na wynikach backtestingu Master Method."""
    try:
        # Połączenie z bazą danych
        conn = sqlite3.connect('llm_trader.db')
        cursor = conn.cursor()
        
        # Sprawdź czy tabela istnieje, jeśli nie - utwórz
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_ideas_extended (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                risk_percentage REAL,
                risk_reward_ratio REAL,
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
        
        # Dane nowego pomysłu handlowego
        now = datetime.datetime.now().isoformat()
        valid_until = (datetime.datetime.now() + datetime.timedelta(days=14)).isoformat()
        
        risk = 0.007  # 70 pips
        reward = 0.0125  # 125 pips
        risk_reward_ratio = round(reward / risk, 2)
        
        idea_data = {
            'symbol': 'EURUSD',
            'direction': 'SELL',
            'entry_price': 1.0750,
            'stop_loss': 1.0820,
            'take_profit': 1.0625,
            'risk_percentage': 2.0,
            'risk_reward_ratio': risk_reward_ratio,
            'status': 'PENDING',
            'created_at': now,
            'updated_at': now,
            'valid_until': valid_until,
            'timeframe': 'H4',
            'strategy': 'Master Method',
            'source': 'Backtesting',
            'technical_analysis': 'Na podstawie wyników backtestingu strategii Master Method na interwale H4 dla pary EURUSD w okresie 2024-09-01 do 2025-04-27. Strategia osiągnęła Profit Factor 1.46 przy 39.47% zyskownych transakcji. Średni zysk wyniósł 11.50 a średnia strata tylko 5.12, co daje bardzo dobry stosunek zysku do ryzyka 2.24:1. System działa najlepiej w trendach spadkowych, wykorzystując odbicia od VWAP zgodne z trendem (SMA50).',
            'fundamental_analysis': 'EURUSD znajduje się w trendzie spadkowym w dłuższym terminie. Polityka monetarna Fed pozostaje jastrzębia w porównaniu do EBC, co wspiera siłę dolara.',
            'risk_analysis': 'Maksymalny drawdown w testach wyniósł tylko 3.72%, co wskazuje na stabilność systemu. Strategia może nie działać optymalnie przy wysokiej zmienności rynku lub w czasie ważnych danych makroekonomicznych.',
            'additional_notes': 'Wykorzystane parametry: SMA okres: 50, VWAP odchylenie: 0.003, wszystkie setupy aktywne. Stosunek zysku do ryzyka: 2.24.'
        }
        
        # Przygotuj dane do wstawienia
        columns = ", ".join(idea_data.keys())
        placeholders = ", ".join(["?" for _ in idea_data.keys()])
        values = tuple(idea_data.values())
        
        cursor.execute(f'''
            INSERT INTO trade_ideas_extended ({columns})
            VALUES ({placeholders})
        ''', values)
        
        # Pobierz ID nowego rekordu
        idea_id = cursor.lastrowid
        conn.commit()
        
        logger.info(f"Dodano nowy pomysł handlowy o ID: {idea_id}")
        
        # Dodanie komentarza do pomysłu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_idea_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_idea_id INTEGER NOT NULL,
                author TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (trade_idea_id) REFERENCES trade_ideas_extended (id)
            )
        ''')
        
        comment_data = {
            'trade_idea_id': idea_id,
            'author': 'System',
            'content': 'Ten pomysł handlowy został wygenerowany automatycznie na podstawie wyników backtestingu strategii Master Method.',
            'created_at': now
        }
        
        columns = ", ".join(comment_data.keys())
        placeholders = ", ".join(["?" for _ in comment_data.keys()])
        values = tuple(comment_data.values())
        
        cursor.execute(f'''
            INSERT INTO trade_idea_comments ({columns})
            VALUES ({placeholders})
        ''', values)
        
        conn.commit()
        logger.info(f"Dodano komentarz do pomysłu handlowego o ID: {idea_id}")
        
        print(f"Pomyślnie dodano nowy pomysł handlowy o ID: {idea_id}")
        print(f"Pomysł jest dostępny pod adresem: http://localhost:5000/trade_idea_details/{idea_id}")
        
    except Exception as e:
        logger.error(f"Błąd podczas dodawania pomysłu handlowego: {e}")
        if conn:
            conn.rollback()
        print(f"Wystąpił błąd: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    dodaj_pomysl_handlowy() 
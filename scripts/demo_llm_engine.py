"""
Skrypt demonstracyjny dla modułu LLM_Engine.

Ten skrypt pokazuje, jak korzystać z modułu LLM_Engine do analizy rynku,
oceny ryzyka i generowania pomysłów handlowych.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Dodaj ścieżkę głównego katalogu projektu do PYTHONPATH
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
sys.path.insert(0, project_dir)

from LLM_Engine.llm_engine import LLMEngine
from LLM_Engine.technical_indicators import TechnicalIndicators
from LLM_Engine.advanced_indicators import AdvancedIndicators

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_sample_market_data():
    """
    Generuje przykładowe dane rynkowe do demonstracji.
    
    Returns:
        Dict: Przykładowe dane rynkowe
    """
    # Generowanie przykładowych danych cenowych
    np.random.seed(42)  # Dla powtarzalności wyników
    
    # Początkowa cena
    start_price = 1.1500
    
    # Lista na dane cenowe
    price_data = []
    
    # Aktualny czas
    now = datetime.now()
    
    # Generowanie 20 świeczek godzinowych, idąc wstecz od teraz
    current_price = start_price
    for i in range(20, 0, -1):
        time_point = now - timedelta(hours=i)
        time_str = time_point.strftime("%Y-%m-%d %H:%M")
        
        # Losowa zmiana ceny z tendencją wzrostową
        change = np.random.normal(0.0002, 0.0010)  # Średnia dodatnia = trend wzrostowy
        
        current_price += change
        
        # Generowanie high, low, open, close
        high = current_price + abs(np.random.normal(0, 0.0005))
        low = current_price - abs(np.random.normal(0, 0.0005))
        
        if i == 20:  # Pierwsza świeczka
            open_price = current_price - np.random.normal(0, 0.0005)
        else:
            open_price = price_data[-1]["close"]
        
        close_price = current_price
        
        # Losowy wolumen
        volume = int(np.random.normal(1000, 300))
        
        candle = {
            "time": time_str,
            "open": round(open_price, 5),
            "high": round(max(high, open_price, close_price), 5),
            "low": round(min(low, open_price, close_price), 5),
            "close": round(close_price, 5),
            "tick_volume": max(volume, 100)
        }
        
        price_data.append(candle)
    
    # Obliczanie wskaźników technicznych
    close_prices = pd.Series([candle["close"] for candle in price_data])
    high_prices = pd.Series([candle["high"] for candle in price_data])
    low_prices = pd.Series([candle["low"] for candle in price_data])
    
    # Inicjalizacja klas wskaźników
    ti = TechnicalIndicators()
    ai = AdvancedIndicators()
    
    # Obliczanie wskaźników
    sma_20 = ti.calculate_sma(close_prices, 20).tolist()
    ema_50 = ti.calculate_ema(close_prices, 50).tolist()
    rsi_14 = ti.calculate_rsi(close_prices, 14).tolist()
    macd_line, signal_line, histogram = ti.calculate_macd(close_prices)
    upper_bb, middle_bb, lower_bb = ti.calculate_bollinger_bands(close_prices)
    atr_14 = ai.calculate_atr(high_prices, low_prices, close_prices, 14).tolist()
    
    # Tworzenie danych do analizy
    market_data = {
        "symbol": "EURUSD",
        "timeframe": "H1",
        "current_price": price_data[-1]["close"],
        "price_data": price_data,
        "indicators": {
            "SMA(20)": [round(x, 5) if not pd.isna(x) else None for x in sma_20],
            "EMA(50)": [round(x, 5) if not pd.isna(x) else None for x in ema_50],
            "RSI(14)": [round(x, 2) if not pd.isna(x) else None for x in rsi_14],
            "MACD": {
                "macd_line": [round(x, 5) if not pd.isna(x) else None for x in macd_line.tolist()],
                "signal_line": [round(x, 5) if not pd.isna(x) else None for x in signal_line.tolist()],
                "histogram": [round(x, 5) if not pd.isna(x) else None for x in histogram.tolist()]
            },
            "Bollinger_Bands": {
                "upper": [round(x, 5) if not pd.isna(x) else None for x in upper_bb.tolist()],
                "middle": [round(x, 5) if not pd.isna(x) else None for x in middle_bb.tolist()],
                "lower": [round(x, 5) if not pd.isna(x) else None for x in lower_bb.tolist()]
            },
            "ATR(14)": [round(x, 5) if not pd.isna(x) else None for x in atr_14]
        },
        "market_conditions": {
            "volatility": "moderate",
            "trend": "bullish",
            "volume": "average"
        },
        "significant_levels": {
            "support": [round(price_data[-1]["close"] * 0.998, 5), round(price_data[-1]["close"] * 0.995, 5)],
            "resistance": [round(price_data[-1]["close"] * 1.002, 5), round(price_data[-1]["close"] * 1.005, 5)]
        },
        "news": [
            {
                "time": (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"),
                "title": "ECB Minutes Released",
                "impact": "medium"
            },
            {
                "time": (now + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"),
                "title": "US Non-Farm Payrolls",
                "impact": "high"
            }
        ]
    }
    
    return market_data

def generate_sample_position_data(market_data):
    """
    Generuje przykładowe dane o pozycji do demonstracji.
    
    Args:
        market_data: Dane rynkowe do wykorzystania
    
    Returns:
        Dict: Przykładowe dane o pozycji
    """
    current_price = market_data["current_price"]
    
    position_data = {
        "symbol": market_data["symbol"],
        "account_balance": 10000.0,
        "open_positions": [
            {
                "symbol": "GBPUSD",
                "type": "buy",
                "volume": 0.1,
                "price_open": 1.2750,
                "sl": 1.2700,
                "tp": 1.2850,
                "profit": 15.0
            }
        ],
        "historical_trades": [
            {
                "symbol": "EURUSD",
                "type": "buy",
                "volume": 0.1,
                "price_open": 1.1450,
                "price_close": 1.1480,
                "profit": 30.0,
                "time_open": "2023-06-01 10:00",
                "time_close": "2023-06-01 15:00"
            },
            {
                "symbol": "EURUSD",
                "type": "sell",
                "volume": 0.1,
                "price_open": 1.1520,
                "price_close": 1.1500,
                "profit": 20.0,
                "time_open": "2023-06-02 10:00",
                "time_close": "2023-06-02 14:00"
            },
            {
                "symbol": "GBPUSD",
                "type": "buy",
                "volume": 0.1,
                "price_open": 1.2700,
                "price_close": 1.2680,
                "profit": -20.0,
                "time_open": "2023-06-03 09:00",
                "time_close": "2023-06-03 16:00"
            }
        ],
        "potential_position": {
            "symbol": market_data["symbol"],
            "type": "buy",
            "entry_price": current_price,
            "volume": 0.1,
            "sl_pips": 50,
            "tp_pips": 100
        }
    }
    
    return position_data

def main():
    """
    Główna funkcja demonstracyjna.
    """
    logger.info("Rozpoczynanie demonstracji modułu LLM_Engine")
    
    try:
        # Inicjalizacja silnika LLM
        logger.info("Inicjalizacja LLMEngine")
        engine = LLMEngine()
        
        # Generowanie przykładowych danych
        logger.info("Generowanie przykładowych danych rynkowych")
        market_data = generate_sample_market_data()
        
        # Analiza rynku
        logger.info("Wykonywanie analizy rynkowej")
        market_analysis = engine.analyze_market(market_data)
        
        # Wyświetlenie wyniku analizy
        logger.info("Wynik analizy rynkowej:")
        print(json.dumps(market_analysis, indent=2, ensure_ascii=False))
        
        # Generowanie pomysłu handlowego
        logger.info("Generowanie pomysłu handlowego")
        trade_idea = engine.generate_trade_idea(market_data, strategy="trend_following")
        
        # Wyświetlenie pomysłu handlowego
        logger.info("Pomysł handlowy:")
        print(json.dumps(trade_idea, indent=2, ensure_ascii=False))
        
        # Generowanie przykładowych danych o pozycji
        logger.info("Generowanie przykładowych danych o pozycji")
        position_data = generate_sample_position_data(market_data)
        
        # Ocena ryzyka
        logger.info("Przeprowadzanie oceny ryzyka")
        risk_assessment = engine.evaluate_position_risk(position_data)
        
        # Wyświetlenie oceny ryzyka
        logger.info("Ocena ryzyka:")
        print(json.dumps(risk_assessment, indent=2, ensure_ascii=False))
        
        # Przykład wyjaśnienia od systemu
        logger.info("Generowanie wyjaśnienia na temat strategii")
        explanation = engine.get_system_explanation(
            "Wyjaśnij, na czym polega strategia podążania za trendem i jakie wskaźniki są w niej najważniejsze?"
        )
        
        # Wyświetlenie wyjaśnienia
        logger.info("Wyjaśnienie strategii:")
        print(explanation)
        
        logger.info("Demonstracja zakończona pomyślnie")
        
    except Exception as e:
        logger.error(f"Błąd podczas demonstracji: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 
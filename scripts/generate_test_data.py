"""
Skrypt do generowania danych testowych dla modułu LLM_Engine.

Skrypt generuje kilka zestawów danych testowych dla różnych par walutowych
i różnych scenariuszy rynkowych, które mogą być używane do testowania
i walidacji modułu LLM_Engine.
"""

import os
import sys
import json
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Dodanie ścieżki głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM_Engine.technical_indicators import TechnicalIndicators
from LLM_Engine.advanced_indicators import AdvancedIndicators
from MT5_Connector.candlestick_patterns import CandlestickPatterns
from MT5_Connector.data_formatter import DataFormatter

# Ścieżka do katalogu z danymi testowymi
TEST_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tests', 'test_data')

# Upewnij się, że katalog istnieje
os.makedirs(TEST_DATA_DIR, exist_ok=True)

# Inicjalizacja komponentów
tech_indicators = TechnicalIndicators()
adv_indicators = AdvancedIndicators()
candlestick_patterns = CandlestickPatterns()
data_formatter = DataFormatter()

def generate_price_data(start_price, length, trend='neutral', volatility=0.001):
    """
    Generuje syntetyczne dane cenowe.
    
    Args:
        start_price (float): Początkowa cena
        length (int): Ilość generowanych świec
        trend (str): Kierunek trendu ('bullish', 'bearish', 'neutral')
        volatility (float): Poziom zmienności
    
    Returns:
        DataFrame: DataFrame zawierający dane OHLCV
    """
    # Ustawienie współczynnika trendu
    if trend == 'bullish':
        trend_factor = 0.0005
    elif trend == 'bearish':
        trend_factor = -0.0005
    else:
        trend_factor = 0.0
    
    # Generowanie losowych zmian cen
    np.random.seed(42)  # Dla powtarzalności
    price_changes = np.random.normal(trend_factor, volatility, length)
    
    # Tworzenie cen zamknięcia
    closes = [start_price]
    for change in price_changes:
        closes.append(closes[-1] * (1 + change))
    closes = closes[1:]  # Usuwamy początkową cenę
    
    # Tworzenie pozostałych danych OHLCV
    highs = []
    lows = []
    opens = [start_price]
    volumes = []
    
    for i in range(len(closes)):
        # Generowanie wysokiego i niskiego
        high_factor = 1 + abs(np.random.normal(0, volatility))
        low_factor = 1 - abs(np.random.normal(0, volatility))
        
        if i > 0:
            opens.append(closes[i-1])
        
        highs.append(max(opens[i], closes[i]) * high_factor)
        lows.append(min(opens[i], closes[i]) * low_factor)
        
        # Generowanie wolumenu
        volumes.append(int(np.random.normal(1000, 200)))
    
    # Tworzenie znaczników czasu
    start_date = datetime.now() - timedelta(days=length)
    timestamps = [start_date + timedelta(hours=i) for i in range(length)]
    
    # Tworzenie DataFrame
    df = pd.DataFrame({
        'time': timestamps,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })
    
    return df

def calculate_indicators(df):
    """
    Oblicza wskaźniki techniczne dla danych cenowych.
    
    Args:
        df (DataFrame): DataFrame z danymi OHLCV
    
    Returns:
        dict: Słownik z obliczonymi wskaźnikami
    """
    # Prostsze wskaźniki
    sma_50 = tech_indicators.calculate_sma(df['close'], 50)
    ema_20 = tech_indicators.calculate_ema(df['close'], 20)
    rsi_14 = tech_indicators.calculate_rsi(df['close'], 14)
    macd_line, signal_line, histogram = tech_indicators.calculate_macd(df['close'])
    upper_bb, middle_bb, lower_bb = tech_indicators.calculate_bollinger_bands(df['close'])
    
    # Zaawansowane wskaźniki
    atr_14 = adv_indicators.calculate_atr(df['high'], df['low'], df['close'], 14)
    adx_14 = adv_indicators.calculate_adx(df['high'], df['low'], df['close'], 14)
    
    # Formacje świecowe
    patterns = []
    for i in range(5, len(df)):
        window = df.iloc[i-5:i+1]
        pattern_df = candlestick_patterns.identify_patterns(window)
        
        # Zbieramy wszystkie aktywne formacje dla ostatniej świecy
        candle_patterns = {}
        for col in pattern_df.columns:
            if col not in ['time', 'open', 'high', 'low', 'close', 'volume'] and pattern_df.iloc[-1][col] == True:
                candle_patterns[col] = True
        
        if candle_patterns:
            patterns.append({
                'index': i,
                'time': df.iloc[i]['time'].strftime('%Y-%m-%d %H:%M:%S'),
                'patterns': list(candle_patterns.keys())
            })
    
    return {
        'sma_50': sma_50.tolist(),
        'ema_20': ema_20.tolist(),
        'rsi_14': rsi_14.tolist(),
        'macd_line': macd_line.tolist(),
        'signal_line': signal_line.tolist(),
        'histogram': histogram.tolist(),
        'upper_bb': upper_bb.tolist(),
        'middle_bb': middle_bb.tolist(),
        'lower_bb': lower_bb.tolist(),
        'atr_14': atr_14.tolist(),
        'adx_14': adx_14.tolist(),
        'patterns': patterns
    }

def generate_test_scenarios():
    """
    Generuje różne scenariusze testowe dla modułu LLM_Engine.
    
    Returns:
        dict: Słownik zawierający scenariusze testowe
    """
    scenarios = {
        'bullish_trend': {
            'description': 'Silny trend wzrostowy',
            'data': generate_price_data(1.1000, 100, 'bullish', 0.001),
            'expected_outcome': {
                'trend': 'bullish',
                'setup': 'Trend Reverter',
                'action': 'ENTER',
                'direction': 'BUY'
            }
        },
        'bearish_trend': {
            'description': 'Silny trend spadkowy',
            'data': generate_price_data(1.1000, 100, 'bearish', 0.001),
            'expected_outcome': {
                'trend': 'bearish',
                'setup': 'Trend Reverter',
                'action': 'ENTER',
                'direction': 'SELL'
            }
        },
        'consolidation': {
            'description': 'Konsolidacja rynku',
            'data': generate_price_data(1.1000, 100, 'neutral', 0.0005),
            'expected_outcome': {
                'trend': 'neutral',
                'setup': 'Small Account Range Rider',
                'action': 'WAIT'
            }
        },
        'bullish_breakout': {
            'description': 'Wybicie z konsolidacji w górę',
            'data': None,  # Zostanie wygenerowane niżej
            'expected_outcome': {
                'trend': 'bullish',
                'setup': 'VWAP Bouncer',
                'action': 'ENTER',
                'direction': 'BUY'
            }
        },
        'bearish_breakdown': {
            'description': 'Wybicie z konsolidacji w dół',
            'data': None,  # Zostanie wygenerowane niżej
            'expected_outcome': {
                'trend': 'bearish',
                'setup': 'VWAP Bouncer',
                'action': 'ENTER',
                'direction': 'SELL'
            }
        }
    }
    
    # Generowanie specjalnych scenariuszy
    
    # Bullish breakout
    df_consolidation = generate_price_data(1.1000, 80, 'neutral', 0.0003)
    df_breakout = generate_price_data(df_consolidation['close'].iloc[-1], 20, 'bullish', 0.002)
    df_breakout['time'] = [df_consolidation['time'].iloc[-1] + timedelta(hours=i+1) for i in range(20)]
    df_bullish_breakout = pd.concat([df_consolidation, df_breakout]).reset_index(drop=True)
    scenarios['bullish_breakout']['data'] = df_bullish_breakout
    
    # Bearish breakdown
    df_consolidation = generate_price_data(1.1000, 80, 'neutral', 0.0003)
    df_breakdown = generate_price_data(df_consolidation['close'].iloc[-1], 20, 'bearish', 0.002)
    df_breakdown['time'] = [df_consolidation['time'].iloc[-1] + timedelta(hours=i+1) for i in range(20)]
    df_bearish_breakdown = pd.concat([df_consolidation, df_breakdown]).reset_index(drop=True)
    scenarios['bearish_breakdown']['data'] = df_bearish_breakdown
    
    return scenarios

def save_test_data(scenarios):
    """
    Zapisuje dane testowe do plików.
    
    Args:
        scenarios (dict): Słownik ze scenariuszami testowymi
    """
    for name, scenario in scenarios.items():
        # Zapisz dane cenowe
        price_data_file = os.path.join(TEST_DATA_DIR, f'{name}_price_data.csv')
        scenario['data'].to_csv(price_data_file, index=False)
        
        # Oblicz i zapisz wskaźniki
        indicators = calculate_indicators(scenario['data'])
        indicators_file = os.path.join(TEST_DATA_DIR, f'{name}_indicators.json')
        with open(indicators_file, 'w') as f:
            json.dump(indicators, f, indent=2)
        
        # Przygotuj wersję danych z kolumną timestamp zamiast time
        df_format = scenario['data'].copy()
        df_format['timestamp'] = df_format['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Konwertuj DataFrame na słownik rekordów z timestampami jako string
        records = []
        for _, row in df_format.iloc[-20:].iterrows():
            record = row.to_dict()
            # Upewniamy się, że wszystkie timestamp są stringami
            record['time'] = record['time'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(record['time'], 'strftime') else str(record['time'])
            records.append(record)
        
        # Przygotuj prosty format danych OHLC do analizy
        formatted_data = {
            "symbol": "EURUSD",
            "timeframe": "H1",
            "data": records,
            "indicators": {
                "sma_50": indicators['sma_50'][-20:],
                "ema_20": indicators['ema_20'][-20:],
                "rsi_14": indicators['rsi_14'][-20:],
                "macd": {
                    "line": indicators['macd_line'][-20:],
                    "signal": indicators['signal_line'][-20:],
                    "histogram": indicators['histogram'][-20:]
                },
                "bollinger_bands": {
                    "upper": indicators['upper_bb'][-20:],
                    "middle": indicators['middle_bb'][-20:],
                    "lower": indicators['lower_bb'][-20:]
                },
                "atr_14": indicators['atr_14'][-20:],
                "adx_14": indicators['adx_14'][-20:]
            },
            "patterns": indicators['patterns']
        }
        
        formatted_file = os.path.join(TEST_DATA_DIR, f'{name}_formatted.json')
        with open(formatted_file, 'w') as f:
            json.dump(formatted_data, f, indent=2)
        
        # Zapisz oczekiwany wynik
        expected_file = os.path.join(TEST_DATA_DIR, f'{name}_expected.json')
        with open(expected_file, 'w') as f:
            json.dump(scenario['expected_outcome'], f, indent=2)
        
        # Zapisz metadane scenariusza
        metadata = {
            'description': scenario['description'],
            'symbol': 'EURUSD',
            'timeframe': 'H1',
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        metadata_file = os.path.join(TEST_DATA_DIR, f'{name}_metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Zapisano dane dla scenariusza: {name}")

if __name__ == "__main__":
    print("Generowanie danych testowych dla LLM_Engine...")
    scenarios = generate_test_scenarios()
    save_test_data(scenarios)
    print(f"Dane testowe zapisane w katalogu: {TEST_DATA_DIR}") 
"""
Moduł do formatowania danych rynkowych dla LLM.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import pandas as pd


class DataFormatter:
    """
    Klasa odpowiedzialna za formatowanie danych rynkowych do postaci, 
    która może być przetwarzana przez model LLM.
    """
    
    @staticmethod
    def format_ohlc_data(df: pd.DataFrame, max_candles: int = 30) -> str:
        """
        Formatuje dane OHLC do czytelnego formatu tekstowego dla LLM.
        
        Args:
            df: DataFrame zawierający dane OHLC.
            max_candles: Maksymalna liczba świec do uwzględnienia.
            
        Returns:
            str: Sformatowany tekst z danymi OHLC.
        """
        # Ograniczenie liczby świec
        if len(df) > max_candles:
            df = df.iloc[-max_candles:]
        
        # Formatowanie danych
        formatted_data = "Dane OHLC (od najstarszej do najnowszej):\n"
        
        for idx, row in df.iterrows():
            date_str = row['timestamp'].strftime('%Y-%m-%d %H:%M')
            formatted_data += f"{date_str}: O={row['open']:.5f}, H={row['high']:.5f}, L={row['low']:.5f}, C={row['close']:.5f}, V={int(row['volume'])}\n"
        
        return formatted_data
    
    @staticmethod
    def format_indicators(df: pd.DataFrame, indicators: List[str], max_candles: int = 10) -> str:
        """
        Formatuje wybrane wskaźniki techniczne do czytelnego formatu tekstowego dla LLM.
        
        Args:
            df: DataFrame zawierający dane wskaźników.
            indicators: Lista nazw kolumn wskaźników do uwzględnienia.
            max_candles: Maksymalna liczba świec do uwzględnienia.
            
        Returns:
            str: Sformatowany tekst z danymi wskaźników.
        """
        # Sprawdzenie, czy wszystkie wskaźniki istnieją
        for indicator in indicators:
            if indicator not in df.columns:
                raise ValueError(f"Wskaźnik {indicator} nie istnieje w danych.")
        
        # Ograniczenie liczby świec
        if len(df) > max_candles:
            df = df.iloc[-max_candles:]
        
        # Formatowanie danych
        formatted_data = "Dane wskaźników technicznych (od najstarszej do najnowszej):\n"
        
        for idx, row in df.iterrows():
            date_str = row['timestamp'].strftime('%Y-%m-%d %H:%M')
            values = ", ".join([f"{ind}={row[ind]:.5f}" for ind in indicators if pd.notna(row[ind])])
            formatted_data += f"{date_str}: {values}\n"
        
        return formatted_data
    
    @staticmethod
    def format_candlestick_patterns(df: pd.DataFrame, max_candles: int = 10) -> str:
        """
        Formatuje wykryte formacje świecowe do czytelnego formatu tekstowego dla LLM.
        
        Args:
            df: DataFrame zawierający dane formacji świecowych.
            max_candles: Maksymalna liczba świec do uwzględnienia.
            
        Returns:
            str: Sformatowany tekst z danymi formacji świecowych.
        """
        # Ograniczenie liczby świec
        if len(df) > max_candles:
            df = df.iloc[-max_candles:]
        
        # Znajdź wszystkie kolumny formacji świecowych
        pattern_columns = [col for col in df.columns if any(pat in col for pat in [
            'doji', 'hammer', 'shooting_star', 'marubozu', 
            'engulfing', 'harami', 'morning_star', 'evening_star', 
            'three_white_soldiers', 'three_black_crows'
        ])]
        
        if not pattern_columns:
            return "Brak wykrytych formacji świecowych w danych."
        
        # Formatowanie danych
        formatted_data = "Wykryte formacje świecowe (od najstarszej do najnowszej):\n"
        
        for idx, row in df.iterrows():
            date_str = row['timestamp'].strftime('%Y-%m-%d %H:%M')
            detected_patterns = [col for col in pattern_columns if row[col]]
            
            if detected_patterns:
                pattern_str = ", ".join(detected_patterns)
                formatted_data += f"{date_str}: {pattern_str}\n"
            else:
                formatted_data += f"{date_str}: Brak formacji\n"
        
        return formatted_data
    
    @staticmethod
    def format_market_summary(
        df: pd.DataFrame, 
        account_info: Dict, 
        symbol_info: Dict,
        timeframe: int
    ) -> str:
        """
        Tworzy podsumowanie rynku dla LLM.
        
        Args:
            df: DataFrame zawierający dane OHLC, wskaźniki i formacje.
            account_info: Słownik z informacjami o koncie.
            symbol_info: Słownik z informacjami o symbolu.
            timeframe: Timeframe używany do analizy.
            
        Returns:
            str: Sformatowane podsumowanie rynku.
        """
        # Ostatnia świeca
        last_candle = df.iloc[-1]
        prev_candle = df.iloc[-2] if len(df) > 1 else None
        
        # Aktualna cena
        current_price = symbol_info.get("bid", 0)
        
        # Formatowanie czasu
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        last_candle_time = last_candle['timestamp'].strftime('%Y-%m-%d %H:%M')
        
        # Zmiana ceny
        price_change = 0
        price_change_pct = 0
        if prev_candle is not None:
            price_change = last_candle['close'] - prev_candle['close']
            price_change_pct = (price_change / prev_candle['close']) * 100
        
        # Zakres dzienny
        daily_high = df['high'].max()
        daily_low = df['low'].min()
        
        # Wolumen
        volume_sum = df['volume'].sum()
        
        # Trendy
        if 'sma_50' in df.columns and 'sma_200' in df.columns:
            trend_50_200 = "wzrostowy" if last_candle['sma_50'] > last_candle['sma_200'] else "spadkowy"
        else:
            trend_50_200 = "brak danych"
        
        # Formacja świecowe
        pattern_columns = [col for col in df.columns if any(pat in col for pat in [
            'doji', 'hammer', 'shooting_star', 'marubozu', 
            'engulfing', 'harami', 'morning_star', 'evening_star', 
            'three_white_soldiers', 'three_black_crows'
        ])]
        
        recent_patterns = []
        for col in pattern_columns:
            if df[col].iloc[-3:].any():
                recent_patterns.append(col)
        
        # Informacje o koncie
        balance = account_info.get("balance", 0)
        equity = account_info.get("equity", 0)
        
        # Formatowanie podsumowania
        summary = f"""
Podsumowanie rynku:
------------------
Czas: {current_time}
Symbol: {symbol_info.get('symbol', 'Brak danych')}
Timeframe: {timeframe} min
Ostatnia ukończona świeca: {last_candle_time}

Ceny:
- Aktualna: {current_price:.5f}
- Otwarcie ostatniej świecy: {last_candle['open']:.5f}
- Zamknięcie ostatniej świecy: {last_candle['close']:.5f}
- Najwyższa ostatniej świecy: {last_candle['high']:.5f}
- Najniższa ostatniej świecy: {last_candle['low']:.5f}
- Zmiana: {price_change:.5f} ({price_change_pct:.2f}%)
- Zakres dzienny: {daily_low:.5f} - {daily_high:.5f}

Wolumen:
- Wolumen ostatniej świecy: {int(last_candle['volume'])}
- Suma wolumenu: {int(volume_sum)}

Wskaźniki techniczne:
"""
        
        # Dodaj dostępne wskaźniki
        indicator_list = ['sma_50', 'sma_200', 'ema_20', 'rsi', 'macd', 'atr', 'vwap', 'bb_upper', 'bb_middle', 'bb_lower']
        for indicator in indicator_list:
            if indicator in df.columns:
                summary += f"- {indicator}: {last_candle[indicator]:.5f}\n"
        
        summary += f"""
Trendy:
- Trend SMA 50/200: {trend_50_200}

Formacje świecowe:
- Ostatnie wykryte formacje: {', '.join(recent_patterns) if recent_patterns else 'Brak'}

Konto:
- Saldo: {balance:.2f} {account_info.get('currency', '')}
- Equity: {equity:.2f} {account_info.get('currency', '')}
- Margin: {account_info.get('margin', 0):.2f} {account_info.get('currency', '')}
- Wolny margin: {account_info.get('free_margin', 0):.2f} {account_info.get('currency', '')}
"""
        
        return summary
    
    @staticmethod
    def format_data_for_llm(
        df: pd.DataFrame, 
        account_info: Dict, 
        symbol_info: Dict,
        timeframe: int,
        include_ohlc: bool = True,
        include_indicators: bool = True,
        include_patterns: bool = True,
        max_candles: int = 30
    ) -> str:
        """
        Łączy wszystkie dane w jeden sformatowany tekst dla LLM.
        
        Args:
            df: DataFrame zawierający dane OHLC, wskaźniki i formacje.
            account_info: Słownik z informacjami o koncie.
            symbol_info: Słownik z informacjami o symbolu.
            timeframe: Timeframe używany do analizy.
            include_ohlc: Czy dołączyć dane OHLC.
            include_indicators: Czy dołączyć wskaźniki techniczne.
            include_patterns: Czy dołączyć formacje świecowe.
            max_candles: Maksymalna liczba świec do uwzględnienia.
            
        Returns:
            str: Sformatowany tekst z danymi dla LLM.
        """
        formatted_text = DataFormatter.format_market_summary(df, account_info, symbol_info, timeframe)
        
        if include_ohlc:
            formatted_text += "\n\n" + DataFormatter.format_ohlc_data(df, max_candles)
        
        if include_indicators:
            indicator_list = ['sma_50', 'sma_200', 'ema_20', 'rsi', 'macd', 'atr', 'vwap', 'bb_upper', 'bb_middle', 'bb_lower']
            available_indicators = [ind for ind in indicator_list if ind in df.columns]
            if available_indicators:
                formatted_text += "\n\n" + DataFormatter.format_indicators(df, available_indicators, max_candles)
        
        if include_patterns:
            formatted_text += "\n\n" + DataFormatter.format_candlestick_patterns(df, max_candles)
        
        return formatted_text 
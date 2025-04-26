"""
Wskaźniki techniczne - moduł do obliczania wskaźników technicznych na podstawie danych z MT5.
"""

from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd


class TechnicalIndicators:
    """
    Klasa implementująca popularne wskaźniki techniczne używane w analizie rynków finansowych.
    """
    
    @staticmethod
    def add_sma(df: pd.DataFrame, period: int = 50, column: str = 'close') -> pd.DataFrame:
        """
        Dodaje Simple Moving Average (SMA) do DataFrame.
        
        Args:
            df: DataFrame zawierający dane cenowe.
            period: Okres SMA.
            column: Kolumna, na podstawie której obliczany jest SMA.
            
        Returns:
            pd.DataFrame: DataFrame z dodaną kolumną SMA.
        """
        column_name = f'sma_{period}'
        df[column_name] = df[column].rolling(window=period).mean()
        return df
    
    @staticmethod
    def add_ema(df: pd.DataFrame, period: int = 50, column: str = 'close') -> pd.DataFrame:
        """
        Dodaje Exponential Moving Average (EMA) do DataFrame.
        
        Args:
            df: DataFrame zawierający dane cenowe.
            period: Okres EMA.
            column: Kolumna, na podstawie której obliczany jest EMA.
            
        Returns:
            pd.DataFrame: DataFrame z dodaną kolumną EMA.
        """
        column_name = f'ema_{period}'
        df[column_name] = df[column].ewm(span=period, adjust=False).mean()
        return df
    
    @staticmethod
    def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Dodaje Average True Range (ATR) do DataFrame.
        
        Args:
            df: DataFrame zawierający dane OHLC.
            period: Okres ATR.
            
        Returns:
            pd.DataFrame: DataFrame z dodaną kolumną ATR.
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Obliczenie True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        
        # Obliczenie ATR
        atr = tr.rolling(window=period).mean()
        df['atr'] = atr
        
        return df
    
    @staticmethod
    def add_vwap(df: pd.DataFrame, reset_period: Optional[str] = 'D') -> pd.DataFrame:
        """
        Dodaje Volume Weighted Average Price (VWAP) do DataFrame.
        
        Args:
            df: DataFrame zawierający dane OHLCV.
            reset_period: Okres resetowania VWAP ('D' dla dziennego, 'W' dla tygodniowego, None dla braku resetowania).
            
        Returns:
            pd.DataFrame: DataFrame z dodaną kolumną VWAP.
        """
        df = df.copy()
        
        # Obliczenie typowej ceny
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        
        # Obliczenie volumextypowyj cenę
        df['vp'] = df['typical_price'] * df['volume']
        
        if reset_period:
            # Grupowanie po okresie i obliczenie narastającej sumy
            df['date'] = df['timestamp'].dt.strftime(f'%Y-%m-%d') if reset_period == 'D' else df['timestamp'].dt.strftime(f'%Y-%W')
            df['cumulative_vp'] = df.groupby('date')['vp'].cumsum()
            df['cumulative_volume'] = df.groupby('date')['volume'].cumsum()
        else:
            # Obliczenie narastającej sumy bez resetowania
            df['cumulative_vp'] = df['vp'].cumsum()
            df['cumulative_volume'] = df['volume'].cumsum()
        
        # Obliczenie VWAP
        df['vwap'] = df['cumulative_vp'] / df['cumulative_volume']
        
        # Usunięcie kolumn pomocniczych
        df.drop(['typical_price', 'vp', 'cumulative_vp', 'cumulative_volume'], axis=1, inplace=True)
        if reset_period:
            df.drop(['date'], axis=1, inplace=True)
        
        return df
    
    @staticmethod
    def add_rsi(df: pd.DataFrame, period: int = 14, column: str = 'close') -> pd.DataFrame:
        """
        Dodaje Relative Strength Index (RSI) do DataFrame.
        
        Args:
            df: DataFrame zawierający dane cenowe.
            period: Okres RSI.
            column: Kolumna, na podstawie której obliczany jest RSI.
            
        Returns:
            pd.DataFrame: DataFrame z dodaną kolumną RSI.
        """
        # Obliczenie zmian cen
        delta = df[column].diff()
        
        # Obliczenie zysków i strat
        gain = delta.copy()
        loss = delta.copy()
        gain[gain < 0] = 0
        loss[loss > 0] = 0
        loss = abs(loss)
        
        # Obliczenie średniego zysku i średniej straty
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Obliczenie RS i RSI
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        return df
    
    @staticmethod
    def add_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0, column: str = 'close') -> pd.DataFrame:
        """
        Dodaje Bollinger Bands do DataFrame.
        
        Args:
            df: DataFrame zawierający dane cenowe.
            period: Okres dla średniej kroczącej.
            std_dev: Liczba odchyleń standardowych dla górnego i dolnego pasma.
            column: Kolumna, na podstawie której obliczane są pasma.
            
        Returns:
            pd.DataFrame: DataFrame z dodanymi kolumnami Bollinger Bands.
        """
        # Obliczenie średniej kroczącej
        df['bb_middle'] = df[column].rolling(window=period).mean()
        
        # Obliczenie odchylenia standardowego
        rolling_std = df[column].rolling(window=period).std()
        
        # Obliczenie górnego i dolnego pasma
        df['bb_upper'] = df['bb_middle'] + (rolling_std * std_dev)
        df['bb_lower'] = df['bb_middle'] - (rolling_std * std_dev)
        
        return df
    
    @staticmethod
    def add_macd(df: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9, column: str = 'close') -> pd.DataFrame:
        """
        Dodaje Moving Average Convergence Divergence (MACD) do DataFrame.
        
        Args:
            df: DataFrame zawierający dane cenowe.
            fast_period: Okres dla szybkiej EMA.
            slow_period: Okres dla wolnej EMA.
            signal_period: Okres dla linii sygnału.
            column: Kolumna, na podstawie której obliczany jest MACD.
            
        Returns:
            pd.DataFrame: DataFrame z dodanymi kolumnami MACD.
        """
        # Obliczenie szybkiej i wolnej EMA
        ema_fast = df[column].ewm(span=fast_period, adjust=False).mean()
        ema_slow = df[column].ewm(span=slow_period, adjust=False).mean()
        
        # Obliczenie MACD
        df['macd'] = ema_fast - ema_slow
        
        # Obliczenie linii sygnału
        df['macd_signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()
        
        # Obliczenie histogramu
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        return df 
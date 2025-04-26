"""
Moduł do identyfikacji formacji świecowych na wykresach cenowych.
"""

from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd


class CandlestickPatterns:
    """
    Klasa implementująca rozpoznawanie powszechnych formacji świecowych.
    """
    
    @staticmethod
    def identify_patterns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Identyfikuje wszystkie wspierane formacje świecowe w DataFrame.
        
        Args:
            df: DataFrame zawierający dane OHLC.
            
        Returns:
            pd.DataFrame: DataFrame z dodanymi kolumnami dla każdej formacji.
        """
        df = df.copy()
        
        # Jednościecowe formacje
        df = CandlestickPatterns.doji(df)
        df = CandlestickPatterns.hammer(df)
        df = CandlestickPatterns.shooting_star(df)
        df = CandlestickPatterns.marubozu(df)
        
        # Dwuświecowe formacje
        df = CandlestickPatterns.engulfing(df)
        df = CandlestickPatterns.harami(df)
        
        # Trójświecowe formacje
        df = CandlestickPatterns.morning_star(df)
        df = CandlestickPatterns.evening_star(df)
        df = CandlestickPatterns.three_white_soldiers(df)
        df = CandlestickPatterns.three_black_crows(df)
        
        return df
    
    @staticmethod
    def doji(df: pd.DataFrame, tolerance: float = 0.05) -> pd.DataFrame:
        """
        Identyfikuje formację Doji (świeca z małym lub zerowym ciałem).
        
        Args:
            df: DataFrame zawierający dane OHLC.
            tolerance: Tolerancja dla określenia "małego" ciała (jako % zakresu high-low).
            
        Returns:
            pd.DataFrame: DataFrame z dodaną kolumną 'doji'.
        """
        # Obliczenie długości ciała
        df['body_size'] = abs(df['close'] - df['open'])
        
        # Obliczenie zakresu high-low
        df['range'] = df['high'] - df['low']
        
        # Identyfikacja Doji
        df['doji'] = (df['body_size'] / df['range'] < tolerance) & (df['range'] > 0)
        
        # Usunięcie kolumn pomocniczych
        df.drop(['body_size', 'range'], axis=1, inplace=True)
        
        return df
    
    @staticmethod
    def hammer(df: pd.DataFrame, body_ratio: float = 0.25, shadow_ratio: float = 2.0) -> pd.DataFrame:
        """
        Identyfikuje formację Hammer (młotek) - świeca z małym ciałem na górze i długim dolnym cieniem.
        
        Args:
            df: DataFrame zawierający dane OHLC.
            body_ratio: Maksymalny stosunek długości ciała do całej świecy.
            shadow_ratio: Minimalny stosunek dolnego cienia do długości ciała.
            
        Returns:
            pd.DataFrame: DataFrame z dodaną kolumną 'hammer'.
        """
        # Obliczenie długości ciała
        df['body_size'] = abs(df['close'] - df['open'])
        
        # Obliczenie górnego i dolnego cienia
        df['upper_shadow'] = df.apply(lambda x: x['high'] - max(x['open'], x['close']), axis=1)
        df['lower_shadow'] = df.apply(lambda x: min(x['open'], x['close']) - x['low'], axis=1)
        
        # Obliczenie całkowitej długości świecy
        df['candle_range'] = df['high'] - df['low']
        
        # Identyfikacja Hammer (młotek)
        df['hammer'] = (
            (df['body_size'] / df['candle_range'] <= body_ratio) & 
            (df['lower_shadow'] / (df['body_size'] + 0.0001) >= shadow_ratio) &
            (df['upper_shadow'] < df['body_size'])
        )
        
        # Usunięcie kolumn pomocniczych
        df.drop(['body_size', 'upper_shadow', 'lower_shadow', 'candle_range'], axis=1, inplace=True)
        
        return df
    
    @staticmethod
    def shooting_star(df: pd.DataFrame, body_ratio: float = 0.25, shadow_ratio: float = 2.0) -> pd.DataFrame:
        """
        Identyfikuje formację Shooting Star (spadająca gwiazda) - świeca z małym ciałem na dole i długim górnym cieniem.
        
        Args:
            df: DataFrame zawierający dane OHLC.
            body_ratio: Maksymalny stosunek długości ciała do całej świecy.
            shadow_ratio: Minimalny stosunek górnego cienia do długości ciała.
            
        Returns:
            pd.DataFrame: DataFrame z dodaną kolumną 'shooting_star'.
        """
        # Obliczenie długości ciała
        df['body_size'] = abs(df['close'] - df['open'])
        
        # Obliczenie górnego i dolnego cienia
        df['upper_shadow'] = df.apply(lambda x: x['high'] - max(x['open'], x['close']), axis=1)
        df['lower_shadow'] = df.apply(lambda x: min(x['open'], x['close']) - x['low'], axis=1)
        
        # Obliczenie całkowitej długości świecy
        df['candle_range'] = df['high'] - df['low']
        
        # Identyfikacja Shooting Star (spadająca gwiazda)
        df['shooting_star'] = (
            (df['body_size'] / df['candle_range'] <= body_ratio) & 
            (df['upper_shadow'] / (df['body_size'] + 0.0001) >= shadow_ratio) &
            (df['lower_shadow'] < df['body_size'])
        )
        
        # Usunięcie kolumn pomocniczych
        df.drop(['body_size', 'upper_shadow', 'lower_shadow', 'candle_range'], axis=1, inplace=True)
        
        return df
    
    @staticmethod
    def marubozu(df: pd.DataFrame, shadow_tolerance: float = 0.05) -> pd.DataFrame:
        """
        Identyfikuje formację Marubozu (świeca bez cieni lub z bardzo małymi cieniami).
        
        Args:
            df: DataFrame zawierający dane OHLC.
            shadow_tolerance: Maksymalny stosunek cieni do całej świecy.
            
        Returns:
            pd.DataFrame: DataFrame z dodanymi kolumnami 'bullish_marubozu' i 'bearish_marubozu'.
        """
        # Obliczenie długości ciała
        df['body_size'] = abs(df['close'] - df['open'])
        
        # Obliczenie górnego i dolnego cienia
        df['upper_shadow'] = df.apply(lambda x: x['high'] - max(x['open'], x['close']), axis=1)
        df['lower_shadow'] = df.apply(lambda x: min(x['open'], x['close']) - x['low'], axis=1)
        
        # Obliczenie całkowitej długości świecy
        df['candle_range'] = df['high'] - df['low']
        
        # Identyfikacja Marubozu
        df['bullish_marubozu'] = (
            (df['close'] > df['open']) &
            (df['upper_shadow'] / df['candle_range'] <= shadow_tolerance) &
            (df['lower_shadow'] / df['candle_range'] <= shadow_tolerance)
        )
        
        df['bearish_marubozu'] = (
            (df['close'] < df['open']) &
            (df['upper_shadow'] / df['candle_range'] <= shadow_tolerance) &
            (df['lower_shadow'] / df['candle_range'] <= shadow_tolerance)
        )
        
        # Usunięcie kolumn pomocniczych
        df.drop(['body_size', 'upper_shadow', 'lower_shadow', 'candle_range'], axis=1, inplace=True)
        
        return df
    
    @staticmethod
    def engulfing(df: pd.DataFrame) -> pd.DataFrame:
        """
        Identyfikuje formację Engulfing (objęcie) - druga świeca całkowicie obejmuje ciało pierwszej.
        
        Args:
            df: DataFrame zawierający dane OHLC.
            
        Returns:
            pd.DataFrame: DataFrame z dodanymi kolumnami 'bullish_engulfing' i 'bearish_engulfing'.
        """
        # Poprzednie wartości
        df['prev_open'] = df['open'].shift(1)
        df['prev_close'] = df['close'].shift(1)
        
        # Identyfikacja Bullish Engulfing (objęcie hossy)
        df['bullish_engulfing'] = (
            (df['close'] > df['open']) &  # Biała/zielona świeca
            (df['prev_close'] < df['prev_open']) &  # Poprzednia czarna/czerwona świeca
            (df['open'] < df['prev_close']) &  # Otwarcie poniżej zamknięcia poprzedniej
            (df['close'] > df['prev_open'])  # Zamknięcie powyżej otwarcia poprzedniej
        )
        
        # Identyfikacja Bearish Engulfing (objęcie bessy)
        df['bearish_engulfing'] = (
            (df['close'] < df['open']) &  # Czarna/czerwona świeca
            (df['prev_close'] > df['prev_open']) &  # Poprzednia biała/zielona świeca
            (df['open'] > df['prev_close']) &  # Otwarcie powyżej zamknięcia poprzedniej
            (df['close'] < df['prev_open'])  # Zamknięcie poniżej otwarcia poprzedniej
        )
        
        # Usunięcie kolumn pomocniczych
        df.drop(['prev_open', 'prev_close'], axis=1, inplace=True)
        
        return df
    
    @staticmethod
    def harami(df: pd.DataFrame) -> pd.DataFrame:
        """
        Identyfikuje formację Harami - druga świeca całkowicie zawiera się w ciele pierwszej.
        
        Args:
            df: DataFrame zawierający dane OHLC.
            
        Returns:
            pd.DataFrame: DataFrame z dodanymi kolumnami 'bullish_harami' i 'bearish_harami'.
        """
        # Poprzednie wartości
        df['prev_open'] = df['open'].shift(1)
        df['prev_close'] = df['close'].shift(1)
        
        # Identyfikacja Bullish Harami
        df['bullish_harami'] = (
            (df['close'] > df['open']) &  # Biała/zielona świeca
            (df['prev_close'] < df['prev_open']) &  # Poprzednia czarna/czerwona świeca
            (df['open'] >= df['prev_close']) &  # Otwarcie powyżej lub równe zamknięciu poprzedniej
            (df['close'] <= df['prev_open']) &  # Zamknięcie poniżej lub równe otwarciu poprzedniej
            (df['open'] < df['prev_open']) &  # Otwarcie poniżej otwarcia poprzedniej
            (df['close'] > df['prev_close'])  # Zamknięcie powyżej zamknięcia poprzedniej
        )
        
        # Identyfikacja Bearish Harami
        df['bearish_harami'] = (
            (df['close'] < df['open']) &  # Czarna/czerwona świeca
            (df['prev_close'] > df['prev_open']) &  # Poprzednia biała/zielona świeca
            (df['open'] <= df['prev_close']) &  # Otwarcie poniżej lub równe zamknięciu poprzedniej
            (df['close'] >= df['prev_open']) &  # Zamknięcie powyżej lub równe otwarciu poprzedniej
            (df['open'] > df['prev_open']) &  # Otwarcie powyżej otwarcia poprzedniej
            (df['close'] < df['prev_close'])  # Zamknięcie poniżej zamknięcia poprzedniej
        )
        
        # Usunięcie kolumn pomocniczych
        df.drop(['prev_open', 'prev_close'], axis=1, inplace=True)
        
        return df
    
    @staticmethod
    def morning_star(df: pd.DataFrame, doji_ratio: float = 0.1) -> pd.DataFrame:
        """
        Identyfikuje formację Morning Star (gwiazda poranna) - formacja zwiastująca odwrócenie trendu spadkowego.
        
        Args:
            df: DataFrame zawierający dane OHLC.
            doji_ratio: Maksymalny stosunek długości ciała do zakresu high-low dla środkowej świecy.
            
        Returns:
            pd.DataFrame: DataFrame z dodaną kolumną 'morning_star'.
        """
        # Poprzednie wartości
        df['prev_open'] = df['open'].shift(2)
        df['prev_close'] = df['close'].shift(2)
        df['prev_high'] = df['high'].shift(2)
        df['prev_low'] = df['low'].shift(2)
        
        df['mid_open'] = df['open'].shift(1)
        df['mid_close'] = df['close'].shift(1)
        df['mid_high'] = df['high'].shift(1)
        df['mid_low'] = df['low'].shift(1)
        
        # Obliczenie długości ciała środkowej świecy
        df['mid_body_size'] = abs(df['mid_close'] - df['mid_open'])
        df['mid_range'] = df['mid_high'] - df['mid_low']
        
        # Identyfikacja Morning Star (gwiazda poranna)
        df['morning_star'] = (
            (df['prev_close'] < df['prev_open']) &  # Pierwsza świeca spadkowa
            (df['mid_body_size'] / df['mid_range'] <= doji_ratio) &  # Środkowa świeca mała (doji lub prawie doji)
            (df['close'] > df['open']) &  # Trzecia świeca wzrostowa
            (df['mid_high'] < df['prev_close']) &  # Środkowa świeca poniżej zamknięcia pierwszej
            (df['open'] > df['mid_high']) &  # Trzecia świeca otwiera się powyżej środkowej
            (df['close'] > ((df['prev_open'] - df['prev_close']) / 2 + df['prev_close']))  # Trzecia świeca zamyka się powyżej środka pierwszej
        )
        
        # Usunięcie kolumn pomocniczych
        df.drop(['prev_open', 'prev_close', 'prev_high', 'prev_low',
                'mid_open', 'mid_close', 'mid_high', 'mid_low',
                'mid_body_size', 'mid_range'], axis=1, inplace=True)
        
        return df
    
    @staticmethod
    def evening_star(df: pd.DataFrame, doji_ratio: float = 0.1) -> pd.DataFrame:
        """
        Identyfikuje formację Evening Star (gwiazda wieczorna) - formacja zwiastująca odwrócenie trendu wzrostowego.
        
        Args:
            df: DataFrame zawierający dane OHLC.
            doji_ratio: Maksymalny stosunek długości ciała do zakresu high-low dla środkowej świecy.
            
        Returns:
            pd.DataFrame: DataFrame z dodaną kolumną 'evening_star'.
        """
        # Poprzednie wartości
        df['prev_open'] = df['open'].shift(2)
        df['prev_close'] = df['close'].shift(2)
        df['prev_high'] = df['high'].shift(2)
        df['prev_low'] = df['low'].shift(2)
        
        df['mid_open'] = df['open'].shift(1)
        df['mid_close'] = df['close'].shift(1)
        df['mid_high'] = df['high'].shift(1)
        df['mid_low'] = df['low'].shift(1)
        
        # Obliczenie długości ciała środkowej świecy
        df['mid_body_size'] = abs(df['mid_close'] - df['mid_open'])
        df['mid_range'] = df['mid_high'] - df['mid_low']
        
        # Identyfikacja Evening Star (gwiazda wieczorna)
        df['evening_star'] = (
            (df['prev_close'] > df['prev_open']) &  # Pierwsza świeca wzrostowa
            (df['mid_body_size'] / df['mid_range'] <= doji_ratio) &  # Środkowa świeca mała (doji lub prawie doji)
            (df['close'] < df['open']) &  # Trzecia świeca spadkowa
            (df['mid_low'] > df['prev_close']) &  # Środkowa świeca powyżej zamknięcia pierwszej
            (df['open'] < df['mid_low']) &  # Trzecia świeca otwiera się poniżej środkowej
            (df['close'] < ((df['prev_close'] - df['prev_open']) / 2 + df['prev_open']))  # Trzecia świeca zamyka się poniżej środka pierwszej
        )
        
        # Usunięcie kolumn pomocniczych
        df.drop(['prev_open', 'prev_close', 'prev_high', 'prev_low',
                'mid_open', 'mid_close', 'mid_high', 'mid_low',
                'mid_body_size', 'mid_range'], axis=1, inplace=True)
        
        return df
    
    @staticmethod
    def three_white_soldiers(df: pd.DataFrame, shadow_ratio: float = 0.3) -> pd.DataFrame:
        """
        Identyfikuje formację Three White Soldiers (trzy białe/zielone świece) - formacja wzrostowa.
        
        Args:
            df: DataFrame zawierający dane OHLC.
            shadow_ratio: Maksymalny stosunek górnego cienia do długości ciała.
            
        Returns:
            pd.DataFrame: DataFrame z dodaną kolumną 'three_white_soldiers'.
        """
        # Poprzednie wartości
        df['prev_open1'] = df['open'].shift(1)
        df['prev_close1'] = df['close'].shift(1)
        df['prev_high1'] = df['high'].shift(1)
        
        df['prev_open2'] = df['open'].shift(2)
        df['prev_close2'] = df['close'].shift(2)
        df['prev_high2'] = df['high'].shift(2)
        
        # Obliczenie długości ciała i górnych cieni
        df['body1'] = df['close'] - df['open']
        df['body2'] = df['prev_close1'] - df['prev_open1']
        df['body3'] = df['prev_close2'] - df['prev_open2']
        
        df['upper_shadow1'] = df['high'] - df['close']
        df['upper_shadow2'] = df['prev_high1'] - df['prev_close1']
        df['upper_shadow3'] = df['prev_high2'] - df['prev_close2']
        
        # Identyfikacja Three White Soldiers
        df['three_white_soldiers'] = (
            (df['body1'] > 0) & (df['body2'] > 0) & (df['body3'] > 0) &  # Wszystkie trzy świece wzrostowe
            (df['open'] > df['prev_open1']) & (df['open'] < df['prev_close1']) &  # Otwarcie drugiej i trzeciej świecy
            (df['prev_open1'] > df['prev_open2']) & (df['prev_open1'] < df['prev_close2']) &  # wewnątrz ciała poprzedniej
            (df['close'] > df['prev_close1']) & (df['prev_close1'] > df['prev_close2']) &  # Każde zamknięcie wyższe niż poprzednie
            (df['upper_shadow1'] / (df['body1'] + 0.0001) <= shadow_ratio) &  # Małe górne cienie
            (df['upper_shadow2'] / (df['body2'] + 0.0001) <= shadow_ratio) &
            (df['upper_shadow3'] / (df['body3'] + 0.0001) <= shadow_ratio)
        )
        
        # Usunięcie kolumn pomocniczych
        df.drop(['prev_open1', 'prev_close1', 'prev_high1',
                'prev_open2', 'prev_close2', 'prev_high2',
                'body1', 'body2', 'body3',
                'upper_shadow1', 'upper_shadow2', 'upper_shadow3'], axis=1, inplace=True)
        
        return df
    
    @staticmethod
    def three_black_crows(df: pd.DataFrame, shadow_ratio: float = 0.3) -> pd.DataFrame:
        """
        Identyfikuje formację Three Black Crows (trzy czarne/czerwone świece) - formacja spadkowa.
        
        Args:
            df: DataFrame zawierający dane OHLC.
            shadow_ratio: Maksymalny stosunek dolnego cienia do długości ciała.
            
        Returns:
            pd.DataFrame: DataFrame z dodaną kolumną 'three_black_crows'.
        """
        # Poprzednie wartości
        df['prev_open1'] = df['open'].shift(1)
        df['prev_close1'] = df['close'].shift(1)
        df['prev_low1'] = df['low'].shift(1)
        
        df['prev_open2'] = df['open'].shift(2)
        df['prev_close2'] = df['close'].shift(2)
        df['prev_low2'] = df['low'].shift(2)
        
        # Obliczenie długości ciała i dolnych cieni
        df['body1'] = df['open'] - df['close']
        df['body2'] = df['prev_open1'] - df['prev_close1']
        df['body3'] = df['prev_open2'] - df['prev_close2']
        
        df['lower_shadow1'] = df['close'] - df['low']
        df['lower_shadow2'] = df['prev_close1'] - df['prev_low1']
        df['lower_shadow3'] = df['prev_close2'] - df['prev_low2']
        
        # Identyfikacja Three Black Crows
        df['three_black_crows'] = (
            (df['body1'] > 0) & (df['body2'] > 0) & (df['body3'] > 0) &  # Wszystkie trzy świece spadkowe
            (df['open'] < df['prev_open1']) & (df['open'] > df['prev_close1']) &  # Otwarcie drugiej i trzeciej świecy
            (df['prev_open1'] < df['prev_open2']) & (df['prev_open1'] > df['prev_close2']) &  # wewnątrz ciała poprzedniej
            (df['close'] < df['prev_close1']) & (df['prev_close1'] < df['prev_close2']) &  # Każde zamknięcie niższe niż poprzednie
            (df['lower_shadow1'] / (df['body1'] + 0.0001) <= shadow_ratio) &  # Małe dolne cienie
            (df['lower_shadow2'] / (df['body2'] + 0.0001) <= shadow_ratio) &
            (df['lower_shadow3'] / (df['body3'] + 0.0001) <= shadow_ratio)
        )
        
        # Usunięcie kolumn pomocniczych
        df.drop(['prev_open1', 'prev_close1', 'prev_low1',
                'prev_open2', 'prev_close2', 'prev_low2',
                'body1', 'body2', 'body3',
                'lower_shadow1', 'lower_shadow2', 'lower_shadow3'], axis=1, inplace=True)
        
        return df 
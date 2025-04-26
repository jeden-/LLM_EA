"""
Moduł zawierający zaawansowane wskaźniki techniczne dla analiz rynkowych.
Rozszerza podstawowy moduł technical_indicators.py o bardziej złożone wskaźniki.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Union, Optional, Tuple, Any
from LLM_Engine.technical_indicators import TechnicalIndicators

class AdvancedIndicators(TechnicalIndicators):
    """
    Klasa zawierająca zaawansowane wskaźniki techniczne używane w analizie rynków finansowych.
    Dziedziczy po klasie TechnicalIndicators.
    """
    
    def __init__(self):
        """Inicjalizacja klasy AdvancedIndicators."""
        super().__init__()
    
    def calculate_atr(
        self, 
        high_series: pd.Series, 
        low_series: pd.Series, 
        close_series: pd.Series, 
        period: int = 14
    ) -> pd.Series:
        """
        Oblicza Average True Range (ATR) - wskaźnik zmienności rynku.
        
        ATR mierzy zmienność rynku bez uwzględniania kierunku ruchu ceny.
        Jest średnią kroczącą z "True Range" (TR), który jest największą z poniższych wartości:
        - Różnica między obecnym high a obecnym low
        - Różnica między poprzednim close a obecnym high
        - Różnica między poprzednim close a obecnym low
        
        ATR często wykorzystywany jest do określania wielkości stop-loss lub do
        identyfikacji okresów zwiększonej zmienności na rynku.
        
        Args:
            high_series: Seria danych najwyższych cen
            low_series: Seria danych najniższych cen
            close_series: Seria danych cen zamknięcia
            period: Okres dla ATR (domyślnie 14)
            
        Returns:
            Seria pandas zawierająca wartości ATR
            
        Raises:
            ValueError: Jeśli serie są różnej długości, są puste lub zawierają mniej punktów niż okres
        """
        # Walidacja danych wejściowych
        if high_series is None or low_series is None or close_series is None:
            raise ValueError("Serie danych nie mogą być puste")
            
        if len(high_series) != len(low_series) or len(high_series) != len(close_series):
            raise ValueError("Wszystkie serie danych muszą mieć tę samą długość")
            
        if len(high_series) < period + 1:
            raise ValueError(f"Serie danych muszą zawierać co najmniej {period + 1} punktów dla okresu {period}")
            
        if period <= 0:
            raise ValueError("Okres musi być większy od zera")
        
        # Obliczenie True Range
        high_low = high_series - low_series
        high_close = np.abs(high_series - close_series.shift(1))
        low_close = np.abs(low_series - close_series.shift(1))
        
        # Utworzenie ramki danych zawierającej wszystkie trzy wartości
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        
        # Wybór maksymalnej wartości dla każdego wiersza
        true_range = ranges.max(axis=1)
        
        # Obliczenie ATR jako wykładniczej średniej kroczącej z True Range
        atr = true_range.ewm(span=period, adjust=False).mean()
        
        return atr
    
    def calculate_adx(
        self, 
        high_series: pd.Series, 
        low_series: pd.Series, 
        close_series: pd.Series, 
        period: int = 14
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Oblicza Average Directional Index (ADX) i wskaźniki kierunkowe (DI+ i DI-).
        
        Args:
            high_series: Seria danych najwyższych cen
            low_series: Seria danych najniższych cen
            close_series: Seria danych cen zamknięcia
            period: Okres dla ADX (domyślnie 14)
            
        Returns:
            Tuple zawierający (ADX, DI+, DI-)
        """
        # Walidacja danych wejściowych
        if high_series is None or low_series is None or close_series is None:
            raise ValueError("Serie danych nie mogą być puste")
            
        if len(high_series) != len(low_series) or len(high_series) != len(close_series):
            raise ValueError("Wszystkie serie danych muszą mieć tę samą długość")
            
        if len(high_series) < period + 1:
            raise ValueError(f"Serie danych muszą zawierać co najmniej {period + 1} punktów dla okresu {period}")
            
        if period <= 0:
            raise ValueError("Okres musi być większy od zera")
            
        # Utwórz serie o tej samej długości co dane wejściowe
        adx_result = pd.Series(np.nan, index=close_series.index)
        plus_di_result = pd.Series(np.nan, index=close_series.index)
        minus_di_result = pd.Series(np.nan, index=close_series.index)
        
        # Jeśli mamy zbyt mało danych, zwróć puste serie
        if len(high_series) <= 2 * period:
            return adx_result, plus_di_result, minus_di_result
        
        # Obliczenie ATR
        atr = self.calculate_atr(high_series, low_series, close_series, period)
        
        # Obliczenie +DM i -DM (Directional Movement)
        high_diff = high_series.diff()
        low_diff = low_series.diff()
        
        plus_dm = high_diff.copy()
        minus_dm = low_diff.copy().abs()
        
        # Zastosowanie warunków dla +DM
        condition1 = high_diff > low_diff.abs()
        condition2 = high_diff > 0
        plus_dm = plus_dm.where(condition1 & condition2, 0)
        
        # Zastosowanie warunków dla -DM
        condition1 = low_diff.abs() > high_diff
        condition2 = low_diff < 0
        minus_dm = minus_dm.where(condition1 & condition2, 0)
        
        # Obliczenie +DI i -DI
        plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)
        
        # Obliczenie DX (Directional Index)
        dx = 100 * (np.abs(plus_di - minus_di) / (plus_di + minus_di))
        
        # Obliczenie ADX
        adx_calc = dx.ewm(span=period, adjust=False).mean()
        
        # Przypisanie obliczonych wartości do wynikowych serii
        valid_indices = ~np.isnan(adx_calc)
        adx_result.loc[valid_indices] = adx_calc.loc[valid_indices]
        plus_di_result.loc[valid_indices] = plus_di.loc[valid_indices]
        minus_di_result.loc[valid_indices] = minus_di.loc[valid_indices]
        
        return adx_result, plus_di_result, minus_di_result
    
    def calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                           k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """
        Oblicza oscylator stochastyczny.
        
        Args:
            high: Szereg czasowy cen najwyższych
            low: Szereg czasowy cen najniższych
            close: Szereg czasowy cen zamknięcia
            k_period: Okres dla %K (domyślnie 14)
            d_period: Okres dla %D (domyślnie 3)
            
        Returns:
            Krotka (%K, %D)
        """
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d = k.rolling(window=d_period).mean()
        
        return k, d
    
    def calculate_ichimoku(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                         tenkan_period: int = 9, kijun_period: int = 26, 
                         senkou_span_b_period: int = 52) -> Dict[str, pd.Series]:
        """
        Oblicza wskaźnik Ichimoku Cloud.
        
        Args:
            high: Szereg czasowy cen najwyższych
            low: Szereg czasowy cen najniższych
            close: Szereg czasowy cen zamknięcia
            tenkan_period: Okres dla Tenkan-sen (domyślnie 9)
            kijun_period: Okres dla Kijun-sen (domyślnie 26)
            senkou_span_b_period: Okres dla Senkou Span B (domyślnie 52)
            
        Returns:
            Słownik z komponentami Ichimoku
        """
        # Tenkan-sen (Conversion Line)
        tenkan_sen = (high.rolling(window=tenkan_period).max() + 
                      low.rolling(window=tenkan_period).min()) / 2
        
        # Kijun-sen (Base Line)
        kijun_sen = (high.rolling(window=kijun_period).max() + 
                     low.rolling(window=kijun_period).min()) / 2
        
        # Senkou Span A (Leading Span A)
        senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun_period)
        
        # Senkou Span B (Leading Span B)
        senkou_span_b = ((high.rolling(window=senkou_span_b_period).max() + 
                          low.rolling(window=senkou_span_b_period).min()) / 2).shift(kijun_period)
        
        # Chikou Span (Lagging Span)
        chikou_span = close.shift(-kijun_period)
        
        return {
            'tenkan_sen': tenkan_sen,
            'kijun_sen': kijun_sen,
            'senkou_span_a': senkou_span_a,
            'senkou_span_b': senkou_span_b,
            'chikou_span': chikou_span
        }
    
    def calculate_fibonacci_retracement(self, high: float, low: float) -> Dict[str, float]:
        """
        Oblicza poziomy zniesienia Fibonacciego.
        
        Args:
            high: Wartość szczytu
            low: Wartość dołka
            
        Returns:
            Słownik z poziomami zniesienia
        """
        diff = high - low
        
        levels = {
            '0.0': low,
            '0.236': low + diff * 0.236,
            '0.382': low + diff * 0.382,
            '0.5': low + diff * 0.5,
            '0.618': low + diff * 0.618,
            '0.786': low + diff * 0.786,
            '1.0': high
        }
        
        return levels 
"""
Moduł zawierający klasy i funkcje do obliczania wskaźników technicznych rynkowych.
Służy jako warstwa abstrakcji dla różnych bibliotek wskaźników technicznych.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Union, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """
    Klasa zawierająca implementacje popularnych wskaźników technicznych używanych w analizie rynków finansowych.
    Wskaźniki są zoptymalizowane pod kątem wydajności i dokładności obliczeń.
    """
    
    def __init__(self):
        """Inicjalizacja klasy TechnicalIndicators."""
        pass
    
    def calculate_sma(self, price_series: pd.Series, period: int) -> pd.Series:
        """
        Oblicza Simple Moving Average (SMA) dla danej serii cenowej.
        
        Args:
            price_series: Seria danych cenowych (zazwyczaj ceny zamknięcia)
            period: Okres dla średniej kroczącej
            
        Returns:
            Seria pandas zawierająca wartości SMA
        """
        return price_series.rolling(window=period).mean()
    
    def calculate_ema(self, price_series: pd.Series, period: int) -> pd.Series:
        """
        Oblicza Exponential Moving Average (EMA) dla danej serii cenowej.
        
        Args:
            price_series: Seria danych cenowych (zazwyczaj ceny zamknięcia)
            period: Okres dla wykładniczej średniej kroczącej
            
        Returns:
            Seria pandas zawierająca wartości EMA
        """
        return price_series.ewm(span=period, adjust=False).mean()
    
    def calculate_rsi(self, price_series: pd.Series, period: int = 14) -> pd.Series:
        """
        Oblicza Relative Strength Index (RSI) dla danej serii cenowej.
        
        Args:
            price_series: Seria danych cenowych (zazwyczaj ceny zamknięcia)
            period: Okres dla RSI (domyślnie 14)
            
        Returns:
            Seria pandas zawierająca wartości RSI
        """
        # Obliczenie zmian cen
        delta = price_series.diff()
        
        # Oddzielenie wzrostów i spadków
        gains = delta.copy()
        losses = delta.copy()
        gains[gains < 0] = 0
        losses[losses > 0] = 0
        losses = abs(losses)
        
        # Obliczenie średnich wzrostów i spadków
        avg_gain = gains.rolling(window=period).mean()
        avg_loss = losses.rolling(window=period).mean()
        
        # Obliczenie RS (Relative Strength)
        rs = avg_gain / avg_loss
        
        # Obliczenie RSI
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_macd(self, series, fast_period=12, slow_period=26, signal_period=9):
        """
        Oblicza wskaźnik MACD (Moving Average Convergence Divergence).
        
        Args:
            series: Szereg cenowy
            fast_period: Okres szybkiej średniej EMA
            slow_period: Okres wolnej średniej EMA
            signal_period: Okres linii sygnału
            
        Returns:
            Słownik zawierający komponenty MACD:
            - 'macd': Linia MACD (różnica między szybką i wolną średnią)
            - 'signal': Linia sygnałowa (EMA z linii MACD)
            - 'histogram': Histogram (różnica między linią MACD a linią sygnału)
        """
        # Sprawdź, czy mamy wystarczającą ilość danych
        if len(series) < max(fast_period, slow_period, signal_period):
            logger.warning(f"Za mało danych do obliczenia MACD. Wymagane: {max(fast_period, slow_period, signal_period)}, otrzymane: {len(series)}")
            return {'macd': pd.Series(), 'signal': pd.Series(), 'histogram': pd.Series()}
        
        try:
            # Oblicz szybką i wolną średnią
            fast_ema = self.calculate_ema(series, period=fast_period)
            slow_ema = self.calculate_ema(series, period=slow_period)
            
            # Oblicz linię MACD jako różnicę między szybką a wolną średnią
            macd_line = fast_ema - slow_ema
            
            # Oblicz linię sygnałową jako EMA z linii MACD
            signal_line = self.calculate_ema(macd_line, period=signal_period)
            
            # Oblicz histogram jako różnicę między linią MACD a linią sygnału
            histogram = macd_line - signal_line
            
            # Zwróć słownik z komponentami
            return {
                'macd': macd_line,
                'signal': signal_line,
                'histogram': histogram
            }
        except Exception as e:
            logger.error(f"Błąd podczas obliczania MACD: {e}")
            return {'macd': pd.Series(), 'signal': pd.Series(), 'histogram': pd.Series()}
    
    def calculate_bollinger_bands(
        self, 
        price_series: pd.Series, 
        period: int = 20, 
        num_std: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Oblicza Bollinger Bands dla danej serii cenowej.
        
        Wskaźnik Bollinger Bands składa się z trzech linii:
        - Środkowej: jest to SMA za dany okres
        - Górnej: środkowa linia + (num_std * odchylenie standardowe)
        - Dolnej: środkowa linia - (num_std * odchylenie standardowe)
        
        Szerokość wstęg dostosowuje się do zmienności rynku - rozszerzają się
        w okresach wysokiej zmienności i zwężają w okresach niskiej zmienności.
        
        Args:
            price_series: Seria danych cenowych (zazwyczaj ceny zamknięcia)
            period: Okres dla średniej kroczącej (domyślnie 20)
            num_std: Liczba odchyleń standardowych (domyślnie 2.0)
            
        Returns:
            Tuple zawierający (górna wstęga, środkowa wstęga, dolna wstęga)
            
        Raises:
            ValueError: Jeśli price_series jest pusta lub zawiera mniej punktów niż okres
        """
        # Walidacja danych wejściowych
        if price_series is None or len(price_series) == 0:
            raise ValueError("Seria cenowa nie może być pusta")
            
        if len(price_series) < period:
            raise ValueError(f"Seria cenowa musi zawierać co najmniej {period} punktów dla okresu {period}")
            
        if period <= 0:
            raise ValueError("Okres musi być większy od zera")
            
        if num_std < 0:
            raise ValueError("Liczba odchyleń standardowych nie może być ujemna")
        
        # Obliczenie środkowej wstęgi (SMA)
        middle_band = self.calculate_sma(price_series, period)
        
        # Obliczenie odchylenia standardowego
        rolling_std = price_series.rolling(window=period).std()
        
        # Obliczenie górnej i dolnej wstęgi
        upper_band = middle_band + (rolling_std * num_std)
        lower_band = middle_band - (rolling_std * num_std)
        
        return upper_band, middle_band, lower_band

class CalculateIndicators(TechnicalIndicators):
    """
    Klasa rozszerzająca TechnicalIndicators o dodatkowe funkcjonalności.
    Służy jako główny interfejs do obliczania wskaźników technicznych w systemie.
    """
    
    def __init__(self):
        """Inicjalizacja klasy CalculateIndicators."""
        super().__init__()
        
    def calculate_ma(self, price_series: pd.Series, period: int) -> pd.Series:
        """
        Alias dla calculate_sma dla zachowania kompatybilności.
        
        Args:
            price_series: Seria danych cenowych
            period: Okres dla średniej kroczącej
            
        Returns:
            pd.Series: Seria z obliczoną średnią kroczącą
        """
        return self.calculate_sma(price_series, period)
        
    def calculate_all_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Oblicza wszystkie dostępne wskaźniki techniczne dla danych wejściowych.
        
        Args:
            data: DataFrame z danymi cenowymi (OHLCV)
            
        Returns:
            Dict[str, Any]: Słownik zawierający wszystkie obliczone wskaźniki
        """
        if data is None or data.empty:
            logger.warning("Otrzymano puste dane wejściowe")
            return {}
            
        try:
            close_prices = data['close']
            
            # Obliczenie podstawowych wskaźników
            indicators = {
                'sma_20': self.calculate_sma(close_prices, 20),
                'sma_50': self.calculate_sma(close_prices, 50),
                'sma_200': self.calculate_sma(close_prices, 200),
                'ema_12': self.calculate_ema(close_prices, 12),
                'ema_26': self.calculate_ema(close_prices, 26),
                'rsi': self.calculate_rsi(close_prices),
                'macd': self.calculate_macd(close_prices)
            }
            
            # Obliczenie Bollinger Bands
            upper, middle, lower = self.calculate_bollinger_bands(close_prices)
            indicators.update({
                'bb_upper': upper,
                'bb_middle': middle,
                'bb_lower': lower
            })
            
            return indicators
            
        except Exception as e:
            logger.error(f"Błąd podczas obliczania wskaźników: {e}")
            return {} 
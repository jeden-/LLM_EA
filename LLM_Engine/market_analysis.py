import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Union, Optional, Any
import logging

from .technical_indicators import TechnicalIndicators

class MarketAnalysis:
    """
    Klasa do analizy rynku finansowego wykorzystująca wskaźniki techniczne 
    i inne metody do wykrywania sygnałów transakcyjnych oraz analizy trendów.
    """
    
    def __init__(self):
        """Inicjalizacja analizatora rynku."""
        self.indicators = TechnicalIndicators()
        self.logger = logging.getLogger(__name__)
    
    def analyze_trend(self, prices: pd.Series) -> Dict[str, Any]:
        """
        Analizuje trend cenowy i jego właściwości.
        
        Args:
            prices: Seria cenowa
            
        Returns:
            Słownik zawierający informacje o trendzie:
                - trend: str - kierunek trendu (bullish, bearish, sideways)
                - strength: int - siła trendu (1-10)
                - volatility: str - zmienność (low, average, high)
                - description: str - opis trendu
                - support_levels: list - poziomy wsparcia
                - resistance_levels: list - poziomy oporu
        """
        if len(prices) < 20:
            self.logger.warning("Za mało danych do analizy trendu (minimum 20 świec).")
            return {
                "trend": "unknown",
                "strength": 0,
                "volatility": "unknown",
                "description": "Niewystarczająca ilość danych do analizy",
                "support_levels": [],
                "resistance_levels": []
            }
            
        # Identyfikacja trendu na podstawie średnich kroczących
        sma20 = prices.rolling(window=20).mean()
        sma50 = prices.rolling(window=50).mean() if len(prices) >= 50 else None
        sma200 = prices.rolling(window=200).mean() if len(prices) >= 200 else None
        
        # Trend bazowy na podstawie SMA20 i aktualnej ceny
        current_price = prices.iloc[-1]
        previous_price = prices.iloc[-2]
        
        if sma200 is not None and len(sma200.dropna()) > 0:
            # Mamy wystarczająco dużo danych dla SMA200
            sma200_last = sma200.iloc[-1]
            if current_price > sma200_last and sma20.iloc[-1] > sma200_last:
                trend = "bullish"
            elif current_price < sma200_last and sma20.iloc[-1] < sma200_last:
                trend = "bearish"
            else:
                # Sprawdzamy krótszy trend
                if current_price > sma20.iloc[-1] and previous_price > sma20.iloc[-1]:
                    trend = "bullish"
                elif current_price < sma20.iloc[-1] and previous_price < sma20.iloc[-1]:
                    trend = "bearish"
                else:
                    trend = "sideways"
        elif sma50 is not None and len(sma50.dropna()) > 0:
            # Używamy SMA50 jeśli nie mamy SMA200
            sma50_last = sma50.iloc[-1]
            if current_price > sma50_last and sma20.iloc[-1] > sma50_last:
                trend = "bullish"
            elif current_price < sma50_last and sma20.iloc[-1] < sma50_last:
                trend = "bearish"
            else:
                if current_price > sma20.iloc[-1]:
                    trend = "bullish"
                elif current_price < sma20.iloc[-1]:
                    trend = "bearish"
                else:
                    trend = "sideways"
        else:
            # Używamy tylko SMA20 i kierunku ceny
            sma20_last = sma20.iloc[-1]
            price_direction = prices.iloc[-5:].pct_change().mean()
            
            if current_price > sma20_last and price_direction > 0:
                trend = "bullish"
            elif current_price < sma20_last and price_direction < 0:
                trend = "bearish"
            else:
                trend = "sideways"
                
        # Siła trendu (1-10)
        strength = self._calculate_trend_strength(prices)
        
        # Zmienność
        volatility = self._calculate_volatility(prices)
        
        # Poziomy wsparcia i oporu
        support_resistance = self.detect_support_resistance(prices)
        
        # Opis trendu
        if trend == "bullish":
            description = "Trend wzrostowy"
            if strength >= 8:
                description += " silny"
            elif strength >= 5:
                description += " umiarkowany"
            else:
                description += " słaby"
        elif trend == "bearish":
            description = "Trend spadkowy"
            if strength >= 8:
                description += " silny"
            elif strength >= 5:
                description += " umiarkowany"
            else:
                description += " słaby"
        else:
            description = "Trend boczny"
            if volatility == "high":
                description += " z dużą zmiennością"
            elif volatility == "low":
                description += " z niską zmiennością"
                
        return {
            "trend": trend,
            "strength": strength,
            "volatility": volatility,
            "description": description,
            "support_levels": support_resistance["support"],
            "resistance_levels": support_resistance["resistance"]
        }
    
    def detect_support_resistance(self, prices: pd.Series, 
                                 window: int = 10, 
                                 threshold: float = 0.02) -> Dict[str, List[float]]:
        """
        Wykrywanie poziomów wsparcia i oporu.
        
        Args:
            prices: Seria cenowa
            window: Okno do wykrywania lokalnych minimów i maksimów
            threshold: Próg odchylenia do grupowania poziomów (jako % wartości)
            
        Returns:
            Dict zawierający listę poziomów wsparcia i oporu
        """
        # Znajdujemy lokalne minima i maksima
        local_max = []
        local_min = []
        
        for i in range(window, len(prices) - window):
            if prices.iloc[i] > max(prices.iloc[i-window:i]) and prices.iloc[i] > max(prices.iloc[i+1:i+window+1]):
                local_max.append(prices.iloc[i])
            
            if prices.iloc[i] < min(prices.iloc[i-window:i]) and prices.iloc[i] < min(prices.iloc[i+1:i+window+1]):
                local_min.append(prices.iloc[i])
        
        # Grupowanie podobnych poziomów
        support_levels = self._group_similar_levels(local_min, threshold)
        resistance_levels = self._group_similar_levels(local_max, threshold)
        
        return {
            "support": support_levels,
            "resistance": resistance_levels
        }
    
    def _group_similar_levels(self, levels: List[float], threshold: float) -> List[float]:
        """
        Grupowanie podobnych poziomów cenowych.
        
        Args:
            levels: Lista poziomów cenowych
            threshold: Próg odchylenia (jako % wartości)
            
        Returns:
            Lista zgrupowanych poziomów
        """
        if not levels:
            return []
        
        levels = sorted(levels)
        grouped = []
        current_group = [levels[0]]
        
        for i in range(1, len(levels)):
            if levels[i] <= current_group[0] * (1 + threshold) and levels[i] >= current_group[0] * (1 - threshold):
                current_group.append(levels[i])
            else:
                grouped.append(sum(current_group) / len(current_group))
                current_group = [levels[i]]
        
        if current_group:
            grouped.append(sum(current_group) / len(current_group))
        
        return grouped
    
    def generate_buy_signals(self, prices: pd.Series, volumes: Optional[pd.Series] = None) -> pd.Series:
        """
        Generuje sygnały kupna na podstawie kombinacji wskaźników.
        
        Args:
            prices: Seria cenowa
            volumes: Opcjonalna seria wolumenów
            
        Returns:
            Seria boolowska z wartościami True dla sygnałów kupna
        """
        if len(prices) < 50:
            self.logger.warning("Za mało danych do generowania sygnałów kupna.")
            return pd.Series([False] * len(prices), index=prices.index)
        
        # Obliczamy potrzebne wskaźniki
        rsi = self.indicators.calculate_rsi(prices)
        macd_data = self.indicators.calculate_macd(prices)
        macd_line, signal_line = macd_data['macd'], macd_data['signal']
        upper, middle, lower = self.indicators.calculate_bollinger_bands(prices, period=20, num_std=2)
        
        # Inicjalizacja serii sygnałów
        buy_signals = pd.Series(False, index=prices.index)
        
        # Sygnał 1: Przecięcie MACD i linii sygnałowej od dołu
        macd_crossover = (macd_line.shift(1) < signal_line.shift(1)) & (macd_line > signal_line)
        
        # Sygnał 2: RSI wychodzi ze strefy wyprzedania (poniżej 30)
        rsi_oversold_exit = (rsi.shift(1) < 30) & (rsi > 30)
        
        # Sygnał 3: Cena dotyka dolnej wstęgi Bollingera i odbija się
        bollinger_bounce = (prices.shift(2) < lower.shift(2)) & (prices.shift(1) < lower.shift(1)) & (prices > prices.shift(1))
        
        # Łączymy sygnały - wystarczy, że jeden z nich jest spełniony
        buy_signals = macd_crossover | rsi_oversold_exit | bollinger_bounce
        
        # Dodatkowa weryfikacja sygnałów za pomocą wolumenu (jeśli dostępny)
        if volumes is not None:
            # Wysoki wolumen potwierdza sygnał
            avg_volume = volumes.rolling(window=20).mean()
            high_volume = volumes > avg_volume * 1.5
            buy_signals = buy_signals & high_volume
        
        return buy_signals
    
    def generate_sell_signals(self, prices: pd.Series, volumes: Optional[pd.Series] = None) -> pd.Series:
        """
        Generuje sygnały sprzedaży na podstawie kombinacji wskaźników.
        
        Args:
            prices: Seria cenowa
            volumes: Opcjonalna seria wolumenów
            
        Returns:
            Seria boolowska z wartościami True dla sygnałów sprzedaży
        """
        if len(prices) < 50:
            self.logger.warning("Za mało danych do generowania sygnałów sprzedaży.")
            return pd.Series([False] * len(prices), index=prices.index)
        
        # Obliczamy potrzebne wskaźniki
        rsi = self.indicators.calculate_rsi(prices)
        macd_data = self.indicators.calculate_macd(prices)
        macd_line, signal_line = macd_data['macd'], macd_data['signal']
        upper, middle, lower = self.indicators.calculate_bollinger_bands(prices, period=20, num_std=2)
        
        # Inicjalizacja serii sygnałów
        sell_signals = pd.Series(False, index=prices.index)
        
        # Sygnał 1: Przecięcie MACD i linii sygnałowej od góry
        macd_crossunder = (macd_line.shift(1) > signal_line.shift(1)) & (macd_line < signal_line)
        
        # Sygnał 2: RSI wchodzi do strefy wykupienia (powyżej 70)
        rsi_overbought = (rsi.shift(1) < 70) & (rsi > 70)
        
        # Sygnał 3: Cena dotyka górnej wstęgi Bollingera i odbija się w dół
        bollinger_rejection = (prices.shift(2) > upper.shift(2)) & (prices.shift(1) > upper.shift(1)) & (prices < prices.shift(1))
        
        # Łączymy sygnały - wystarczy, że jeden z nich jest spełniony
        sell_signals = macd_crossunder | rsi_overbought | bollinger_rejection
        
        # Dodatkowa weryfikacja sygnałów za pomocą wolumenu (jeśli dostępny)
        if volumes is not None:
            # Wysoki wolumen potwierdza sygnał
            avg_volume = volumes.rolling(window=20).mean()
            high_volume = volumes > avg_volume * 1.5
            sell_signals = sell_signals & high_volume
        
        return sell_signals
    
    def identify_market_conditions(self, prices: pd.Series) -> Dict[str, float]:
        """
        Identyfikuje warunki rynkowe i ich siłę.
        
        Args:
            prices: Seria cenowa
            
        Returns:
            Słownik zawierający oceny warunków rynkowych
        """
        if len(prices) < 50:
            self.logger.warning("Za mało danych do identyfikacji warunków rynkowych.")
            return {"trend": 0, "volatility": 0, "momentum": 0}
        
        # Ocena trendu
        trend_strength = self._calculate_trend_strength(prices)
        
        # Ocena zmienności
        volatility = self._calculate_volatility(prices)
        
        # Ocena momentum
        momentum = self._calculate_momentum(prices)
        
        return {
            "trend": trend_strength,     # Od -1 (silny trend spadkowy) do 1 (silny trend wzrostowy)
            "volatility": volatility,    # Od 0 (niska zmienność) do 1 (wysoka zmienność)
            "momentum": momentum         # Od -1 (silne momentum spadkowe) do 1 (silne momentum wzrostowe)
        }
    
    def _calculate_trend_strength(self, prices: pd.Series) -> float:
        """
        Oblicza siłę trendu w zakresie od -1 (trend spadkowy) do 1 (trend wzrostowy).
        
        Args:
            prices: Seria cenowa
            
        Returns:
            float: Siła trendu w zakresie od -1 do 1
        """
        ema20 = self.indicators.calculate_ema(prices, 20).iloc[-1]
        ema50 = self.indicators.calculate_ema(prices, 50).iloc[-1]
        ema100 = self.indicators.calculate_ema(prices, 100).iloc[-1]
        
        # Sprawdzamy relacje między średnimi
        if ema20 > ema50 > ema100:
            # Silny trend wzrostowy
            strength = (ema20 / ema100 - 1) * 10  # Normalizacja 
            return min(strength, 1.0)  # Ograniczenie do 1.0
        
        elif ema20 < ema50 < ema100:
            # Silny trend spadkowy
            strength = (1 - ema20 / ema100) * 10  # Normalizacja
            return max(-strength, -1.0)  # Ograniczenie do -1.0
        
        elif ema20 > ema50:
            # Słaby trend wzrostowy
            return 0.5
        
        elif ema20 < ema50:
            # Słaby trend spadkowy
            return -0.5
        
        else:
            # Brak trendu
            return 0.0
    
    def _calculate_volatility(self, prices: pd.Series) -> float:
        """
        Oblicza względną zmienność rynku w zakresie od 0 do 1.
        
        Args:
            prices: Seria cenowa
            
        Returns:
            float: Miara zmienności w zakresie od 0 do 1
        """
        # Sprawdzenie, czy mamy wystarczająco dużo danych
        if len(prices) < 20:
            self.logger.warning("Za mało danych do obliczenia zmienności (minimum 20 świec).")
            return 0.0
            
        # Obliczamy zmienność jako znormalizowane odchylenie standardowe
        returns = prices.pct_change().dropna()
        if len(returns) < 20:
            return 0.0
            
        current_vol = returns.iloc[-20:].std() * np.sqrt(252)  # Annualizacja
        
        # Normalizacja do zakresu 0-1, zakładając że zmienność >40% to już wysoka
        normalized_vol = min(current_vol / 0.4, 1.0)
        
        return normalized_vol
    
    def _calculate_momentum(self, prices: pd.Series) -> float:
        """
        Oblicza momentum rynku w zakresie od -1 do 1.
        
        Args:
            prices: Seria cenowa
            
        Returns:
            float: Momentum w zakresie od -1 do 1
        """
        # Obliczamy RSI jako główny wskaźnik momentum
        rsi = self.indicators.calculate_rsi(prices).iloc[-1]
        
        # Normalizacja RSI z zakresu 0-100 do zakresu -1 do 1
        momentum = (rsi - 50) / 50
        
        return momentum 
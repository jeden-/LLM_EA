"""
Moduł do przechowywania i zarządzania danymi rynkowymi.

Ten moduł zapewnia struktury danych oraz funkcje do:
1. Pobierania danych z MT5
2. Przechowywania danych OHLCV
3. Przeliczania różnych ram czasowych
4. Dodawania indykatorów technicznych
5. Przygotowywania danych do analizy
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple, Any
import logging

from .technical_indicators import TechnicalIndicators

logger = logging.getLogger(__name__)

class MarketData:
    """
    Klasa do zarządzania danymi rynkowymi, które będą wykorzystywane 
    przez systemy analityczne i decyzyjne.
    """
    
    def __init__(self, symbol: str = None, timeframe: str = None):
        """
        Inicjalizacja obiektu MarketData.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Rama czasowa (np. 'M1', 'M5', 'M15', 'H1', 'D1')
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.indicators = TechnicalIndicators()
        
        # Główne dane cenowe (OHLCV)
        self.data = pd.DataFrame()
        
        # Słownik przechowujący dane dla różnych ram czasowych
        self.timeframe_data = {}
        
        # Słownik przechowujący przeliczone indykatory
        self.calculated_indicators = {}
        
        # Metadane
        self.last_update = None
        self.data_source = None
    
    def set_data(self, data: pd.DataFrame):
        """
        Ustawia dane OHLCV w głównym DataFrame.
        
        Args:
            data: DataFrame z danymi OHLCV
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Dane muszą być w formacie pandas DataFrame")
        
        # Sprawdzenie, czy DataFrame ma wymagane kolumny
        required_columns = ['time', 'open', 'high', 'low', 'close']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            raise ValueError(f"Brakujące kolumny w danych: {missing_columns}")
        
        self.data = data.copy()
        
        # Upewnij się, że kolumna czasu jest indeksem
        if 'time' in self.data.columns and not isinstance(self.data.index, pd.DatetimeIndex):
            self.data['time'] = pd.to_datetime(self.data['time'])
            self.data.set_index('time', inplace=True)
        
        # Ustawienie metadanych
        self.last_update = datetime.now()
        self.symbol = self.symbol or data.get('symbol', [None])[0]
        self.timeframe = self.timeframe or data.get('timeframe', [None])[0]
        
        # Dodaj dane do słownika ram czasowych
        if self.timeframe:
            self.timeframe_data[self.timeframe] = self.data.copy()
        
        logger.info(f"Załadowano {len(self.data)} rekordów dla {self.symbol} ({self.timeframe})")
    
    def append_data(self, new_data: pd.DataFrame):
        """
        Dodaje nowe dane do istniejącego DataFrame.
        
        Args:
            new_data: DataFrame z nowymi danymi OHLCV
        """
        if self.data.empty:
            self.set_data(new_data)
            return
        
        # Sprawdzenie, czy DataFrame ma wymagane kolumny
        required_columns = ['time', 'open', 'high', 'low', 'close']
        missing_columns = [col for col in required_columns if col not in new_data.columns]
        
        if missing_columns:
            raise ValueError(f"Brakujące kolumny w danych: {missing_columns}")
        
        # Skopiuj dane, aby uniknąć modyfikacji oryginalnego DataFrame
        new_data = new_data.copy()
        
        # Konwersja kolumny czasu na datetime
        if 'time' in new_data.columns and not isinstance(new_data.index, pd.DatetimeIndex):
            new_data['time'] = pd.to_datetime(new_data['time'])
            new_data.set_index('time', inplace=True)
        
        # Połącz dane i usuń duplikaty
        combined_data = pd.concat([self.data, new_data])
        self.data = combined_data[~combined_data.index.duplicated(keep='last')].sort_index()
        
        # Aktualizacja słownika ram czasowych
        if self.timeframe:
            self.timeframe_data[self.timeframe] = self.data.copy()
        
        # Ustawienie metadanych
        self.last_update = datetime.now()
        
        logger.info(f"Dodano {len(new_data)} nowych rekordów dla {self.symbol} ({self.timeframe})")
    
    def add_timeframe(self, timeframe: str, data: pd.DataFrame):
        """
        Dodaje dane dla określonej ramy czasowej.
        
        Args:
            timeframe: Nazwa ramy czasowej (np. 'M1', 'M5', 'M15', 'H1', 'D1')
            data: DataFrame z danymi OHLCV dla tej ramy czasowej
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Dane muszą być w formacie pandas DataFrame")
        
        # Sprawdzenie, czy DataFrame ma wymagane kolumny
        required_columns = ['time', 'open', 'high', 'low', 'close']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            raise ValueError(f"Brakujące kolumny w danych: {missing_columns}")
        
        # Skopiuj dane, aby uniknąć modyfikacji oryginalnego DataFrame
        data_copy = data.copy()
        
        # Konwersja kolumny czasu na datetime
        if 'time' in data_copy.columns and not isinstance(data_copy.index, pd.DatetimeIndex):
            data_copy['time'] = pd.to_datetime(data_copy['time'])
            data_copy.set_index('time', inplace=True)
        
        self.timeframe_data[timeframe] = data_copy
        
        logger.info(f"Dodano dane dla ramy czasowej {timeframe} ({len(data_copy)} rekordów)")
    
    def resample_timeframe(self, source_tf: str, target_tf: str):
        """
        Przelicza dane z jednej ramy czasowej na inną.
        
        Args:
            source_tf: Źródłowa rama czasowa
            target_tf: Docelowa rama czasowa
        
        Returns:
            DataFrame z przeliczonymi danymi dla docelowej ramy czasowej
        """
        if source_tf not in self.timeframe_data:
            raise ValueError(f"Brak danych dla ramy czasowej {source_tf}")
        
        # Mapowanie nazw ram czasowych na stringi resample Pandas
        tf_mapping = {
            'M1': '1T', 'M5': '5T', 'M15': '15T', 'M30': '30T',
            'H1': '1H', 'H4': '4H', 'H8': '8H', 'D1': '1D',
            'W1': '1W', 'MN1': '1M'
        }
        
        if target_tf not in tf_mapping:
            raise ValueError(f"Nieobsługiwana rama czasowa: {target_tf}")
        
        source_data = self.timeframe_data[source_tf]
        
        # Sprawdzenie, czy możemy przeliczać z niższej na wyższą ramę czasową
        if self._get_minutes(source_tf) > self._get_minutes(target_tf):
            logger.warning("Przeliczanie z wyższej ramy czasowej na niższą może być niedokładne")
        
        # Resample danych
        resampled = source_data.resample(tf_mapping[target_tf]).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum' if 'volume' in source_data.columns else None
        }).dropna()
        
        # Dodaj przeliczone dane do słownika ram czasowych
        self.timeframe_data[target_tf] = resampled
        
        logger.info(f"Przeliczono dane z {source_tf} na {target_tf} ({len(resampled)} rekordów)")
        return resampled
    
    def _get_minutes(self, timeframe: str) -> int:
        """Konwertuje nazwę ramy czasowej na liczbę minut."""
        tf_minutes = {
            'M1': 1, 'M5': 5, 'M15': 15, 'M30': 30,
            'H1': 60, 'H4': 240, 'H8': 480, 'D1': 1440,
            'W1': 10080, 'MN1': 43200
        }
        return tf_minutes.get(timeframe, 0)
    
    def calculate_indicator(self, indicator_name: str, timeframe: str = None, **params):
        """
        Oblicza wskaźnik techniczny i zapisuje wynik.
        
        Args:
            indicator_name: Nazwa wskaźnika do obliczenia
            timeframe: Rama czasowa dla obliczeń (jeśli None, używa głównej ramy czasowej)
            **params: Parametry dla funkcji wskaźnika
        
        Returns:
            Wynik obliczeń wskaźnika. Dla MACD zwraca krotkę (macd_line, signal_line, histogram),
            a dla Bollinger Bands zwraca krotkę (upper, middle, lower).
        """
        tf = timeframe or self.timeframe
        
        if tf not in self.timeframe_data:
            raise ValueError(f"Brak danych dla ramy czasowej {tf}")
        
        price_data = self.timeframe_data[tf]
        
        # Sprawdź, czy mamy implementację dla tego wskaźnika
        method_name = f"calculate_{indicator_name.lower()}"
        if not hasattr(self.indicators, method_name):
            raise ValueError(f"Nieobsługiwany wskaźnik: {indicator_name}")
        
        # Wywołaj odpowiednią metodę z klasy TechnicalIndicators
        indicator_method = getattr(self.indicators, method_name)
        
        # Przygotowanie argumentów w zależności od wymaganego wskaźnika
        result = None
        
        if indicator_name.lower() in ['sma', 'ema', 'rsi']:
            # Te wskaźniki wymagają tylko serii cenowej
            result = indicator_method(price_data['close'], **params)
        elif indicator_name.lower() == 'macd':
            # MACD zwraca słownik z komponentami
            macd_result = indicator_method(price_data['close'], **params)
            
            # Przekształcamy wynik ze słownika na krotkę dla zachowania kompatybilności wstecznej
            if isinstance(macd_result, dict):
                result = (macd_result['macd'], macd_result['signal'], macd_result['histogram'])
            else:
                logger.warning(f"Nieoczekiwany format wyniku MACD: {type(macd_result)}")
                if isinstance(macd_result, pd.Series):
                    # Dla zachowania kompatybilności, tworzymy sztuczne linie
                    result = (macd_result, pd.Series(index=macd_result.index), pd.Series(index=macd_result.index))
                else:
                    # W przypadku innych typów danych, zwracamy puste serie
                    result = (pd.Series(), pd.Series(), pd.Series())
        elif indicator_name.lower() == 'bollinger_bands':
            # Bollinger Bands zwraca krotkę (upper, middle, lower)
            result = indicator_method(price_data['close'], **params)
            # Upewniamy się, że zwracamy krotkę
            if not isinstance(result, tuple) or len(result) != 3:
                logger.warning(f"Wynik Bollinger Bands nie jest poprawną krotką: {result}")
                result = (pd.Series(), pd.Series(), pd.Series())
        
        # Zapisz wynik w słowniku obliczonych wskaźników
        key = f"{indicator_name}_{tf}"
        if params:
            param_str = "_".join([f"{k}_{v}" for k, v in params.items()])
            key = f"{key}_{param_str}"
        
        self.calculated_indicators[key] = result
        
        logger.info(f"Obliczono wskaźnik {indicator_name} dla {tf}")
        return result
    
    def get_market_snapshot(self, timeframe: str = None) -> Dict[str, Any]:
        """
        Zwraca pełny obraz rynku dla danej ramy czasowej, zawierający aktualne ceny i wskaźniki.
        
        Args:
            timeframe: Rama czasowa dla danych (jeśli None, używa głównej ramy czasowej)
        
        Returns:
            Słownik zawierający pełny obraz rynku
        """
        tf = timeframe or self.timeframe
        
        if tf not in self.timeframe_data or self.timeframe_data[tf].empty:
            raise ValueError(f"Brak danych dla ramy czasowej {tf}")
        
        # Pobierz najnowsze dane cenowe
        latest_data = self.timeframe_data[tf].iloc[-1]
        
        # Inicjalizacja wyniku
        snapshot = {
            "symbol": self.symbol,
            "timeframe": tf,
            "current_price": latest_data['close'],
            "time": latest_data.name.isoformat() if hasattr(latest_data.name, 'isoformat') else str(latest_data.name),
            "ohlc": {
                "open": latest_data['open'],
                "high": latest_data['high'],
                "low": latest_data['low'],
                "close": latest_data['close']
            },
            "volume": latest_data.get('volume', None),
            "indicators": {},
            "significant_levels": self._calculate_significant_levels(tf),
            "market_conditions": self._assess_market_conditions(tf)
        }
        
        # Dodaj obliczone wskaźniki
        for key, value in self.calculated_indicators.items():
            if key.endswith(tf) or key.split('_')[1] == tf:
                indicator_name = key.split('_')[0]
                
                if isinstance(value, tuple):
                    # Dla wskaźników zwracających wiele serii (np. MACD, Bollinger Bands)
                    if indicator_name.lower() == 'macd':
                        macd_line, signal_line, histogram = value
                        snapshot["indicators"]["macd"] = {
                            "macd_line": macd_line.iloc[-1],
                            "signal_line": signal_line.iloc[-1],
                            "histogram": histogram.iloc[-1]
                        }
                    elif indicator_name.lower() == 'bollinger_bands':
                        upper, middle, lower = value
                        snapshot["indicators"]["bollinger_bands"] = {
                            "upper": upper.iloc[-1],
                            "middle": middle.iloc[-1],
                            "lower": lower.iloc[-1]
                        }
                else:
                    # Dla wskaźników zwracających pojedynczą serię
                    snapshot["indicators"][indicator_name.lower()] = value.iloc[-1]
        
        return snapshot
    
    def _calculate_significant_levels(self, timeframe: str) -> Dict[str, Any]:
        """
        Oblicza istotne poziomy cenowe (wsparcie, opór, itp.) dla danej ramy czasowej.
        """
        if timeframe not in self.timeframe_data:
            return {}
        
        data = self.timeframe_data[timeframe]
        if len(data) < 20:
            return {}
        
        # Przykładowa implementacja - w praktyce potrzebny bardziej zaawansowany algorytm
        recent_high = data['high'].iloc[-20:].max()
        recent_low = data['low'].iloc[-20:].min()
        
        # Znajdź ostatni indeks wystąpienia high/low
        high_idx = data['high'].iloc[-20:].idxmax()
        low_idx = data['low'].iloc[-20:].idxmin()
        
        # Oblicz, jak dawno wystąpiły
        last_date = data.index[-1]
        high_ago = (last_date - high_idx).days if hasattr(last_date, 'days') else 0
        low_ago = (last_date - low_idx).days if hasattr(last_date, 'days') else 0
        
        # Bardzo uproszczone wykrywanie wsparcia/oporu
        prices = data['close'].values
        supports = []
        resistances = []
        
        # Znajdź lokalne minima/maksima jako potencjalne wsparcia/opory
        for i in range(10, len(prices) - 10):
            if all(prices[i] <= prices[i-j] for j in range(1, 6)) and all(prices[i] <= prices[i+j] for j in range(1, 6)):
                supports.append(prices[i])
            if all(prices[i] >= prices[i-j] for j in range(1, 6)) and all(prices[i] >= prices[i+j] for j in range(1, 6)):
                resistances.append(prices[i])
        
        # Ogranicz do 3 poziomów
        supports = sorted(supports)[:3] if supports else []
        resistances = sorted(resistances, reverse=True)[:3] if resistances else []
        
        return {
            "recent_high": {"value": float(recent_high), "time_ago": f"{high_ago} dni" if high_ago else "dziś"},
            "recent_low": {"value": float(recent_low), "time_ago": f"{low_ago} dni" if low_ago else "dziś"},
            "support": [float(s) for s in supports],
            "resistance": [float(r) for r in resistances]
        }
    
    def _assess_market_conditions(self, timeframe: str) -> Dict[str, Any]:
        """
        Ocenia ogólne warunki rynkowe (trend, zmienność, momentum) dla danej ramy czasowej.
        """
        if timeframe not in self.timeframe_data:
            return {}
        
        data = self.timeframe_data[timeframe]
        if len(data) < 50:
            return {}
        
        # Obliczenie zmienności
        returns = data['close'].pct_change().dropna()
        volatility = returns.std() * (252 ** 0.5)  # Annualizowana zmienność
        
        # Porównanie wolumenu z średnią (jeśli dostępny)
        volume_comparison = ""
        if 'volume' in data.columns:
            avg_volume = data['volume'].iloc[-20:].mean()
            last_volume = data['volume'].iloc[-1]
            
            if last_volume > avg_volume * 1.3:
                volume_comparison = "Znacznie powyżej średniej"
            elif last_volume > avg_volume * 1.1:
                volume_comparison = "Powyżej średniej"
            elif last_volume < avg_volume * 0.7:
                volume_comparison = "Znacznie poniżej średniej"
            elif last_volume < avg_volume * 0.9:
                volume_comparison = "Poniżej średniej"
            else:
                volume_comparison = "Na poziomie średniej"
        
        # Określenie trendu
        short_ma = data['close'].rolling(20).mean().iloc[-1]
        long_ma = data['close'].rolling(50).mean().iloc[-1]
        
        trend = ""
        if short_ma > long_ma * 1.03:
            trend = "Silny trend wzrostowy"
        elif short_ma > long_ma * 1.01:
            trend = "Trend wzrostowy"
        elif short_ma < long_ma * 0.97:
            trend = "Silny trend spadkowy"
        elif short_ma < long_ma * 0.99:
            trend = "Trend spadkowy"
        else:
            trend = "Konsolidacja / Brak wyraźnego trendu"
        
        # Obliczeanie momentum
        momentum = data['close'].iloc[-1] / data['close'].iloc[-10] - 1
        
        momentum_desc = ""
        if momentum > 0.03:
            momentum_desc = "Silne dodatnie momentum"
        elif momentum > 0.01:
            momentum_desc = "Dodatnie momentum"
        elif momentum < -0.03:
            momentum_desc = "Silne ujemne momentum"
        elif momentum < -0.01:
            momentum_desc = "Ujemne momentum"
        else:
            momentum_desc = "Neutralne momentum"
        
        return {
            "trend": {"description": trend},
            "volatility": {"value": float(volatility), "description": "Wysoka" if volatility > 0.2 else "Średnia" if volatility > 0.1 else "Niska"},
            "momentum": {"value": float(momentum), "description": momentum_desc},
            "volume": {"comparison_to_average": volume_comparison} if volume_comparison else {}
        } 
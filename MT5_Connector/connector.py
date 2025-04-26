"""
Główny interfejs modułu MT5_Connector - łączy wszystkie komponenty i udostępnia API dla innych modułów.
"""

from typing import Dict, List, Optional, Union
import os
import time
from datetime import datetime, timedelta

import pandas as pd
from loguru import logger

from .mt5_client import MT5Client
from .indicators import TechnicalIndicators
from .candlestick_patterns import CandlestickPatterns
from .data_formatter import DataFormatter


class MT5Connector:
    """
    Główna klasa konektora MT5, która łączy funkcjonalności wszystkich komponentów
    i udostępnia jednolite API dla innych modułów systemu.
    """
    
    def __init__(self):
        """Inicjalizacja konektora MT5."""
        self.client = MT5Client()
        self.indicators = TechnicalIndicators()
        self.patterns = CandlestickPatterns()
        self.formatter = DataFormatter()
        
        # Inicjalizacja stanu
        self.is_initialized = False
        self.last_update_time = None
        self.default_symbol = os.getenv("MT5_SYMBOL", "EURUSD")
        self.default_timeframe = int(os.getenv("MT5_TIMEFRAME", "1"))
        
        # Cache danych
        self._candles_cache = {}
        self._account_info_cache = {}
        self._symbol_info_cache = {}
    
    def initialize(self) -> bool:
        """
        Inicjalizacja konektora - nawiązanie połączenia z MT5.
        
        Returns:
            bool: True jeśli inicjalizacja się powiodła, False w przeciwnym przypadku.
        """
        logger.info("Inicjalizacja konektora MT5...")
        
        if self.is_initialized:
            logger.info("Konektor MT5 jest już zainicjalizowany.")
            return True
        
        # Połączenie z MT5
        if not self.client.connect():
            logger.error("Nie udało się połączyć z MT5. Inicjalizacja konektora nieudana.")
            return False
        
        self.is_initialized = True
        self.last_update_time = datetime.now()
        
        # Pobranie początkowych danych
        self.update_account_info()
        self.update_symbol_info(self.default_symbol)
        
        logger.info("Konektor MT5 zainicjalizowany pomyślnie.")
        return True
    
    def shutdown(self) -> None:
        """Zamknięcie konektora - zakończenie połączenia z MT5."""
        logger.info("Zamykanie konektora MT5...")
        
        if not self.is_initialized:
            logger.info("Konektor MT5 nie był zainicjalizowany.")
            return
        
        # Rozłączenie z MT5
        self.client.disconnect()
        
        self.is_initialized = False
        logger.info("Konektor MT5 zamknięty pomyślnie.")
    
    def update_account_info(self) -> Dict:
        """
        Aktualizacja informacji o koncie.
        
        Returns:
            Dict: Aktualne informacje o koncie.
        """
        if not self._ensure_initialized():
            return {}
        
        self._account_info_cache = self.client.get_account_info()
        return self._account_info_cache
    
    def update_symbol_info(self, symbol: Optional[str] = None) -> Dict:
        """
        Aktualizacja informacji o symbolu.
        
        Args:
            symbol: Symbol, dla którego aktualizujemy informacje. Domyślnie używany jest symbol z konfiguracji.
            
        Returns:
            Dict: Aktualne informacje o symbolu.
        """
        if not self._ensure_initialized():
            return {}
        
        symbol = symbol or self.default_symbol
        self._symbol_info_cache[symbol] = self.client.get_symbol_info(symbol)
        return self._symbol_info_cache[symbol]
    
    def get_account_info(self) -> Dict:
        """
        Pobieranie informacji o koncie.
        
        Returns:
            Dict: Informacje o koncie.
        """
        # Jeśli cache jest pusty lub starszy niż 5 sekund, aktualizuj
        if (not self._account_info_cache or 
            (datetime.now() - self.last_update_time).total_seconds() > 5):
            return self.update_account_info()
        
        return self._account_info_cache
    
    def get_symbol_info(self, symbol: Optional[str] = None) -> Dict:
        """
        Pobieranie informacji o symbolu.
        
        Args:
            symbol: Symbol, dla którego pobieramy informacje. Domyślnie używany jest symbol z konfiguracji.
            
        Returns:
            Dict: Informacje o symbolu.
        """
        symbol = symbol or self.default_symbol
        
        # Jeśli cache jest pusty lub starszy niż 2 sekundy, aktualizuj
        if (symbol not in self._symbol_info_cache or 
            (datetime.now() - self.last_update_time).total_seconds() > 2):
            return self.update_symbol_info(symbol)
        
        return self._symbol_info_cache[symbol]
    
    def get_candles(
        self, 
        symbol: Optional[str] = None, 
        timeframe: Optional[int] = None, 
        count: int = 100,
        include_current: bool = True,
        add_indicators: bool = True,
        add_patterns: bool = True,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Pobieranie świec OHLCV z opcjonalnymi wskaźnikami i formacjami.
        
        Args:
            symbol: Symbol, dla którego pobieramy świece. Domyślnie używany jest symbol z konfiguracji.
            timeframe: Timeframe, dla którego pobieramy świece. Domyślnie używany jest timeframe z konfiguracji.
            count: Liczba świec do pobrania.
            include_current: Czy dołączyć bieżącą, nieukończoną świecę.
            add_indicators: Czy dodać wskaźniki techniczne.
            add_patterns: Czy dodać identyfikację formacji świecowych.
            use_cache: Czy używać cache'u.
            
        Returns:
            pd.DataFrame: DataFrame z danymi.
        """
        if not self._ensure_initialized():
            return pd.DataFrame()
        
        symbol = symbol or self.default_symbol
        timeframe = timeframe or self.default_timeframe
        
        # Klucz cache'u
        cache_key = f"{symbol}_{timeframe}_{count}_{include_current}"
        
        # Sprawdź cache
        if use_cache and cache_key in self._candles_cache:
            cache_time, df = self._candles_cache[cache_key]
            # Jeśli cache jest młodszy niż połowa timeframe'u, użyj go
            if (datetime.now() - cache_time).total_seconds() < (timeframe * 30):
                return df
        
        # Pobierz dane
        df = self.client.get_candles(symbol, timeframe, count, None, include_current)
        
        if df.empty:
            logger.warning(f"Nie udało się pobrać danych dla {symbol} z timeframe {timeframe}.")
            return df
        
        # Dodaj wskaźniki
        if add_indicators:
            df = self._add_all_indicators(df)
        
        # Dodaj formacje świecowe
        if add_patterns:
            df = self.patterns.identify_patterns(df)
        
        # Zaktualizuj cache
        if use_cache:
            self._candles_cache[cache_key] = (datetime.now(), df)
        
        self.last_update_time = datetime.now()
        return df
    
    def get_formatted_data_for_llm(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[int] = None,
        count: int = 100,
        include_current: bool = True
    ) -> str:
        """
        Pobiera dane i formatuje je w tekst dla modelu LLM.
        
        Args:
            symbol: Symbol, dla którego pobieramy dane. Domyślnie używany jest symbol z konfiguracji.
            timeframe: Timeframe, dla którego pobieramy dane. Domyślnie używany jest timeframe z konfiguracji.
            count: Liczba świec do pobrania.
            include_current: Czy dołączyć bieżącą, nieukończoną świecę.
            
        Returns:
            str: Sformatowany tekst z danymi dla LLM.
        """
        if not self._ensure_initialized():
            return "Błąd: Konektor MT5 nie jest zainicjalizowany."
        
        symbol = symbol or self.default_symbol
        timeframe = timeframe or self.default_timeframe
        
        # Pobierz wszystkie potrzebne dane
        df = self.get_candles(symbol, timeframe, count, include_current, True, True)
        account_info = self.get_account_info()
        symbol_info = self.get_symbol_info(symbol)
        
        # Formatuj dane dla LLM
        formatted_text = self.formatter.format_data_for_llm(df, account_info, symbol_info, timeframe)
        
        return formatted_text
    
    def _ensure_initialized(self) -> bool:
        """
        Upewnia się, że konektor jest zainicjalizowany.
        
        Returns:
            bool: True jeśli konektor jest zainicjalizowany, False w przeciwnym przypadku.
        """
        if not self.is_initialized:
            logger.warning("Konektor MT5 nie jest zainicjalizowany. Próba inicjalizacji...")
            return self.initialize()
        return True
    
    def _add_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Dodaje wszystkie wskaźniki techniczne do DataFrame.
        
        Args:
            df: DataFrame zawierający dane OHLC.
            
        Returns:
            pd.DataFrame: DataFrame z dodanymi wskaźnikami.
        """
        # Dodaj SMA
        df = self.indicators.add_sma(df, 50)
        df = self.indicators.add_sma(df, 200)
        
        # Dodaj EMA
        df = self.indicators.add_ema(df, 20)
        
        # Dodaj ATR
        df = self.indicators.add_atr(df)
        
        # Dodaj VWAP
        df = self.indicators.add_vwap(df)
        
        # Dodaj RSI
        df = self.indicators.add_rsi(df)
        
        # Dodaj Bollinger Bands
        df = self.indicators.add_bollinger_bands(df)
        
        # Dodaj MACD
        df = self.indicators.add_macd(df)
        
        return df 
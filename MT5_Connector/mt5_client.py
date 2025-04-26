"""
Klient MetaTrader 5 - moduł odpowiedzialny za komunikację z platformą handlową.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from loguru import logger
from dotenv import load_dotenv

# Ładowanie zmiennych środowiskowych
load_dotenv()

class MT5Client:
    """
    Klasa klienta MetaTrader 5 zapewniająca interfejs komunikacyjny z platformą.
    """
    
    def __init__(self):
        """Inicjalizacja klienta MT5."""
        self.is_connected = False
        self.login = int(os.getenv("MT5_LOGIN", "0"))
        self.password = os.getenv("MT5_PASSWORD", "")
        self.server = os.getenv("MT5_SERVER", "")
        self.default_symbol = os.getenv("MT5_SYMBOL", "EURUSD")
        self.default_timeframe = int(os.getenv("MT5_TIMEFRAME", "1"))
        
    def connect(self) -> bool:
        """
        Połączenie z platformą MT5.
        
        Returns:
            bool: True jeśli połączenie się powiodło, False w przeciwnym przypadku.
        """
        logger.info("Próba połączenia z platformą MetaTrader 5...")
        
        # Jeśli jesteśmy już połączeni, zwróć True
        if self.is_connected:
            logger.info("Połączenie z MT5 już istnieje.")
            return True
        
        # Inicjalizacja połączenia z MT5
        if not mt5.initialize():
            logger.error(f"Inicjalizacja MT5 nieudana. Kod błędu: {mt5.last_error()}")
            return False
        
        # Logowanie do konta
        if self.login > 0:
            login_result = mt5.login(
                login=self.login,
                password=self.password,
                server=self.server
            )
            
            if not login_result:
                logger.error(f"Logowanie do MT5 nieudane. Kod błędu: {mt5.last_error()}")
                mt5.shutdown()
                return False
                
            logger.info(f"Zalogowano do konta {self.login} na serwerze {self.server}")
        
        self.is_connected = True
        logger.info("Połączenie z MetaTrader 5 ustanowione pomyślnie.")
        return True
    
    def disconnect(self) -> None:
        """Zamknięcie połączenia z MT5."""
        if self.is_connected:
            mt5.shutdown()
            self.is_connected = False
            logger.info("Połączenie z MetaTrader 5 zakończone.")
    
    def get_account_info(self) -> Dict:
        """
        Pobieranie informacji o koncie.
        
        Returns:
            Dict: Słownik z informacjami o koncie.
        """
        if not self._ensure_connection():
            return {}
        
        account_info = mt5.account_info()
        if account_info is None:
            logger.error(f"Nie udało się pobrać informacji o koncie. Kod błędu: {mt5.last_error()}")
            return {}
        
        # Konwersja namedtuple na słownik
        return {
            "balance": account_info.balance,
            "equity": account_info.equity,
            "margin": account_info.margin,
            "free_margin": account_info.margin_free,
            "profit": account_info.profit,
            "leverage": account_info.leverage,
            "currency": account_info.currency,
            "server": account_info.server,
            "name": account_info.name,
            "login": account_info.login
        }
    
    def get_symbol_info(self, symbol: Optional[str] = None) -> Dict:
        """
        Pobieranie informacji o symbolu.
        
        Args:
            symbol: Symbol, dla którego pobieramy informacje. Domyślnie używany jest symbol z konfiguracji.
            
        Returns:
            Dict: Słownik z informacjami o symbolu.
        """
        if not self._ensure_connection():
            return {}
        
        symbol = symbol or self.default_symbol
        symbol_info = mt5.symbol_info(symbol)
        
        if symbol_info is None:
            logger.error(f"Nie udało się pobrać informacji o symbolu {symbol}. Kod błędu: {mt5.last_error()}")
            return {}
        
        # Konwersja namedtuple na słownik
        return {
            "symbol": symbol_info.name,
            "bid": symbol_info.bid,
            "ask": symbol_info.ask,
            "spread": symbol_info.spread,
            "point": symbol_info.point,
            "tick_value": symbol_info.trade_tick_value,
            "tick_size": symbol_info.trade_tick_size,
            "volume_min": symbol_info.volume_min,
            "volume_max": symbol_info.volume_max,
            "volume_step": symbol_info.volume_step
        }
    
    def get_candles(
        self, 
        symbol: Optional[str] = None, 
        timeframe: Optional[int] = None, 
        count: int = 100,
        start_time: Optional[datetime] = None,
        include_current: bool = True
    ) -> pd.DataFrame:
        """
        Pobieranie świec (OHLCV) dla danego symbolu i timeframe'u.
        
        Args:
            symbol: Symbol, dla którego pobieramy świece. Domyślnie używany jest symbol z konfiguracji.
            timeframe: Timeframe, dla którego pobieramy świece. Domyślnie używany jest timeframe z konfiguracji.
            count: Liczba świec do pobrania.
            start_time: Czas początkowy, od którego pobieramy świece.
            include_current: Czy dołączyć bieżącą, nieukończoną świecę.
            
        Returns:
            pd.DataFrame: DataFrame z danymi OHLCV.
        """
        if not self._ensure_connection():
            return pd.DataFrame()
        
        symbol = symbol or self.default_symbol
        timeframe = timeframe or self.default_timeframe
        
        # Mapowanie timeframe'u na wartości MT5
        mt5_timeframe = self._map_timeframe(timeframe)
        
        # Pobieranie danych
        if start_time:
            rates = mt5.copy_rates_from(symbol, mt5_timeframe, start_time, count)
        else:
            rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, count)
        
        if rates is None or len(rates) == 0:
            logger.error(f"Nie udało się pobrać świec dla {symbol}. Kod błędu: {mt5.last_error()}")
            return pd.DataFrame()
        
        # Konwersja na DataFrame
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Usunięcie bieżącej świecy, jeśli trzeba
        if not include_current and len(df) > 0:
            last_complete_time = df.iloc[-1]['time']
            current_time = pd.to_datetime(datetime.now())
            if last_complete_time.minute == current_time.minute and last_complete_time.hour == current_time.hour:
                df = df.iloc[:-1]
        
        # Zmiana nazw kolumn na bardziej czytelne
        df.rename(columns={
            'time': 'timestamp',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'tick_volume': 'volume',
            'spread': 'spread',
            'real_volume': 'real_volume'
        }, inplace=True)
        
        return df
    
    def _ensure_connection(self) -> bool:
        """
        Upewnia się, że połączenie z MT5 jest aktywne.
        
        Returns:
            bool: True jeśli połączenie jest aktywne, False w przeciwnym przypadku.
        """
        if not self.is_connected:
            return self.connect()
        return True
    
    def _map_timeframe(self, timeframe: int) -> int:
        """
        Mapuje timeframe na wartości używane przez MT5.
        
        Args:
            timeframe: Timeframe w minutach.
            
        Returns:
            int: Odpowiadająca wartość dla MT5.
        """
        timeframe_map = {
            1: mt5.TIMEFRAME_M1,
            5: mt5.TIMEFRAME_M5,
            15: mt5.TIMEFRAME_M15,
            30: mt5.TIMEFRAME_M30,
            60: mt5.TIMEFRAME_H1,
            240: mt5.TIMEFRAME_H4,
            1440: mt5.TIMEFRAME_D1,
        }
        
        return timeframe_map.get(timeframe, mt5.TIMEFRAME_M1) 
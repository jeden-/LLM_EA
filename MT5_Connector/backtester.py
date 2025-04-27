"""
Moduł backtestingu - umożliwia testowanie strategii handlowych na historycznych danych.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Callable
import pandas as pd
import numpy as np
import logging
import traceback  # Dodaję import traceback, który jest używany, ale nie był zaimportowany
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import json
import sys

from .connector import MT5Connector
from .indicators import TechnicalIndicators

# Konfiguracja loggera
logger = logging.getLogger(__name__)

class Backtester:
    """
    Klasa odpowiedzialna za przeprowadzanie backtestów strategii handlowych
    na historycznych danych z MT5.
    """
    
    def __init__(self, connector=None, config=None):
        """
        Inicjalizacja backtestera.
        
        Args:
            connector: Instancja konektora do MT5 lub innego źródła danych
            config: Konfiguracja aplikacji
        """
        self.connector = connector
        self.config = config
        self.result = {}
        # Ustawienia domyślne
        self.min_position_time = 60 * 60  # 1 godzina w sekundach
        self.results = {}
        self.trades = []
        self.equity_curve = []
        
    def initialize(self) -> bool:
        """
        Inicjalizacja backtestera - nawiązanie połączenia z MT5.
        
        Returns:
            bool: True jeśli inicjalizacja się powiodła, False w przeciwnym przypadku.
        """
        if not self.connector.is_initialized:
            return self.connector.initialize()
        return True
        
    def _convert_timeframe_to_minutes(self, timeframe):
        """
        Konwertuje format timeframe na wartość w minutach.
        
        Args:
            timeframe (str): Format timeframe (np. 'M1', 'H1', 'D1')
            
        Returns:
            int: Wartość w minutach
        """
        timeframe_dict = {
            'M1': 1,
            'M5': 5,
            'M15': 15,
            'M30': 30,
            'H1': 60,
            'H4': 240,
            'D1': 1440,
            'W1': 10080,
            'MN1': 43200
        }
        
        return timeframe_dict.get(timeframe, 60)  # Domyślnie H1
        
    def run_backtest(
        self,
        symbol: str,
        timeframe: str,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        initial_balance: float,
        strategy: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Uruchamia backtesting dla wybranej strategii i parametrów
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Zakres czasowy świec (np. 'M5', 'H1', 'D1')
            start_date: Data początkowa w formacie YYYY-MM-DD lub obiekt datetime
            end_date: Data końcowa w formacie YYYY-MM-DD lub obiekt datetime
            initial_balance: Początkowy kapitał
            strategy: Wybrana strategia ('ma_cross', 'bollinger_bands', 'rsi', 'macd', 'support_resistance', 'price_action', 'master_method')
            params: Dodatkowe parametry strategii
            
        Returns:
            Dict: Wyniki backtestingu zawierające metryki, transakcje i krzywą equity
        """
        try:
            # Konwersja timeframe na minuty
            tf_minutes = self._convert_timeframe_to_minutes(timeframe)
            if tf_minutes == -1:
                raise ValueError(f"Nieznany timeframe: {timeframe}")
                
            # Konwersja dat na obiekty datetime
            if isinstance(start_date, str):
                start_date_dt = datetime.strptime(start_date, '%Y-%m-%d')
            else:
                start_date_dt = start_date
                
            if isinstance(end_date, str):
                end_date_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)  # Dodaj 1 dzień, żeby uwzględnić end_date
            else:
                end_date_dt = end_date + timedelta(days=1)  # Dodaj 1 dzień, żeby uwzględnić end_date
            
            # Dodatkowa walidacja końcowa data > początkowa data
            if end_date_dt <= start_date_dt:
                raise ValueError("Data końcowa musi być późniejsza niż data początkowa")
                
            # Oblicz ile świec pobrać na podstawie różnicy dat i timeframe
            days_diff = (end_date_dt - start_date_dt).days
            candles_per_day = 24 * 60 / tf_minutes
            candles_to_fetch = int(days_diff * candles_per_day * 1.5)  # Dodajemy 50% więcej dla pewności
            
            # Pobierz dane historyczne
            logger.info(f"Pobieranie danych dla {symbol}, {timeframe}, od {start_date} do {end_date}")
            
            # Połączenie z MT5 i pobranie danych historycznych
            df = self.connector.get_candles(
                symbol=symbol,
                timeframe=tf_minutes,
                count=candles_to_fetch,
                include_current=False,
                add_indicators=True,
                use_cache=False
            )
            
            if df is None or df.empty:
                raise ValueError(f"Nie udało się pobrać danych historycznych dla {symbol} {timeframe}")
                
            # Filtruj dane po dacie
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df[(df['timestamp'] >= start_date_dt) & (df['timestamp'] <= end_date_dt)]
            
            if df.empty:
                raise ValueError(f"Brak danych dla wybranego okresu {start_date} - {end_date}")
                
            logger.info(f"Pobrano {len(df)} świec dla okresu {start_date} - {end_date}")
            
            # Reset zmiennych do śledzenia transakcji i equity
            self.trades = []
            self.equity_curve = []
            
            # Wybór i uruchomienie strategii
            success = False
            if strategy == 'ma_cross':
                success = self._strategy_ma_cross(df, symbol, initial_balance, params)
            elif strategy == 'bollinger_bands':
                success = self._strategy_bollinger_bands(df, symbol, initial_balance, params)
            elif strategy == 'rsi':
                success = self._strategy_rsi(df, symbol, initial_balance, params)
            elif strategy == 'macd':
                success = self._strategy_macd(df, symbol, initial_balance, params)
            elif strategy == 'support_resistance':
                success = self._strategy_support_resistance(df, symbol, initial_balance, params)
            elif strategy == 'price_action':
                success = self._strategy_price_action(df, symbol, initial_balance, params)
            elif strategy == 'master_method':
                success = self._strategy_master_method(df, symbol, initial_balance, params)
            else:
                raise ValueError(f"Nieznana strategia: {strategy}")
                
            if not success:
                raise ValueError(f"Błąd podczas wykonywania backtestingu z użyciem strategii {strategy}")
                
            # Oblicz metryki na podstawie transakcji
            metrics = self._calculate_metrics(self.trades, initial_balance)
            
            # Przygotuj wyniki
            results = {
                'success': True,
                'metrics': metrics,
                'trades': self.trades,
                'equity_curve': self.equity_curve,
                'symbol': symbol,
                'timeframe': timeframe,
                'strategy': strategy,
                'start_date': start_date,
                'end_date': end_date,
                'initial_balance': initial_balance,
                'params': params or {}
            }
            
            logger.info(f"Zakończono backtesting {strategy} dla {symbol} {timeframe}. Wyniki: {metrics}")
            return results
            
        except Exception as e:
            logger.error(f"Błąd podczas backtestingu: {str(e)}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'symbol': symbol,
                'timeframe': timeframe,
                'strategy': strategy,
                'start_date': start_date,
                'end_date': end_date
            }
    
    def _calculate_metrics(self, trades: List[Dict], initial_balance: float) -> Dict:
        """
        Oblicza metryki wydajności na podstawie historii transakcji.
        
        Args:
            trades: Lista słowników zawierających informacje o transakcjach
            initial_balance: Początkowy kapitał
        
        Returns:
            Dict: Słownik metryk wydajności
        """
        if not trades:
            logger.warning("Brak transakcji do analizy metryki")
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'max_drawdown_pct': 0,
                'sharpe_ratio': 0
            }
        
        # Podstawowe metryki
        total_trades = len([t for t in trades if 'pnl' in t])
        winning_trades = len([t for t in trades if 'pnl' in t and t['pnl'] > 0])
        losing_trades = len([t for t in trades if 'pnl' in t and t['pnl'] < 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Profity
        total_pnl = sum(t['pnl'] for t in trades if 'pnl' in t)
        avg_win = sum(t['pnl'] for t in trades if 'pnl' in t and t['pnl'] > 0) / winning_trades if winning_trades > 0 else 0
        avg_loss = sum(abs(t['pnl']) for t in trades if 'pnl' in t and t['pnl'] < 0) / losing_trades if losing_trades > 0 else 0
        
        # Profit factor
        gross_profit = sum(t['pnl'] for t in trades if 'pnl' in t and t['pnl'] > 0)
        gross_loss = abs(sum(t['pnl'] for t in trades if 'pnl' in t and t['pnl'] < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Maksymalny drawdown
        max_drawdown = 0
        max_drawdown_pct = 0
        peak = initial_balance
        
        for point in self.equity_curve:
            equity = point['equity']
            if equity > peak:
                peak = equity
            else:
                drawdown = peak - equity
                drawdown_pct = (drawdown / peak) * 100
                if drawdown_pct > max_drawdown_pct:
                    max_drawdown = drawdown
                    max_drawdown_pct = drawdown_pct
        
        # Sharpe ratio (uproszczony)
        if len(self.equity_curve) > 1:
            returns = []
            for i in range(1, len(self.equity_curve)):
                prev_equity = self.equity_curve[i-1]['equity']
                curr_equity = self.equity_curve[i]['equity']
                if prev_equity > 0:
                    returns.append((curr_equity - prev_equity) / prev_equity)
                    
            if returns:
                avg_return = sum(returns) / len(returns)
                std_return = np.std(returns) if len(returns) > 1 else 0.0001
                sharpe_ratio = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown_pct': max_drawdown_pct,
            'sharpe_ratio': sharpe_ratio
        }
    
    def _strategy_ma_cross(self, df: pd.DataFrame, symbol: str, initial_balance: float, params: Optional[Dict] = None) -> bool:
        """
        Strategia przecięcia średnich kroczących (SMA).
        
        Args:
            df: DataFrame z danymi historycznymi
            symbol: Symbol instrumentu
            initial_balance: Początkowy kapitał
            params: Parametry strategii (fast_ma_period, slow_ma_period, lot_size)
            
        Returns:
            bool: True jeśli strategia została wykonana pomyślnie
        """
        params = params or {}
        fast_ma_period = params.get('fast_ma_period', 10)
        slow_ma_period = params.get('slow_ma_period', 50)
        lot_size = params.get('lot_size', 0.1)
        
        logger.info(f"Uruchamianie strategii MA Cross z parametrami: fast={fast_ma_period}, slow={slow_ma_period}, lot={lot_size}")
        
        # Dodanie średnich jeśli nie istnieją
        if f'sma_{fast_ma_period}' not in df.columns:
            df[f'sma_{fast_ma_period}'] = df['close'].rolling(window=fast_ma_period).mean()
        if f'sma_{slow_ma_period}' not in df.columns:
            df[f'sma_{slow_ma_period}'] = df['close'].rolling(window=slow_ma_period).mean()
        
        # Odrzucenie początkowych wierszy bez średnich
        df = df.dropna(subset=[f'sma_{fast_ma_period}', f'sma_{slow_ma_period}'])
        
        # Zmienne do śledzenia stanu
        position = None  # None = brak pozycji, 'BUY' = pozycja długa, 'SELL' = pozycja krótka
        entry_price = 0
        entry_date = None
        current_balance = initial_balance
        
        # Główna pętla backtestingu
        for i in range(1, len(df)):
            prev = df.iloc[i-1]
            curr = df.iloc[i]
            
            # Sprawdź sygnały
            prev_fast = prev[f'sma_{fast_ma_period}']
            prev_slow = prev[f'sma_{slow_ma_period}']
            curr_fast = curr[f'sma_{fast_ma_period}']
            curr_slow = curr[f'sma_{slow_ma_period}']
            
            # Wykryj przecięcie
            buy_signal = prev_fast <= prev_slow and curr_fast > curr_slow
            sell_signal = prev_fast >= prev_slow and curr_fast < curr_slow
            
            # Jeśli mamy pozycję, sprawdź czy zamknąć
            if position == 'BUY' and sell_signal:
                # Zamknij pozycję długą
                exit_price = curr['close']
                pnl = (exit_price - entry_price) * lot_size * 100000  # Przykładowe obliczenie P/L
                current_balance += pnl
                
                # Zapisz transakcję
                self.trades.append({
                    'date': curr['timestamp'].strftime('%Y-%m-%d'),
                    'type': 'SELL',  # Zamknięcie pozycji długiej
                    'price': exit_price,
                    'size': lot_size,
                    'pnl': pnl,
                    'reason': f'SMA({fast_ma_period}) przecięła SMA({slow_ma_period}) od góry'
                })
                
                # Zapisz punkt na krzywej equity
                self.equity_curve.append({
                    'date': curr['timestamp'].strftime('%Y-%m-%d'),
                    'equity': current_balance
                })
                
                # Resetuj stan
                position = None
                
            elif position == 'SELL' and buy_signal:
                # Zamknij pozycję krótką
                exit_price = curr['close']
                pnl = (entry_price - exit_price) * lot_size * 100000  # Przykładowe obliczenie P/L
                current_balance += pnl
                
                # Zapisz transakcję
                self.trades.append({
                    'date': curr['timestamp'].strftime('%Y-%m-%d'),
                    'type': 'BUY',  # Zamknięcie pozycji krótkiej
                    'price': exit_price,
                    'size': lot_size,
                    'pnl': pnl,
                    'reason': f'SMA({fast_ma_period}) przecięła SMA({slow_ma_period}) od dołu'
                })
                
                # Zapisz punkt na krzywej equity
                self.equity_curve.append({
                    'date': curr['timestamp'].strftime('%Y-%m-%d'),
                    'equity': current_balance
                })
                
                # Resetuj stan
                position = None
                
            # Jeśli nie mamy pozycji, sprawdź czy otworzyć
            if position is None:
                if buy_signal:
                    # Otwórz pozycję długą
                    position = 'BUY'
                    entry_price = curr['close']
                    entry_date = curr['timestamp']
                    
                    # Zapisz transakcję otwarcia
                    self.trades.append({
                        'date': curr['timestamp'].strftime('%Y-%m-%d'),
                        'type': 'BUY',
                        'price': entry_price,
                        'size': lot_size,
                        'pnl': 0,  # P/L będzie znane dopiero przy zamknięciu
                        'reason': f'SMA({fast_ma_period}) przecięła SMA({slow_ma_period}) od dołu'
                    })
                    
                elif sell_signal:
                    # Otwórz pozycję krótką
                    position = 'SELL'
                    entry_price = curr['close']
                    entry_date = curr['timestamp']
                    
                    # Zapisz transakcję otwarcia
                    self.trades.append({
                        'date': curr['timestamp'].strftime('%Y-%m-%d'),
                        'type': 'SELL',
                        'price': entry_price,
                        'size': lot_size,
                        'pnl': 0,  # P/L będzie znane dopiero przy zamknięciu
                        'reason': f'SMA({fast_ma_period}) przecięła SMA({slow_ma_period}) od góry'
                    })
        
        # Zamknij otwartą pozycję na koniec backtestingu
        if position == 'BUY':
            exit_price = df.iloc[-1]['close']
            pnl = (exit_price - entry_price) * lot_size * 100000
            current_balance += pnl
            
            # Zapisz transakcję zamknięcia
            self.trades.append({
                'date': df.iloc[-1]['timestamp'].strftime('%Y-%m-%d'),
                'type': 'SELL',  # Zamknięcie pozycji długiej
                'price': exit_price,
                'size': lot_size,
                'pnl': pnl,
                'reason': 'Koniec backtestingu'
            })
            
        elif position == 'SELL':
            exit_price = df.iloc[-1]['close']
            pnl = (entry_price - exit_price) * lot_size * 100000
            current_balance += pnl
            
            # Zapisz transakcję zamknięcia
            self.trades.append({
                'date': df.iloc[-1]['timestamp'].strftime('%Y-%m-%d'),
                'type': 'BUY',  # Zamknięcie pozycji krótkiej
                'price': exit_price,
                'size': lot_size,
                'pnl': pnl,
                'reason': 'Koniec backtestingu'
            })
            
        # Zapisz końcowy punkt na krzywej equity
        self.equity_curve.append({
            'date': df.iloc[-1]['timestamp'].strftime('%Y-%m-%d'),
            'equity': current_balance
        })
        
        return True
    
    def _strategy_bollinger_bands(self, df: pd.DataFrame, symbol: str, initial_balance: float, params: Optional[Dict] = None) -> bool:
        """
        Strategia wstęg Bollingera.
        
        Args:
            df: DataFrame z danymi historycznymi
            symbol: Symbol instrumentu
            initial_balance: Początkowy kapitał
            params: Parametry strategii
            
        Returns:
            bool: True jeśli strategia została wykonana pomyślnie
        """
        # Tutaj zaimplementuj strategię wstęg Bollingera
        # Na razie zwracamy sukces
        return True
        
    def _strategy_rsi(self, df: pd.DataFrame, symbol: str, initial_balance: float, params: Optional[Dict] = None) -> bool:
        """
        Strategia RSI (Relative Strength Index).
        
        Args:
            df: DataFrame z danymi historycznymi
            symbol: Symbol instrumentu
            initial_balance: Początkowy kapitał
            params: Parametry strategii
            
        Returns:
            bool: True jeśli strategia została wykonana pomyślnie
        """
        # Tutaj zaimplementuj strategię RSI
        # Na razie zwracamy sukces
        return True
        
    def _strategy_macd(self, df: pd.DataFrame, symbol: str, initial_balance: float, params: Optional[Dict] = None) -> bool:
        """
        Strategia MACD (Moving Average Convergence Divergence).
        
        Args:
            df: DataFrame z danymi historycznymi
            symbol: Symbol instrumentu
            initial_balance: Początkowy kapitał
            params: Parametry strategii
            
        Returns:
            bool: True jeśli strategia została wykonana pomyślnie
        """
        # Tutaj zaimplementuj strategię MACD
        # Na razie zwracamy sukces
        return True
        
    def _strategy_support_resistance(self, df: pd.DataFrame, symbol: str, initial_balance: float, params: Optional[Dict] = None) -> bool:
        """
        Strategia wsparć i oporów.
        
        Args:
            df: DataFrame z danymi historycznymi
            symbol: Symbol instrumentu
            initial_balance: Początkowy kapitał
            params: Parametry strategii
            
        Returns:
            bool: True jeśli strategia została wykonana pomyślnie
        """
        # Tutaj zaimplementuj strategię wsparć i oporów
        # Na razie zwracamy sukces
        return True
        
    def _strategy_price_action(self, df: pd.DataFrame, symbol: str, initial_balance: float, params: Optional[Dict] = None) -> bool:
        """
        Strategia price action.
        
        Args:
            df: DataFrame z danymi historycznymi
            symbol: Symbol instrumentu
            initial_balance: Początkowy kapitał
            params: Parametry strategii
            
        Returns:
            bool: True jeśli strategia została wykonana pomyślnie
        """
        # Tutaj zaimplementuj strategię price action
        # Na razie zwracamy sukces
        return True
    
    def _strategy_master_method(self, df: pd.DataFrame, symbol: str, initial_balance: float, params: Optional[Dict] = None) -> bool:
        """
        Implementacja strategii "Metoda Master" łączącej trzy setupy handlowe:
        1. Trend Reverter - odwrócenia krótkoterminowe w kierunku głównego trendu
        2. VWAP Bouncer - odbicia od VWAP zgodne z głównym trendem
        3. Small Account Range Rider - wykorzystanie dziennych zakresów cenowych
        
        Args:
            df: DataFrame z danymi cenowymi i obliczonymi wskaźnikami
            symbol: Symbol instrumentu
            initial_balance: Początkowy kapitał
            params: Dodatkowe parametry strategii (opcjonalnie)
            
        Returns:
            bool: True jeśli backtest przebiegł pomyślnie, False w przeciwnym razie
        """
        try:
            # Domyślne parametry
            default_params = {
                'sma_period': 50,          # SMA do określenia trendu
                'risk_percent': 2.0,       # Maksymalne ryzyko na transakcję jako % kapitału
                'vwap_deviation': 0.002,   # Minimalne odchylenie od VWAP (0.2%)
                'atr_period': 14,          # Okres ATR do określenia zmienności
                'atr_multiplier_sl': 1.5,  # Mnożnik ATR dla stop loss
                'atr_multiplier_tp': 3.0,  # Mnożnik ATR dla take profit
                'lot_multiplier': 0.1,     # Mnożnik wielkości pozycji
                'setup_type': 'all'        # Typ setupu (trend_reverter, vwap_bouncer, range_rider, all)
            }
            
            # Aktualizacja parametrów jeśli podano
            if params:
                default_params.update(params)
            
            # Przypisanie parametrów z updated default_params
            sma_period = default_params['sma_period']
            risk_percent = default_params['risk_percent']
            vwap_deviation = default_params['vwap_deviation']
            atr_period = default_params['atr_period']
            atr_multiplier_sl = default_params['atr_multiplier_sl']
            atr_multiplier_tp = default_params['atr_multiplier_tp']
            lot_multiplier = default_params['lot_multiplier']
            setup_type = default_params['setup_type']
            
            # Sprawdź czy w DataFrame są wymagane kolumny
            required_columns = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
            for col in required_columns:
                if col not in df.columns:
                    logger.error(f"Brak wymaganej kolumny {col} w danych wejściowych")
                    return False
            
            # Inicjalizacja wskaźników jeśli nie są już obliczone
            # 1. SMA dla określenia trendu
            if f'sma_{sma_period}' not in df.columns:
                df[f'sma_{sma_period}'] = df['close'].rolling(window=sma_period).mean()
            
            # 2. ATR dla określenia zmienności i poziomów SL/TP
            if 'atr' not in df.columns:
                df['tr'] = np.maximum(
                    df['high'] - df['low'],
                    np.maximum(
                        abs(df['high'] - df['close'].shift(1)),
                        abs(df['low'] - df['close'].shift(1))
                    )
                )
                df['atr'] = df['tr'].rolling(window=atr_period).mean()
            
            # 3. VWAP (Volume Weighted Average Price)
            if 'vwap' not in df.columns:
                df['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
            
            # Usuń wiersze z NaN (początkowe, gdzie nie można obliczyć wskaźników)
            df = df.dropna()
            
            # Inicjalizacja zmiennych backtestingu
            self.trades = []
            self.equity_curve = []
            
            position = None  # Aktualna pozycja (None, 'BUY', 'SELL')
            entry_price = 0.0  # Cena wejścia
            stop_loss = 0.0   # Poziom stop loss
            take_profit = 0.0 # Poziom take profit
            lot_size = 0.01   # Domyślny rozmiar lota
            current_balance = initial_balance  # Aktualny stan konta
            
            # Zapisz początkowy stan equity
            self.equity_curve.append({
                'date': df.iloc[0]['timestamp'].strftime('%Y-%m-%d'),
                'equity': current_balance
            })
            
            # Funkcje pomocnicze do identyfikacji formacji świecowych
            def is_bullish_candle(candle):
                return candle['close'] > candle['open']
                
            def is_bearish_candle(candle):
                return candle['close'] < candle['open']
                
            def is_doji(candle, threshold=0.05):
                return abs(candle['close'] - candle['open']) / (candle['high'] - candle['low']) < threshold
                
            def is_hammer(candle):
                # Świeca młota - długi dolny cień, małe ciało na górze
                body_size = abs(candle['close'] - candle['open'])
                lower_wick = min(candle['open'], candle['close']) - candle['low']
                upper_wick = candle['high'] - max(candle['open'], candle['close'])
                
                return (lower_wick > 2 * body_size and
                        upper_wick < body_size * 0.5 and
                        body_size > 0)
                        
            def is_shooting_star(candle):
                # Gwiazda spadająca - długi górny cień, małe ciało na dole
                body_size = abs(candle['close'] - candle['open'])
                lower_wick = min(candle['open'], candle['close']) - candle['low']
                upper_wick = candle['high'] - max(candle['open'], candle['close'])
                
                return (upper_wick > 2 * body_size and
                        lower_wick < body_size * 0.5 and
                        body_size > 0)
                        
            def is_engulfing_bullish(prev_candle, curr_candle):
                return (is_bearish_candle(prev_candle) and is_bullish_candle(curr_candle) and
                        curr_candle['open'] < prev_candle['close'] and
                        curr_candle['close'] > prev_candle['open'])
                        
            def is_engulfing_bearish(prev_candle, curr_candle):
                return (is_bullish_candle(prev_candle) and is_bearish_candle(curr_candle) and
                        curr_candle['open'] > prev_candle['close'] and
                        curr_candle['close'] < prev_candle['open'])
                
            def is_vwap_bounce(prev_candle, curr_candle, trend, vwap_value, deviation):
                # Odbicie z dołu (trend wzrostowy)
                if trend == 'up':
                    return (prev_candle['low'] <= vwap_value * (1 - deviation) and
                            curr_candle['close'] > vwap_value and
                            is_bullish_candle(curr_candle))
                # Odbicie z góry (trend spadkowy)            
                else:
                    return (prev_candle['high'] >= vwap_value * (1 + deviation) and
                            curr_candle['close'] < vwap_value and
                            is_bearish_candle(curr_candle))
                            
            def is_john_wick(candle, threshold=0.003):
                # Sprawdź czy świeca ma długi dolny cień
                body_size = abs(candle['close'] - candle['open'])
                lower_wick = min(candle['open'], candle['close']) - candle['low']
                return lower_wick > body_size and lower_wick / candle['low'] > threshold
                
            # Pomocnicza funkcja do wykrywania "Power Tower" (świecy z długim górnym cieniem w trendzie spadkowym)
            def is_power_tower(candle, threshold=0.003):
                # Sprawdź czy świeca ma długi górny cień
                body_size = abs(candle['close'] - candle['open'])
                upper_wick = candle['high'] - max(candle['open'], candle['close'])
                return upper_wick > body_size and upper_wick / candle['high'] > threshold
                
            # Główna pętla backtestingu
            for i in range(2, len(df)):  # Zaczynamy od 2, bo potrzebujemy dwóch poprzednich świec
                prev2 = df.iloc[i-2]
                prev = df.iloc[i-1]
                curr = df.iloc[i]
                
                # Określenie trendu na podstawie 50 SMA
                trend = 'up' if curr['close'] > curr[f'sma_{sma_period}'] else 'down'
                
                # ATR na aktualnej świecy do ustalenia SL/TP
                current_atr = curr['atr']
                
                # Sprawdź odchylenie od VWAP
                vwap_pct_diff = (curr['close'] - curr['vwap']) / curr['vwap']
                
                # 1. Generowanie sygnału wejścia
                buy_signal = False
                sell_signal = False
                setup_name = ""
                
                # SETUP 1: "Trend Reverter" - krótkoterminowe odwrócenia w kierunku głównego trendu
                if setup_type in ['trend_reverter', 'all']:
                    if trend == 'up' and vwap_pct_diff < -vwap_deviation:
                        # Szukamy formacji odwrócenia
                        if is_hammer(prev) or is_engulfing_bullish(prev2, prev) or is_john_wick(prev):
                            buy_signal = True
                            setup_name = "Trend Reverter (Long)"
                            trade_reason = "Odwrócenie w kierunku trendu wzrostowego po odchyleniu od VWAP"
                            
                    elif trend == 'down' and vwap_pct_diff > vwap_deviation:
                        # Szukamy formacji odwrócenia
                        if is_shooting_star(prev) or is_engulfing_bearish(prev2, prev) or is_power_tower(prev):
                            sell_signal = True
                            setup_name = "Trend Reverter (Short)"
                            trade_reason = "Odwrócenie w kierunku trendu spadkowego po odchyleniu od VWAP"
                
                # SETUP 2: "VWAP Bouncer" - odbicia od VWAP zgodne z głównym trendem
                if setup_type in ['vwap_bouncer', 'all'] and not buy_signal and not sell_signal:
                    if is_vwap_bounce(prev, curr, 'up' if trend == 'up' else 'down', curr['vwap'], vwap_deviation):
                        if trend == 'up':
                            buy_signal = True
                            setup_name = "VWAP Bouncer (Long)"
                            trade_reason = "Odbicie od VWAP zgodne z trendem wzrostowym"
                        else:
                            sell_signal = True
                            setup_name = "VWAP Bouncer (Short)"
                            trade_reason = "Odbicie od VWAP zgodne z trendem spadkowym"
                
                # SETUP 3: "Small Account Range Rider" - wykorzystuje dzienne zakresy cenowe
                if setup_type in ['range_rider', 'all'] and not buy_signal and not sell_signal:
                    # Obliczanie skumulowanego dziennego zakresu (ATR jako przybliżenie)
                    daily_range_used = abs(curr['high'] - curr['low']) / current_atr
                    
                    # Sprawdzamy czy wykorzystano już 70-80% dziennego zakresu
                    if daily_range_used >= 0.7:
                        # Przypadek dla trendu wzrostowego - szukamy okazji do kupna przy korekcie
                        if trend == 'up' and vwap_pct_diff < -vwap_deviation:
                            if is_hammer(prev) or is_john_wick(prev) or is_engulfing_bullish(prev2, prev):
                                buy_signal = True
                                setup_name = "Range Rider (Long)"
                                trade_reason = "Korekta w trendzie wzrostowym po wykorzystaniu >70% dziennego zakresu"
                        
                        # Przypadek dla trendu spadkowego - szukamy okazji do sprzedaży przy korekcie
                        elif trend == 'down' and vwap_pct_diff > vwap_deviation:
                            if is_shooting_star(prev) or is_power_tower(prev) or is_engulfing_bearish(prev2, prev):
                                sell_signal = True
                                setup_name = "Range Rider (Short)"
                                trade_reason = "Korekta w trendzie spadkowym po wykorzystaniu >70% dziennego zakresu"
                
                # 2. Zarządzanie pozycją
                # Jeśli nie mamy otwartej pozycji, sprawdź sygnały
                if position is None:
                    # Obliczenie wielkości pozycji na podstawie ryzyka
                    # Zakładamy, że stop loss będzie ustawiony w odległości ATR * mnożnik
                    potential_loss_pips = current_atr * atr_multiplier_sl
                    
                    # Konwersja % ryzyka na kwotę
                    risk_amount = current_balance * (risk_percent / 100.0)
                    
                    # Obliczenie wielkości pozycji (dostosuj do specyfiki rynku)
                    # Przybliżenie wartości pip dla standardowego konta Forex
                    pip_value = 0.0001  # Standardowa wartość pip dla większości par walutowych
                    
                    # Obliczenie wielkości lota na podstawie ryzyka
                    # Dla uproszczenia zakładamy, że 1 lot = 100,000 jednostek waluty
                    lot_size = max(0.01, round((risk_amount / (potential_loss_pips / pip_value)) / 100000, 2))
                    
                    # Dostosowanie wielkości lota dla małych kont
                    lot_size = min(lot_size, current_balance * lot_multiplier / 1000)
                    
                    if buy_signal:
                        position = 'BUY'
                        entry_price = curr['close']
                        stop_loss = entry_price - (current_atr * atr_multiplier_sl)
                        take_profit = entry_price + (current_atr * atr_multiplier_tp)
                        
                        # Zapisz trade do historii
                        self.trades.append({
                            'entry_date': curr['timestamp'].strftime('%Y-%m-%d %H:%M'),
                            'symbol': symbol,
                            'position': position,
                            'setup': setup_name,
                            'reason': trade_reason,
                            'entry_price': entry_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'lot_size': lot_size,
                            'risk_amount': risk_amount,
                            'exit_date': None,
                            'exit_price': None,
                            'profit_loss': None,
                            'pnl': None,
                            'result': None
                        })
                        
                    elif sell_signal:
                        position = 'SELL'
                        entry_price = curr['close']
                        stop_loss = entry_price + (current_atr * atr_multiplier_sl)
                        take_profit = entry_price - (current_atr * atr_multiplier_tp)
                        
                        # Zapisz trade do historii
                        self.trades.append({
                            'entry_date': curr['timestamp'].strftime('%Y-%m-%d %H:%M'),
                            'symbol': symbol,
                            'position': position,
                            'setup': setup_name,
                            'reason': trade_reason,
                            'entry_price': entry_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'lot_size': lot_size,
                            'risk_amount': risk_amount,
                            'exit_date': None,
                            'exit_price': None,
                            'profit_loss': None,
                            'pnl': None,
                            'result': None
                        })
                
                # Jeśli mamy otwartą pozycję, sprawdź czy należy ją zamknąć
                else:
                    # Indeks ostatniego trade'u
                    last_trade_idx = len(self.trades) - 1
                    last_trade = self.trades[last_trade_idx]
                    
                    # Sprawdź czy został osiągnięty stop loss lub take profit
                    if position == 'BUY':
                        # Sprawdź stop loss
                        if curr['low'] <= stop_loss:
                            # Zamknij pozycję po stop loss
                            exit_price = stop_loss
                            profit_loss = (exit_price - entry_price) * last_trade['lot_size'] * 100000  # Przybliżenie dla par walutowych
                            current_balance += profit_loss
                            
                            # Aktualizuj informacje o zamkniętym trade
                            self.trades[last_trade_idx]['exit_date'] = curr['timestamp'].strftime('%Y-%m-%d %H:%M')
                            self.trades[last_trade_idx]['exit_price'] = exit_price
                            self.trades[last_trade_idx]['profit_loss'] = profit_loss
                            self.trades[last_trade_idx]['pnl'] = profit_loss
                            self.trades[last_trade_idx]['result'] = 'LOSS'
                            
                            # Resetuj pozycję
                            position = None
                            
                            # Zapisz stan equity
                            self.equity_curve.append({
                                'date': curr['timestamp'].strftime('%Y-%m-%d'),
                                'equity': current_balance
                            })
                            
                        # Sprawdź take profit
                        elif curr['high'] >= take_profit:
                            # Zamknij pozycję po take profit
                            exit_price = take_profit
                            profit_loss = (exit_price - entry_price) * last_trade['lot_size'] * 100000
                            current_balance += profit_loss
                            
                            # Aktualizuj informacje o zamkniętym trade
                            self.trades[last_trade_idx]['exit_date'] = curr['timestamp'].strftime('%Y-%m-%d %H:%M')
                            self.trades[last_trade_idx]['exit_price'] = exit_price
                            self.trades[last_trade_idx]['profit_loss'] = profit_loss
                            self.trades[last_trade_idx]['pnl'] = profit_loss
                            self.trades[last_trade_idx]['result'] = 'WIN'
                            
                            # Resetuj pozycję
                            position = None
                            
                            # Zapisz stan equity
                            self.equity_curve.append({
                                'date': curr['timestamp'].strftime('%Y-%m-%d'),
                                'equity': current_balance
                            })
                    
                    elif position == 'SELL':
                        # Sprawdź stop loss
                        if curr['high'] >= stop_loss:
                            # Zamknij pozycję po stop loss
                            exit_price = stop_loss
                            profit_loss = (entry_price - exit_price) * last_trade['lot_size'] * 100000
                            current_balance += profit_loss
                            
                            # Aktualizuj informacje o zamkniętym trade
                            self.trades[last_trade_idx]['exit_date'] = curr['timestamp'].strftime('%Y-%m-%d %H:%M')
                            self.trades[last_trade_idx]['exit_price'] = exit_price
                            self.trades[last_trade_idx]['profit_loss'] = profit_loss
                            self.trades[last_trade_idx]['pnl'] = profit_loss
                            self.trades[last_trade_idx]['result'] = 'LOSS'
                            
                            # Resetuj pozycję
                            position = None
                            
                            # Zapisz stan equity
                            self.equity_curve.append({
                                'date': curr['timestamp'].strftime('%Y-%m-%d'),
                                'equity': current_balance
                            })
                            
                        # Sprawdź take profit
                        elif curr['low'] <= take_profit:
                            # Zamknij pozycję po take profit
                            exit_price = take_profit
                            profit_loss = (entry_price - exit_price) * last_trade['lot_size'] * 100000
                            current_balance += profit_loss
                            
                            # Aktualizuj informacje o zamkniętym trade
                            self.trades[last_trade_idx]['exit_date'] = curr['timestamp'].strftime('%Y-%m-%d %H:%M')
                            self.trades[last_trade_idx]['exit_price'] = exit_price
                            self.trades[last_trade_idx]['profit_loss'] = profit_loss
                            self.trades[last_trade_idx]['pnl'] = profit_loss
                            self.trades[last_trade_idx]['result'] = 'WIN'
                            
                            # Resetuj pozycję
                            position = None
                            
                            # Zapisz stan equity
                            self.equity_curve.append({
                                'date': curr['timestamp'].strftime('%Y-%m-%d'),
                                'equity': current_balance
                            })
            
            # Zamknij wszystkie otwarte pozycje na końcu testu
            if position is not None:
                last_trade_idx = len(self.trades) - 1
                last_trade = self.trades[last_trade_idx]
                last_price = df.iloc[-1]['close']
                
                if position == 'BUY':
                    profit_loss = (last_price - entry_price) * last_trade['lot_size'] * 100000
                else:  # SELL
                    profit_loss = (entry_price - last_price) * last_trade['lot_size'] * 100000
                
                current_balance += profit_loss
                
                # Aktualizuj informacje o zamkniętym trade
                self.trades[last_trade_idx]['exit_date'] = df.iloc[-1]['timestamp'].strftime('%Y-%m-%d %H:%M')
                self.trades[last_trade_idx]['exit_price'] = last_price
                self.trades[last_trade_idx]['profit_loss'] = profit_loss
                self.trades[last_trade_idx]['pnl'] = profit_loss
                self.trades[last_trade_idx]['result'] = 'WIN' if profit_loss > 0 else 'LOSS'
                
                # Zapisz końcowy stan equity
                self.equity_curve.append({
                    'date': df.iloc[-1]['timestamp'].strftime('%Y-%m-%d'),
                    'equity': current_balance
                })
            
            # Test pomyślny
            logger.info(f"Ukończono backtesting strategii Master Method dla {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd podczas backtestingu strategii Master Method: {str(e)}")
            logger.error(traceback.format_exc())
            return False 
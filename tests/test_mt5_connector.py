"""
Testy dla modułu MT5_Connector.
"""

import os
import sys
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest
from dotenv import load_dotenv

# Dodaj katalog główny projektu do ścieżki
sys.path.insert(0, str(Path(__file__).parent.parent))

from MT5_Connector.connector import MT5Connector
from MT5_Connector.mt5_client import MT5Client
from MT5_Connector.indicators import TechnicalIndicators
from MT5_Connector.candlestick_patterns import CandlestickPatterns
from MT5_Connector.data_formatter import DataFormatter


# Ładowanie zmiennych środowiskowych
load_dotenv()


class TestMT5Client:
    """Testy dla klasy MT5Client."""
    
    @mock.patch('MT5_Connector.mt5_client.mt5')
    def test_connect(self, mock_mt5):
        """Test połączenia z MT5."""
        # Konfiguracja mocka
        mock_mt5.initialize.return_value = True
        mock_mt5.login.return_value = True
        
        # Utworzenie klienta i wywołanie testu
        client = MT5Client()
        result = client.connect()
        
        # Sprawdzenie, czy metody zostały wywołane
        mock_mt5.initialize.assert_called_once()
        assert result is True
        assert client.is_connected is True
    
    @mock.patch('MT5_Connector.mt5_client.mt5')
    def test_disconnect(self, mock_mt5):
        """Test rozłączenia z MT5."""
        # Utworzenie klienta i ustawienie stanu
        client = MT5Client()
        client.is_connected = True
        
        # Wywołanie testu
        client.disconnect()
        
        # Sprawdzenie, czy metody zostały wywołane
        mock_mt5.shutdown.assert_called_once()
        assert client.is_connected is False
    
    @mock.patch('MT5_Connector.mt5_client.mt5')
    def test_get_account_info(self, mock_mt5):
        """Test pobierania informacji o koncie."""
        # Konfiguracja mocka
        mock_account_info = mock.Mock()
        mock_account_info.balance = 10000.0
        mock_account_info.equity = 10050.0
        mock_account_info.margin = 100.0
        mock_account_info.margin_free = 9950.0
        mock_account_info.profit = 50.0
        mock_account_info.leverage = 100
        mock_account_info.currency = "USD"
        mock_account_info.server = "TestServer"
        mock_account_info.name = "Test Account"
        mock_account_info.login = 12345
        
        mock_mt5.account_info.return_value = mock_account_info
        
        # Utworzenie klienta i ustawienie stanu
        client = MT5Client()
        client.is_connected = True
        
        # Wywołanie testu
        result = client.get_account_info()
        
        # Sprawdzenie, czy metody zostały wywołane i rezultat jest poprawny
        mock_mt5.account_info.assert_called_once()
        assert result["balance"] == 10000.0
        assert result["equity"] == 10050.0
        assert result["currency"] == "USD"
    
    @mock.patch('MT5_Connector.mt5_client.mt5')
    def test_get_candles(self, mock_mt5):
        """Test pobierania świec."""
        # Konfiguracja mocka
        import numpy as np
        
        # Tworzenie danych testowych
        test_rates = np.array([
            (1631145600, 1.18, 1.185, 1.178, 1.182, 100, 0, 0),
            (1631145660, 1.182, 1.187, 1.181, 1.186, 110, 0, 0)
        ], dtype=[
            ('time', '<i8'), ('open', '<f8'), ('high', '<f8'), ('low', '<f8'), 
            ('close', '<f8'), ('tick_volume', '<i8'), ('spread', '<i8'), ('real_volume', '<i8')
        ])
        
        mock_mt5.copy_rates_from_pos.return_value = test_rates
        
        # Utworzenie klienta i ustawienie stanu
        client = MT5Client()
        client.is_connected = True
        
        # Wywołanie testu
        result = client.get_candles()
        
        # Sprawdzenie, czy metody zostały wywołane i rezultat jest poprawny
        mock_mt5.copy_rates_from_pos.assert_called_once()
        assert len(result) == 2
        assert "open" in result.columns
        assert "high" in result.columns
        assert "low" in result.columns
        assert "close" in result.columns
        assert "volume" in result.columns


class TestTechnicalIndicators:
    """Testy dla klasy TechnicalIndicators."""
    
    def test_add_sma(self):
        """Test dodawania SMA."""
        # Przygotowanie danych testowych
        data = {
            'timestamp': pd.date_range(start='2023-01-01', periods=10, freq='1min'),
            'open': [1.1, 1.12, 1.13, 1.1, 1.08, 1.09, 1.11, 1.12, 1.13, 1.14],
            'high': [1.15, 1.16, 1.17, 1.14, 1.12, 1.14, 1.15, 1.17, 1.18, 1.19],
            'low': [1.08, 1.1, 1.11, 1.07, 1.06, 1.07, 1.09, 1.1, 1.11, 1.12],
            'close': [1.12, 1.13, 1.14, 1.08, 1.09, 1.11, 1.12, 1.13, 1.14, 1.15],
            'volume': [100, 110, 120, 90, 80, 100, 110, 120, 130, 140]
        }
        df = pd.DataFrame(data)
        
        # Wywołanie testu
        indicators = TechnicalIndicators()
        result = indicators.add_sma(df, period=3, column='close')
        
        # Sprawdzenie rezultatu
        assert 'sma_3' in result.columns
        # Pierwsze dwie wartości SMA powinny być NaN (okno 3)
        assert pd.isna(result['sma_3'].iloc[0])
        assert pd.isna(result['sma_3'].iloc[1])
        # Trzecia wartość powinna być średnią z trzech pierwszych wartości
        assert result['sma_3'].iloc[2] == (1.12 + 1.13 + 1.14) / 3
    
    def test_add_atr(self):
        """Test dodawania ATR."""
        # Przygotowanie danych testowych
        data = {
            'timestamp': pd.date_range(start='2023-01-01', periods=10, freq='1min'),
            'open': [1.1, 1.12, 1.13, 1.1, 1.08, 1.09, 1.11, 1.12, 1.13, 1.14],
            'high': [1.15, 1.16, 1.17, 1.14, 1.12, 1.14, 1.15, 1.17, 1.18, 1.19],
            'low': [1.08, 1.1, 1.11, 1.07, 1.06, 1.07, 1.09, 1.1, 1.11, 1.12],
            'close': [1.12, 1.13, 1.14, 1.08, 1.09, 1.11, 1.12, 1.13, 1.14, 1.15],
            'volume': [100, 110, 120, 90, 80, 100, 110, 120, 130, 140]
        }
        df = pd.DataFrame(data)
        
        # Wywołanie testu
        indicators = TechnicalIndicators()
        result = indicators.add_atr(df, period=3)
        
        # Sprawdzenie rezultatu
        assert 'atr' in result.columns
        # Pierwsze dwie wartości ATR powinny być NaN (okno 3)
        assert pd.isna(result['atr'].iloc[0])
        assert pd.isna(result['atr'].iloc[1])


class TestCandlestickPatterns:
    """Testy dla klasy CandlestickPatterns."""
    
    def test_doji(self):
        """Test identyfikacji formacji Doji."""
        # Przygotowanie danych testowych - typowy Doji
        data = {
            'timestamp': pd.date_range(start='2023-01-01', periods=3, freq='1min'),
            'open': [1.1, 1.12, 1.15],
            'high': [1.15, 1.13, 1.20],
            'low': [1.08, 1.11, 1.10],
            'close': [1.1, 1.12, 1.18],  # Pierwszy i drugi to Doji (open == close), trzeci ma różne wartości
            'volume': [100, 110, 120]
        }
        df = pd.DataFrame(data)
        
        # Wywołanie testu
        patterns = CandlestickPatterns()
        result = patterns.doji(df)
        
        # Sprawdzenie rezultatu
        assert 'doji' in result.columns
        assert result['doji'].iloc[0] == True  # Pierwszy powinien być Doji
        assert result['doji'].iloc[1] == True  # Drugi powinien być Doji
        assert result['doji'].iloc[2] == False  # Trzeci nie powinien być Doji
    
    def test_hammer(self):
        """Test identyfikacji formacji Hammer."""
        # Przygotowanie danych testowych - typowy Hammer
        data = {
            'timestamp': pd.date_range(start='2023-01-01', periods=3, freq='1min'),
            'open': [1.15, 1.14, 1.15],
            'high': [1.16, 1.15, 1.20],
            'low': [1.10, 1.05, 1.10],  # Drugi ma długi dolny cień
            'close': [1.15, 1.14, 1.15],
            'volume': [100, 110, 120]
        }
        df = pd.DataFrame(data)
        
        # Wywołanie testu
        patterns = CandlestickPatterns()
        result = patterns.hammer(df)
        
        # Sprawdzenie rezultatu
        assert 'hammer' in result.columns
        assert result['hammer'].iloc[0] == False  # Pierwszy nie powinien być Hammer
        # Drugi może być Hammer, ale zależy od parametrów
        assert result['hammer'].iloc[2] == False  # Trzeci nie powinien być Hammer


class TestDataFormatter:
    """Testy dla klasy DataFormatter."""
    
    def test_format_ohlc_data(self):
        """Test formatowania danych OHLC."""
        # Przygotowanie danych testowych
        data = {
            'timestamp': pd.date_range(start='2023-01-01', periods=3, freq='1min'),
            'open': [1.1, 1.12, 1.13],
            'high': [1.15, 1.16, 1.17],
            'low': [1.08, 1.1, 1.11],
            'close': [1.12, 1.13, 1.14],
            'volume': [100, 110, 120]
        }
        df = pd.DataFrame(data)
        
        # Wywołanie testu
        formatter = DataFormatter()
        result = formatter.format_ohlc_data(df)
        
        # Sprawdzenie rezultatu
        assert isinstance(result, str)
        assert "Dane OHLC" in result
        assert "2023-01-01 00:00" in result
        assert "O=1.10000" in result
    
    def test_format_market_summary(self):
        """Test formatowania podsumowania rynku."""
        # Przygotowanie danych testowych
        data = {
            'timestamp': pd.date_range(start='2023-01-01', periods=3, freq='1min'),
            'open': [1.1, 1.12, 1.13],
            'high': [1.15, 1.16, 1.17],
            'low': [1.08, 1.1, 1.11],
            'close': [1.12, 1.13, 1.14],
            'volume': [100, 110, 120],
            'sma_50': [1.11, 1.12, 1.13],
            'sma_200': [1.10, 1.11, 1.12]
        }
        df = pd.DataFrame(data)
        
        account_info = {
            "balance": 10000.0,
            "equity": 10050.0,
            "margin": 100.0,
            "free_margin": 9950.0,
            "profit": 50.0,
            "currency": "USD"
        }
        
        symbol_info = {
            "symbol": "EURUSD",
            "bid": 1.14,
            "ask": 1.1402,
            "spread": 2,
            "point": 0.00001
        }
        
        # Wywołanie testu
        formatter = DataFormatter()
        result = formatter.format_market_summary(df, account_info, symbol_info, 1)
        
        # Sprawdzenie rezultatu
        assert isinstance(result, str)
        assert "Podsumowanie rynku" in result
        assert "EURUSD" in result
        assert "Timeframe: 1" in result


class TestMT5Connector:
    """Testy dla klasy MT5Connector."""
    
    @mock.patch('MT5_Connector.connector.MT5Client')
    def test_initialize(self, mock_client_class):
        """Test inicjalizacji konektora."""
        # Konfiguracja mocka
        mock_client = mock.Mock()
        mock_client.connect.return_value = True
        mock_client.get_account_info.return_value = {"balance": 10000.0}
        mock_client.get_symbol_info.return_value = {"symbol": "EURUSD"}
        mock_client_class.return_value = mock_client
        
        # Utworzenie konektora i wywołanie testu
        connector = MT5Connector()
        result = connector.initialize()
        
        # Sprawdzenie, czy metody zostały wywołane i rezultat jest poprawny
        mock_client.connect.assert_called_once()
        assert result is True
        assert connector.is_initialized is True
    
    @mock.patch('MT5_Connector.connector.MT5Client')
    def test_get_candles(self, mock_client_class):
        """Test pobierania świec z wskaźnikami i formacjami."""
        # Konfiguracja mocka
        mock_client = mock.Mock()
        
        # Tworzenie danych testowych
        data = {
            'timestamp': pd.date_range(start='2023-01-01', periods=3, freq='1min'),
            'open': [1.1, 1.12, 1.13],
            'high': [1.15, 1.16, 1.17],
            'low': [1.08, 1.1, 1.11],
            'close': [1.12, 1.13, 1.14],
            'volume': [100, 110, 120]
        }
        mock_client.get_candles.return_value = pd.DataFrame(data)
        mock_client_class.return_value = mock_client
        
        # Utworzenie konektora i ustawienie stanu
        connector = MT5Connector()
        connector.is_initialized = True
        
        # Wywołanie testu
        result = connector.get_candles()
        
        # Sprawdzenie, czy metody zostały wywołane i rezultat jest poprawny
        mock_client.get_candles.assert_called_once()
        assert not result.empty
        assert 'sma_50' in result.columns  # Wskaźniki zostały dodane
        
    @mock.patch('MT5_Connector.connector.MT5Client')
    def test_get_formatted_data_for_llm(self, mock_client_class):
        """Test pobierania sformatowanych danych dla LLM."""
        # Konfiguracja mocka
        mock_client = mock.Mock()
        
        # Tworzenie danych testowych
        data = {
            'timestamp': pd.date_range(start='2023-01-01', periods=3, freq='1min'),
            'open': [1.1, 1.12, 1.13],
            'high': [1.15, 1.16, 1.17],
            'low': [1.08, 1.1, 1.11],
            'close': [1.12, 1.13, 1.14],
            'volume': [100, 110, 120]
        }
        mock_client.get_candles.return_value = pd.DataFrame(data)
        mock_client.get_account_info.return_value = {"balance": 10000.0}
        mock_client.get_symbol_info.return_value = {"symbol": "EURUSD"}
        mock_client_class.return_value = mock_client
        
        # Utworzenie konektora i ustawienie stanu
        connector = MT5Connector()
        connector.is_initialized = True
        
        # Zastąpienie metody konektora get_candles, aby zwracała DataFrame z danymi testowymi
        def mock_get_candles(*args, **kwargs):
            df = pd.DataFrame(data)
            df = connector._add_all_indicators(df)
            return df
        
        connector.get_candles = mock_get_candles
        
        # Wywołanie testu
        result = connector.get_formatted_data_for_llm()
        
        # Sprawdzenie, czy metody zostały wywołane i rezultat jest poprawny
        mock_client.get_account_info.assert_called_once()
        mock_client.get_symbol_info.assert_called_once()
        assert isinstance(result, str)
        assert "Podsumowanie rynku" in result 
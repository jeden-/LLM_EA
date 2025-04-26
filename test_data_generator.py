"""
Generator danych testowych dla systemu handlowego LLM.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class TestData:
    """
    Klasa zawierająca dane testowe do walidacji LLM_Engine i jego komponentów.
    Dostarcza różne zestawy danych dla różnych instrumentów i ram czasowych.
    """
    
    @staticmethod
    def generate_ohlc_data(symbol='EURUSD', timeframe='H1', num_candles=100, start_date=None, volatility=0.002):
        """
        Generuje sztuczne dane OHLC (Open, High, Low, Close) dla określonego symbolu i ramy czasowej.
        
        Args:
            symbol: Symbol instrumentu (np. 'EURUSD')
            timeframe: Rama czasowa (np. 'H1', 'D1')
            num_candles: Liczba świec do wygenerowania
            start_date: Data początkowa (jeśli None, używa aktualnej daty)
            volatility: Parametr zmienności ceny
            
        Returns:
            DataFrame zawierający dane OHLC, wolumen i czas
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=num_candles if timeframe == 'D1' else num_candles/24)
        
        # Początkowa cena
        initial_price = {
            'EURUSD': 1.1200,
            'GBPUSD': 1.3000,
            'USDJPY': 110.00,
            'BTCUSD': 45000.00,
            'GOLD': 1800.00,
            'SP500': 4500.00
        }.get(symbol, 100.00)
        
        # Odstęp czasowy
        if timeframe == 'M1':
            time_delta = timedelta(minutes=1)
        elif timeframe == 'M5':
            time_delta = timedelta(minutes=5)
        elif timeframe == 'M15':
            time_delta = timedelta(minutes=15)
        elif timeframe == 'M30':
            time_delta = timedelta(minutes=30)
        elif timeframe == 'H1':
            time_delta = timedelta(hours=1)
        elif timeframe == 'H4':
            time_delta = timedelta(hours=4)
        elif timeframe == 'D1':
            time_delta = timedelta(days=1)
        else:
            time_delta = timedelta(hours=1)
        
        # Generacja danych
        np.random.seed(42)  # Dla powtarzalności
        
        dates = [start_date + i * time_delta for i in range(num_candles)]
        
        # Generowanie cen z losowym dryfem i zmiennością
        price_changes = np.random.normal(0, volatility, num_candles)
        prices = [initial_price]
        
        for change in price_changes:
            next_price = prices[-1] * (1 + change)
            prices.append(next_price)
        
        prices = prices[1:]  # Usunięcie ceny początkowej
        
        # Tworzenie OHLC
        data = []
        for i, date in enumerate(dates):
            price = prices[i]
            high_factor = 1 + abs(np.random.normal(0, volatility/2))
            low_factor = 1 - abs(np.random.normal(0, volatility/2))
            
            open_price = price
            high_price = price * high_factor
            low_price = price * low_factor
            close_price = price * (1 + np.random.normal(0, volatility/3))
            
            # Korekta - upewnienie się, że high jest najwyższy, a low najniższy
            high_price = max(open_price, high_price, close_price)
            low_price = min(open_price, low_price, close_price)
            
            volume = int(np.random.gamma(2.0, 1000))
            
            data.append({
                'time': date,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume,
                'symbol': symbol,
                'timeframe': timeframe
            })
        
        return pd.DataFrame(data)
    
    @staticmethod
    def get_trending_market_data(symbol='EURUSD', trend='up', num_candles=100):
        """
        Generuje dane z wyraźnym trendem (wzrostowym lub spadkowym).
        
        Args:
            symbol: Symbol instrumentu
            trend: Kierunek trendu ('up' lub 'down')
            num_candles: Liczba świec
            
        Returns:
            DataFrame z danymi OHLC przedstawiającymi trend
        """
        base_data = TestData.generate_ohlc_data(symbol=symbol, num_candles=num_candles, volatility=0.001)  # Mniejsza zmienność bazowa
        
        # Silniejszy komponent trendu
        trend_factor = 0.02 if trend == 'up' else -0.02  # Podwojony trend
        
        # Kumulacyjna zmiana dla wzmocnienia trendu
        cumulative_change = 0
        
        for i in range(1, len(base_data)):
            # Progresywna zmiana ceny z kumulacją
            trend_change = (i / num_candles) * trend_factor * base_data.iloc[0]['close']
            cumulative_change += trend_change
            
            # Dodanie minimalnego szumu do trendu
            noise = np.random.normal(0, 0.0002) * base_data.iloc[0]['close']  # Zmniejszony szum
            total_change = cumulative_change + noise
            
            # Aplikowanie zmiany do wszystkich cen OHLC
            base_data.iloc[i, base_data.columns.get_loc('open')] = base_data.iloc[0]['open'] + total_change
            base_data.iloc[i, base_data.columns.get_loc('high')] = base_data.iloc[0]['high'] + total_change
            base_data.iloc[i, base_data.columns.get_loc('low')] = base_data.iloc[0]['low'] + total_change
            base_data.iloc[i, base_data.columns.get_loc('close')] = base_data.iloc[0]['close'] + total_change
        
        return base_data
    
    @staticmethod
    def get_ranging_market_data(symbol='EURUSD', num_candles=100, range_width=0.02):
        """
        Generuje dane dla rynku w konsolidacji (range-bound).
        
        Args:
            symbol: Symbol instrumentu
            num_candles: Liczba świec
            range_width: Szerokość zakresu jako procent ceny początkowej
            
        Returns:
            DataFrame z danymi OHLC przedstawiającymi konsolidację
        """
        base_data = TestData.generate_ohlc_data(symbol=symbol, num_candles=num_candles)
        
        # Parametry konsolidacji
        midpoint = base_data.iloc[0]['close']
        range_half_width = midpoint * range_width / 2
        
        for i in range(len(base_data)):
            # Sinusoidalny wzór oscylacji w zakresie
            oscillation = np.sin(i * 0.1) * range_half_width
            
            base_data.iloc[i, base_data.columns.get_loc('open')] = midpoint + oscillation * 0.9
            base_data.iloc[i, base_data.columns.get_loc('close')] = midpoint + oscillation * 1.1
            base_data.iloc[i, base_data.columns.get_loc('high')] = max(
                base_data.iloc[i]['open'], 
                base_data.iloc[i]['close']
            ) + abs(oscillation) * 0.2
            base_data.iloc[i, base_data.columns.get_loc('low')] = min(
                base_data.iloc[i]['open'], 
                base_data.iloc[i]['close']
            ) - abs(oscillation) * 0.2
        
        return base_data
    
    @staticmethod
    def get_volatile_market_data(symbol='EURUSD', num_candles=100, volatility_factor=3):
        """
        Generuje dane dla wysoce zmiennego rynku.
        
        Args:
            symbol: Symbol instrumentu
            num_candles: Liczba świec
            volatility_factor: Mnożnik standardowej zmienności
            
        Returns:
            DataFrame z danymi OHLC przedstawiającymi wysoką zmienność
        """
        return TestData.generate_ohlc_data(
            symbol=symbol, 
            num_candles=num_candles, 
            volatility=0.002 * volatility_factor
        )
    
    @staticmethod
    def get_support_resistance_data(symbol='EURUSD', num_candles=100, levels=None):
        """
        Generuje dane z wyraźnymi poziomami wsparcia i oporu.
        
        Args:
            symbol: Symbol instrumentu
            num_candles: Liczba świec
            levels: Lista poziomów wsparcia/oporu; jeśli None, generuje automatycznie
            
        Returns:
            DataFrame z danymi OHLC i poziomami wsparcia/oporu
        """
        base_data = TestData.generate_ohlc_data(symbol=symbol, num_candles=num_candles)
        
        # Jeśli poziomy nie są określone, generujemy je
        if levels is None:
            base_price = base_data.iloc[0]['close']
            range_width = base_price * 0.10  # 10% zakresu ceny
            num_levels = 3
            
            levels = []
            for i in range(num_levels):
                level = base_price * (1 - 0.05 + i * 0.05)  # Poziomy co 5%
                levels.append(level)
        
        # Dostosowujemy ceny, aby respektowały poziomy wsparcia/oporu
        for i in range(len(base_data)):
            # Znajdź najbliższy poziom
            price = base_data.iloc[i]['close']
            distances = [abs(price - level) for level in levels]
            closest_level_idx = distances.index(min(distances))
            closest_level = levels[closest_level_idx]
            
            # Jeśli cena jest blisko poziomu (w odległości 1%), dostosuj ją
            if min(distances) / price < 0.01:
                # 70% szans na odbicie, 30% na przebicie
                if np.random.random() > 0.3:
                    # Odbicie
                    direction = 1 if price < closest_level else -1
                    adjustment = abs(price - closest_level) * direction
                    
                    # Aplikowanie silniejszego odbicia
                    base_data.iloc[i, base_data.columns.get_loc('close')] = closest_level + adjustment * 0.5
                    
                    # Dostosuj high/low
                    if direction > 0:
                        base_data.iloc[i, base_data.columns.get_loc('high')] = max(
                            base_data.iloc[i]['high'],
                            closest_level + abs(adjustment)
                        )
                    else:
                        base_data.iloc[i, base_data.columns.get_loc('low')] = min(
                            base_data.iloc[i]['low'],
                            closest_level - abs(adjustment)
                        )
                else:
                    # Przebicie - zostawiamy cenę bez zmian
                    pass
        
        return base_data
    
    @staticmethod
    def get_multi_timeframe_data(symbol='EURUSD', timeframes=None, num_candles=100):
        """
        Generuje dane dla wielu ram czasowych dla tego samego symbolu.
        
        Args:
            symbol: Symbol instrumentu
            timeframes: Lista ram czasowych do wygenerowania
            num_candles: Liczba świec dla najdłuższej ramy czasowej
            
        Returns:
            Słownik DataFrame'ów, gdzie kluczami są ramy czasowe
        """
        if timeframes is None:
            timeframes = ['M15', 'H1', 'H4', 'D1']
        
        # Znajdź najdłuższą ramę czasową
        tf_to_minutes = {
            'M1': 1, 'M5': 5, 'M15': 15, 'M30': 30,
            'H1': 60, 'H4': 240, 'D1': 1440
        }
        
        max_tf_minutes = max(tf_to_minutes[tf] for tf in timeframes)
        
        # Ustal liczbę świec dla każdej ramy czasowej
        start_date = datetime.now() - timedelta(minutes=max_tf_minutes * num_candles)
        
        result = {}
        for tf in timeframes:
            tf_minutes = tf_to_minutes[tf]
            tf_candles = int(max_tf_minutes * num_candles / tf_minutes)
            
            result[tf] = TestData.generate_ohlc_data(
                symbol=symbol,
                timeframe=tf,
                num_candles=tf_candles,
                start_date=start_date
            )
        
        return result

    @staticmethod
    def get_common_test_data():
        """
        Zwraca standardowy zestaw danych testowych dla najczęściej używanych przypadków.
        
        Returns:
            Słownik zawierający różne zestawy danych testowych
        """
        return {
            'eurusd_h1': TestData.generate_ohlc_data(symbol='EURUSD', timeframe='H1'),
            'eurusd_h1_uptrend': TestData.get_trending_market_data(symbol='EURUSD', trend='up'),
            'eurusd_h1_downtrend': TestData.get_trending_market_data(symbol='EURUSD', trend='down'),
            'eurusd_h1_range': TestData.get_ranging_market_data(symbol='EURUSD'),
            'eurusd_h1_volatile': TestData.get_volatile_market_data(symbol='EURUSD'),
            'eurusd_h1_support_resistance': TestData.get_support_resistance_data(symbol='EURUSD'),
            'eurusd_multi_tf': TestData.get_multi_timeframe_data(symbol='EURUSD'),
            'btcusd_h1': TestData.generate_ohlc_data(symbol='BTCUSD', timeframe='H1'),
            'gold_h1': TestData.generate_ohlc_data(symbol='GOLD', timeframe='H1'),
        } 
#!/usr/bin/env python
"""
Przykładowy skrypt demonstrujący użycie modułu MT5_Connector.
"""

import os
import sys
import time
from pathlib import Path

# Dodaj katalog główny projektu do ścieżki
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from dotenv import load_dotenv

from MT5_Connector.connector import MT5Connector


def main():
    """Główna funkcja przykładu."""
    # Konfiguracja loggera
    logger.add("logs/mt5_connector_example.log", rotation="1 MB", level="INFO")
    logger.info("Uruchamianie przykładu konektora MT5...")
    
    # Ładowanie zmiennych środowiskowych
    load_dotenv()
    
    # Inicjalizacja konektora
    connector = MT5Connector()
    if not connector.initialize():
        logger.error("Nie udało się zainicjalizować konektora MT5. Kończenie.")
        return
    
    try:
        # Pobierz i wyświetl informacje o koncie
        account_info = connector.get_account_info()
        logger.info(f"Informacje o koncie: {account_info}")
        
        # Pobierz i wyświetl informacje o symbolu
        symbol = os.getenv("MT5_SYMBOL", "EURUSD")
        symbol_info = connector.get_symbol_info(symbol)
        logger.info(f"Informacje o symbolu {symbol}: {symbol_info}")
        
        # Pobierz dane świec z wskaźnikami i formacjami
        timeframe = int(os.getenv("MT5_TIMEFRAME", "1"))
        df = connector.get_candles(symbol, timeframe, 100, True, True, True)
        
        # Wyświetl kilka ostatnich świec
        logger.info(f"Pobrano {len(df)} świec dla {symbol} z timeframe {timeframe}")
        logger.info(f"Ostatnie 3 świece:\n{df.tail(3)}")
        
        # Pobierz sformatowane dane dla LLM
        formatted_data = connector.get_formatted_data_for_llm(symbol, timeframe, 50)
        
        # Wyświetl sformatowane dane (tylko fragment)
        data_preview = formatted_data.split("\n\n")[0] + "\n\n(dane skrócone dla czytelności)"
        logger.info(f"Sformatowane dane dla LLM:\n{data_preview}")
        
        # Zapisz pełne dane do pliku
        with open("data_for_llm_example.txt", "w", encoding="utf-8") as f:
            f.write(formatted_data)
        logger.info("Pełne dane zapisano do pliku 'data_for_llm_example.txt'")
        
        # Pętla z danymi w czasie rzeczywistym (5 iteracji)
        logger.info("Rozpoczynam pobieranie danych w czasie rzeczywistym...")
        for i in range(5):
            # Pobierz aktualne dane
            current_data = connector.get_candles(symbol, timeframe, 10, True, True, True, use_cache=False)
            
            # Wyświetl aktualną cenę
            if not current_data.empty:
                last_candle = current_data.iloc[-1]
                logger.info(f"Iteracja {i+1}: Aktualna cena {symbol}: {last_candle['close']:.5f}")
                
                # Sprawdź, czy wykryto jakieś formacje świecowe
                pattern_columns = [col for col in current_data.columns if any(pat in col for pat in [
                    'doji', 'hammer', 'shooting_star', 'marubozu', 
                    'engulfing', 'harami', 'morning_star', 'evening_star', 
                    'three_white_soldiers', 'three_black_crows'
                ])]
                
                detected_patterns = []
                for col in pattern_columns:
                    if last_candle[col]:
                        detected_patterns.append(col)
                
                if detected_patterns:
                    logger.info(f"Wykryte formacje dla ostatniej świecy: {detected_patterns}")
            
            # Czekaj 10 sekund przed kolejną iteracją
            time.sleep(10)
    
    except Exception as e:
        logger.exception(f"Wystąpił błąd: {e}")
    
    finally:
        # Zamknij konektor
        connector.shutdown()
        logger.info("Przykład zakończony.")


if __name__ == "__main__":
    main() 
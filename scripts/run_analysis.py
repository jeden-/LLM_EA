#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do przeprowadzenia jednorazowej analizy rynkowej dla wybranych symboli.
Pozwala na szybkie generowanie analiz LLM dla par walutowych bez konieczności uruchamiania całego agenta.
"""

import os
import sys
import argparse
import json
import logging
import time
from datetime import datetime

# Konfiguracja systemu logowania
def configure_logging(level_name: str, log_file: str = None):
    """
    Konfiguracja systemu logowania.
    
    Args:
        level_name: Poziom logowania (debug, info, warning, error, critical)
        log_file: Ścieżka do pliku z logami (opcjonalnie)
    """
    # Mapowanie nazw poziomów na stałe logging
    levels = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }
    level = levels.get(level_name.lower(), logging.INFO)
    
    # Podstawowa konfiguracja
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Logger główny
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Czyszczenie istniejących handlerów
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Handler dla konsoli
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler dla pliku (jeśli podano)
    if log_file:
        # Upewnij się, że katalog istnieje
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def parse_arguments():
    """
    Parsowanie argumentów linii poleceń.
    
    Returns:
        argparse.Namespace: Sparsowane argumenty
    """
    parser = argparse.ArgumentParser(description="Przeprowadzenie jednorazowej analizy rynkowej")
    
    # Parametry analizy
    parser.add_argument("--symbols", type=str, nargs="+",
                        help="Lista symboli do analizy, np. EURUSD GBPUSD")
    parser.add_argument("--timeframe", type=str, default="H1",
                        help="Timeframe do analizy (np. M15, H1, H4, D1), domyślnie: H1")
    parser.add_argument("--bars", type=int, default=100,
                        help="Liczba świec do analizy, domyślnie: 100")
    parser.add_argument("--force", action="store_true",
                        help="Wymuś analizę nawet jeśli istnieje w cache")
    
    # Parametry MT5
    parser.add_argument("--mt5-path", type=str, 
                        default=None,
                        help="Ścieżka do terminala MT5 (domyślnie: z konfiguracji)")
    parser.add_argument("--login", type=int, default=None,
                        help="Login do MT5 (domyślnie: z konfiguracji)")
    parser.add_argument("--password", type=str, default=None,
                        help="Hasło do MT5 (domyślnie: z konfiguracji)")
    parser.add_argument("--server", type=str, default=None,
                        help="Serwer MT5 (domyślnie: z konfiguracji)")
    
    # Parametry wyjścia
    parser.add_argument("--output", type=str, default="text", 
                        choices=["text", "json", "silent"],
                        help="Format wyjściowy (domyślnie: text)")
    parser.add_argument("--save", type=str, default=None,
                        help="Zapisz wyniki do pliku (domyślnie: brak)")
    
    # Parametry logowania
    parser.add_argument("--log-level", type=str, default="info",
                        choices=["debug", "info", "warning", "error", "critical"],
                        help="Poziom logowania (domyślnie: info)")
    parser.add_argument("--log-file", type=str, 
                        default=None,
                        help="Ścieżka do pliku z logami (domyślnie: brak)")
    
    args = parser.parse_args()
    
    # Sprawdź, czy symbole zostały podane (tylko jeśli nie wyświetlamy pomocy)
    if len(sys.argv) > 1 and '--help' not in sys.argv and '-h' not in sys.argv and not args.symbols:
        parser.error("Argument --symbols jest wymagany")
    
    return args

def format_analysis_output(symbol, analysis, format_type="text"):
    """
    Formatuje wyniki analizy do wybranego formatu.
    
    Args:
        symbol: Symbol analizowanego instrumentu
        analysis: Wyniki analizy
        format_type: Format wyjściowy (text, json)
        
    Returns:
        str: Sformatowane dane analizy
    """
    if format_type == "json":
        # Wzbogacenie danych o symbol
        result = analysis.copy()
        result["symbol"] = symbol
        return json.dumps(result, indent=2, ensure_ascii=False)
    
    # Format tekstowy
    trend_data = analysis.get("trend", {})
    sr_levels = analysis.get("support_resistance", {})
    
    output = []
    output.append(f"==== Analiza rynkowa: {symbol} ====")
    output.append(f"Czas analizy: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append("")
    
    # Trend
    output.append("=== TREND ===")
    output.append(f"Główny trend: {trend_data.get('trend', 'brak danych')}")
    output.append(f"Siła trendu: {trend_data.get('strength', 'brak danych')}/10")
    output.append(f"Zmienność: {trend_data.get('volatility', 'brak danych')}")
    
    # Poziomy wsparcia/oporu
    output.append("\n=== POZIOMY WSPARCIA I OPORU ===")
    supports = sr_levels.get("support", [])
    resistance = sr_levels.get("resistance", [])
    
    output.append("Wsparcia:")
    for level in supports:
        output.append(f"  - {level}")
    
    output.append("Opory:")
    for level in resistance:
        output.append(f"  - {level}")
    
    # Wskaźniki
    output.append("\n=== WSKAŹNIKI ===")
    indicators = analysis.get("indicators", {})
    for name, value in indicators.items():
        output.append(f"{name}: {value}")
    
    # Rekomendacja
    if "recommendation" in analysis:
        output.append("\n=== REKOMENDACJA ===")
        output.append(analysis["recommendation"])
    
    # Pomysł handlowy
    if "trade_idea" in analysis:
        trade = analysis["trade_idea"]
        output.append("\n=== POMYSŁ HANDLOWY ===")
        output.append(f"Kierunek: {trade.get('direction', 'brak')}")
        output.append(f"Wejście: {trade.get('entry', 'brak')}")
        output.append(f"Stop Loss: {trade.get('stop_loss', 'brak')}")
        output.append(f"Take Profit: {trade.get('take_profit', 'brak')}")
        output.append(f"Stosunek zysku do ryzyka: {trade.get('risk_reward_ratio', 'brak')}")
        
        if "comment" in trade:
            output.append(f"\nKomentarz: {trade['comment']}")
    
    return "\n".join(output)

def main():
    """
    Główna funkcja skryptu.
    """
    # Parsowanie argumentów
    args = parse_arguments()
    
    # Jeśli pokazujemy pomoc, kończymy wykonanie
    if '--help' in sys.argv or '-h' in sys.argv:
        return

    # Dodajemy główny katalog projektu do ścieżki
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    # Import lokalnych modułów projektu (po sprawdzeniu argumentów)
    from MT5_Connector.mt5_connector import MT5Connector
    from LLM_Engine.llm_interface import LLMInterface
    from LLM_Engine.config import Config
    
    # Konfiguracja logowania
    logger = configure_logging(args.log_level, args.log_file)
    logger.info(f"Rozpoczęto analizę symboli: {args.symbols}")
    
    # Inicjalizacja MT5
    mt5_config = {}
    if args.mt5_path:
        mt5_config['terminal_path'] = args.mt5_path
    if args.login:
        mt5_config['login'] = args.login
    if args.password:
        mt5_config['password'] = args.password
    if args.server:
        mt5_config['server'] = args.server
    
    try:
        # Tworzenie instancji konektora MT5
        mt5 = MT5Connector(**mt5_config)
        mt5.connect()
        logger.info("Połączono z terminalem MT5")
        
        # Inicjalizacja interfejsu LLM
        config = Config()
        llm_interface = LLMInterface(config)
        
        # Statystyki
        successful_analyses = 0
        failed_analyses = 0
        all_results = {}
        
        # Czas rozpoczęcia
        start_time = time.time()
        
        # Przetwarzanie każdego symbolu
        for symbol in args.symbols:
            symbol = symbol.upper()
            logger.info(f"Analizowanie {symbol} na timeframe {args.timeframe}")
            
            try:
                # Pobranie danych
                df = mt5.get_rates(symbol, args.timeframe, args.bars)
                
                if df is None or len(df) == 0:
                    logger.error(f"Nie udało się pobrać danych dla {symbol}")
                    failed_analyses += 1
                    continue
                
                # Przeprowadzenie analizy
                analysis = llm_interface.analyze_market(
                    symbol, 
                    args.timeframe, 
                    df,
                    force_analysis=args.force
                )
                
                # Formatowanie i wyświetlanie wyników
                if args.output != "silent":
                    formatted = format_analysis_output(symbol, analysis, args.output)
                    if args.output == "text":
                        print(formatted)
                        print("\n" + "="*50 + "\n")
                
                # Zapisanie wyników
                all_results[symbol] = analysis
                successful_analyses += 1
                
            except Exception as e:
                logger.error(f"Błąd podczas analizy {symbol}: {str(e)}")
                failed_analyses += 1
        
        # Zapisanie wszystkich wyników do pliku (jeśli podano)
        if args.save and successful_analyses > 0:
            try:
                # Upewnij się, że katalog istnieje
                save_dir = os.path.dirname(args.save)
                if save_dir and not os.path.exists(save_dir):
                    os.makedirs(save_dir)
                
                # Zapisz do pliku
                with open(args.save, 'w', encoding='utf-8') as f:
                    if args.output == "json":
                        json.dump(all_results, f, indent=2, ensure_ascii=False)
                    else:
                        # Format tekstowy dla wielu symboli
                        for symbol, analysis in all_results.items():
                            f.write(format_analysis_output(symbol, analysis, "text"))
                            f.write("\n\n" + "="*50 + "\n\n")
                
                logger.info(f"Zapisano wyniki do pliku: {args.save}")
            except Exception as e:
                logger.error(f"Błąd podczas zapisywania wyników: {str(e)}")
        
        # Podsumowanie
        elapsed_time = time.time() - start_time
        logger.info(f"Zakończono analizę. Udane: {successful_analyses}, Błędy: {failed_analyses}")
        logger.info(f"Całkowity czas przetwarzania: {elapsed_time:.2f} sekund")
        
    except Exception as e:
        logger.error(f"Krytyczny błąd aplikacji: {str(e)}")
        return 1
    finally:
        # Zamknięcie połączenia MT5
        try:
            mt5.shutdown()
            logger.info("Zamknięto połączenie z terminalem MT5")
        except:
            pass
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
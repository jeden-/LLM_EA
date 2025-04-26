#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do wyświetlania ostatnich analiz rynkowych dla wybranych symboli.
Pozwala na szybki podgląd wyników analiz LLM dla par walutowych.
"""

import os
import sys
import argparse
import json
import logging
from datetime import datetime
from tabulate import tabulate

# Dodajemy główny katalog projektu do ścieżki
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import agenta
from Expert_Advisor.agent_connector import AgentConnector
from LLM_Engine.llm_interface import LLMInterface

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
    parser = argparse.ArgumentParser(description="Wyświetlanie ostatnich analiz rynkowych")
    
    # Parametry połączenia dla weryfikacji danych na żywo
    parser.add_argument("--connect", action="store_true",
                        help="Połącz z agentem w celu weryfikacji danych na żywo")
    parser.add_argument("--host", type=str, default="localhost",
                        help="Adres hosta (domyślnie: localhost)")
    parser.add_argument("--req-port", type=int, default=5555,
                        help="Port dla komunikacji REQUEST/REPLY (domyślnie: 5555)")
    
    # Filtry wyświetlania
    parser.add_argument("--symbol", type=str, default=None,
                        help="Symbol do wyświetlenia (domyślnie: wszystkie)")
    parser.add_argument("--format", type=str, default="table", choices=["table", "json", "text"],
                        help="Format wyświetlania wyników (domyślnie: table)")
    parser.add_argument("--details", action="store_true",
                        help="Wyświetl szczegółowe informacje o analizie")
    
    # Parametry logowania
    parser.add_argument("--log-level", type=str, default="info",
                        choices=["debug", "info", "warning", "error", "critical"],
                        help="Poziom logowania (domyślnie: info)")
    parser.add_argument("--log-file", type=str, 
                        default=None,
                        help="Ścieżka do pliku z logami (domyślnie: brak)")
    
    return parser.parse_args()

def format_analysis_table(analyses, show_details=False):
    """
    Formatuje analizy do postaci tabeli.
    
    Args:
        analyses: Słownik z analizami dla symboli
        show_details: Czy pokazywać szczegóły analizy
        
    Returns:
        str: Sformatowany tekst tabeli
    """
    headers = ["Symbol", "Trend", "Siła", "Rekomendacja", "Data analizy"]
    rows = []
    
    for symbol, analysis in analyses.items():
        if not analysis:
            rows.append([symbol, "Brak danych", "", "", ""])
            continue
            
        # Podstawowe dane
        timestamp = analysis.get('timestamp', 'b/d')
        if isinstance(timestamp, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            
        trend = analysis.get('trend', {}).get('name', 'b/d')
        strength = analysis.get('trend', {}).get('strength', 'b/d')
        recommendation = analysis.get('recommendation', 'b/d')
        
        rows.append([
            symbol, 
            trend, 
            strength, 
            recommendation, 
            timestamp
        ])
    
    # Sortowanie po symbolu
    rows.sort(key=lambda x: x[0])
    
    return tabulate(rows, headers=headers, tablefmt="grid")

def format_analysis_json(analyses):
    """
    Formatuje analizy do formatu JSON.
    
    Args:
        analyses: Słownik z analizami dla symboli
        
    Returns:
        str: Sformatowany tekst JSON
    """
    return json.dumps(analyses, indent=2, ensure_ascii=False)

def format_analysis_text(analyses, show_details=False):
    """
    Formatuje analizy do zwykłego tekstu.
    
    Args:
        analyses: Słownik z analizami dla symboli
        show_details: Czy pokazywać szczegóły analizy
        
    Returns:
        str: Sformatowany tekst
    """
    result = []
    
    for symbol, analysis in analyses.items():
        result.append(f"===== {symbol} =====")
        
        if not analysis:
            result.append("Brak danych dla tego symbolu")
            result.append("")
            continue
        
        # Podstawowe informacje
        timestamp = analysis.get('timestamp', 'b/d')
        if isinstance(timestamp, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        
        result.append(f"Data analizy: {timestamp}")
        
        # Informacje o trendzie
        trend_data = analysis.get('trend', {})
        result.append(f"Trend: {trend_data.get('name', 'b/d')}")
        result.append(f"Siła trendu: {trend_data.get('strength', 'b/d')}")
        result.append(f"Zmienność: {trend_data.get('volatility', 'b/d')}")
        
        # Poziomy wsparcia/oporu
        sr_levels = analysis.get('support_resistance', {})
        support = sr_levels.get('support', [])
        resistance = sr_levels.get('resistance', [])
        
        if support:
            result.append(f"Poziomy wsparcia: {', '.join(map(str, support))}")
        if resistance:
            result.append(f"Poziomy oporu: {', '.join(map(str, resistance))}")
        
        # Rekomendacja
        result.append(f"Rekomendacja: {analysis.get('recommendation', 'b/d')}")
        
        # Idea handlowa (jeśli dostępna)
        trade_idea = analysis.get('trade_idea', {})
        if trade_idea:
            result.append("\nIdea handlowa:")
            result.append(f"  Kierunek: {trade_idea.get('direction', 'b/d')}")
            result.append(f"  Wejście: {trade_idea.get('entry', 'b/d')}")
            result.append(f"  Stop Loss: {trade_idea.get('stop_loss', 'b/d')}")
            result.append(f"  Take Profit: {trade_idea.get('take_profit', 'b/d')}")
            result.append(f"  Ryzyko/Zysk: {trade_idea.get('risk_reward_ratio', 'b/d')}")
        
        # Szczegóły analizy (jeśli wybrano)
        if show_details and 'details' in analysis:
            result.append("\nSzczegóły analizy:")
            for key, value in analysis.get('details', {}).items():
                result.append(f"  {key}: {value}")
        
        result.append("\n")
    
    return "\n".join(result)

def main():
    """Główna funkcja programu."""
    # Parsowanie argumentów
    args = parse_arguments()
    
    # Konfiguracja logowania
    logger = configure_logging(args.log_level, args.log_file)
    
    analyses = {}
    
    if args.connect:
        # Połączenie z uruchomionym agentem
        try:
            logger.info(f"Nawiązywanie połączenia z agentem ({args.host}:{args.req_port})")
            agent = AgentConnector(
                server_address=args.host,
                req_port=args.req_port,
                pub_port=0,  # Nie potrzebujemy portu publikacyjnego
                update_interval=0,  # Nie będziemy aktualizować
                debug_mode=True
            )
            
            # Pobierz analizy
            if args.symbol:
                analysis = agent.show_last_analysis(args.symbol)
                if analysis:
                    analyses[args.symbol] = analysis
            else:
                analyses = agent.show_last_analysis()
                
            if not analyses:
                print("Brak dostępnych analiz. Czy agent jest uruchomiony i przeprowadził analizy?")
                return
                
        except Exception as e:
            logger.error(f"Błąd podczas łączenia z agentem: {e}")
            return
    else:
        # Tworzymy instancję LLMInterface, aby odczytać analizy z pliku cache
        logger.info("Odczytywanie analiz z pliku cache...")
        try:
            llm = LLMInterface()
            cache_data = llm.cache_manager.load_cache()
            
            # Wyciągamy analizy z cache
            for key, value in cache_data.items():
                if key.startswith("market_analysis_"):
                    # Wyciągamy symbol z klucza cache
                    parts = key.split("_")
                    if len(parts) > 2:
                        symbol = parts[2].upper()
                        if args.symbol and args.symbol.upper() != symbol:
                            continue
                        analyses[symbol] = value.get('result', {})
        except Exception as e:
            logger.error(f"Błąd podczas odczytywania cache: {e}")
            return
    
    # Brak danych
    if not analyses:
        print("Nie znaleziono żadnych analiz")
        return
        
    # Formatowanie wyników
    if args.format == "table":
        output = format_analysis_table(analyses, args.details)
    elif args.format == "json":
        output = format_analysis_json(analyses)
    else:  # text
        output = format_analysis_text(analyses, args.details)
    
    # Wyświetlenie wyników
    print(output)

if __name__ == "__main__":
    main() 
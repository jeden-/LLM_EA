"""
Skrypt do walidacji wyników i wydajności modelu LLM.

Skrypt przeprowadza testy i walidację modułu LLM_Engine
na przygotowanych wcześniej danych testowych, analizując
skuteczność modelu, czasochlonność oraz dokładność odpowiedzi.
"""

import os
import sys
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

# Dodanie ścieżki głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM_Engine.llm_engine import LLMEngine
from LLM_Engine.market_analyzer import MarketAnalyzer
from LLM_Engine.prompt_builder import PromptBuilder
from LLM_Engine.response_parser import ResponseParser
from LLM_Engine.llm_interface import LLMInterface

# Ścieżka do katalogu z danymi testowymi
TEST_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tests', 'test_data')
RESULTS_DIR = os.path.join(TEST_DATA_DIR, 'results')

# Upewnij się, że katalog wyników istnieje
os.makedirs(RESULTS_DIR, exist_ok=True)

# Inicjalizacja podstawowych komponentów
response_parser = ResponseParser()
prompt_builder = PromptBuilder()

# Tworzymy tymczasowy plik konfiguracyjny dla testów
test_config = {
    "model_name": "grok-3-mini-fast-beta",
    "model_type": "grok",
    "xai_api_key": "test_key",
    "xai_base_url": "https://api.x.ai/v1",
    "timeout": 60,
    "max_retries": 1,
    "cache_dir": os.path.join(TEST_DATA_DIR, "cache"),
    "enable_caching": True
}

config_path = os.path.join(TEST_DATA_DIR, "test_config.json")
with open(config_path, 'w') as f:
    json.dump(test_config, f, indent=2)

# Inicjalizacja silnika LLM z konfiguracją testową
llm_engine = LLMEngine(config_file=config_path)

# Możemy korzystać teraz z wewnętrznych komponentów silnika
market_analyzer = llm_engine.market_analyzer
llm_client = llm_engine.llm_client

def load_test_scenarios():
    """
    Ładuje scenariusze testowe z katalogu danych testowych.
    
    Returns:
        list: Lista scenariuszy testowych
    """
    scenarios = []
    
    # Znajdź wszystkie pliki metadanych
    metadata_files = [f for f in os.listdir(TEST_DATA_DIR) if f.endswith('_metadata.json')]
    
    for metadata_file in metadata_files:
        scenario_name = metadata_file.replace('_metadata.json', '')
        
        # Ładowanie metadanych
        with open(os.path.join(TEST_DATA_DIR, metadata_file), 'r') as f:
            metadata = json.load(f)
        
        # Ładowanie oczekiwanego wyniku
        with open(os.path.join(TEST_DATA_DIR, f'{scenario_name}_expected.json'), 'r') as f:
            expected = json.load(f)
        
        # Ładowanie sformatowanych danych
        with open(os.path.join(TEST_DATA_DIR, f'{scenario_name}_formatted.json'), 'r') as f:
            formatted_data = json.load(f)
        
        scenarios.append({
            'name': scenario_name,
            'metadata': metadata,
            'expected': expected,
            'formatted_data': formatted_data
        })
    
    return scenarios

def run_analysis(scenario):
    """
    Przeprowadza analizę scenariusza za pomocą modułu LLM_Engine.
    
    Args:
        scenario (dict): Scenariusz testowy
    
    Returns:
        dict: Wyniki analizy
    """
    start_time = time.time()
    
    try:
        # Przygotowanie danych wejściowych do analizy
        market_data = {
            "symbol": scenario['metadata']['symbol'],
            "timeframe": scenario['metadata']['timeframe'],
            "price_data": scenario['formatted_data']['data'],
            "indicators": scenario['formatted_data']['indicators'],
            "news": []  # Nie mamy wiadomości w danych testowych
        }
        
        # Analiza rynku
        market_analysis = llm_engine.analyze_market(market_data)
        
        # Generowanie pomysłu handlowego
        trade_idea = llm_engine.generate_trade_idea(market_data)
        
        end_time = time.time()
        duration = end_time - start_time
        
        return {
            'success': True,
            'market_analysis': market_analysis,
            'trade_idea': trade_idea,
            'duration': duration
        }
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        
        return {
            'success': False,
            'error': str(e),
            'duration': duration
        }

def evaluate_results(scenario, results):
    """
    Ocenia wyniki analizy w porównaniu z oczekiwanymi wynikami.
    
    Args:
        scenario (dict): Scenariusz testowy
        results (dict): Wyniki analizy
    
    Returns:
        dict: Ocena wyników
    """
    if not results['success']:
        return {
            'success': False,
            'error': results['error'],
            'score': 0.0,
            'duration': results['duration']
        }
    
    expected = scenario['expected']
    score = 0.0
    max_score = 4.0  # Maksymalna możliwa ocena
    
    # Ocena trendu
    if 'trend' in expected and 'trend' in results['market_analysis']:
        if expected['trend'].lower() == results['market_analysis']['trend'].lower():
            score += 1.0
    
    # Ocena setupu
    if 'setup' in expected and 'setup' in results['market_analysis']:
        if expected['setup'].lower() in results['market_analysis']['setup'].lower():
            score += 1.0
    
    # Ocena akcji
    if 'action' in expected and 'action' in results['trade_idea']:
        if expected['action'].lower() == results['trade_idea']['action'].lower():
            score += 1.0
    
    # Ocena kierunku
    if 'direction' in expected and 'direction' in results['trade_idea']:
        if expected['direction'].lower() == results['trade_idea']['direction'].lower():
            score += 1.0
    
    # Normalizacja wyniku
    normalized_score = score / max_score
    
    return {
        'success': True,
        'score': normalized_score,
        'raw_score': score,
        'max_score': max_score,
        'duration': results['duration']
    }

def run_validation():
    """
    Przeprowadza pełną walidację modułu LLM_Engine na wszystkich scenariuszach testowych.
    
    Returns:
        dict: Wyniki walidacji
    """
    print("Rozpoczynanie walidacji modułu LLM_Engine...")
    
    scenarios = load_test_scenarios()
    print(f"Załadowano {len(scenarios)} scenariuszy testowych.")
    
    all_results = []
    total_duration = 0.0
    total_score = 0.0
    successful_scenarios = 0
    
    for i, scenario in enumerate(scenarios):
        print(f"Analizowanie scenariusza {i+1}/{len(scenarios)}: {scenario['name']}...")
        
        # Przeprowadzenie analizy
        results = run_analysis(scenario)
        
        # Ocena wyników
        evaluation = evaluate_results(scenario, results)
        
        # Zapisanie wyników
        scenario_results = {
            'scenario_name': scenario['name'],
            'description': scenario['metadata']['description'],
            'symbol': scenario['metadata']['symbol'],
            'timeframe': scenario['metadata']['timeframe'],
            'success': evaluation['success'],
            'score': evaluation.get('score', 0.0),
            'duration': evaluation['duration']
        }
        
        if evaluation['success']:
            scenario_results['raw_score'] = evaluation['raw_score']
            scenario_results['max_score'] = evaluation['max_score']
            total_score += evaluation['score']
            successful_scenarios += 1
        else:
            scenario_results['error'] = evaluation['error']
        
        all_results.append(scenario_results)
        total_duration += evaluation['duration']
        
        # Zapisanie pełnych wyników analizy
        if results['success']:
            analysis_results = {
                'market_analysis': results['market_analysis'],
                'trade_idea': results['trade_idea'],
                'expected': scenario['expected'],
                'evaluation': evaluation
            }
            
            results_file = os.path.join(RESULTS_DIR, f"{scenario['name']}_results.json")
            with open(results_file, 'w') as f:
                json.dump(analysis_results, f, indent=2)
    
    # Obliczenie podsumowania
    avg_score = total_score / len(scenarios) if scenarios else 0.0
    avg_duration = total_duration / len(scenarios) if scenarios else 0.0
    success_rate = successful_scenarios / len(scenarios) if scenarios else 0.0
    
    summary = {
        'total_scenarios': len(scenarios),
        'successful_scenarios': successful_scenarios,
        'success_rate': success_rate,
        'average_score': avg_score,
        'average_duration': avg_duration,
        'total_duration': total_duration,
        'test_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'results': all_results
    }
    
    # Zapisanie podsumowania
    summary_file = os.path.join(RESULTS_DIR, "validation_summary.json")
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Generowanie tabeli wyników
    results_df = pd.DataFrame(all_results)
    if not results_df.empty:
        results_df.to_csv(os.path.join(RESULTS_DIR, "validation_results.csv"), index=False)
    
    # Wyświetlenie podsumowania
    print("\nWyniki walidacji:")
    print(f"Całkowita liczba scenariuszy: {len(scenarios)}")
    print(f"Udane scenariusze: {successful_scenarios}")
    print(f"Wskaźnik powodzenia: {success_rate:.2%}")
    print(f"Średni wynik: {avg_score:.2%}")
    print(f"Średni czas analizy: {avg_duration:.2f} s")
    print(f"Całkowity czas analizy: {total_duration:.2f} s")
    print(f"\nSzczegółowe wyniki zapisano w katalogu: {RESULTS_DIR}")
    
    return summary

def tune_prompt_parameters():
    """
    Przeprowadza strojenie parametrów promptów na podstawie wyników walidacji.
    
    Returns:
        dict: Rekomendowane parametry promptów
    """
    print("\nRozpoczęcie strojenia parametrów promptów...")
    
    # W rzeczywistej implementacji należałoby przetestować różne warianty promptów
    # i porównać ich skuteczność. W tej wersji demonstracyjnej po prostu zwracamy
    # zalecane parametry.
    
    recommended_params = {
        'temperature': 0.2,  # Niska temperatura dla bardziej deterministycznych wyników
        'max_tokens': 2000,  # Wystarczająco dużo tokenów dla pełnej analizy
        'num_candles_context': 50,  # Liczba świec do uwzględnienia w kontekście
        'num_candles_display': 20,  # Liczba świec do wyświetlenia w prompcie
        'include_indicators': True,  # Uwzględnienie wskaźników technicznych
        'include_patterns': True,  # Uwzględnienie formacji świecowych
        'prompt_structure': [
            'market_context',
            'technical_indicators',
            'candlestick_patterns',
            'task_description',
            'output_format',
            'examples'
        ]
    }
    
    # Zapisz rekomendowane parametry
    params_file = os.path.join(RESULTS_DIR, "recommended_prompt_params.json")
    with open(params_file, 'w') as f:
        json.dump(recommended_params, f, indent=2)
    
    print(f"Rekomendowane parametry promptów zapisano w pliku: {params_file}")
    
    return recommended_params

if __name__ == "__main__":
    # Sprawdź, czy dane testowe istnieją
    if not os.path.exists(TEST_DATA_DIR) or not any(f.endswith('_formatted.json') for f in os.listdir(TEST_DATA_DIR)):
        print("Brak danych testowych. Najpierw wygeneruj dane za pomocą skryptu generate_test_data.py.")
        sys.exit(1)
    
    # Przeprowadź walidację
    summary = run_validation()
    
    # Przeprowadź strojenie parametrów promptów
    recommended_params = tune_prompt_parameters()
    
    print("\nWalidacja i strojenie parametrów zakończone.") 
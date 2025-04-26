#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skrypt do uruchomienia testów systemu LLM Trading na koncie demo MT5.
Skrypt automatycznie uruchamia wszystkie niezbędne komponenty systemu,
monitoruje ich działanie i zbiera dane do analizy.
"""

import os
import sys
import time
import argparse
import logging
import signal
import subprocess
import datetime
import json
from pathlib import Path

# Dodajemy ścieżkę głównego katalogu projektu do sys.path
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_DIR))

from Common.logging_config import setup_logging
from Database.database import DatabaseHandler

# Inicjalizacja parsera argumentów
parser = argparse.ArgumentParser(description='Uruchom testy systemu LLM Trading na koncie demo.')
parser.add_argument('--env', type=str, default='dev', choices=['dev', 'test', 'prod'],
                    help='Środowisko, w którym ma być uruchomiony system (domyślnie: dev)')
parser.add_argument('--duration', type=int, default=24,
                    help='Czas trwania testu w godzinach (domyślnie: 24)')
parser.add_argument('--symbols', type=str, default='EURUSD,GBPUSD,USDJPY',
                    help='Lista par walutowych do monitorowania, oddzielonych przecinkami')
parser.add_argument('--port', type=int, default=5000,
                    help='Port, na którym ma być uruchomiony dashboard (domyślnie: 5000)')
parser.add_argument('--no-dashboard', action='store_true',
                    help='Nie uruchamiaj dashboardu')
parser.add_argument('--verbose', '-v', action='store_true',
                    help='Wyświetlaj więcej informacji diagnostycznych')
parser.add_argument('--debug', action='store_true',
                    help='Uruchom w trybie debugowania')

# Funkcja do uruchamiania procesów
def run_process(cmd, env_vars=None, cwd=None):
    """Uruchamia proces z podanymi parametrami."""
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    
    return subprocess.Popen(
        cmd,
        env=env,
        cwd=cwd or PROJECT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

# Funkcja do zatrzymywania procesów
def kill_processes(processes):
    """Zatrzymuje uruchomione procesy."""
    for name, process in processes.items():
        if process and process.poll() is None:
            logger.info(f"Zatrzymywanie procesu {name}...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Proces {name} nie zatrzymał się - wymuszam zakończenie.")
                process.kill()

# Funkcja do zbierania statystyk
def collect_statistics(db_handler, start_time):
    """Zbiera i zapisuje statystyki testów."""
    end_time = datetime.datetime.now()
    
    # Pobierz statystyki z bazy danych
    trades = db_handler.get_all_trades()
    trade_ideas = db_handler.get_all_trade_ideas()
    analyses = db_handler.get_market_analyses()
    
    # Oblicz podstawowe metryki
    if trades:
        profitable_trades = sum(1 for t in trades if t.get('profit', 0) > 0)
        losing_trades = sum(1 for t in trades if t.get('profit', 0) <= 0)
        total_profit = sum(t.get('profit', 0) for t in trades)
        win_rate = profitable_trades / len(trades) if trades else 0
    else:
        profitable_trades = losing_trades = total_profit = 0
        win_rate = 0
    
    # Przygotuj statystyki
    stats = {
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'duration_hours': (end_time - start_time).total_seconds() / 3600,
        'trades_count': len(trades),
        'trade_ideas_count': len(trade_ideas),
        'analyses_count': len(analyses),
        'profitable_trades': profitable_trades,
        'losing_trades': losing_trades,
        'total_profit': total_profit,
        'win_rate': win_rate
    }
    
    # Zapisz statystyki do pliku
    stats_dir = PROJECT_DIR / 'data' / 'statistics'
    stats_dir.mkdir(exist_ok=True, parents=True)
    
    stats_file = stats_dir / f'demo_test_{start_time.strftime("%Y%m%d_%H%M%S")}.json'
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=4)
    
    logger.info(f"Statystyki testu zapisano do {stats_file}")
    
    # Wyświetl podsumowanie
    logger.info("=== PODSUMOWANIE TESTU ===")
    logger.info(f"Czas trwania: {stats['duration_hours']:.2f} godzin")
    logger.info(f"Liczba transakcji: {stats['trades_count']}")
    logger.info(f"Zyskowne transakcje: {stats['profitable_trades']} ({stats['win_rate'] * 100:.2f}%)")
    logger.info(f"Całkowity zysk/strata: {stats['total_profit']:.2f}")
    logger.info(f"Liczba analiz rynkowych: {stats['analyses_count']}")
    logger.info(f"Liczba wygenerowanych pomysłów handlowych: {stats['trade_ideas_count']}")
    logger.info("=== KONIEC PODSUMOWANIA ===")
    
    return stats

# Funkcja do kontroli czasu testu
def is_test_finished(start_time, duration_hours):
    """Sprawdza, czy test powinien się zakończyć."""
    elapsed = (datetime.datetime.now() - start_time).total_seconds() / 3600
    return elapsed >= duration_hours

# Funkcja do sprawdzania stanu procesów
def check_processes(processes):
    """Sprawdza stan uruchomionych procesów i restartuje je w razie potrzeby."""
    for name, process in processes.items():
        if process and process.poll() is not None:
            logger.warning(f"Proces {name} zakończył działanie (kod wyjścia: {process.returncode}) - restartuję...")
            
            # Pobierz standardowe wyjście i błędy
            stdout, stderr = process.communicate()
            if stdout:
                logger.debug(f"Ostatnie wyjście {name}: {stdout}")
            if stderr:
                logger.error(f"Ostatnie błędy {name}: {stderr}")
            
            # Uruchom proces ponownie, używając tej samej komendy
            processes[name] = run_process(process.args, cwd=process.cwd)
            logger.info(f"Proces {name} zrestartowany.")

# Główna funkcja
def main():
    args = parser.parse_args()
    
    # Konfiguracja logowania
    log_level = logging.DEBUG if args.debug else (logging.INFO if args.verbose else logging.WARNING)
    setup_logging(log_level, f"logs/demo_test/demo_test_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logger.info(f"Rozpoczynam test systemu LLM Trading w środowisku {args.env}")
    logger.info(f"Czas trwania testu: {args.duration} godzin")
    logger.info(f"Monitorowane pary walutowe: {args.symbols}")
    
    # Sprawdź, czy plik .env istnieje
    if not os.path.exists(PROJECT_DIR / '.env'):
        logger.error("Plik .env nie istnieje. Utwórz go na podstawie .env.example i skonfiguruj zmienne środowiskowe.")
        return 1
    
    # Sprawdź konfigurację środowiska
    env_file = PROJECT_DIR / f'config/{args.env}/config.json'
    if not env_file.exists():
        logger.error(f"Plik konfiguracyjny {env_file} nie istnieje.")
        return 1
    
    # Ustaw zmienne środowiskowe
    env_vars = {
        'ENV': args.env,
        'DEBUG': 'True' if args.debug else 'False',
        'LOG_LEVEL': 'DEBUG' if args.debug else ('INFO' if args.verbose else 'WARNING'),
        'TRADING_SYMBOLS': args.symbols,
        'TRADING_MODE': 'DEMO'  # Upewnij się, że tryb jest ustawiony na DEMO
    }
    
    # Inicjalizuj połączenie z bazą danych
    db_handler = DatabaseHandler(env=args.env)
    
    # Uruchom procesy komponentów systemu
    processes = {}
    start_time = datetime.datetime.now()
    
    try:
        # Uruchom bazę danych
        logger.info("Uruchamiam bazę danych...")
        processes['database'] = run_process(
            ['python', 'Database/run_database.py', f'--env={args.env}'],
            env_vars=env_vars
        )
        time.sleep(2)  # Daj czas na uruchomienie bazy danych
        
        # Uruchom konektor MT5
        logger.info("Uruchamiam konektor MT5...")
        processes['mt5_connector'] = run_process(
            ['python', 'MT5_Connector/run_connector.py', f'--env={args.env}'],
            env_vars=env_vars
        )
        time.sleep(2)
        
        # Uruchom silnik LLM
        logger.info("Uruchamiam silnik LLM...")
        processes['llm_engine'] = run_process(
            ['python', 'LLM_Engine/run_engine.py', f'--env={args.env}'],
            env_vars=env_vars
        )
        time.sleep(2)
        
        # Uruchom agenta zarządzającego
        logger.info("Uruchamiam agenta zarządzającego...")
        processes['agent_manager'] = run_process(
            ['python', 'Agent_Manager/run_manager.py', f'--env={args.env}'],
            env_vars=env_vars
        )
        time.sleep(2)
        
        # Uruchom dashboard (opcjonalnie)
        if not args.no_dashboard:
            logger.info(f"Uruchamiam dashboard na porcie {args.port}...")
            processes['dashboard'] = run_process(
                ['python', 'Dashboard/run_dashboard.py', f'--env={args.env}', f'--port={args.port}'],
                env_vars=env_vars
            )
            logger.info(f"Dashboard dostępny pod adresem: http://localhost:{args.port}")
        
        # Uruchom monitorowanie
        logger.info("Uruchamiam monitorowanie systemu...")
        processes['monitoring'] = run_process(
            ['python', 'scripts/monitor_system.py', f'--env={args.env}', '--auto-restart', '--db-check-interval=3600'],
            env_vars=env_vars
        )
        
        logger.info("Wszystkie komponenty uruchomione. Test rozpoczęty.")
        logger.info(f"Test potrwa do {(start_time + datetime.timedelta(hours=args.duration)).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Główna pętla testu
        try:
            while not is_test_finished(start_time, args.duration):
                # Sprawdź stan procesów
                check_processes(processes)
                
                # Wyświetl status
                elapsed = (datetime.datetime.now() - start_time).total_seconds() / 3600
                remaining = args.duration - elapsed
                logger.info(f"Test w trakcie: {elapsed:.2f}h / {args.duration}h (pozostało: {remaining:.2f}h)")
                
                # Aktualizuj statystyki co godzinę
                if int(elapsed) > 0 and int(elapsed) % 1 == 0:
                    try:
                        trades_count = len(db_handler.get_all_trades())
                        ideas_count = len(db_handler.get_all_trade_ideas())
                        analyses_count = len(db_handler.get_market_analyses())
                        logger.info(f"Status po {int(elapsed)}h: {trades_count} transakcji, {ideas_count} pomysłów, {analyses_count} analiz")
                    except Exception as e:
                        logger.error(f"Błąd podczas pobierania statystyk: {e}")
                
                # Poczekaj przed następnym sprawdzeniem
                time.sleep(300)  # Sprawdzaj co 5 minut
                
            logger.info("Czas testu upłynął. Zatrzymuję komponenty...")
            
        except KeyboardInterrupt:
            logger.info("Otrzymano sygnał przerwania. Zatrzymuję test...")
        
        # Zbierz statystyki przed zatrzymaniem
        try:
            stats = collect_statistics(db_handler, start_time)
        except Exception as e:
            logger.error(f"Błąd podczas zbierania statystyk: {e}")
            stats = {}
        
        # Zatrzymaj wszystkie procesy
        kill_processes(processes)
        
        logger.info("Test zakończony.")
        return 0
        
    except Exception as e:
        logger.error(f"Wystąpił błąd podczas testu: {e}", exc_info=True)
        kill_processes(processes)
        return 1
    finally:
        # Upewnij się, że wszystkie procesy zostały zatrzymane
        kill_processes(processes)

# Obsługa sygnału przerwania
def signal_handler(sig, frame):
    logger.info("Otrzymano sygnał przerwania. Zatrzymuję test...")
    sys.exit(0)

if __name__ == "__main__":
    # Konfiguracja logowania
    logger = logging.getLogger(__name__)
    
    # Rejestracja handlera sygnału
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    sys.exit(main()) 
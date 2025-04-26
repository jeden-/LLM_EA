#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Agent Connector - moduł łączący system analizy LLM z Expert Advisor MT5.
Zarządza komunikacją dwukierunkową poprzez ZeroMQ.
"""

import os
import sys
import json
import time
import logging
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime
import traceback

# Dodanie katalogu głównego projektu do ścieżki, aby umożliwić importy
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import klienta ZeroMQ
from Common.zmq_client import ZmqClient
from Database.database import DatabaseHandler
from LLM_Engine.llm_engine import LLMEngine

# Konfiguracja loggera
logger = logging.getLogger(__name__)

class AgentConnector:
    """
    Klasa AgentConnector zarządza komunikacją między systemem analizy LLM
    a Expert Advisorem MT5 poprzez protokół ZeroMQ.
    
    Funkcje:
    - Odbieranie statusu i danych rynkowych z MT5
    - Przetwarzanie danych przez silnik LLM
    - Wysyłanie sygnałów handlowych do MT5
    - Zapisywanie danych transakcyjnych w bazie danych
    """
    
    def __init__(self, 
                 server_address: str = "localhost", 
                 req_port: int = 5555, 
                 pub_port: int = 5556,
                 update_interval: int = 60,
                 debug_mode: bool = False):
        """
        Inicjalizacja agenta łączącego.
        
        Args:
            server_address: Adres serwera ZeroMQ (domyślnie localhost)
            req_port: Port dla komunikacji REQUEST/REPLY
            pub_port: Port dla komunikacji PUBLISH/SUBSCRIBE
            update_interval: Interwał aktualizacji analizy w sekundach (domyślnie 60)
            debug_mode: Tryb debugowania - więcej logów i bez rzeczywistego handlu
        """
        self.zmq_client = ZmqClient(server_address, req_port, pub_port)
        self.llm_engine = LLMEngine()
        self.db_handler = DatabaseHandler()
        
        self.update_interval = update_interval
        self.debug_mode = debug_mode
        self.last_update_time = 0
        self.active_symbols = []
        self.running = False
        
        # Statystyki
        self.stats = {
            "signals_sent": 0,
            "successful_trades": 0,
            "failed_trades": 0,
            "errors": 0,
            "start_time": None,
            "last_signal_time": None
        }
        
    def connect(self) -> bool:
        """
        Nawiązanie połączenia z Expert Advisor poprzez ZeroMQ.
        
        Returns:
            True, jeśli połączenie zostało nawiązane pomyślnie, False w przeciwnym razie
        """
        logger.info("Łączenie z Expert Advisor...")
        
        # Połączenie z ZeroMQ
        if not self.zmq_client.connect():
            logger.error(f"Nie udało się połączyć z ZeroMQ: {self.zmq_client.get_last_error()}")
            return False
            
        # Sprawdzenie statusu EA
        status = self.zmq_client.get_status()
        if not status:
            logger.error("Nie udało się pobrać statusu EA")
            return False
            
        logger.info(f"Połączono z Expert Advisor. Status: {status}")
        
        # Rejestracja aktywnych symboli
        if "symbols" in status:
            self.active_symbols = status["symbols"]
            logger.info(f"Aktywne symbole: {self.active_symbols}")
        else:
            # Domyślny symbol, jeśli nie podano w statusie
            self.active_symbols = ["EURUSD"]
            logger.warning(f"Nie znaleziono aktywnych symboli w statusie. Używam domyślnego: {self.active_symbols}")
        
        # Inicjalizacja statystyk
        self.stats["start_time"] = datetime.now().isoformat()
        
        return True
    
    def disconnect(self):
        """Zakończenie połączenia z Expert Advisor."""
        if self.zmq_client:
            self.zmq_client.disconnect()
        logger.info("Rozłączono z Expert Advisor")
    
    def start(self):
        """Uruchomienie agenta łączącego w pętli głównej."""
        if not self.zmq_client.is_connected:
            if not self.connect():
                logger.error("Nie można uruchomić agenta bez połączenia z Expert Advisor")
                return
        
        logger.info("Uruchamianie agenta łączącego...")
        self.running = True
        self.stats["start_time"] = datetime.now().isoformat()
        
        try:
            while self.running:
                try:
                    # Sprawdzenie, czy czas na aktualizację analizy
                    current_time = time.time()
                    if current_time - self.last_update_time >= self.update_interval:
                        self._update_analysis()
                        self.last_update_time = current_time
                    
                    # Krótka pauza, aby nie obciążać CPU
                    time.sleep(0.1)
                    
                except Exception as e:
                    self.stats["errors"] += 1
                    logger.error(f"Błąd w pętli głównej: {e}")
                    logger.error(traceback.format_exc())
                    # Krótkie opóźnienie przed ponowną próbą
                    time.sleep(5)
                    
        except KeyboardInterrupt:
            logger.info("Przerwano działanie agenta przez użytkownika")
        finally:
            self.disconnect()
    
    def stop(self):
        """Zatrzymanie działania agenta."""
        logger.info("Zatrzymywanie agenta łączącego...")
        self.running = False
    
    def _update_analysis(self):
        """
        Aktualizacja analizy rynku i generowanie sygnałów handlowych.
        """
        logger.info("Aktualizacja analizy rynku...")
        
        for symbol in self.active_symbols:
            try:
                # Pobranie danych rynkowych dla symbolu
                market_data = self._get_market_data(symbol)
                if not market_data:
                    logger.warning(f"Brak danych rynkowych dla {symbol}")
                    continue
                
                # Analiza danych przez silnik LLM
                analysis_result = self.llm_engine.analyze_market(market_data)
                
                if not analysis_result:
                    logger.warning(f"Nie udało się przeprowadzić analizy dla {symbol}")
                    continue
                    
                # Generowanie idei handlowej na podstawie analizy
                trade_idea = self.llm_engine.generate_trade_idea(market_data, analysis_result)
                
                if not trade_idea:
                    logger.warning(f"Nie udało się wygenerować idei handlowej dla {symbol}")
                    continue
                
                # Sprawdzenie, czy mamy sygnał handlowy
                if trade_idea.get("direction") in ["buy", "sell"]:
                    # Przekształcenie idei handlowej na sygnał
                    self._process_trade_idea(symbol, trade_idea)
                else:
                    logger.info(f"Brak sygnału handlowego dla {symbol} - kierunek: {trade_idea.get('direction')}")
                
                # Zapisanie wyników analizy w bazie danych
                self._save_analysis_to_db(symbol, market_data, analysis_result, trade_idea)
                
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Błąd podczas analizy symbolu {symbol}: {e}")
                logger.error(traceback.format_exc())
    
    def _get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Pobranie danych rynkowych z Expert Advisor.
        
        Args:
            symbol: Symbol instrumentu
            
        Returns:
            Słownik z danymi rynkowymi lub None w przypadku błędu
        """
        try:
            # Przygotowanie wiadomości
            request = {
                "type": "get_market_data",
                "symbol": symbol,
                "timestamp": datetime.now().isoformat()
            }
            
            # Wysłanie zapytania
            self.zmq_client.req_socket.send_json(request)
            
            # Odebranie odpowiedzi
            reply = self.zmq_client.req_socket.recv_json()
            
            if reply.get("type") == "market_data" and reply.get("symbol") == symbol:
                return reply
            else:
                logger.error(f"Nieoczekiwana odpowiedź na zapytanie o dane rynkowe: {reply}")
                return None
                
        except Exception as e:
            logger.error(f"Błąd podczas pobierania danych rynkowych dla {symbol}: {e}")
            return None
    
    def _process_trade_idea(self, symbol: str, trade_idea: Dict[str, Any]):
        """
        Przetworzenie idei handlowej na sygnał dla Expert Advisor.
        
        Args:
            symbol: Symbol instrumentu
            trade_idea: Słownik z ideą handlową
        """
        direction = trade_idea.get("direction", "").upper()
        
        # Sprawdzenie, czy mamy poprawną ideę handlową
        if direction not in ["BUY", "SELL"]:
            logger.warning(f"Nieprawidłowy kierunek w idei handlowej: {direction}")
            return
            
        # Pobranie parametrów
        entry_price = float(trade_idea.get("entry", 0))
        stop_loss = float(trade_idea.get("stop_loss", 0))
        take_profit = float(trade_idea.get("take_profit", 0))
        
        logger.info(f"Generowanie sygnału handlowego: {direction} {symbol} @ {entry_price}, SL: {stop_loss}, TP: {take_profit}")
        
        # W trybie debugowania tylko logujemy sygnał
        if self.debug_mode:
            logger.info(f"[DEBUG] Sygnał handlowy nie zostanie wysłany (tryb debug): {direction} {symbol}")
            return
            
        # Wysłanie sygnału do Expert Advisor
        if self.zmq_client.send_trade_signal(direction, symbol, entry_price, stop_loss, take_profit):
            self.stats["signals_sent"] += 1
            self.stats["last_signal_time"] = datetime.now().isoformat()
            logger.info(f"Sygnał handlowy wysłany pomyślnie: {direction} {symbol}")
        else:
            logger.error(f"Błąd podczas wysyłania sygnału handlowego: {self.zmq_client.get_last_error()}")
    
    def _save_analysis_to_db(self, symbol: str, market_data: Dict[str, Any], 
                            analysis_result: Dict[str, Any], trade_idea: Dict[str, Any]):
        """
        Zapisanie wyników analizy w bazie danych.
        
        Args:
            symbol: Symbol instrumentu
            market_data: Dane rynkowe
            analysis_result: Wynik analizy
            trade_idea: Idea handlowa
        """
        try:
            # Przygotowanie danych do zapisu
            data = {
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "market_data": market_data,
                "analysis": analysis_result,
                "trade_idea": trade_idea
            }
            
            # Zapisanie w bazie danych
            self.db_handler.insert_one("analysis_history", data)
            logger.debug(f"Zapisano wyniki analizy dla {symbol} w bazie danych")
            
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania wyników analizy w bazie danych: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Pobranie statystyk działania agenta.
        
        Returns:
            Słownik ze statystykami
        """
        # Dodanie bieżącego czasu działania
        if self.stats["start_time"]:
            start_time = datetime.fromisoformat(self.stats["start_time"])
            uptime_seconds = (datetime.now() - start_time).total_seconds()
            self.stats["uptime"] = {
                "seconds": int(uptime_seconds),
                "minutes": int(uptime_seconds / 60),
                "hours": int(uptime_seconds / 3600)
            }
            
        return self.stats


if __name__ == "__main__":
    # Konfiguracja loggera
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Utworzenie i uruchomienie agenta
    agent = AgentConnector(debug_mode=True)
    
    try:
        agent.start()
    except KeyboardInterrupt:
        print("Przerwano przez użytkownika")
    finally:
        agent.stop() 
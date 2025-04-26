#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Klient ZeroMQ do komunikacji z Expert Advisor w MetaTrader 5.
Umożliwia wysyłanie sygnałów handlowych i odbieranie statusu EA.
"""

import zmq
import json
import time
import logging
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime

# Konfiguracja loggera
logger = logging.getLogger(__name__)

class ZmqClient:
    """
    Klasa klienta ZeroMQ do komunikacji z MT5 Expert Advisor.
    
    Wspiera komunikację w dwóch trybach:
    1. REQUEST/REPLY - do wysyłania poleceń i odbierania odpowiedzi
    2. PUBLISH/SUBSCRIBE - do rozsyłania sygnałów handlowych
    """
    
    def __init__(self, server_address: str = "localhost", req_port: int = 5555, pub_port: int = 5556):
        """
        Inicjalizacja klienta ZeroMQ.
        
        Args:
            server_address: Adres serwera ZeroMQ (domyślnie localhost)
            req_port: Port dla komunikacji REQUEST/REPLY
            pub_port: Port dla komunikacji PUBLISH/SUBSCRIBE
        """
        self.server_address = server_address
        self.req_port = req_port
        self.pub_port = pub_port
        
        self.context = zmq.Context()
        self.req_socket = None
        self.pub_socket = None
        
        self.is_connected = False
        self.last_error = None
        
        self._initialize_sockets()
    
    def _initialize_sockets(self):
        """Inicjalizacja socketów ZeroMQ."""
        try:
            # Inicjalizacja socketu REQUEST/REPLY
            self.req_socket = self.context.socket(zmq.REQ)
            # Ustawienie timeout na operacje
            self.req_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 sekund timeout na odbieranie
            self.req_socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 sekund timeout na wysyłanie
            
            # Inicjalizacja socketu PUBLISH
            self.pub_socket = self.context.socket(zmq.PUB)
            
            logger.info("Zainicjalizowano sockety ZeroMQ")
        except zmq.ZMQError as e:
            self.last_error = f"Błąd podczas inicjalizacji socketów ZeroMQ: {e}"
            logger.error(self.last_error)
            self._cleanup_sockets()
    
    def connect(self) -> bool:
        """
        Połączenie z serwerem ZeroMQ.
        
        Returns:
            True, jeśli połączenie zostało nawiązane pomyślnie, False w przeciwnym razie
        """
        if self.is_connected:
            return True
        
        try:
            # Połączenie socketów
            req_endpoint = f"tcp://{self.server_address}:{self.req_port}"
            pub_endpoint = f"tcp://{self.server_address}:{self.pub_port}"
            
            self.req_socket.connect(req_endpoint)
            self.pub_socket.bind(pub_endpoint)
            
            # Daj czas na ustanowienie połączenia
            time.sleep(0.5)
            
            # Sprawdź połączenie poprzez ping
            if self._ping():
                self.is_connected = True
                logger.info(f"Połączono z serwerem ZeroMQ na {req_endpoint} i {pub_endpoint}")
                return True
            else:
                self.last_error = "Nie otrzymano odpowiedzi ping od serwera ZeroMQ"
                logger.error(self.last_error)
                self._cleanup_sockets()
                return False
                
        except zmq.ZMQError as e:
            self.last_error = f"Błąd podczas łączenia z serwerem ZeroMQ: {e}"
            logger.error(self.last_error)
            self._cleanup_sockets()
            return False
    
    def _ping(self) -> bool:
        """
        Sprawdzenie połączenia poprzez wysłanie wiadomości ping.
        
        Returns:
            True, jeśli otrzymano odpowiedź, False w przeciwnym razie
        """
        ping_message = {"type": "ping", "timestamp": datetime.now().isoformat()}
        
        try:
            self.req_socket.send_json(ping_message)
            reply = self.req_socket.recv_json()
            
            if reply.get("type") == "pong":
                return True
                
        except zmq.ZMQError as e:
            self.last_error = f"Błąd podczas sprawdzania połączenia (ping): {e}"
            logger.error(self.last_error)
            
        return False
    
    def disconnect(self):
        """Zakończenie połączenia z serwerem ZeroMQ."""
        self._cleanup_sockets()
        self.is_connected = False
        logger.info("Rozłączono z serwerem ZeroMQ")
    
    def _cleanup_sockets(self):
        """Zamknięcie socketów i zwolnienie zasobów."""
        if self.req_socket:
            self.req_socket.close()
            self.req_socket = None
            
        if self.pub_socket:
            self.pub_socket.close()
            self.pub_socket = None
    
    def __del__(self):
        """Destruktor klasy - upewniamy się, że sockety są zamykane."""
        self._cleanup_sockets()
        if self.context:
            self.context.term()
    
    def send_trade_signal(self, action: str, symbol: str, entry_price: float = 0.0,
                         stop_loss: float = 0.0, take_profit: float = 0.0) -> bool:
        """
        Wysłanie sygnału handlowego do Expert Advisor.
        
        Args:
            action: Rodzaj akcji ('BUY', 'SELL', 'CLOSE')
            symbol: Symbol instrumentu (np. 'EURUSD')
            entry_price: Cena wejścia (0 = cena rynkowa)
            stop_loss: Poziom stop loss (0 = brak)
            take_profit: Poziom take profit (0 = brak)
            
        Returns:
            True, jeśli sygnał został wysłany pomyślnie, False w przeciwnym razie
        """
        if not self.is_connected:
            self.last_error = "Nie połączono z serwerem ZeroMQ"
            logger.error(self.last_error)
            return False
            
        # Walidacja parametrów
        if action not in ["BUY", "SELL", "CLOSE"]:
            self.last_error = f"Nieznana akcja: {action}. Dozwolone: BUY, SELL, CLOSE"
            logger.error(self.last_error)
            return False
            
        # Przygotowanie wiadomości
        signal = {
            "type": "trade_signal",
            "action": action,
            "symbol": symbol,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Wysłanie sygnału przez PUBLISH
            self.pub_socket.send_json(signal)
            logger.info(f"Wysłano sygnał {action} dla {symbol} przez kanał publikacji")
            
            # Dodatkowo możemy wysłać przez REQUEST/REPLY, aby otrzymać potwierdzenie
            self.req_socket.send_json(signal)
            reply = self.req_socket.recv_json()
            
            if reply.get("status") == "success":
                logger.info("Otrzymano potwierdzenie sygnału")
                return True
            else:
                self.last_error = f"Błąd podczas przetwarzania sygnału: {reply.get('error', 'Nieznany błąd')}"
                logger.error(self.last_error)
                return False
                
        except zmq.ZMQError as e:
            self.last_error = f"Błąd podczas wysyłania sygnału: {e}"
            logger.error(self.last_error)
            return False
    
    def get_status(self) -> Optional[Dict[str, Any]]:
        """
        Pobranie statusu Expert Advisor.
        
        Returns:
            Słownik zawierający informacje o statusie EA lub None w przypadku błędu
        """
        if not self.is_connected:
            self.last_error = "Nie połączono z serwerem ZeroMQ"
            logger.error(self.last_error)
            return None
            
        try:
            # Przygotowanie wiadomości
            request = {
                "type": "get_status",
                "timestamp": datetime.now().isoformat()
            }
            
            # Wysłanie zapytania
            self.req_socket.send_json(request)
            
            # Odebranie odpowiedzi
            reply = self.req_socket.recv_json()
            
            if reply.get("type") == "status":
                return reply
            else:
                self.last_error = f"Nieoczekiwany typ odpowiedzi: {reply.get('type')}"
                logger.error(self.last_error)
                return None
                
        except zmq.ZMQError as e:
            self.last_error = f"Błąd podczas pobierania statusu: {e}"
            logger.error(self.last_error)
            return None
    
    def get_last_error(self) -> Optional[str]:
        """
        Zwraca ostatni błąd, który wystąpił podczas komunikacji.
        
        Returns:
            Komunikat błędu lub None, jeśli nie było błędu
        """
        return self.last_error


if __name__ == "__main__":
    # Przykład użycia
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    client = ZmqClient()
    
    try:
        if client.connect():
            # Przykład wysłania sygnału handlowego
            client.send_trade_signal("BUY", "EURUSD", 1.1050, 1.1000, 1.1150)
            
            # Przykład pobrania statusu
            status = client.get_status()
            if status:
                print(f"Status EA: Symbol: {status.get('symbol')}, "
                      f"Bid: {status.get('bid')}, Ask: {status.get('ask')}, "
                      f"Balance: {status.get('balance')}, Equity: {status.get('equity')}")
            
            # Pętla nasłuchiwania
            print("Nasłuchiwanie na komunikaty (Ctrl+C aby zakończyć)...")
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("Przerwano przez użytkownika")
    finally:
        client.disconnect() 
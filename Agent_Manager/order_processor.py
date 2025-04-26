"""
Moduł przetwarzania zleceń handlowych dla systemu handlowego LLM.

Odpowiada za:
1. Przygotowanie zleceń handlowych do wykonania
2. Komunikację z Expert Advisor w MT5
3. Śledzenie statusu zleceń
4. Obsługę odpowiedzi z MT5
"""

import logging
import json
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from MT5_Connector.connector import MT5Connector
from Database.database import DatabaseHandler
from .risk_manager import RiskManager

logger = logging.getLogger(__name__)

class OrderProcessor:
    """
    Klasa do przetwarzania zleceń handlowych w systemie handlowym.
    """
    
    def __init__(
        self,
        mt5_connector: Optional[MT5Connector] = None,
        db_handler: Optional[DatabaseHandler] = None,
        risk_manager: Optional[RiskManager] = None
    ):
        """
        Inicjalizacja procesora zleceń.
        
        Args:
            mt5_connector: Konektor MT5
            db_handler: Handler bazy danych
            risk_manager: Menedżer ryzyka
        """
        self.mt5_connector = mt5_connector
        self.db_handler = db_handler if db_handler else DatabaseHandler()
        self.risk_manager = risk_manager
        self.magic_number = 123456  # Identyfikator zleceń dla EA
        
        logger.info("Inicjalizacja OrderProcessor")
    
    def set_mt5_connector(self, mt5_connector: MT5Connector) -> None:
        """
        Ustawienie konektora MT5.
        
        Args:
            mt5_connector: Instancja konektora MT5
        """
        self.mt5_connector = mt5_connector
    
    def set_risk_manager(self, risk_manager: RiskManager) -> None:
        """
        Ustawienie menedżera ryzyka.
        
        Args:
            risk_manager: Instancja menedżera ryzyka
        """
        self.risk_manager = risk_manager
    
    def process_trade_idea(
        self,
        trade_idea: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Przetwarzanie pomysłu handlowego i przygotowanie zlecenia.
        
        Args:
            trade_idea: Słownik z danymi pomysłu handlowego
            
        Returns:
            Dict[str, Any]: Wynik przetwarzania
        """
        # Sprawdź, czy mamy wszystkie niezbędne dane
        required_fields = ["symbol", "direction", "entry_price", "stop_loss", "take_profit"]
        for field in required_fields:
            if field not in trade_idea:
                logger.error(f"Brak wymaganego pola w pomyśle handlowym: {field}")
                return {
                    "success": False,
                    "error": f"Brak wymaganego pola: {field}",
                    "order": None
                }
        
        # Pobierz informacje z pomysłu handlowego
        symbol = trade_idea["symbol"]
        direction = trade_idea["direction"].lower()
        entry_price = float(trade_idea["entry_price"])
        stop_loss = float(trade_idea["stop_loss"])
        take_profit = float(trade_idea["take_profit"])
        
        # Opcjonalne pola
        trade_id = trade_idea.get("id")
        analysis_id = trade_idea.get("analysis_id")
        risk_reward = trade_idea.get("risk_reward", 0.0)
        volume = trade_idea.get("volume", None)
        
        # Jeśli nie mamy konektora MT5, nie możemy przetworzyć zlecenia
        if not self.mt5_connector:
            logger.error("MT5Connector nie został ustawiony. Nie można przetworzyć zlecenia.")
            return {
                "success": False,
                "error": "MT5Connector nie został ustawiony",
                "order": None
            }
        
        # Walidacja pomysłu handlowego przez menedżera ryzyka
        if self.risk_manager:
            validation_result = self.risk_manager.validate_trade_idea(
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            if not validation_result["valid"]:
                logger.warning(f"Pomysł handlowy nie przeszedł walidacji: {validation_result['reason']}")
                return {
                    "success": False,
                    "error": validation_result["reason"],
                    "order": None,
                    "validation": validation_result
                }
            
            # Jeśli nie określono wielkości pozycji, użyj sugestii menedżera ryzyka
            if volume is None:
                volume = validation_result["position_size"]
        else:
            # Jeśli nie ma menedżera ryzyka, użyj domyślnej minimalnej wielkości
            if volume is None:
                volume = 0.01
        
        # Przygotuj zlecenie handlowe
        order = {
            "action": "OPEN_POSITION",
            "symbol": symbol,
            "order_type": direction.upper(),
            "volume": volume,
            "price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "magic": self.magic_number,
            "comment": f"LLM_Trade_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "trade_id": trade_id,
            "analysis_id": analysis_id
        }
        
        # Zapisz pomysł handlowy do bazy danych jeśli nie ma już ID
        if not trade_id and self.db_handler:
            try:
                trade_idea_id = self.db_handler.insert_trade_idea(
                    analysis_id=analysis_id,
                    symbol=symbol,
                    direction=direction,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    risk_reward=risk_reward
                )
                order["trade_id"] = trade_idea_id
            except Exception as e:
                logger.error(f"Błąd podczas zapisywania pomysłu handlowego do bazy danych: {e}")
        
        return {
            "success": True,
            "order": order,
            "validation": validation_result if self.risk_manager else None
        }
    
    def send_order_to_mt5(
        self,
        order: Dict[str, Any],
        wait_for_response: bool = True,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Wysłanie zlecenia do MT5 przez Expert Advisor.
        
        Args:
            order: Słownik z danymi zlecenia
            wait_for_response: Czy czekać na odpowiedź
            timeout: Limit czasu oczekiwania w sekundach
            
        Returns:
            Dict[str, Any]: Odpowiedź z MT5
        """
        if not self.mt5_connector:
            logger.error("MT5Connector nie został ustawiony. Nie można wysłać zlecenia.")
            return {
                "success": False,
                "error": "MT5Connector nie został ustawiony"
            }
        
        try:
            # To jest uproszczona implementacja - zakładamy, że MT5Connector ma metodę send_command
            # W rzeczywistości należy zaimplementować komunikację z EA zgodnie z wybranym protokołem (np. ZeroMQ)
            response = self.mt5_connector.send_command(order)
            
            # Jeśli nie czekamy na odpowiedź, zwróć natychmiast
            if not wait_for_response:
                return {
                    "success": True,
                    "message": "Zlecenie zostało wysłane, ale nie czekamy na odpowiedź",
                    "order": order
                }
            
            # Czekaj na odpowiedź z limitem czasu
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Sprawdź, czy mamy odpowiedź
                if response and "status" in response:
                    # Jeśli operacja się powiodła
                    if response["status"] == "SUCCESS":
                        # Zapisz transakcję do bazy danych
                        if self.db_handler and "ticket" in response:
                            try:
                                trade_id = self.db_handler.insert_trade(
                                    trade_idea_id=order.get("trade_id"),
                                    symbol=order["symbol"],
                                    direction=order["order_type"].lower(),
                                    entry_price=response.get("open_price", order["price"]),
                                    entry_time=response.get("open_time", datetime.now().isoformat()),
                                    stop_loss=response.get("stop_loss", order["stop_loss"]),
                                    take_profit=response.get("take_profit", order["take_profit"]),
                                    volume=order["volume"],
                                    comment=order["comment"]
                                )
                                response["database_trade_id"] = trade_id
                            except Exception as e:
                                logger.error(f"Błąd podczas zapisywania transakcji do bazy danych: {e}")
                        
                        return {
                            "success": True,
                            "message": "Zlecenie zostało zrealizowane",
                            "response": response,
                            "order": order
                        }
                    else:
                        # Jeśli operacja się nie powiodła
                        return {
                            "success": False,
                            "error": response.get("message", "Nieznany błąd"),
                            "response": response,
                            "order": order
                        }
                
                # Krótkie opóźnienie przed kolejnym sprawdzeniem
                time.sleep(0.1)
            
            # Jeśli upłynął limit czasu
            return {
                "success": False,
                "error": "Upłynął limit czasu oczekiwania na odpowiedź",
                "order": order
            }
            
        except Exception as e:
            logger.error(f"Wystąpił błąd podczas wysyłania zlecenia: {e}")
            return {
                "success": False,
                "error": str(e),
                "order": order
            }
    
    def close_position(
        self,
        ticket: Union[int, str],
        reason: str = "Manual close",
        wait_for_response: bool = True,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Zamknięcie pozycji w MT5.
        
        Args:
            ticket: Numer ticketu pozycji
            reason: Powód zamknięcia
            wait_for_response: Czy czekać na odpowiedź
            timeout: Limit czasu oczekiwania w sekundach
            
        Returns:
            Dict[str, Any]: Odpowiedź z MT5
        """
        if not self.mt5_connector:
            logger.error("MT5Connector nie został ustawiony. Nie można zamknąć pozycji.")
            return {
                "success": False,
                "error": "MT5Connector nie został ustawiony"
            }
        
        # Przygotuj polecenie zamknięcia pozycji
        close_command = {
            "action": "CLOSE_POSITION",
            "ticket": ticket,
            "magic": self.magic_number,
            "comment": f"LLM_Close_{reason}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        try:
            # To jest uproszczona implementacja - zakładamy, że MT5Connector ma metodę send_command
            response = self.mt5_connector.send_command(close_command)
            
            # Jeśli nie czekamy na odpowiedź, zwróć natychmiast
            if not wait_for_response:
                return {
                    "success": True,
                    "message": "Zlecenie zamknięcia zostało wysłane, ale nie czekamy na odpowiedź",
                    "command": close_command
                }
            
            # Czekaj na odpowiedź z limitem czasu
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Sprawdź, czy mamy odpowiedź
                if response and "status" in response:
                    # Jeśli operacja się powiodła
                    if response["status"] == "SUCCESS":
                        # Aktualizuj status transakcji w bazie danych
                        if self.db_handler and "trade_id" in response:
                            try:
                                self.db_handler.update_trade(
                                    trade_id=response["trade_id"],
                                    exit_price=response.get("close_price", 0),
                                    exit_time=response.get("close_time", datetime.now().isoformat()),
                                    profit_loss=response.get("profit_loss", 0),
                                    status="closed"
                                )
                            except Exception as e:
                                logger.error(f"Błąd podczas aktualizacji transakcji w bazie danych: {e}")
                        
                        return {
                            "success": True,
                            "message": "Pozycja została zamknięta",
                            "response": response,
                            "command": close_command
                        }
                    else:
                        # Jeśli operacja się nie powiodła
                        return {
                            "success": False,
                            "error": response.get("message", "Nieznany błąd"),
                            "response": response,
                            "command": close_command
                        }
                
                # Krótkie opóźnienie przed kolejnym sprawdzeniem
                time.sleep(0.1)
            
            # Jeśli upłynął limit czasu
            return {
                "success": False,
                "error": "Upłynął limit czasu oczekiwania na odpowiedź",
                "command": close_command
            }
            
        except Exception as e:
            logger.error(f"Wystąpił błąd podczas zamykania pozycji: {e}")
            return {
                "success": False,
                "error": str(e),
                "command": close_command
            }
    
    def modify_position(
        self,
        ticket: Union[int, str],
        new_stop_loss: Optional[float] = None,
        new_take_profit: Optional[float] = None,
        wait_for_response: bool = True,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Modyfikacja pozycji w MT5.
        
        Args:
            ticket: Numer ticketu pozycji
            new_stop_loss: Nowy poziom stop-loss (None jeśli bez zmian)
            new_take_profit: Nowy poziom take-profit (None jeśli bez zmian)
            wait_for_response: Czy czekać na odpowiedź
            timeout: Limit czasu oczekiwania w sekundach
            
        Returns:
            Dict[str, Any]: Odpowiedź z MT5
        """
        if not self.mt5_connector:
            logger.error("MT5Connector nie został ustawiony. Nie można zmodyfikować pozycji.")
            return {
                "success": False,
                "error": "MT5Connector nie został ustawiony"
            }
        
        # Jeśli nic się nie zmienia, nie ma potrzeby wysyłać polecenia
        if new_stop_loss is None and new_take_profit is None:
            return {
                "success": False,
                "error": "Nie określono nowych wartości do modyfikacji"
            }
        
        # Przygotuj polecenie modyfikacji pozycji
        modify_command = {
            "action": "MODIFY_POSITION",
            "ticket": ticket,
            "magic": self.magic_number
        }
        
        if new_stop_loss is not None:
            modify_command["stop_loss"] = new_stop_loss
        
        if new_take_profit is not None:
            modify_command["take_profit"] = new_take_profit
        
        try:
            # To jest uproszczona implementacja - zakładamy, że MT5Connector ma metodę send_command
            response = self.mt5_connector.send_command(modify_command)
            
            # Jeśli nie czekamy na odpowiedź, zwróć natychmiast
            if not wait_for_response:
                return {
                    "success": True,
                    "message": "Zlecenie modyfikacji zostało wysłane, ale nie czekamy na odpowiedź",
                    "command": modify_command
                }
            
            # Czekaj na odpowiedź z limitem czasu
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Sprawdź, czy mamy odpowiedź
                if response and "status" in response:
                    # Jeśli operacja się powiodła
                    if response["status"] == "SUCCESS":
                        # Możemy tutaj zaktualizować bazę danych, jeśli potrzeba
                        return {
                            "success": True,
                            "message": "Pozycja została zmodyfikowana",
                            "response": response,
                            "command": modify_command
                        }
                    else:
                        # Jeśli operacja się nie powiodła
                        return {
                            "success": False,
                            "error": response.get("message", "Nieznany błąd"),
                            "response": response,
                            "command": modify_command
                        }
                
                # Krótkie opóźnienie przed kolejnym sprawdzeniem
                time.sleep(0.1)
            
            # Jeśli upłynął limit czasu
            return {
                "success": False,
                "error": "Upłynął limit czasu oczekiwania na odpowiedź",
                "command": modify_command
            }
            
        except Exception as e:
            logger.error(f"Wystąpił błąd podczas modyfikacji pozycji: {e}")
            return {
                "success": False,
                "error": str(e),
                "command": modify_command
            }
    
    def process_extended_trade_idea(
        self,
        trade_idea_id: int
    ) -> Dict[str, Any]:
        """
        Przetwarzanie pomysłu handlowego z rozszerzonej tabeli trade_ideas_extended i przygotowanie zlecenia.
        
        Args:
            trade_idea_id: ID pomysłu handlowego z tabeli trade_ideas_extended
            
        Returns:
            Dict[str, Any]: Wynik przetwarzania
        """
        # Sprawdź czy mamy handler bazy danych
        if not self.db_handler:
            logger.error("DatabaseHandler nie został ustawiony. Nie można przetworzyć pomysłu handlowego.")
            return {
                "success": False,
                "error": "DatabaseHandler nie został ustawiony",
                "order": None
            }
        
        # Pobierz pomysł handlowy z bazy danych
        trade_idea = self.db_handler.get_trade_idea(trade_idea_id)
        if not trade_idea:
            logger.error(f"Nie znaleziono pomysłu handlowego o ID: {trade_idea_id}")
            return {
                "success": False,
                "error": f"Nie znaleziono pomysłu handlowego o ID: {trade_idea_id}",
                "order": None
            }
        
        # Sprawdź, czy pomysł może być przetworzony (status PENDING)
        if trade_idea.get("status") != "PENDING":
            logger.warning(f"Pomysł handlowy o ID {trade_idea_id} nie może być przetworzony. Status: {trade_idea.get('status')}")
            return {
                "success": False,
                "error": f"Pomysł handlowy o ID {trade_idea_id} nie może być przetworzony. Status: {trade_idea.get('status')}",
                "order": None
            }
        
        # Jeśli pomysł zawiera wartość risk_percentage, użyj jej do wyliczenia wielkości pozycji
        position_size = None
        risk_validation = None
        
        if (self.risk_manager and 
            "risk_percentage" in trade_idea and 
            trade_idea["risk_percentage"] is not None):
            
            try:
                # Pobierz informacje o rynku z MT5
                if not self.mt5_connector:
                    logger.error("MT5Connector nie został ustawiony. Nie można obliczyć wielkości pozycji.")
                    return {
                        "success": False,
                        "error": "MT5Connector nie został ustawiony",
                        "order": None
                    }
                
                symbol_info = self.mt5_connector.get_symbol_info(trade_idea["symbol"])
                
                if not symbol_info or "point" not in symbol_info:
                    logger.error(f"Nie można pobrać informacji o symbolu {trade_idea['symbol']}")
                    return {
                        "success": False,
                        "error": f"Nie można pobrać informacji o symbolu {trade_idea['symbol']}",
                        "order": None
                    }
                
                # Oblicz wielkość pozycji na podstawie ryzyka
                position_size = self.risk_manager.calculate_position_size(
                    symbol=trade_idea["symbol"],
                    direction=trade_idea["direction"],
                    entry_price=float(trade_idea["entry_price"]),
                    stop_loss=float(trade_idea["stop_loss"]),
                    risk_percent=float(trade_idea["risk_percentage"]),
                    symbol_info=symbol_info
                )
                
                # Waliduj pomysł handlowy
                risk_validation = self.risk_manager.validate_trade_idea(
                    symbol=trade_idea["symbol"],
                    direction=trade_idea["direction"],
                    entry_price=float(trade_idea["entry_price"]),
                    stop_loss=float(trade_idea["stop_loss"]),
                    take_profit=float(trade_idea["take_profit"])
                )
                
                if not risk_validation["valid"]:
                    # Aktualizuj status pomysłu handlowego
                    self.update_trade_idea_status(
                        trade_idea_id=trade_idea_id,
                        status="REJECTED",
                        rejection_reason=risk_validation["reason"]
                    )
                    
                    logger.warning(f"Pomysł handlowy o ID {trade_idea_id} nie przeszedł walidacji: {risk_validation['reason']}")
                    return {
                        "success": False,
                        "error": risk_validation["reason"],
                        "order": None,
                        "validation": risk_validation
                    }
                
            except Exception as e:
                logger.error(f"Wystąpił błąd podczas przetwarzania pomysłu handlowego: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "order": None
                }
        
        # Przygotuj zlecenie handlowe
        order = {
            "action": "OPEN_POSITION",
            "symbol": trade_idea["symbol"],
            "order_type": trade_idea["direction"].upper(),
            "volume": position_size if position_size else 0.01,  # Domyślna minimalna wielkość
            "price": float(trade_idea["entry_price"]),
            "stop_loss": float(trade_idea["stop_loss"]),
            "take_profit": float(trade_idea["take_profit"]),
            "magic": self.magic_number,
            "comment": f"LLM_TradeIdea_{trade_idea_id}",
            "trade_idea_id": trade_idea_id
        }
        
        return {
            "success": True,
            "order": order,
            "validation": risk_validation
        }
    
    def execute_trade_idea(
        self,
        trade_idea_id: int,
        wait_for_response: bool = True,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Wykonanie pomysłu handlowego - przetworzenie i wysłanie zlecenia do MT5.
        
        Args:
            trade_idea_id: ID pomysłu handlowego
            wait_for_response: Czy czekać na odpowiedź z MT5
            timeout: Limit czasu oczekiwania w sekundach
            
        Returns:
            Dict[str, Any]: Wynik wykonania
        """
        # Przetwarzanie pomysłu handlowego
        process_result = self.process_extended_trade_idea(trade_idea_id)
        
        if not process_result["success"]:
            return process_result
        
        # Wysłanie zlecenia do MT5
        order = process_result["order"]
        result = self.send_order_to_mt5(order, wait_for_response, timeout)
        
        # Aktualizacja statusu pomysłu handlowego
        if result["success"]:
            # Pobierz ticket z odpowiedzi
            ticket = None
            if "response" in result and "ticket" in result["response"]:
                ticket = result["response"]["ticket"]
            
            # Aktualizuj status pomysłu handlowego
            self.update_trade_idea_status(
                trade_idea_id=trade_idea_id,
                status="EXECUTED",
                ticket=ticket
            )
        else:
            # Jeśli wystąpił błąd, zaktualizuj status z powodem odrzucenia
            self.update_trade_idea_status(
                trade_idea_id=trade_idea_id,
                status="REJECTED",
                rejection_reason=result.get("error", "Nieznany błąd podczas wysyłania zlecenia do MT5")
            )
        
        return {
            "success": result["success"],
            "message": result.get("message", result.get("error", "")),
            "response": result.get("response"),
            "order": order,
            "trade_idea_id": trade_idea_id
        }
    
    def update_trade_idea_status(
        self,
        trade_idea_id: int,
        status: str,
        rejection_reason: str = None,
        ticket: Union[int, str] = None
    ) -> bool:
        """
        Aktualizacja statusu pomysłu handlowego.
        
        Args:
            trade_idea_id: ID pomysłu handlowego
            status: Nowy status (PENDING, EXECUTED, REJECTED, EXPIRED)
            rejection_reason: Powód odrzucenia (jeśli status to REJECTED)
            ticket: Numer ticketu transakcji (jeśli status to EXECUTED)
            
        Returns:
            bool: True jeśli aktualizacja powiodła się, False w przeciwnym razie
        """
        if not self.db_handler:
            logger.error("DatabaseHandler nie został ustawiony. Nie można zaktualizować statusu pomysłu handlowego.")
            return False
        
        update_data = {
            "status": status,
            "updated_at": datetime.now().isoformat()
        }
        
        if status == "EXECUTED":
            update_data["executed_at"] = datetime.now().isoformat()
            if ticket:
                # Tutaj możemy dodać referencję do ticketu w danych pomysłu handlowego
                # np. jako dodatkowe pole w tabeli trade_ideas_extended
                update_data["ticket"] = ticket
        
        if status == "REJECTED" and rejection_reason:
            update_data["rejection_reason"] = rejection_reason
        
        # Aktualizuj pomysł handlowy w bazie danych
        return self.db_handler.update_trade_idea(trade_idea_id, update_data)
    
    def expire_old_trade_ideas(self) -> int:
        """
        Oznaczenie przeterminowanych pomysłów handlowych jako EXPIRED.
        
        Returns:
            int: Liczba zaktualizowanych pomysłów handlowych
        """
        if not self.db_handler:
            logger.error("DatabaseHandler nie został ustawiony. Nie można zaktualizować przeterminowanych pomysłów handlowych.")
            return 0
        
        try:
            # Pobierz aktualną datę i czas
            current_time = datetime.now().isoformat()
            
            # Znajdź wszystkie pomysły handlowe, które są PENDING i mają valid_until starsze niż obecna data
            if not self.connect():
                return 0
            
            self.db_handler.cursor.execute("""
                SELECT id FROM trade_ideas_extended 
                WHERE status = 'PENDING' 
                AND valid_until IS NOT NULL 
                AND valid_until < ?
            """, (current_time,))
            
            expired_ids = [row["id"] for row in self.db_handler.cursor.fetchall()]
            
            # Aktualizuj status na EXPIRED dla znalezionych pomysłów
            count = 0
            for idea_id in expired_ids:
                updated = self.update_trade_idea_status(
                    trade_idea_id=idea_id,
                    status="EXPIRED",
                    rejection_reason="Pomysł handlowy przekroczył datę ważności"
                )
                if updated:
                    count += 1
            
            logger.info(f"Zaktualizowano {count} przeterminowanych pomysłów handlowych na status EXPIRED")
            return count
            
        except Exception as e:
            logger.error(f"Wystąpił błąd podczas aktualizacji przeterminowanych pomysłów handlowych: {e}")
            return 0
        finally:
            if hasattr(self.db_handler, 'disconnect'):
                self.db_handler.disconnect() 
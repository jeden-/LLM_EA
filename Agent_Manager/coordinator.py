"""
Moduł koordynatora agenta dla systemu handlowego LLM.

Odpowiada za:
1. Integrację wszystkich komponentów systemu (MT5_Connector, LLM_Engine, Database)
2. Koordynację przepływu danych między komponentami
3. Zarządzanie cyklem pracy systemu
4. Monitorowanie stanu systemu
"""

import os
import time
import json
import logging
import threading
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta

from MT5_Connector.connector import MT5Connector
from LLM_Engine.llm_engine import LLMEngine
from Database.database import DatabaseHandler
from .risk_manager import RiskManager
from .order_processor import OrderProcessor

logger = logging.getLogger(__name__)

class AgentCoordinator:
    """
    Główna klasa koordynatora agenta, integrująca wszystkie komponenty systemu handlowego LLM.
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        mt5_connector: Optional[MT5Connector] = None,
        llm_engine: Optional[LLMEngine] = None,
        db_handler: Optional[DatabaseHandler] = None
    ):
        """
        Inicjalizacja koordynatora agenta.
        
        Args:
            config_path: Ścieżka do pliku konfiguracyjnego
            mt5_connector: Instancja konektora MT5
            llm_engine: Instancja silnika LLM
            db_handler: Instancja handlera bazy danych
        """
        # Podstawowa konfiguracja
        self.config = self._load_config(config_path)
        self.last_analysis_time = {}
        self.running = False
        self.symbols = self.config.get("symbols", ["EURUSD", "GBPUSD", "USDJPY"])
        self.timeframes = self.config.get("timeframes", [1, 5, 15, 30, 60, 240, 1440])
        self.analysis_interval = self.config.get("analysis_interval_seconds", 300)
        self.monitoring_thread = None
        
        # Inicjalizacja komponentów
        self.db_handler = db_handler if db_handler else DatabaseHandler()
        self.mt5_connector = mt5_connector if mt5_connector else MT5Connector()
        self.llm_engine = llm_engine if llm_engine else LLMEngine(config_file=config_path)
        
        # Inicjalizacja dodatkowych komponentów
        self.risk_manager = RiskManager(db_handler=self.db_handler)
        self.order_processor = OrderProcessor(
            db_handler=self.db_handler,
            risk_manager=self.risk_manager
        )
        
        # Powiązanie komponentów
        self.risk_manager.set_mt5_connector(self.mt5_connector)
        self.order_processor.set_mt5_connector(self.mt5_connector)
        self.order_processor.set_risk_manager(self.risk_manager)
        
        logger.info(f"Inicjalizacja AgentCoordinator z {len(self.symbols)} symbolami i {len(self.timeframes)} timeframe'ami")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        Ładowanie konfiguracji z pliku.
        
        Args:
            config_path: Ścieżka do pliku konfiguracyjnego
            
        Returns:
            Dict[str, Any]: Załadowana konfiguracja
        """
        default_config = {
            "symbols": ["EURUSD", "GBPUSD", "USDJPY"],
            "timeframes": [1, 5, 15, 30, 60, 240, 1440],
            "analysis_interval_seconds": 300,
            "max_risk_per_trade_pct": 2.0,
            "daily_risk_limit_pct": 5.0,
            "magic_number": 123456,
            "enable_auto_trading": False,
            "log_level": "INFO"
        }
        
        if not config_path or not os.path.exists(config_path):
            logger.warning(f"Plik konfiguracyjny nie istnieje: {config_path}. Używanie konfiguracji domyślnej.")
            return default_config
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            # Połącz z domyślną konfiguracją, aby zapewnić wszystkie niezbędne pola
            merged_config = {**default_config, **config}
            return merged_config
        
        except Exception as e:
            logger.error(f"Błąd podczas ładowania konfiguracji: {e}")
            return default_config
    
    def initialize(self) -> bool:
        """
        Inicjalizacja i połączenie wszystkich komponentów.
        
        Returns:
            bool: True jeśli inicjalizacja się powiodła, False w przeciwnym przypadku
        """
        logger.info("Inicjalizacja komponentów systemu...")
        
        # Inicjalizacja bazy danych
        if not self.db_handler.init_database():
            logger.error("Nie można zainicjalizować bazy danych")
            return False
        
        # Inicjalizacja konektora MT5
        if not self.mt5_connector.initialize():
            logger.error("Nie można zainicjalizować konektora MT5")
            return False
        
        # Sprawdzenie połączenia z MT5
        account_info = self.mt5_connector.get_account_info()
        if not account_info:
            logger.error("Nie można pobrać informacji o koncie z MT5")
            return False
        
        logger.info(f"Połączono z kontem MT5: {account_info.get('login')} (Balance: {account_info.get('balance')})")
        
        # Logowanie informacji o inicjalizacji
        if self.db_handler:
            self.db_handler.insert_log(
                level="INFO",
                module="AgentCoordinator",
                message=f"System zainicjalizowany. Konto: {account_info.get('login')}, Saldo: {account_info.get('balance')}"
            )
        
        return True
    
    def shutdown(self) -> None:
        """Wyłączenie wszystkich komponentów systemu."""
        logger.info("Wyłączanie systemu...")
        
        # Zatrzymaj wątek monitorowania
        self.stop_monitoring()
        
        # Zamknij konektor MT5
        if self.mt5_connector:
            self.mt5_connector.shutdown()
        
        # Zapisz log o zamknięciu
        if self.db_handler:
            self.db_handler.insert_log(
                level="INFO",
                module="AgentCoordinator",
                message="System został wyłączony"
            )
        
        logger.info("System został wyłączony")
    
    def analyze_market(
        self,
        symbol: str,
        timeframe: int,
        force: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Przeprowadzenie analizy rynku dla danego symbolu i timeframe'u.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Timeframe analizy
            force: Czy wymusić analizę (ignorując ostatni czas analizy)
            
        Returns:
            Optional[Dict[str, Any]]: Wynik analizy lub None w przypadku błędu
        """
        # Sprawdź, czy minęło wystarczająco dużo czasu od ostatniej analizy
        key = f"{symbol}_{timeframe}"
        if not force and key in self.last_analysis_time:
            last_time = self.last_analysis_time[key]
            elapsed_seconds = (datetime.now() - last_time).total_seconds()
            
            # Jeśli nie minął jeszcze interwał analizy, pomiń
            if elapsed_seconds < self.analysis_interval:
                logger.debug(f"Pomijanie analizy {symbol} {timeframe} - minęło tylko {elapsed_seconds}s od ostatniej analizy")
                return None
        
        logger.info(f"Rozpoczynanie analizy rynku dla {symbol} ({timeframe})")
        
        try:
            # Pobierz dane rynkowe z MT5
            candles_df = self.mt5_connector.get_candles(
                symbol=symbol,
                timeframe=timeframe,
                count=100,  # Liczba świec do analizy
                include_current=True,
                add_indicators=True,
                add_patterns=True
            )
            
            if candles_df.empty:
                logger.error(f"Nie można pobrać danych dla {symbol} ({timeframe})")
                return None
            
            # Konwersja DataFrame do listy słowników (format wymagany przez LLMEngine)
            price_data = candles_df.to_dict('records')
            
            # Przygotowanie wskaźników technicznych
            indicators = {
                "sma_50": candles_df['sma_50'].iloc[-1] if 'sma_50' in candles_df.columns else None,
                "ema_20": candles_df['ema_20'].iloc[-1] if 'ema_20' in candles_df.columns else None,
                "atr": candles_df['atr'].iloc[-1] if 'atr' in candles_df.columns else None,
                "vwap": candles_df['vwap'].iloc[-1] if 'vwap' in candles_df.columns else None,
                "rsi": candles_df['rsi'].iloc[-1] if 'rsi' in candles_df.columns else None,
                "macd": candles_df['macd'].iloc[-1] if 'macd' in candles_df.columns else None,
                "macd_signal": candles_df['macd_signal'].iloc[-1] if 'macd_signal' in candles_df.columns else None,
                "bollinger_upper": candles_df['bollinger_upper'].iloc[-1] if 'bollinger_upper' in candles_df.columns else None,
                "bollinger_middle": candles_df['bollinger_middle'].iloc[-1] if 'bollinger_middle' in candles_df.columns else None,
                "bollinger_lower": candles_df['bollinger_lower'].iloc[-1] if 'bollinger_lower' in candles_df.columns else None
            }
            
            # Przeprowadź analizę przez LLM
            analysis_result = self.llm_engine.analyze_market(
                symbol=symbol,
                timeframe=str(timeframe),
                price_data=price_data,
                indicators=indicators,
                strategy_name="Master",  # Używamy strategii Master z dokumentacji
                risk_level=self.config.get("risk_level", "medium")
            )
            
            # Zapisz czas ostatniej analizy
            self.last_analysis_time[key] = datetime.now()
            
            # Zapisz analizę do bazy danych
            if self.db_handler and analysis_result:
                analysis_id = self.db_handler.insert_market_analysis(
                    symbol=symbol,
                    timeframe=str(timeframe),
                    analysis_data=analysis_result
                )
                
                # Jeśli analiza zawiera pomysł handlowy, zapisz go
                if "trade_idea" in analysis_result and analysis_result["trade_idea"]["action"] == "ENTER":
                    trade_idea = analysis_result["trade_idea"]
                    
                    # Pobierz szczegóły pomysłu handlowego
                    direction = trade_idea.get("direction", "").lower()
                    entry_price = float(trade_idea.get("entry_price", 0))
                    stop_loss = float(trade_idea.get("stop_loss", 0))
                    take_profit = float(trade_idea.get("take_profit", 0))
                    
                    # Oblicz stosunek zysku do ryzyka
                    if stop_loss > 0 and take_profit > 0 and entry_price > 0:
                        if direction == "buy":
                            risk = entry_price - stop_loss
                            reward = take_profit - entry_price
                        else:  # sell
                            risk = stop_loss - entry_price
                            reward = entry_price - take_profit
                            
                        risk_reward = reward / risk if risk > 0 else 0
                    else:
                        risk_reward = 0
                    
                    # Zapisz pomysł handlowy do bazy danych
                    trade_idea_id = self.db_handler.insert_trade_idea(
                        analysis_id=analysis_id,
                        symbol=symbol,
                        direction=direction,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        risk_reward=risk_reward
                    )
                    
                    # Dodaj ID do wyników
                    analysis_result["trade_idea"]["id"] = trade_idea_id
            
            logger.info(f"Analiza rynku dla {symbol} ({timeframe}) zakończona pomyślnie")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Błąd podczas analizy rynku dla {symbol} ({timeframe}): {e}")
            
            # Zapisz błąd do bazy danych
            if self.db_handler:
                self.db_handler.insert_log(
                    level="ERROR",
                    module="AgentCoordinator",
                    message=f"Błąd analizy {symbol} ({timeframe}): {str(e)}"
                )
            
            return None
    
    def process_analysis_result(
        self,
        analysis_result: Dict[str, Any],
        auto_trade: bool = False
    ) -> Dict[str, Any]:
        """
        Przetwarzanie wyników analizy i ewentualne wykonanie transakcji.
        
        Args:
            analysis_result: Wynik analizy rynku
            auto_trade: Czy automatycznie realizować transakcje
            
        Returns:
            Dict[str, Any]: Wynik przetwarzania
        """
        if not analysis_result:
            return {"success": False, "error": "Brak wyników analizy"}
        
        # Sprawdź, czy analiza zawiera pomysł handlowy
        if "trade_idea" not in analysis_result:
            return {
                "success": True,
                "message": "Analiza nie zawiera pomysłu handlowego",
                "action": "NONE"
            }
        
        trade_idea = analysis_result["trade_idea"]
        
        # Sprawdź akcję
        action = trade_idea.get("action", "").upper()
        
        if action == "WAIT":
            return {
                "success": True,
                "message": "Analiza sugeruje czekanie",
                "action": "WAIT",
                "reason": trade_idea.get("reason", "Brak warunków do wejścia")
            }
        
        if action == "ENTER":
            # Przetwórz pomysł handlowy przez OrderProcessor
            processing_result = self.order_processor.process_trade_idea(trade_idea)
            
            # Jeśli przetwarzanie się nie powiodło
            if not processing_result["success"]:
                return {
                    "success": False,
                    "error": processing_result["error"],
                    "action": "ENTER_FAILED"
                }
            
            # Jeśli nie chcemy automatycznie handlować, zwróć wynik
            if not auto_trade:
                return {
                    "success": True,
                    "message": "Przygotowano zlecenie handlowe, ale auto_trade=False",
                    "action": "ENTER_PREPARED",
                    "order": processing_result["order"]
                }
            
            # Sprawdź limit dziennego ryzyka przed wykonaniem transakcji
            risk_check = self.risk_manager.check_daily_risk_limit(
                daily_risk_limit_pct=self.config.get("daily_risk_limit_pct", 5.0)
            )
            
            if risk_check["limit_exceeded"]:
                logger.warning(f"Przekroczony dzienny limit ryzyka: {risk_check['current_risk']:.2f}%")
                return {
                    "success": False,
                    "error": "Przekroczony dzienny limit ryzyka",
                    "action": "RISK_LIMIT_EXCEEDED",
                    "risk_check": risk_check
                }
            
            # Wyślij zlecenie do MT5
            order_result = self.order_processor.send_order_to_mt5(
                order=processing_result["order"],
                wait_for_response=True,
                timeout=30
            )
            
            return {
                "success": order_result["success"],
                "message": order_result.get("message", order_result.get("error", "")),
                "action": "ENTER_EXECUTED" if order_result["success"] else "ENTER_FAILED",
                "order_result": order_result
            }
        
        if action == "EXIT":
            # Jeśli mamy identyfikator pozycji, zamknij ją
            ticket = trade_idea.get("ticket")
            
            if not ticket:
                return {
                    "success": False,
                    "error": "Brak identyfikatora pozycji do zamknięcia",
                    "action": "EXIT_FAILED"
                }
            
            # Jeśli nie chcemy automatycznie handlować, zwróć wynik
            if not auto_trade:
                return {
                    "success": True,
                    "message": "Przygotowano zlecenie zamknięcia, ale auto_trade=False",
                    "action": "EXIT_PREPARED",
                    "ticket": ticket
                }
            
            # Zamknij pozycję
            close_result = self.order_processor.close_position(
                ticket=ticket,
                reason=trade_idea.get("reason", "Analysis"),
                wait_for_response=True,
                timeout=30
            )
            
            return {
                "success": close_result["success"],
                "message": close_result.get("message", close_result.get("error", "")),
                "action": "EXIT_EXECUTED" if close_result["success"] else "EXIT_FAILED",
                "close_result": close_result
            }
        
        # Jeśli akcja nie jest rozpoznawalna
        return {
            "success": False,
            "error": f"Nierozpoznana akcja: {action}",
            "action": "UNKNOWN"
        }
    
    def generate_trade_idea(
        self,
        symbol: str,
        timeframe: str,
        force_analysis: bool = False
    ) -> Dict[str, Any]:
        """
        Generuje pomysł handlowy na podstawie analizy rynku.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Timeframe analizy (jako string, np. 'H1', 'D1')
            force_analysis: Czy wymusić nową analizę
            
        Returns:
            Dict[str, Any]: Wygenerowany pomysł handlowy lub informacja o błędzie
        """
        logger.info(f"Generowanie pomysłu handlowego dla {symbol} ({timeframe})")
        
        # Konwersja timeframe ze stringa na int
        tf_map = {'M1': 1, 'M5': 5, 'M15': 15, 'M30': 30, 'H1': 60, 'H4': 240, 'D1': 1440}
        tf_int = tf_map.get(timeframe, 60)  # Domyślnie H1
        
        # Przeprowadź analizę rynku
        analysis = self.analyze_market(symbol, tf_int, force=force_analysis)
        
        if not analysis:
            logger.error(f"Nie udało się przeprowadzić analizy rynku dla {symbol} ({timeframe})")
            return {
                "success": False,
                "error": "Błąd analizy rynku",
                "symbol": symbol,
                "timeframe": timeframe
            }
        
        # Zapisz analizę w bazie danych
        analysis_id = None
        try:
            if self.db_handler:
                analysis_id = self.db_handler.insert_market_analysis(
                    symbol=symbol,
                    timeframe=timeframe,
                    analysis_data=analysis
                )
                logger.info(f"Zapisano analizę rynku w bazie danych (ID: {analysis_id})")
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania analizy: {e}")
        
        # Przygotuj pomysł handlowy
        trade_idea = {
            "symbol": symbol,
            "direction": analysis.get("direction", "NEUTRAL"),
            "entry_price": analysis.get("entry_price", 0.0),
            "stop_loss": analysis.get("stop_loss", 0.0),
            "take_profit": analysis.get("take_profit", 0.0),
            "confidence": analysis.get("confidence", 0.0),
            "analysis_id": analysis_id,
            "justification": analysis.get("justification", ""),
            "timeframe": timeframe
        }
        
        # Oblicz stosunek zysku do ryzyka
        if trade_idea["entry_price"] > 0 and trade_idea["stop_loss"] > 0 and trade_idea["take_profit"] > 0:
            if trade_idea["direction"] == "BUY":
                risk = trade_idea["entry_price"] - trade_idea["stop_loss"]
                reward = trade_idea["take_profit"] - trade_idea["entry_price"]
            else:  # SELL
                risk = trade_idea["stop_loss"] - trade_idea["entry_price"]
                reward = trade_idea["entry_price"] - trade_idea["take_profit"]
                
            trade_idea["risk_reward"] = round(reward / risk, 2) if risk > 0 else 0
        else:
            trade_idea["risk_reward"] = 0
        
        # Zapisz pomysł handlowy w bazie danych
        idea_id = None
        try:
            if self.db_handler and analysis_id:
                idea_id = self.db_handler.insert_trade_idea(
                    analysis_id=analysis_id,
                    symbol=trade_idea["symbol"],
                    direction=trade_idea["direction"],
                    entry_price=trade_idea["entry_price"],
                    stop_loss=trade_idea["stop_loss"],
                    take_profit=trade_idea["take_profit"],
                    risk_reward=trade_idea["risk_reward"]
                )
                trade_idea["id"] = idea_id
                logger.info(f"Zapisano pomysł handlowy w bazie danych (ID: {idea_id})")
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania pomysłu handlowego: {e}")
        
        return {
            "success": True,
            "id": idea_id,
            "symbol": trade_idea["symbol"],
            "direction": trade_idea["direction"],
            "entry_price": trade_idea["entry_price"],
            "stop_loss": trade_idea["stop_loss"],
            "take_profit": trade_idea["take_profit"],
            "risk_reward": trade_idea["risk_reward"],
            "analysis_id": analysis_id
        }
    
    def run_market_analysis(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[int] = None,
        auto_trade: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Przeprowadzenie analizy rynku dla określonych symboli i timeframe'ów.
        
        Args:
            symbol: Symbol do analizy (jeśli None, analizuje wszystkie skonfigurowane symbole)
            timeframe: Timeframe do analizy (jeśli None, analizuje wszystkie skonfigurowane timeframe'y)
            auto_trade: Czy automatycznie realizować transakcje na podstawie analizy
            
        Returns:
            List[Dict[str, Any]]: Lista wyników analizy i przetwarzania
        """
        results = []
        
        # Określ symbole do analizy
        symbols_to_analyze = [symbol] if symbol else self.symbols
        
        # Określ timeframe'y do analizy
        timeframes_to_analyze = [timeframe] if timeframe else self.timeframes
        
        # Dla każdej kombinacji symbolu i timeframe'u przeprowadź analizę
        for sym in symbols_to_analyze:
            for tf in timeframes_to_analyze:
                # Przeprowadź analizę rynku
                analysis_result = self.analyze_market(symbol=sym, timeframe=tf)
                
                # Jeśli analiza się powiodła, przetwórz wynik
                if analysis_result:
                    processing_result = self.process_analysis_result(
                        analysis_result=analysis_result,
                        auto_trade=auto_trade
                    )
                    
                    # Dodaj wynik do listy
                    results.append({
                        "symbol": sym,
                        "timeframe": tf,
                        "analysis": analysis_result,
                        "processing": processing_result
                    })
        
        return results
    
    def start_monitoring(self, auto_trade: bool = False) -> bool:
        """
        Uruchomienie wątku monitorowania rynku w tle.
        
        Args:
            auto_trade: Czy automatycznie realizować transakcje na podstawie analizy
            
        Returns:
            bool: True jeśli monitorowanie zostało uruchomione, False w przeciwnym przypadku
        """
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            logger.warning("Monitorowanie już jest uruchomione")
            return False
        
        self.running = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(auto_trade,),
            daemon=True
        )
        self.monitoring_thread.start()
        
        logger.info(f"Rozpoczęto monitorowanie rynku (auto_trade={auto_trade})")
        return True
    
    def stop_monitoring(self) -> bool:
        """
        Zatrzymanie wątku monitorowania rynku.
        
        Returns:
            bool: True jeśli monitorowanie zostało zatrzymane, False w przeciwnym przypadku
        """
        if not self.monitoring_thread or not self.monitoring_thread.is_alive():
            logger.warning("Monitorowanie nie jest uruchomione")
            return False
        
        self.running = False
        self.monitoring_thread.join(timeout=5)
        
        if self.monitoring_thread.is_alive():
            logger.warning("Nie udało się zatrzymać wątku monitorowania w ciągu 5 sekund")
            return False
        
        logger.info("Zatrzymano monitorowanie rynku")
        return True
    
    def _monitoring_loop(self, auto_trade: bool = False) -> None:
        """
        Główna pętla monitorowania rynku.
        
        Args:
            auto_trade: Czy automatycznie realizować transakcje na podstawie analizy
        """
        logger.info(f"Uruchomiono pętlę monitorowania (auto_trade={auto_trade})")
        
        while self.running:
            try:
                # Przeprowadź analizę rynku dla wszystkich symboli i timeframe'ów
                self.run_market_analysis(auto_trade=auto_trade)
                
                # Sprawdź otwarte pozycje i zarządzaj nimi
                self._manage_open_positions()
                
                # Pauza przed kolejną iteracją
                for _ in range(60):  # Sprawdzaj co sekundę, czy running jest nadal True
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Błąd w pętli monitorowania: {e}")
                
                # Zapisz błąd do bazy danych
                if self.db_handler:
                    self.db_handler.insert_log(
                        level="ERROR",
                        module="AgentCoordinator",
                        message=f"Błąd w pętli monitorowania: {str(e)}"
                    )
                
                # Poczekaj przed ponowną próbą
                time.sleep(10)
        
        logger.info("Zakończono pętlę monitorowania")
    
    def _manage_open_positions(self) -> None:
        """Zarządzanie otwartymi pozycjami."""
        if not self.mt5_connector:
            logger.error("Brak połączenia z MT5. Nie można zarządzać pozycjami.")
            return
        
        try:
            # Pobierz otwarte pozycje
            positions = self.mt5_connector.get_open_positions()
            
            for pos in positions:
                # Logika do zarządzania pozycjami
                position_ticket = pos.get('ticket')
                symbol = pos.get('symbol')
                current_profit = pos.get('profit', 0)
                
                logger.debug(f"Zarządzanie pozycją {position_ticket} ({symbol}): zysk {current_profit}")
                
                # Tu można dodać logikę do dostosowywania SL/TP, częściowego zamykania, itd.
        
        except Exception as e:
            logger.error(f"Błąd podczas zarządzania pozycjami: {e}")
    
    def execute_trade_idea(self, trade_idea_id: int) -> Dict[str, Any]:
        """
        Wykonuje pomysł handlowy poprzez wysłanie zlecenia do MT5.
        
        Args:
            trade_idea_id: ID pomysłu handlowego do wykonania
            
        Returns:
            Dict[str, Any]: Wynik wykonania pomysłu
        """
        logger.info(f"Wykonywanie pomysłu handlowego (ID: {trade_idea_id})")
        
        # Sprawdź, czy mamy niezbędne komponenty
        if not self.db_handler:
            return {"success": False, "error": "Brak połączenia z bazą danych"}
        if not self.mt5_connector:
            return {"success": False, "error": "Brak połączenia z MT5"}
        if not self.order_processor:
            return {"success": False, "error": "Brak procesora zleceń"}
        
        # Pobierz dane pomysłu handlowego
        trade_idea = self.db_handler.get_trade_idea(trade_idea_id)
        if not trade_idea:
            return {"success": False, "error": f"Nie znaleziono pomysłu handlowego (ID: {trade_idea_id})"}
        
        # Sprawdź, czy pomysł jest aktualny i oczekujący
        if trade_idea.get('status') != 'PENDING':
            return {
                "success": False, 
                "error": f"Pomysł handlowy ma niewłaściwy status: {trade_idea.get('status')}"
            }
        
        # Wykonaj sprawdzenie ryzyka
        risk_check = self.risk_manager.validate_trade_idea(
            symbol=trade_idea.get('symbol'),
            direction=trade_idea.get('direction'),
            entry_price=float(trade_idea.get('entry_price')),
            stop_loss=float(trade_idea.get('stop_loss')),
            take_profit=float(trade_idea.get('take_profit'))
        )
        
        if not risk_check.get('valid', False):
            # Aktualizuj status pomysłu na REJECTED
            self.db_handler.update_trade_idea(
                trade_idea_id, 
                {'status': 'REJECTED', 'rejection_reason': risk_check.get('reason')}
            )
            return {
                "success": False, 
                "error": f"Pomysł odrzucony przez zarządzanie ryzykiem: {risk_check.get('reason')}",
                "risk_limit_exceeded": True
            }
        
        # Przekaż pomysł do procesora zleceń
        result = self.order_processor.execute_trade_idea(trade_idea_id)
        
        # Aktualizuj status pomysłu na podstawie wyniku
        if result.get('success', False):
            self.db_handler.update_trade_idea(
                trade_idea_id, 
                {'status': 'EXECUTED', 'executed_at': datetime.now().isoformat()}
            )
            logger.info(f"Pomyślnie wykonano pomysł handlowy (ID: {trade_idea_id})")
        else:
            self.db_handler.update_trade_idea(
                trade_idea_id, 
                {'status': 'FAILED', 'rejection_reason': result.get('error')}
            )
            logger.error(f"Błąd podczas wykonywania pomysłu handlowego: {result.get('error')}")
        
        return result 
"""
Główny moduł silnika LLM do analizy rynku i generowania decyzji handlowych.

Ten moduł odpowiada za:
1. Inicjalizację komponenów (klient LLM, builder promptów, parser odpowiedzi)
2. Koordynację przepływu danych między komponentami
3. Wykonywanie analizy rynku i generowanie decyzji handlowych
4. Zarządzanie ryzykiem
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import time

from LLM_Engine.config import Config
from LLM_Engine.grok_client import GrokClient
from LLM_Engine.prompt_builder import PromptBuilder
from LLM_Engine.response_parser import ResponseParser
from LLM_Engine.market_analyzer import MarketAnalyzer
from LLM_Engine.cache_manager import CacheManager

logger = logging.getLogger(__name__)

class LLMEngine:
    """
    Główna klasa silnika LLM do analizy rynku i generowania decyzji handlowych.
    
    Koordynuje pracę wszystkich komponentów: klienta LLM, buildera promptów,
    parsera odpowiedzi, analizatora rynku i menadżera cache.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Inicjalizuje silnik LLM.
        
        Args:
            config_file: Opcjonalna ścieżka do pliku konfiguracyjnego
        """
        # Inicjalizacja konfiguracji
        self.config = Config(config_file)
        logger.info(f"Inicjalizacja silnika LLM z modelem: {self.config.model_name}")
        
        # Inicjalizacja menadżera cache
        self.cache_manager = CacheManager(
            cache_dir=self.config.cache_dir,
            enabled=self.config.enable_caching
        )
        
        # Inicjalizacja klienta LLM
        if self.config.model_type == "grok":
            # Inicjalizacja klienta Grok
            self.grok_client = GrokClient(
                api_key=self.config.xai_api_key,
                model_name=self.config.model_name,
                base_url=self.config.xai_base_url,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries
            )
            self.llm_client = self.grok_client  # Ustawienie głównego klienta
            logger.info(f"Zainicjalizowano klienta Grok z URL: {self.config.xai_base_url}")
        else:
            raise ValueError(f"Nieobsługiwany typ modelu: {self.config.model_type}")
        
        # Inicjalizacja buildera promptów
        templates_path = os.path.join(os.path.dirname(__file__), "templates")
        self.prompt_builder = PromptBuilder(templates_path=templates_path)
        
        # Inicjalizacja parsera odpowiedzi
        self.response_parser = ResponseParser()
        
        # Inicjalizacja analizatora rynku
        self.market_analyzer = MarketAnalyzer(llm_interface=self.llm_client)
        
        logger.info("Silnik LLM został zainicjalizowany")
        
    def analyze_market(
        self,
        symbol: str,
        timeframe: str,
        price_data: List[Dict[str, Any]],
        indicators: Dict[str, Any],
        news: Optional[List[Dict[str, Any]]] = None,
        strategy_name: Optional[str] = None,
        risk_level: str = "medium",
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analizuje rynek i generuje rekomendacje handlowe.
        
        Args:
            symbol: Symbol instrumentu (np. "EURUSD")
            timeframe: Przedział czasowy (np. "H1", "D1")
            price_data: Lista słowników z danymi cenowymi (OHLCV)
            indicators: Słownik z wartościami wskaźników technicznych
            news: Opcjonalna lista wiadomości rynkowych
            strategy_name: Opcjonalna nazwa strategii do zastosowania
            risk_level: Poziom ryzyka ("low", "medium", "high")
            additional_context: Dodatkowy kontekst dla modelu
            
        Returns:
            Dict[str, Any]: Wynik analizy i rekomendacje
        """
        # Generowanie unikalnego klucza cache
        cache_key = self._generate_cache_key(
            "market_analysis",
            symbol=symbol,
            timeframe=timeframe,
            last_candle=price_data[-1] if price_data else None,
            strategy=strategy_name
        )
        
        # Sprawdzenie cache
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            logger.info(f"Znaleziono wynik w cache dla {symbol} {timeframe}")
            return cached_result
        
        # Budowanie promptu do analizy rynku
        prompt = self.prompt_builder.build_market_analysis_prompt(
            symbol=symbol,
            timeframe=timeframe,
            price_data=price_data,
            indicators=indicators,
            news=news,
            strategy_name=strategy_name,
            risk_level=risk_level,
            additional_context=additional_context
        )
        
        # Pomiar czasu generowania odpowiedzi
        start_time = time.time()
        
        # Generowanie odpowiedzi w formacie JSON
        response = self.llm_client.generate_with_json_output(
            prompt=prompt,
            system_prompt="Jesteś doświadczonym analitykiem rynku. Analizujesz dane cenowe instrumentów finansowych."
        )
        
        generation_time = time.time() - start_time
        logger.info(f"Wygenerowano odpowiedź w {generation_time:.2f} sekundach")
        
        # Weryfikacja i walidacja odpowiedzi
        validated_response = self.response_parser.validate_market_analysis(response)
        
        # Dodanie metadanych do odpowiedzi
        validated_response["metadata"] = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "timeframe": timeframe,
            "model": self.config.model_name,
            "generation_time": generation_time
        }
        
        # Zapis do cache
        self.cache_manager.set(cache_key, validated_response)
        
        return validated_response
    
    def evaluate_position_risk(
        self,
        symbol: str,
        entry_price: float,
        position_type: str,
        stop_loss: float,
        take_profit: float,
        account_balance: float,
        risk_per_trade_pct: float = 2.0,
        open_positions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Ocenia ryzyko pozycji handlowej.
        
        Args:
            symbol: Symbol instrumentu
            entry_price: Cena wejścia
            position_type: Typ pozycji ("buy" lub "sell")
            stop_loss: Poziom stop loss
            take_profit: Poziom take profit
            account_balance: Stan konta
            risk_per_trade_pct: Procent ryzyka na transakcję
            open_positions: Lista obecnie otwartych pozycji
            
        Returns:
            Dict[str, Any]: Ocena ryzyka pozycji
        """
        if open_positions is None:
            open_positions = []
            
        # Generowanie unikalnego klucza cache
        cache_key = self._generate_cache_key(
            "position_risk",
            symbol=symbol,
            entry_price=entry_price,
            position_type=position_type,
            stop_loss=stop_loss,
            take_profit=take_profit,
            account_balance=account_balance
        )
        
        # Sprawdzenie cache
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            logger.info(f"Znaleziono ocenę ryzyka w cache dla {symbol} {position_type}")
            return cached_result
        
        # Obliczanie podstawowych metryk ryzyka
        if position_type.lower() == "buy":
            stop_loss_pips = (entry_price - stop_loss) * 10000
            take_profit_pips = (take_profit - entry_price) * 10000
        else:  # sell
            stop_loss_pips = (stop_loss - entry_price) * 10000
            take_profit_pips = (entry_price - take_profit) * 10000
            
        risk_reward_ratio = take_profit_pips / stop_loss_pips if stop_loss_pips != 0 else 0
        risk_amount = (account_balance * risk_per_trade_pct) / 100
        
        # Budowanie promptu do oceny ryzyka
        prompt = f"""
        Ocena ryzyka pozycji handlowej:
        Symbol: {symbol}
        Typ: {position_type}
        Cena wejścia: {entry_price}
        Stop Loss: {stop_loss} ({stop_loss_pips:.1f} pips)
        Take Profit: {take_profit} ({take_profit_pips:.1f} pips)
        Współczynnik RR: {risk_reward_ratio:.2f}
        Stan konta: {account_balance}
        Ryzyko kwotowe: {risk_amount}
        Liczba otwartych pozycji: {len(open_positions)}
        
        Oceń ryzyko tej pozycji i udziel rekomendacji w formacie JSON.
        """
        
        # Generowanie odpowiedzi w formacie JSON
        schema = {
            "risk_assessment": {
                "total_risk": "low/medium/high",
                "risk_reward_quality": "poor/acceptable/good/excellent",
                "position_sizing": "too_small/appropriate/too_large"
            },
            "recommendation": {
                "should_execute": True,
                "adjusted_position_size": "optional",
                "explanation": "string"
            }
        }
        
        response = self.llm_client.generate_with_json_output(
            prompt=prompt,
            system_prompt="Jesteś doświadczonym zarządzającym ryzykiem.",
            schema=schema
        )
        
        # Weryfikacja i walidacja odpowiedzi
        validated_response = self.response_parser.validate_risk_assessment(response)
        
        # Dodanie metadanych do odpowiedzi
        validated_response["metadata"] = {
                    "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "position_type": position_type,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": risk_reward_ratio
        }
        
        # Zapis do cache
        self.cache_manager.set(cache_key, validated_response)
        
        return validated_response
    
    def generate_trade_idea(
        self,
        market_data: Dict[str, Any],
        risk_profile: str = "balanced",
        max_risk_per_trade_pct: float = 2.0
    ) -> Dict[str, Any]:
        """
        Generuje pomysł na transakcję na podstawie danych rynkowych.
        
        Args:
            market_data: Słownik z danymi rynkowymi
            risk_profile: Profil ryzyka ("conservative", "balanced", "aggressive")
            max_risk_per_trade_pct: Maksymalny procent ryzyka na transakcję
            
        Returns:
            Dict[str, Any]: Pomysł na transakcję
        """
        symbol = market_data.get("symbol", "Unknown")
        timeframe = market_data.get("timeframe", "Unknown")
        current_price = market_data.get("current_price", 0.0)
        
        # Generowanie unikalnego klucza cache
        cache_key = self._generate_cache_key(
            "trade_idea",
            symbol=symbol,
            timeframe=timeframe,
            current_price=current_price,
            risk_profile=risk_profile
        )
        
        # Sprawdzenie cache
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            logger.info(f"Znaleziono pomysł w cache dla {symbol} {timeframe}")
            return cached_result
        
        # Uproszczenie danych rynkowych do promptu
        price_data = market_data.get("price_data", [])
        last_candles = price_data[-5:] if len(price_data) >= 5 else price_data
        
        # Budowanie promptu
        prompt = f"""
        Wygeneruj pomysł na transakcję dla:
        Symbol: {symbol}
        Przedział czasowy: {timeframe}
        Aktualny kurs: {current_price}
        Profil ryzyka: {risk_profile}
        Maksymalne ryzyko na transakcję: {max_risk_per_trade_pct}%
        
        Ostatnie świece:
        """
        
        for candle in last_candles:
            prompt += f"- O: {candle.get('open')}, H: {candle.get('high')}, L: {candle.get('low')}, C: {candle.get('close')}\n"
        
        prompt += """
        Określ:
        1. Kierunek transakcji (buy/sell)
        2. Uzasadnienie
        3. Poziom wejścia
        4. Stop loss
        5. Take profit
        
        Odpowiedź podaj w formacie JSON.
        """
        
        # Generowanie odpowiedzi
        schema = {
            "direction": "buy/sell",
            "entry": "float or range",
            "stop_loss": "float",
            "take_profit": "float",
            "rationale": "string",
            "confidence": "0-10 scale",
            "timeframe": "string"
        }
        
        response = self.llm_client.generate_with_json_output(
            prompt=prompt,
            system_prompt="Jesteś doświadczonym traderem. Generujesz konkretne pomysły na transakcje.",
            schema=schema
        )
        
        # Walidacja odpowiedzi
        validated_response = {}
        
        # Sprawdzenie, czy response jest stringiem i ewentualne parsowanie do słownika
        if isinstance(response, str):
            try:
                import json
                response = json.loads(response)
            except json.JSONDecodeError:
                logger.error(f"Nie można sparsować odpowiedzi JSON: {response}")
                response = {}

        if "direction" in response:
            validated_response["direction"] = response["direction"].lower()
        else:
            validated_response["direction"] = "hold"
            
        if "entry" in response:
            try:
                # Obsługa zarówno liczby jak i zakresu (np. "1.0800-1.0820")
                entry_value = response["entry"]
                if isinstance(entry_value, (int, float)):
                    validated_response["entry"] = float(entry_value)
                elif isinstance(entry_value, str) and "-" in entry_value:
                    entry_range = entry_value.split("-")
                    validated_response["entry_min"] = float(entry_range[0])
                    validated_response["entry_max"] = float(entry_range[1])
                else:
                    validated_response["entry"] = float(entry_value)
            except (ValueError, TypeError):
                validated_response["entry"] = current_price
        else:
            validated_response["entry"] = current_price
        
        # Domyślne wartości dla stop loss i take profit
        sl_default = current_price * 0.99 if validated_response["direction"] == "buy" else current_price * 1.01
        tp_default = current_price * 1.02 if validated_response["direction"] == "buy" else current_price * 0.98
        
        validated_response["stop_loss"] = float(response.get("stop_loss", sl_default))
        validated_response["take_profit"] = float(response.get("take_profit", tp_default))
        validated_response["rationale"] = response.get("rationale", "Brak uzasadnienia")
        validated_response["confidence"] = int(response.get("confidence", 5))
        
        # Obliczanie stosunku zysku do ryzyka
        if validated_response["direction"] == "buy":
            risk = validated_response["entry"] - validated_response["stop_loss"]
            reward = validated_response["take_profit"] - validated_response["entry"]
        else:
            risk = validated_response["stop_loss"] - validated_response["entry"]
            reward = validated_response["entry"] - validated_response["take_profit"]
            
        validated_response["risk_reward_ratio"] = round(reward / risk, 2) if risk > 0 else 0
        
        # Dodanie metadanych
        validated_response["metadata"] = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "timeframe": timeframe,
            "current_price": current_price,
            "risk_profile": risk_profile
        }
        
        # Zapis do cache
        self.cache_manager.set(cache_key, validated_response)
        
        return validated_response
    
    def calculate_position_size(
        self,
        symbol: str,
        account_balance: float,
        risk_per_trade_pct: float,
        entry_price: float,
        stop_loss: float,
        risk_per_pip: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Oblicza optymalną wielkość pozycji na podstawie zarządzania ryzykiem.
        
        Args:
            symbol: Symbol instrumentu
            account_balance: Stan konta
            risk_per_trade_pct: Procent ryzyka na transakcję
            entry_price: Cena wejścia
            stop_loss: Poziom stop loss
            risk_per_pip: Opcjonalna wartość ryzyka na pip
            
        Returns:
            Dict[str, Any]: Informacje o wielkości pozycji
        """
        # Obliczenie ryzyka
        risk_amount = account_balance * (risk_per_trade_pct / 100)
        stop_loss_pips = abs(entry_price - stop_loss) * 10000  # Dla par walutowych
        
        # Jeśli ryzyko na pip nie jest podane, przyjmujemy domyślne wartości
        if risk_per_pip is None:
            # Przyjmujemy że 0.01 lota = 1 USD/pip dla głównych par walutowych
            risk_per_pip = 1.0  # USD na pip na 0.01 lota
            
        # Obliczenie wielkości pozycji
        if stop_loss_pips > 0 and risk_per_pip > 0:
            position_size = risk_amount / (stop_loss_pips * risk_per_pip / 0.01)
            position_size = round(position_size, 2)  # Zaokrąglenie do 0.01 lota
        else:
            position_size = 0.01  # Minimalna wielkość
            
        return {
            "position_size": position_size,
            "risk_amount": risk_amount,
            "stop_loss_pips": stop_loss_pips,
            "risk_per_pip": risk_per_pip
        }
    
    def calculate_stop_loss_take_profit(
        self,
        symbol: str,
        position_type: str,
        entry_price: float,
        market_data: Dict[str, Any],
        risk_reward_ratio: float = 2.0,
        atr_multiplier: float = 1.5
    ) -> Dict[str, float]:
        """
        Oblicza poziomy stop loss i take profit na podstawie analizy rynku.
        
        Args:
            symbol: Symbol instrumentu
            position_type: Typ pozycji ("buy" lub "sell")
            entry_price: Cena wejścia
            market_data: Dane rynkowe zawierające wskaźniki
            risk_reward_ratio: Pożądany stosunek zysku do ryzyka
            atr_multiplier: Mnożnik ATR do obliczania stop loss
            
        Returns:
            Dict[str, float]: Poziomy stop loss i take profit
        """
        # Pobierz wskaźnik ATR jeśli dostępny
        indicators = market_data.get("indicators", {})
        atr = indicators.get("atr", None)
        
        if atr is not None and isinstance(atr, (list, tuple)) and len(atr) > 0:
            atr_value = atr[-1]  # Ostatnia wartość ATR
        else:
            # Jeśli ATR nie jest dostępny, użyj prostej metody opartej na średnim ruchu
            price_data = market_data.get("price_data", [])
            if len(price_data) >= 10:
                # Oblicz średni dzienny ruch z ostatnich 10 świec
                avg_range = sum(c.get("high", 0) - c.get("low", 0) for c in price_data[-10:]) / 10
                atr_value = avg_range
            else:
                # Domyślna wartość, jeśli nie ma wystarczających danych
                atr_value = entry_price * 0.001  # 0.1% ceny wejścia
        
        # Obliczanie stop loss na podstawie ATR
        sl_distance = atr_value * atr_multiplier
        
        if position_type.lower() == "buy":
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + (sl_distance * risk_reward_ratio)
        else:  # sell
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - (sl_distance * risk_reward_ratio)
            
        # Zaokrąglenie do 5 miejsc po przecinku
        stop_loss = round(stop_loss, 5)
        take_profit = round(take_profit, 5)
        
        return {
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "atr_value": atr_value,
            "risk_pips": sl_distance * 10000,  # Dla par walutowych
            "reward_pips": sl_distance * risk_reward_ratio * 10000  # Dla par walutowych
        }
    
    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """
        Generuje unikalny klucz cache na podstawie parametrów.
        
        Args:
            prefix: Prefiks klucza
            **kwargs: Parametry do uwzględnienia w kluczu
            
        Returns:
            str: Unikalny klucz cache
        """
        # Konwersja wartości do prostych typów serializowalnych
        serializable_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, dict):
                serializable_kwargs[key] = json.dumps(value, sort_keys=True)
            elif isinstance(value, (list, tuple)):
                if len(value) > 0 and isinstance(value[0], dict):
                    # Dla list słowników, używamy tylko pierwszego i ostatniego elementu
                    serializable_kwargs[key] = json.dumps([value[0], value[-1]], sort_keys=True)
                else:
                    serializable_kwargs[key] = str(value)
            else:
                serializable_kwargs[key] = str(value)
        
        # Tworzenie klucza jako połączenie prefiksu i wartości parametrów
        key_parts = [prefix]
        for k, v in sorted(serializable_kwargs.items()):
            key_parts.append(f"{k}={v}")
        
        return ":".join(key_parts)


# Przykład użycia
if __name__ == "__main__":
    # Konfiguracja logowania
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Inicjalizacja silnika LLM
    engine = LLMEngine()
    
    # Przykładowe dane rynkowe
    symbol = "EURUSD"
    timeframe = "H1"
    
    print(f"Silnik LLM został zainicjalizowany z modelem: {engine.config.model_name}")
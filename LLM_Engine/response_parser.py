"""
Parser odpowiedzi z modeli LLM.

Ten moduł zawiera implementacje parserów dla odpowiedzi z modeli językowych (LLM).
Parsery odpowiadają za ekstrakcję i walidację danych z odpowiedzi w różnych formatach.
"""

import json
import re
import logging
from typing import Dict, List, Any, Tuple, Optional, Type
from abc import ABC, abstractmethod
from datetime import datetime

# Konfiguracja loggera
logger = logging.getLogger(__name__)

class ResponseParser(ABC):
    """
    Bazowa klasa dla parserów odpowiedzi z modeli LLM.
    
    Klasa definiuje interfejs i wspólną funkcjonalność dla wszystkich parserów odpowiedzi.
    Implementuje metody do parsowania, walidacji i ekstrakcji metadanych.
    """
    
    def __init__(self):
        """Inicjalizacja parsera odpowiedzi."""
        self.parsed_response = None
        logger.debug(f"Inicjalizacja {self.__class__.__name__}")
    
    @abstractmethod
    def parse(self, response: str) -> Dict[str, Any]:
        """
        Parsuje odpowiedź z modelu LLM.
        
        Args:
            response: Tekst odpowiedzi do sparsowania
            
        Returns:
            Dict[str, Any]: Sparsowane dane
        """
        pass
    
    def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Waliduje sparsowane dane.
        
        Args:
            data: Dane do walidacji
            
        Returns:
            Tuple[bool, List[str]]: Wynik walidacji (True/False) i lista błędów
        """
        return True, []
    
    def validate_market_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Waliduje analizę rynku.
        
        Args:
            analysis: Słownik z analizą rynku do walidacji
            
        Returns:
            Dict[str, Any]: Zwalidowana analiza rynku
            
        Raises:
            ValueError: Gdy analiza nie przejdzie walidacji
        """
        required_fields = {
            "trend": ["bullish", "bearish", "sideways"],
            "strength": (1, 10),
            "volatility": ["low", "average", "high"],
            "description": str,
            "recommendation": str,
            "support_levels": list,
            "resistance_levels": list,
            "key_levels": list,
            "buy_signals": list,
            "sell_signals": list
        }
        
        # Sprawdzenie wymaganych pól
        for field, validation in required_fields.items():
            if field not in analysis:
                raise ValueError(f"Brak wymaganego pola: {field}")
                
            value = analysis[field]
            
            # Walidacja wartości pól
            if isinstance(validation, list):
                if value not in validation:
                    raise ValueError(f"Nieprawidłowa wartość dla {field}: {value}. Dozwolone wartości: {validation}")
            elif isinstance(validation, tuple):
                if not isinstance(value, (int, float)) or value < validation[0] or value > validation[1]:
                    raise ValueError(f"Wartość {field} musi być liczbą z zakresu {validation}")
            elif validation == str and not isinstance(value, str):
                raise ValueError(f"Pole {field} musi być tekstem")
            elif validation == list and not isinstance(value, list):
                raise ValueError(f"Pole {field} musi być listą")
                
        # Walidacja poziomów
        for level_list in [analysis["support_levels"], analysis["resistance_levels"], analysis["key_levels"]]:
            if not all(isinstance(level, (int, float)) for level in level_list):
                raise ValueError("Wszystkie poziomy muszą być liczbami")
                
        # Walidacja sygnałów
        for signal_list in [analysis["buy_signals"], analysis["sell_signals"]]:
            if not all(isinstance(signal, (int, float)) for signal in signal_list):
                raise ValueError("Wszystkie sygnały muszą być liczbami")
                
        # Dodanie metadanych
        if "metadata" not in analysis:
            analysis["metadata"] = {}
            
        analysis["metadata"]["validation_timestamp"] = datetime.now().isoformat()
        analysis["metadata"]["validation_status"] = "valid"
        
        return analysis
    
    def extract_metadata(self, response: str) -> Dict[str, Any]:
        """
        Ekstrahuje metadane z odpowiedzi.
        
        Args:
            response: Tekst odpowiedzi
            
        Returns:
            Dict[str, Any]: Metadane odpowiedzi
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "length": len(response),
            "has_code_blocks": "```" in response,
            "has_json": "```json" in response or "{" in response
        }
    
    def clean_response(self, response: str) -> str:
        """Czyści odpowiedź z nadmiarowych znaków białych."""
        if not response:
            return ""
        
        # Zachowanie bloków kodu
        code_blocks = []
        cleaned = response
        
        # Wyodrębnienie bloków kodu
        while "```" in cleaned:
            start = cleaned.find("```")
            end = cleaned.find("```", start + 3)
            if end == -1:
                break
            code_block = cleaned[start:end+3]
            placeholder = f"__CODE_BLOCK_{len(code_blocks)}__"
            code_blocks.append((placeholder, code_block))
            cleaned = cleaned.replace(code_block, placeholder)
        
        # Czyszczenie tekstu
        lines = cleaned.strip().split("\n")
        cleaned_lines = []
        prev_empty = False
        
        for line in lines:
            # Usuwanie nadmiarowych spacji, zachowując wcięcia
            line = " ".join(part.strip() for part in line.split())
            is_empty = not line
            
            if not (is_empty and prev_empty):
                cleaned_lines.append(line)
            
            prev_empty = is_empty
        
        cleaned = "\n".join(cleaned_lines)
        
        # Przywracanie bloków kodu
        for placeholder, code_block in code_blocks:
            cleaned = cleaned.replace(placeholder, code_block)
        
        return cleaned

class JSONResponseParser(ResponseParser):
    """
    Parser odpowiedzi w formacie JSON.
    
    Specjalizuje się w obsłudze odpowiedzi zawierających dane w formacie JSON,
    niezależnie czy to jako cała odpowiedź czy w blokach kodu.
    """
    
    def __init__(self, schema: Dict[str, Any] = None):
        """
        Inicjalizacja parsera JSON.
        
        Args:
            schema: Opcjonalny schemat do walidacji odpowiedzi JSON
        """
        super().__init__()
        self.schema = schema
    
    def parse(self, response: str) -> Dict[str, Any]:
        """
        Parsuje odpowiedź zawierającą JSON.
        
        Args:
            response: Tekst odpowiedzi do sparsowania
            
        Returns:
            Dict[str, Any]: Sparsowane dane JSON
        """
        try:
            # Czyszczenie odpowiedzi
            cleaned_response = self.clean_response(response)
            
            # Ekstrakcja JSON z odpowiedzi
            json_data = extract_json_from_response(cleaned_response)
            
            # Zapisanie sparsowanych danych
            self.parsed_response = json_data
            
            # Walidacja danych, jeśli podano schemat
            if self.schema:
                valid, errors = self.validate(json_data)
                if not valid:
                    logger.warning(f"Walidacja JSON nie powiodła się: {errors}")
            
            return json_data
        
        except Exception as e:
            logger.error(f"Błąd podczas parsowania JSON: {str(e)}")
            return {}
    
    def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Waliduje dane JSON zgodnie ze schematem.
        
        Args:
            data: Dane JSON do walidacji
            
        Returns:
            Tuple[bool, List[str]]: Wynik walidacji i lista błędów
        """
        if not self.schema:
            return True, []
        
        errors = []
        
        # Sprawdzenie wymaganych pól
        for field in self.schema.get("required", []):
            if field not in data:
                errors.append(f"Brak wymaganego pola: {field}")
        
        # Sprawdzenie typów pól
        for field, field_type in self.schema.get("properties", {}).items():
            if field in data:
                if field_type == "string" and not isinstance(data[field], str):
                    errors.append(f"Pole {field} powinno być typu string")
                elif field_type == "number" and not isinstance(data[field], (int, float)):
                    errors.append(f"Pole {field} powinno być typu number")
                elif field_type == "boolean" and not isinstance(data[field], bool):
                    errors.append(f"Pole {field} powinno być typu boolean")
                elif field_type == "array" and not isinstance(data[field], list):
                    errors.append(f"Pole {field} powinno być typu array")
                elif field_type == "object" and not isinstance(data[field], dict):
                    errors.append(f"Pole {field} powinno być typu object")
        
        return len(errors) == 0, errors

class TradeSignalParser(ResponseParser):
    """
    Parser odpowiedzi zawierających sygnały handlowe.
    
    Specjalizuje się w ekstrakcji danych dotyczących sygnałów handlowych,
    takich jak kierunek, cena wejścia, stop loss itp.
    """
    
    def __init__(self):
        """Inicjalizacja parsera sygnałów handlowych."""
        super().__init__()
    
    def parse(self, response: str) -> List[Dict[str, Any]]:
        """
        Parsuje odpowiedź zawierającą sygnały handlowe.
        
        Args:
            response: Tekst odpowiedzi do sparsowania
            
        Returns:
            List[Dict[str, Any]]: Lista sparsowanych sygnałów handlowych
        """
        try:
            # Czyszczenie odpowiedzi
            cleaned_response = self.clean_response(response)
            
            # Ekstrakcja sygnałów handlowych
            trade_signals = extract_trading_signals(cleaned_response)
            
            # Walidacja i standaryzacja każdego sygnału
            valid_signals = []
            for signal in trade_signals:
                standardized_signal = self._standardize_signal(signal)
                valid, errors = self.validate(standardized_signal)
                if valid:
                    valid_signals.append(standardized_signal)
                else:
                    logger.warning(f"Sygnał handlowy nie przeszedł walidacji: {errors}")
            
            # Zapisanie sparsowanych danych
            self.parsed_response = valid_signals
            
            return valid_signals
            
        except Exception as e:
            logger.error(f"Błąd podczas parsowania sygnałów handlowych: {str(e)}")
            return []
    
    def _standardize_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standaryzuje format sygnału handlowego.
        
        Args:
            signal: Sygnał handlowy do standaryzacji
            
        Returns:
            Dict[str, Any]: Standaryzowany sygnał handlowy
        """
        standardized = signal.copy()
        
        # Standaryzacja kierunku transakcji
        if "direction" in standardized and "signal" not in standardized:
            standardized["signal"] = standardized.pop("direction")
        if isinstance(standardized.get("signal"), str):
            signal_value = standardized["signal"].lower()
            if signal_value in ["buy", "long"]:
                standardized["signal"] = "buy"
            elif signal_value in ["sell", "short"]:
                standardized["signal"] = "sell"
        
        # Standaryzacja pary walutowej
        if "symbol" in standardized and "pair" not in standardized:
            standardized["pair"] = standardized.pop("symbol")
        
        # Standaryzacja ceny wejścia
        if "entry_price" in standardized and "entry" not in standardized:
            standardized["entry"] = standardized.pop("entry_price")
        
        # Konwersja wartości liczbowych
        numeric_fields = ["entry", "stop_loss", "take_profit", "risk_reward"]
        for field in numeric_fields:
            if field in standardized and not isinstance(standardized[field], (int, float)):
                try:
                    standardized[field] = float(str(standardized[field]).replace(',', '.'))
                except (ValueError, TypeError):
                    standardized.pop(field, None)
        
        return standardized
    
    def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Waliduje sygnał handlowy.
        
        Args:
            data: Dane sygnału do walidacji
            
        Returns:
            Tuple[bool, List[str]]: Wynik walidacji i lista błędów
        """
        errors = []
        
        # Sprawdzenie wymaganych pól
        required_fields = ["signal", "pair"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            errors.append(f"Missing required fields: {', '.join(missing_fields)}")
            return False, errors
        
        # Walidacja kierunku transakcji
        if data["signal"] not in ["buy", "sell"]:
            errors.append(f"Invalid signal value: {data['signal']}")
            return False, errors
        
        # Walidacja pary walutowej
        if not isinstance(data["pair"], str) or not re.match(r'^[A-Z]{6}$', data["pair"]):
            errors.append(f"Invalid pair format: {data['pair']}")
            return False, errors
        
        # Walidacja wartości liczbowych
        numeric_fields = ["entry", "stop_loss", "take_profit"]
        for field in numeric_fields:
            if field in data:
                if not isinstance(data[field], (int, float)):
                    errors.append(f"Invalid {field} value: must be a number")
                    return False, errors
                if data[field] <= 0:
                    errors.append(f"Invalid {field} value: must be positive")
                    return False, errors
        
        # Walidacja spójności poziomów cenowych
        if all(field in data for field in numeric_fields):
            entry = data["entry"]
            sl = data["stop_loss"]
            tp = data["take_profit"]
            
            if data["signal"] == "buy":
                if not (sl < entry < tp):
                    errors.append("Invalid price levels for BUY signal: should be SL < Entry < TP")
                    return False, errors
            else:  # sell
                if not (tp < entry < sl):
                    errors.append("Invalid price levels for SELL signal: should be TP < Entry < SL")
                    return False, errors
        
        return True, []

class MarketAnalysisParser(ResponseParser):
    """
    Parser odpowiedzi zawierających analizę rynku.
    
    Specjalizuje się w ekstrakcji danych dotyczących analizy rynku,
    takich jak trend, poziomy wsparcia/oporu, wskaźniki techniczne itp.
    """
    
    def __init__(self):
        """Inicjalizacja parsera analizy rynku."""
        super().__init__()
    
    def parse(self, response: str) -> Dict[str, Any]:
        """
        Parsuje odpowiedź zawierającą analizę rynku.
        
        Args:
            response: Tekst odpowiedzi do sparsowania
            
        Returns:
            Dict[str, Any]: Sparsowane dane analizy rynku
        """
        try:
            # Czyszczenie odpowiedzi
            cleaned_response = self.clean_response(response)
            
            # Ekstrakcja JSON z odpowiedzi
            json_data = extract_json_from_response(cleaned_response)
            
            # Standaryzacja kluczy
            standardized_data = self._standardize_keys(json_data)
            
            # Walidacja danych
            valid, errors = self.validate(standardized_data)
            if not valid:
                logger.warning(f"Walidacja analizy rynku nie powiodła się: {errors}")
                return {}
            
            # Zapisanie sparsowanych danych
            self.parsed_response = standardized_data
            
            return standardized_data
            
        except Exception as e:
            logger.error(f"Błąd podczas parsowania analizy rynku: {str(e)}")
            return {}
    
    def _standardize_keys(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standaryzuje klucze w danych analizy rynku.
        
        Args:
            data: Dane do standaryzacji
            
        Returns:
            Dict[str, Any]: Dane ze standaryzowanymi kluczami
        """
        standardized = data.copy()
        
        # Mapowanie kluczy
        key_mapping = {
            "market": "market",
            "pair": "market",
            "symbol": "market",
            "instrument": "market",
            "strength": "strength",
            "support": "support_levels",
            "resistance": "resistance_levels"
        }
        
        # Zamiana kluczy - zawsze mapuj zgodnie z key_mapping
        for old_key, new_key in key_mapping.items():
            if old_key in standardized:
                value = standardized.pop(old_key)
                standardized[new_key] = value
        
        # Konwersja wartości
        if "trend" in standardized and isinstance(standardized["trend"], str):
            standardized["trend"] = standardized["trend"].lower()
        
        if "strength" in standardized:
            try:
                standardized["strength"] = int(standardized["strength"])
            except (ValueError, TypeError):
                standardized.pop("strength")
        
        # Konwersja poziomów na listy
        level_fields = ["support_levels", "resistance_levels"]
        for field in level_fields:
            if field in standardized:
                if isinstance(standardized[field], (int, float)):
                    standardized[field] = [standardized[field]]
                elif isinstance(standardized[field], str):
                    try:
                        standardized[field] = [float(x.strip()) for x in standardized[field].split(",")]
                    except (ValueError, TypeError):
                        standardized[field] = []
        
        return standardized
    
    def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Waliduje dane analizy rynku.
        
        Args:
            data: Dane do walidacji
            
        Returns:
            Tuple[bool, List[str]]: Wynik walidacji i lista błędów
        """
        errors = []
        
        # Sprawdzenie wymaganych pól
        required_fields = ["market", "trend"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            errors.append(f"Missing required fields: {', '.join(missing_fields)}")
            return False, errors
        
        # Walidacja pary walutowej
        if not isinstance(data["market"], str) or not re.match(r'^[A-Z]{6}$', data["market"]):
            errors.append(f"Invalid market format: {data['market']}")
            return False, errors
        
        # Walidacja trendu
        valid_trends = ["bullish", "bearish", "neutral", "sideways"]
        if data["trend"] not in valid_trends:
            errors.append(f"Invalid trend value: {data['trend']}")
            return False, errors
        
        # Walidacja siły trendu
        if "strength" in data:
            if not isinstance(data["strength"], int) or not (1 <= data["strength"] <= 10):
                errors.append("Trend strength must be an integer between 1 and 10")
                return False, errors
        
        # Walidacja poziomów
        level_fields = ["support_levels", "resistance_levels"]
        for field in level_fields:
            if field in data:
                if not isinstance(data[field], list):
                    errors.append(f"{field} must be a list")
                    return False, errors
                if not all(isinstance(x, (int, float)) and x > 0 for x in data[field]):
                    errors.append(f"All {field} must be positive numbers")
                    return False, errors
        
        return True, []

class RiskAssessmentParser(ResponseParser):
    """Parser oceny ryzyka."""
    
    def parse(self, response: str) -> Dict[str, Any]:
        """Parsuje ocenę ryzyka."""
        try:
            # Czyszczenie odpowiedzi
            cleaned = self.clean_response(response)
            
            # Ekstrakcja JSON z bloku kodu
            if "```json" in cleaned:
                start = cleaned.find("```json") + 7
                end = cleaned.find("```", start)
                if end != -1:
                    json_str = cleaned[start:end].strip()
                else:
                    json_str = cleaned[start:].strip()
            else:
                json_str = cleaned
            
            # Parsowanie JSON
            data = json.loads(json_str)
            
            # Walidacja
            valid, errors = self.validate(data)
            if not valid:
                logger.warning(f"Nieprawidłowa ocena ryzyka: {', '.join(errors)}")
                return {}
            
            return data
            
        except Exception as e:
            logger.error(f"Błąd parsowania oceny ryzyka: {str(e)}")
            return {}
    
    def validate(self, assessment: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Waliduje ocenę ryzyka."""
        errors = []
        
        # Wymagane pola
        required_fields = ["trade_id", "risk_level", "risk_reward_ratio"]
        for field in required_fields:
            if field not in assessment:
                errors.append(f"Brak wymaganego pola: {field}")
        
        # Walidacja poziomu ryzyka
        valid_risk_levels = ["low", "medium", "high", "extreme"]
        if "risk_level" in assessment and assessment["risk_level"] not in valid_risk_levels:
            errors.append(f"Nieprawidłowy poziom ryzyka (dozwolone: {', '.join(valid_risk_levels)})")
            return False, errors
        
        # Walidacja współczynnika risk/reward
        if "risk_reward_ratio" in assessment:
            rr = assessment["risk_reward_ratio"]
            if not isinstance(rr, (int, float)) or rr <= 0:
                errors.append("risk_reward_ratio musi być dodatnią liczbą")
        
        # Walidacja czynników ryzyka
        if "risk_factors" in assessment:
            risk_factors = assessment["risk_factors"]
            if not isinstance(risk_factors, list):
                errors.append("risk_factors musi być listą")
            else:
                for factor in risk_factors:
                    if not isinstance(factor, dict):
                        errors.append("każdy czynnik ryzyka musi być obiektem")
                        break
                    if "factor" not in factor or "impact" not in factor:
                        errors.append("każdy czynnik ryzyka musi mieć pola 'factor' i 'impact'")
                        break
                    if not isinstance(factor["factor"], str):
                        errors.append("pole 'factor' musi być tekstem")
                        break
                    valid_impacts = ["low", "medium", "high"]
                    if factor["impact"] not in valid_impacts:
                        errors.append(f"pole 'impact' musi być jednym z: {', '.join(valid_impacts)}")
                        break
        
        # Walidacja zaleceń
        if "recommendations" in assessment:
            recommendations = assessment["recommendations"]
            if not isinstance(recommendations, list):
                errors.append("recommendations musi być listą")
            else:
                for rec in recommendations:
                    if not isinstance(rec, str):
                        errors.append("każde zalecenie musi być tekstem")
                        break
        
        return len(errors) == 0, errors

class TradeIdeaParser(ResponseParser):
    """
    Parser pomysłów handlowych.
    
    Specjalizuje się w ekstrakcji danych dotyczących pomysłów handlowych,
    takich jak kierunek transakcji, poziomy wejścia, stop loss i take profit.
    """
    
    def __init__(self):
        """Inicjalizacja parsera pomysłów handlowych."""
        super().__init__()
    
    def parse(self, response: str) -> Dict[str, Any]:
        """
        Parsuje odpowiedź zawierającą pomysł handlowy.
        
        Args:
            response: Tekst odpowiedzi do sparsowania
            
        Returns:
            Dict[str, Any]: Sparsowany pomysł handlowy
        """
        try:
            # Czyszczenie odpowiedzi
            cleaned_response = self.clean_response(response)
            
            # Ekstrakcja JSON z odpowiedzi
            json_data = extract_json_from_response(cleaned_response)
            if not json_data:
                return {}
            
            # Standaryzacja danych
            standardized_data = self._standardize_trade_idea(json_data)
            
            # Walidacja danych
            valid, errors = self.validate(standardized_data)
            if not valid:
                logger.warning(f"Walidacja pomysłu handlowego nie powiodła się: {errors}")
                return {}
            
            # Zapisanie sparsowanych danych
            self.parsed_response = standardized_data
            
            return standardized_data
            
        except Exception as e:
            logger.error(f"Błąd podczas parsowania pomysłu handlowego: {str(e)}")
            return {}
    
    def _standardize_trade_idea(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standaryzuje dane pomysłu handlowego.
        
        Args:
            data: Dane do standaryzacji
            
        Returns:
            Dict[str, Any]: Standaryzowane dane
        """
        standardized = {
            "action": data.get("action", "HOLD").upper(),
            "symbol": data.get("symbol", ""),
            "entry_price": float(data.get("entry_price", 0)),
            "stop_loss": float(data.get("stop_loss", 0)),
            "take_profit": float(data.get("take_profit", 0)),
            "risk_reward_ratio": float(data.get("risk_reward_ratio", 0)),
            "confidence": int(data.get("confidence", 0)),
            "timeframe": data.get("timeframe", ""),
            "reasoning": data.get("reasoning", ""),
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "source": "trade_idea_parser"
            }
        }
        
        return standardized
    
    def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Waliduje sparsowane dane pomysłu handlowego.
        
        Args:
            data: Dane do walidacji
            
        Returns:
            Tuple[bool, List[str]]: Wynik walidacji (True/False) i lista błędów
        """
        errors = []
        
        # Sprawdzenie wymaganych pól
        required_fields = ["action", "symbol"]
        for field in required_fields:
            if not data.get(field):
                errors.append(f"Brak wymaganego pola: {field}")
        
        # Walidacja akcji
        valid_actions = ["BUY", "SELL", "HOLD"]
        if data.get("action") not in valid_actions:
            errors.append(f"Nieprawidłowa akcja: {data.get('action')}")
        
        # Walidacja wartości liczbowych
        numeric_fields = ["entry_price", "stop_loss", "take_profit", "risk_reward_ratio"]
        for field in numeric_fields:
            value = data.get(field, 0)
            if not isinstance(value, (int, float)):
                errors.append(f"Pole {field} musi być liczbą")
        
        # Walidacja poziomu pewności
        confidence = data.get("confidence", 0)
        if not isinstance(confidence, int) or confidence < 0 or confidence > 100:
            errors.append("Poziom pewności musi być liczbą całkowitą od 0 do 100")
        
        return len(errors) == 0, errors

class ResponseParserFactory:
    """
    Fabryka parserów odpowiedzi.
    
    Odpowiada za tworzenie odpowiednich parserów w zależności od typu odpowiedzi.
    """
    
    @staticmethod
    def get_parser(response_type: str) -> ResponseParser:
        """
        Zwraca odpowiedni parser dla danego typu odpowiedzi.
        
        Args:
            response_type: Typ odpowiedzi (np. 'json', 'trade_signal', 'market_analysis')
            
        Returns:
            ResponseParser: Instancja odpowiedniego parsera
            
        Raises:
            ValueError: Gdy podano nieznany typ odpowiedzi
        """
        parsers = {
            "json": JSONResponseParser,
            "trade_signal": TradeSignalParser,
            "market_analysis": MarketAnalysisParser,
            "risk_assessment": RiskAssessmentParser,
            "trade_idea": TradeIdeaParser
        }
        
        parser_class = parsers.get(response_type.lower())
        if parser_class:
            return parser_class()
        else:
            raise ValueError(f"Nieznany typ odpowiedzi: {response_type}")

# Implementacje funkcji używanych w testach

def extract_json_from_response(response: str) -> Dict[str, Any]:
    """
    Ekstrahuje dane JSON z odpowiedzi.
    
    Obsługuje różne formaty, w których JSON może być umieszczony w odpowiedzi,
    w tym w blokach kodu markdown czy bezpośrednio w tekście.
    
    Args:
        response: Tekst odpowiedzi
        
    Returns:
        Dict[str, Any]: Wyekstrahowane dane JSON lub pusty słownik w przypadku błędu
    """
    try:
        # Wyszukiwanie bloków kodu JSON
        json_block_pattern = r'```(?:json)?\s*([\s\S]*?)```'
        json_blocks = re.findall(json_block_pattern, response)
        
        for block in json_blocks:
            try:
                return json.loads(block.strip())
            except json.JSONDecodeError:
                continue
        
        # Jeśli nie znaleziono w blokach kodu, szukaj JSON bezpośrednio w tekście
        json_pattern = r'{[\s\S]*}'
        json_matches = re.findall(json_pattern, response)
        
        for match in json_matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        # Jeśli nie znaleziono, zwróć pusty słownik
        return {}
        
    except Exception as e:
        logger.error(f"Błąd podczas ekstrahowania JSON: {str(e)}")
        return {}

def extract_trading_signals(response: str) -> List[Dict[str, Any]]:
    """
    Ekstrahuje sygnały handlowe z odpowiedzi.
    
    Args:
        response: Tekst odpowiedzi
        
    Returns:
        List[Dict[str, Any]]: Lista sygnałów handlowych
    """
    signals = []
    
    # Ekstrakcja wszystkich bloków JSON
    json_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)```', response)
    
    for block in json_blocks:
        try:
            data = json.loads(block.strip())
            
            # Standaryzacja kluczy
            if "symbol" in data and "pair" not in data:
                data["pair"] = data["symbol"]
            if "direction" in data and "signal" not in data:
                data["signal"] = data["direction"]
            if "entry_price" in data and "entry" not in data:
                data["entry"] = data["entry_price"]
            
            # Sprawdzenie, czy to sygnał handlowy
            if ("signal" in data or "direction" in data) and ("pair" in data or "symbol" in data):
                # Konwersja wartości
                if isinstance(data.get("signal"), str):
                    data["signal"] = data["signal"].lower()
                if isinstance(data.get("direction"), str):
                    data["signal"] = data["direction"].lower()
                
                signals.append(data)
        except json.JSONDecodeError:
            continue
    
    # Ekstrakcja sygnałów z tekstu
    # Wyszukiwanie par, sygnału, poziomów wejścia/wyjścia za pomocą wyrażeń regularnych
    text_blocks = re.split(r'```(?:json)?\s*[\s\S]*?```', response)
    for block in text_blocks:
        if not block.strip():
            continue
            
        pair_pattern = r'(?i)(?:para|pair|instrument|symbol)[:\s]+([A-Z]{6})'
        signal_pattern = r'(?i)(?:sygnał|signal|action|kierunek)[:\s]+(buy|sell|long|short)'
        entry_pattern = r'(?i)(?:wejście|entry|cena wejścia)[:\s]+([\d.]+)'
        sl_pattern = r'(?i)(?:stop loss|sl)[:\s]+([\d.]+)'
        tp_pattern = r'(?i)(?:take profit|tp)[:\s]+([\d.]+)'
        timeframe_pattern = r'(?i)(?:timeframe|okres|tf)[:\s]+([A-Z0-9]+)'
        rationale_pattern = r'(?i)(?:uzasadnienie|rationale|reason)[:\s]+([^\n]+)'
        
        pair_match = re.search(pair_pattern, block)
        signal_match = re.search(signal_pattern, block)
        
        if pair_match and signal_match:
            signal = {
                "pair": pair_match.group(1),
                "signal": signal_match.group(1).lower()
            }
            
            if "long" in signal["signal"]:
                signal["signal"] = "buy"
            elif "short" in signal["signal"]:
                signal["signal"] = "sell"
            
            entry_match = re.search(entry_pattern, block)
            if entry_match:
                signal["entry"] = float(entry_match.group(1))
                
            sl_match = re.search(sl_pattern, block)
            if sl_match:
                signal["stop_loss"] = float(sl_match.group(1))
                
            tp_match = re.search(tp_pattern, block)
            if tp_match:
                signal["take_profit"] = float(tp_match.group(1))
                
            timeframe_match = re.search(timeframe_pattern, block)
            if timeframe_match:
                signal["timeframe"] = timeframe_match.group(1).upper()
                
            rationale_match = re.search(rationale_pattern, block)
            if rationale_match:
                signal["rationale"] = rationale_match.group(1).strip()
            
            signals.append(signal)
    
    return signals

def parse_market_analysis(response: str) -> Dict[str, Any]:
    """
    Parsuje analizę rynkową z odpowiedzi.
    
    Args:
        response: Tekst odpowiedzi
        
    Returns:
        Dict[str, Any]: Sparsowana analiza rynkowa
    """
    # Najpierw próbujemy znaleźć JSON
    market_data = extract_json_from_response(response)
    
    if market_data and ("pair" in market_data or "symbol" in market_data):
        # Standaryzacja kluczy
        if "symbol" in market_data and "pair" not in market_data:
            market_data["pair"] = market_data["symbol"]
        
        return market_data
    
    # Jeśli nie znaleziono JSON lub nie zawiera wymaganych pól, ekstrahujemy dane za pomocą regex
    market_data = {}
    
    # Ekstrahowanie pary walutowej
    pair_pattern = r'(?i)analiza\s+rynku\s+([A-Z]{6})'
    pair_match = re.search(pair_pattern, response)
    if pair_match:
        market_data["pair"] = pair_match.group(1)
    
    # Ekstrahowanie trendu
    trend_pattern = r'(?i)trend[:\s]+(wzrostowy|spadkowy|rosnący|malejący|sideways|bullish|bearish|neutral)'
    trend_match = re.search(trend_pattern, response)
    if trend_match:
        trend = trend_match.group(1).lower()
        if trend in ["wzrostowy", "rosnący", "bullish"]:
            market_data["trend"] = "bullish"
        elif trend in ["spadkowy", "malejący", "bearish"]:
            market_data["trend"] = "bearish"
        else:
            market_data["trend"] = "neutral"
    
    # Ekstrahowanie poziomów wsparcia/oporu
    support_pattern = r'(?i)wsparcie[:\s]+([\d., ]+)'
    resistance_pattern = r'(?i)opór[:\s]+([\d., ]+)'
    
    support_match = re.search(support_pattern, response)
    resistance_match = re.search(resistance_pattern, response)
    
    key_levels = {}
    
    if support_match:
        support_str = support_match.group(1)
        support_values = re.findall(r'([\d.]+)', support_str)
        key_levels["support"] = [float(val) for val in support_values]
    
    if resistance_match:
        resistance_str = resistance_match.group(1)
        resistance_values = re.findall(r'([\d.]+)', resistance_str)
        key_levels["resistance"] = [float(val) for val in resistance_values]
    
    if key_levels:
        market_data["key_levels"] = key_levels
    
    # Ekstrahowanie perspektywy/podsumowania
    outlook_pattern = r'(?i)(?:perspektywa|outlook|podsumowanie|summary)[:\s]+(.+?)(?=\n\n|\n[A-Z]|\Z)'
    outlook_match = re.search(outlook_pattern, response, re.DOTALL)
    if outlook_match:
        market_data["outlook"] = outlook_match.group(1).strip()
    
    return market_data

def parse_risk_assessment(response: str) -> Dict[str, Any]:
    """
    Parsuje ocenę ryzyka z odpowiedzi.
    
    Args:
        response: Tekst odpowiedzi
        
    Returns:
        Dict[str, Any]: Sparsowana ocena ryzyka
    """
    # Najpierw próbujemy znaleźć JSON
    risk_data = extract_json_from_response(response)
    
    if risk_data and "risk_level" in risk_data:
        return risk_data
    
    # Jeśli nie znaleziono JSON lub nie zawiera wymaganych pól, ekstrahujemy dane za pomocą regex
    risk_data = {}
    
    # Ekstrahowanie pary walutowej
    pair_pattern = r'(?i)(?:para|pair|instrument|symbol)[:\s]+([A-Z]{6})'
    pair_match = re.search(pair_pattern, response)
    if pair_match:
        risk_data["pair"] = pair_match.group(1)
    
    # Ekstrahowanie typu pozycji
    position_pattern = r'(?i)(?:pozycja|position)[:\s]+(long|short|buy|sell)'
    position_match = re.search(position_pattern, response)
    if position_match:
        position = position_match.group(1).lower()
        if position in ["buy", "long"]:
            risk_data["position_type"] = "long"
        else:
            risk_data["position_type"] = "short"
    
    # Ekstrahowanie poziomu ryzyka
    risk_level_pattern = r'(?i)(?:poziom ryzyka|risk level)[:\s]+(high|medium|low|wysokie|średnie|niskie)'
    risk_level_match = re.search(risk_level_pattern, response)
    if risk_level_match:
        risk_level = risk_level_match.group(1).lower()
        if risk_level in ["high", "wysokie"]:
            risk_data["risk_level"] = "high"
        elif risk_level in ["medium", "średnie"]:
            risk_data["risk_level"] = "medium"
        else:
            risk_data["risk_level"] = "low"
    
    # Ekstrahowanie maksymalnej straty procentowej
    max_loss_pattern = r'(?i)(?:maksymalna strata|max loss)[:\s]+([\d.]+)%?'
    max_loss_match = re.search(max_loss_pattern, response)
    if max_loss_match:
        risk_data["max_loss_percent"] = float(max_loss_match.group(1))
    
    # Ekstrahowanie stosunku zysku do ryzyka
    rr_pattern = r'(?i)(?:stosunek zysku do ryzyka|risk reward ratio|risk reward|risk/reward)[:\s]+([\d.]+)'
    rr_match = re.search(rr_pattern, response)
    if rr_match:
        risk_data["risk_reward_ratio"] = float(rr_match.group(1))
    
    return risk_data

def validate_trade_idea(trade_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Waliduje pomysł handlowy pod kątem poprawności danych.
    
    Args:
        trade_data: Dane pomysłu handlowego
        
    Returns:
        Tuple[bool, str]: Wynik walidacji (True/False) i komunikat
    """
    # Sprawdzenie wymaganych pól
    required_fields = ["pair", "direction", "entry_price", "stop_loss", "take_profit", "timeframe", "rationale"]
    missing_fields = [field for field in required_fields if field not in trade_data]
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    # Sprawdzenie poprawności kierunku
    valid_directions = ["buy", "sell", "long", "short"]
    if trade_data["direction"].lower() not in valid_directions:
        return False, f"Invalid direction: {trade_data['direction']}"
    
    # Sprawdzenie wartości liczbowych
    numeric_fields = ["entry_price", "stop_loss", "take_profit"]
    for field in numeric_fields:
        if not isinstance(trade_data[field], (int, float)):
            return False, f"Invalid value for {field}: must be a number"
    
    # Sprawdzenie timeframe
    valid_timeframes = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN"]
    if trade_data["timeframe"] not in valid_timeframes:
        return False, f"Invalid timeframe: {trade_data['timeframe']}"
    
    # Sprawdzenie uzasadnienia
    if not isinstance(trade_data["rationale"], str) or len(trade_data["rationale"].strip()) < 5:
        return False, f"Invalid rationale: must be a non-empty string"
    
    # Jeśli wszystkie walidacje przeszły pomyślnie
    return True, "Trade idea is valid" 
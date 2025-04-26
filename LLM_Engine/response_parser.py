"""
Moduł odpowiedzialny za przetwarzanie i walidację odpowiedzi z modelu LLM.

Ten moduł implementuje funkcje do:
1. Wyodrębniania struktury JSON z odpowiedzi tekstowych
2. Walidacji zgodności odpowiedzi ze schematami
3. Naprawiania nieprawidłowych lub niekompletnych odpowiedzi
4. Standaryzacji formatów odpowiedzi dla różnych typów analizy
"""

import json
import re
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
import jsonschema

# Konfiguracja loggera
logger = logging.getLogger(__name__)

class ResponseParser:
    """
    Klasa odpowiedzialna za przetwarzanie i walidację odpowiedzi z modelu LLM.
    """
    
    # Schemat dla odpowiedzi analizy rynkowej
    MARKET_ANALYSIS_SCHEMA = {
        "type": "object",
        "required": ["key_levels", "explanation"],
        "properties": {
            "analysis": {
                "type": "object",
                "properties": {
                    "trend": {
                        "type": "string",
                        "enum": ["bullish", "bearish", "neutral", "sideways", "ranging"]
                    },
                    "strength": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10
                    },
                    "volatility": {"type": "string"},
                    "momentum": {"type": "string"}
                },
                "required": ["trend"]
            },
            "trend": {
                "type": "string",
                "enum": ["bullish", "bearish", "neutral", "sideways", "ranging"]
            },
            "strength": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10
            },
            "key_levels": {
                "type": "object",
                "required": ["support", "resistance"],
                "properties": {
                    "support": {
                        "type": "array",
                        "items": {"type": "number"}
                    },
                    "resistance": {
                        "type": "array",
                        "items": {"type": "number"}
                    }
                }
            },
            "recommendation": {
                "oneOf": [
                    {
                        "type": "string",
                        "enum": ["buy", "sell", "hold", "wait"]
                    },
                    {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string"},
                            "setup": {"type": "string"}
                        },
                        "required": ["action"]
                    }
                ]
            },
            "explanation": {
                "type": "string"
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
            },
            "time_frame": {
                "type": "string"
            },
            "pattern": {
                "type": "string"
            }
        },
        "additionalProperties": True
    }
    
    # Schemat dla odpowiedzi zarządzania ryzykiem
    RISK_MANAGEMENT_SCHEMA = {
        "type": "object",
        "required": ["position_size", "stop_loss", "take_profit", "risk_assessment"],
        "properties": {
            "position_size": {
                "type": "object",
                "required": ["units", "lots"],
                "properties": {
                    "units": {"type": "number"},
                    "lots": {"type": "number"}
                }
            },
            "stop_loss": {
                "type": "object",
                "required": ["price", "pips", "account_risk_percent"],
                "properties": {
                    "price": {"type": "number"},
                    "pips": {"type": "number"},
                    "account_risk_percent": {"type": "number"}
                }
            },
            "take_profit": {
                "type": "object",
                "required": ["price", "pips", "risk_reward_ratio"],
                "properties": {
                    "price": {"type": "number"},
                    "pips": {"type": "number"},
                    "risk_reward_ratio": {"type": "number"}
                }
            },
            "risk_assessment": {
                "type": "object",
                "required": ["overall_risk_level"],
                "properties": {
                    "overall_risk_level": {
                        "type": "string",
                        "enum": ["low", "medium", "high"]
                    }
                }
            },
            "explanation": {
                "type": "string"
            }
        },
        "additionalProperties": True
    }
    
    def __init__(self):
        """
        Inicjalizuje parser odpowiedzi.
        """
        logger.info("Inicjalizacja ResponseParser")
    
    def extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Wyodrębnia obiekt JSON z tekstu odpowiedzi.
        
        Args:
            text: Tekst odpowiedzi z modelu LLM
            
        Returns:
            Dict[str, Any]: Sparsowany obiekt JSON lub None jeśli nie znaleziono
            
        Uwaga:
            Ta metoda próbuje znaleźć i sparsować JSON na kilka sposobów:
            1. Szuka bloków kodu oznaczonych jako json
            2. Szuka par znaków {} w tekście
            3. Próbuje sparsować cały tekst jako JSON
        """
        # Metoda 1: Szukanie bloków kodu JSON
        json_regex = r"```(?:json)?\s*([\s\S]*?)\s*```"
        matches = re.findall(json_regex, text)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        # Metoda 2: Szukanie par znaków {} w tekście
        start_idx = text.find('{')
        if start_idx != -1:
            # Znajdź ostatni nawias zamykający
            nested_level = 0
            for i in range(start_idx, len(text)):
                if text[i] == '{':
                    nested_level += 1
                elif text[i] == '}':
                    nested_level -= 1
                    if nested_level == 0:
                        # Znaleziono kompletny obiekt JSON
                        try:
                            return json.loads(text[start_idx:i+1])
                        except json.JSONDecodeError:
                            break
        
        # Metoda 3: Próba sparsowania całego tekstu
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Nie można znaleźć poprawnego JSON w odpowiedzi")
            return None
    
    def validate_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """
        Waliduje dane względem schematu JSON.
        
        Args:
            data: Dane do walidacji
            schema: Schemat JSON do walidacji
            
        Returns:
            bool: True jeśli dane są zgodne ze schematem, False w przeciwnym razie
        """
        try:
            jsonschema.validate(instance=data, schema=schema)
            return True
        except jsonschema.exceptions.ValidationError as e:
            logger.warning(f"Walidacja schematu nie powiodła się: {str(e)}")
            return False
    
    def parse_market_analysis(self, response: str) -> Dict[str, Any]:
        """
        Parsuje odpowiedź analizy rynkowej.
        
        Args:
            response: Odpowiedź z modelu LLM
            
        Returns:
            Dict[str, Any]: Sparsowana i znormalizowana odpowiedź
            
        Raises:
            ValueError: Jeśli odpowiedź nie zawiera poprawnego JSON lub nie można jej naprawić
        """
        # Próba wyodrębnienia JSON z odpowiedzi
        data = self.extract_json_from_text(response)
        
        if not data:
            error_msg = "Nie można wyodrębnić JSON z odpowiedzi analizy rynkowej"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Walidacja względem schematu analizy rynkowej
        is_valid = self.validate_schema(data, self.MARKET_ANALYSIS_SCHEMA)
        
        # Jeśli dane nie są zgodne ze schematem, spróbuj je naprawić
        if not is_valid:
            logger.info("Próba naprawy nieprawidłowej odpowiedzi analizy rynkowej")
            data = self._try_fix_market_analysis(data)
            
            # Ponowna walidacja
            is_valid = self.validate_schema(data, self.MARKET_ANALYSIS_SCHEMA)
            if not is_valid:
                logger.warning("Nie można naprawić odpowiedzi analizy rynkowej")
                
                # Dodaj metadane błędu, ale zwróć dane nawet jeśli są nieprawidłowe
                data["_validation"] = {
                    "is_valid": False,
                    "timestamp": datetime.now().isoformat(),
                    "error": "Odpowiedź nie spełnia schematu analizy rynkowej"
                }
            else:
                data["_validation"] = {
                    "is_valid": True,
                    "timestamp": datetime.now().isoformat(),
                    "was_fixed": True
                }
        else:
            data["_validation"] = {
                "is_valid": True,
                "timestamp": datetime.now().isoformat(),
                "was_fixed": False
            }
        
        return data
    
    def _try_fix_market_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Próbuje naprawić nieprawidłową odpowiedź analizy rynkowej.
        
        Args:
            data: Nieprawidłowe dane odpowiedzi
            
        Returns:
            Dict[str, Any]: Naprawione dane
        """
        fixed_data = data.copy()
        
        # Sprawdź czy mamy nową strukturę z analysis jako obiektem
        if "analysis" in fixed_data and isinstance(fixed_data["analysis"], dict):
            # Mamy nową strukturę - sprawdźmy czy wszystkie kluczowe pola są obecne
            analysis = fixed_data["analysis"]
            
            # Sprawdź i napraw pole "trend" w analysis
            if "trend" not in analysis or analysis["trend"] not in ["bullish", "bearish", "neutral", "sideways", "ranging"]:
                # Jeśli brak trendu, spróbuj wywnioskować z rekomendacji
                if "recommendation" in fixed_data:
                    if isinstance(fixed_data["recommendation"], dict) and "action" in fixed_data["recommendation"]:
                        action = fixed_data["recommendation"]["action"].lower()
                        if "buy" in action:
                            analysis["trend"] = "bullish"
                        elif "sell" in action:
                            analysis["trend"] = "bearish"
                        else:
                            analysis["trend"] = "neutral"
                    elif isinstance(fixed_data["recommendation"], str):
                        if fixed_data["recommendation"] == "buy":
                            analysis["trend"] = "bullish"
                        elif fixed_data["recommendation"] == "sell":
                            analysis["trend"] = "bearish"
                        else:
                            analysis["trend"] = "neutral"
                    else:
                        analysis["trend"] = "neutral"
                else:
                    analysis["trend"] = "neutral"  # Domyślnie neutralny
            
            # Sprawdź i napraw pole "strength" w analysis
            if "strength" not in analysis or not isinstance(analysis["strength"], int) or analysis["strength"] < 1 or analysis["strength"] > 10:
                if "strength" in analysis and isinstance(analysis["strength"], (int, float)):
                    # Konwersja do zakresu 1-10
                    if analysis["strength"] <= 0:
                        analysis["strength"] = 1
                    elif analysis["strength"] > 10:
                        analysis["strength"] = 10
                    else:
                        analysis["strength"] = int(analysis["strength"])
                else:
                    analysis["strength"] = 5  # Domyślnie średnia siła
            
            # Sprawdź czy mamy kluczowe pola volatility i momentum
            if "volatility" not in analysis:
                analysis["volatility"] = "średnia"
            if "momentum" not in analysis:
                analysis["momentum"] = "neutralny"
            
            # Zaktualizuj główny obiekt analysis
            fixed_data["analysis"] = analysis
            
        # Stara struktura - obsługa pola "trend" bezpośrednio w głównym obiekcie
        elif "trend" not in fixed_data or fixed_data["trend"] not in ["bullish", "bearish", "neutral", "sideways", "ranging"]:
            # Jeśli brak trendu, spróbuj wywnioskować z rekomendacji
            if "recommendation" in fixed_data:
                if isinstance(fixed_data["recommendation"], dict) and "action" in fixed_data["recommendation"]:
                    action = fixed_data["recommendation"]["action"].lower()
                    if "buy" in action:
                        fixed_data["trend"] = "bullish"
                    elif "sell" in action:
                        fixed_data["trend"] = "bearish"
                    else:
                        fixed_data["trend"] = "neutral"
                elif isinstance(fixed_data["recommendation"], str):
                    if fixed_data["recommendation"] == "buy":
                        fixed_data["trend"] = "bullish"
                    elif fixed_data["recommendation"] == "sell":
                        fixed_data["trend"] = "bearish"
                    else:
                        fixed_data["trend"] = "neutral"
                else:
                    fixed_data["trend"] = "neutral"
            else:
                fixed_data["trend"] = "neutral"  # Domyślnie neutralny
            
            # Stwórz obiekt analysis jeśli nie ma
            fixed_data["analysis"] = {
                "trend": fixed_data["trend"],
                "strength": fixed_data.get("strength", 5),
                "volatility": "średnia",
                "momentum": "neutralny"
            }
        
        # Sprawdź i napraw pole "strength" w głównym obiekcie (stara struktura)
        if "strength" not in fixed_data or not isinstance(fixed_data["strength"], int) or fixed_data["strength"] < 1 or fixed_data["strength"] > 10:
            if "strength" in fixed_data and isinstance(fixed_data["strength"], (int, float)):
                # Konwersja do zakresu 1-10
                if fixed_data["strength"] <= 0:
                    fixed_data["strength"] = 1
                elif fixed_data["strength"] > 10:
                    fixed_data["strength"] = 10
                else:
                    fixed_data["strength"] = int(fixed_data["strength"])
            else:
                fixed_data["strength"] = 5  # Domyślnie średnia siła
        
        # Sprawdź i napraw pole "key_levels"
        if "key_levels" not in fixed_data or not isinstance(fixed_data["key_levels"], dict):
            fixed_data["key_levels"] = {"support": [], "resistance": []}
        else:
            if "support" not in fixed_data["key_levels"] or not isinstance(fixed_data["key_levels"]["support"], list):
                fixed_data["key_levels"]["support"] = []
            if "resistance" not in fixed_data["key_levels"] or not isinstance(fixed_data["key_levels"]["resistance"], list):
                fixed_data["key_levels"]["resistance"] = []
        
        # Sprawdź i napraw pole "recommendation"
        if "recommendation" not in fixed_data:
            # Stwórz nową strukturę recommendation
            if "analysis" in fixed_data and "trend" in fixed_data["analysis"]:
                trend = fixed_data["analysis"]["trend"]
                if trend == "bullish":
                    fixed_data["recommendation"] = {"action": "Wait for bullish setup", "setup": "Pullback to support"}
                elif trend == "bearish":
                    fixed_data["recommendation"] = {"action": "Wait for bearish setup", "setup": "Pullback to resistance"}
                else:
                    fixed_data["recommendation"] = {"action": "Wait for clear setup", "setup": "Range breakout"}
            else:
                fixed_data["recommendation"] = {"action": "Wait for clear setup", "setup": "None at this time"}
        elif isinstance(fixed_data["recommendation"], str) and fixed_data["recommendation"] not in ["buy", "sell", "hold", "wait"]:
            # Przekształć string na nową strukturę
            action = fixed_data["recommendation"]
            fixed_data["recommendation"] = {"action": action, "setup": "Custom setup"}
        
        # Sprawdź i napraw pole "explanation"
        if "explanation" not in fixed_data or not fixed_data["explanation"]:
            trend = fixed_data.get("analysis", {}).get("trend", fixed_data.get("trend", "neutral"))
            strength = fixed_data.get("analysis", {}).get("strength", fixed_data.get("strength", 5))
            fixed_data["explanation"] = f"Analiza wskazuje na trend {trend} o sile {strength}/10."
        
        return fixed_data
    
    def parse_risk_management(self, response: str) -> Dict[str, Any]:
        """
        Parsuje odpowiedź zarządzania ryzykiem.
        
        Args:
            response: Odpowiedź z modelu LLM
            
        Returns:
            Dict[str, Any]: Sparsowana i znormalizowana odpowiedź
            
        Raises:
            ValueError: Jeśli odpowiedź nie zawiera poprawnego JSON lub nie można jej naprawić
        """
        # Próba wyodrębnienia JSON z odpowiedzi
        data = self.extract_json_from_text(response)
        
        if not data:
            error_msg = "Nie można wyodrębnić JSON z odpowiedzi zarządzania ryzykiem"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Walidacja względem schematu zarządzania ryzykiem
        is_valid = self.validate_schema(data, self.RISK_MANAGEMENT_SCHEMA)
        
        # Jeśli dane nie są zgodne ze schematem, spróbuj je naprawić
        if not is_valid:
            logger.info("Próba naprawy nieprawidłowej odpowiedzi zarządzania ryzykiem")
            data = self._try_fix_risk_management(data)
            
            # Ponowna walidacja
            is_valid = self.validate_schema(data, self.RISK_MANAGEMENT_SCHEMA)
            if not is_valid:
                logger.warning("Nie można naprawić odpowiedzi zarządzania ryzykiem")
                
                # Dodaj metadane błędu, ale zwróć dane nawet jeśli są nieprawidłowe
                data["_validation"] = {
                    "is_valid": False,
                    "timestamp": datetime.now().isoformat(),
                    "error": "Odpowiedź nie spełnia schematu zarządzania ryzykiem"
                }
            else:
                data["_validation"] = {
                    "is_valid": True,
                    "timestamp": datetime.now().isoformat(),
                    "was_fixed": True
                }
        else:
            data["_validation"] = {
                "is_valid": True,
                "timestamp": datetime.now().isoformat(),
                "was_fixed": False
            }
        
        return data
    
    def _try_fix_risk_management(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Próbuje naprawić nieprawidłową odpowiedź zarządzania ryzykiem.
        
        Args:
            data: Nieprawidłowe dane odpowiedzi
            
        Returns:
            Dict[str, Any]: Naprawione dane
        """
        fixed_data = data.copy()
        
        # Sprawdź i napraw pole "position_size"
        if "position_size" not in fixed_data or not isinstance(fixed_data["position_size"], dict):
            fixed_data["position_size"] = {"units": 0, "lots": 0}
        else:
            if "units" not in fixed_data["position_size"] or not isinstance(fixed_data["position_size"]["units"], (int, float)):
                fixed_data["position_size"]["units"] = 0
            if "lots" not in fixed_data["position_size"] or not isinstance(fixed_data["position_size"]["lots"], (int, float)):
                fixed_data["position_size"]["lots"] = 0
        
        # Sprawdź i napraw pole "stop_loss"
        if "stop_loss" not in fixed_data or not isinstance(fixed_data["stop_loss"], dict):
            fixed_data["stop_loss"] = {"price": 0, "pips": 0, "account_risk_percent": 0}
        else:
            if "price" not in fixed_data["stop_loss"] or not isinstance(fixed_data["stop_loss"]["price"], (int, float)):
                fixed_data["stop_loss"]["price"] = 0
            if "pips" not in fixed_data["stop_loss"] or not isinstance(fixed_data["stop_loss"]["pips"], (int, float)):
                fixed_data["stop_loss"]["pips"] = 0
            if "account_risk_percent" not in fixed_data["stop_loss"] or not isinstance(fixed_data["stop_loss"]["account_risk_percent"], (int, float)):
                fixed_data["stop_loss"]["account_risk_percent"] = 0
        
        # Sprawdź i napraw pole "take_profit"
        if "take_profit" not in fixed_data or not isinstance(fixed_data["take_profit"], dict):
            fixed_data["take_profit"] = {"price": 0, "pips": 0, "risk_reward_ratio": 0}
        else:
            if "price" not in fixed_data["take_profit"] or not isinstance(fixed_data["take_profit"]["price"], (int, float)):
                fixed_data["take_profit"]["price"] = 0
            if "pips" not in fixed_data["take_profit"] or not isinstance(fixed_data["take_profit"]["pips"], (int, float)):
                fixed_data["take_profit"]["pips"] = 0
            if "risk_reward_ratio" not in fixed_data["take_profit"] or not isinstance(fixed_data["take_profit"]["risk_reward_ratio"], (int, float)):
                fixed_data["take_profit"]["risk_reward_ratio"] = 0
        
        # Sprawdź i napraw pole "risk_assessment"
        if "risk_assessment" not in fixed_data or not isinstance(fixed_data["risk_assessment"], dict):
            fixed_data["risk_assessment"] = {"overall_risk_level": "medium"}
        else:
            if "overall_risk_level" not in fixed_data["risk_assessment"] or fixed_data["risk_assessment"]["overall_risk_level"] not in ["low", "medium", "high"]:
                fixed_data["risk_assessment"]["overall_risk_level"] = "medium"
        
        return fixed_data
    
    def parse_custom_json_response(self, response: str, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Parsuje niestandardową odpowiedź JSON z opcjonalną walidacją schematu.
        
        Args:
            response: Odpowiedź z modelu LLM
            schema: Opcjonalny schemat do walidacji
            
        Returns:
            Dict[str, Any]: Sparsowana odpowiedź
            
        Raises:
            ValueError: Jeśli odpowiedź nie zawiera poprawnego JSON
        """
        # Próba wyodrębnienia JSON z odpowiedzi
        data = self.extract_json_from_text(response)
        
        if not data:
            error_msg = "Nie można wyodrębnić JSON z odpowiedzi"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Walidacja względem dostarczonego schematu (jeśli istnieje)
        if schema:
            is_valid = self.validate_schema(data, schema)
            data["_validation"] = {
                "is_valid": is_valid,
                "timestamp": datetime.now().isoformat()
            }
        else:
            data["_validation"] = {
                "is_valid": None,  # Brak walidacji
                "timestamp": datetime.now().isoformat()
            }
        
        return data
    
    def parse_free_text_response(self, response: str) -> str:
        """
        Parsuje odpowiedź tekstową bez formatu JSON.
        
        Args:
            response: Odpowiedź z modelu LLM
            
        Returns:
            str: Czysty tekst odpowiedzi
        """
        # Usuń znaczniki kodu markdown
        text = re.sub(r"```[a-z]*\n|```", "", response)
        
        # Usunięcie dodatkowych znaków nowej linii i spacji
        text = re.sub(r"\n+", "\n", text)
        text = re.sub(r" +", " ", text)
        
        return text.strip()
        
    def validate_market_analysis(self, response: str) -> Dict[str, Any]:
        """
        Waliduje i przetwarza odpowiedź analizy rynkowej.
        
        Args:
            response: Odpowiedź z modelu LLM
            
        Returns:
            Dict[str, Any]: Zwalidowana i przetworzona odpowiedź
            
        Note:
            Ta metoda jest wrapperem dla parse_market_analysis, która dodaje metadane
            do wynikowej odpowiedzi
        """
        try:
            # Parsowanie odpowiedzi
            result = self.parse_market_analysis(response)
            
            # Dodanie metadanych do odpowiedzi
            if "_metadata" not in result:
                result["_metadata"] = {
                    "timestamp": datetime.now().isoformat(),
                    "execution_time_ms": 0,
                    "provider": "default",
                    "success": True
                }
            
            return result
        except Exception as e:
            logger.error(f"Błąd podczas walidacji analizy rynkowej: {str(e)}")
            # Zwrócenie pustego wyniku z informacją o błędzie
            return {
                "error": str(e),
                "_validation": {
                    "is_valid": False,
                    "timestamp": datetime.now().isoformat(),
                    "error": f"Błąd podczas walidacji: {str(e)}"
                },
                "_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "execution_time_ms": 0,
                    "provider": "default",
                    "success": False
                }
            }
        
    def validate_risk_assessment(self, response: str) -> Dict[str, Any]:
        """
        Waliduje i przetwarza odpowiedź oceny ryzyka.
        
        Args:
            response: Odpowiedź z modelu LLM
            
        Returns:
            Dict[str, Any]: Zwalidowana i przetworzona odpowiedź
            
        Note:
            Ta metoda jest wrapperem dla parse_risk_management, która dodaje metadane
            do wynikowej odpowiedzi
        """
        try:
            # Parsowanie odpowiedzi
            result = self.parse_risk_management(response)
            
            # Dodanie metadanych do odpowiedzi
            if "_metadata" not in result:
                result["_metadata"] = {
                    "timestamp": datetime.now().isoformat(),
                    "execution_time_ms": 0,
                    "provider": "default",
                    "success": True
                }
            
            return result
        except Exception as e:
            logger.error(f"Błąd podczas walidacji oceny ryzyka: {str(e)}")
            # Zwrócenie pustego wyniku z informacją o błędzie
            return {
                "error": str(e),
                "_validation": {
                    "is_valid": False,
                    "timestamp": datetime.now().isoformat(),
                    "error": f"Błąd podczas walidacji: {str(e)}"
                },
                "_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "execution_time_ms": 0,
                    "provider": "default",
                    "success": False
                }
            }


# Przykład użycia
if __name__ == "__main__":
    # Konfiguracja logowania
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Inicjalizacja parsera
    parser = ResponseParser()
    
    # Przykładowa odpowiedź JSON
    example_response = """
    Oto analiza rynku:
    
    ```json
    {
      "trend": "bullish",
      "strength": 7,
      "key_levels": {
        "support": [1.0780, 1.0750],
        "resistance": [1.0850, 1.0880]
      },
      "recommendation": "buy",
      "explanation": "Rynek wykazuje silny trend wzrostowy z potencjałem kontynuacji."
    }
    ```
    """
    
    # Parsowanie przykładowej odpowiedzi
    try:
        result = parser.parse_market_analysis(example_response)
        print("Sparsowana odpowiedź:")
        print(json.dumps(result, indent=2))
    except ValueError as e:
        print(f"Błąd parsowania: {str(e)}") 
"""
Moduł postprocessora dla odpowiedzi z modeli LLM.

Ten moduł zawiera klasy odpowiedzialne za przetwarzanie odpowiedzi z modeli językowych,
w tym parsowanie struktury JSON, walidację odpowiedzi i formatowanie wyników.
"""

import json
import logging
import re
import jsonschema
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

# Inicjalizacja loggera
logger = logging.getLogger(__name__)

class LLMPostprocessor:
    """
    Klasa bazowa dla postprocessora odpowiedzi z modelu LLM.
    """
    
    def __init__(self):
        """Inicjalizacja postprocessora."""
        logger.debug("Inicjalizacja LLMPostprocessor")
        self.processed_response = None
        
    def extract_text_from_response(self, response: str) -> str:
        """
        Ekstrahuje czysty tekst z odpowiedzi LLM, która może być w różnych formatach.
        
        Args:
            response: Odpowiedź tekstowa lub w formacie JSON
            
        Returns:
            str: Wyekstrahowany tekst odpowiedzi
        """
        # Próba parsowania jako JSON
        try:
            # Odpowiedź może być już obiektem JSON lub stringiem do parsowania
            if isinstance(response, str):
                json_data = json.loads(response)
            else:
                json_data = response
                
            # Szukanie tekstu w znanej strukturze 
            if "choices" in json_data and len(json_data["choices"]) > 0:
                if "message" in json_data["choices"][0] and "content" in json_data["choices"][0]["message"]:
                    return json_data["choices"][0]["message"]["content"]
                elif "text" in json_data["choices"][0]:
                    return json_data["choices"][0]["text"]
            
            # Jeśli jest pole content bezpośrednio w odpowiedzi
            if "content" in json_data:
                return json_data["content"]
                
            # Jeśli jest pole text bezpośrednio w odpowiedzi
            if "text" in json_data:
                return json_data["text"]
                
        except (json.JSONDecodeError, TypeError, KeyError):
            # Jeśli nie jest to poprawny JSON lub nie znaleziono tekstu w strukturze
            pass
            
        # Jeśli nie udało się znaleźć tekstu w JSON, zwróć oryginalną odpowiedź
        return response

    def clean_response(self, response: str) -> str:
        """
        Czyści odpowiedź z modelu LLM.
        
        Args:
            response: Odpowiedź z modelu LLM
            
        Returns:
            str: Oczyszczona odpowiedź
        """
        # Usunięcie nadmiarowych białych znaków
        cleaned = re.sub(r'\s+', ' ', response)
        cleaned = cleaned.strip()
        
        return cleaned
    
    def postprocess_response(self, response: str) -> str:
        """
        Przetwarza odpowiedź z modelu LLM.
        
        Args:
            response: Odpowiedź z modelu LLM
            
        Returns:
            str: Przetworzona odpowiedź
        """
        # W klasie bazowej po prostu zwraca odpowiedź bez zmian
        self.processed_response = response
        return response
    
    def get_processed_response(self) -> str:
        """
        Zwraca przetworzoną odpowiedź.
        
        Returns:
            str: Przetworzona odpowiedź
        """
        return self.processed_response
    
    def extract_json(self, response: str) -> Dict[str, Any]:
        """
        Ekstraktuje strukturę JSON z odpowiedzi tekstowej.
        
        Args:
            response: Odpowiedź tekstowa z modelu LLM
            
        Returns:
            Dict[str, Any]: Struktura JSON lub pusty słownik
        """
        from LLM_Engine.response_parser import extract_json_from_response
        
        try:
            return extract_json_from_response(response)
        except Exception as e:
            logger.error(f"Błąd podczas ekstraktowania JSON: {str(e)}")
            return {}
    
    def process_generic_response(self, response: str) -> Dict[str, Any]:
        """
        Przetwarza ogólną odpowiedź z modelu LLM.
        
        Args:
            response: Odpowiedź z modelu LLM
            
        Returns:
            Dict[str, Any]: Przetworzona odpowiedź
        """
        # Próba ekstraktowania JSON
        json_data = self.extract_json(response)
        
        if json_data:
            return {
                "parsed_data": json_data,
                "raw_response": response
            }
        else:
            # Jeśli nie udało się sparsować JSON, zwróć surową odpowiedź
            cleaned_response = self.clean_response(response)
            return {
                "text": cleaned_response,
                "raw_response": response
            }
    
    def process_market_analysis(self, response: str) -> Dict[str, Any]:
        """
        Przetwarza odpowiedź zawierającą analizę rynku.
        
        Args:
            response: Odpowiedź z modelu LLM
            
        Returns:
            Dict[str, Any]: Przetworzona analiza rynku
        """
        # Ekstraktowanie JSON
        json_data = self.extract_json(response)
        
        # Sprawdzenie, czy zawiera wymagane pola
        required_fields = ["key_levels"]
        
        if json_data and all(field in json_data for field in required_fields):
            result = json_data
        else:
            # Próba naprawy odpowiedzi
            result = self._repair_market_analysis(response)
        
        # Dodanie oryginalnej odpowiedzi
        result["raw_response"] = response
        
        # Dodanie timestampu
        result["timestamp"] = datetime.now().isoformat()
        
        return result
    
    def _repair_market_analysis(self, response: str) -> Dict[str, Any]:
        """
        Próbuje naprawić nieprawidłową odpowiedź analizy rynku.
        
        Args:
            response: Odpowiedź z modelu LLM
            
        Returns:
            Dict[str, Any]: Naprawiona analiza rynku
        """
        result = {
            "key_levels": {
                "support": [],
                "resistance": []
            },
            "explanation": "Nie udało się wyodrębnić pełnej analizy."
        }
        
        # Próba ekstrakcji trendu
        trend_match = re.search(r'trend[:\s]+([a-zA-Z]+)', response, re.IGNORECASE)
        if trend_match:
            result["trend"] = trend_match.group(1).lower()
        
        # Próba ekstrakcji poziomów wsparcia
        support_matches = re.findall(r'support[:\s]+([\d.]+)', response, re.IGNORECASE)
        if support_matches:
            result["key_levels"]["support"] = [float(level) for level in support_matches]
        
        # Próba ekstrakcji poziomów oporu
        resistance_matches = re.findall(r'resistance[:\s]+([\d.]+)', response, re.IGNORECASE)
        if resistance_matches:
            result["key_levels"]["resistance"] = [float(level) for level in resistance_matches]
        
        # Próba ekstrakcji rekomendacji
        recommendation_match = re.search(r'recommendation[:\s]+([a-zA-Z]+)', response, re.IGNORECASE)
        if recommendation_match:
            result["recommendation"] = recommendation_match.group(1).lower()
        
        return result
    
    def process_trade_signal(self, response: str) -> Dict[str, Any]:
        """
        Przetwarza odpowiedź zawierającą sygnał handlowy.
        
        Args:
            response: Odpowiedź z modelu LLM
            
        Returns:
            Dict[str, Any]: Przetworzony sygnał handlowy
        """
        # Ekstraktowanie JSON
        json_data = self.extract_json(response)
        
        # Sprawdzenie, czy zawiera wymagane pola
        required_fields = ["signal", "entry"]
        
        if json_data and all(field in json_data for field in required_fields):
            result = json_data
        else:
            # Próba naprawy odpowiedzi
            result = self._repair_trade_signal(response)
        
        # Dodanie oryginalnej odpowiedzi
        result["raw_response"] = response
        
        # Dodanie timestampu
        result["timestamp"] = datetime.now().isoformat()
        
        return result
    
    def _repair_trade_signal(self, response: str) -> Dict[str, Any]:
        """
        Próbuje naprawić nieprawidłową odpowiedź sygnału handlowego.
        
        Args:
            response: Odpowiedź z modelu LLM
            
        Returns:
            Dict[str, Any]: Naprawiony sygnał handlowy
        """
        result = {
            "signal": "unknown",
            "entry": 0.0,
            "explanation": "Nie udało się wyodrębnić pełnego sygnału."
        }
        
        # Próba ekstrakcji kierunku sygnału
        signal_match = re.search(r'(buy|sell|long|short)', response, re.IGNORECASE)
        if signal_match:
            signal = signal_match.group(1).lower()
            if signal in ["buy", "long"]:
                result["signal"] = "buy"
            elif signal in ["sell", "short"]:
                result["signal"] = "sell"
        
        # Próba ekstrakcji ceny wejścia
        entry_match = re.search(r'entry[:\s]+([\d.]+)', response, re.IGNORECASE)
        if entry_match:
            result["entry"] = float(entry_match.group(1))
        
        # Próba ekstrakcji stop loss
        sl_match = re.search(r'stop[_\s-]*loss[:\s]+([\d.]+)', response, re.IGNORECASE)
        if sl_match:
            result["stop_loss"] = float(sl_match.group(1))
        
        # Próba ekstrakcji take profit
        tp_match = re.search(r'take[_\s-]*profit[:\s]+([\d.]+)', response, re.IGNORECASE)
        if tp_match:
            result["take_profit"] = float(tp_match.group(1))
        
        return result
    
    def process_risk_assessment(self, response: str) -> Dict[str, Any]:
        """
        Przetwarza odpowiedź zawierającą ocenę ryzyka.
        
        Args:
            response: Odpowiedź z modelu LLM
            
        Returns:
            Dict[str, Any]: Przetworzona ocena ryzyka
        """
        # Ekstraktowanie JSON
        json_data = self.extract_json(response)
        
        # Sprawdzenie, czy zawiera wymagane pola
        required_fields = ["risk_level", "position_size"]
        
        if json_data and all(field in json_data for field in required_fields):
            result = json_data
        else:
            # Próba naprawy odpowiedzi
            result = self._repair_risk_assessment(response)
        
        # Dodanie oryginalnej odpowiedzi
        result["raw_response"] = response
        
        # Dodanie timestampu
        result["timestamp"] = datetime.now().isoformat()
        
        return result
    
    def _repair_risk_assessment(self, response: str) -> Dict[str, Any]:
        """
        Próbuje naprawić nieprawidłową odpowiedź oceny ryzyka.
        
        Args:
            response: Odpowiedź z modelu LLM
            
        Returns:
            Dict[str, Any]: Naprawiona ocena ryzyka
        """
        result = {
            "risk_level": "unknown",
            "position_size": 0.0,
            "explanation": "Nie udało się wyodrębnić pełnej oceny ryzyka."
        }
        
        # Próba ekstrakcji poziomu ryzyka
        risk_level_match = re.search(r'risk[_\s-]*level[:\s]+([a-zA-Z]+)', response, re.IGNORECASE)
        if risk_level_match:
            result["risk_level"] = risk_level_match.group(1).lower()
        
        # Próba ekstrakcji wielkości pozycji
        position_size_match = re.search(r'position[_\s-]*size[:\s]+([\d.]+)', response, re.IGNORECASE)
        if position_size_match:
            result["position_size"] = float(position_size_match.group(1))
        
        # Próba ekstrakcji stosunku ryzyka do zysku
        risk_reward_match = re.search(r'risk[_\s-]*reward[:\s]+([\d.]+)', response, re.IGNORECASE)
        if risk_reward_match:
            result["risk_reward"] = float(risk_reward_match.group(1))
        
        return result


class MarketAnalysisPostprocessor(LLMPostprocessor):
    """
    Postprocesor odpowiedzi zawierających analizę rynkową.
    
    Przetwarza surowe odpowiedzi modelu, aby wyodrębnić i sformatować
    analizę rynkową.
    """
    
    def __init__(self):
        """Inicjalizacja postprocesora analizy rynkowej."""
        super().__init__()
        logger.debug("Inicjalizacja MarketAnalysisPostprocessor")
        self.expected_schema = {
            "type": "object",
            "properties": {
                "pair": {"type": "string"},
                "timeframe": {"type": "string"},
                "trend": {"type": "string"},
                "sentiment": {"type": "string"},
                "key_levels": {
                    "type": "object",
                    "properties": {
                        "support": {"type": "array", "items": {"type": "number"}},
                        "resistance": {"type": "array", "items": {"type": "number"}}
                    }
                }
            },
            "required": ["pair", "trend", "key_levels"]
        }
    
    def extract_market_sentiment(self, text: str) -> str:
        """
        Ekstraktuje sentyment rynkowy z tekstu.
        
        Args:
            text: Tekst z analizą rynku
            
        Returns:
            str: Sentyment rynkowy
        """
        # Próba ekstrakcji z JSON
        json_data = self.extract_json(text)
        
        if json_data and "sentiment" in json_data:
            return json_data["sentiment"]
            
        # Wyszukiwanie w tekście
        sentiment_patterns = {
            "bullish": r'bullish|trend wzrostowy|byczo|byczego|wzrost|wzrosty',
            "bearish": r'bearish|trend spadkowy|niedźwiedzi|niedźwiedziego|spadek|spadki',
            "neutral": r'neutral|sideways|boczny|konsolidacja|neutralny'
        }
        
        for sentiment, pattern in sentiment_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return sentiment
                
        # Domyślny sentyment
        return "neutral"
    
    def extract_key_levels(self, text: str) -> Dict[str, List[float]]:
        """
        Ekstraktuje kluczowe poziomy wsparcia i oporu.
        
        Args:
            text: Tekst z analizą rynku
            
        Returns:
            Dict[str, List[float]]: Słownik z poziomami wsparcia i oporu
        """
        result = {
            "support": [],
            "resistance": []
        }
        
        # Próba ekstrakcji z JSON
        json_data = self.extract_json(text)
        
        if json_data and "key_levels" in json_data:
            if "support" in json_data["key_levels"]:
                result["support"] = json_data["key_levels"]["support"]
            if "resistance" in json_data["key_levels"]:
                result["resistance"] = json_data["key_levels"]["resistance"]
            return result
            
        # Wyszukiwanie w tekście
        # Poziomy wsparcia
        support_matches = re.findall(r'wsparcie[:]?\s+([\d\.]+)', text, re.IGNORECASE)
        support_matches += re.findall(r'support[:]?\s+([\d\.]+)', text, re.IGNORECASE)
        
        # Poziomy oporu
        resistance_matches = re.findall(r'opór[:]?\s+([\d\.]+)', text, re.IGNORECASE)
        resistance_matches += re.findall(r'resistance[:]?\s+([\d\.]+)', text, re.IGNORECASE)
        
        # Konwersja do liczb zmiennoprzecinkowych
        if support_matches:
            result["support"] = [float(level) for level in support_matches]
        if resistance_matches:
            result["resistance"] = [float(level) for level in resistance_matches]
            
        return result
    
    def summarize_analysis(self, analysis: str, max_length: int = 150) -> str:
        """
        Tworzy krótkie podsumowanie analizy rynkowej.
        
        Args:
            analysis: Pełny tekst analizy
            max_length: Maksymalna długość podsumowania
            
        Returns:
            str: Skrócone podsumowanie analizy
        """
        # Wyszukiwanie podsumowania
        summary_pattern = r'(?i)(?:podsumowanie|summary|conclusion|wnioski)[\s:]*(.+?)(?=\n\n|\Z)'
        summary_match = re.search(summary_pattern, analysis, re.DOTALL)
        
        if summary_match:
            summary = summary_match.group(1).strip()
            return summary[:max_length] if len(summary) > max_length else summary
        
        # Jeśli nie znaleziono eksplicytnego podsumowania, weź ostatni akapit
        paragraphs = [p.strip() for p in analysis.split('\n\n') if p.strip()]
        if paragraphs:
            paragraph = paragraphs[-1]
            return paragraph[:max_length] if len(paragraph) > max_length else paragraph
            
        # Jeśli nie ma akapitów, weź ostatnie zdanie
        sentences = [s.strip() for s in analysis.split('.') if s.strip()]
        if sentences:
            sentence = sentences[-1] + '.'
            return sentence[:max_length] if len(sentence) > max_length else sentence
            
        # Ostateczność - zwróć skrócony tekst
        return analysis[:max_length] + '...' if len(analysis) > max_length else analysis
    
    def postprocess_response(self, response: str) -> Dict[str, Any]:
        """
        Przetwarza odpowiedź analizy rynku z modelu LLM.
        
        Args:
            response: Odpowiedź z modelu LLM
            
        Returns:
            Dict[str, Any]: Przetworzona analiza rynku
        """
        # Ekstrakcja JSON z tekstu
        json_data = self.extract_json(response)
        
        if not json_data:
            logger.warning("Nie znaleziono danych JSON w odpowiedzi")
            json_data = {}
        
        # Dodanie metadanych
        result = json_data.copy()
        result["timestamp"] = datetime.now().isoformat()
        result["raw_response"] = response
        
        # Dodanie podsumowania
        if "analysis" in result:
            result["summary"] = self.summarize_analysis(result["analysis"])
        else:
            # Próba wygenerowania podsumowania z tekstu odpowiedzi
            result["summary"] = self.summarize_analysis(response)
        
        # Zapisanie przetworzonej odpowiedzi
        self.processed_response = result
        
        return result


class TradingSignalPostprocessor(LLMPostprocessor):
    """
    Postprocesor dla sygnałów handlowych z modeli LLM.
    """
    
    def __init__(self):
        """Inicjalizacja postprocesora sygnałów handlowych."""
        super().__init__()
        logger.debug("Inicjalizacja TradingSignalPostprocessor")
        self.expected_schema = {
            "type": "object",
            "properties": {
                "action": {"type": "string"},
                "pair": {"type": "string"},
                "entry_price": {"type": "number"},
                "stop_loss": {"type": "number"},
                "take_profit": {"type": "number"},
                "confidence": {"type": "number"}
            },
            "required": ["action", "pair", "entry_price", "stop_loss", "take_profit"]
        }
    
    def extract_trade_parameters(self, text: str) -> Dict[str, Any]:
        """
        Ekstrahuje parametry transakcji z tekstu.
        
        Args:
            text: Tekst odpowiedzi zawierający parametry transakcji
            
        Returns:
            Dict[str, Any]: Słownik z parametrami transakcji
        """
        # Inicjalizacja słownika wynikowego
        trade_params = {}
        
        # Najpierw próbujemy ekstrakcji JSON
        try:
            json_processor = JSONResponsePostprocessor()
            json_data = json_processor.extract_json_from_text(text)
            
            # Jeśli udało się wyodrębnić JSON, używamy go jako podstawy
            trade_params.update(json_data)
            logger.debug("Znaleziono parametry transakcji w formacie JSON")
            
            # Jeśli już mamy podstawowe pola, zwracamy wynik
            if all(k in trade_params for k in ["signal", "entry", "stop_loss", "take_profit"]):
                return trade_params
                
        except ValueError:
            logger.debug("Nie znaleziono parametrów transakcji w formacie JSON, próba ekstrakcji za pomocą wyrażeń regularnych")
        
        # Ekstrakcja kierunku transakcji (BUY/SELL)
        signal_pattern = r'(?i)(?:sygnał|signal|action|kierunek)\s*[:-]\s*([A-Za-z]+)'
        signal_match = re.search(signal_pattern, text)
        if signal_match:
            signal = signal_match.group(1).upper()
            if signal in ["BUY", "LONG", "KUPNO", "KUPUJ"]:
                trade_params["signal"] = "BUY"
            elif signal in ["SELL", "SHORT", "SPRZEDAŻ", "SPRZEDAJ"]:
                trade_params["signal"] = "SELL"
            else:
                trade_params["signal"] = "WAIT"
        
        # Ekstrakcja pary walutowej
        pair_pattern = r'(?i)(?:para|pair|instrument|symbol)\s*[:-]\s*([A-Za-z0-9/]+)'
        pair_match = re.search(pair_pattern, text)
        if pair_match:
            trade_params["pair"] = pair_match.group(1).upper()
        
        # Ekstrakcja ceny wejścia
        entry_pattern = r'(?i)(?:wejście|cena wejścia|entry|entry price)\s*[:-]\s*([\d.]+)'
        entry_match = re.search(entry_pattern, text)
        if entry_match:
            trade_params["entry"] = float(entry_match.group(1))
        
        # Ekstrakcja stop loss
        sl_pattern = r'(?i)(?:stop loss|sl)\s*[:-]\s*([\d.]+)'
        sl_match = re.search(sl_pattern, text)
        if sl_match:
            trade_params["stop_loss"] = float(sl_match.group(1))
        
        # Ekstrakcja take profit
        tp_pattern = r'(?i)(?:take profit|tp)\s*[:-]\s*([\d.]+)'
        tp_match = re.search(tp_pattern, text)
        if tp_match:
            trade_params["take_profit"] = float(tp_match.group(1))
        
        # Ekstrakcja poziomu ufności
        confidence_pattern = r'(?i)(?:pewność|confidence|poziom ufności)\s*[:-]\s*([A-Za-z]+|\d+%?)'
        confidence_match = re.search(confidence_pattern, text)
        if confidence_match:
            confidence = confidence_match.group(1).lower()
            # Konwersja słownego określenia na wartość liczbową
            if confidence in ["wysoka", "high", "strong"]:
                trade_params["confidence"] = "high"
            elif confidence in ["średnia", "medium", "moderate"]:
                trade_params["confidence"] = "medium"
            elif confidence in ["niska", "low", "weak"]:
                trade_params["confidence"] = "low"
            else:
                # Jeśli podano wartość procentową
                percent_match = re.search(r'(\d+)%?', confidence)
                if percent_match:
                    percent = int(percent_match.group(1))
                    if percent >= 75:
                        trade_params["confidence"] = "high"
                    elif percent >= 40:
                        trade_params["confidence"] = "medium"
                    else:
                        trade_params["confidence"] = "low"
                else:
                    trade_params["confidence"] = confidence
        
        # Ekstrakcja uzasadnienia
        rationale_pattern = r'(?i)(?:uzasadnienie|rationale|reason|explanation)\s*[:-]\s*([\s\S]+?)(?=\n\n|\Z)'
        rationale_match = re.search(rationale_pattern, text)
        if rationale_match:
            trade_params["rationale"] = rationale_match.group(1).strip()
        
        return trade_params
    
    def validate_trade_signal(self, trade_params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Waliduje parametry sygnału handlowego.
        
        Args:
            trade_params: Parametry sygnału handlowego
            
        Returns:
            Tuple[bool, List[str]]: (Czy sygnał jest poprawny, lista błędów)
        """
        errors = []
        
        # Sprawdzenie wymaganych pól
        required_fields = ["signal"]
        if "action" in trade_params and "signal" not in trade_params:
            trade_params["signal"] = trade_params["action"]
            
        missing_fields = [field for field in required_fields if field not in trade_params]
        
        if missing_fields:
            logger.warning(f"Brak wymaganych pól: {', '.join(missing_fields)}")
            errors.append(f"Missing required fields: {', '.join(missing_fields)}")
            return False, errors
        
        # Walidacja kierunku transakcji
        signal = trade_params.get("signal", "").upper()
        if signal not in ["BUY", "SELL", "WAIT"]:
            logger.warning(f"Nieprawidłowy sygnał: {signal}")
            errors.append(f"Invalid signal value: {signal}")
            return False, errors
        
        # Jeśli sygnał to WAIT, nie potrzebujemy więcej walidacji
        if signal == "WAIT":
            return True, []
        
        # Sprawdzenie spójności poziomów cenowych dla sygnału BUY
        if signal == "BUY":
            entry = trade_params.get("entry_price")
            stop_loss = trade_params.get("stop_loss")
            take_profit = trade_params.get("take_profit")
            
            if all([entry, stop_loss, take_profit]):
                # Dla BUY: stop_loss < entry < take_profit
                if not (stop_loss < entry < take_profit):
                    logger.warning(f"Niespójne poziomy cenowe dla BUY: SL={stop_loss}, Entry={entry}, TP={take_profit}")
                    errors.append("Invalid price levels for BUY signal")
                    return False, errors
        
        # Sprawdzenie spójności poziomów cenowych dla sygnału SELL
        elif signal == "SELL":
            entry = trade_params.get("entry_price")
            stop_loss = trade_params.get("stop_loss")
            take_profit = trade_params.get("take_profit")
            
            if all([entry, stop_loss, take_profit]):
                # Dla SELL: take_profit < entry < stop_loss
                if not (take_profit < entry < stop_loss):
                    logger.warning(f"Niespójne poziomy cenowe dla SELL: TP={take_profit}, Entry={entry}, SL={stop_loss}")
                    errors.append("Invalid price levels for SELL signal")
                    return False, errors
        
        return True, []

    def calculate_risk_reward_ratio(self, params: Dict[str, Any] = None, entry: float = None, stop_loss: float = None, take_profit: float = None, signal: str = None) -> float:
        """
        Oblicza stosunek zysku do ryzyka (RR).
        
        Args:
            params: Opcjonalny słownik z parametrami transakcji
            entry: Cena wejścia
            stop_loss: Poziom stop loss
            take_profit: Poziom take profit
            signal: Kierunek transakcji ("BUY" lub "SELL")
            
        Returns:
            float: Stosunek zysku do ryzyka
        """
        # Jeśli podano słownik z parametrami, ekstrahuj z niego wartości
        if params is not None:
            entry = params.get("entry_price")
            stop_loss = params.get("stop_loss")
            take_profit = params.get("take_profit")
            signal = params.get("signal") or params.get("action")
        
        # Sprawdzenie wymaganych danych
        if not all([entry, stop_loss, take_profit, signal]):
            logger.warning("Brak wymaganych danych do obliczenia stosunku RR")
            return 0.0
        
        # Konwersja wejść na liczby (na wszelki wypadek)
        try:
            entry = float(entry)
            stop_loss = float(stop_loss)
            take_profit = float(take_profit)
        except (ValueError, TypeError):
            logger.error("Nieprawidłowe dane wejściowe do obliczenia stosunku RR")
            return 0.0
        
        # Obliczenie ryzyka i potencjalnego zysku
        risk = 0.0
        reward = 0.0
        
        signal = signal.upper()
        if signal in ["BUY", "LONG"]:
            risk = entry - stop_loss
            reward = take_profit - entry
        elif signal in ["SELL", "SHORT"]:
            risk = stop_loss - entry
            reward = entry - take_profit
        else:
            logger.warning(f"Nieznany kierunek transakcji: {signal}")
            return 0.0
        
        # Ochrona przed dzieleniem przez zero
        if risk <= 0:
            logger.warning("Nieprawidłowe ryzyko (mniejsze lub równe zero)")
            return 0.0
        
        # Obliczenie stosunku
        risk_reward_ratio = reward / risk
        
        return round(risk_reward_ratio, 2)
    
    def enrich_trade_signal(self, trade_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wzbogaca sygnał handlowy o dodatkowe informacje.
        
        Args:
            trade_params: Parametry handlowe do wzbogacenia
            
        Returns:
            Dict[str, Any]: Wzbogacony sygnał handlowy
        """
        enriched = trade_params.copy()
        
        # Dodanie znormalizowanego pola 'signal' jeśli jest 'action'
        if "action" in enriched and not "signal" in enriched:
            enriched["signal"] = enriched["action"]
            
        # Obliczenie stosunku ryzyka do nagrody
        if all(key in enriched for key in ["entry_price", "stop_loss", "take_profit"]):
            enriched["risk_reward_ratio"] = self.calculate_risk_reward_ratio(
                entry=enriched["entry_price"], 
                stop_loss=enriched["stop_loss"], 
                take_profit=enriched["take_profit"],
                signal=enriched.get("signal") or enriched.get("action")
            )
        
        # Dodanie wartości pip
        if "pair" in enriched:
            pair = enriched["pair"].upper()
            # Domyślna wartość pip dla głównych par walutowych
            if pair.endswith("JPY"):
                pip_value = 0.01  # Dla par z JPY
            else:
                pip_value = 0.0001  # Dla innych par
                
            enriched["pip_value"] = pip_value
            
        # Dodanie timestampu
        enriched["timestamp"] = datetime.now().isoformat()
        
        return enriched
    
    def postprocess_response(self, response: str) -> Dict[str, Any]:
        """
        Przetwarza odpowiedź zawierającą sygnał handlowy.
        
        Args:
            response: Odpowiedź z modelu LLM
            
        Returns:
            Dict[str, Any]: Przetworzony sygnał handlowy
        """
        # Ekstrakcja tekstu z odpowiedzi
        text = self.extract_text_from_response(response)
        
        # Czyszczenie tekstu
        cleaned_text = self.clean_response(text)
        
        try:
            # Ekstrakcja parametrów transakcji
            trade_params = self.extract_trade_parameters(cleaned_text)
            
            # Walidacja sygnału
            is_valid, errors = self.validate_trade_signal(trade_params)
            
            if is_valid:
                # Wzbogacenie sygnału
                trade_signal = self.enrich_trade_signal(trade_params)
                
                logger.info(f"Pomyślnie przetworzono sygnał handlowy: {trade_signal['signal']}")
                self.processed_response = trade_signal
                return trade_signal
            else:
                logger.warning("Nieprawidłowy sygnał handlowy")
                error_response = {
                    "error": "Nieprawidłowy sygnał handlowy",
                    "raw_signal": trade_params,
                    "raw_response": response,
                    "errors": errors
                }
                self.processed_response = error_response
                return error_response
                
        except Exception as e:
            logger.error(f"Błąd podczas przetwarzania sygnału handlowego: {str(e)}")
            error_response = {
                "error": str(e),
                "raw_response": response
            }
            self.processed_response = error_response
            return error_response 


class JSONResponsePostprocessor(LLMPostprocessor):
    """
    Postprocesor odpowiedzi w formacie JSON.
    """
    
    def __init__(self, schema: Dict[str, Any] = None):
        """
        Inicjalizacja postprocesora odpowiedzi JSON.
        
        Args:
            schema: Schemat walidacji JSON (opcjonalny)
        """
        super().__init__()
        self.expected_schema = schema or {}
        logger.debug("Inicjalizacja JSONResponsePostprocessor")
        
    def set_expected_schema(self, schema: Dict[str, Any]):
        """
        Ustawia schemat walidacji.
        
        Args:
            schema: Schemat walidacji JSON
        """
        self.expected_schema = schema
        
    def fix_common_json_errors(self, json_str: str) -> str:
        """
        Naprawia częste błędy w JSON.
        
        Args:
            json_str: String JSON z możliwymi błędami
            
        Returns:
            str: Naprawiony string JSON
        """
        # Naprawianie braku cudzysłowów przy kluczach
        fixed = re.sub(r'(?<={|,)\s*(\w+):', r'"\1":', json_str)
        
        # Usuwanie przecinka przed końcowym nawiasem
        fixed = re.sub(r',\s*}', r'}', fixed)
        
        # Usuwanie podwójnych przecinków
        fixed = re.sub(r',,', r',', fixed)
        
        return fixed
    
    def postprocess_response(self, response: str) -> Dict[str, Any]:
        """
        Przetwarza odpowiedź JSON z modelu LLM.
        
        Args:
            response: Odpowiedź z modelu LLM
            
        Returns:
            Dict[str, Any]: Przetworzona odpowiedź JSON
        """
        # Ekstrakcja JSON z tekstu
        json_data = self.extract_json_from_text(response)
        
        # Walidacja schematu
        if self.expected_schema and json_data:
            is_valid = self.validate_json_schema(json_data)
            if not is_valid:
                logger.warning("JSON nie jest zgodny z oczekiwanym schematem")
        
        # Zapisanie przetworzonej odpowiedzi
        self.processed_response = json_data
        
        # Dodanie metadanych
        result = json_data.copy() if json_data else {}
        result["timestamp"] = datetime.now().isoformat()
        result["raw_response"] = response
        
        return result
    
    def extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """
        Ekstrahuje dane JSON z tekstu.
        
        Args:
            text: Tekst, który może zawierać JSON
            
        Returns:
            Dict[str, Any]: Dane JSON
            
        Raises:
            ValueError: Jeśli nie można znaleźć lub sparsować JSON
        """
        # Próba znalezienia bloku JSON za pomocą wyrażeń regularnych
        json_pattern = r'```(?:json)?\s*({[\s\S]*?})\s*```|({[\s\S]*?})'
        matches = re.findall(json_pattern, text)
        
        # Sprawdź wszystkie potencjalne dopasowania
        for match_groups in matches:
            for potential_json in match_groups:
                if potential_json.strip():
                    try:
                        return json.loads(potential_json)
                    except json.JSONDecodeError:
                        continue
        
        # Jeśli nie znaleziono JSON w blokach kodu, próbujemy parsować cały tekst
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            # Ostatnia próba - szukamy dowolnych nawiasów klamrowych
            try:
                start_idx = text.find('{')
                end_idx = text.rfind('}')
                
                if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                    potential_json = text[start_idx:end_idx+1]
                    return json.loads(potential_json)
                    
                raise ValueError("Nie znaleziono poprawnego formatu JSON w odpowiedzi")
            except json.JSONDecodeError:
                raise ValueError("Nie można sparsować JSON z tekstu")
    
    def validate_json_schema(self, data: Dict[str, Any], schema: Dict[str, Any] = None) -> bool:
        """
        Waliduje dane JSON wg schematu.
        
        Args:
            data: Dane JSON do walidacji
            schema: Schemat walidacji (opcjonalny, użyje expected_schema jeśli nie podano)
            
        Returns:
            bool: Czy dane są zgodne ze schematem
        """
        schema = schema or self.expected_schema
        
        # Jeśli nie mamy schematu, zakładamy, że dane są poprawne
        if not schema:
            return True
            
        try:
            jsonschema.validate(instance=data, schema=schema)
            return True
        except jsonschema.exceptions.ValidationError as e:
            logger.warning(f"Błąd walidacji JSON: {str(e)}")
            return False
    
    def format_for_display(self, data: Dict[str, Any]) -> str:
        """
        Formatuje dane JSON do wyświetlenia.
        
        Args:
            data: Dane JSON
            
        Returns:
            str: Sformatowany tekst
        """
        # Usunięcie metadanych przed formatowaniem
        display_data = data.copy()
        
        if "raw_response" in display_data:
            del display_data["raw_response"]
            
        if "timestamp" in display_data:
            del display_data["timestamp"]
            
        # Formatowanie do czytelnego JSON
        try:
            return json.dumps(display_data, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Błąd podczas formatowania JSON: {str(e)}")
            return str(display_data) 
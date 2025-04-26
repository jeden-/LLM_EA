"""
Funkcje pomocnicze dla silnika LLM.
"""
import os
import re
import json
import logging
from typing import Dict, Any, Optional, List, Union, Tuple

# Konfiguracja loggera
logger = logging.getLogger(__name__)

def load_prompt_template(template_path: str) -> str:
    """
    Ładuje szablon promptu z pliku.
    
    Args:
        template_path: Ścieżka do pliku z szablonem
        
    Returns:
        Zawartość szablonu jako string
    
    Raises:
        FileNotFoundError: Gdy plik szablonu nie istnieje
    """
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Nie znaleziono pliku szablonu: {template_path}")
        raise FileNotFoundError(f"Szablon promptu nie istnieje: {template_path}")

def format_prompt(template: str, variables: Dict[str, Any]) -> str:
    """
    Formatuje szablon promptu, podstawiając zmienne.
    
    Args:
        template: Szablon promptu z placeholderami w formacie {nazwa_zmiennej}
        variables: Słownik zmiennych do podstawienia
        
    Returns:
        Sformatowany prompt
        
    Raises:
        KeyError: Gdy brakuje wymaganej zmiennej
    """
    try:
        return template.format(**variables)
    except KeyError as e:
        logger.error(f"Brakująca zmienna w szablonie promptu: {e}")
        raise KeyError(f"Brakująca zmienna w szablonie promptu: {e}")

def extract_json_from_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Wyciąga obiekt JSON z tekstu odpowiedzi.
    
    Args:
        response_text: Tekst odpowiedzi, który może zawierać JSON
        
    Returns:
        Sparsowany obiekt JSON lub None, jeśli nie znaleziono poprawnego JSON
    """
    from LLM_Engine.response_parser import ResponseParserFactory
    
    try:
        # Użyj parsera JSON z fabryki
        parser = ResponseParserFactory.get_parser("json")
        result = parser.parse(response_text)
        
        if result:
            return result
        return None
        
    except Exception as e:
        logger.error(f"Błąd podczas parsowania JSON: {str(e)}")
        return None

def parse_llm_response(response: Dict[str, Any]) -> str:
    """
    Parsuje odpowiedź z API LLM.
    
    Args:
        response: Odpowiedź z API LLM
        
    Returns:
        Wyciągnięty tekst odpowiedzi
        
    Raises:
        ValueError: Gdy format odpowiedzi jest nieznany lub niepoprawny
    """
    # Sprawdzenie formatu odpowiedzi Ollama
    if "response" in response:
        return response["response"]
    
    # Obsługa formatu OpenAI
    if "choices" in response:
        choices = response["choices"]
        if choices and len(choices) > 0:
            choice = choices[0]
            if "message" in choice and "content" in choice["message"]:
                return choice["message"]["content"]
            elif "text" in choice:
                return choice["text"]
    
    # Obsługa formatu Claude/Anthropic
    if "content" in response:
        return response["content"]
    
    # Jeśli nic nie pasuje, logujemy ostrzeżenie i zwracamy pusty string
    logger.warning(f"Nieznany format odpowiedzi LLM: {response}")
    return ""

def prepare_conversation_history(messages: List[Dict[str, str]]) -> str:
    """
    Przygotowuje historię konwersacji w formacie tekstowym.
    
    Args:
        messages: Lista wiadomości w formacie [{"role": "user|assistant|system", "content": "treść"}]
        
    Returns:
        Sformatowana historia konwersacji jako tekst
    """
    formatted_history = []
    
    for msg in messages:
        role = msg.get("role", "").lower()
        content = msg.get("content", "")
        
        if role == "user":
            formatted_history.append(f"Użytkownik: {content}")
        elif role == "assistant":
            formatted_history.append(f"Asystent: {content}")
        elif role == "system":
            formatted_history.append(f"System: {content}")
        else:
            formatted_history.append(f"{role.capitalize()}: {content}")
    
    return "\n\n".join(formatted_history)

def get_token_count(text: str) -> int:
    """
    Szacuje liczbę tokenów w tekście.
    
    To jest prosta implementacja - dla dokładniejszych wyników 
    należy użyć odpowiedniego tokenizera dla danego modelu.
    
    Args:
        text: Tekst do analizy
        
    Returns:
        Przybliżona liczba tokenów
    """
    # Prosta heurystyka: około 4 znaki = 1 token (dla języka angielskiego)
    # Dla języka polskiego może być nieco mniej wydajne
    return len(text) // 4

def truncate_text(text: str, max_tokens: int) -> str:
    """
    Obcina tekst do określonej liczby tokenów.
    
    Args:
        text: Tekst do obcięcia
        max_tokens: Maksymalna liczba tokenów
        
    Returns:
        Obcięty tekst
    """
    if get_token_count(text) <= max_tokens:
        return text
    
    # Prosta implementacja - obcina na podstawie szacowanej liczby znaków
    # ~4 znaki na token
    char_limit = max_tokens * 4
    return text[:char_limit] + "..." 

def parse_trading_advice(response_text: str) -> Dict[str, Any]:
    """
    Parsuje odpowiedź LLM zawierającą porady tradingowe.
    
    Args:
        response_text: Tekst odpowiedzi z LLM
        
    Returns:
        Słownik zawierający sparsowane porady tradingowe z następującymi kluczami:
        - action: Akcja (BUY, SELL, HOLD)
        - symbol: Symbol instrumentu
        - entry_price: Sugerowana cena wejścia (opcjonalne)
        - stop_loss: Sugerowany poziom stop loss (opcjonalne)
        - take_profit: Sugerowany poziom take profit (opcjonalne)
        - timeframe: Horyzont czasowy (opcjonalne)
        - confidence: Poziom pewności (0-100) (opcjonalne)
        - reasoning: Uzasadnienie (opcjonalne)
        
    Raises:
        ValueError: Gdy nie udało się sparsować niezbędnych informacji
    """
    # Najpierw próbujemy wyciągnąć JSON, jeśli istnieje
    json_data = extract_json_from_response(response_text)
    if json_data:
        # Sprawdzamy czy mamy wszystkie wymagane pola
        if "action" in json_data and "symbol" in json_data:
            # Dodajemy domyślne wartości dla opcjonalnych pól, jeśli nie istnieją
            result = {
                "action": json_data.get("action", "").upper(),
                "symbol": json_data.get("symbol", ""),
                "entry_price": json_data.get("entry_price"),
                "stop_loss": json_data.get("stop_loss"),
                "take_profit": json_data.get("take_profit"),
                "timeframe": json_data.get("timeframe"),
                "confidence": json_data.get("confidence"),
                "reasoning": json_data.get("reasoning", "")
            }
            logger.info(f"Sparsowano poradę tradingową z JSON: {result}")
            return result
    
    # Jeśli nie ma JSON lub jest niekompletny, próbujemy wyciągnąć dane z tekstu
    # Szukamy typowych wzorców w tekście odpowiedzi
    
    # Wzorce dla akcji
    action_pattern = r"(?:działanie|akcja|decyzja)[\s:]*(?:jest|to)?[\s:]*(BUY|SELL|HOLD|KUPUJ|SPRZEDAJ|TRZYMAJ)"
    action_match = re.search(action_pattern, response_text, re.IGNORECASE)
    
    # Wzorce dla symbolu
    symbol_pattern = r"(?:symbol|instrument|para|waluta)[\s:]*([A-Z0-9]{2,10}(?:/[A-Z0-9]{2,10})?)"
    symbol_match = re.search(symbol_pattern, response_text, re.IGNORECASE)
    
    # Kontynuujemy tylko jeśli znaleziono przynajmniej akcję i symbol
    if action_match and symbol_match:
        action = action_match.group(1).upper()
        # Mapowanie polskich akcji na angielskie
        if action == "KUPUJ":
            action = "BUY"
        elif action == "SPRZEDAJ":
            action = "SELL"
        elif action == "TRZYMAJ":
            action = "HOLD"
            
        symbol = symbol_match.group(1).upper()
        
        # Próbujemy znaleźć pozostałe informacje
        entry_price_pattern = r"(?:cena wejścia|entry price|wejście)[\s:]*([0-9]+(?:[.,][0-9]+)?)"
        entry_price_match = re.search(entry_price_pattern, response_text, re.IGNORECASE)
        entry_price = float(entry_price_match.group(1).replace(',', '.')) if entry_price_match else None
        
        stop_loss_pattern = r"(?:stop loss|stop-loss|sl)[\s:]*([0-9]+(?:[.,][0-9]+)?)"
        stop_loss_match = re.search(stop_loss_pattern, response_text, re.IGNORECASE)
        stop_loss = float(stop_loss_match.group(1).replace(',', '.')) if stop_loss_match else None
        
        take_profit_pattern = r"(?:take profit|take-profit|tp)[\s:]*([0-9]+(?:[.,][0-9]+)?)"
        take_profit_match = re.search(take_profit_pattern, response_text, re.IGNORECASE)
        take_profit = float(take_profit_match.group(1).replace(',', '.')) if take_profit_match else None
        
        timeframe_pattern = r"(?:timeframe|okres|tf)[\s:]*([A-Z0-9]+)"
        timeframe_match = re.search(timeframe_pattern, response_text, re.IGNORECASE)
        timeframe = timeframe_match.group(1) if timeframe_match else None
        
        confidence_pattern = r"(?:pewność|confidence|pewnosc)[\s:]*([0-9]+)(?:\s*%|\s*procent)?"
        confidence_match = re.search(confidence_pattern, response_text, re.IGNORECASE)
        confidence = int(confidence_match.group(1)) if confidence_match else None
        
        # Szukamy uzasadnienia - wszystko po "uzasadnienie" lub "reasoning"
        reasoning_pattern = r"(?:uzasadnienie|reasoning|analiza)[\s:]+(.+)(?:$|\n\n)"
        reasoning_match = re.search(reasoning_pattern, response_text, re.IGNORECASE | re.DOTALL)
        reasoning = reasoning_match.group(1).strip() if reasoning_match else ""
        
        result = {
            "action": action,
            "symbol": symbol,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "timeframe": timeframe,
            "confidence": confidence,
            "reasoning": reasoning
        }
        
        logger.info(f"Sparsowano poradę tradingową z tekstu: {result}")
        return result
    
    # Jeśli nie udało się znaleźć wymaganych informacji
    logger.error("Nie udało się sparsować porady tradingowej")
    raise ValueError("Nie udało się wyciągnąć akcji i symbolu z odpowiedzi LLM") 
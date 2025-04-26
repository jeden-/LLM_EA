"""
Moduł formatujący prompty dla modeli LLM.

Ten moduł odpowiada za formatowanie różnych typów promptów do odpowiedniego 
formatu dla modeli językowych, uwzględniając specyficzne wymagania różnych modeli.
"""

import logging
from typing import Dict, List, Any, Optional, Union
import json
import re

# Inicjalizacja loggera
logger = logging.getLogger(__name__)

class PromptFormatter:
    """
    Klasa bazowa formatera promptów.
    
    Odpowiada za formatowanie promptów do odpowiedniego formatu dla różnych modeli LLM.
    """
    
    def __init__(self, model_type: str = "general"):
        """
        Inicjalizacja formatera promptów.
        
        Args:
            model_type: Typ modelu, dla którego formatowane są prompty
        """
        self.model_type = model_type
        self.system_template = ""
        self.user_template = ""
        self.template_variables = {}
        logger.debug(f"Inicjalizacja PromptFormatter dla modelu typu: {model_type}")
    
    def set_system_template(self, template: str):
        """
        Ustawia szablon systemowy.
        
        Args:
            template: Szablon systemowy
        """
        self.system_template = template
        
    def set_user_template(self, template: str):
        """
        Ustawia szablon użytkownika.
        
        Args:
            template: Szablon użytkownika
        """
        self.user_template = template
        
    def add_variable(self, name: str, value: Any):
        """
        Dodaje zmienną do szablonu.
        
        Args:
            name: Nazwa zmiennej
            value: Wartość zmiennej
        """
        self.template_variables[name] = value
        
    def add_variables(self, variables: Dict[str, Any]):
        """
        Dodaje wiele zmiennych do szablonu.
        
        Args:
            variables: Słownik zmiennych do dodania
        """
        self.template_variables.update(variables)
        
    def format(self) -> Dict[str, str]:
        """
        Formatuje prompt z użyciem zdefiniowanych szablonów i zmiennych.
        
        Returns:
            Dict[str, str]: Prompt w formacie {system, user}
        """
        # Formatowanie promptów
        try:
            system_prompt = self.system_template.format(**self.template_variables)
            user_prompt = self.user_template.format(**self.template_variables)
            
            return {
                "system": system_prompt,
                "user": user_prompt
            }
        except KeyError as e:
            raise KeyError(f"Brakująca zmienna w szablonie: {e}")
            
    def reset(self):
        """Resetuje stan formatera do wartości początkowych."""
        self.system_template = ""
        self.user_template = ""
        self.template_variables = {}
    
    def format_prompt(self, system_prompt: str, user_prompt: str) -> str:
        """
        Formatuje prompt dla modelu.
        
        Args:
            system_prompt: Prompt systemowy
            user_prompt: Prompt użytkownika
            
        Returns:
            str: Sformatowany prompt
        """
        # Domyślne formatowanie dla ogólnego modelu
        return f"{system_prompt}\n\n{user_prompt}"
    
    def format_chat_prompt(self, messages: List[Dict[str, str]]) -> Union[str, Dict[str, Any]]:
        """
        Formatuje prompt czatowy dla modelu.
        
        Args:
            messages: Lista wiadomości w formacie [{"role": "system"|"user"|"assistant", "content": "..."}, ...]
            
        Returns:
            Union[str, Dict[str, Any]]: Sformatowany prompt czatowy
        """
        # Domyślne formatowanie dla ogólnego modelu - połącz wiadomości
        formatted_prompt = ""
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                formatted_prompt += f"System: {content}\n\n"
            elif role == "user":
                formatted_prompt += f"User: {content}\n\n"
            elif role == "assistant":
                formatted_prompt += f"Assistant: {content}\n\n"
                
        return formatted_prompt.strip()
    
    def format_data_for_prompt(self, data: Dict[str, Any]) -> str:
        """
        Formatuje dane do użycia w prompcie.
        
        Args:
            data: Słownik z danymi
            
        Returns:
            str: Sformatowane dane
        """
        return json.dumps(data, indent=2)


class OpenAIPromptFormatter(PromptFormatter):
    """
    Formater promptów dla modeli OpenAI.
    """
    
    def __init__(self):
        """Inicjalizacja formatera promptów OpenAI."""
        super().__init__("openai")
    
    def format_prompt(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Formatuje prompt dla modeli OpenAI.
        
        Args:
            system_prompt: Prompt systemowy
            user_prompt: Prompt użytkownika
            
        Returns:
            Dict[str, Any]: Prompt w formacie OpenAI
        """
        return {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
    
    def format_chat_prompt(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Formatuje prompt czatowy dla modeli OpenAI.
        
        Args:
            messages: Lista wiadomości
            
        Returns:
            Dict[str, Any]: Prompt czatowy w formacie OpenAI
        """
        # Sprawdzenie, czy wszystkie wiadomości mają poprawny format
        formatted_messages = []
        
        for message in messages:
            if "role" in message and "content" in message:
                role = message["role"]
                if role in ["system", "user", "assistant"]:
                    formatted_messages.append(message)
        
        return {"messages": formatted_messages}


class OllamaPromptFormatter(PromptFormatter):
    """
    Formater promptów dla modeli Ollama.
    """
    
    def __init__(self):
        """Inicjalizacja formatera promptów Ollama."""
        super().__init__("ollama")
    
    def format_prompt(self, system_prompt: str, user_prompt: str) -> str:
        """
        Formatuje prompt dla modeli Ollama.
        
        Args:
            system_prompt: Prompt systemowy
            user_prompt: Prompt użytkownika
            
        Returns:
            str: Prompt w formacie Ollama
        """
        return f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n{user_prompt} [/INST]"
    
    def format_chat_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        Formatuje prompt czatowy dla modeli Ollama.
        
        Args:
            messages: Lista wiadomości
            
        Returns:
            str: Prompt czatowy w formacie Ollama
        """
        formatted_prompt = ""
        system_prompt = ""
        
        # Znajdź prompt systemowy
        for message in messages:
            if message.get("role") == "system":
                system_prompt = message.get("content", "")
                break
        
        # Dodaj prompt systemowy
        if system_prompt:
            formatted_prompt = f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n"
        else:
            formatted_prompt = "<s>[INST] "
        
        # Dodaj konwersację
        conversation = []
        for message in messages:
            role = message.get("role")
            content = message.get("content", "")
            
            if role == "system":
                continue  # Już dodany wcześniej
            elif role == "user":
                conversation.append(content)
            elif role == "assistant":
                conversation.append(f"[/INST] {content} </s><s>[INST] ")
        
        # Połącz konwersację
        formatted_prompt += " ".join(conversation)
        
        # Zamknij prompt
        if formatted_prompt.endswith("<s>[INST] "):
            formatted_prompt = formatted_prompt[:-10]
        else:
            formatted_prompt += " [/INST]"
        
        return formatted_prompt


class AnthropicPromptFormatter(PromptFormatter):
    """
    Formater promptów dla modeli Anthropic.
    """
    
    def __init__(self):
        """Inicjalizacja formatera promptów Anthropic."""
        super().__init__("anthropic")
    
    def format_prompt(self, system_prompt: str, user_prompt: str) -> str:
        """
        Formatuje prompt dla modeli Anthropic.
        
        Args:
            system_prompt: Prompt systemowy
            user_prompt: Prompt użytkownika
            
        Returns:
            str: Prompt w formacie Anthropic
        """
        return f"{system_prompt}\n\nHuman: {user_prompt}\n\nAssistant: "
    
    def format_chat_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        Formatuje prompt czatowy dla modeli Anthropic.
        
        Args:
            messages: Lista wiadomości
            
        Returns:
            str: Prompt czatowy w formacie Anthropic
        """
        formatted_prompt = ""
        system_content = ""
        
        # Znajdź i ekstrakcja komunikatu systemowego
        for message in messages:
            if message.get("role") == "system":
                system_content = message.get("content", "")
                break
        
        # Dodaj komunikat systemowy na początku
        if system_content:
            formatted_prompt += f"{system_content}\n\n"
        
        # Dodaj pozostałe wiadomości
        for message in messages:
            role = message.get("role")
            content = message.get("content", "")
            
            if role == "system":
                continue  # Już dodany na początku
            elif role == "user":
                formatted_prompt += f"Human: {content}\n\n"
            elif role == "assistant":
                formatted_prompt += f"Assistant: {content}\n\n"
        
        # Dodaj końcowy znacznik dla asystenta
        if not formatted_prompt.endswith("Assistant: "):
            formatted_prompt += "Assistant: "
        
        return formatted_prompt


class TradingPromptFormatter(PromptFormatter):
    """
    Formater promptów dla zadań tradingowych.
    
    Specjalizuje się w formatowaniu promptów dla różnych zadań związanych z tradingiem.
    """
    
    def __init__(self, model_type: str = "general"):
        """
        Inicjalizacja formatera promptów tradingowych.
        
        Args:
            model_type: Typ modelu, dla którego formatowane są prompty
        """
        super().__init__(model_type)
        self.system_template = "You are a trading expert specializing in financial markets analysis. You excel in technical analysis, fundamental analysis, and generating trading signals."
        logger.debug("Inicjalizacja TradingPromptFormatter")
    
    def format_market_data(self, data: Dict[str, Any]) -> str:
        """
        Formatuje dane rynkowe dla promptu.
        
        Args:
            data: Dane rynkowe
            
        Returns:
            str: Sformatowane dane rynkowe
        """
        formatted_data = "Dane rynkowe:\n"
        
        # Dodanie podstawowych informacji
        if "symbol" in data:
            formatted_data += f"Symbol: {data['symbol']}\n"
        if "timeframe" in data:
            formatted_data += f"Interwał: {data['timeframe']}\n"
            
        # Dodanie danych cenowych
        if "price_data" in data and isinstance(data["price_data"], list) and data["price_data"]:
            formatted_data += "\nDane cenowe (ostatnie 5 świec):\n"
            candles = data["price_data"][-5:]  # Ostatnie 5 świec
            
            for i, candle in enumerate(candles):
                formatted_data += f"Świeca {i+1}: "
                if isinstance(candle, dict):
                    formatted_data += f"O={candle.get('open', 'N/A')}, "
                    formatted_data += f"H={candle.get('high', 'N/A')}, "
                    formatted_data += f"L={candle.get('low', 'N/A')}, "
                    formatted_data += f"C={candle.get('close', 'N/A')}"
                    if "volume" in candle:
                        formatted_data += f", V={candle['volume']}"
                else:
                    formatted_data += f"{candle}"
                formatted_data += "\n"
                
        # Dodanie wskaźników technicznych
        if "indicators" in data and isinstance(data["indicators"], dict):
            formatted_data += "\nWskaźniki techniczne:\n"
            
            for indicator, value in data["indicators"].items():
                formatted_data += f"{indicator}: "
                if isinstance(value, list):
                    # Dla wskaźników z wieloma wartościami, pokaż tylko ostatnią
                    formatted_data += f"{value[-1] if value else 'N/A'}"
                else:
                    formatted_data += f"{value}"
                formatted_data += "\n"
                
        return formatted_data
    
    def format_market_analysis_prompt(self) -> Dict[str, str]:
        """
        Formatuje prompt dla analizy rynku.
        
        Returns:
            Dict[str, str]: Prompt w formacie {system, user}
        """
        # Sprawdzenie wymaganych zmiennych
        required_variables = ["pair", "timeframe"]
        for var in required_variables:
            if var not in self.template_variables:
                raise ValueError(f"Brakująca zmienna: {var}")
                
        # Pobranie zmiennych
        pair = self.template_variables["pair"]
        timeframe = self.template_variables["timeframe"]
        context = self.template_variables.get("context", "")
        
        # Formatowanie promptu użytkownika
        user_prompt = f"Wykonaj analizę techniczną dla pary {pair} na interwale {timeframe}."
        
        if context:
            user_prompt += f"\n\nDodatkowy kontekst: {context}"
            
        return {
            "system": self.system_template,
            "user": user_prompt
        }
    
    def format_trade_signal_prompt(self) -> Dict[str, str]:
        """
        Formatuje prompt dla generowania sygnału handlowego.
        
        Returns:
            Dict[str, str]: Prompt w formacie {system, user}
        """
        # Sprawdzenie wymaganych zmiennych
        required_variables = ["pair", "timeframe"]
        for var in required_variables:
            if var not in self.template_variables:
                raise ValueError(f"Brakująca zmienna: {var}")
                
        # Pobranie zmiennych
        pair = self.template_variables["pair"]
        timeframe = self.template_variables["timeframe"]
        
        # Formatowanie promptu użytkownika
        user_prompt = f"Wygeneruj sygnał handlowy dla pary {pair} na interwale {timeframe}."
        
        # Dodanie wskaźników technicznych
        indicators = []
        if "rsi" in self.template_variables:
            indicators.append(f"RSI: {self.template_variables['rsi']}")
        if "macd" in self.template_variables:
            indicators.append(f"MACD: {self.template_variables['macd']}")
        if "ema" in self.template_variables:
            indicators.append(f"EMA: {self.template_variables['ema']}")
            
        if indicators:
            user_prompt += "\n\nDodatkowe informacje:\n" + "\n".join(indicators)
            
        return {
            "system": self.system_template,
            "user": user_prompt
        }
    
    def format_risk_assessment_prompt(self) -> Dict[str, str]:
        """
        Formatuje prompt dla oceny ryzyka.
        
        Returns:
            Dict[str, str]: Prompt w formacie {system, user}
        """
        # Sprawdzenie wymaganych zmiennych
        required_variables = ["pair", "direction", "entry_price", "stop_loss", "take_profit", "account_balance"]
        for var in required_variables:
            if var not in self.template_variables:
                raise ValueError(f"Brakująca zmienna: {var}")
                
        # Pobranie zmiennych
        pair = self.template_variables["pair"]
        direction = self.template_variables["direction"]
        entry_price = self.template_variables["entry_price"]
        stop_loss = self.template_variables["stop_loss"]
        take_profit = self.template_variables["take_profit"]
        account_balance = self.template_variables["account_balance"]
        risk_percentage = self.template_variables.get("risk_percentage", 2)
        
        # Formatowanie promptu użytkownika
        user_prompt = f"Assess the risk and recommended position size for the following trade:\n\n"
        user_prompt += f"Pair: {pair}\n"
        user_prompt += f"Direction: {direction}\n"
        user_prompt += f"Entry Price: {entry_price}\n"
        user_prompt += f"Stop Loss: {stop_loss}\n"
        user_prompt += f"Take Profit: {take_profit}\n"
        user_prompt += f"Account Balance: {account_balance}\n"
        user_prompt += f"Risk Percentage: {risk_percentage}%"
        
        return {
            "system": self.system_template,
            "user": user_prompt
        }


class ConversationFormatter:
    """
    Formater do tworzenia i formatowania konwersacji dla modeli LLM.
    
    Pozwala na tworzenie wieloturowych konwersacji w formacie odpowiednim dla modeli LLM.
    """
    
    def __init__(self):
        """Inicjalizacja formatera konwersacji."""
        self.system_template = ""
        self.messages = []
        logger.debug("Inicjalizacja ConversationFormatter")
        
    def set_system_message(self, message: str):
        """
        Ustawia wiadomość systemową.
        
        Args:
            message: Treść wiadomości systemowej
        """
        self.system_template = message
        
    def add_user_message(self, message: str):
        """
        Dodaje wiadomość użytkownika do konwersacji.
        
        Args:
            message: Treść wiadomości użytkownika
        """
        self.messages.append({"role": "user", "content": message})
        
    def add_assistant_message(self, message: str):
        """
        Dodaje wiadomość asystenta do konwersacji.
        
        Args:
            message: Treść wiadomości asystenta
        """
        self.messages.append({"role": "assistant", "content": message})
        
    def format_conversation(self) -> List[Dict[str, str]]:
        """
        Formatuje konwersację do formatu odpowiedniego dla modeli LLM.
            
        Returns:
            List[Dict[str, str]]: Lista wiadomości w formacie konwersacji
        """
        formatted_conversation = []
        
        # Dodanie wiadomości systemowej
        if self.system_template:
            formatted_conversation.append({"role": "system", "content": self.system_template})
            
        # Dodanie pozostałych wiadomości
        formatted_conversation.extend(self.messages)
        
        return formatted_conversation
        
    def get_last_n_messages(self, n: int) -> List[Dict[str, str]]:
        """
        Pobiera ostatnie n wiadomości z konwersacji.
        
        Args:
            n: Liczba wiadomości do pobrania
            
        Returns:
            List[Dict[str, str]]: Ostatnie n wiadomości
        """
        return self.messages[-n:] if n < len(self.messages) else self.messages
        
    def clear_messages(self):
        """Czyści wszystkie wiadomości, zachowując wiadomość systemową."""
        self.messages = []
        

class JSONOutputFormatter(PromptFormatter):
    """
    Formater specjalizujący się w tworzeniu promptów z instrukcją zwracania JSON.
    
    Dodaje odpowiednie instrukcje i schemat, aby model zwracał dane w formacie JSON.
    """
    
    def __init__(self):
        """Inicjalizacja formatera JSON."""
        super().__init__(model_type="json")
        self.json_schema = {}
        self.system_template = "Process the data and return the response in JSON format."
        self.template_variables = {}
        logger.debug("Inicjalizacja JSONOutputFormatter")
        
    def set_json_schema(self, schema: Dict[str, Any]):
        """
        Ustawia schemat JSON dla odpowiedzi.
        
        Args:
            schema: Schemat JSON
        """
        self.json_schema = schema
        
    def set_system_template(self, template: str):
        """
        Ustawia szablon systemowy.
        
        Args:
            template: Szablon systemowy
        """
        self.system_template = template
        
    def add_variables(self, variables: Dict[str, Any]):
        """
        Dodaje wiele zmiennych do szablonu.
        
        Args:
            variables: Słownik zmiennych do dodania
        """
        self.template_variables.update(variables)
        
    def format_json_prompt(self, instruction: str, data: Dict[str, Any] = None) -> Dict[str, str]:
        """
        Formatuje prompt z instrukcją zwracania JSON.
        
        Args:
            instruction: Instrukcja dla modelu
            data: Dane wejściowe
            
        Returns:
            Dict[str, str]: Prompt w formacie {system, user}
        """
        # Jeśli nie podano danych wejściowych, użyj zmiennych szablonu
        if data is None:
            data = self.template_variables
        
        # Formatowanie danych wejściowych
        formatted_data = json.dumps(data, ensure_ascii=False, indent=2)
        
        # Podstawowy system prompt
        system_prompt = self.system_template
        
        # Dodanie informacji o schemacie, jeśli jest dostępny
        if self.json_schema:
            schema_json = json.dumps(self.json_schema, ensure_ascii=False, indent=2)
            system_prompt += f"\n\nReturn the response according to this JSON schema:\n```json\n{schema_json}\n```"
        
        # Formatowanie instrukcji i danych
        user_prompt = instruction
        if data:
            user_prompt += f"\n\nInput data:\n```json\n{formatted_data}\n```"
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }

class PromptFormatterFactory:
    """
    Fabryka formaterów promptów.
    """
    
    @staticmethod
    def get_formatter(model_type: str) -> PromptFormatter:
        """
        Zwraca odpowiedni formater promptów dla danego typu modelu.
        
        Args:
            model_type: Typ modelu ("openai", "ollama", "anthropic", "general")
            
        Returns:
            PromptFormatter: Odpowiedni formater promptów
        """
        model_type = model_type.lower()
        
        if model_type == "openai":
            return OpenAIPromptFormatter()
        elif model_type == "ollama":
            return OllamaPromptFormatter()
        elif model_type == "anthropic":
            return AnthropicPromptFormatter()
        else:
            return PromptFormatter("general") 
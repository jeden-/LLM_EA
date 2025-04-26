"""
Moduł zarządzania promptami dla modeli LLM.

Ten moduł odpowiada za zarządzanie i przygotowywanie promptów dla różnych 
typów modeli LLM, w tym ładowanie szablonów, wypełnianie zmiennych i 
przechowywanie historii promptów.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union
import re
from datetime import datetime
from jinja2 import Template, Environment, BaseLoader

# Inicjalizacja loggera
logger = logging.getLogger(__name__)

# Inicjalizacja środowiska Jinja2
env = Environment(loader=BaseLoader())

# Funkcje pomocnicze
def load_prompt_template(template_name: str, templates_dir: str = None) -> Dict[str, Any]:
    """
    Ładuje szablon promptu z pliku.
    
    Args:
        template_name: Nazwa szablonu
        templates_dir: Katalog z szablonami (opcjonalny)
        
    Returns:
        Dict[str, Any]: Załadowany szablon
        
    Raises:
        ValueError: Jeśli nie znaleziono szablonu
    """
    # Jeśli nie podano katalogu szablonów, użyj domyślnej ścieżki
    if templates_dir is None:
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        
    # Ścieżka do pliku szablonu
    template_path = os.path.join(templates_dir, f"{template_name}.json")
    
    # Sprawdzenie, czy plik istnieje
    if not os.path.exists(template_path):
        raise ValueError(f"Nie znaleziono szablonu: {template_name}")
        
    # Ładowanie szablonu
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_data = json.load(f)
            
        return template_data
    except Exception as e:
        logger.error(f"Błąd podczas ładowania szablonu {template_name}: {str(e)}")
        raise ValueError(f"Błąd podczas ładowania szablonu: {str(e)}")
        
def save_prompt_template(template: Dict[str, Any], templates_dir: str = None) -> bool:
    """
    Zapisuje szablon promptu do pliku.
    
    Args:
        template: Dane szablonu
        templates_dir: Katalog z szablonami (opcjonalny)
        
    Returns:
        bool: True jeśli operacja się powiodła, False w przeciwnym razie
    """
    # Jeśli nie podano katalogu szablonów, użyj domyślnej ścieżki
    if templates_dir is None:
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        
    # Sprawdzenie wymaganych pól
    if "name" not in template:
        logger.error("Szablon musi zawierać pole 'name'")
        return False
        
    # Utworzenie katalogu, jeśli nie istnieje
    os.makedirs(templates_dir, exist_ok=True)
    
    # Ścieżka do pliku szablonu
    template_path = os.path.join(templates_dir, f"{template['name']}.json")
    
    # Zapisanie szablonu
    try:
        with open(template_path, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Szablon {template['name']} został zapisany")
        return True
    except Exception as e:
        logger.error(f"Błąd podczas zapisywania szablonu {template['name']}: {str(e)}")
        return False
        
def get_available_templates(templates_dir: str = None) -> List[Dict[str, Any]]:
    """
    Pobiera listę dostępnych szablonów.
    
    Args:
        templates_dir: Katalog z szablonami (opcjonalny)
        
    Returns:
        List[Dict[str, Any]]: Lista dostępnych szablonów
    """
    # Jeśli nie podano katalogu szablonów, użyj domyślnej ścieżki
    if templates_dir is None:
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        
    # Sprawdzenie, czy katalog istnieje
    if not os.path.exists(templates_dir):
        logger.warning(f"Katalog szablonów {templates_dir} nie istnieje")
        return []
        
    # Lista dostępnych szablonów
    templates = []
    
    # Ładowanie szablonów z plików .json
    for filename in os.listdir(templates_dir):
        if filename.endswith(".json"):
            template_name = os.path.splitext(filename)[0]
            
            try:
                template = load_prompt_template(template_name, templates_dir)
                templates.append(template)
            except Exception as e:
                logger.error(f"Błąd podczas ładowania szablonu {template_name}: {str(e)}")
                
    return templates
    
def format_system_prompt(prompt: str, **kwargs) -> str:
    """
    Formatuje prompt systemowy na podstawie przekazanego szablonu i parametrów.
    
    Args:
        prompt: Szablon promptu systemowego
        **kwargs: Parametry do formatowania
        
    Returns:
        str: Sformatowany prompt systemowy
    """
    try:
        return prompt.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Brak wymaganego parametru w promptcie systemowym: {str(e)}")
        return prompt
    except Exception as e:
        logger.error(f"Błąd podczas formatowania promptu systemowego: {str(e)}")
        return prompt

def create_chat_messages(system_prompt: str, user_prompt: str, history: List[Dict[str, str]] = None) -> List[Dict[str, str]]:
    """
    Tworzy format wiadomości dla modeli czatowych.
    
    Args:
        system_prompt: Prompt systemowy
        user_prompt: Prompt użytkownika
        history: Historia konwersacji (opcjonalna)
        
    Returns:
        List[Dict[str, str]]: Lista wiadomości w formacie czatu
    """
    # Inicjalizacja listy wiadomości
    messages = [{"role": "system", "content": system_prompt}]
    
    # Dodanie historii konwersacji, jeśli podano
    if history:
        messages.extend(history)
        
    # Dodanie aktualnego promptu użytkownika
    messages.append({"role": "user", "content": user_prompt})
    
    return messages

class PromptTemplate:
    """
    Klasa reprezentująca szablon promptu.
    """
    
    def __init__(self, name: str, system_prompt: str = None, user_prompt: str = None, description: str = "", metadata: Dict[str, Any] = None):
        """
        Inicjalizacja szablonu promptu.
        
        Args:
            name: Nazwa szablonu
            system_prompt: Prompt systemowy (opcjonalny)
            user_prompt: Prompt użytkownika (opcjonalny)
            description: Opis szablonu (opcjonalny)
            metadata: Dodatkowe metadane szablonu (opcjonalne)
        """
        self.name = name
        self.system_prompt = system_prompt or ""
        self.user_prompt = user_prompt or ""
        self.description = description
        self.metadata = metadata or {}
        
    def fill(self, variables: Dict[str, Any]) -> Dict[str, str]:
        """
        Wypełnia szablon podanymi zmiennymi.
        
        Args:
            variables: Słownik ze zmiennymi do podstawienia
            
        Returns:
            Dict[str, str]: Słownik z wypełnionymi promptami
        """
        try:
            filled_system = format_system_prompt(self.system_prompt, **variables)
            filled_user = self.user_prompt.format(**variables)
            
            return {
                "system_prompt": filled_system,
                "user_prompt": filled_user
            }
        except Exception as e:
            logger.error(f"Błąd podczas wypełniania szablonu: {str(e)}")
            return {
                "system_prompt": self.system_prompt,
                "user_prompt": self.user_prompt
            }
            
    def get_required_variables(self) -> List[str]:
        """
        Zwraca listę wymaganych zmiennych w szablonie.
        
        Returns:
            List[str]: Lista nazw wymaganych zmiennych
        """
        variables = set()
        
        # Szukanie zmiennych w promptach
        for prompt in [self.system_prompt, self.user_prompt]:
            matches = re.findall(r'\{([a-zA-Z0-9_]+)\}', prompt)
            variables.update(matches)
            
        return list(variables)
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Konwertuje szablon do słownika.
        
        Returns:
            Dict[str, Any]: Słownik reprezentujący szablon
        """
        return {
            "name": self.name,
            "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt,
            "description": self.description,
            "metadata": self.metadata
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptTemplate':
        """
        Tworzy szablon z słownika.
        
        Args:
            data: Słownik z danymi szablonu
            
        Returns:
            PromptTemplate: Utworzony szablon
        """
        return cls(
            name=data.get("name", ""),
            system_prompt=data.get("system_prompt", ""),
            user_prompt=data.get("user_prompt", ""),
            description=data.get("description", ""),
            metadata=data.get("metadata", {})
        )


class PromptManager:
    """
    Klasa zarządzająca szablonami promptów.
    """
    
    def __init__(self, templates_dir: str = None):
        """
        Inicjalizacja menedżera promptów.
        
        Args:
            templates_dir: Katalog z szablonami (opcjonalny)
        """
        if templates_dir is None:
            templates_dir = os.path.join(os.path.dirname(__file__), "templates")
            
        self.templates_dir = templates_dir
        self.templates = {}  # Słownik przechowujący załadowane szablony
        self.templates_cache = {}  # Cache dla szablonów
        self.history = []  # Historia użytych promptów
        
        # Utworzenie katalogu szablonów, jeśli nie istnieje
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # Załadowanie szablonów
        self.load_templates()
        
        # Inicjalizacja cache'u
        self._init_cache()
        
    def _init_cache(self):
        """Inicjalizuje cache szablonów."""
        for template in self.templates.values():
            self.templates_cache[template.name] = template.to_dict()
            
    def load_templates(self):
        """Ładuje wszystkie szablony z katalogu."""
        try:
            for filename in os.listdir(self.templates_dir):
                if filename.endswith(".json"):
                    template_name = os.path.splitext(filename)[0]
                    template_path = os.path.join(self.templates_dir, filename)
                    
                    with open(template_path, "r", encoding="utf-8") as f:
                        template_data = json.load(f)
                        template = PromptTemplate.from_dict(template_data)
                        self.templates[template_name] = template
                        
            logger.info(f"Załadowano {len(self.templates)} szablonów")
        except Exception as e:
            logger.error(f"Błąd podczas ładowania szablonów: {str(e)}")
            
    def get_template(self, template_name: str) -> Optional[PromptTemplate]:
        """
        Pobiera szablon o podanej nazwie.
        
        Args:
            template_name: Nazwa szablonu
            
        Returns:
            Optional[PromptTemplate]: Szablon lub None jeśli nie znaleziono
        """
        return self.templates.get(template_name)
        
    def load_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Ładuje szablon z pliku.
        
        Args:
            template_name: Nazwa szablonu
            
        Returns:
            Optional[Dict[str, Any]]: Załadowany szablon lub None
            
        Raises:
            ValueError: Jeśli nie znaleziono szablonu
        """
        try:
            template = load_prompt_template(template_name, self.templates_dir)
            return template
        except ValueError as e:
            raise ValueError(str(e))
            
    def save_template(self, template: Dict[str, Any]) -> bool:
        """
        Zapisuje szablon do pliku.
        
        Args:
            template: Dane szablonu
            
        Returns:
            bool: True jeśli operacja się powiodła
        """
        if not isinstance(template, dict) or "name" not in template:
            logger.error("Nieprawidłowy format szablonu")
            return False
            
        template_name = template["name"]
        
        # Sprawdzenie, czy szablon już istnieje
        existing_template = self.get_template(template_name)
        if existing_template:
            # Aktualizacja istniejącego szablonu
            self.templates[template_name] = PromptTemplate.from_dict(template)
        else:
            # Dodanie nowego szablonu
            self.templates[template_name] = PromptTemplate.from_dict(template)
            
        # Aktualizacja cache'u
        self.templates_cache[template_name] = template
            
        # Zapisanie do pliku
        return save_prompt_template(template, self.templates_dir)
        
    def create_template(self, **kwargs) -> bool:
        """
        Tworzy nowy szablon.
        
        Args:
            **kwargs: Parametry szablonu (name, system_prompt, user_prompt, description, metadata)
            
        Returns:
            bool: True jeśli operacja się powiodła
            
        Raises:
            ValueError: Jeśli brakuje wymaganych parametrów
        """
        required_fields = ["name"]
        missing_fields = [field for field in required_fields if field not in kwargs]
        
        if missing_fields:
            raise ValueError(f"Brakujące wymagane pola: {', '.join(missing_fields)}")
            
        # Jeśli podano parameters, dodaj je do metadata
        if "parameters" in kwargs:
            if "metadata" not in kwargs:
                kwargs["metadata"] = {}
            kwargs["metadata"]["parameters"] = kwargs.pop("parameters")
            
        template = PromptTemplate(**kwargs)
        self.templates[template.name] = template
        self.templates_cache[template.name] = template.to_dict()
        return True
        
    def delete_template(self, template_name: str) -> bool:
        """
        Usuwa szablon.
        
        Args:
            template_name: Nazwa szablonu
            
        Returns:
            bool: True jeśli operacja się powiodła
            
        Raises:
            ValueError: Jeśli szablon nie istnieje
        """
        if template_name not in self.templates:
            raise ValueError(f"Szablon {template_name} nie istnieje")
            
        template_path = os.path.join(self.templates_dir, f"{template_name}.json")
        try:
            # Usunięcie pliku
            if os.path.exists(template_path):
                os.remove(template_path)
            
            # Usunięcie z pamięci
            del self.templates[template_name]
            if template_name in self.templates_cache:
                del self.templates_cache[template_name]
                
            return True
        except Exception as e:
            logger.error(f"Błąd podczas usuwania szablonu {template_name}: {str(e)}")
            return False
            
    def format_prompt(self, template_name: str, **kwargs) -> Dict[str, str]:
        """
        Formatuje prompt na podstawie szablonu i zmiennych.
        
        Args:
            template_name: Nazwa szablonu
            **kwargs: Zmienne do podstawienia
            
        Returns:
            Dict[str, str]: Słownik z wypełnionymi promptami
            
        Raises:
            ValueError: Jeśli brakuje wymaganych zmiennych
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Nie znaleziono szablonu: {template_name}")
            
        required_vars = template.get_required_variables()
        missing_vars = [var for var in required_vars if var not in kwargs]
        
        if missing_vars:
            raise ValueError(f"Brakujące zmienne: {', '.join(missing_vars)}")
            
        return template.fill(kwargs)
        
    def list_templates(self) -> List[Dict[str, Any]]:
        """
        Zwraca listę dostępnych szablonów.
        
        Returns:
            List[Dict[str, Any]]: Lista szablonów w formacie słowników
        """
        return [template.to_dict() for template in self.templates.values()]
        
    def search_templates(self, tags: List[str] = None) -> List[Dict[str, Any]]:
        """
        Wyszukuje szablony po tagach.
        
        Args:
            tags: Lista tagów do wyszukania
            
        Returns:
            List[Dict[str, Any]]: Lista znalezionych szablonów
        """
        if not tags:
            return self.list_templates()
            
        return [
            template.to_dict() for template in self.templates.values()
            if all(tag in template.metadata.get("tags", []) for tag in tags)
        ]

    def create_prompt(self, template_name: str, variables: Dict[str, Any] = None) -> Optional[str]:
        """
        Tworzy prompt na podstawie szablonu i zmiennych.
        
        Args:
            template_name: Nazwa szablonu
            variables: Zmienne do podstawienia
            
        Returns:
            Optional[str]: Sformatowany prompt lub None
        """
        template = self.get_template(template_name)
        if not template:
            return None
            
        try:
            prompt = template.fill(variables or {})
            self.add_to_history(template_name, variables or {}, prompt)
            return prompt
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia promptu: {str(e)}")
            return None
            
    def add_to_history(self, template_name: str, variables: Dict[str, Any], prompt: str):
        """
        Dodaje prompt do historii.
        
        Args:
            template_name: Nazwa użytego szablonu
            variables: Użyte zmienne
            prompt: Utworzony prompt
        """
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "template_name": template_name,
            "variables": variables,
            "prompt": prompt
        }
        
        self.history.append(history_entry)
        
        # Ograniczenie historii do 100 ostatnich promptów
        if len(self.history) > 100:
            self.history = self.history[-100:]


class TradingPromptManager(PromptManager):
    """
    Specjalizowany menedżer promptów dla zastosowań handlowych.
    """
    
    def __init__(self, templates_dir: str = None):
        """
        Inicjalizacja menedżera promptów handlowych.
        
        Args:
            templates_dir: Ścieżka do katalogu z szablonami (opcjonalna)
        """
        super().__init__(templates_dir)
        
        # Dodanie domyślnych szablonów
        self._add_default_templates()
        
        logger.info("Inicjalizacja TradingPromptManager")
        
    def _add_default_templates(self):
        """Dodaje domyślne szablony handlowe."""
        default_templates = [
            {
                "name": "market_analysis",
                "template": self._get_default_market_analysis_template(),
                "description": "Domyślny szablon analizy rynku",
                "metadata": {"tags": ["analiza", "rynek"]}
            },
            {
                "name": "trading_signal",
                "template": self._get_default_trading_signal_template(),
                "description": "Domyślny szablon sygnałów handlowych",
                "metadata": {"tags": ["trading", "sygnały"]}
            },
            {
                "name": "risk_management",
                "template": self._get_default_risk_management_template(),
                "description": "Domyślny szablon zarządzania ryzykiem",
                "metadata": {"tags": ["ryzyko", "zarządzanie"]}
            }
        ]
        
        for template_data in default_templates:
            if not self.get_template(template_data["name"]):
                template = PromptTemplate(**template_data)
                self.templates[template.name] = template
    
    def create_market_analysis_prompt(self, symbol: str, timeframe: str, price_data: Dict[str, Any], indicators: Dict[str, Any] = None) -> str:
        """
        Tworzy prompt do analizy rynku.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Interwał czasowy
            price_data: Dane cenowe
            indicators: Wskaźniki techniczne (opcjonalne)
            
        Returns:
            str: Prompt do analizy rynku
        """
        variables = {
            "symbol": symbol,
            "timeframe": timeframe,
            "price_data": price_data
        }
        
        if indicators:
            variables["indicators"] = indicators
            
        prompt = self.create_prompt("market_analysis", variables)
        
        if prompt is None:
            # Użyj domyślnego szablonu jeśli nie znaleziono
            logger.warning("Używam domyślnego szablonu dla analizy rynku")
            
            default_template = self._get_default_market_analysis_template()
            template = PromptTemplate(
                name="market_analysis_default",
                template=default_template,
                description="Domyślny szablon analizy rynku"
            )
            
            self.add_template(template)
            prompt = self.create_prompt("market_analysis_default", variables)
            
        return prompt
    
    def create_trading_signal_prompt(self, symbol: str, timeframe: str, price_data: Dict[str, Any], strategy: str = None) -> str:
        """
        Tworzy prompt do generowania sygnałów handlowych.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Interwał czasowy
            price_data: Dane cenowe
            strategy: Nazwa strategii (opcjonalna)
            
        Returns:
            str: Prompt do generowania sygnałów handlowych
        """
        variables = {
            "symbol": symbol,
            "timeframe": timeframe,
            "price_data": price_data
        }
        
        if strategy:
            variables["strategy"] = strategy
            
        prompt = self.create_prompt("trading_signal", variables)
        
        if prompt is None:
            # Użyj domyślnego szablonu jeśli nie znaleziono
            logger.warning("Używam domyślnego szablonu dla sygnałów handlowych")
            
            default_template = self._get_default_trading_signal_template()
            template = PromptTemplate(
                name="trading_signal_default",
                template=default_template,
                description="Domyślny szablon sygnałów handlowych"
            )
            
            self.add_template(template)
            prompt = self.create_prompt("trading_signal_default", variables)
            
        return prompt
    
    def create_risk_management_prompt(self, trade_idea: Dict[str, Any], account_balance: float, risk_tolerance: str = "medium") -> str:
        """
        Tworzy prompt do zarządzania ryzykiem.
        
        Args:
            trade_idea: Pomysł handlowy
            account_balance: Stan konta
            risk_tolerance: Tolerancja ryzyka (opcjonalna)
            
        Returns:
            str: Prompt do zarządzania ryzykiem
        """
        variables = {
            "trade_idea": trade_idea,
            "account_balance": account_balance,
            "risk_tolerance": risk_tolerance
        }
        
        prompt = self.create_prompt("risk_management", variables)
        
        if prompt is None:
            # Użyj domyślnego szablonu jeśli nie znaleziono
            logger.warning("Używam domyślnego szablonu dla zarządzania ryzykiem")
            
            default_template = self._get_default_risk_management_template()
            template = PromptTemplate(
                name="risk_management_default",
                template=default_template,
                description="Domyślny szablon zarządzania ryzykiem"
            )
            
            self.add_template(template)
            prompt = self.create_prompt("risk_management_default", variables)
            
        return prompt
    
    def _get_default_market_analysis_template(self) -> str:
        """
        Zwraca domyślny szablon analizy rynku.
        
        Returns:
            str: Domyślny szablon analizy rynku
        """
        return """
Wykonaj szczegółową analizę techniczną dla pary {{symbol}} na interwale {{timeframe}}.

Dane cenowe:
{{price_data}}

{% if indicators is defined %}
Wskaźniki techniczne:
{{indicators}}
{% endif %}

Odpowiedź podaj w formacie JSON:
{
  "trend": "bullish/bearish/neutral",
  "key_levels": {
    "support": [poziom1, poziom2],
    "resistance": [poziom1, poziom2]
  },
  "explanation": "Wyjaśnienie analizy..."
}
        """
    
    def _get_default_trading_signal_template(self) -> str:
        """
        Zwraca domyślny szablon sygnałów handlowych.
        
        Returns:
            str: Domyślny szablon sygnałów handlowych
        """
        return """
Wygeneruj konkretny sygnał handlowy dla pary {{symbol}} na interwale {{timeframe}}.

Dane cenowe:
{{price_data}}

{% if strategy is defined %}
Strategia: {{strategy}}
{% endif %}

Odpowiedź podaj w formacie JSON:
{
  "signal": "buy/sell/wait",
  "entry": poziom_wejścia,
  "stop_loss": poziom_stop_loss,
  "take_profit": poziom_take_profit,
  "explanation": "Uzasadnienie sygnału..."
}
        """
    
    def _get_default_risk_management_template(self) -> str:
        """
        Zwraca domyślny szablon zarządzania ryzykiem.
        
        Returns:
            str: Domyślny szablon zarządzania ryzykiem
        """
        return """
Dokonaj oceny ryzyka i zaproponuj parametry pozycji dla poniższego pomysłu handlowego.

Pomysł handlowy:
{{trade_idea}}

Stan konta: {{account_balance}}
Tolerancja ryzyka: {{risk_tolerance}}

Odpowiedź podaj w formacie JSON:
{
  "risk_level": "low/medium/high",
  "position_size": zalecana_wielkość_pozycji,
  "risk_per_trade": procent_ryzykowanego_kapitału,
  "risk_reward_ratio": stosunek_zysku_do_ryzyka,
  "explanation": "Uzasadnienie oceny..."
}
        """ 
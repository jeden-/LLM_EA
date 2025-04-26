"""
Moduł odpowiedzialny za wybór odpowiedniego modelu LLM.
"""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class ModelSelector:
    """
    Klasa odpowiedzialna za wybór odpowiedniego modelu LLM na podstawie zadania.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicjalizacja selektora modeli.
        
        Args:
            config: Konfiguracja selektora zawierająca mapowanie modeli
        """
        self.model_mapping = config.get('model_mapping', {
            'gpt-4': {
                'tasks': ['trade_signal', 'market_analysis', 'risk_assessment'],
                'max_tokens': 8000,
                'cost_per_1k': 0.03
            },
            'gpt-3.5-turbo': {
                'tasks': ['trade_signal', 'market_analysis'],
                'max_tokens': 4000,
                'cost_per_1k': 0.002
            }
        })
        self.fallback_model = config.get('fallback_model', 'gpt-3.5-turbo')
        
        # Cache dla dostępnych modeli
        self._available_models = None
        
    def get_available_models(self) -> List[str]:
        """
        Zwraca listę dostępnych modeli.
        
        Returns:
            Lista nazw dostępnych modeli
        """
        return list(self.model_mapping.keys())
        
    def select_model(self, task_type: str) -> str:
        """
        Wybiera model na podstawie typu zadania.
        
        Args:
            task_type: Typ zadania do wykonania
            
        Returns:
            Nazwa wybranego modelu
            
        Raises:
            ValueError: Gdy nie znaleziono odpowiedniego modelu
        """
        suitable_models = [
            model for model, config in self.model_mapping.items()
            if task_type in config['tasks']
        ]
        
        if not suitable_models:
            logger.warning(f"Nie znaleziono modelu dla zadania {task_type}, używam modelu fallback")
            return self.fallback_model
            
        # Wybierz model z najniższym kosztem
        return min(suitable_models, key=lambda m: self.model_mapping[m]['cost_per_1k'])
        
    def select_model_by_params(
        self,
        task_type: str,
        max_tokens: Optional[int] = None,
        max_cost: Optional[float] = None
    ) -> str:
        """
        Wybiera model na podstawie parametrów.
        
        Args:
            task_type: Typ zadania do wykonania
            max_tokens: Maksymalna liczba tokenów
            max_cost: Maksymalny koszt za 1000 tokenów
            
        Returns:
            Nazwa wybranego modelu
            
        Raises:
            ValueError: Gdy nie znaleziono odpowiedniego modelu
        """
        suitable_models = [
            model for model, config in self.model_mapping.items()
            if task_type in config['tasks'] and
            (max_tokens is None or config['max_tokens'] >= max_tokens) and
            (max_cost is None or config['cost_per_1k'] <= max_cost)
        ]
        
        if not suitable_models:
            logger.warning(
                f"Nie znaleziono modelu dla zadania {task_type} "
                f"(max_tokens={max_tokens}, max_cost={max_cost}), "
                "używam modelu fallback"
            )
            return self.fallback_model
            
        # Wybierz model z najniższym kosztem
        return min(suitable_models, key=lambda m: self.model_mapping[m]['cost_per_1k']) 
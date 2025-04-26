"""
Moduł preprocessora dla danych wejściowych do modeli LLM.

Ten moduł zawiera klasy odpowiedzialne za przygotowanie danych przed ich wysłaniem do modeli językowych,
w tym czyszczenie, normalizację i formatowanie danych rynkowych.
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import pandas as pd

# Inicjalizacja loggera
logger = logging.getLogger(__name__)

class LLMPreprocessor:
    """
    Bazowa klasa preprocessora dla danych wejściowych do LLM.
    
    Odpowiada za ogólne operacje na danych wejściowych, takie jak czyszczenie, 
    normalizacja i walidacja.
    """
    
    def __init__(self):
        """Inicjalizacja preprocessora."""
        logger.debug("Inicjalizacja LLMPreprocessor")
        
    def clean_input_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Czyści dane wejściowe usuwając niepotrzebne znaki i normalizując format.
        
        Args:
            data: Słownik z danymi wejściowymi
            
        Returns:
            Dict[str, Any]: Oczyszczone dane
        """
        if data is None:
            return {}
            
        # Tworzenie kopii, aby nie modyfikować oryginalnych danych
        cleaned_data = {}
        
        for key, value in data.items():
            # Rekurencyjne czyszczenie słowników
            if isinstance(value, dict):
                cleaned_data[key] = self.clean_input_data(value)
            # Czyszczenie list (bez rekurencji dla prostoty)
            elif isinstance(value, list):
                cleaned_data[key] = value
            # Czyszczenie tekstu
            elif isinstance(value, str):
                # Usunięcie nadmiarowych białych znaków
                cleaned_value = re.sub(r'\s+', ' ', value)
                # Usunięcie białych znaków z początku i końca
                cleaned_value = cleaned_value.strip()
                cleaned_data[key] = cleaned_value
            # Zaokrąglenie liczb zmiennoprzecinkowych
            elif isinstance(value, float):
                cleaned_data[key] = round(value, 3)
            # Inne typy bez zmian
            else:
                cleaned_data[key] = value
                
        return cleaned_data
        
    def validate_input_data(self, data: Dict[str, Any], required_fields: List[str]) -> bool:
        """
        Sprawdza, czy dane wejściowe zawierają wszystkie wymagane pola.
        
        Args:
            data: Słownik z danymi wejściowymi
            required_fields: Lista wymaganych pól
            
        Returns:
            bool: True jeśli dane zawierają wszystkie wymagane pola, False w przeciwnym razie
        """
        if data is None:
            return False
            
        for field in required_fields:
            if field not in data:
                logger.warning(f"Brak wymaganego pola: {field}")
                return False
                
        return True
        
    def normalize_market_data(self, market_data: Dict[str, List[float]]) -> Dict[str, List[float]]:
        """
        Normalizuje dane rynkowe do zakresu [0, 1].
        
        Args:
            market_data: Słownik z danymi rynkowymi (OHLCV)
            
        Returns:
            Dict[str, List[float]]: Znormalizowane dane
        """
        normalized_data = {}
        
        # Normalizacja dla każdego typu danych osobno (open, high, low, close, volume)
        for key, values in market_data.items():
            if not values:
                normalized_data[key] = []
                continue
                
            min_val = min(values)
            max_val = max(values)
            
            # Unikamy dzielenia przez zero
            if max_val == min_val:
                normalized_data[key] = [0.5 for _ in values]
            else:
                normalized_data[key] = [(v - min_val) / (max_val - min_val) for v in values]
                
        return normalized_data


class MarketDataPreprocessor(LLMPreprocessor):
    """
    Preprocessor specjalizujący się w przygotowaniu danych rynkowych dla LLM.
    """
    
    def __init__(self):
        """Inicjalizacja preprocessora danych rynkowych."""
        super().__init__()
        
        # Import tutaj, aby uniknąć importów cyklicznych
        from LLM_Engine.technical_indicators import CalculateIndicators
        self.indicators = CalculateIndicators()
        
    def add_technical_indicators(self, market_data: Dict[str, Any], indicators: List[str] = None) -> Dict[str, Any]:
        """
        Dodaje wskaźniki techniczne do danych rynkowych.
        
        Args:
            market_data: Słownik z danymi rynkowymi
            indicators: Lista nazw wskaźników do obliczenia
            
        Returns:
            Dict[str, Any]: Dane rynkowe z dodanymi wskaźnikami
        """
        # Jeśli nie podano listy wskaźników, użyj domyślnej
        if indicators is None:
            indicators = ["ma", "rsi"]
            
        # Tworzymy kopię danych rynkowych
        result = market_data.copy()
        
        # Pobieramy ceny zamknięcia
        close_prices = market_data.get("close", [])
        
        # Dodajemy wskaźniki
        for indicator in indicators:
            if indicator.lower() == "ma":
                result["ma"] = self.indicators.calculate_ma(close_prices)
            elif indicator.lower() == "rsi":
                result["rsi"] = self.indicators.calculate_rsi(close_prices)
            # Dodatkowe wskaźniki można zaimplementować tutaj
                
        return result
        
    def format_price_data(self, market_data: Dict[str, Any]) -> str:
        """
        Formatuje dane rynkowe do postaci tekstowej dla modelu LLM.
        
        Args:
            market_data: Słownik z danymi rynkowymi
            
        Returns:
            str: Sformatowany tekst z danymi rynkowymi
        """
        formatted_text = "#### Dane rynkowe ####\n"
        
        # Określenie liczby okresów
        num_periods = len(market_data.get("close", []))
        
        # Dla każdego okresu przygotuj dane
        for i in range(num_periods):
            formatted_text += f"Okres {i+1}:\n"
            
            # Dodaj dane OHLC
            for key in ["open", "high", "low", "close"]:
                if key in market_data and i < len(market_data[key]):
                    formatted_text += f"{key.capitalize()}: {market_data[key][i]}\n"
            
            # Dodaj informację o wolumenie
            if "volume" in market_data and i < len(market_data["volume"]):
                formatted_text += f"Volume: {market_data['volume'][i]}\n"
            
            # Dodaj wskaźniki
            for key in market_data:
                if key not in ["open", "high", "low", "close", "volume", "symbol", "timeframe"]:
                    if i < len(market_data[key]) and market_data[key][i] is not None:
                        formatted_text += f"{key.upper()}: {market_data[key][i]}\n"
            
            formatted_text += "\n"
            
        return formatted_text
        
    def process_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Przetwarza dane rynkowe - główna metoda procesora.
        
        Args:
            market_data: Słownik z danymi rynkowymi
            
        Returns:
            Dict[str, Any]: Przetworzone dane
        """
        # Sprawdzenie wymaganych pól
        required_fields = ["symbol", "timeframe", "open", "high", "low", "close"]
        if not self.validate_input_data(market_data, required_fields):
            logger.error("Nieprawidłowe dane rynkowe - brak wymaganych pól")
            return {"error": "Nieprawidłowe dane rynkowe"}
        
        # Czyszczenie danych
        cleaned_data = self.clean_input_data(market_data)
        
        # Dodanie wskaźników technicznych
        data_with_indicators = self.add_technical_indicators(cleaned_data)
        
        # Formatowanie danych dla modelu
        formatted_data = self.format_price_data(data_with_indicators)
        
        # Zwracamy pełen zestaw danych + tekst sformatowany dla modelu
        result = data_with_indicators.copy()
        result["formatted_data"] = formatted_data
        
        return result


class PromptTemplateProcessor(LLMPreprocessor):
    """
    Preprocessor do przetwarzania szablonów promptów.
    """
    
    def __init__(self, template_dir: str = None):
        """
        Inicjalizacja procesora szablonów.
        
        Args:
            template_dir: Ścieżka do katalogu z szablonami
        """
        super().__init__()
        
        # Jeśli nie podano katalogu, użyj domyślnego
        if template_dir is None:
            import os
            template_dir = os.path.join(os.path.dirname(__file__), "templates")
            
        self.template_dir = template_dir
        
    def load_template(self, template_name: str) -> str:
        """
        Ładuje szablon z pliku.
        
        Args:
            template_name: Nazwa szablonu (bez rozszerzenia)
            
        Returns:
            str: Zawartość szablonu
        """
        import os
        
        template_path = os.path.join(self.template_dir, f"{template_name}.txt")
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Błąd podczas ładowania szablonu {template_name}: {str(e)}")
            return ""
    
    def fill_template(self, template: str, data: Dict[str, Any]) -> str:
        """
        Wypełnia szablon danymi.
        
        Args:
            template: Tekst szablonu
            data: Słownik z danymi do wstawienia
            
        Returns:
            str: Wypełniony szablon
        """
        filled_template = template
        
        # Zastępowanie zmiennych w formacie {{variable}}
        for key, value in data.items():
            placeholder = f"{{{{{key}}}}}"
            filled_template = filled_template.replace(placeholder, str(value))
            
        return filled_template
        
    def prepare_task_prompt(self, task_type: str, data: Dict[str, Any]) -> str:
        """
        Przygotowuje prompt dla określonego zadania.
        
        Args:
            task_type: Typ zadania (np. "market_analysis", "trade_signal")
            data: Dane do wstawienia w szablon
            
        Returns:
            str: Przygotowany prompt
        """
        # Ładowanie odpowiedniego szablonu
        template = self.load_template(task_type)
        
        if not template:
            logger.warning(f"Nie znaleziono szablonu dla zadania {task_type}. Używam domyślnego.")
            template = "Wykonaj zadanie typu {{task_type}} używając danych: {{formatted_data}}"
            
        # Dodanie typu zadania do danych
        data["task_type"] = task_type
        
        # Wypełnienie szablonu danymi
        prompt = self.fill_template(template, data)
        
        return prompt


class HistoricalDataPreprocessor(LLMPreprocessor):
    """
    Preprocessor specjalizujący się w przygotowaniu danych historycznych.
    """
    
    def __init__(self):
        """Inicjalizacja preprocessora danych historycznych."""
        super().__init__()
        
    def filter_by_date_range(self, data: Dict[str, List], start_date: str, end_date: str) -> Dict[str, List]:
        """
        Filtruje dane według zakresu dat.
        
        Args:
            data: Słownik z danymi historycznymi
            start_date: Data początkowa w formacie YYYY-MM-DD
            end_date: Data końcowa w formacie YYYY-MM-DD
            
        Returns:
            Dict[str, List]: Przefiltrowane dane
        """
        if not data or "dates" not in data:
            return data
            
        # Konwersja dat na obiekty datetime
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Znalezienie indeksów dla zakresu dat
        indices = []
        for i, date_str in enumerate(data["dates"]):
            # Obsługa różnych formatów dat
            try:
                if " " in date_str:  # Format z godziną
                    date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                else:  # Format tylko data
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                    
                if start <= date <= end:
                    indices.append(i)
            except ValueError as e:
                logger.warning(f"Nieprawidłowy format daty: {date_str}, {e}")
                continue
        
        # Filtrowanie danych
        filtered_data = {}
        for key in data:
            filtered_data[key] = [data[key][i] for i in indices]
            
        return filtered_data
        
    def _resample_to_target_timeframe(self, data: Dict[str, List], target_timeframe: str) -> Dict[str, List]:
        """
        Przewzorcowuje dane do docelowego interwału czasowego używając pandas DataFrame.
        
        Args:
            data: Słownik z danymi historycznymi
            target_timeframe: Docelowy interwał czasowy
            
        Returns:
            Dict[str, List]: Przewzorcowane dane
        """
        if not data or "dates" not in data:
            return data
            
        try:
            # Konwersja danych do DataFrame
            df = pd.DataFrame(data)
            df['dates'] = pd.to_datetime(df['dates'])
            df.set_index('dates', inplace=True)
            
            # Mapowanie interwałów na format pandas
            timeframe_map = {
                'M1': '1min', 'M5': '5min', 'M15': '15min', 'M30': '30min',
                'H1': '1H', 'H4': '4H', 'D1': '1D', 'W1': '1W'
            }
            resample_rule = timeframe_map.get(target_timeframe.upper(), '1min')
            
            # Resampling z odpowiednimi agregacjami
            resampled = df.resample(resample_rule).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })
            
            # Konwersja z powrotem do słownika
            result = {
                'dates': resampled.index.strftime('%Y-%m-%d %H:%M').tolist(),
                'open': resampled['open'].tolist(),
                'high': resampled['high'].tolist(),
                'low': resampled['low'].tolist(),
                'close': resampled['close'].tolist(),
                'volume': resampled['volume'].tolist()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Błąd podczas resamplingu danych: {e}")
            return data
        
    def _get_group_size(self, timeframe: str) -> int:
        """
        Określa rozmiar grupy na podstawie interwału czasowego.
        
        Args:
            timeframe: Interwał czasowy (np. H1, H4, D1)
            
        Returns:
            int: Rozmiar grupy
        """
        timeframe = timeframe.upper()
        if timeframe.startswith("M"):  # Minutowy
            return int(timeframe[1:])
        elif timeframe.startswith("H"):  # Godzinowy
            return int(timeframe[1:]) * 60
        elif timeframe.startswith("D"):  # Dzienny
            return int(timeframe[1:]) * 1440
        else:
            return 1
        
    def resample_data(self, data: Dict[str, List], source_timeframe: str, target_timeframe: str) -> Dict[str, List]:
        """
        Przewzorcowuje dane do nowego interwału czasowego.
        
        Args:
            data: Słownik z danymi historycznymi
            source_timeframe: Aktualny interwał czasowy
            target_timeframe: Docelowy interwał czasowy
            
        Returns:
            Dict[str, List]: Przewzorcowane dane
        """
        if source_timeframe == target_timeframe:
            return data
            
        return self._resample_to_target_timeframe(data, target_timeframe)
        
    def prepare_historical_data(self, data: Dict[str, Any], timeframe: str = None, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        Przygotowuje dane historyczne do analizy.
        
        Args:
            data: Słownik z danymi historycznymi
            timeframe: Docelowy timeframe (opcjonalny)
            start_date: Data początkowa (opcjonalna)
            end_date: Data końcowa (opcjonalna)
            
        Returns:
            Dict[str, Any]: Przetworzone dane historyczne
        """
        # Walidacja danych wejściowych
        required_fields = ["symbol", "data"]
        if not self.validate_input_data(data, required_fields):
            raise ValueError("Brak wymaganych pól w danych wejściowych")
            
        # Przygotowanie parametrów
        start = start_date or data.get("start_date")
        end = end_date or data.get("end_date")
        target_tf = timeframe or data.get("target_timeframe")
        source_tf = data.get("source_timeframe")
        
        # Filtrowanie danych po zakresie dat
        filtered_data = self.filter_by_date_range(data["data"], start, end)
        
        # Resampling danych jeśli potrzebny
        if source_tf and target_tf and source_tf != target_tf:
            processed_data = self.resample_data(filtered_data, source_tf, target_tf)
        else:
            processed_data = filtered_data
            
        # Przygotowanie wyniku
        result = {
            "symbol": data["symbol"],
            "timeframe": target_tf or source_tf,  # Dodajemy timeframe do wyniku
            "data": processed_data
        }
        
        # Dodanie metadanych
        if start:
            result["start_date"] = start
        if end:
            result["end_date"] = end
            
        return result 
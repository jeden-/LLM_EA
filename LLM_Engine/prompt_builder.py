"""
Moduł budowania promptów dla lokalnego modelu LLM.

Ten moduł odpowiada za:
1. Generowanie wyspecjalizowanych promptów dla modelu LLM
2. Formatowanie danych rynkowych do analizy
3. Dostosowanie kontekstu do różnych strategii inwestycyjnych
4. Zarządzanie szablonami promptów dla różnych przypadków użycia
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class PromptBuilder:
    """
    Klasa odpowiedzialna za budowanie promptów dla modelu LLM.
    
    Umożliwia tworzenie wyspecjalizowanych promptów zawierających dane rynkowe,
    kontekst historyczny, strategie inwestycyjne i inne informacje potrzebne
    modelowi do wykonania analizy i podejmowania decyzji handlowych.
    """
    
    def __init__(self, templates_path: Optional[str] = None):
        """
        Inicjalizuje builder promptów.
        
        Args:
            templates_path: Opcjonalna ścieżka do katalogu z szablonami promptów
        """
        self.templates_path = templates_path
        self.templates = self._load_templates() if templates_path else {}
        
    def _load_templates(self) -> Dict[str, str]:
        """
        Ładuje szablony promptów z plików.
        
        Returns:
            Dict[str, str]: Słownik z szablonami promptów
        """
        import os
        
        templates = {}
        try:
            if os.path.isdir(self.templates_path):
                for filename in os.listdir(self.templates_path):
                    if filename.endswith('.txt'):
                        template_name = os.path.splitext(filename)[0]
                        file_path = os.path.join(self.templates_path, filename)
                        
                        with open(file_path, 'r', encoding='utf-8') as f:
                            templates[template_name] = f.read()
                            
                logger.info(f"Załadowano {len(templates)} szablonów promptów")
            else:
                logger.warning(f"Ścieżka {self.templates_path} nie jest katalogiem")
        except Exception as e:
            logger.error(f"Błąd podczas ładowania szablonów: {str(e)}")
            
        return templates
        
    def build_market_analysis_prompt(
        self,
        symbol: str,
        timeframe: str,
        price_data: List[Dict[str, Any]],
        indicators: Dict[str, List[Any]],
        news: Optional[List[Dict[str, Any]]] = None,
        strategy_name: Optional[str] = None,
        risk_level: str = "medium",
        additional_context: Optional[str] = None,
        max_candles: int = 3  # Zmniejszona liczba świec (domyślnie 3 zamiast 5)
    ) -> str:
        """
        Buduje prompt do analizy rynku i rekomendacji handlowych.
        
        Args:
            symbol: Symbol instrumentu (np. "EURUSD")
            timeframe: Przedział czasowy (np. "H1", "D1")
            price_data: Lista słowników z danymi cenowymi (OHLCV)
            indicators: Słownik z wartościami wskaźników technicznych
            news: Opcjonalna lista wiadomości rynkowych
            strategy_name: Opcjonalna nazwa strategii do zastosowania
            risk_level: Poziom ryzyka ("low", "medium", "high")
            additional_context: Dodatkowy kontekst dla modelu
            max_candles: Maksymalna liczba świec do uwzględnienia w prompcie
            
        Returns:
            str: Kompletny prompt do wysłania do modelu
        """
        # Przygotowanie nagłówka - bardziej zwięzły
        header = f"""Analiza: {symbol}, {timeframe}"""

        # Przygotowanie danych cenowych (mniej świec)
        price_section = "### Dane cenowe\n"
        display_candles = min(max_candles, len(price_data))
        for i in range(-display_candles, 0):
            candle = price_data[i]
            price_section += (f"O:{candle.get('open', 'N/A')}, "
                            f"H:{candle.get('high', 'N/A')}, L:{candle.get('low', 'N/A')}, "
                            f"C:{candle.get('close', 'N/A')}\n")
            
        # Przygotowanie sekcji wskaźników - tylko kluczowe wartości, mniej wartości historycznych
        indicators_section = "### Wskaźniki\n"
        for indicator_name, values in indicators.items():
            # Pokazujemy tylko ostatnią wartość zamiast trzech ostatnich
            if isinstance(values, list) and len(values) > 0:
                indicators_section += f"{indicator_name}: {values[-1]}\n"
            elif isinstance(values, dict):
                indicators_section += f"{indicator_name}: {values}\n"
            else:
                indicators_section += f"{indicator_name}: {values}\n"
            
        # Przygotowanie wiadomości (jeśli dostępne) - ograniczenie do 2 najnowszych
        news_section = ""
        if news and len(news) > 0:
            news_section = "### Wiadomości\n"
            for item in news[:2]:  # Ograniczenie do 2 najnowszych wiadomości
                news_section += f"- {item.get('title', 'N/A')}\n"
                
        # Przygotowanie informacji o strategii - krótsza wersja
        strategy_section = ""
        if strategy_name:
            strategy_section = f"### Strategia: {strategy_name}, Ryzyko: {risk_level}\n"
                
        # Dodatkowy kontekst - opcjonalny i skrócony
        context_section = f"\n### Kontekst\n{additional_context}\n" if additional_context else ""
                
        # Przygotowanie pytań i instrukcji dla modelu - jeszcze bardziej zwięzłe
        instructions = """
### Zadanie
Analiza techniczna i rekomendacja:
{
  "analysis": {
    "trend": "bullish/bearish/sideways",
    "key_levels": {
      "support": [poziom1, poziom2],
      "resistance": [poziom1, poziom2]
    }
  },
  "recommendation": {
    "action": "buy/sell/hold",
    "entry_price": float,
    "stop_loss": float,
    "take_profit": float
  }
}

Odpowiedź: TYLKO JSON
"""

        # Złożenie pełnego promptu
        full_prompt = f"{header}\n{price_section}\n{indicators_section}\n{news_section}\n{strategy_section}\n{context_section}\n{instructions}"
        
        return full_prompt
    
    def build_risk_management_prompt(
        self,
        symbol: str,
        account_balance: float,
        open_positions: List[Dict[str, Any]],
        historical_trades: List[Dict[str, Any]],
        risk_per_trade_pct: float = 2.0,
        max_open_positions: int = 5,
    ) -> str:
        """
        Buduje prompt do analizy zarządzania ryzykiem.
        
        Args:
            symbol: Symbol instrumentu do analizy
            account_balance: Aktualny stan konta
            open_positions: Lista otwartych pozycji
            historical_trades: Lista historycznych transakcji
            risk_per_trade_pct: Procent ryzyka na transakcję
            max_open_positions: Maksymalna liczba otwartych pozycji
            
        Returns:
            str: Prompt do analizy zarządzania ryzykiem
        """
        # Formatowanie otwartych pozycji
        open_positions_str = "Brak otwartych pozycji"
        if open_positions:
            open_positions_str = "\n".join([
                f"{i+1}. {pos['symbol']}: Kierunek: {pos['type']}, Wielkość: {pos['volume']}, "
                f"Cena otwarcia: {pos['price_open']}, SL: {pos['sl']}, TP: {pos['tp']}, "
                f"Zysk/strata: {pos['profit']}"
                for i, pos in enumerate(open_positions)
            ])
        
        # Podsumowanie historycznych transakcji
        wins = sum(1 for trade in historical_trades if trade.get('profit', 0) > 0)
        losses = sum(1 for trade in historical_trades if trade.get('profit', 0) <= 0)
        win_rate = (wins / len(historical_trades)) * 100 if historical_trades else 0
        total_profit = sum(trade.get('profit', 0) for trade in historical_trades)
        
        prompt = f"""Analiza zarządzania ryzykiem
Instrument: {symbol}
Stan konta: {account_balance}
Ryzyko na transakcję: {risk_per_trade_pct}%
Maksymalna liczba otwartych pozycji: {max_open_positions}

### Otwarte pozycje
{open_positions_str}

### Podsumowanie historycznych transakcji
Liczba transakcji: {len(historical_trades)}
Wygrane: {wins}, Przegrane: {losses}
Win rate: {win_rate:.2f}%
Łączny zysk/strata: {total_profit}

### Zadanie
Na podstawie powyższych danych przeprowadź analizę zarządzania ryzykiem i udziel odpowiedzi w następującym formacie JSON:
{
  "position_sizing": {
    "recommended_volume": float_value,
    "max_risk_amount": float_value,
    "safe_stop_loss_pips": integer_value
  },
  "risk_assessment": {
    "current_account_risk": "low/medium/high",
    "portfolio_diversification": "good/moderate/poor",
    "exposure_to_symbol": "low/medium/high",
    "max_drawdown_risk": float_value
  },
  "recommendations": {
    "can_open_new_position": true/false,
    "should_reduce_exposure": true/false,
    "specific_actions": ["action1", "action2"]
  },
  "explanation": "Krótkie uzasadnienie rekomendacji w 2-3 zdaniach"
}

Twoja odpowiedź powinna zawierać TYLKO obiekt JSON bez żadnych dodatkowych komentarzy czy tekstu przed lub po nim.
"""
        return prompt
    
    def build_prompt_from_template(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Buduje prompt na podstawie szablonu i kontekstu.
        
        Args:
            template_name: Nazwa szablonu do użycia
            context: Słownik z danymi do wypełnienia szablonu
            
        Returns:
            str: Wypełniony prompt
            
        Raises:
            ValueError: Jeśli szablon nie istnieje
        """
        if template_name not in self.templates:
            raise ValueError(f"Szablon '{template_name}' nie istnieje")
        
        template = self.templates[template_name]
        
        # Prosta implementacja wypełniania szablonu
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, indent=2)
            template = template.replace(placeholder, str(value))
            
        return template


# Przykład użycia
if __name__ == "__main__":
    # Konfiguracja logowania
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Inicjalizacja buildera promptów
    builder = PromptBuilder()
    
    # Przykładowe dane
    symbol = "EURUSD"
    timeframe = "H1"
    
    price_data = [
        {"time": "2023-06-01 12:00", "open": 1.0750, "high": 1.0765, "low": 1.0745, "close": 1.0760, "tick_volume": 1250},
        {"time": "2023-06-01 13:00", "open": 1.0760, "high": 1.0780, "low": 1.0755, "close": 1.0775, "tick_volume": 1300},
        {"time": "2023-06-01 14:00", "open": 1.0775, "high": 1.0785, "low": 1.0770, "close": 1.0780, "tick_volume": 1150},
    ]
    
    indicators = {
        "MA(20)": [1.0720, 1.0725, 1.0730, 1.0735, 1.0740],
        "RSI(14)": [45.5, 48.2, 52.7, 58.3, 62.1],
        "MACD": [0.0012, 0.0015, 0.0018, 0.0022, 0.0025]
    }
    
    # Generowanie promptu
    prompt = builder.build_market_analysis_prompt(
        symbol=symbol,
        timeframe=timeframe,
        price_data=price_data,
        indicators=indicators,
        strategy_name="Trend Following",
        risk_level="medium"
    )
    
    print("Wygenerowany prompt:")
    print(prompt) 
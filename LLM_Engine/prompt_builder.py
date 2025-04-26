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
        self.system_prompt = ""
        self.user_prompt = ""
        self.prompt_variables = {}
        
    def set_system_prompt(self, prompt: str) -> None:
        """Ustawia prompt systemowy."""
        self.system_prompt = prompt
        
    def set_user_prompt(self, prompt: str) -> None:
        """Ustawia prompt użytkownika."""
        self.user_prompt = prompt
        
    def add_variable(self, name: str, value: Any) -> None:
        """Dodaje zmienną do promptu."""
        self.prompt_variables[name] = value
        
    def add_variables(self, variables: Dict[str, Any]) -> None:
        """Dodaje wiele zmiennych do promptu."""
        self.prompt_variables.update(variables)
        
    def build(self) -> Dict[str, str]:
        """Buduje finalny prompt."""
        system_prompt = self.system_prompt.format(**self.prompt_variables)
        user_prompt = self.user_prompt.format(**self.prompt_variables)
        return {
            "system": system_prompt,
            "user": user_prompt
        }
            
    def reset(self) -> None:
        """Resetuje builder do stanu początkowego."""
        self.system_prompt = ""
        self.user_prompt = ""
        self.prompt_variables = {}
        
    def clone(self):
        """Tworzy kopię buildera."""
        new_builder = PromptBuilder(self.templates_path)
        new_builder.system_prompt = self.system_prompt
        new_builder.user_prompt = self.user_prompt
        new_builder.prompt_variables = self.prompt_variables.copy()
        return new_builder
        
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

    def build_stop_loss_prompt(
        self,
        entry_price: float,
        risk_level: str,
        trend: str,
        support_levels: List[float],
        volatility: float
    ) -> str:
        """
        Buduje prompt do obliczenia poziomu stop loss.
        
        Args:
            entry_price: Cena wejścia
            risk_level: Poziom ryzyka ("low", "medium", "high")
            trend: Kierunek trendu ("bullish", "bearish")
            support_levels: Lista poziomów wsparcia
            volatility: Zmienność rynku (ATR)
            
        Returns:
            str: Prompt do wysłania do modelu
        """
        prompt = f"""### Obliczenie Stop Loss
Cena wejścia: {entry_price}
Poziom ryzyka: {risk_level}
Trend: {trend}
Poziomy wsparcia: {', '.join(map(str, support_levels))}
Zmienność (ATR): {volatility}

Zadanie:
Oblicz optymalny poziom stop loss uwzględniając:
1. Poziom ryzyka
2. Kierunek trendu
3. Najbliższe poziomy wsparcia
4. Zmienność rynku

Odpowiedź w formacie JSON:
{{
  "stop_loss": float,
  "explanation": string
}}
"""
        return prompt
        
    def build_take_profit_prompt(
        self,
        entry_price: float,
        risk_reward: float,
        stop_loss: float,
        resistance_levels: List[float],
        trend: str
    ) -> str:
        """
        Buduje prompt do obliczenia poziomu take profit.
        
        Args:
            entry_price: Cena wejścia
            risk_reward: Oczekiwany stosunek zysku do ryzyka
            stop_loss: Poziom stop loss
            resistance_levels: Lista poziomów oporu
            trend: Kierunek trendu ("bullish", "bearish")
            
        Returns:
            str: Prompt do wysłania do modelu
        """
        prompt = f"""### Obliczenie Take Profit
Cena wejścia: {entry_price}
Stop Loss: {stop_loss}
Oczekiwany RR: {risk_reward}
Trend: {trend}
Poziomy oporu: {', '.join(map(str, resistance_levels))}

Zadanie:
Oblicz optymalny poziom take profit uwzględniając:
1. Oczekiwany stosunek zysku do ryzyka
2. Kierunek trendu
3. Najbliższe poziomy oporu
4. Dystans od stop loss

Odpowiedź w formacie JSON:
{{
  "take_profit": float,
  "explanation": string
}}
"""
        return prompt
        
    def build_trade_idea_prompt(
        self,
        market_analysis: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        current_price: float
    ) -> str:
        """
        Buduje prompt do wygenerowania pomysłu handlowego.
        
        Args:
            market_analysis: Wynik analizy rynku
            risk_assessment: Ocena ryzyka
            current_price: Aktualna cena
            
        Returns:
            str: Prompt do wysłania do modelu
        """
        # Formatowanie analizy rynku
        trend = market_analysis.get("trend", "unknown")
        strength = market_analysis.get("strength", 0)
        key_levels = market_analysis.get("key_levels", {})
        recommendation = market_analysis.get("recommendation", "none")
        
        # Formatowanie oceny ryzyka
        risk_level = risk_assessment.get("level", "medium")
        risk_factors = risk_assessment.get("factors", [])
        risk_recommendations = risk_assessment.get("recommendations", [])
        
        prompt = f"""### Generowanie Pomysłu Handlowego

Analiza Rynku:
- Trend: {trend} (siła: {strength}/10)
- Rekomendacja: {recommendation}
- Poziomy kluczowe:
  * Wsparcia: {', '.join(map(str, key_levels.get('support', [])))}
  * Opory: {', '.join(map(str, key_levels.get('resistance', [])))}

Ocena Ryzyka:
- Poziom: {risk_level}
- Czynniki: {', '.join(risk_factors)}
- Rekomendacje: {', '.join(risk_recommendations)}

Aktualna cena: {current_price}

Zadanie:
Wygeneruj precyzyjny pomysł handlowy uwzględniając powyższe dane.

Odpowiedź w formacie JSON:
{{
  "direction": "buy/sell",
  "entry_price": float,
  "stop_loss": float,
  "take_profit": float,
  "risk_reward": float,
  "explanation": string,
  "additional_conditions": [string]
}}
"""
        return prompt

class TradingPromptBuilder(PromptBuilder):
    """
    Klasa odpowiedzialna za budowanie promptów do analizy handlowej.
    
    Specjalizuje się w tworzeniu promptów zawierających dane rynkowe,
    informacje o parach walutowych, interwałach czasowych i wskaźnikach technicznych.
    """
    
    def __init__(self, templates_path: Optional[str] = None):
        """
        Inicjalizuje budowniczego promptów handlowych.
        
        Args:
            templates_path: Opcjonalna ścieżka do katalogu z szablonami promptów
        """
        super().__init__(templates_path)
        self.system_prompt = "Jesteś ekspertem w handlu na rynkach finansowych, specjalizującym się w analizie technicznej i fundamentalnej."
        self.user_prompt = ""
        self.prompt_variables = {}
    
    def set_market_context(self, context: str) -> None:
        """
        Ustawia kontekst rynkowy dla promptu.
        
        Args:
            context: Opis aktualnej sytuacji rynkowej
        """
        self.user_prompt += f"\n\n### Kontekst rynkowy\n{context}"
    
    def add_trading_pair(self, pair: str) -> None:
        """
        Dodaje informację o parze handlowej.
        
        Args:
            pair: Symbol pary handlowej (np. "EURUSD")
        """
        self.prompt_variables["pair"] = pair
    
    def add_timeframe(self, timeframe: str) -> None:
        """
        Dodaje informację o interwale czasowym.
        
        Args:
            timeframe: Interwał czasowy (np. "H1", "D1")
        """
        self.prompt_variables["timeframe"] = timeframe
    
    def add_indicators(self, indicators: List[str]) -> None:
        """
        Dodaje listę wskaźników do analizy.
        
        Args:
            indicators: Lista nazw wskaźników technicznych
        """
        indicators_text = ", ".join(indicators)
        self.user_prompt += f"\n\n### Wskaźniki techniczne\nPrzy analizie uwzględnij następujące wskaźniki: {indicators_text}"
    
    def request_trade_signals(self) -> None:
        """
        Dodaje prośbę o generowanie sygnałów handlowych.
        """
        pair = self.prompt_variables.get("pair", "[PARA]")
        timeframe = self.prompt_variables.get("timeframe", "[INTERWAŁ]")
        
        self.user_prompt += f"\n\n### Prośba o sygnał\nWygeneruj sygnał handlowy dla pary {pair} na interwale {timeframe}. " \
                           f"Określ kierunek (kupno/sprzedaż), cenę wejścia, poziom stop-loss i take-profit. " \
                           f"Przedstaw odpowiedź w formacie JSON."
    
    def build(self) -> Dict[str, str]:
        """
        Buduje kompletny prompt handlowy.
        
        Returns:
            Dict[str, str]: Słownik zawierający prompty systemowy i użytkownika
        """
        # Zastąp zmienne w promptach
        system = self.system_prompt
        user = self.user_prompt
        
        for key, value in self.prompt_variables.items():
            placeholder = f"{{{key}}}"
            system = system.replace(placeholder, str(value))
            user = user.replace(placeholder, str(value))
        
        return {
            "system": system,
            "user": user
        }
    
    def clone(self):
        """
        Tworzy kopię budowniczego promptów.
        
        Returns:
            TradingPromptBuilder: Nowa instancja z tymi samymi ustawieniami
        """
        clone = TradingPromptBuilder(self.templates_path)
        clone.system_prompt = self.system_prompt
        clone.user_prompt = self.user_prompt
        clone.prompt_variables = self.prompt_variables.copy()
        return clone
    
    def reset(self) -> None:
        """
        Resetuje builder do stanu początkowego.
        """
        self.system_prompt = "Jesteś ekspertem w handlu na rynkach finansowych, specjalizującym się w analizie technicznej i fundamentalnej."
        self.user_prompt = ""
        self.prompt_variables = {}

class MarketAnalysisPromptBuilder(PromptBuilder):
    """
    Klasa odpowiedzialna za budowanie promptów do analizy rynku.
    
    Specjalizuje się w tworzeniu promptów zawierających dane rynkowe,
    kontekst rynkowy i wskaźniki techniczne dla modeli LLM.
    """
    
    def __init__(self, templates_path: Optional[str] = None):
        """
        Inicjalizacja budowniczego promptów do analizy rynku.
        
        Args:
            templates_path: Opcjonalna ścieżka do katalogu z szablonami promptów
        """
        super().__init__(templates_path)
        self.system_prompt = "Jesteś ekspertem w analizie rynków finansowych, specjalizującym się w analizie technicznej i fundamentalnej. Twoim zadaniem jest dostarczenie dokładnej analizy sytuacji rynkowej i zidentyfikowanie potencjalnych szans handlowych."
        self.user_prompt = ""
        self.instrument = None
        self.timeframe = None
        
    def add_instrument(self, symbol: str, timeframe: str = "H1"):
        """
        Dodaje instrument do analizy.
        
        Args:
            symbol: Symbol instrumentu
            timeframe: Interwał czasowy (domyślnie H1)
        """
        self.instrument = symbol
        self.timeframe = timeframe
        self.add_variable("instrument", symbol)
        self.add_variable("timeframe", timeframe)
        
        self.user_prompt += f"\n\nPrzeanalizuj instrument: {symbol} na interwale {timeframe}"
    
    def add_analysis_period(self, period: str):
        """
        Dodaje informacje o okresie analizy.
        
        Args:
            period: Opis okresu analizy (np. "ostatni tydzień", "od 2023-01-01 do 2023-02-01")
        """
        self.prompt_variables["period"] = period
        self.user_prompt += f"\nOkres analizy: {period}"
    
    def request_technical_analysis(self, include_indicators: List[str] = None):
        """
        Dodaje prośbę o analizę techniczną.
        
        Args:
            include_indicators: Lista wskaźników technicznych do uwzględnienia (opcjonalna)
        """
        self.user_prompt += "\n\n### Analiza techniczna\n"
        self.user_prompt += "Przeprowadź szczegółową analizę techniczną, w tym identyfikację trendu, poziomów wsparcia i oporu oraz kluczowych formacji cenowych."
        
        if include_indicators:
            indicators_text = ", ".join(include_indicators)
            self.user_prompt += f"\nUwzględnij następujące wskaźniki techniczne: {indicators_text}"
            
        self.user_prompt += "\n\nTwoja odpowiedź powinna zawierać:\n"
        self.user_prompt += "1. Aktualny trend (wzrostowy/spadkowy/boczny)\n"
        self.user_prompt += "2. Kluczowe poziomy wsparcia i oporu\n"
        self.user_prompt += "3. Ważne formacje cenowe\n"
        self.user_prompt += "4. Potencjalne punkty zwrotne\n"
        self.user_prompt += "5. Rekomendację działania (kupno/sprzedaż/wstrzymanie się)"
    
    def request_fundamental_analysis(self, include_factors: List[str] = None):
        """
        Dodaje prośbę o analizę fundamentalną.
        
        Args:
            include_factors: Lista czynników fundamentalnych do uwzględnienia (opcjonalna)
        """
        self.user_prompt += "\n\n### Analiza fundamentalna\n"
        self.user_prompt += "Przeprowadź analizę fundamentalną, uwzględniając czynniki makroekonomiczne i rynkowe."
        
        if include_factors:
            factors_text = ", ".join(include_factors)
            self.user_prompt += f"\nUwzględnij następujące czynniki: {factors_text}"
            
        self.user_prompt += "\n\nTwoja odpowiedź powinna zawierać:\n"
        self.user_prompt += "1. Kluczowe czynniki wpływające na instrument\n"
        self.user_prompt += "2. Aktualne dane ekonomiczne\n"
        self.user_prompt += "3. Wpływ polityki monetarnej\n"
        self.user_prompt += "4. Nastroje rynkowe\n"
        self.user_prompt += "5. Długoterminową perspektywę"
    
    def request_sentiment_analysis(self):
        """
        Dodaje prośbę o analizę sentymentu rynkowego.
        """
        self.user_prompt += "\n\n### Analiza sentymentu\n"
        self.user_prompt += "Przeprowadź analizę sentymentu rynkowego dla tego instrumentu."
        
        self.user_prompt += "\n\nTwoja odpowiedź powinna zawierać:\n"
        self.user_prompt += "1. Aktualny sentyment rynkowy (byczki/niedźwiedzie/neutralny)\n"
        self.user_prompt += "2. Wskaźniki sentymentu (pozycje traderów, optymizm/pesymizm uczestników rynku)\n"
        self.user_prompt += "3. Potencjalne zmiany sentymentu\n"
        self.user_prompt += "4. Wpływ sentymentu na przyszłe ruchy cen"


class RiskAssessmentPromptBuilder(PromptBuilder):
    """
    Klasa odpowiedzialna za budowanie promptów do oceny ryzyka.
    
    Specjalizuje się w tworzeniu promptów dotyczących zarządzania ryzykiem,
    kalkulacji wielkości pozycji i oceny stosunku ryzyka do zysku.
    """
    
    def __init__(self, templates_path: Optional[str] = None):
        """
        Inicjalizacja budowniczego promptów do oceny ryzyka.
        
        Args:
            templates_path: Opcjonalna ścieżka do katalogu z szablonami promptów
        """
        super().__init__(templates_path)
        self.system_prompt = "Jesteś ekspertem w zarządzaniu ryzykiem na rynkach finansowych. Twoim zadaniem jest ocena ryzyka potencjalnych transakcji oraz dostarczenie zaleceń dotyczących zarządzania kapitałem i minimalizacji potencjalnych strat."
        self.user_prompt = ""
        self.trade_details = {}
        
    def add_trade_details(self, pair: str, direction: str, entry_price: float, stop_loss: float, take_profit: float, lot_size: float = None):
        """
        Dodaje szczegóły transakcji do analizy.
        
        Args:
            pair: Symbol pary walutowej
            direction: Kierunek transakcji (BUY/SELL)
            entry_price: Cena wejścia
            stop_loss: Poziom stop loss
            take_profit: Poziom take profit
            lot_size: Wielkość pozycji (opcjonalne)
        """
        self.trade_details = {
            "pair": pair,
            "direction": direction.upper(),
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit
        }
        
        if lot_size is not None:
            self.trade_details["lot_size"] = lot_size
            
        self.add_variables(self.trade_details)
    
    def request_risk_reward_analysis(self, account_balance: float = None, risk_tolerance: str = "medium"):
        """
        Dodaje prośbę o analizę stosunku ryzyka do zysku.
        
        Args:
            account_balance: Saldo konta (opcjonalne)
            risk_tolerance: Tolerancja ryzyka (opcjonalna)
        """
        self.prompt_variables.update({
            "account_balance": account_balance,
            "risk_tolerance": risk_tolerance
        })
        
        self.user_prompt += "\n\n### Analiza ryzyka i zysku\n"
        self.user_prompt += "Przeprowadź szczegółową analizę stosunku ryzyka do zysku dla powyższej transakcji."
        
        if account_balance:
            self.user_prompt += f"\nSaldo konta: {account_balance}"
            
        self.user_prompt += f"\nTolerancja ryzyka: {risk_tolerance.upper()}"
        
        self.user_prompt += "\n\nTwoja odpowiedź powinna zawierać:\n"
        self.user_prompt += "1. Stosunek ryzyka do zysku (R:R)\n"
        self.user_prompt += "2. Ryzyko w pipach/punktach\n"
        self.user_prompt += "3. Potencjalny zysk w pipach/punktach\n"
        self.user_prompt += "4. Ocenę jakości transakcji\n"
        self.user_prompt += "5. Zalecenia dotyczące modyfikacji poziomów (jeśli potrzebne)"
    
    def request_position_sizing_advice(self, account_balance: float, max_risk_percent: float = 2.0, existing_positions: int = 0):
        """
        Dodaje prośbę o zalecenia dotyczące wielkości pozycji.
        
        Args:
            account_balance: Saldo konta
            max_risk_percent: Maksymalny procent ryzyka na transakcję
            existing_positions: Liczba istniejących pozycji
        """
        self.prompt_variables.update({
            "account_balance": account_balance,
            "max_risk_percent": max_risk_percent,
            "existing_positions": existing_positions
        })
        
        self.user_prompt += "\n\n### Zalecenia dotyczące wielkości pozycji\n"
        self.user_prompt += f"Saldo konta: {account_balance}\n"
        self.user_prompt += f"Maksymalny procent ryzyka na transakcję: {max_risk_percent}%\n"
        self.user_prompt += f"Liczba istniejących pozycji: {existing_positions}"
        
        self.user_prompt += "\n\nOblicz i zaleć optymalną wielkość pozycji, uwzględniając:\n"
        self.user_prompt += "1. Maksymalną kwotę do zaryzykowania\n"
        self.user_prompt += "2. Wielkość pozycji w lotach/kontraktach\n"
        self.user_prompt += "3. Wpływ na łączne ryzyko portfela\n"
        self.user_prompt += "4. Potencjalny wpływ na saldo konta (najgorszy scenariusz)\n"
        self.user_prompt += "5. Zalecenia dotyczące zarządzania wieloma pozycjami (jeśli dotyczy)"


class TradeSignalPromptBuilder(PromptBuilder):
    """
    Klasa odpowiedzialna za budowanie promptów do generowania sygnałów handlowych.
    
    Specjalizuje się w tworzeniu promptów wymagających konkretnych sygnałów
    wejścia i wyjścia na podstawie analizy technicznej i danych rynkowych.
    """
    
    def __init__(self, templates_path: Optional[str] = None):
        """
        Inicjalizacja budowniczego promptów do sygnałów handlowych.
        
        Args:
            templates_path: Opcjonalna ścieżka do katalogu z szablonami promptów
        """
        super().__init__(templates_path)
        self.system_prompt = "Jesteś ekspertem w tradingu na rynkach finansowych. Twoim zadaniem jest analiza danych rynkowych i generowanie precyzyjnych sygnałów handlowych z konkretnymi poziomami wejścia, stop loss i take profit."
        self.user_prompt = ""
        self.market_data = {}
        
    def add_market_data(self, pair: str, timeframe: str, current_price: float, high: float = None, low: float = None, volume: float = None):
        """
        Dodaje dane rynkowe do analizy.
        
        Args:
            pair: Symbol pary walutowej
            timeframe: Interwał czasowy
            current_price: Aktualna cena
            high: Najwyższa cena (opcjonalne)
            low: Najniższa cena (opcjonalne)
            volume: Wolumen (opcjonalne)
        """
        self.market_data = {
            "pair": pair,
            "timeframe": timeframe,
            "current_price": current_price
        }
        
        if high is not None:
            self.market_data["high"] = high
        if low is not None:
            self.market_data["low"] = low
        if volume is not None:
            self.market_data["volume"] = volume
            
        # Dodaj dane rynkowe do promptu użytkownika
        self.user_prompt += "\n### Dane rynkowe\n"
        self.user_prompt += f"Para walutowa: {pair}\n"
        self.user_prompt += f"Interwał czasowy: {timeframe}\n"
        self.user_prompt += f"Aktualna cena: {current_price}\n"
        
        if high is not None:
            self.user_prompt += f"Cena najwyższa: {high}\n"
        if low is not None:
            self.user_prompt += f"Cena najniższa: {low}\n"
        if volume is not None:
            self.user_prompt += f"Wolumen: {volume}\n"
            
        # Dodaj zmienne do szablonu
        self.add_variables(self.market_data)
    
    def add_indicator_values(self, indicators: Dict[str, Any]):
        """
        Dodaje wartości wskaźników technicznych do promptu.
        
        Args:
            indicators: Słownik z wartościami wskaźników
        """
        self.prompt_variables["indicators"] = indicators
        
        self.user_prompt += "\n### Wskaźniki techniczne\n"
        
        for name, values in indicators.items():
            self.user_prompt += f"{name.upper()}: "
            
            if isinstance(values, list):
                # Wyświetl tylko ostatnie 3 wartości
                display_values = values[-3:] if len(values) > 3 else values
                self.user_prompt += ", ".join([str(v) for v in display_values])
            else:
                self.user_prompt += str(values)
                
            self.user_prompt += "\n"
    
    def request_entry_signal(self, strategy: str = None):
        """
        Dodaje prośbę o sygnał wejścia.
        
        Args:
            strategy: Nazwa strategii (opcjonalna)
        """
        self.user_prompt += "\n\n### Sygnał wejścia\n"
        
        if strategy:
            self.prompt_variables["strategy"] = strategy
            self.user_prompt += f"Strategia: {strategy}\n\n"
            
        self.user_prompt += "Wygeneruj konkretny sygnał wejścia dla tego instrumentu na podstawie analizy technicznej."
        
        self.user_prompt += "\n\nTwoja odpowiedź powinna zawierać:\n"
        self.user_prompt += "1. Kierunek transakcji (BUY/SELL)\n"
        self.user_prompt += "2. Konkretną cenę wejścia\n"
        self.user_prompt += "3. Konkretny poziom Stop Loss\n"
        self.user_prompt += "4. Konkretny poziom Take Profit\n"
        self.user_prompt += "5. Stosunek ryzyka do zysku (R:R)\n"
        self.user_prompt += "6. Uzasadnienie techniczne"
    
    def request_exit_signal(self, entry_price: float, entry_direction: str, current_profit: float = None):
        """
        Dodaje prośbę o sygnał wyjścia.
        
        Args:
            entry_price: Cena wejścia
            entry_direction: Kierunek transakcji ("buy" lub "sell")
            current_profit: Aktualny zysk/strata (opcjonalny)
        """
        self.prompt_variables.update({
            "entry_price": entry_price,
            "entry_direction": entry_direction
        })
        
        if current_profit is not None:
            self.prompt_variables["current_profit"] = current_profit
            
        dir_text = "KUPNO" if entry_direction.lower() == "buy" else "SPRZEDAŻ"
        
        self.user_prompt += "\n\n### Sygnał wyjścia\n"
        self.user_prompt += f"Aktualna pozycja: {dir_text} z ceną wejścia {entry_price}\n"
        
        if current_profit is not None:
            profit_text = "zysk" if current_profit >= 0 else "strata"
            self.user_prompt += f"Aktualny {profit_text}: {abs(current_profit)}\n"
            
        self.user_prompt += "\nOceń, czy należy zamknąć pozycję, przesunąć Stop Loss lub Take Profit."
        
        self.user_prompt += "\n\nTwoja odpowiedź powinna zawierać:\n"
        self.user_prompt += "1. Decyzję (ZAMKNIJ/TRZYMAJ/ZMODYFIKUJ)\n"
        self.user_prompt += "2. Uzasadnienie techniczne\n"
        self.user_prompt += "3. Nowy poziom Stop Loss (jeśli dotyczy)\n"
        self.user_prompt += "4. Nowy poziom Take Profit (jeśli dotyczy)\n"
        self.user_prompt += "5. Dodatkowe uwagi dotyczące zarządzania pozycją"

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
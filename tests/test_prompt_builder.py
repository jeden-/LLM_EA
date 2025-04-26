"""
Testy dla budowniczego promptów LLM.

Ten moduł zawiera testy jednostkowe dla funkcjonalności związanych
z budowaniem i dostosowywaniem promptów dla modeli językowych (LLM).
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Dodanie ścieżki głównego katalogu projektu do PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LLM_Engine.prompt_builder import (
    PromptBuilder,
    TradingPromptBuilder,
    MarketAnalysisPromptBuilder,
    RiskAssessmentPromptBuilder,
    TradeSignalPromptBuilder
)

class TestPromptBuilder(unittest.TestCase):
    """Testy dla bazowej klasy PromptBuilder i jej metod."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.builder = PromptBuilder()
        
    def test_init(self):
        """Test inicjalizacji budowniczego promptów."""
        self.assertEqual(self.builder.system_prompt, "")
        self.assertEqual(self.builder.user_prompt, "")
        self.assertEqual(self.builder.prompt_variables, {})
        
    def test_set_system_prompt(self):
        """Test ustawiania promptu systemowego."""
        system_prompt = "Jesteś ekspertem od analizy rynków finansowych."
        self.builder.set_system_prompt(system_prompt)
        self.assertEqual(self.builder.system_prompt, system_prompt)
        
    def test_set_user_prompt(self):
        """Test ustawiania promptu użytkownika."""
        user_prompt = "Przeanalizuj aktualną sytuację na rynku."
        self.builder.set_user_prompt(user_prompt)
        self.assertEqual(self.builder.user_prompt, user_prompt)
        
    def test_add_variable(self):
        """Test dodawania zmiennej do promptu."""
        self.builder.add_variable("market", "forex")
        self.assertEqual(self.builder.prompt_variables["market"], "forex")
        
    def test_add_variables(self):
        """Test dodawania wielu zmiennych do promptu."""
        variables = {"market": "forex", "pair": "EURUSD"}
        self.builder.add_variables(variables)
        self.assertEqual(self.builder.prompt_variables["market"], "forex")
        self.assertEqual(self.builder.prompt_variables["pair"], "EURUSD")
        
    def test_build(self):
        """Test budowania promptu."""
        # Konfiguracja budowniczego
        self.builder.set_system_prompt("Jesteś ekspertem od {market}.")
        self.builder.set_user_prompt("Przeanalizuj parę {pair} na interwale {timeframe}.")
        self.builder.add_variables({
            "market": "forex",
            "pair": "EURUSD",
            "timeframe": "H4"
        })
        
        # Budowanie promptu
        prompt = self.builder.build()
        
        # Weryfikacja
        self.assertEqual(prompt["system"], "Jesteś ekspertem od forex.")
        self.assertEqual(prompt["user"], "Przeanalizuj parę EURUSD na interwale H4.")
        
    def test_build_with_missing_variables(self):
        """Test budowania promptu z brakującymi zmiennymi."""
        # Konfiguracja budowniczego
        self.builder.set_system_prompt("Jesteś ekspertem od {market}.")
        self.builder.set_user_prompt("Przeanalizuj parę {pair} na interwale {timeframe}.")
        self.builder.add_variable("market", "forex")
        self.builder.add_variable("pair", "EURUSD")
        # Brak zmiennej timeframe
        
        # Próba budowania promptu
        with self.assertRaises(KeyError):
            self.builder.build()
    
    def test_reset(self):
        """Test resetowania budowniczego promptów."""
        # Konfiguracja budowniczego
        self.builder.set_system_prompt("Jesteś ekspertem od analizy rynków.")
        self.builder.set_user_prompt("Przeanalizuj sytuację na rynku.")
        self.builder.add_variable("market", "forex")
        
        # Reset budowniczego
        self.builder.reset()
        
        # Weryfikacja
        self.assertEqual(self.builder.system_prompt, "")
        self.assertEqual(self.builder.user_prompt, "")
        self.assertEqual(self.builder.prompt_variables, {})
    
    def test_clone(self):
        """Test klonowania budowniczego promptów."""
        # Konfiguracja budowniczego
        self.builder.set_system_prompt("Jesteś ekspertem od analizy rynków.")
        self.builder.set_user_prompt("Przeanalizuj sytuację na rynku.")
        self.builder.add_variable("market", "forex")
        
        # Klonowanie budowniczego
        cloned_builder = self.builder.clone()
        
        # Weryfikacja
        self.assertEqual(cloned_builder.system_prompt, self.builder.system_prompt)
        self.assertEqual(cloned_builder.user_prompt, self.builder.user_prompt)
        self.assertEqual(cloned_builder.prompt_variables, self.builder.prompt_variables)
        
        # Sprawdzenie, czy to faktycznie kopia (a nie ten sam obiekt)
        self.assertIsNot(cloned_builder, self.builder)
        
        # Sprawdzenie, czy zmiana w sklonowanym obiekcie nie wpływa na oryginał
        cloned_builder.add_variable("new_var", "value")
        self.assertNotIn("new_var", self.builder.prompt_variables)


class TestTradingPromptBuilder(unittest.TestCase):
    """Testy dla klasy TradingPromptBuilder."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.builder = TradingPromptBuilder()
        
    def test_init(self):
        """Test inicjalizacji budowniczego promptów handlowych."""
        # Sprawdzenie domyślnych wartości
        self.assertIn("ekspert", self.builder.system_prompt.lower())
        self.assertIn("handlu", self.builder.system_prompt.lower())
        
    def test_set_market_context(self):
        """Test ustawiania kontekstu rynkowego."""
        context = "Rynek jest w trendzie wzrostowym od 3 dni."
        self.builder.set_market_context(context)
        
        # Weryfikacja
        self.assertIn(context, self.builder.user_prompt)
        
    def test_add_trading_pair(self):
        """Test dodawania pary handlowej."""
        pair = "EURUSD"
        self.builder.add_trading_pair(pair)
        
        # Weryfikacja
        self.assertEqual(self.builder.prompt_variables["pair"], pair)
        
    def test_add_timeframe(self):
        """Test dodawania interwału czasowego."""
        timeframe = "H4"
        self.builder.add_timeframe(timeframe)
        
        # Weryfikacja
        self.assertEqual(self.builder.prompt_variables["timeframe"], timeframe)
        
    def test_add_indicators(self):
        """Test dodawania wskaźników technicznych."""
        indicators = ["RSI", "MACD", "Moving Average"]
        self.builder.add_indicators(indicators)
        
        # Weryfikacja
        prompt = self.builder.build()
        for indicator in indicators:
            self.assertIn(indicator, prompt["user"])
            
    def test_request_trade_signals(self):
        """Test żądania sygnałów handlowych."""
        # Dodanie niezbędnych zmiennych
        self.builder.add_trading_pair("EURUSD")
        self.builder.add_timeframe("H4")
        
        # Żądanie sygnałów handlowych
        self.builder.request_trade_signals()
        
        # Budowanie promptu
        prompt = self.builder.build()
        
        # Weryfikacja
        self.assertIn("sygnał", prompt["user"].lower())
        self.assertIn("handlowy", prompt["user"].lower())
        self.assertIn("EURUSD", prompt["user"])
        self.assertIn("H4", prompt["user"])


class TestMarketAnalysisPromptBuilder(unittest.TestCase):
    """Testy dla klasy MarketAnalysisPromptBuilder."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.builder = MarketAnalysisPromptBuilder()
        
    def test_init(self):
        """Test inicjalizacji budowniczego promptów analizy rynku."""
        # Sprawdzenie domyślnych wartości
        self.assertIn("ekspert", self.builder.system_prompt.lower())
        self.assertIn("analizie", self.builder.system_prompt.lower())
        
    def test_add_instrument(self):
        """Test dodawania instrumentu finansowego."""
        instrument = "EURUSD"
        self.builder.add_instrument(instrument)
        
        # Weryfikacja
        self.assertEqual(self.builder.prompt_variables["instrument"], instrument)
        
    def test_add_analysis_period(self):
        """Test dodawania okresu analizy."""
        period = "last week"
        self.builder.add_analysis_period(period)
        
        # Weryfikacja
        self.assertEqual(self.builder.prompt_variables["period"], period)
        
    def test_request_technical_analysis(self):
        """Test żądania analizy technicznej."""
        # Dodanie niezbędnych zmiennych
        self.builder.add_instrument("EURUSD")
        self.builder.add_analysis_period("last week")

        # Żądanie analizy technicznej
        self.builder.request_technical_analysis()

        # Budowanie promptu
        prompt = self.builder.build()

        # Weryfikacja
        self.assertIn("analiza techniczna", prompt["user"].lower())
        self.assertIn("trend", prompt["user"].lower())
        self.assertIn("wsparcia", prompt["user"].lower())
        
    def test_request_fundamental_analysis(self):
        """Test żądania analizy fundamentalnej."""
        # Dodanie niezbędnych zmiennych
        self.builder.add_instrument("EURUSD")
        
        # Żądanie analizy fundamentalnej
        self.builder.request_fundamental_analysis()
        
        # Budowanie promptu
        prompt = self.builder.build()
        
        # Weryfikacja
        self.assertIn("fundamentalna", prompt["user"].lower())
        self.assertIn("EURUSD", prompt["user"])
        
    def test_request_sentiment_analysis(self):
        """Test żądania analizy sentymentu."""
        # Dodanie niezbędnych zmiennych
        self.builder.add_instrument("EURUSD")
        
        # Żądanie analizy sentymentu
        self.builder.request_sentiment_analysis()
        
        # Budowanie promptu
        prompt = self.builder.build()
        
        # Weryfikacja
        self.assertIn("sentyment", prompt["user"].lower())
        self.assertIn("EURUSD", prompt["user"])


class TestRiskAssessmentPromptBuilder(unittest.TestCase):
    """Testy dla klasy RiskAssessmentPromptBuilder."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.builder = RiskAssessmentPromptBuilder()
        
    def test_init(self):
        """Test inicjalizacji budowniczego promptów oceny ryzyka."""
        # Sprawdzenie domyślnych wartości
        self.assertIn("ekspert", self.builder.system_prompt.lower())
        self.assertIn("ryzykiem", self.builder.system_prompt.lower())
        
    def test_add_trade_details(self):
        """Test dodawania szczegółów transakcji."""
        details = {
            "pair": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.0950,
            "stop_loss": 1.0900,
            "take_profit": 1.1050,
            "lot_size": 0.1
        }
        
        self.builder.add_trade_details(**details)
        
        # Weryfikacja
        for key, value in details.items():
            self.assertEqual(self.builder.prompt_variables[key], value)
            
    def test_request_risk_reward_analysis(self):
        """Test żądania analizy stosunku ryzyka do zysku."""
        # Dodanie niezbędnych zmiennych
        self.builder.add_trade_details(
            pair="EURUSD",
            direction="BUY",
            entry_price=1.0950,
            stop_loss=1.0900,
            take_profit=1.1050
        )

        # Żądanie analizy stosunku ryzyka do zysku
        self.builder.request_risk_reward_analysis()

        # Budowanie promptu
        prompt = self.builder.build()

        # Weryfikacja
        self.assertIn("analiza ryzyka", prompt["user"].lower())
        self.assertIn("stosunek ryzyka do zysku", prompt["user"].lower())
        
    def test_request_position_sizing_advice(self):
        """Test żądania porady dotyczącej rozmiaru pozycji."""
        # Dodanie niezbędnych zmiennych
        self.builder.add_variable("account_balance", 10000)
        self.builder.add_variable("risk_percentage", 2)
        self.builder.add_trade_details(
            pair="EURUSD",
            direction="BUY",
            entry_price=1.0950,
            stop_loss=1.0900,
            take_profit=1.1050
        )

        # Żądanie porady dotyczącej wielkości pozycji
        self.builder.request_position_sizing_advice(10000, 2.0)

        # Budowanie promptu
        prompt = self.builder.build()

        # Weryfikacja
        self.assertIn("wielkość pozycji", prompt["user"].lower())
        self.assertIn("saldo konta", prompt["user"].lower())


class TestTradeSignalPromptBuilder(unittest.TestCase):
    """Testy dla klasy TradeSignalPromptBuilder."""
    
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.builder = TradeSignalPromptBuilder()
        
    def test_init(self):
        """Test inicjalizacji budowniczego promptów sygnałów handlowych."""
        self.assertIn("ekspert", self.builder.system_prompt.lower())
        self.assertIn("trading", self.builder.system_prompt.lower())
        self.assertEqual(self.builder.user_prompt, "")
        self.assertEqual(self.builder.market_data, {})
        
    def test_add_market_data(self):
        """Test dodawania danych rynkowych."""
        # Przygotowanie danych testowych
        pair = "EURUSD"
        timeframe = "H4"
        current_price = 1.1234
        high = 1.1300
        low = 1.1200
        volume = 1000.0
        
        # Dodanie danych rynkowych
        self.builder.add_market_data(
            pair=pair,
            timeframe=timeframe,
            current_price=current_price,
            high=high,
            low=low,
            volume=volume
        )
        
        # Weryfikacja danych w market_data
        self.assertEqual(self.builder.market_data["pair"], pair)
        self.assertEqual(self.builder.market_data["timeframe"], timeframe)
        self.assertEqual(self.builder.market_data["current_price"], current_price)
        self.assertEqual(self.builder.market_data["high"], high)
        self.assertEqual(self.builder.market_data["low"], low)
        self.assertEqual(self.builder.market_data["volume"], volume)
        
        # Weryfikacja promptu użytkownika
        prompt = self.builder.user_prompt
        self.assertIn("### Dane rynkowe", prompt)
        self.assertIn(f"Para walutowa: {pair}", prompt)
        self.assertIn(f"Interwał czasowy: {timeframe}", prompt)
        self.assertIn(f"Aktualna cena: {current_price}", prompt)
        self.assertIn(f"Cena najwyższa: {high}", prompt)
        self.assertIn(f"Cena najniższa: {low}", prompt)
        self.assertIn(f"Wolumen: {volume}", prompt)
        
    def test_add_market_data_minimal(self):
        """Test dodawania minimalnych danych rynkowych (bez opcjonalnych parametrów)."""
        # Przygotowanie danych testowych
        pair = "EURUSD"
        timeframe = "H4"
        current_price = 1.1234
        
        # Dodanie danych rynkowych
        self.builder.add_market_data(
            pair=pair,
            timeframe=timeframe,
            current_price=current_price
        )
        
        # Weryfikacja danych w market_data
        self.assertEqual(self.builder.market_data["pair"], pair)
        self.assertEqual(self.builder.market_data["timeframe"], timeframe)
        self.assertEqual(self.builder.market_data["current_price"], current_price)
        self.assertNotIn("high", self.builder.market_data)
        self.assertNotIn("low", self.builder.market_data)
        self.assertNotIn("volume", self.builder.market_data)
        
        # Weryfikacja promptu użytkownika
        prompt = self.builder.user_prompt
        self.assertIn("### Dane rynkowe", prompt)
        self.assertIn(f"Para walutowa: {pair}", prompt)
        self.assertIn(f"Interwał czasowy: {timeframe}", prompt)
        self.assertIn(f"Aktualna cena: {current_price}", prompt)
        self.assertNotIn("Cena najwyższa", prompt)
        self.assertNotIn("Cena najniższa", prompt)
        self.assertNotIn("Wolumen", prompt)
        
    def test_add_market_data_updates_variables(self):
        """Test czy dodawanie danych rynkowych aktualizuje zmienne promptu."""
        # Przygotowanie danych testowych
        pair = "EURUSD"
        timeframe = "H4"
        current_price = 1.1234
        
        # Dodanie danych rynkowych
        self.builder.add_market_data(
            pair=pair,
            timeframe=timeframe,
            current_price=current_price
        )
        
        # Weryfikacja zmiennych promptu
        self.assertEqual(self.builder.prompt_variables["pair"], pair)
        self.assertEqual(self.builder.prompt_variables["timeframe"], timeframe)
        self.assertEqual(self.builder.prompt_variables["current_price"], current_price)
        
        # Budowanie promptu i weryfikacja
        prompt = self.builder.build()
        self.assertIn(pair, prompt["user"])
        self.assertIn(timeframe, prompt["user"])
        self.assertIn(str(current_price), prompt["user"])


if __name__ == '__main__':
    unittest.main() 
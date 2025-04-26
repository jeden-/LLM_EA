"""
Test dla modułu market_analyzer.py
"""

import unittest
from unittest.mock import MagicMock, patch
import json
import os
import sys
from datetime import datetime
import pandas as pd
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from LLM_Engine.market_analyzer import MarketAnalyzer
from LLM_Engine.llm_interface import LLMInterface


class TestMarketAnalyzer(unittest.TestCase):
    """Testy dla klasy MarketAnalyzer."""
    
    def setUp(self):
        """Konfiguracja przed każdym testem."""
        # Mockowanie interfejsu LLM
        self.llm_interface_mock = MagicMock(spec=LLMInterface)
        self.llm_interface_mock.generate_response.return_value = json.dumps({
            "trend": "bullish",
            "strength": 7,
            "key_levels": {
                "support": [1.0780, 1.0750],
                "resistance": [1.0850, 1.0880]
            },
            "recommendation": "buy",
            "explanation": "Rynek wykazuje silny trend wzrostowy."
        })
        
        # Inicjalizacja analizatora rynku z mockiem
        self.analyzer = MarketAnalyzer(llm_interface=self.llm_interface_mock)
        
        # Przykładowe dane rynkowe
        self.market_data = {
            "symbol": "EURUSD",
            "timeframe": "H1",
            "current_price": 1.0750,
            "technical_indicators": {
                "moving_averages": [
                    {"type": "SMA", "period": 20, "value": 1.0720},
                    {"type": "EMA", "period": 50, "value": 1.0710}
                ],
                "rsi": {"period": 14, "value": 65.2},
                "macd": {"macd_line": 0.0015, "signal_line": 0.0010, "histogram": 0.0005},
                "bollinger_bands": {"upper": 1.0800, "middle": 1.0750, "lower": 1.0700, "bandwidth": 0.0100, "is_expanding": True}
            },
            "market_conditions": {
                "trend": {"description": "wzrostowy"},
                "volatility": {"value": 0.0075, "description": "średnia"},
                "volume": {"value": 1250, "comparison_to_average": "powyżej średniej"}
            },
            "significant_levels": {
                "support": [1.0730, 1.0700],
                "resistance": [1.0780, 1.0800],
                "recent_high": {"value": 1.0785, "time_ago": "2 hours ago"},
                "recent_low": {"value": 1.0695, "time_ago": "5 hours ago"}
            }
        }
    
    def test_prepare_market_data(self):
        """Test formatowania danych rynkowych."""
        formatted_data = self.analyzer.prepare_market_data(self.market_data)
        
        # Sprawdzenie podstawowych informacji
        self.assertEqual(formatted_data["symbol"], "EURUSD")
        self.assertEqual(formatted_data["timeframe"], "H1")
        self.assertEqual(formatted_data["current_price"], "1.075")
        
        # Sprawdzenie wskaźników technicznych
        self.assertIn("20 SMA (1.07200)", formatted_data["moving_averages"])
        self.assertIn("50 EMA (1.07100)", formatted_data["moving_averages"])
        self.assertIn("65.2", formatted_data["rsi"])
        self.assertIn("bullish", formatted_data["macd"].lower())
        
        # Sprawdzenie poziomów wsparcia i oporu
        self.assertIn("1.07300", formatted_data["support_levels"])
        self.assertIn("1.07000", formatted_data["support_levels"])
        self.assertIn("1.07800", formatted_data["resistance_levels"])
        self.assertIn("1.08000", formatted_data["resistance_levels"])
    
    def test_analyze_market(self):
        """Test analizy rynku."""
        # Przygotowanie danych serii cenowych i wolumenu
        prices = pd.Series(np.linspace(1.07, 1.08, 40))  # 40 punktów od 1.07 do 1.08
        volumes = pd.Series(np.random.randint(1000, 2000, 40))  # Losowe wolumeny
        
        # Mockowanie self.market_analysis w self.analyzer
        self.analyzer.market_analysis = MagicMock()
        
        # Mockowanie metod market_analysis
        self.analyzer.market_analysis.analyze_trend.return_value = {
            "trend": "bullish",
            "strength": 7,
            "volatility": "medium",
            "description": "Umiarkowany trend wzrostowy",
            "support_levels": [1.073, 1.071],
            "resistance_levels": [1.078, 1.081]
        }
        self.analyzer.market_analysis.generate_buy_signals.return_value = [35, 36, 38]  # Indeksy sygnałów
        self.analyzer.market_analysis.generate_sell_signals.return_value = []  # Brak sygnałów sprzedaży
        
        # Wywołanie metody
        result = self.analyzer.analyze_market(prices, volumes)
        
        # Sprawdzenie wyniku analizy - teraz nie sprawdzamy interfejsu LLM, tylko wywołania metod market_analysis
        self.analyzer.market_analysis.analyze_trend.assert_called_once_with(prices)
        self.analyzer.market_analysis.generate_buy_signals.assert_called_once()
        self.analyzer.market_analysis.generate_sell_signals.assert_called_once()
        
        # Sprawdzenie wyniku analizy
        self.assertEqual(result["trend"], "bullish")
        self.assertEqual(result["strength"], 7)
        self.assertIn("recommendation", result)
        
        # Sprawdzenie poziomów wsparcia i oporu
        self.assertEqual(len(result["support_levels"]), 2)
        self.assertEqual(len(result["resistance_levels"]), 2)
        self.assertEqual(len(result["key_levels"]), 4)  # 2 poziomy wsparcia + 2 poziomy oporu
    
    def test_evaluate_trade_setup(self):
        """Test oceny planu handlowego."""
        trade_data = {
            "symbol": "EURUSD",
            "direction": "buy",
            "entry_price": 1.0750,
            "stop_loss": 1.0700,
            "take_profit": 1.0850,
            "strategy": "trend following",
            "market_conditions": self.market_data["market_conditions"]
        }
        
        # Ustawienie wartości zwracanej przez generate_response
        self.llm_interface_mock.generate_response.return_value = json.dumps({
            "risk_score": 6,
            "probability_of_success": 65,
            "risk_reward_ratio": 2.0,
            "assessment": "Dobra okazja handlowa z akceptowalnym poziomem ryzyka.",
            "suggested_adjustments": {
                "entry_price": None,
                "stop_loss": 1.0710,
                "take_profit": None
            }
        })
        
        result = self.analyzer.evaluate_trade_setup(trade_data)
        
        # Sprawdzenie wyniku oceny
        self.assertIn("risk_score", result)
        self.assertIn("probability_of_success", result)
        self.assertIn("risk_reward_ratio", result)
        self.assertIn("assessment", result)
        self.assertIn("suggested_adjustments", result)
        
        # Sprawdzenie wartości
        self.assertEqual(result["risk_score"], 6)
        self.assertEqual(result["probability_of_success"], 65)
        self.assertEqual(result["suggested_adjustments"]["stop_loss"], 1.0710)


if __name__ == '__main__':
    unittest.main() 
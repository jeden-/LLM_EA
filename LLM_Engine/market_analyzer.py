"""
Module responsible for market analysis using LLM models.

This module:
1. Collects and formats market data
2. Constructs prompts using templates
3. Sends requests to LLM models
4. Processes and validates responses
5. Returns structured market analysis results
"""

import json
import logging
import re
import time
from typing import Dict, List, Tuple, Optional, Union, Any
from datetime import datetime
import pandas as pd

from .llm_interface import LLMInterface
from .market_analysis import MarketAnalysis
from .prompt_templates import get_prompt, get_system_prompt

# Configure logging
logger = logging.getLogger(__name__)

class MarketAnalyzer:
    """
    Class responsible for analyzing market data using LLM models.
    """
    
    def __init__(self, llm_interface: LLMInterface):
        """
        Initialize the MarketAnalyzer with a configured LLM interface.
        
        Args:
            llm_interface: Configured instance of LLMInterface
        """
        self.llm_interface = llm_interface
        self.logger = logger  # Przypisanie loggera z poziomu modułu do instancji
        logger.info("MarketAnalyzer initialized")
        self.market_analysis = MarketAnalysis()
    
    def prepare_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare and format market data for use in LLM prompts.
        
        Args:
            market_data: Raw market data from MT5
            
        Returns:
            Formatted market data ready for prompt templates
        """
        # Example of formatting and enriching market data
        formatted_data = {}
        
        # Basic symbol information
        formatted_data["symbol"] = market_data.get("symbol", "")
        formatted_data["timeframe"] = market_data.get("timeframe", "")
        formatted_data["current_price"] = str(market_data.get("current_price", ""))
        
        # Format technical indicators
        if "technical_indicators" in market_data:
            ti = market_data["technical_indicators"]
            
            # Moving averages
            ma_info = []
            for ma in ti.get("moving_averages", []):
                ma_info.append(f"{ma['period']} {ma['type']} ({ma['value']:.5f})")
            
            formatted_data["moving_averages"] = ", ".join(ma_info) if ma_info else "No data"
            
            # RSI
            if "rsi" in ti:
                rsi = ti["rsi"]
                rsi_value = rsi.get("value", 0)
                rsi_desc = "overbought" if rsi_value > 70 else "oversold" if rsi_value < 30 else "neutral"
                formatted_data["rsi"] = f"{rsi_value:.1f} ({rsi_desc})"
            else:
                formatted_data["rsi"] = "No data"
            
            # MACD
            if "macd" in ti:
                macd = ti["macd"]
                macd_line = macd.get("macd_line", 0)
                signal_line = macd.get("signal_line", 0)
                histogram = macd.get("histogram", 0)
                
                trend = "bullish" if macd_line > signal_line else "bearish"
                momentum = "increasing" if histogram > 0 else "decreasing"
                
                formatted_data["macd"] = f"MACD ({macd_line:.5f}) {'above' if macd_line > signal_line else 'below'} Signal ({signal_line:.5f}), {trend} with {momentum} momentum"
            else:
                formatted_data["macd"] = "No data"
            
            # Bollinger Bands
            if "bollinger_bands" in ti:
                bb = ti["bollinger_bands"]
                current_price = market_data.get("current_price", 0)
                upper_band = bb.get("upper", 0)
                middle_band = bb.get("middle", 0)
                lower_band = bb.get("lower", 0)
                bandwidth = bb.get("bandwidth", 0)
                
                position = "near upper band" if current_price > (middle_band + (upper_band - middle_band) * 0.7) else \
                           "near lower band" if current_price < (middle_band - (middle_band - lower_band) * 0.7) else \
                           "near middle band"
                
                band_state = "expanding" if bb.get("is_expanding", False) else "contracting"
                
                formatted_data["bollinger_bands"] = f"Price {position} (Upper: {upper_band:.5f}, Middle: {middle_band:.5f}, Lower: {lower_band:.5f}), bands {band_state}"
            else:
                formatted_data["bollinger_bands"] = "No data"
                
            # Additional indicators as a combined string
            additional_indicators = []
            
            # Stochastic
            if "stochastic" in ti:
                stoch = ti["stochastic"]
                k_value = stoch.get("k_value", 0)
                d_value = stoch.get("d_value", 0)
                
                stoch_state = "overbought" if k_value > 80 else "oversold" if k_value < 20 else "neutral"
                crossover = "bullish crossover" if k_value > d_value and k_value - d_value < 5 else \
                            "bearish crossover" if d_value > k_value and d_value - k_value < 5 else "no recent crossover"
                
                additional_indicators.append(f"Stochastic: %K({k_value:.1f}) %D({d_value:.1f}), {stoch_state} with {crossover}")
            
            # ATR for volatility
            if "atr" in ti:
                atr_value = ti["atr"].get("value", 0)
                formatted_data["volatility"] = f"ATR({ti['atr'].get('period', 14)}) = {atr_value:.5f}"
            else:
                formatted_data["volatility"] = "No volatility data"
            
            # Add any other indicators
            for indicator_name, indicator_data in ti.items():
                if indicator_name not in ["moving_averages", "rsi", "macd", "bollinger_bands", "stochastic", "atr"]:
                    if isinstance(indicator_data, dict) and "description" in indicator_data:
                        additional_indicators.append(f"{indicator_name}: {indicator_data['description']}")
                    elif isinstance(indicator_data, dict) and "value" in indicator_data:
                        additional_indicators.append(f"{indicator_name}: {indicator_data['value']}")
            
            formatted_data["additional_indicators"] = "\n- " + "\n- ".join(additional_indicators) if additional_indicators else ""
        
        # Format market conditions
        if "market_conditions" in market_data:
            mc = market_data["market_conditions"]
            
            # Volume
            if "volume" in mc:
                vol = mc["volume"]
                vol_comparison = vol.get("comparison_to_average", "")
                formatted_data["volume"] = f"{vol_comparison}" if vol_comparison else f"{vol.get('value', 'No data')}"
            else:
                formatted_data["volume"] = "No volume data"
            
            # Recent price movement
            if "price_movement" in mc:
                pm = mc["price_movement"]
                formatted_data["recent_price_movement"] = pm.get("description", "No recent price movement data")
            else:
                formatted_data["recent_price_movement"] = "No recent price movement data"
            
            # Additional market conditions
            additional_conditions = []
            for condition_name, condition_data in mc.items():
                if condition_name not in ["volume", "price_movement"]:
                    if isinstance(condition_data, dict) and "description" in condition_data:
                        additional_conditions.append(f"{condition_name}: {condition_data['description']}")
            
            formatted_data["additional_market_conditions"] = "\n- " + "\n- ".join(additional_conditions) if additional_conditions else ""
        
        # Format significant levels
        if "significant_levels" in market_data:
            sl = market_data["significant_levels"]
            
            # Support levels
            if "support" in sl:
                support_levels = [f"{level:.5f}" for level in sl["support"]]
                formatted_data["support_levels"] = ", ".join(support_levels) if support_levels else "No support levels identified"
            else:
                formatted_data["support_levels"] = "No support levels data"
            
            # Resistance levels
            if "resistance" in sl:
                resistance_levels = [f"{level:.5f}" for level in sl["resistance"]]
                formatted_data["resistance_levels"] = ", ".join(resistance_levels) if resistance_levels else "No resistance levels identified"
            else:
                formatted_data["resistance_levels"] = "No resistance levels data"
            
            # Recent high/low
            formatted_data["recent_high"] = f"{sl.get('recent_high', {}).get('value', 'Unknown')}" + (f" ({sl.get('recent_high', {}).get('time_ago', '')})" if sl.get('recent_high', {}).get('time_ago', '') else "")
            formatted_data["recent_low"] = f"{sl.get('recent_low', {}).get('value', 'Unknown')}" + (f" ({sl.get('recent_low', {}).get('time_ago', '')})" if sl.get('recent_low', {}).get('time_ago', '') else "")
            
            # Additional levels
            additional_levels = []
            for level_name, level_data in sl.items():
                if level_name not in ["support", "resistance", "recent_high", "recent_low"]:
                    if isinstance(level_data, dict) and "description" in level_data:
                        additional_levels.append(f"{level_name}: {level_data['description']}")
                    elif isinstance(level_data, list):
                        level_values = [f"{level:.5f}" for level in level_data]
                        additional_levels.append(f"{level_name}: {', '.join(level_values)}")
            
            formatted_data["additional_levels"] = "\n- " + "\n- ".join(additional_levels) if additional_levels else ""
        
        # Additional context
        if "additional_context" in market_data:
            ac = market_data["additional_context"]
            context_items = []
            
            for context_name, context_data in ac.items():
                if isinstance(context_data, dict) and "description" in context_data:
                    context_items.append(f"{context_name}: {context_data['description']}")
                elif isinstance(context_data, str):
                    context_items.append(f"{context_name}: {context_data}")
            
            formatted_data["additional_context"] = "\n".join(context_items) if context_items else ""
        else:
            formatted_data["additional_context"] = ""
        
        logger.debug(f"Market data formatted for {formatted_data['symbol']} on {formatted_data['timeframe']} timeframe")
        return formatted_data
    
    def analyze_market(self, prices: pd.Series, volumes: pd.Series = None) -> Dict[str, Any]:
        """
        Całościowa analiza rynku z wykorzystaniem uczenia maszynowego i analizy technicznej.
        
        Args:
            prices: Seria cenowa do analizy
            volumes: Opcjonalna seria wolumenów
            
        Returns:
            Słownik zawierający kompleksową analizę rynku
        """
        if len(prices) < 30:
            self.logger.warning("Za mało danych do analizy (potrzeba minimum 30 świec).")
            return {
                "trend": "unknown",
                "strength": 0,
                "volatility": "unknown",
                "recommendation": "Zbyt mało danych do analizy",
                "support_levels": [],
                "resistance_levels": [],
                "key_levels": []
            }
            
        # Analiza trendu
        trend_analysis = self.market_analysis.analyze_trend(prices)
        
        # Generowanie sygnałów handlowych
        if volumes is not None:
            buy_signals = self.market_analysis.generate_buy_signals(prices, volumes)
            sell_signals = self.market_analysis.generate_sell_signals(prices, volumes)
        else:
            # Jeśli nie ma danych o wolumenie, użyj wersji bez wolumenu
            buy_signals = self.market_analysis.generate_buy_signals(prices)
            sell_signals = self.market_analysis.generate_sell_signals(prices)
            
        # Identyfikacja kluczowych poziomów cenowych
        support_resistance = trend_analysis["support_levels"] + trend_analysis["resistance_levels"]
        
        # Sortowanie poziomów rosnąco
        key_levels = sorted(support_resistance)
        
        # Rekomendacja handlowa bazująca na trendzie i sygnałach
        current_price = prices.iloc[-1]
        
        # Liczba ostatnich świec do sprawdzenia sygnałów
        signal_window = 3
        recent_buy_signals = sum([1 for idx in buy_signals if idx >= len(prices) - signal_window])
        recent_sell_signals = sum([1 for idx in sell_signals if idx >= len(prices) - signal_window])
        
        if trend_analysis["trend"] == "bullish" and recent_buy_signals > 0:
            recommendation = "Szukaj okazji do wejścia na długiej pozycji przy cofnięciach"
        elif trend_analysis["trend"] == "bearish" and recent_sell_signals > 0:
            recommendation = "Szukaj okazji do wejścia na krótkiej pozycji przy odbiciu"
        elif trend_analysis["trend"] == "bullish" and trend_analysis["strength"] >= 7:
            recommendation = "Czekaj na potwierdzenie wzrostowego setupu"
        elif trend_analysis["trend"] == "bearish" and trend_analysis["strength"] >= 7:
            recommendation = "Czekaj na potwierdzenie spadkowego setupu"
        elif trend_analysis["trend"] == "sideways":
            recommendation = "Handel w zakresie między poziomami wsparcia i oporu"
        else:
            recommendation = "Brak wyraźnego sygnału, zachowaj ostrożność"
            
        # Zbuduj kompletną analizę
        market_analysis = {
            "trend": trend_analysis["trend"],
            "strength": trend_analysis["strength"],
            "volatility": trend_analysis["volatility"],
            "description": trend_analysis["description"],
            "recommendation": recommendation,
            "support_levels": trend_analysis["support_levels"],
            "resistance_levels": trend_analysis["resistance_levels"],
            "key_levels": key_levels,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals
        }
        
        return market_analysis
    
    def evaluate_trade_setup(self, trade_data: Dict[str, Any], provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluate a potential trade setup using LLM.
        
        Args:
            trade_data: Dictionary containing trade and market data
            provider: Optional specific LLM provider to use
            
        Returns:
            Dictionary containing structured trade evaluation
        """
        start_time = time.time()
        logger.info(f"Evaluating trade setup for {trade_data.get('symbol', 'unknown symbol')}")
        
        try:
            # Get the trade evaluation prompt
            prompt_text = get_prompt("trade_suggestion", **trade_data)
            system_prompt = get_system_prompt("trade_advisor")
            
            # Send to LLM and get response
            llm_response = self.llm_interface.generate_response(
                prompt=prompt_text,
                system_prompt=system_prompt,
                provider_name=provider
            )
            
            # Extract JSON from the response
            evaluation = self._extract_json_from_response(llm_response)
            
            # Add metadata to the evaluation
            evaluation["_metadata"] = {
                "timestamp": datetime.now().isoformat(),
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "provider": provider if provider else "default",
                "success": True
            }
            
            logger.info(f"Trade evaluation completed for {trade_data.get('symbol', 'unknown symbol')} in {evaluation['_metadata']['execution_time_ms']}ms")
            return evaluation
            
        except Exception as e:
            logger.error(f"Error during trade evaluation: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "execution_time_ms": int((time.time() - start_time) * 1000),
                    "provider": provider if provider else "default",
                    "success": False
                }
            }
    
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """
        Extract and parse JSON from LLM response.
        
        Args:
            response: Raw response from LLM
            
        Returns:
            Parsed JSON as dictionary
        """
        # Find JSON content in the response
        json_start = response.find("{")
        json_end = response.rfind("}")
        
        if json_start == -1 or json_end == -1:
            # Try looking for JSON in code blocks
            json_matches = []
            start_marker = "```json"
            end_marker = "```"
            
            start_pos = response.find(start_marker)
            while start_pos != -1:
                # Find the end of this code block
                start_content = start_pos + len(start_marker)
                end_pos = response.find(end_marker, start_content)
                
                if end_pos == -1:
                    break
                
                # Extract JSON content
                json_content = response[start_content:end_pos].strip()
                json_matches.append(json_content)
                
                # Look for the next code block
                start_pos = response.find(start_marker, end_pos)
            
            if json_matches:
                # Use the longest JSON match (assuming it's the most complete)
                json_content = max(json_matches, key=len)
            else:
                raise ValueError("No JSON found in the response")
        else:
            json_content = response[json_start:json_end + 1]
        
        # Parse the JSON
        try:
            parsed = json.loads(json_content)
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from response: {str(e)}")
            logger.debug(f"JSON content that failed to parse: {json_content}")
            raise ValueError(f"Invalid JSON in LLM response: {str(e)}")

# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create LLM interface (assuming it's already implemented)
    from .llm_interface import LLMInterface
    llm = LLMInterface()
    
    # Create market analyzer
    analyzer = MarketAnalyzer(llm)
    
    # Example market data
    market_data = {
        "symbol": "EUR/USD",
        "timeframe": "4H",
        "current_price": 1.0821,
        "technical_indicators": {
            "moving_averages": [
                {"type": "SMA", "period": 50, "value": 1.0798},
                {"type": "EMA", "period": 200, "value": 1.0754}
            ],
            "rsi": {"period": 14, "value": 58.3},
            "macd": {"macd_line": 0.0023, "signal_line": 0.0018, "histogram": 0.0005},
            "bollinger_bands": {"upper": 1.0845, "middle": 1.0810, "lower": 1.0775, "bandwidth": 0.0070, "is_expanding": True},
            "stochastic": {"k_value": 82.5, "d_value": 75.3},
            "atr": {"period": 14, "value": 0.0062}
        },
        "market_conditions": {
            "volume": {"value": 15000, "comparison_to_average": "Above 20-day average by 15%"},
            "price_movement": {"description": "Upward trend for past 5 days with 3 consecutive higher highs and higher lows"}
        },
        "significant_levels": {
            "support": [1.0780, 1.0750, 1.0720],
            "resistance": [1.0850, 1.0880, 1.0900],
            "recent_high": {"value": 1.0840, "time_ago": "yesterday"},
            "recent_low": {"value": 1.0760, "time_ago": "5 days ago"},
            "fibonacci_retracement": [1.0795, 1.0810, 1.0825]
        },
        "additional_context": {
            "economic_events": "ECB interest rate decision scheduled tomorrow",
            "market_sentiment": "USD weakening against most major currencies this week"
        }
    }
    
    # Run market analysis
    analysis = analyzer.analyze_market(market_data)
    
    # Print result
    print(json.dumps(analysis, indent=2)) 
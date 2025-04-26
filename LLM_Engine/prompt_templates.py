"""
Module containing prompt templates for LLM requests in the trading system.

This module provides templates for different types of LLM requests:
1. Market analysis
2. Risk management
3. Trade suggestions
4. Trade evaluation
5. System diagnostics
"""

from typing import Dict, Any, Optional, List, Union
from string import Template

# System prompts define the role and constraints for the LLM
SYSTEM_PROMPTS = {
    "market_analyst": """You are an expert financial market analyst with deep knowledge of technical analysis, 
fundamental analysis, and market psychology. Your task is to analyze market data and provide clear, 
objective trading insights. Base your analysis solely on the data provided and avoid making speculative claims. 
Format your response as JSON following the exact schema specified in the user's prompt.""",
    
    "risk_manager": """You are a conservative risk management specialist for a trading system. 
Your primary goal is to protect capital and ensure sustainable trading. Analyze the provided trade details 
and market conditions to recommend appropriate position sizes, stop-loss levels, and take-profit targets. 
Always prioritize capital preservation over profit potential. Format your response as JSON following the 
exact schema specified in the user's prompt.""",
    
    "trade_advisor": """You are a professional trading advisor with expertise in the forex market. 
Your job is to evaluate potential trades based on technical indicators, price action, market sentiment, 
and risk parameters. Provide balanced advice considering both the upside potential and downside risks. 
Format your response as JSON following the exact schema specified in the user's prompt.""",
    
    "system_diagnostic": """You are a diagnostic assistant for an automated trading system. 
Your task is to analyze system performance metrics, error logs, and operational data to identify potential issues 
and suggest improvements. Be precise in your analysis and provide actionable recommendations. 
Format your response as JSON following the exact schema specified in the user's prompt."""
}

# Template for market analysis prompt
MARKET_ANALYSIS_TEMPLATE = Template("""
Analyze the following market data for ${symbol} and provide a comprehensive market analysis.

TIMEFRAME: ${timeframe}

CURRENT PRICE: ${current_price}

TECHNICAL INDICATORS:
- Moving Averages: ${moving_averages}
- RSI: ${rsi}
- MACD: ${macd}
- Bollinger Bands: ${bollinger_bands}
${additional_indicators}

MARKET CONDITIONS:
- Volatility: ${volatility}
- Trading Volume: ${volume}
- Recent Price Movement: ${recent_price_movement}
${additional_market_conditions}

SIGNIFICANT LEVELS:
- Support Levels: ${support_levels}
- Resistance Levels: ${resistance_levels}
- Recent High: ${recent_high}
- Recent Low: ${recent_low}
${additional_levels}

${additional_context}

Based on this information, provide a detailed market analysis in the following JSON format:

```json
{
    "trend": "bullish|bearish|sideways",
    "strength": 1-10,
    "key_levels": {
        "support": [level1, level2, ...],
        "resistance": [level1, level2, ...]
    },
    "recommendation": "buy|sell|hold",
    "entry_price": number,
    "stop_loss": number,
    "take_profit": number,
    "time_frame_outlook": {
        "short_term": "bullish|bearish|sideways",
        "medium_term": "bullish|bearish|sideways",
        "long_term": "bullish|bearish|sideways"
    },
    "explanation": "detailed rationale for your analysis and recommendation"
}
```

Use all available data in your analysis. Provide specific price levels for entry, stop-loss, and take-profit. 
Your explanation should be comprehensive but focused on the most relevant factors influencing your recommendation.
""")

# Template for risk management prompt
RISK_MANAGEMENT_TEMPLATE = Template("""
Analyze the following trade setup and provide risk management recommendations.

ACCOUNT DETAILS:
- Account Balance: ${account_balance} ${account_currency}
- Current Open Positions: ${open_positions}
- Current Risk Exposure: ${risk_exposure}

TRADE SETUP:
- Symbol: ${symbol}
- Direction: ${direction}
- Entry Price: ${entry_price}
- Trade Rationale: ${trade_rationale}

MARKET CONDITIONS:
- Current Price: ${current_price}
- Recent Volatility: ${volatility}
- Average True Range (ATR): ${atr}
${additional_market_conditions}

RISK PREFERENCES:
- Max Risk Per Trade: ${max_risk_percent}% of account
- Max Daily Drawdown: ${max_daily_drawdown}% of account
- Max Total Risk Exposure: ${max_risk_exposure}% of account

${additional_context}

Based on this information, provide risk management recommendations in the following JSON format:

```json
{
    "position_size": {
        "units": number,
        "lots": number
    },
    "stop_loss": {
        "price": number,
        "pips": number,
        "account_risk_percent": number
    },
    "take_profit": {
        "price": number,
        "pips": number,
        "risk_reward_ratio": number
    },
    "risk_assessment": {
        "overall_risk_level": "low|medium|high",
        "volatility_risk": "low|medium|high",
        "correlation_risk": "low|medium|high",
        "timing_risk": "low|medium|high"
    },
    "additional_recommendations": [
        "specific advice 1",
        "specific advice 2",
        ...
    ],
    "explanation": "detailed rationale for your recommendations"
}
```

Be conservative in your approach to risk management. Consider current market volatility and account conditions 
when determining position size. Ensure that your recommendations comply with the specified risk parameters.
""")

# Template for trade suggestion prompt
TRADE_SUGGESTION_TEMPLATE = Template("""
Review the following market information and suggest potential trading opportunities.

MARKET OVERVIEW:
- Current Market Environment: ${market_environment}
- Major Economic Events: ${economic_events}
- Market Sentiment: ${market_sentiment}

SYMBOLS OF INTEREST:
${symbols_analysis}

TECHNICAL CONTEXT:
- Key Technical Patterns: ${technical_patterns}
- Significant Price Levels: ${significant_levels}
- Divergences: ${divergences}
${additional_technical_context}

TRADING PARAMETERS:
- Preferred Time Frame: ${preferred_timeframe}
- Risk Tolerance: ${risk_tolerance}
- Trading Style: ${trading_style}

${additional_context}

Based on this information, suggest up to 3 potential trading opportunities in the following JSON format:

```json
{
    "trade_opportunities": [
        {
            "symbol": "symbol name",
            "direction": "buy|sell",
            "entry_type": "market|limit|stop",
            "entry_price": number,
            "stop_loss": number,
            "take_profit": number,
            "time_frame": "time frame",
            "strength": 1-10,
            "rationale": "brief explanation of the trade idea",
            "key_indicators": ["indicator1", "indicator2", ...],
            "risk_reward_ratio": number
        },
        ...
    ],
    "market_outlook": "brief overall market assessment",
    "risk_considerations": "important risk factors to be aware of"
}
```

Prioritize trades with favorable risk-reward ratios and clear technical setups. Include specific price levels 
and a clear rationale for each suggested trade. Consider how each trade fits within the current market context.
""")

# Template for trade evaluation prompt
TRADE_EVALUATION_TEMPLATE = Template("""
Evaluate the performance and execution of the following completed trade.

TRADE DETAILS:
- Symbol: ${symbol}
- Direction: ${direction}
- Entry Price: ${entry_price}
- Exit Price: ${exit_price}
- Stop Loss: ${stop_loss}
- Take Profit: ${take_profit}
- Position Size: ${position_size}
- Entry Time: ${entry_time}
- Exit Time: ${exit_time}
- Profit/Loss: ${profit_loss} (${profit_loss_percent}% of account)

TRADE RATIONALE:
${trade_rationale}

MARKET CONDITIONS DURING TRADE:
${market_conditions}

TECHNICAL INDICATORS AT ENTRY:
${entry_indicators}

TECHNICAL INDICATORS AT EXIT:
${exit_indicators}

${additional_context}

Based on this information, evaluate this trade in the following JSON format:

```json
{
    "trade_grade": "A|B|C|D|F",
    "entry_quality": {
        "score": 1-10,
        "strengths": ["strength1", "strength2", ...],
        "weaknesses": ["weakness1", "weakness2", ...]
    },
    "exit_quality": {
        "score": 1-10,
        "strengths": ["strength1", "strength2", ...],
        "weaknesses": ["weakness1", "weakness2", ...]
    },
    "risk_management": {
        "score": 1-10,
        "strengths": ["strength1", "strength2", ...],
        "weaknesses": ["weakness1", "weakness2", ...]
    },
    "learning_points": [
        "learning point 1",
        "learning point 2",
        ...
    ],
    "improvement_suggestions": [
        "suggestion 1",
        "suggestion 2",
        ...
    ],
    "overall_assessment": "detailed evaluation of the trade's execution and outcome"
}
```

Be objective in your assessment. Focus on the quality of decision-making and execution rather than simply 
the outcome. Identify specific learning points and actionable improvements for future trades.
""")

# Template for system diagnostics prompt
SYSTEM_DIAGNOSTICS_TEMPLATE = Template("""
Analyze the following trading system performance metrics and diagnostic information.

SYSTEM OVERVIEW:
- System Version: ${system_version}
- Running Since: ${running_since}
- Total Trades Executed: ${total_trades}
- Win Rate: ${win_rate}%
- Average Profit/Loss: ${average_pnl}
- Sharpe Ratio: ${sharpe_ratio}

PERFORMANCE METRICS:
- Daily Returns: ${daily_returns}
- Max Drawdown: ${max_drawdown}% (${max_drawdown_period})
- Recovery Factor: ${recovery_factor}
- Profit Factor: ${profit_factor}

ERROR LOGS:
${error_logs}

RESOURCE UTILIZATION:
- CPU Usage: ${cpu_usage}
- Memory Usage: ${memory_usage}
- API Call Frequency: ${api_calls}
- Response Time: ${response_time}

OPERATIONAL ISSUES:
${operational_issues}

${additional_context}

Based on this information, provide a system diagnostic report in the following JSON format:

```json
{
    "system_health": {
        "overall_status": "healthy|degraded|critical",
        "reliability_score": 1-10,
        "performance_score": 1-10,
        "risk_management_score": 1-10
    },
    "identified_issues": [
        {
            "issue": "description of the issue",
            "severity": "low|medium|high|critical",
            "impact": "how this affects system performance",
            "potential_causes": ["cause1", "cause2", ...],
            "recommended_actions": ["action1", "action2", ...]
        },
        ...
    ],
    "optimization_opportunities": [
        {
            "area": "specific area for improvement",
            "expected_benefit": "description of potential improvement",
            "implementation_complexity": "low|medium|high",
            "priority": "low|medium|high"
        },
        ...
    ],
    "summary": "overall assessment of system health and key recommendations"
}
```

Be thorough in your analysis and specific in your recommendations. Prioritize issues that could affect 
system stability, performance, or risk management. Consider both technical and trading strategy aspects.
""")

# Function to get a filled template
def get_prompt(template_name: str, **kwargs) -> str:
    """
    Get a prompt with the template filled with the provided parameters.
    
    Args:
        template_name: Name of the template to use
        **kwargs: Parameters to fill in the template
        
    Returns:
        Filled prompt template as a string
    """
    templates = {
        "market_analysis": MARKET_ANALYSIS_TEMPLATE,
        "risk_management": RISK_MANAGEMENT_TEMPLATE,
        "trade_suggestion": TRADE_SUGGESTION_TEMPLATE,
        "trade_evaluation": TRADE_EVALUATION_TEMPLATE,
        "system_diagnostics": SYSTEM_DIAGNOSTICS_TEMPLATE
    }
    
    if template_name not in templates:
        raise ValueError(f"Template {template_name} not found")
    
    # Set default values for optional parameters
    for key in kwargs:
        if kwargs[key] is None:
            kwargs[key] = ""
    
    # Add empty string for missing parameters to avoid KeyError
    template = templates[template_name]
    for key in [k[1] for k in template.pattern.finditer(template.template)]:
        if key not in kwargs:
            kwargs[key] = ""
    
    return template.safe_substitute(kwargs)

# Function to get system prompt
def get_system_prompt(role: str) -> str:
    """
    Get the system prompt for a specific role.
    
    Args:
        role: Role name (market_analyst, risk_manager, etc.)
        
    Returns:
        System prompt as a string
    """
    if role not in SYSTEM_PROMPTS:
        raise ValueError(f"System prompt for role {role} not found")
    
    return SYSTEM_PROMPTS[role]

# Example usage
if __name__ == "__main__":
    # Example of using market analysis template
    market_analysis_prompt = get_prompt(
        "market_analysis",
        symbol="EUR/USD",
        timeframe="4H",
        current_price="1.0821",
        moving_averages="50 EMA (1.0798) above 200 EMA (1.0754), bullish crossover 3 days ago",
        rsi="58.3 (neutral with bullish bias)",
        macd="MACD (0.0023) above Signal (0.0018), positive and rising",
        bollinger_bands="Price near upper band (1.0845), bands expanding",
        volatility="Medium, ATR(14) = 0.0062",
        volume="Above 20-day average by 15%",
        recent_price_movement="Upward trend for past 5 days with 3 consecutive higher highs and higher lows",
        support_levels="1.0780, 1.0750, 1.0720",
        resistance_levels="1.0850, 1.0880, 1.0900",
        recent_high="1.0840 (yesterday)",
        recent_low="1.0760 (5 days ago)",
        additional_indicators="Stochastic oscillator showing overbought conditions at 82.5",
        additional_market_conditions="ECB interest rate decision scheduled tomorrow",
        additional_levels="Fibonacci retracement level at 1.0795 (38.2%)",
        additional_context="USD weakening against most major currencies this week"
    )
    
    # Print the prompt
    print(market_analysis_prompt)
    print("\nSystem prompt:")
    print(get_system_prompt("market_analyst")) 
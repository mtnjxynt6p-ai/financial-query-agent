"""
State schema for Financial Query Agent.

Defines the data structures that flow through the LangGraph agent,
including conversation history, analysis results, and portfolio context.
"""

from typing import Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pydantic import BaseModel, Field


class Message(BaseModel):
    """A single message in the conversation (user or assistant)."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class StockDataPoint(BaseModel):
    """Raw stock data snapshot."""
    symbol: str
    price: float
    volume: int
    date: str
    high: float
    low: float
    open: float
    close: float


class IndicatorAnalysis(BaseModel):
    """Technical indicators computed for a stock."""
    symbol: str
    rsi: Optional[float] = None  # Relative Strength Index (0-100)
    volatility: Optional[float] = None  # Standard deviation of returns (%)
    momentum: Optional[float] = None  # Price momentum (% change)
    ma_50: Optional[float] = None  # 50-day moving average
    ma_200: Optional[float] = None  # 200-day moving average
    signal_strength: str = "neutral"  # "strong_buy", "buy", "neutral", "sell", "strong_sell"


class AnalysisResult(BaseModel):
    """Complete analysis for a stock or portfolio."""
    query_symbol: str
    stock_data: Optional[StockDataPoint] = None
    indicators: Optional[IndicatorAnalysis] = None
    reasoning: str = ""  # LLM reasoning over the data
    recommendation: str = ""  # Final recommendation
    confidence_score: float = 0.0  # 0.0 to 1.0


class ToolCall(BaseModel):
    """Log of a tool invocation."""
    tool_name: str
    input_params: dict
    output: Any
    timestamp: datetime = Field(default_factory=datetime.now)


@dataclass
class AgentState:
    """
    Main state object for LangGraph agent.
    
    This flows through each node in the graph and is updated incrementally
    as the agent processes the user's query.
    """
    # Conversation
    messages: List[Message] = field(default_factory=list)
    current_query: str = ""
    
    # Analysis results
    stock_analysis: Optional[AnalysisResult] = None
    latest_data: Optional[StockDataPoint] = None
    latest_indicators: Optional[IndicatorAnalysis] = None
    
    # Comparison (for multi-stock queries)
    comparison_symbols: List[str] = field(default_factory=list)
    comparison_results: List[AnalysisResult] = field(default_factory=list)
    
    # Portfolio context (optional, for personalized recommendations)
    portfolio_holdings: dict = field(default_factory=dict)  # {symbol: shares}
    portfolio_allocation_pref: dict = field(default_factory=dict)  # {symbol: target %}
    
    # Tool tracking (for transparency)
    tool_calls: List[ToolCall] = field(default_factory=list)
    
    # Validation
    final_response: str = ""
    guardrail_checks: dict = field(default_factory=dict)  # {check_name: passed}
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    session_id: str = ""
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to conversation history."""
        self.messages.append(Message(role=role, content=content))
    
    def log_tool_call(self, tool_name: str, input_params: dict, output: Any) -> None:
        """Log a tool invocation."""
        self.tool_calls.append(
            ToolCall(
                tool_name=tool_name,
                input_params=input_params,
                output=output
            )
        )
    
    def get_conversation_history(self, limit: int = 10) -> str:
        """Get recent conversation as formatted string for LLM context."""
        recent = self.messages[-limit:]
        history = "\n".join(
            f"{msg.role.upper()}: {msg.content}" 
            for msg in recent
        )
        return history

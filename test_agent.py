"""
Unit tests for Financial Query Agent components.

Run with: pytest test_agent.py -v
"""

import pytest
from datetime import datetime
from state import AgentState, Message, AnalysisResult, StockDataPoint
from tools import StockDataTool, IndicatorsTool, PortfolioTool
from guardrails import GuardrailValidator
import pandas as pd


class TestState:
    """Test AgentState and data models."""
    
    def test_agent_state_creation(self):
        """Test AgentState initialization."""
        state = AgentState(
            current_query="Analyze AAPL",
            session_id="test_session_1"
        )
        assert state.current_query == "Analyze AAPL"
        assert state.session_id == "test_session_1"
        assert len(state.messages) == 0
    
    def test_add_message(self):
        """Test adding messages to state."""
        state = AgentState(current_query="Test")
        state.add_message("user", "Hello")
        state.add_message("assistant", "Hi there")
        
        assert len(state.messages) == 2
        assert state.messages[0].role == "user"
        assert state.messages[1].content == "Hi there"
    
    def test_get_conversation_history(self):
        """Test conversation history retrieval."""
        state = AgentState(current_query="Test")
        state.add_message("user", "Q1")
        state.add_message("assistant", "A1")
        state.add_message("user", "Q2")
        
        history = state.get_conversation_history(limit=2)
        assert "Q2" in history
        assert "A1" in history
    
    def test_log_tool_call(self):
        """Test tool call logging."""
        state = AgentState(current_query="Test")
        state.log_tool_call("test_tool", {"param": "value"}, {"result": "success"})
        
        assert len(state.tool_calls) == 1
        assert state.tool_calls[0].tool_name == "test_tool"


class TestStockDataTool:
    """Test StockDataTool."""
    
    def test_tool_initialization(self):
        """Test tool initialization."""
        tool = StockDataTool(cache_duration_minutes=10)
        assert tool.cache == {}
    
    def test_get_stock_data_real(self):
        """Test fetching real stock data (if network available)."""
        tool = StockDataTool()
        data = tool.get_stock_data("AAPL", period="1mo")
        
        if data:  # Skip if network not available
            assert data["symbol"] == "AAPL"
            assert "price" in data
            assert "date" in data
            assert data["price"] > 0
    
    def test_caching(self):
        """Test that cache prevents duplicate API calls."""
        tool = StockDataTool(cache_duration_minutes=10)
        
        # First call
        data1 = tool.get_stock_data("AAPL", period="1mo")
        if data1:
            # Second call should use cache
            data2 = tool.get_stock_data("AAPL", period="1mo")
            assert data1 == data2
            # Cache should have one entry
            assert len(tool.cache) == 1


class TestIndicatorsTool:
    """Test IndicatorsTool."""
    
    def test_rsi_calculation(self):
        """Test RSI calculation."""
        # Create synthetic price data
        prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
                           111, 110, 112, 114, 113, 115, 117, 116, 118, 120] * 3)
        
        rsi = IndicatorsTool.calculate_rsi(prices, period=14)
        assert rsi is not None
        assert 0 <= rsi <= 100
    
    def test_volatility_calculation(self):
        """Test volatility calculation."""
        prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
                           111, 110, 112, 114, 113, 115, 117, 116, 118, 120])
        
        vol = IndicatorsTool.calculate_volatility(prices, period=10)
        assert vol is not None
        assert vol >= 0
    
    def test_momentum_calculation(self):
        """Test momentum calculation."""
        prices = pd.Series([100 + i for i in range(50)])  # Consistent uptrend
        
        momentum = IndicatorsTool.calculate_momentum(prices, period=10)
        assert momentum is not None
        assert momentum > 0  # Uptrend should be positive
    
    def test_signal_strength(self):
        """Test signal strength determination."""
        # Strong oversold
        signal = IndicatorsTool.get_signal_strength(rsi=25, momentum=2, volatility=15)
        assert signal in ["strong_buy", "buy", "neutral", "sell", "strong_sell"]
        
        # Overbought
        signal = IndicatorsTool.get_signal_strength(rsi=75, momentum=-3, volatility=20)
        assert signal in ["strong_buy", "buy", "neutral", "sell", "strong_sell"]


class TestPortfolioTool:
    """Test PortfolioTool."""
    
    def test_portfolio_value_calculation(self):
        """Test portfolio value calculation."""
        holdings = {"AAPL": 10, "GOOGL": 5}
        prices = {"AAPL": 150, "GOOGL": 140}
        
        value = PortfolioTool.calculate_portfolio_value(holdings, prices)
        expected = 10 * 150 + 5 * 140
        assert value == expected
    
    def test_allocation_calculation(self):
        """Test allocation percentage calculation."""
        holdings = {"AAPL": 10, "GOOGL": 5}
        prices = {"AAPL": 150, "GOOGL": 100}
        
        allocation = PortfolioTool.calculate_allocation(holdings, prices)
        total = allocation["AAPL"] + allocation["GOOGL"]
        assert 99 < total <= 100  # Should sum to ~100%
    
    def test_rebalance_suggestions(self):
        """Test rebalancing suggestions."""
        current = {"AAPL": 60, "GOOGL": 40}
        target = {"AAPL": 50, "GOOGL": 50}
        
        suggestions = PortfolioTool.suggest_rebalance(current, target, threshold=5)
        assert len(suggestions) > 0
        assert any("Reduce" in s and "AAPL" in s for s in suggestions)


class TestGuardrailValidator:
    """Test GuardrailValidator."""
    
    def test_overconfidence_detection(self):
        """Test detection of overconfident language."""
        text = "You must definitely buy this stock. It's guaranteed to go up."
        ok, flagged = GuardrailValidator.check_overconfidence(text)
        assert not ok
        assert len(flagged) > 0
    
    def test_no_overconfidence(self):
        """Test clean text passes overconfidence check."""
        text = "This stock shows bullish momentum. Consider increasing your position if comfortable with risk."
        ok, flagged = GuardrailValidator.check_overconfidence(text)
        assert ok
    
    def test_disclaimer_check(self):
        """Test disclaimer detection."""
        text = "Buy this stock! Not financial advice though."
        has_disclaimer, reason = GuardrailValidator.check_has_disclaimer(text)
        assert has_disclaimer
    
    def test_confidence_score_detection(self):
        """Test confidence score detection."""
        text = "I recommend AAPL. Confidence: 0.75"
        has_score, reason = GuardrailValidator.check_has_confidence_score(text)
        assert has_score
    
    def test_full_validation(self):
        """Test full validation suite."""
        good_response = """
        AAPL shows RSI of 65 and momentum of +8%.
        Recommendation: Consider increasing position cautiously.
        Confidence: 0.70 / 1.0
        
        ⚠️ DISCLAIMER: This is not financial advice. Consult a licensed advisor.
        """
        
        validator = GuardrailValidator()
        results = validator.validate(good_response)
        
        assert "checks" in results
        assert "score" in results
        assert results["score"] > 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

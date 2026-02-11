"""
Simplified demo runner that showcases the agent workflow WITHOUT requiring LLM API keys.

This runs the full pipeline (parse → fetch → analyze → reason with mock LLM → validate)
using mock responses to demonstrate the architecture and guardrails.
"""

import logging
from agent import (
    parse_query, fetch_data, analyze, validate,
    build_agent_graph, AgentState, stock_tool, indicator_tool
)
from state import AnalysisResult
from guardrails import GuardrailValidator
from datetime import datetime
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)


def mock_reason_step(state: AgentState) -> AgentState:
    """
    Mock reasoning step that generates a sample recommendation without calling LLM.
    
    In production, this would call Claude or your LLM.
    """
    logger.info(f"🧠 Generating mock recommendation...")
    
    # Generate realistic recommendation based on fetched data
    if not state.comparison_symbols:
        state.final_response = "No valid symbols found in query. Please mention stock tickers (e.g., AAPL, TSLA)."
        state.add_message("assistant", state.final_response)
        return state
    
    try:
        symbol = state.comparison_symbols[0]
        data = stock_tool.get_stock_data(symbol, period="1y")
        
        if data and 'history' in data and not data['history'].empty:
            indicators = indicator_tool.analyze_stock(data)
            
            # Generate a mock but realistic recommendation
            if indicators.get('rsi'):
                rsi = indicators['rsi']
                volatility = indicators.get('volatility', 0)
                momentum = indicators.get('momentum', 0)
                signal = indicators['signal_strength']
                price = data.get('price', 0)
                
                if rsi < 30:
                    rec = f"{symbol} is oversold (RSI: {rsi:.1f}, Price: ${price:.2f}). Consider accumulating position cautiously. Confidence: 0.65"
                elif rsi > 70:
                    rec = f"{symbol} is overbought (RSI: {rsi:.1f}, Price: ${price:.2f}). Consider trimming position. Confidence: 0.60"
                else:
                    if momentum > 0:
                        rec = f"{symbol} shows bullish momentum ({momentum:+.1f}%, Price: ${price:.2f}). Monitor for further upside. Confidence: 0.70"
                    else:
                        rec = f"{symbol} shows bearish momentum ({momentum:+.1f}%, Price: ${price:.2f}). Watch support levels. Confidence: 0.55"
                
                if volatility and volatility > 30:
                    rec += f" ⚠️ High volatility ({volatility:.1f}%): Consider hedging with protective puts."
                
                rec += "\n\n⚠️ DISCLAIMER: This analysis is for educational purposes only and not financial advice. Consult a licensed advisor before investing."
                
                state.final_response = rec
                state.add_message("assistant", rec)
                logger.info(f"  ✓ Generated mock recommendation")
                return state
        
        # Fallback if no indicators
        state.final_response = f"Unable to generate complete analysis for {symbol}. Data may be incomplete."
        state.add_message("assistant", state.final_response)
        return state
    
    except Exception as e:
        logger.error(f"Error in mock reasoning: {e}")
        state.final_response = f"Error generating recommendation: {str(e)}"
        state.add_message("assistant", state.final_response)
        return state


def run_agent_demo(query: str, use_mock: bool = True) -> AgentState:
    """
    Run the agent workflow step-by-step with optional mock LLM.
    
    This is perfect for demonstrating architecture without API keys.
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"🤖 FINANCIAL AGENT DEMO (Mock LLM Mode)")
    logger.info(f"{'='*80}")
    logger.info(f"Query: {query}\n")
    
    # Initialize state
    state = AgentState(
        current_query=query,
        session_id=f"demo_{int(datetime.now().timestamp())}"
    )
    
    try:
        # Run each step manually for visibility
        logger.info("Step 1️⃣ : Parsing query...")
        state = parse_query(state)
        
        logger.info("\nStep 2️⃣ : Fetching stock data...")
        state = fetch_data(state)
        
        logger.info("\nStep 3️⃣ : Analyzing indicators...")
        state = analyze(state)
        
        logger.info("\nStep 4️⃣ : Reasoning (using mock LLM)...")
        state = mock_reason_step(state)
        
        logger.info("\nStep 5️⃣ : Validating with guardrails...")
        state = validate(state)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"✓ DEMO COMPLETE")
        logger.info(f"{'='*80}\n")
        
        return state
    
    except Exception as e:
        logger.error(f"Demo execution failed: {e}")
        state.add_message("error", str(e))
        return state


def print_demo_output(state: AgentState) -> None:
    """Pretty-print the demo output."""
    print("\n" + "="*80)
    print("📊 RECOMMENDATION")
    print("="*80)
    print(state.final_response or "No recommendation generated")
    
    print("\n" + "="*80)
    print("📋 ANALYSIS METADATA")
    print("="*80)
    print(f"Symbols analyzed: {', '.join(state.comparison_symbols) if state.comparison_symbols else 'None'}")
    print(f"Tool calls made: {len(state.tool_calls)}")
    print(f"Guardrail score: {state.guardrail_checks.get('score', 'N/A'):.2f}/1.0" if state.guardrail_checks else "Guardrail score: N/A")
    print(f"Conversation turns: {len(state.messages)}")
    
    if state.guardrail_checks:
        print("\n" + "="*80)
        print("✓ GUARDRAIL CHECKS")
        print("="*80)
        for check_name, result in state.guardrail_checks.get("checks", {}).items():
            status = "✓ PASS" if result.get("passed") else "✗ FAIL"
            print(f"{status} | {check_name}: {result.get('reason')}")
    
    if state.tool_calls:
        print("\n" + "="*80)
        print("🔧 TOOL CALLS")
        print("="*80)
        for i, call in enumerate(state.tool_calls[-3:], 1):  # Last 3 calls
            print(f"{i}. {call.tool_name}")
            if isinstance(call.output, dict):
                print(f"   Output: {json.dumps({k: v for k, v in call.output.items() if k not in ['history']}, indent=2)}")
    
    print("\n")


# Example queries
DEMO_QUERIES = [
    "Analyze AAPL's recent performance and suggest if I should hedge with options",
    "Compare TSLA and NVDA momentum and recommend allocation",
    "Is MSFT showing bullish signals? Check RSI and momentum.",
]


if __name__ == "__main__":
    import sys
    
    print("\n" + "="*80)
    print("🚀 FINANCIAL QUERY AGENT - DEMO (No API Keys Required)")
    print("="*80)
    print("\nThis demo runs the full agent workflow using mock data and mock LLM responses.")
    print("Perfect for understanding the architecture without needing API access!\n")
    
    if len(sys.argv) > 1:
        # Custom query
        query = " ".join(sys.argv[1:])
    else:
        # Use first demo query
        query = DEMO_QUERIES[0]
        print(f"Running first demo query. Usage: python run_demo.py [your custom query]\n")
    
    # Run demo
    result = run_agent_demo(query)
    
    # Print output
    print_demo_output(result)
    
    print("="*80)
    print("💡 Next Steps:")
    print("  1. Set ANTHROPIC_API_KEY and run: python run_examples.py")
    print("  2. Run tests: pytest test_agent.py -v")
    print("  3. Read SETUP_GUIDE.md for more details")
    print("="*80 + "\n")

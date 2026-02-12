"""
Core Financial Query Agent using LangGraph.

Orchestrates a multi-step workflow:
1. Parse user query → extract stocks, intent
2. Fetch data → use StockDataTool
3. Analyze → use IndicatorsTool
4. Reason → LLM reasons over data
5. Validate → Guardrails check response
"""

import logging
import os
from typing import Optional, Any
from datetime import datetime
import json
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage

from state import AgentState, Message, AnalysisResult, StockDataPoint, IndicatorAnalysis
from tools import StockDataTool, IndicatorsTool, PortfolioTool
from prompts import get_system_prompt, get_reasoning_prompt
from guardrails import GuardrailValidator

# Load environment variables from .env
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize tools (with mock mode enabled for demo/testing)
stock_tool = StockDataTool(use_mock=True)
indicator_tool = IndicatorsTool()
portfolio_tool = PortfolioTool()

# Initialize LLM (AWS Bedrock Claude)
# ChatBedrock automatically uses AWS credentials from environment (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION)
try:
    # Try Claude 3.5 Sonnet (most common model ID format)
    # If that fails, the error will guide us to the correct model ID
    llm = ChatBedrock(
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )
    logger.info("✓ ChatBedrock initialized successfully")
except Exception as e:
    logger.error(f"Error initializing ChatBedrock: {e}")
    logger.error("Make sure AWS credentials are set in .env or environment variables")
    raise

guardrail_validator = GuardrailValidator()


# ============================================================================
# NODE FUNCTIONS: Each node is a step in the agent workflow
# ============================================================================

def parse_query(state: AgentState) -> AgentState:
    """
    Parse user query to extract:
    - Stocks to analyze
    - Type of query (comparison, hedging, allocation, etc.)
    - Time horizon
    
    Uses LLM to extract structured info (with fallback to regex).
    """
    # Ensure messages are Message objects (not dicts)
    if state.messages:
        if isinstance(state.messages[0], dict):
            state.messages = [
                Message(**msg) if isinstance(msg, dict) else msg 
                for msg in state.messages
            ]
    else:
        state.messages = []
    
    # Ensure current_query is set
    if not state.current_query and state.messages:
        # Extract content from last user message
        for msg in reversed(state.messages):
            if isinstance(msg, Message) and msg.role == "user":
                state.current_query = msg.content
                break
    
    logger.info(f"🔍 Parsing query: {state.current_query}")
    
    parse_prompt = f"""Extract structured information from this financial query:

Query: "{state.current_query}"

Respond in JSON format with:
{{
  "stocks": ["SYMBOL1", "SYMBOL2"],  // stocks mentioned
  "query_type": "analysis|comparison|hedging|allocation",  // type of query
  "time_horizon": "short-term|medium-term|long-term",
  "intent": "brief explanation of what user is asking"
}}"""
    
    try:
        response = llm.invoke([
            SystemMessage(content="You are a financial query parser. Extract key info and respond only with JSON."),
            HumanMessage(content=parse_prompt)
        ])
        
        # Parse JSON from response
        response_text = response.content.strip()
        # Clean up markdown code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        parsed = json.loads(response_text)
        
        state.comparison_symbols = parsed.get("stocks", [])
        logger.info(f"  ✓ Extracted symbols: {state.comparison_symbols}")
        logger.info(f"    Query type: {parsed.get('query_type')}")
        logger.info(f"    Time horizon: {parsed.get('time_horizon')}")
        
    except Exception as e:
        logger.warning(f"Failed to parse query with LLM: {e}. Using fallback extraction.")
        # Fallback: extract only valid stock symbols (1-5 uppercase letters)
        import re
        symbols = re.findall(r'\b[A-Z]{1,5}\b', state.current_query.upper())
        # Filter common non-stock words and single letters
        common_words = {"AND", "THE", "FOR", "NOT", "ARE", "BUT", "WITH", "FROM", "SHOULD", "IF", "IS", "TO", "A", "S", "I", "E", "P", "V"}
        symbols = [s for s in symbols if s not in common_words and len(s) >= 2]
        state.comparison_symbols = list(dict.fromkeys(symbols))  # Remove duplicates, preserve order
    
    state.add_message("system", f"Parsed query. Stocks to analyze: {state.comparison_symbols}")
    return state


def fetch_data(state: AgentState) -> AgentState:
    """
    Fetch stock data for identified symbols using StockDataTool.
    
    Logs tool calls for transparency.
    """
    # Ensure state fields are initialized
    if state.comparison_symbols is None:
        state.comparison_symbols = []
    if state.tool_calls is None:
        state.tool_calls = []
    if state.comparison_results is None:
        state.comparison_results = []
    
    logger.info(f"📊 Fetching data for: {state.comparison_symbols}")
    
    if not state.comparison_symbols:
        logger.warning("No symbols to fetch. Aborting.")
        state.add_message("assistant", "I couldn't identify any stock symbols in your query. Could you mention specific tickers?")
        return state
    
    for symbol in state.comparison_symbols[:5]:  # Limit to 5 for safety
        data = stock_tool.get_stock_data(symbol, period="1y")
        
        if data:
            state.log_tool_call(
                tool_name="get_stock_data",
                input_params={"symbol": symbol, "period": "1y"},
                output={"price": data["price"], "date": data["date"], "change_percent": data["change_percent"]}
            )
            # Store latest data point
            state.latest_data = StockDataPoint(
                symbol=data["symbol"],
                price=data["price"],
                volume=data["volume"],
                date=data["date"],
                high=data["high"],
                low=data["low"],
                open=data["open"],
                close=data["price"]  # Use current price as close
            )
            logger.info(f"  ✓ {symbol}: ${data['price']:.2f} ({data['change_percent']:+.2f}%)")
    
    state.add_message("system", f"Fetched data for {len(state.tool_calls)} symbol(s)")
    return state


def analyze(state: AgentState) -> AgentState:
    """
    Calculate technical indicators (RSI, volatility, momentum) for each stock.
    """
    # Ensure state fields are initialized
    if state.comparison_symbols is None:
        state.comparison_symbols = []
    if state.tool_calls is None:
        state.tool_calls = []
    
    logger.info(f"📈 Analyzing indicators...")
    
    for symbol in state.comparison_symbols[:5]:
        data = stock_tool.get_stock_data(symbol, period="1y")
        
        if data:
            indicators = indicator_tool.analyze_stock(data)
            
            if indicators:
                state.latest_indicators = IndicatorAnalysis(
                    symbol=indicators["symbol"],
                    rsi=indicators.get("rsi"),
                    volatility=indicators.get("volatility"),
                    momentum=indicators.get("momentum"),
                    ma_50=indicators.get("ma_50"),
                    ma_200=indicators.get("ma_200"),
                    signal_strength=indicators.get("signal_strength", "neutral")
                )
                
                state.log_tool_call(
                    tool_name="analyze_indicators",
                    input_params={"symbol": symbol},
                    output=indicators
                )
                
                logger.info(f"  ✓ {symbol}: RSI={indicators['rsi']:.1f}, Vol={indicators['volatility']:.1f}%, "
                           f"Momentum={indicators['momentum']:+.1f}%, Signal={indicators['signal_strength']}")
    
    state.add_message("system", f"Calculated indicators for {len(state.comparison_symbols)} symbols")
    return state


def reason(state: AgentState) -> AgentState:
    """
    Use LLM to reason over the data and generate a recommendation.
    
    This is where the agent's "thinking" happens.
    """
    logger.info(f"🧠 Reasoning over data...")
    
    # Prepare context from tool calls and data
    tool_calls_list = state.tool_calls if state.tool_calls else []
    data_summary = "\n".join([
        f"Tool: {call.tool_name}, Output: {json.dumps(call.output, default=str)}"
        for call in tool_calls_list[-5:]  # Last 5 calls
    ])
    
    reasoning_context = f"""
User Query: {state.current_query}

Recent Data Fetched:
{data_summary}

Conversation History (last 5 messages):
{state.get_conversation_history(limit=5)}

Based on this data, provide a financial analysis and recommendation. 
Remember to include confidence scores, cite the data, and include appropriate disclaimers.
"""
    
    try:
        response = llm.invoke([
            SystemMessage(content=get_system_prompt()),
            HumanMessage(content=reasoning_context)
        ])
        
        recommendation = response.content
        state.final_response = recommendation
        state.add_message("assistant", recommendation)
        
        logger.info(f"  ✓ Generated recommendation (first 100 chars): {recommendation[:100]}...")
        
    except Exception as e:
        logger.error(f"Error during reasoning: {e}")
        state.final_response = "I encountered an error while analyzing the data. Please try again."
        state.add_message("assistant", state.final_response)
    
    return state


def validate(state: AgentState) -> AgentState:
    """
    Run guardrail checks on the LLM-generated recommendation.
    
    Checks for overconfidence, hallucination, disclaimers, reasoning.
    """
    logger.info(f"✓ Validating response with guardrails...")
    
    # Prepare data context for hallucination check
    tool_calls = state.tool_calls if state.tool_calls else []
    data_points = [
        f"{call.tool_name}: {json.dumps(call.output, default=str)}"
        for call in tool_calls
    ]
    
    validation_results = guardrail_validator.validate(state.final_response, data_context=data_points)
    state.guardrail_checks = validation_results
    
    logger.info(f"  Guardrail score: {validation_results['score']:.2f}/1.0")
    for check_name, result in validation_results["checks"].items():
        status = "✓" if result["passed"] else "✗"
        logger.info(f"    {status} {check_name}: {result['reason']}")
    
    # If any critical checks failed, log suggestions
    if not validation_results["all_passed"]:
        suggestions = guardrail_validator.suggest_improvements(validation_results)
        logger.warning(f"  Improvement suggestions:")
        for suggestion in suggestions:
            logger.warning(f"    - {suggestion}")
    
    state.add_message("system", f"Validation complete. Score: {validation_results['score']:.2f}/1.0")
    return state


# ============================================================================
# BUILD THE LANGGRAPH
# ============================================================================

def build_agent_graph():
    """
    Construct the LangGraph StateGraph for the financial agent.
    
    Flow:
    START → parse_query → fetch_data → analyze → reason → validate → END
    """
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("parse_query", parse_query)
    graph.add_node("fetch_data", fetch_data)
    graph.add_node("analyze", analyze)
    graph.add_node("reason", reason)
    graph.add_node("validate", validate)
    
    # Define edges (workflow)
    graph.set_entry_point("parse_query")
    graph.add_edge("parse_query", "fetch_data")
    graph.add_edge("fetch_data", "analyze")
    graph.add_edge("analyze", "reason")
    graph.add_edge("reason", "validate")
    graph.add_edge("validate", END)
    
    # Compile graph
    try:
        agent = graph.compile()
        logger.info("✓ Agent graph compiled successfully")
    except Exception as e:
        logger.error(f"Error compiling graph: {e}")
        raise
    
    return agent


# ============================================================================
# RUN THE AGENT
# ============================================================================

def run_agent(query: str, portfolio_context: Optional[dict] = None) -> AgentState:
    """
    Execute the agent with a user query.
    
    Args:
        query: User's financial question
        portfolio_context: Optional portfolio holdings for personalization
    
    Returns:
        Final AgentState with all analysis and results
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"🤖 FINANCIAL AGENT EXECUTING")
    logger.info(f"{'='*70}")
    logger.info(f"Query: {query}\n")
    
    # Initialize state
    state = AgentState(
        current_query=query,
        portfolio_holdings=portfolio_context or {},
        session_id=f"session_{int(datetime.now().timestamp())}"
    )
    
    # Build and run agent
    agent = build_agent_graph()
    
    try:
        logger.info(f"Invoking agent graph with query...")
        # For langgraph <= 0.1.2, we need to handle checkpoints differently
        result_state = agent.invoke(state, {"configurable": {"thread_id": state.session_id}})
        logger.info(f"\n{'='*70}")
        logger.info(f"✓ AGENT COMPLETE")
        logger.info(f"{'='*70}\n")
        return result_state
    except Exception as e:
        logger.error(f"Agent execution failed: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return state
    
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        state.add_message("error", str(e))
        return state


# ============================================================================
# UTILITIES
# ============================================================================

def print_agent_output(state) -> None:
    """Pretty-print the agent's final output."""
    print("\n" + "="*70)
    print("📊 FINAL RESPONSE")
    print("="*70)
    
    # Handle both AgentState objects and dict-like returns from langgraph 0.2.0
    final_response = state.get('final_response') if isinstance(state, dict) else getattr(state, 'final_response', None)
    if final_response:
        print(final_response)
    else:
        print("No response generated")
    
    print("\n" + "="*70)
    print("🔍 ANALYSIS METADATA")
    print("="*70)
    
    # Extract symbols
    symbols = state.get('comparison_symbols') if isinstance(state, dict) else getattr(state, 'comparison_symbols', [])
    print(f"Symbols analyzed: {', '.join(symbols) if symbols else 'None'}")
    
    # Extract tool calls
    tool_calls = state.get('tool_calls') if isinstance(state, dict) else getattr(state, 'tool_calls', [])
    print(f"Tool calls: {len(tool_calls)}")
    
    # Extract guardrail score
    guardrail_checks = state.get('guardrail_checks') if isinstance(state, dict) else getattr(state, 'guardrail_checks', {})
    score = guardrail_checks.get('score', 'N/A') if guardrail_checks else 'N/A'
    if isinstance(score, (int, float)):
        print(f"Guardrail score: {score:.2f}/1.0")
    else:
        print(f"Guardrail score: {score}")
    
    # Extract messages
    messages = state.get('messages') if isinstance(state, dict) else getattr(state, 'messages', [])
    print(f"Conversation turns: {len(messages)}")
    print("\n")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)-8s | %(name)s | %(message)s'
    )
    
    # Example: run a simple query
    query = "Analyze AAPL's recent performance and suggest if I should hedge with options if volatility > 30%"
    result = run_agent(query)
    print_agent_output(result)

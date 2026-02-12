"""
Streamlit frontend for Financial Query Agent.
Run with: streamlit run streamlit_app.py
"""

import streamlit as st
import logging
from agent import build_agent_graph
from state import Message
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Financial Query Agent",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Title and description
st.title("💼 Financial Query Agent")
st.markdown("""
Ask multi-step financial questions about stocks. The agent:
1. **Parses** your query to extract symbols and intent
2. **Fetches** real stock data (with 5-min cache)
3. **Analyzes** technical indicators (RSI, volatility, momentum)
4. **Reasons** using Claude to generate recommendations
5. **Validates** outputs with guardrails to prevent hallucination

Built with **LangGraph + AWS Bedrock + Yahoo Finance API**
""")

st.divider()

# Sidebar with examples
with st.sidebar:
    st.header("📝 Example Queries")
    examples = [
        "Analyze AAPL's recent performance",
        "Compare TSLA and NVDA momentum",
        "Is MSFT a good buy at current levels?",
        "What's the volatility of NVDA?",
        "AAPL vs GOOGL - which is more stable?"
    ]
    
    for i, example in enumerate(examples):
        if st.button(example, key=f"example_{i}", use_container_width=True):
            st.session_state.query = example
    
    st.divider()
    st.subheader("ℹ️ How It Works")
    st.info("""
    - **Real data**: Live stock prices from Yahoo Finance
    - **Cached**: 5-minute cache to avoid rate limits
    - **Safe**: LLM-as-judge validation prevents bad advice
    - **Fast**: Runs in 15-30 seconds
    """)

# Main query input
st.subheader("🔍 Ask a Question")

# Initialize session state for query
if "query" not in st.session_state:
    st.session_state.query = ""

query = st.text_area(
    "Enter your financial question:",
    value=st.session_state.query,
    placeholder="e.g., Analyze AAPL and NVDA - which has better momentum?",
    height=80,
    key="query_input"
)

col1, col2 = st.columns([3, 1])

with col1:
    run_button = st.button("🚀 Analyze", use_container_width=True, type="primary")

with col2:
    clear_button = st.button("🔄 Clear", use_container_width=True)

if clear_button:
    st.session_state.query = ""
    st.rerun()

st.divider()

# Run agent if button clicked
if run_button and query:
    try:
        with st.spinner("🔄 Running 5-node agent workflow..."):
            logger.info(f"Processing query: {query}")
            
            # Build and run agent
            agent = build_agent_graph()
            
            # Create proper Message object
            user_message = Message(role="user", content=query)
            
            result = agent.invoke({
                "messages": [user_message]
            })
            
            # Handle None result
            if result is None:
                st.error("❌ Agent returned no result. Check logs for details.")
                logger.error("Agent.invoke() returned None")
                st.stop()
            
            # Extract results with safe defaults
            if isinstance(result, dict):
                # Handle both dict and AgentState object
                symbols = result.get("comparison_symbols", [])
                recommendation = result.get("final_response", "") or result.get("recommendation", "")
                guardrail_score = float(result.get("guardrail_checks", {}).get("score", 0.0)) if isinstance(result.get("guardrail_checks"), dict) else 0.0
                tool_calls_list = result.get("tool_calls", [])
                # Count tool calls (could be list of objects or ints)
                tool_calls_count = len(tool_calls_list) if isinstance(tool_calls_list, list) else 0
                
                # Fallback if recommendation is still empty
                if not recommendation:
                    recommendation = "Agent completed but no specific recommendation was generated. Please try a more specific query."
            else:
                logger.error(f"Unexpected result type: {type(result)}, value: {result}")
                st.error(f"❌ Unexpected result format. Got {type(result).__name__} instead of dict")
                st.stop()
            
        st.success("✅ Analysis Complete!")
        
        # Display results in columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Guardrail Score", f"{guardrail_score:.2f}/1.0", 
                     help="Safety validation: 1.0 = all checks passed, <1.0 = some warnings")
        
        with col2:
            st.metric("Symbols Analyzed", len(symbols), help=", ".join(symbols) if symbols else "None")
        
        with col3:
            st.metric("Tool Calls", tool_calls_count, help="Number of tool invocations (data fetch, indicators, etc.)")
        
        st.divider()
        
        # Recommendation
        st.subheader("📊 Recommendation")
        st.markdown(recommendation)
        
        # Guardrail validation details
        with st.expander("🛡️ Guardrail Validation Details", expanded=guardrail_score < 1.0):
            st.write("**Validation Checks:**")
            
            # Try to get checks from guardrail_checks dict
            guardrail_checks = result.get("guardrail_checks", {})
            if isinstance(guardrail_checks, dict) and "checks" in guardrail_checks:
                checks = guardrail_checks["checks"]
            else:
                checks = guardrail_checks
            
            if isinstance(checks, dict):
                for check_name, check_result in checks.items():
                    # Handle both bool values and dict with 'passed' key
                    if isinstance(check_result, dict):
                        passed = check_result.get("passed", False)
                    else:
                        passed = bool(check_result)
                    status = "✅" if passed else "⚠️"
                    st.write(f"{status} {check_name.replace('_', ' ').title()}: {'Pass' if passed else 'Needs attention'}")
            else:
                st.info("Validation details not available")
            
            if guardrail_score < 1.0:
                st.warning("""
                ⚠️ **Note:** Some guardrail checks flagged warnings. This is normal—our validation is conservative 
                to prevent financial advice errors. Always consult a licensed financial advisor before investing.
                """)
        
        # Raw data (for transparency)
        with st.expander("📋 Full Results (JSON)", expanded=False):
            st.json(result)
        
    except Exception as e:
        st.error(f"❌ Error running agent: {str(e)}")
        logger.error(f"Agent error: {e}", exc_info=True)
        st.info("""
        **Troubleshooting:**
        1. Make sure `.env` is configured with AWS credentials
        2. Check that all dependencies are installed: `pip install -r requirements.txt`
        3. Try running `python3 demo.py` to test the agent directly
        4. Check the terminal logs above for detailed error messages
        """)
        st.stop()

elif run_button:
    st.warning("⚠️ Please enter a question before clicking Analyze")

st.divider()

# Footer
st.markdown("""
---
**Disclaimer:** This agent provides technical analysis and AI-generated insights, not financial advice. 
Always consult a licensed financial advisor before making investment decisions.

**Built with:** LangGraph • LangChain • Claude (AWS Bedrock) • Yahoo Finance API
""")

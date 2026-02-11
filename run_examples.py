"""
Example queries and runner for the Financial Query Agent.

Run this to test the agent end-to-end with realistic financial queries.
"""

import logging
from agent import run_agent, print_agent_output

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-8s | %(message)s'
)

logger = logging.getLogger(__name__)


# Example queries
EXAMPLE_QUERIES = [
    # Single stock analysis
    "Analyze AAPL's recent performance and suggest if I should hedge with options if volatility > 30%",
    
    # Comparison
    "Compare TSLA and NVDA momentum and recommend allocation",
    
    # Technical analysis
    "What's the current RSI for GOOGL? Is it oversold?",
    
    # Hedging decision
    "Should I hedge my MSFT position? What's the current volatility?",
    
    # Trend analysis
    "Is AMZN in an uptrend? Check the 200-day MA and momentum.",
]


def run_examples(query_indices: list = None):
    """
    Run example queries.
    
    Args:
        query_indices: List of indices to run (e.g., [0, 2]). If None, run all.
    """
    if query_indices is None:
        query_indices = range(len(EXAMPLE_QUERIES))
    
    for idx in query_indices:
        if idx < len(EXAMPLE_QUERIES):
            query = EXAMPLE_QUERIES[idx]
            print(f"\n{'#'*80}")
            print(f"# EXAMPLE {idx + 1}")
            print(f"{'#'*80}\n")
            
            result = run_agent(query)
            print_agent_output(result)
            
            # Print guardrail details (handle both AgentState and dict-like objects)
            guardrail_checks = result.get('guardrail_checks') if isinstance(result, dict) else getattr(result, 'guardrail_checks', None)
            if guardrail_checks:
                print("\n📋 GUARDRAIL CHECKS:")
                for check_name, check_result in guardrail_checks.get("checks", {}).items():
                    status = "✓" if check_result.get("passed") else "✗"
                    print(f"  {status} {check_name}: {check_result.get('reason')}")
            
            print("\n" + "="*80 + "\n")


def run_custom_query(query: str):
    """
    Run a custom query.
    
    Args:
        query: Your custom financial query
    """
    print(f"\nYour query: {query}\n")
    result = run_agent(query)
    print_agent_output(result)
    
    if result.guardrail_checks:
        print("\n📋 GUARDRAIL CHECKS:")
        for check_name, check_result in result.guardrail_checks.get("checks", {}).items():
            status = "✓" if check_result.get("passed") else "✗"
            print(f"  {status} {check_name}: {check_result.get('reason')}")


if __name__ == "__main__":
    import sys
    
    print("\n" + "="*80)
    print("🤖 FINANCIAL QUERY AGENT - EXAMPLES")
    print("="*80)
    
    if len(sys.argv) > 1:
        # Run specific example(s)
        if sys.argv[1].isdigit():
            indices = [int(x) - 1 for x in sys.argv[1:]]
            run_examples(indices)
        else:
            # Custom query
            custom_query = " ".join(sys.argv[1:])
            run_custom_query(custom_query)
    else:
        # Run first example by default
        print("\nRunning first example...")
        print("Usage: python run_examples.py [query_num] or python run_examples.py [custom query]")
        run_examples([0])

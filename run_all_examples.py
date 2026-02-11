"""
Run all 5 example queries and show condensed results.
"""
import logging
from run_examples import EXAMPLE_QUERIES, run_agent

# Reduce logging noise
logging.basicConfig(level=logging.WARNING)

print("\n" + "="*80)
print("🚀 FINANCIAL AGENT - ALL EXAMPLES DEMO")
print("="*80)

for i in range(len(EXAMPLE_QUERIES)):
    print(f'\n{"#"*80}')
    print(f'EXAMPLE {i+1}: {EXAMPLE_QUERIES[i]}')
    print(f'{"#"*80}')
    
    result = run_agent(EXAMPLE_QUERIES[i])
    
    # Extract data
    final_response = result.get('final_response', 'No response')
    symbols = result.get('comparison_symbols', [])
    tool_calls = result.get('tool_calls', [])
    guardrail = result.get('guardrail_checks', {})
    score = guardrail.get('score', 'N/A')
    
    print(f'\n✓ Symbols analyzed: {", ".join(symbols) if symbols else "None"}')
    print(f'✓ Tool calls made: {len(tool_calls)}')
    if isinstance(score, (int, float)):
        print(f'✓ Guardrail score: {score:.2f}/1.0')
    else:
        print(f'✓ Guardrail score: {score}')
    
    print(f'\n💡 RESPONSE PREVIEW (first 300 chars):')
    print('-' * 80)
    preview = final_response[:300] + '...' if len(final_response) > 300 else final_response
    print(preview)
    print('-' * 80)

print(f'\n{"="*80}')
print("✅ ALL EXAMPLES COMPLETED")
print("="*80)

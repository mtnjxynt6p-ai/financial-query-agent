# FAQ - Interview Q&A

## Architecture Questions

### "Why StateGraph instead of just chaining calls together?"

**Q:** What's the advantage of LangGraph's StateGraph over something simpler like LangChain's legacy Agent?

**A:**
```python
# Bad: Linear chain (loses context)
response = fetch_data(query) 
response = analyze(response)
response = reason(response)  # ← Only sees analyze() output, not original query

# Good: StateGraph (maintains full context)
state.current_query = query
state = fetch_data(state)      # Can access current_query
state = analyze(state)         # Can access current_query + latest_data
state = reason(state)          # Can access all previous state

# Why it matters:
# - Conversation history persists across turns
# - Can implement conditional logic: "if volatility > 30%, add risk check"
# - Auditable: dump state at each step for debugging
# - Testable: stub state, test node function
```

**For Wells Fargo:** "This matters for advisor-facing tools where context is crucial. If a client asks 'based on yesterday's analysis, what if rates rise 2%?', the agent needs yesterday's analysis in state. LinearChain loses it."

---

### "How would you handle multi-user concurrency?"

**Q:** What if 100 advisors use this simultaneously?

**A:**
```python
# Current: Single-threaded, one query at a time
result = run_agent(query)

# Scaled: Per-user session state
run_agent(
    query, 
    session_id="advisor_123",  # ← Isolates state per user
    thread_id="conversation_456"
)

# Implementation:
# 1. Use langgraph's built-in checkpointer (SQL, Redis, or memory)
# 2. Each advisor gets isolated state
# 3. LLM calls are queued/batched
# 4. Results cached by (query_hash, session_id)

# Code change:
from langgraph.checkpoint.sqlite import SqliteSaver
memory = SqliteSaver(conn=":memory:")
graph = agent.compile(checkpointer=memory)

# Each call with different session_id is isolated
graph.invoke(state, config={"configurable": {"thread_id": "user_123"}})
```

**For Wells Fargo:** "This is how you'd run this in a multi-advisor platform. SQLite for dev, Postgres for prod. Each advisor's conversation is isolated and can be resumed later."

---

### "What about hallucination? How do you know Claude doesn't make up data?"

**Q:** I see the guardrail checks, but how do you prevent 'confident but wrong' outputs?

**A:**
```python
# Method 1: Grounding (what I do)
# Claude only sees data we fetched, not internet knowledge
context = f"""
RSI: {state.latest_indicators.rsi}
Price: {state.latest_data.AAPL.price}
"""
# Result: "RSI is {rsi_value}, suggesting..."
# ✓ Grounded in fetched data

# Method 2: Guardrails (what I validate)
def check_hallucination(response):
    # Regex: "will definitely rise" (predictive) = risky
    # Regex: "might decline" (uncertain) = safe
    return score

# Method 3: Constrained output
# Instead of free-form text, enforce JSON:
{"recommendation": "...", "confidence": 0.7, "cited_indicators": ["RSI", "MA"]}

# Real risk: Claude says "RSI is 51.8" when we only gave it RSI=51.76
# That's not hallucination, that's rounding. We accept it.

# Real hallucination: Claude says "AAPL beat earnings yesterday" 
# But we never fetched earnings data!
# My guardrail would flag this (no "earnings" in tool_calls).
```

**For Wells Fargo:** "Grounding is your best defense. Never let Claude access the internet during reasoning. Give it exactly what it needs. If it hallucinates anyway, the audit trail (tool_calls) proves it."

---

## Cost & Performance Questions

### "How much does this cost to run?"

**Q:** What are the real costs at scale?

**A:**
```python
# Per-query breakdown:

# 1. yfinance (free) or Bloomberg ($10k/month site license)
# 2. Claude API:
#    - Reasoning call: ~500 tokens avg
#      Input: $0.003/1M tokens = $0.0000015
#      Output: $0.00006/1M tokens = $0.00003
#      Subtotal: ~$0.000032
#    
#    - Guardrail call: ~200 tokens
#      Input: $0.0000006
#      Output: $0.000012
#      Subtotal: ~$0.000013

# Total per query: ~$0.000045 (0.0045 cents)

# At 1M queries/day:
#   $0.000045 * 1M = $45/day
#   $45 * 365 = ~$16k/year just for Claude

# At Wells Fargo scale (wealth management):
#   Maybe 10k advisor-queries/day = $160/year
#   Vs advisor time saved: $200k/year salary
#   ROI: 1250x

# If cost becomes a concern:
# 1. Fine-tune smaller model for guardrails (cheaper)
# 2. Batch API for off-peak queries
# 3. Cache guardrail checks (same output = same validation)
```

**For Wells Fargo:** "Cost is sub-penny per query. What matters is whether it saves advisor time. If it saves 2 minutes per query * 10 advisors * 10 queries/day, that's 20 hours/week = $1200. You'd pay $50k/year for that happily."

---

### "How fast is this? Can it support real-time trading?"

**Q:** Response time requirements?

**A:**
```python
# Current latency (from logs):
# 1. Parse: 50ms (local regex)
# 2. Fetch: 500ms (yfinance or cache hit)
# 3. Analyze: 100ms (numpy, local)
# 4. Reason: 2000-3000ms (API call to Claude)
# 5. Validate: 1500-2000ms (API call to guardrail)

# Total: ~5-6 seconds per query

# For real-time trading (< 100ms):
#   ✗ Not suitable (Claude API is ~2-3s alone)
#   ✓ Use: lower-latency models (Llama, local inference)

# For advisor tools (< 3s user expectation):
#   ✓ Suitable, but optimize:
#      - Cache guardrail checks (if output looks similar)
#      - Parallel nodes (fetch + cache lookup simultaneously)
#      - Use Claude Batch API for off-peak analysis

# Optimization example:
parallel_fetch = asyncio.gather(
    fetch_data("AAPL"),
    fetch_cache("AAPL", "1w")  # ← Parallel
)
# Saves ~500ms if both needed

# Code with parallelization:
from langgraph.graph import StateGraph
graph.add_edge("parse_query", ["fetch_data", "check_cache"])  # ← Both run
graph.add_edge(["fetch_data", "check_cache"], "analyze")
```

**For Wells Fargo:** "This is built for advisory workflows (3-5s response), not trading (milliseconds). If you need real-time, you'd use lower-latency models or pre-computed analysis. Different tool for different job."

---

## Technical Debt Questions

### "I noticed the guardrail disclaimer check failed. Why?"

**Q:** The disclaimer is clearly there. Why did validation fail?

**A:**
```python
# Current check (brittle):
def check_disclaimer(response):
    patterns = [
        r"not financial advice",
        r"disclaimer",
        r"consult"
    ]
    for pattern in patterns:
        if re.search(pattern, response, re.IGNORECASE):
            return True
    return False

# Problem: Claude says "⚠️ DISCLAIMER: This analysis is for informational..."
# But my regex looks for "not financial advice" (misses it)

# Solution 1: Better regex
patterns = [
    r"not (financial|investment) advice",
    r"disclaimer",
    r"for (informational|educational) purposes",  # ← Added
    r"consult.*advisor"
]

# Solution 2: LLM-based check (what I should do)
# Instead of regex, ask Claude: "Does this response include a disclaimer?"
# More robust, but slower/pricier

# Solution 3: Enforce structured output
output = {
    "recommendation": "...",
    "disclaimer": "This is not financial advice..."
}
# Then check: if 'disclaimer' in output
```

**For Wells Fargo:** "This is the kind of thing you catch in code review and fix iteratively. In production, I'd use an LLM-based check because financial advice disclaimers are nuanced. Regex is a shortcut for demos."

---

### "What if the LLM is down or slow?"

**Q:** Dependency on third-party services is risky. How do you handle outages?

**A:**
```python
# Current: No retry logic (should add)
def reason(state):
    try:
        response = llm.invoke([...])
    except Exception as e:
        return mock_response()  # ← Fallback

# Better: Exponential backoff + circuit breaker
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
def reason_with_retry(state):
    return llm.invoke([...])

# If all retries fail:
def reason(state):
    try:
        return reason_with_retry(state)
    except Exception:
        logger.error("Claude down, using cached analysis or mock")
        return mock_response_from_cache(state.current_query)

# Implementation:
# - Cache successful responses by query_hash
# - If LLM fails, return cached result from similar query
# - Fall back to simple rule-based recommendation
```

**For Wells Fargo:** "High availability is non-negotiable in finance. You'd add: LLM retry logic, fallback to simpler models (Llama), cached responses for common queries. This is a 'production hardening' task—not complex, just necessary."

---

## Integration Questions

### "How would you integrate this with Wells Fargo's existing systems?"

**Q:** Walk me through the integration architecture.

**A:**
```python
# Option 1: REST API wrapper
from fastapi import FastAPI
app = FastAPI()

@app.post("/analyze")
async def analyze(query: str):
    result = run_agent(query)
    return {
        "recommendation": result['final_response'],
        "score": result['guardrail_checks']['score'],
        "audit_trail": result['tool_calls']
    }

# Option 2: Embedded in advisor portal
# Import as library:
from financial_agent import run_agent
result = run_agent(user_query)
display_result(result)

# Option 3: Batch processing for overnight analysis
# Store queries in queue, process in batch with Claude Batch API

# Data integration:
# Wells Fargo has internal market data (not yfinance)
# Swap the data source:

class WFMarketDataTool(StockDataTool):
    def get_stock_data(self, symbol, period):
        # Instead of yfinance:
        data = wells_fargo_api.get_data(symbol, period)
        return data

# The agent doesn't care where data comes from (polymorphism)

# Compliance integration:
# Log all recommendations to audit database
audit_log = {
    "timestamp": datetime.now(),
    "advisor_id": session_id,
    "query": query,
    "recommendation": result,
    "guardrail_score": score,
    "tool_calls": tool_calls,
    "compliance_approved": score > 0.75
}
store_audit_log(audit_log)
```

**For Wells Fargo:** "The architecture is plugin-friendly. Replace yfinance with Bloomberg, add compliance checks, log to your audit DB—all without changing the core agent logic. That's what 'composable' means."

---

### "How would you add portfolio-level analysis?"

**Q:** The agent analyzes individual stocks. What about whole portfolios?

**A:**
```python
# Current: Single-stock analysis
Agent
  └─ Analyze AAPL

# Desired: Portfolio analysis
Agent
  ├─ Analyze AAPL, GOOGL, MSFT, NVDA (holdings)
  ├─ Calculate correlation matrix (diversification)
  ├─ Compute portfolio volatility (aggregate)
  ├─ Assess sector concentration
  └─ Recommend rebalancing

# Code addition:
def portfolio_analysis(state):
    """New node to analyze entire portfolio."""
    
    # Fetch all holdings
    holdings = state.portfolio_holdings  # {"AAPL": 0.4, "GOOGL": 0.3, ...}
    
    # Fetch data for all
    all_data = {
        symbol: fetch_data(symbol) 
        for symbol in holdings.keys()
    }
    
    # Compute aggregate metrics
    portfolio_vol = compute_portfolio_volatility(all_data, weights=holdings)
    correlations = compute_correlations(all_data)
    sector_exposure = analyze_sector_concentration(holdings)
    
    # Generate recommendation
    context = f"""
    Portfolio volatility: {portfolio_vol}%
    Sector concentration: {sector_exposure}
    Correlation matrix: {correlations}
    
    Should we rebalance?
    """
    
    recommendation = llm.invoke(context)
    
    state.portfolio_analysis = {
        "volatility": portfolio_vol,
        "sector_exposure": sector_exposure,
        "recommendation": recommendation
    }
    return state

# Add to graph:
graph.add_node("portfolio_analysis", portfolio_analysis)
graph.add_edge("analyze", "portfolio_analysis")
graph.add_edge("portfolio_analysis", "reason")  # Reason uses portfolio context
```

**For Wells Fargo:** "This is a 2-day feature. The hard part isn't the code—it's defining 'good rebalancing' for your compliance rules. Once you define that, adding the node is straightforward."

---

## Domain Knowledge Questions

### "How do you know these indicators are actually useful?"

**Q:** RSI, volatility, momentum—are these predictive or just noise?

**A:**
```python
# Good question. Honest answer:

# RSI (Relative Strength Index):
# ✓ Widely used, industry standard (80% overbought, 20% oversold)
# ✓ Incorporated in many trading systems
# ✗ Lagging indicator (historical, not predictive)
# ? Works well in range-bound markets, fails in trends

# Volatility:
# ✓ Useful for options pricing, risk assessment
# ✓ Can signal regime change
# ✗ Doesn't predict direction

# Momentum:
# ✓ Shows trend strength
# ✗ High momentum often means mean reversion coming

# Best approach: Ensemble
# Instead of single indicator, use multiple:
recommendation = ensemble_vote([
    rsi_signal(),
    momentum_signal(),
    mean_reversion_signal(),
    technical_support_levels(),
    fundamental_valuation(),
])

# For Wells Fargo:
# - Talk to their research team about what indicators matter
# - This agent is a framework (add any indicators)
# - Not claiming to predict markets (I'm not!)
# - Just organizing data intelligently with validation
```

**For Wells Fargo:** "I'm not claiming these indicators predict the market. I'm showing you can build a framework that applies whatever indicators your research team recommends, validates the output, and explains the reasoning. That's the value."

---

## Follow-up Questions

### "If you had more time, what would you build?"

**A:** See INTERVIEW_NARRATIVE.md Part 7 ("What I'd Do With More Time")

Key areas:
1. **Multi-asset classes:** Bonds, commodities, crypto
2. **Factor-based analysis:** Value, momentum, quality factors
3. **Risk metrics:** VaR, Sharpe ratio, Sortino ratio
4. **Scenario analysis:** "What if rates rise 100 bps?"
5. **Backtesting:** Did this strategy have worked historically?
6. **Client-specific rules:** "Avoid energy stocks due to ESG mandate"

---

### "Why Python? Why not [Java/C++/Go]?"

**A:**
```python
# Python reasons:
✓ Fast iteration (demo in 48 hours)
✓ Rich ML/data science ecosystem (pandas, numpy, sklearn)
✓ Easy integration with LLM APIs (langchain, langgraph)
✓ Type hints (mypy) give you safety without compilation

# Java reasons:
✓ Used at Wells Fargo (familiar)
✓ Better performance (matters at 1M QPS)
✓ Compiled safety (catches errors pre-production)
✓ Enterprise frameworks (Spring, Jakarta)

# My answer:
"For this project, Python was right for speed and clarity.
In production at Wells Fargo, you might use Java for:
  - Consistency with internal systems
  - Multi-threaded concurrency
  - Compiled performance
I could port the architecture to Java in a week.
The value is in the architecture, not the language."
```

---

### "What did you learn building this?"

**A:**
```python
# Technical lessons:
1. StateGraph is powerful for complex workflows
   - Much better than linear chains
   
2. Type hints catch bugs early
   - Pydantic forced me to think about data contracts
   
3. Guardrails are critical for LLM apps
   - You can't just trust the model's output
   
4. External APIs are unreliable
   - Mock fallback saved the demo

# Domain lessons:
1. Financial analysis is nuanced
   - Single indicator ≠ reliable signal
   - Need ensemble + validation
   
2. Disclaimers matter
   - Legally and ethically
   - Should be enforced by system, not hope

3. Audit trails are essential
   - Why did the system recommend this?
   - tool_calls log shows the reasoning path

# Process lessons:
1. Build incrementally (mock → real API)
2. Test each node independently
3. Document as you go (INTERVIEW_NARRATIVE.md)
4. Think about edge cases (what if yfinance is down?)
```

**For the interview:** "The biggest lesson was that building reliable AI isn't just about the model—it's about the system around it. Guardrails, logging, fallbacks, validation. That's what separates a demo from a production system."

---

## Emergency Fallbacks

**If they ask something you don't know:**

❓ "How would you optimize the LLM calls?"
✅ "Great question. I haven't benchmarked yet, but I'd start by: (1) measuring latency of each node, (2) caching high-frequency queries, (3) using batch API for off-peak. Let me think through the math..."

❓ "What about regulatory compliance?"
✅ "In banking, I'd expect requirements around: explainability (why did you recommend X?), audit trails (show all decisions), disclaimers (not financial advice), bias testing (does it favor certain strategies?). My tool_calls log + guardrail checks + disclaimers provide the foundation. The compliance team would add on top."

❓ "How does this compare to competitors like Bloomberg Terminal?"
✅ "Bloomberg is a full ecosystem (terminal, research, data feeds, $25k/year). This is a lightweight automation layer on top of free data. It's not a replacement—it's for internal advisor tools. Different market."


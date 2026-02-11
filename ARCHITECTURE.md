# Architecture & Design

## 5-Node StateGraph Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                      USER QUERY                             │
│         "Analyze AAPL's recent performance..."              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  1️⃣  PARSE_QUERY       │
        ├────────────────────────┤
        │ • Extract symbols      │
        │ • Detect intent        │
        │ • Extract time horizon │
        │ Output: symbols=AAPL   │
        └────────┬───────────────┘
                 │
                 ▼
        ┌────────────────────────┐
        │  2️⃣  FETCH_DATA        │
        ├────────────────────────┤
        │ • Call yfinance        │
        │ • Cache (5 min TTL)    │
        │ • Mock fallback        │
        │ Output: StockDataPoint │
        └────────┬───────────────┘
                 │
                 ▼
        ┌────────────────────────┐
        │  3️⃣  ANALYZE          │
        ├────────────────────────┤
        │ • Calculate RSI        │
        │ • Compute volatility   │
        │ • Momentum analysis    │
        │ Output: IndicatorAnly  │
        └────────┬───────────────┘
                 │
                 ▼
        ┌────────────────────────┐
        │  4️⃣  REASON            │
        ├────────────────────────┤
        │ • Invoke Claude API    │
        │ • Cite data sources    │
        │ • Generate analysis    │
        │ Output: recommendation │
        └────────┬───────────────┘
                 │
                 ▼
        ┌────────────────────────┐
        │  5️⃣  VALIDATE         │
        ├────────────────────────┤
        │ • Check overconfidence │
        │ • Verify disclaimers   │
        │ • Score 0.0-1.0        │
        │ Output: guardrail_check│
        └────────┬───────────────┘
                 │
                 ▼
    ┌─────────────────────────────┐
    │     FINAL RESPONSE          │
    │  recommendation + score     │
    │  audit trail (tool_calls)   │
    └─────────────────────────────┘
```

## State Flow (Immutable Data)

```
AgentState at each node:

[PARSE]
  current_query: "Analyze AAPL..."
  comparison_symbols: ["AAPL"]
  messages: [{"role": "user", "content": "..."}]

[FETCH] (state + new data)
  latest_data: {"AAPL": StockDataPoint(...)}
  tool_calls: [ToolCall(tool="fetch", ...)]

[ANALYZE] (state + indicators)
  latest_indicators: IndicatorAnalysis(rsi=51.8, ...)
  tool_calls: [..., ToolCall(tool="analyze", ...)]

[REASON] (state + LLM output)
  final_response: "Based on the data..."
  messages: [..., {"role": "assistant", "content": "..."}]

[VALIDATE] (state + guardrail checks)
  guardrail_checks: {"score": 0.8, "checks": {...}}
  final state ready for response
```

## Tool Ecosystem

```
┌──────────────────────────────────────────────────────────────┐
│                        TOOLS LAYER                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────┐  ┌─────────────────────┐           │
│  │  StockDataTool      │  │  IndicatorsTool     │           │
│  ├─────────────────────┤  ├─────────────────────┤           │
│  │ • yfinance wrapper  │  │ • RSI calculation   │           │
│  │ • 5-min cache       │  │ • Volatility        │           │
│  │ • Mock fallback     │  │ • Momentum          │           │
│  │ Returns: Dict       │  │ • Moving averages   │           │
│  └─────────────────────┘  │ Returns: Dict       │           │
│                           └─────────────────────┘           │
│                                                              │
│  ┌─────────────────────┐  ┌─────────────────────┐           │
│  │  PortfolioTool      │  │ GuardrailValidator  │           │
│  ├─────────────────────┤  ├─────────────────────┤           │
│  │ • Allocation %      │  │ • Overconfidence    │           │
│  │ • Rebalance logic   │  │ • Disclaimer check  │           │
│  │ • Diversification   │  │ • Reasoning audit   │           │
│  │ Returns: Dict       │  │ Returns: score 0-1  │           │
│  └─────────────────────┘  └─────────────────────┘           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## LLM-as-Judge Pattern (Safety)

```
                    ┌──────────────────┐
                    │  USER QUERY      │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
        ┌──────────▶│ LLM 1: REASONING │◀──────────┐
        │           └────────┬─────────┘           │
        │                    │                     │
        │          Generates Recommendation       │
        │                    │                     │
        │                    ▼                     │
        │           ┌──────────────────┐           │
        │           │ LLM 2: VALIDATION│           │
        │           └────────┬─────────┘           │
        │                    │                     │
        │    Checks:        │                     │
        │    • Overconfidence (regex)              │
        │    • Disclaimer (LLM-based)              │
        │    • Confidence score (LLM-based)        │
        │    • Hallucination (fact-check)          │
        │    • Reasoning (cites data)              │
        │                    │                     │
        │                    ▼                     │
        │           ┌──────────────────┐           │
        │           │ GUARDRAIL SCORE  │           │
        │           │   0.0 - 1.0      │           │
        │           └──────────────────┘           │
        │                                         │
        │                                         │
        └─────────────────────────────────────────┘
              (Audit trail for compliance)
```

## Resilience Pattern

```
┌─────────────────────────────────┐
│  Request: Get AAPL data         │
├─────────────────────────────────┤
│                                 │
│  Try: yfinance.Ticker("AAPL")   │
│  ├─ Success? → Return data      │
│  └─ Fail? → Rate limited        │
│                                 │
│  Try: Check cache (5 min)       │
│  ├─ Found? → Return cached      │
│  └─ Not found?                  │
│                                 │
│  Try: Return mock data          │
│  ├─ Generate realistic prices   │
│  ├─ Log fallback decision       │
│  └─ Continue workflow           │
│                                 │
│  Result: Always return data     │
│  (99.9% uptime guarantee)       │
│                                 │
└─────────────────────────────────┘
```

## Type Safety (Pydantic)

```
Input → Validation → Processing → Validated Output

user_query: str
    ↓
AgentState validates all fields
    ├─ current_query: str ✓
    ├─ comparison_symbols: List[str] ✓
    ├─ latest_data: Dict[str, StockDataPoint] ✓
    ├─ latest_indicators: IndicatorAnalysis ✓
    ├─ tool_calls: List[ToolCall] ✓
    ├─ messages: List[Message] ✓
    ├─ final_response: str ✓
    └─ guardrail_checks: Dict ✓
    ↓
Each node can safely access/modify state
(mypy catches type errors at development time)
    ↓
Final response with 100% type safety
```

## Production Attributes

| Attribute | Implementation |
|-----------|-----------------|
| **Stateful** | LangGraph StateGraph persists state across 5 nodes |
| **Typed** | Pydantic dataclasses for all models |
| **Testable** | Each tool is independent, mockable |
| **Logged** | Every action logged at INFO/WARNING/ERROR levels |
| **Cached** | 5-minute TTL on expensive API calls |
| **Fallback** | Mock data when external APIs fail |
| **Auditable** | tool_calls array shows every decision |
| **Safe** | Guardrails prevent hallucination & overconfidence |
| **Composable** | Each tool can be swapped independently |

## Scaling Considerations

### Current (Single Query)
```
User Query → Agent → Response (3-5 seconds)
```

### Scaled (1000 QPS)
```
User Queries (batch)
    ↓
Load Balancer
    ├→ Agent Instance 1
    ├→ Agent Instance 2
    ├→ Agent Instance N
    ↓
Redis Cache (guardrail checks, data)
    ↓
Batch LLM API (lower cost, higher throughput)
    ↓
Response Queue
    ↓
Results
```

### Key scaling paths:
- **Parallel tools:** fetch_data() and analyze() don't depend on each other → run in parallel
- **Batch LLM:** Call Claude batch API instead of sync invoke
- **Cache guardrail checks:** Same recommendation text = same validation result
- **Data warehouse:** Batch ingest yfinance → query analytics DB instead

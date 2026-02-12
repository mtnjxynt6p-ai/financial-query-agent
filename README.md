# Financial Query Agent with LangGraph

A production-grade financial analysis agent demonstrating **agentic orchestration**, **tool composition**, and **LLM-as-judge validation** using LangGraph + LangChain + Claude.

## Quick Demo (2-3 minutes)

```bash
python3 demo.py
```

This shows the full 5-node workflow: parsing → fetching → analyzing → reasoning → validating.

## Features

- **Multi-step agent orchestration**: 5-node StateGraph (parse → fetch → analyze → reason → validate)
- **Tool ecosystem**: Stock data (yfinance + mock fallback), technical indicators, portfolio context
- **Stateful workflows**: Conversation memory + analysis state across nodes
- **Guardrails**: LLM-as-judge validation (5 checks: overconfidence, disclaimer, confidence_score, reasoning, hallucination)
- **Production-ready**: Type hints, logging, error handling, audit trails, caching

## Architecture

```
User Query
    ↓
[1] PARSE: Extract symbols & intent
    ↓
[2] FETCH: Get data (yfinance + mock fallback)
    ↓
[3] ANALYZE: Calculate technical indicators (RSI, volatility, momentum)
    ↓
[4] REASON: Claude generates recommendation
    ↓
[5] VALIDATE: Guardrails check for hallucination & safety
    ↓
Response (recommendation + 0.0-1.0 guardrail score)
```

## Project Structure

```
financial_agent/
├── README.md                      # This file
├── requirements.txt               # Dependencies
├── .env.example                   # AWS Bedrock credentials template
│
├── agent.py                       # Core agent: StateGraph + nodes
├── state.py                       # Pydantic data models
├── tools.py                       # Three tools: StockDataTool, IndicatorsTool, PortfolioTool
├── prompts.py                     # System prompts & templates
├── guardrails.py                  # LLM-as-judge validation
│
├── streamlit_app.py               # Web UI for the agent (Streamlit)
├── demo.py                        # Clean 2-3 minute CLI demo
├── run_examples.py                # Run all 5 example queries
├── run_demo.py                    # Demo mode (no API keys needed)
├── test_agent.py                  # Unit tests
└── run_all_examples.py            # Batch runner for examples
```

## Installation & Usage

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure AWS Bedrock credentials
```bash
cp .env.example .env
# Edit .env with your AWS credentials
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
# AWS_REGION=us-east-1
```

### 3. Run the agent

**Option A: Web UI (Recommended)**
```bash
# Start Streamlit web interface
streamlit run streamlit_app.py
```
Opens at `http://localhost:8501` with:
- Interactive query input with example buttons
- Real-time results with metrics (guardrail score, symbols, tool calls)
- Expandable guardrail validation details
- Full results JSON for transparency

**Option B: Command-line demos**
```bash
# Quick 2-3 min demo (2 queries)
python3 demo.py

# Full examples (5 queries, ~5 min)
python3 run_examples.py

# Mock mode (no API keys needed, all guardrails pass 1.0/1.0)
python3 run_demo.py
```

## What It Does (Example Output)

**Query:** "Analyze AAPL's recent performance and suggest if I should hedge with options if volatility > 30%"

**Agent processes:**
1. **Parse:** Extracts AAPL, detects hedging intent
2. **Fetch:** Gets AAPL price ($184.16), volume, dates
3. **Analyze:** Calculates RSI=51.8, Volatility=1.5%, Momentum=-2.6%
4. **Reason:** Claude analyzes data: "Volatility is low (1.5% < 30%), so hedging not needed"
5. **Validate:** 5 checks pass, score=0.80/1.0

**Final Response:**
```
✓ Recommendation: Do not hedge. Volatility is low.
✓ Guardrail score: 0.80/1.0
✓ Symbols analyzed: AAPL
✓ Tool calls: 2
✓ Validation checks: 4/5 passed
```



## Technical Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **StateGraph** | Persistent state, testable nodes | More complex than linear chains |
| **Dual-LLM** (reason + validate) | Safety + explainability | Higher latency/cost |
| **Mock fallback** | Resilience, demo-friendly | More code |
| **AWS Bedrock** | Enterprise, VPC-isolated | Higher latency than direct API |
| **Pydantic models** | Type safety, validation | Boilerplate code |

## Development

### Run tests
```bash
pytest test_agent.py -v
```

### Enable debug logging
```bash
export LOG_LEVEL=DEBUG
python3 run_examples.py
```

### Extend the agent
- Add new tools in `tools.py`
- Add new validation checks in `guardrails.py`
- Add new nodes in `agent.py` (modify StateGraph)

## What I'd Build With More Time

1. **Portfolio analysis node**: Multi-stock correlation, rebalancing
2. **Risk metrics**: VaR, Sharpe ratio, scenario analysis ("what if rates +100bps?")
3. **Factor-based analysis**: Value, momentum, quality factors
4. **Backtesting**: Did this strategy have worked historically?
5. **Compliance filters**: Reject recommendations violating investment policy



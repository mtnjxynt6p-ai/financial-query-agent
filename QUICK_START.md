# Quick Start Guide

## 1️⃣ Install & Setup (2 minutes)

```bash
# Navigate to the project
cd /Users/russellbrown/brown-bi-com-react/financial_agent

# Install dependencies
pip install -r requirements.txt

# (Optional) Set your API key if you want to use real Claude
export ANTHROPIC_API_KEY=sk-ant-xxxxx...
# or edit .env file
```

## 2️⃣ Run the Demo (30 seconds)

```bash
# Run with mock data (no API key needed!)
python run_demo.py
```

**Expected output**: The agent analyzes AAPL, shows indicators (RSI, volatility, momentum), generates a recommendation, and validates it. All guardrails pass (score 1.0).

## 3️⃣ Try Custom Queries

```bash
# Run with a custom query
python3 run_demo.py "Compare TSLA and NVDA. Which is better for growth?"

# Or run example queries (requires AWS credentials)
python3 run_examples.py

# Run specific example
python3 run_examples.py 2
```

## 4️⃣ Run Tests

```bash
# Run all tests
pytest test_agent.py -v

# Run specific test
pytest test_agent.py::TestStockDataTool -v
```

## 5️⃣ Explore the Code

| File | What It Does |
|------|-----------|
| [state.py](state.py) | Data models (AgentState, Message, AnalysisResult) |
| [tools.py](tools.py) | Stock data, technical analysis, portfolio tools |
| [agent.py](agent.py) | LangGraph orchestration (THE CORE) |
| [prompts.py](prompts.py) | System prompts + templates |
| [guardrails.py](guardrails.py) | LLM-as-judge validation |
| [run_demo.py](run_demo.py) | Demo runner (mock data) |
| [run_examples.py](run_examples.py) | Real queries (needs API key) |
| [test_agent.py](test_agent.py) | Unit tests |

## 📖 What to Read

1. **First**: [README.md](README.md) - Overview
2. **Then**: [SETUP_GUIDE.md](SETUP_GUIDE.md) - Architecture + customization
3. **For interview**: [INTERVIEW_TALKING_POINTS.md](INTERVIEW_TALKING_POINTS.md) - How to explain it

## 🎯 What the Agent Does

```
User Query
    ↓
[Parse] Extract stocks (AAPL, TSLA, ...)
    ↓
[Fetch] Get real-time prices & volume
    ↓
[Analyze] Calculate RSI, volatility, momentum
    ↓
[Reason] LLM generates recommendation
    ↓
[Validate] Check for hallucination, disclaimers, overconfidence
    ↓
Recommendation + Confidence Score + Guardrail Checks
```

## 💡 Interview Prep Checklist

- [ ] Run the demo: `python run_demo.py`
- [ ] Read [INTERVIEW_TALKING_POINTS.md](INTERVIEW_TALKING_POINTS.md)
- [ ] Understand [agent.py](agent.py) (the orchestration logic)
- [ ] Practice explaining "StateGraph" + "tool integration" + "guardrails"
- [ ] Try a custom query with `run_demo.py "your query here"`
- [ ] Review the guardrail checks (how does the agent prevent hallucination?)
- [ ] Think about: "How would you scale this to 1000 concurrent agents?"

## 🚀 Next Steps

### To Run with Real LLM (Claude API)
1. Get an API key from https://console.anthropic.com
2. Set `export ANTHROPIC_API_KEY=sk-ant-xxxxx...`
3. Run: `python run_examples.py`

### To Modify the Agent
1. Add a new tool in [tools.py](tools.py)
2. Import it in [agent.py](agent.py)
3. Create a new node function (e.g., `def fetch_news(state)`)
4. Add the node to the graph: `graph.add_node("fetch_news", fetch_news)`
5. Add edges: `graph.add_edge("fetch_data", "fetch_news")`

### To Add More Guardrails
1. Add a check method in [guardrails.py](guardrails.py)
2. Call it in `GuardrailValidator.validate()`
3. Test it with `pytest test_agent.py::TestGuardrailValidator`

## ⚡ Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'langgraph'` | Run `pip install -r requirements.txt` |
| `Error: Could not resolve authentication method` | The demo uses mock LLM; this is normal. Real queries need API key. |
| `No data found for symbol AAPL` | The agent falls back to mock data. This is intentional for demo mode. |
| Test fails with `AttributeError: 'dict' object has no attribute 'Close'` | Use `tools.py` from this project (not your own). |

## 📞 Quick Reference

```bash
# Demos
python3 run_demo.py                                    # Default query, mock data
python3 run_demo.py "Analyze TSLA volatility"          # Custom query, mock data
python3 run_examples.py                                # Real queries (needs API key)

# Tests
pytest test_agent.py -v                               # All tests
pytest test_agent.py::TestTools -v                    # Just tool tests

# One-liners
python -c "from tools import StockDataTool; t=StockDataTool(use_mock=True); print(t.get_stock_data('AAPL'))"
```

## 🎓 Key Concepts

- **StateGraph**: LangGraph's way of orchestrating multi-step workflows
- **AgentState**: Mutable context object that flows through each node
- **Tool Integration**: ReAct pattern—Reason → Act (call tool) → Observe (update state)
- **Guardrails**: LLM-as-judge to prevent hallucination & overconfidence
- **Pydantic**: Type-safe data validation at runtime

You've got this! 🚀

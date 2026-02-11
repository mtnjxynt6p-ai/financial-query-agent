# Financial Agent Project Structure & File Guide

## 📁 Directory Contents

```
financial_agent/
├── 📄 README.md                       # Main documentation
├── 📄 QUICK_START.md                  # Get running in 2 minutes
├── 📄 SETUP_GUIDE.md                  # Detailed architecture & customization
├── 📄 INTERVIEW_TALKING_POINTS.md     # How to explain this in interviews
├── 📋 PROJECT_STRUCTURE.md            # This file
│
├── requirements.txt                   # Python dependencies (pip install -r)
├── .env.example                       # Environment variables template
├── .env                               # Your local .env (add API key here)
│
├── 🔧 CORE IMPLEMENTATION
│   ├── state.py                       # Data models (AgentState, Message, etc.)
│   ├── tools.py                       # Stock data, indicators, portfolio tools
│   ├── agent.py                       # LangGraph orchestration (THE MAIN FILE)
│   ├── prompts.py                     # System prompts + templates
│   └── guardrails.py                  # LLM-as-judge validation
│
├── 🚀 RUNNERS & EXAMPLES
│   ├── run_demo.py                    # Demo with mock data (no API key needed!)
│   └── run_examples.py                # Real examples (requires API key)
│
└── 🧪 TESTS
    └── test_agent.py                  # Unit tests (pytest)
```

---

## 📚 File Descriptions

### Documentation Files

#### README.md
- **Purpose**: Overview of the project, features, architecture, quick start
- **For**: First-time readers, understanding what the project does
- **Key sections**: Features, structure, quick start, interview talking points

#### QUICK_START.md
- **Purpose**: Get the project running in 2 minutes
- **For**: Impatient users, demo time, quick testing
- **Key sections**: Install, run demo, try queries, run tests

#### SETUP_GUIDE.md
- **Purpose**: Deep dive into architecture, customization, troubleshooting
- **For**: Understanding how it works, modifying it, deploying
- **Key sections**: Architecture, file structure, how to use, customization, troubleshooting

#### INTERVIEW_TALKING_POINTS.md
- **Purpose**: How to explain your work in an interview
- **For**: Interview preparation, explaining code
- **Key sections**: Technical points, interview script, follow-up answers, project statistics

#### PROJECT_STRUCTURE.md
- **Purpose**: This file. Explains all files in the project
- **For**: Navigating the codebase

---

### Core Implementation Files

#### state.py
- **Purpose**: Define all data models using Pydantic
- **Classes**:
  - `Message`: A single message (user/assistant/system)
  - `StockDataPoint`: Price, volume, date, high/low/open/close
  - `IndicatorAnalysis`: RSI, volatility, momentum, MAs, signal strength
  - `AnalysisResult`: Complete analysis for a stock
  - `ToolCall`: Log entry for a tool invocation
  - `AgentState`: Main state object (conversation, analysis, portfolio, tool calls)
- **Key methods**:
  - `add_message()`: Add to conversation history
  - `log_tool_call()`: Log a tool invocation
  - `get_conversation_history()`: Retrieve recent messages
- **Why**: Type-safe, immutable data contracts between modules

#### tools.py
- **Purpose**: Implement three composable tools
- **Classes**:
  - `StockDataTool`: Fetch stock data from yfinance (with caching + mock fallback)
  - `IndicatorsTool`: Calculate RSI, volatility, momentum, MAs, signal strength
  - `PortfolioTool`: Analyze allocation, suggest rebalancing
- **Key methods**:
  - `StockDataTool.get_stock_data()`: Fetch OHLCV data
  - `IndicatorsTool.analyze_stock()`: Full technical analysis
  - `PortfolioTool.calculate_allocation()`: % allocation
- **Why**: Modular, testable, independent of agent logic

#### agent.py
- **Purpose**: LangGraph StateGraph orchestration (THE CORE AGENT)
- **Node functions**:
  - `parse_query()`: Extract symbols from user query
  - `fetch_data()`: Get stock data for each symbol
  - `analyze()`: Calculate indicators
  - `reason()`: LLM generates recommendation
  - `validate()`: Guardrail checks
- **Key functions**:
  - `build_agent_graph()`: Construct the StateGraph
  - `run_agent()`: Execute the workflow
  - `print_agent_output()`: Pretty-print results
- **Why**: Shows how to orchestrate multi-step workflows with LangGraph

#### prompts.py
- **Purpose**: All prompts and templates in one place
- **Constants**:
  - `SYSTEM_PROMPT`: Role, constraints, guidelines
  - `REASONING_PROMPT`: Step-by-step reasoning guide
  - `GUARDRAIL_PROMPT`: Validation prompt
  - `OUTPUT_TEMPLATE`: Formatted output template
  - `EXAMPLES`: Few-shot examples for in-context learning
- **Key functions**:
  - `get_system_prompt()`: Return system prompt
  - `format_output()`: Format final response
- **Why**: Centralize prompting logic, easy to iterate/tweak

#### guardrails.py
- **Purpose**: Validate agent outputs to prevent hallucination & overconfidence
- **Class**: `GuardrailValidator`
- **Methods**:
  - `check_overconfidence()`: Regex check for absolute language
  - `check_has_disclaimer()`: Ensure financial advice disclaimer
  - `check_has_confidence_score()`: Score must be explicit
  - `check_has_reasoning()`: Must cite data
  - `check_no_hallucination()`: Flag predictive claims
  - `validate()`: Run all checks, return score
  - `suggest_improvements()`: Recommendations if any checks fail
- **Why**: Safety first. Financial systems must prevent harmful outputs.

---

### Runner Files

#### run_demo.py
- **Purpose**: Demonstrate the agent WITHOUT API keys (uses mock data)
- **Key function**: `run_agent_demo()` (calls parse_query → fetch → analyze → mock_reason → validate)
- **What it shows**: Full workflow, guardrail checks passing, tool calls logged
- **When to use**: Quick demo, interview prep, testing without API
- **Run**: `python run_demo.py "your query"`

#### run_examples.py
- **Purpose**: Run realistic financial queries with real LLM
- **Examples**: 5 pre-built queries (single stock, comparison, technical, hedging, trends)
- **What it requires**: ANTHROPIC_API_KEY set in environment
- **When to use**: After setting up AWS credentials, testing with real Claude
- **Run**: `python3 run_examples.py` or `python3 run_examples.py 1` or `python3 run_examples.py "custom query"`

---

### Test File

#### test_agent.py
- **Purpose**: Unit tests for all components
- **Test classes**:
  - `TestState`: AgentState creation, messages, history
  - `TestStockDataTool`: Data fetching, caching
  - `TestIndicatorsTool`: RSI, volatility, momentum, signal
  - `TestPortfolioTool`: Allocation, rebalancing
  - `TestGuardrailValidator`: Overconfidence, disclaimer, confidence, reasoning, hallucination
- **Run**: `pytest test_agent.py -v`
- **Why**: Ensure each component works independently

---

## 🔄 Data Flow

```
USER QUERY
    ↓
state.py (AgentState created)
    ↓
agent.py::parse_query() 
    ↑ uses prompts.py system prompt (if LLM available)
    ↑ fallback to regex extraction
    ↓ updates state.comparison_symbols
    ↓
agent.py::fetch_data()
    ↑ uses tools.py::StockDataTool
    ↓ updates state.latest_data, state.tool_calls
    ↓
agent.py::analyze()
    ↑ uses tools.py::IndicatorsTool
    ↓ updates state.latest_indicators, state.tool_calls
    ↓
agent.py::reason()
    ↑ calls Claude LLM with state context
    ↑ uses prompts.py system prompt + reasoning prompt
    ↓ updates state.final_response
    ↓
agent.py::validate()
    ↑ uses guardrails.py::GuardrailValidator
    ↓ updates state.guardrail_checks
    ↓
FINAL OUTPUT (recommendation + confidence + metadata)
```

---

## 🚀 Common Tasks

### Task: Run the demo
```bash
python run_demo.py
```
**Files involved**: run_demo.py → agent.py → tools.py → guardrails.py

### Task: Run tests
```bash
pytest test_agent.py -v
```
**Files involved**: test_agent.py → state.py, tools.py, guardrails.py

### Task: Add a new tool
1. Edit `tools.py` (add class + methods)
2. Import in `agent.py`
3. Create node function (e.g., `def fetch_news(state)`)
4. Add to graph: `graph.add_node(...)`
5. Connect edges

### Task: Modify system prompt
1. Edit `prompts.py` (update `SYSTEM_PROMPT`)
2. Re-run `python3 run_examples.py`

### Task: Add a guardrail check
1. Edit `guardrails.py` (add method to `GuardrailValidator`)
2. Call in `validate()` method
3. Add test in `test_agent.py`

---

## 📊 File Statistics

| File | Lines | Purpose | Complexity |
|------|-------|---------|------------|
| state.py | ~150 | Data models | Low |
| tools.py | ~320 | Stock/analysis/portfolio | Medium |
| agent.py | ~250 | LangGraph orchestration | Medium |
| prompts.py | ~170 | Prompts + templates | Low |
| guardrails.py | ~240 | Validation | Medium |
| run_demo.py | ~180 | Demo runner | Low |
| run_examples.py | ~110 | Example runner | Low |
| test_agent.py | ~310 | Tests | Medium |
| **TOTAL** | **~1,730** | **Full agent system** | **Medium** |

---

## 🎓 Learning Path

### If you're new to LangGraph:
1. Read `README.md`
2. Understand `state.py` (what data flows through?)
3. Read `agent.py` (how are nodes connected?)
4. Run `python run_demo.py` (see it in action)

### If you're new to financial analysis:
1. Read `tools.py` (what indicators matter?)
2. Play with `IndicatorsTool` calculations
3. Read `prompts.py` (how do we reason about markets?)
4. Modify queries in `run_demo.py`

### If you're preparing for interview:
1. Read `INTERVIEW_TALKING_POINTS.md` (practice script)
2. Run `python run_demo.py` (show it working)
3. Explain each file's purpose (use this guide)
4. Discuss: How would you extend this to trading workflows?

---

## 🔗 Dependencies

- **langgraph**: Workflow orchestration
- **langchain**: LLM integrations + tools
- **langchain-anthropic**: Claude API support
- **yfinance**: Stock data
- **pandas**: Data manipulation
- **pydantic**: Type validation
- **pytest**: Testing

See `requirements.txt` for exact versions.

---

## 📞 Quick Navigation

**Want to understand**: Go to file:
- Agent architecture? → `agent.py` + `SETUP_GUIDE.md`
- How tools work? → `tools.py` + code examples
- Data models? → `state.py` + `SETUP_GUIDE.md`
- Validation/safety? → `guardrails.py` + `INTERVIEW_TALKING_POINTS.md`
- Examples? → `run_demo.py` or `run_examples.py`
- Tests? → `test_agent.py`

---

Good luck with your interview! This structure is designed to be explored progressively—start with docs, then code, then running examples. 🚀

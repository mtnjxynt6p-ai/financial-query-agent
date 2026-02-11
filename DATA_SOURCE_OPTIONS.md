# Options to Get Real Stock Prices

## Problem
Yahoo Finance is blocking requests from your environment (likely geolocation-based or IP-based restriction). Both `yfinance` and `pandas_datareader` (which use Yahoo) are affected.

## Solutions

### Option 1: Use Alpha Vantage API (Recommended for Demo)
Free tier: 5 calls/min, 500 calls/day (more than enough)
- Requires free API key from https://www.alphavantage.co/

```python
# Add to .env:
ALPHA_VANTAGE_API_KEY=your_key_here

# Then use:
python3 demo.py  # Will automatically try Alpha Vantage
```

### Option 2: Use Polygon.io API  
Free tier: 5 calls/min
- Requires free API key from https://polygon.io/

### Option 3: Use IEX Cloud API
Free tier: 100 calls/month (limited but free)
- Requires free API key from https://iexcloud.io/

### Option 4: Use a paid data service
- Bloomberg Terminal (if your organization has it)
- FactSet
- Reuters Eikon

### Option 5: Continue with Mock Data (Interview-Friendly)
✓ Works reliably
✓ Shows system design without API dependencies
✓ Realistic prices ($273 for AAPL, etc.)
✓ Perfect for demos

**I recommend:** Get a free Alpha Vantage key (takes 2 min), and I'll integrate it. Falls back to mock data if API fails.

## Current Code Status
The agent now has 3-tier fallback:
1. yfinance (blocked)
2. pandas_datareader (blocked - same API)
3. Mock data (always works) ✓

To add Alpha Vantage, I'll add tier 2 (before mock fallback).

## What to do next?

1. **Get real data:** Sign up for free Alpha Vantage key, I'll integrate it (5 min setup)
2. **Keep mock mode:** It works great and is interview-friendly anyway
3. **Use interview workaround:** During interview, explain that in production you'd use Bloomberg/FactSet, but demo uses realistic mock prices

Which would you prefer?

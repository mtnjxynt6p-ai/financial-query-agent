#!/usr/bin/env python3
"""Test real data fetching with fallback approach."""

from tools import StockDataTool

print("Testing with REAL data (use_mock=False):\n")
tool = StockDataTool(use_mock=False)

for symbol in ['AAPL', 'TSLA', 'NVDA']:
    data = tool.get_stock_data(symbol, period='1d')
    if data:
        print(f"✓ {symbol}: ${data['price']:.2f} (REAL DATA!)")
    else:
        print(f"✗ {symbol}: failed to fetch")

#!/usr/bin/env python3
"""Diagnose why Yahoo Finance is blocking requests."""

import requests
import yfinance as yf

print("=" * 80)
print("YAHOO FINANCE DIAGNOSTIC")
print("=" * 80)

# Test 1: Direct HTTP request to Yahoo Finance
print("\n1. Testing direct HTTP request to Yahoo Finance...")
try:
    url = "https://query1.finance.yahoo.com/v8/finance/chart/AAPL?interval=1d&range=1d"
    
    # Without user-agent
    print("   Trying WITHOUT user-agent...")
    resp = requests.get(url, timeout=10)
    print(f"   Status: {resp.status_code}")
    print(f"   Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
    print(f"   Content length: {len(resp.text)} bytes")
    if resp.status_code != 200:
        print(f"   First 200 chars: {resp.text[:200]}")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n   Trying WITH proper user-agent...")
try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"   Status: {resp.status_code}")
    print(f"   Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
    if resp.status_code == 200:
        print(f"   ✓ SUCCESS! Got {len(resp.text)} bytes of data")
        # Try to parse JSON
        try:
            data = resp.json()
            if 'chart' in data and 'result' in data['chart']:
                price = data['chart']['result'][0]['meta']['regularMarketPrice']
                print(f"   ✓ AAPL current price: ${price}")
        except:
            print(f"   ✗ Can't parse JSON response")
    else:
        print(f"   First 200 chars: {resp.text[:200]}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 2: yfinance with default session
print("\n2. Testing yfinance with default session...")
try:
    ticker = yf.Ticker("AAPL")
    hist = ticker.history(period="1d")
    if len(hist) > 0:
        print(f"   ✓ SUCCESS! Got {len(hist)} rows")
        print(f"   Latest close: ${hist['Close'].iloc[-1]:.2f}")
    else:
        print(f"   ✗ Empty dataframe returned")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 3: yfinance with custom session
print("\n3. Testing yfinance with custom session + headers...")
try:
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    })
    
    ticker = yf.Ticker("AAPL", session=session)
    hist = ticker.history(period="1d")
    if len(hist) > 0:
        print(f"   ✓ SUCCESS! Got {len(hist)} rows")
        print(f"   Latest close: ${hist['Close'].iloc[-1]:.2f}")
    else:
        print(f"   ✗ Empty dataframe returned")
except Exception as e:
    print(f"   ERROR: {e}")

# Test 4: Check if it's a network issue
print("\n4. Testing network connectivity...")
try:
    # Try a simple request to Yahoo's main site
    resp = requests.get("https://finance.yahoo.com", timeout=5)
    print(f"   Yahoo Finance homepage: {resp.status_code}")
    
    # Try another financial API
    resp = requests.get("https://www.google.com", timeout=5)
    print(f"   Google (control): {resp.status_code}")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n" + "=" * 80)
print("DIAGNOSIS COMPLETE")
print("=" * 80)

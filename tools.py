"""
Tools for the Financial Query Agent.

Includes: stock data fetching, technical indicators, portfolio analysis.
"""

import logging
from typing import Optional, List, Dict
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import requests
import time

logger = logging.getLogger(__name__)


class StockDataTool:
    """Fetches and caches stock data from Yahoo Finance API."""
    
    def __init__(self, cache_duration_minutes: int = 5, use_mock: bool = False):
        self.cache: Dict[str, tuple] = {}  # {symbol: (timestamp, data)}
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        self.use_mock = use_mock  # Use mock data if API fails
        self.last_request_time = 0  # Track last API call for rate limiting
        self.min_request_interval = 1.0  # Minimum 1 second between requests
    
    def _get_mock_data(self, symbol: str) -> Dict:
        """Generate realistic mock data for testing."""
        import random
        base_prices = {
            "AAPL": 273,      # Updated to Feb 2026 realistic price
            "TSLA": 280,      # Updated to Feb 2026 realistic price
            "NVDA": 920,      # Updated to Feb 2026 realistic price
            "GOOGL": 190,     # Updated to Feb 2026 realistic price
            "MSFT": 460,      # Updated to Feb 2026 realistic price
            "AMZN": 250,      # Updated to Feb 2026 realistic price
        }
        
        base = base_prices.get(symbol.upper(), 100)
        noise = random.uniform(-0.05, 0.05)
        price = base * (1 + noise)
        
        return {
            "symbol": symbol.upper(),
            "price": price,
            "open": price * 0.98,
            "high": price * 1.02,
            "low": price * 0.95,
            "volume": random.randint(10_000_000, 100_000_000),
            "date": str(datetime.now().date()),
            "change_percent": float(random.uniform(-3, 3)),
            "history": pd.DataFrame({
                "Close": [base * (1 + random.uniform(-0.02, 0.02)) for _ in range(252)]
            })
        }
    
    def get_stock_data(
        self, 
        symbol: str, 
        period: str = "1y"
    ) -> Optional[Dict]:
        """
        Fetch stock data for a symbol.
        
        Args:
            symbol: Stock ticker (e.g., "AAPL")
            period: Data period ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y")
        
        Returns:
            Dict with price, volume, date, and range info, or None on error.
        """
        # Check cache
        if symbol in self.cache:
            timestamp, cached_data = self.cache[symbol]
            if datetime.now() - timestamp < self.cache_duration:
                logger.info(f"Using cached data for {symbol}")
                return cached_data
        
        try:
            logger.info(f"Fetching data for {symbol} (period={period})")
            
            # Rate limiting: wait if needed
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_request_interval:
                wait_time = self.min_request_interval - elapsed
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
                time.sleep(wait_time)
            
            # Try direct Yahoo Finance API with exponential backoff
            for attempt in range(3):  # Max 3 attempts
                try:
                    data = self._fetch_from_yahoo_api(symbol, period)
                    if data:
                        self.cache[symbol] = (datetime.now(), data)
                        logger.info(f"✓ Got data for {symbol}: ${data['price']:.2f}")
                        self.last_request_time = time.time()
                        return data
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:
                        # Rate limited - exponential backoff
                        wait_time = (2 ** attempt) * 2  # 2s, 4s, 8s
                        logger.warning(f"Rate limited (429). Waiting {wait_time}s before retry {attempt+1}/3")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.warning(f"HTTP error {e.response.status_code} for {symbol}")
                        break
                except Exception as e:
                    logger.warning(f"API call failed for {symbol}: {str(e)[:80]}")
                    break
            
            # Fallback to mock data
            logger.warning(f"Could not fetch real data for {symbol}")
            if self.use_mock:
                logger.info(f"Using mock data for {symbol}")
                data = self._get_mock_data(symbol)
                self.cache[symbol] = (datetime.now(), data)
                return data
            return None
        
        except Exception as e:
            logger.error(f"Unexpected error fetching data for {symbol}: {e}")
            if self.use_mock:
                logger.info(f"Falling back to mock data for {symbol}")
                data = self._get_mock_data(symbol)
                self.cache[symbol] = (datetime.now(), data)
                return data
            return None
    
    def _fetch_from_yahoo_api(self, symbol: str, period: str) -> Optional[Dict]:
        """Fetch stock data directly from Yahoo Finance API."""
        # Convert period to timestamps
        end = int(datetime.now().timestamp())
        period_map = {
            '1d': 86400,
            '5d': 86400 * 5,
            '1mo': 86400 * 30,
            '3mo': 86400 * 90,
            '6mo': 86400 * 180,
            '1y': 86400 * 365,
            '2y': 86400 * 730,
            '5y': 86400 * 1825
        }
        period_seconds = period_map.get(period, 86400 * 365)
        start = end - period_seconds
        
        # Yahoo Finance API endpoint
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}'
        params = {
            'period1': start,
            'period2': end,
            'interval': '1d'
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://finance.yahoo.com/'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()  # Raise HTTPError for bad status codes
        
        data = response.json()
        
        # Parse response
        if 'chart' not in data or 'result' not in data['chart']:
            return None
        
        result = data['chart']['result'][0]
        if 'timestamp' not in result or not result['timestamp']:
            return None
        
        # Extract price data
        quotes = result['indicators']['quote'][0]
        timestamps = result['timestamp']
        
        # Build DataFrame for historical data
        hist_data = {
            'Open': quotes['open'],
            'High': quotes['high'],
            'Low': quotes['low'],
            'Close': quotes['close'],
            'Volume': quotes['volume']
        }
        hist = pd.DataFrame(hist_data, index=pd.to_datetime(timestamps, unit='s'))
        hist = hist.dropna()  # Remove any null rows
        
        if hist.empty:
            return None
        
        # Get latest data
        latest = hist.iloc[-1]
        prev_close = hist.iloc[-2]['Close'] if len(hist) > 1 else latest['Close']
        
        return {
            "symbol": symbol.upper(),
            "price": float(latest['Close']),
            "open": float(latest['Open']),
            "high": float(latest['High']),
            "low": float(latest['Low']),
            "volume": int(latest['Volume']) if not pd.isna(latest['Volume']) else 0,
            "date": str(latest.name.date()),
            "change_percent": float((latest['Close'] - prev_close) / prev_close * 100),
            "history": hist
        }
    
    def get_multiple_stocks(self, symbols: List[str]) -> Dict[str, Dict]:
        """Fetch data for multiple symbols."""
        results = {}
        for symbol in symbols:
            data = self.get_stock_data(symbol)
            if data:
                results[symbol] = data
        return results


class IndicatorsTool:
    """Calculates technical indicators from price history."""
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> Optional[float]:
        """
        Calculate Relative Strength Index (0-100).
        
        RSI > 70: Overbought (consider selling)
        RSI < 30: Oversold (consider buying)
        """
        if len(prices) < period + 1:
            return None
        
        deltas = prices.diff()
        seed = deltas[:period + 1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        
        rs = up / down if down != 0 else 0
        rsi = 100 - (100 / (1 + rs))
        return float(rsi)
    
    @staticmethod
    def calculate_volatility(prices: pd.Series, period: int = 20) -> Optional[float]:
        """
        Calculate volatility as standard deviation of returns (%).
        
        High volatility: Increased hedging risk; consider options.
        """
        if len(prices) < period:
            return None
        
        returns = prices.pct_change().tail(period)
        volatility_pct = returns.std() * 100
        return float(volatility_pct)
    
    @staticmethod
    def calculate_momentum(prices: pd.Series, period: int = 20) -> Optional[float]:
        """
        Calculate momentum as % change over period.
        
        Positive momentum: Uptrend. Negative: Downtrend.
        """
        if len(prices) < period:
            return None
        
        current = prices.iloc[-1]
        past = prices.iloc[-period]
        momentum = (current - past) / past * 100
        return float(momentum)
    
    @staticmethod
    def calculate_moving_averages(prices: pd.Series) -> tuple[Optional[float], Optional[float]]:
        """Calculate 50-day and 200-day moving averages."""
        ma_50 = prices.tail(50).mean() if len(prices) >= 50 else None
        ma_200 = prices.tail(200).mean() if len(prices) >= 200 else None
        return (float(ma_50) if ma_50 else None, float(ma_200) if ma_200 else None)
    
    @staticmethod
    def get_signal_strength(rsi: Optional[float], momentum: Optional[float], volatility: Optional[float]) -> str:
        """
        Determine overall signal strength based on indicators.
        
        Returns: "strong_buy", "buy", "neutral", "sell", "strong_sell"
        """
        if rsi is None or momentum is None:
            return "neutral"
        
        score = 0
        
        # RSI signals
        if rsi < 30:
            score += 2  # Strong oversold
        elif rsi < 40:
            score += 1  # Weak oversold
        elif rsi > 70:
            score -= 2  # Strong overbought
        elif rsi > 60:
            score -= 1  # Weak overbought
        
        # Momentum signals
        if momentum > 5:
            score += 1
        elif momentum > 0:
            score += 0.5
        elif momentum < -5:
            score -= 1
        elif momentum < 0:
            score -= 0.5
        
        # Volatility modifier (high volatility = caution)
        if volatility and volatility > 30:
            score *= 0.8
        
        if score >= 2:
            return "strong_buy"
        elif score >= 0.5:
            return "buy"
        elif score <= -2:
            return "strong_sell"
        elif score <= -0.5:
            return "sell"
        else:
            return "neutral"
    
    def analyze_stock(self, stock_data: Dict) -> Dict:
        """
        Full technical analysis for a stock.
        
        Returns dict with RSI, volatility, momentum, MAs, and signal.
        """
        if 'history' not in stock_data or stock_data['history'].empty:
            return {}
        
        prices = stock_data['history']['Close']
        
        rsi = self.calculate_rsi(prices)
        volatility = self.calculate_volatility(prices)
        momentum = self.calculate_momentum(prices)
        ma_50, ma_200 = self.calculate_moving_averages(prices)
        
        signal = self.get_signal_strength(rsi, momentum, volatility)
        
        return {
            "symbol": stock_data['symbol'],
            "rsi": rsi,
            "volatility": volatility,
            "momentum": momentum,
            "ma_50": ma_50,
            "ma_200": ma_200,
            "signal_strength": signal,
        }


class PortfolioTool:
    """Analyzes portfolio allocation and exposure."""
    
    @staticmethod
    def calculate_portfolio_value(holdings: Dict[str, float], prices: Dict[str, float]) -> float:
        """Calculate total portfolio value given holdings and prices."""
        total = 0.0
        for symbol, shares in holdings.items():
            if symbol in prices:
                total += shares * prices[symbol]
        return total
    
    @staticmethod
    def calculate_allocation(holdings: Dict[str, float], prices: Dict[str, float]) -> Dict[str, float]:
        """Calculate % allocation of each position."""
        total_value = PortfolioTool.calculate_portfolio_value(holdings, prices)
        if total_value == 0:
            return {}
        
        allocation = {}
        for symbol, shares in holdings.items():
            if symbol in prices:
                position_value = shares * prices[symbol]
                allocation[symbol] = (position_value / total_value) * 100
        
        return allocation
    
    @staticmethod
    def suggest_rebalance(
        current_allocation: Dict[str, float],
        target_allocation: Dict[str, float],
        threshold: float = 5.0
    ) -> List[str]:
        """
        Suggest rebalancing if allocations drift beyond threshold.
        
        Args:
            current_allocation: Current % allocation
            target_allocation: Target % allocation
            threshold: Drift threshold (%)
        
        Returns:
            List of rebalancing suggestions
        """
        suggestions = []
        
        for symbol in set(current_allocation.keys()) | set(target_allocation.keys()):
            current = current_allocation.get(symbol, 0)
            target = target_allocation.get(symbol, 0)
            drift = abs(current - target)
            
            if drift > threshold:
                if current > target:
                    suggestions.append(f"Reduce {symbol} by {drift:.1f}% (drift from target)")
                else:
                    suggestions.append(f"Increase {symbol} by {drift:.1f}% (drift from target)")
        
        return suggestions

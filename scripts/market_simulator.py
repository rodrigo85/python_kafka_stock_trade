#!/usr/bin/env python3
"""Synthetic Market Simulator for the Real-Time Stock Order Matching Engine.

Simulates realistic exchange order flow:
- Emits resting limit orders (bids and asks) forming a realistic order book
- Generates aggressive crossing market orders that trigger executions and partial fills
- Supports multiple tickers (AAPL, MSFT, GOOGL, TSLA) and configurable rates

Usage:
    python scripts/market_simulator.py --count 20 --rate 2.0
    python scripts/market_simulator.py --continuous --symbol AAPL --rate 1.0
"""

import argparse
import os
import random
import sys
import time
from typing import Dict

# Ensure project root is in pythonpath
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from kafka.producer import create_order, send_order

SAMPLE_USERS = ["trader_alpha", "hedge_fund_xyz", "retail_bob", "market_maker_1", "quant_fund", "algo_bot_42"]
TICKER_BASE_PRICES: Dict[str, float] = {
    "AAPL": 185.0,
    "MSFT": 420.0,
    "GOOGL": 175.0,
    "TSLA": 250.0,
}


def simulate_order(symbol: str, base_price: float) -> Dict:
    """Generate a realistic limit order with random price near market and typical quantities."""
    user = random.choice(SAMPLE_USERS)
    order_type = random.choice(["buy", "sell"])
    quantity = random.choice([50, 100, 150, 200, 300, 500])

    # 80% passive resting orders (spread), 20% aggressive crossing orders (triggers match)
    is_crossing = random.random() < 0.25

    price_offset = round(random.uniform(0.10, 2.50), 2)

    if order_type == "buy":
        price = round(base_price + (price_offset if is_crossing else -price_offset), 2)
    else:
        price = round(base_price + (-price_offset if is_crossing else price_offset), 2)

    return create_order(
        user_id=user,
        order_type=order_type,
        stock_id=symbol,
        price=price,
        quantity=quantity,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic Stock Order Flow Simulator")
    parser.add_argument("--symbol", default="AAPL", help="Stock ticker symbol (default: AAPL)")
    parser.add_argument("--count", type=int, default=15, help="Number of orders to generate (default: 15)")
    parser.add_argument("--rate", type=float, default=2.0, help="Orders per second (default: 2.0)")
    parser.add_argument("--continuous", action="store_true", help="Run continuously until stopped")
    args = parser.parse_args()

    symbol = args.symbol.upper()
    base_price = TICKER_BASE_PRICES.get(symbol, 100.0)
    interval = 1.0 / max(args.rate, 0.05)

    print(f"[MARKET SIMULATOR] Target: {symbol} (Base: ${base_price:.2f}) | Rate: {args.rate}/s")
    print(f"[START] Streaming synthetic orders to Kafka... Press Ctrl+C to stop.\n")

    emitted = 0
    try:
        while args.continuous or emitted < args.count:
            order = simulate_order(symbol, base_price)
            success = send_order(order)
            status_tag = "SENT" if success else "SIMULATED"
            print(
                f"[{status_tag}] {order['order_type'].upper():4s} {order['quantity']:4d} {symbol} "
                f"@ ${order['price']:6.2f} (User: {order['user_id']})"
            )
            emitted += 1
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[STOP] Market simulator stopped by user.")
    finally:
        print(f"[DONE] Total orders generated: {emitted}")


if __name__ == "__main__":
    main()

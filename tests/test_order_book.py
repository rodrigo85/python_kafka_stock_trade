"""Unit tests for the OrderBook matching engine."""

import pytest
import time
from backend.order import Order
from backend.order_book import OrderBook


class TestOrderBookMatchingEngine:
    """Verifies Price-Time Priority, exact matching, partial fills, depth sweeps, and aggregation."""

    @pytest.fixture
    def empty_book(self) -> OrderBook:
        """Provide a clean in-memory OrderBook instance without DB connections."""
        book = OrderBook(db=None)
        book.clear()
        return book

    def test_no_match_when_spread_not_crossed(self, empty_book: OrderBook) -> None:
        """Buy at $140 and Sell at $150 should rest in the book without matching."""
        buy = Order(stock_symbol="AAPL", user_id="u1", order_type="buy", price=140.0, original_quantity=10, quantity=10)
        sell = Order(stock_symbol="AAPL", user_id="u2", order_type="sell", price=150.0, original_quantity=10, quantity=10)

        trades_buy = empty_book.add_order(buy)
        trades_sell = empty_book.add_order(sell)

        assert len(trades_buy) == 0
        assert len(trades_sell) == 0
        assert len(empty_book.buy_orders) == 1
        assert len(empty_book.sell_orders) == 1

    def test_exact_match(self, empty_book: OrderBook) -> None:
        """Resting sell 100 @ 150 vs incoming buy 100 @ 150 -> 1 trade of 100 @ 150, book cleared."""
        sell = Order(stock_symbol="AAPL", user_id="seller", order_type="sell", price=150.0, original_quantity=100, quantity=100)
        empty_book.add_order(sell)

        buy = Order(stock_symbol="AAPL", user_id="buyer", order_type="buy", price=150.0, original_quantity=100, quantity=100)
        trades = empty_book.add_order(buy)

        assert len(trades) == 1
        trade = trades[0]
        assert trade["matched_quantity"] == 100
        assert trade["price"] == 150.0
        assert trade["stock_symbol"] == "AAPL"

        # Both orders should be completely consumed
        assert len(empty_book.buy_orders) == 0
        assert len(empty_book.sell_orders) == 0

    def test_partial_fill_buy_order_remaining(self, empty_book: OrderBook) -> None:
        """Incoming buy 100 @ 150 vs resting sell 40 @ 150 -> trade 40, buy 60 remains in book."""
        sell = Order(stock_symbol="AAPL", user_id="seller", order_type="sell", price=150.0, original_quantity=40, quantity=40)
        empty_book.add_order(sell)

        buy = Order(stock_symbol="AAPL", user_id="buyer", order_type="buy", price=150.0, original_quantity=100, quantity=100)
        trades = empty_book.add_order(buy)

        assert len(trades) == 1
        assert trades[0]["matched_quantity"] == 40
        assert trades[0]["price"] == 150.0

        # Sell book empty, buy book has 1 resting order with quantity 60
        assert len(empty_book.sell_orders) == 0
        assert len(empty_book.buy_orders) == 1
        assert empty_book.buy_orders[0].quantity == 60

    def test_partial_fill_sell_order_remaining(self, empty_book: OrderBook) -> None:
        """Resting buy 50 @ 150 vs incoming sell 120 @ 150 -> trade 50, sell 70 remains in book."""
        buy = Order(stock_symbol="AAPL", user_id="buyer", order_type="buy", price=150.0, original_quantity=50, quantity=50)
        empty_book.add_order(buy)

        sell = Order(stock_symbol="AAPL", user_id="seller", order_type="sell", price=150.0, original_quantity=120, quantity=120)
        trades = empty_book.add_order(sell)

        assert len(trades) == 1
        assert trades[0]["matched_quantity"] == 50
        assert trades[0]["price"] == 150.0

        assert len(empty_book.buy_orders) == 0
        assert len(empty_book.sell_orders) == 1
        assert empty_book.sell_orders[0].quantity == 70

    def test_price_improvement_executes_at_resting_price(self, empty_book: OrderBook) -> None:
        """Resting sell at 150. Buyer enters market willing to pay up to 155 -> executes at resting price 150."""
        sell = Order(stock_symbol="AAPL", user_id="seller", order_type="sell", price=150.0, original_quantity=50, quantity=50)
        empty_book.add_order(sell)

        buy = Order(stock_symbol="AAPL", user_id="buyer", order_type="buy", price=155.0, original_quantity=50, quantity=50)
        trades = empty_book.add_order(buy)

        assert len(trades) == 1
        assert trades[0]["price"] == 150.0  # Executed at resting price

    def test_price_time_priority_fifo(self, empty_book: OrderBook) -> None:
        """Two buyers bid the same price ($150). The earlier arrival must be filled first."""
        t1 = 1000.0
        t2 = 1005.0

        buyer_1 = Order(stock_symbol="AAPL", user_id="first_buyer", order_type="buy", price=150.0, original_quantity=50, quantity=50, timestamp=t1)
        buyer_2 = Order(stock_symbol="AAPL", user_id="second_buyer", order_type="buy", price=150.0, original_quantity=50, quantity=50, timestamp=t2)

        empty_book.add_order(buyer_1)
        empty_book.add_order(buyer_2)

        # Seller arrives with 50 shares
        seller = Order(stock_symbol="AAPL", user_id="seller", order_type="sell", price=150.0, original_quantity=50, quantity=50)
        trades = empty_book.add_order(seller)

        assert len(trades) == 1
        assert trades[0]["buy_order_id"] == buyer_1.order_id  # First buyer filled
        assert len(empty_book.buy_orders) == 1
        assert empty_book.buy_orders[0].user_id == "second_buyer"

    def test_multiple_price_levels_depth_sweep(self, empty_book: OrderBook) -> None:
        """Resting sells: 30 @ 100, 30 @ 101, 30 @ 102. Incoming buy: 75 @ 102 sweeps multiple levels."""
        empty_book.add_order(Order(stock_symbol="AAPL", user_id="s1", order_type="sell", price=100.0, original_quantity=30, quantity=30))
        empty_book.add_order(Order(stock_symbol="AAPL", user_id="s2", order_type="sell", price=101.0, original_quantity=30, quantity=30))
        empty_book.add_order(Order(stock_symbol="AAPL", user_id="s3", order_type="sell", price=102.0, original_quantity=30, quantity=30))

        # Sweep buy
        trades = empty_book.add_order(Order(stock_symbol="AAPL", user_id="b1", order_type="buy", price=102.0, original_quantity=75, quantity=75))

        assert len(trades) == 3
        assert trades[0]["matched_quantity"] == 30
        assert trades[0]["price"] == 100.0

        assert trades[1]["matched_quantity"] == 30
        assert trades[1]["price"] == 101.0

        assert trades[2]["matched_quantity"] == 15
        assert trades[2]["price"] == 102.0

        # Remaining in sell book: 15 @ 102
        assert len(empty_book.sell_orders) == 1
        assert empty_book.sell_orders[0].quantity == 15

    def test_sum_quantity_by_price_and_order_rows(self, empty_book: OrderBook) -> None:
        """Verify Level 2 market depth aggregation and UI table row generation."""
        empty_book.add_order(Order(stock_symbol="AAPL", user_id="b1", order_type="buy", price=149.0, original_quantity=100, quantity=100))
        empty_book.add_order(Order(stock_symbol="AAPL", user_id="b2", order_type="buy", price=149.0, original_quantity=50, quantity=50))
        empty_book.add_order(Order(stock_symbol="AAPL", user_id="s1", order_type="sell", price=151.0, original_quantity=75, quantity=75))

        buy_depth, sell_depth = empty_book.sum_quantity_by_price("AAPL")
        assert buy_depth[149.0] == 150
        assert sell_depth[151.0] == 75

        rows = empty_book.get_order_rows()
        assert len(rows) == 3

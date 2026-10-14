"""Order matching engine implementing price-time priority (FIFO) execution."""

from collections import defaultdict, deque
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
import uuid

from backend.order import Order

logger = logging.getLogger("OrderBook")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class OrderBook:
    """In-memory Level 2 Order Book with Price-Time Priority matching and Cassandra persistence."""

    def __init__(
        self,
        db: Optional[Any] = None,
        default_symbol: str = "AAPL",
        trade_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self.db = db
        self.default_symbol = default_symbol
        self.trade_callback = trade_callback

        # Buy orders: sorted descending by price, then ascending by timestamp (FIFO)
        self.buy_orders: deque[Order] = deque()
        # Sell orders: sorted ascending by price, then ascending by timestamp (FIFO)
        self.sell_orders: deque[Order] = deque()

        if self.db and hasattr(self.db, "session") and self.db.session:
            self.load_active_orders(self.default_symbol)

    def load_active_orders(self, stock_symbol: str) -> None:
        """Load resting active orders from the database into the in-memory queues."""
        if not self.db:
            return

        try:
            buy_orders = self.db.get_active_orders(stock_symbol, "buy")
            sell_orders = self.db.get_active_orders(stock_symbol, "sell")

            # Sort buys: highest price first, then earliest arrival (FIFO)
            self.buy_orders = deque(sorted(buy_orders, key=lambda o: (-o.price, o.timestamp)))
            # Sort sells: lowest price first, then earliest arrival (FIFO)
            self.sell_orders = deque(sorted(sell_orders, key=lambda o: (o.price, o.timestamp)))

            logger.info(
                f"Loaded active orders for {stock_symbol}: {len(self.buy_orders)} buys, {len(self.sell_orders)} sells."
            )
        except Exception as e:
            logger.warning(f"Could not load active orders from database: {e}")

    def add_order(self, order: Order) -> List[Dict[str, Any]]:
        """Add an incoming order to the order book and execute matching."""
        if order.order_type == "buy":
            return self.match_buy_order(order)
        elif order.order_type == "sell":
            return self.match_sell_order(order)
        else:
            raise ValueError(f"Unknown order type '{order.order_type}'")

    def match_buy_order(self, buy_order: Order) -> List[Dict[str, Any]]:
        """Match an incoming buy order against resting sell orders (lowest ask price)."""
        executed_trades: List[Dict[str, Any]] = []

        while buy_order.quantity > 0 and self.sell_orders:
            resting_sell = self.sell_orders[0]

            # Price check: buyer must be willing to pay at least the sell price
            if buy_order.price < resting_sell.price:
                break

            # Execution occurs at the resting order's price (standard exchange price-improvement rule)
            trade_price = resting_sell.price
            trade_qty = min(buy_order.quantity, resting_sell.quantity)

            # Record match
            match_event = self._record_trade(buy_order, resting_sell, trade_qty, trade_price)
            executed_trades.append(match_event)

            # Deduct quantities
            buy_order.quantity -= trade_qty
            resting_sell.quantity -= trade_qty

            # If resting sell is completely filled, pop it from the book
            if resting_sell.quantity == 0:
                self.sell_orders.popleft()

        # If buy order has remaining unfilled quantity, insert it into resting buy queue
        if buy_order.quantity > 0:
            self._insert_sorted(self.buy_orders, buy_order, is_buy=True)
            if self.db:
                self.db.insert_order(buy_order)
        elif self.db:
            self.db.move_to_completed_orders(buy_order)

        return executed_trades

    def match_sell_order(self, sell_order: Order) -> List[Dict[str, Any]]:
        """Match an incoming sell order against resting buy orders (highest bid price)."""
        executed_trades: List[Dict[str, Any]] = []

        while sell_order.quantity > 0 and self.buy_orders:
            resting_buy = self.buy_orders[0]

            # Price check: seller's price must be at or below resting bid price
            if sell_order.price > resting_buy.price:
                break

            # Execution occurs at the resting order's price
            trade_price = resting_buy.price
            trade_qty = min(sell_order.quantity, resting_buy.quantity)

            # Record match
            match_event = self._record_trade(resting_buy, sell_order, trade_qty, trade_price)
            executed_trades.append(match_event)

            # Deduct quantities
            sell_order.quantity -= trade_qty
            resting_buy.quantity -= trade_qty

            # If resting buy is completely filled, pop it from the book
            if resting_buy.quantity == 0:
                self.buy_orders.popleft()

        # If sell order has remaining unfilled quantity, insert it into resting sell queue
        if sell_order.quantity > 0:
            self._insert_sorted(self.sell_orders, sell_order, is_buy=False)
            if self.db:
                self.db.insert_order(sell_order)
        elif self.db:
            self.db.move_to_completed_orders(sell_order)

        return executed_trades

    def _record_trade(
        self, buy_order: Order, sell_order: Order, trade_qty: int, trade_price: float
    ) -> Dict[str, Any]:
        """Record trade match to persistence, invoke callbacks, and emit event."""
        match_id = str(uuid.uuid4())
        trade_event = {
            "match_id": match_id,
            "buy_order_id": buy_order.order_id,
            "sell_order_id": sell_order.order_id,
            "stock_symbol": buy_order.stock_symbol,
            "price": trade_price,
            "matched_quantity": trade_qty,
            "timestamp": buy_order.timestamp,
        }

        logger.info(
            f"TRADE MATCH [{buy_order.stock_symbol}]: {trade_qty} shares @ ${trade_price:.2f} "
            f"(Buyer: {buy_order.user_id}, Seller: {sell_order.user_id})"
        )

        if self.db:
            try:
                self.db.move_to_history(buy_order, sell_order, trade_qty, trade_price)
            except Exception as e:
                logger.error(f"Failed to persist trade {match_id} to database: {e}")

        if self.trade_callback:
            try:
                self.trade_callback(trade_event)
            except Exception as e:
                logger.error(f"Error executing trade callback: {e}")

        return trade_event

    def _insert_sorted(self, queue: deque[Order], order: Order, is_buy: bool) -> None:
        """Insert order maintaining Price-Time Priority (FIFO for equal prices)."""
        idx = 0
        while idx < len(queue):
            current = queue[idx]
            if is_buy:
                # Buys: Higher price has priority. On equal price, earlier timestamp has priority.
                if order.price > current.price or (
                    order.price == current.price and order.timestamp < current.timestamp
                ):
                    break
            else:
                # Sells: Lower price has priority. On equal price, earlier timestamp has priority.
                if order.price < current.price or (
                    order.price == current.price and order.timestamp < current.timestamp
                ):
                    break
            idx += 1

        queue.insert(idx, order)

    def get_order_rows(self) -> List[Dict[str, Any]]:
        """Return formatted order book queue rows for UI table rendering."""
        order_rows: List[Dict[str, Any]] = []

        # Sell asks (ascending price)
        for sell in self.sell_orders:
            order_rows.append({"buy_qty": "", "price": sell.price, "sell_qty": sell.quantity})

        # Buy bids (descending price)
        for buy in self.buy_orders:
            order_rows.append({"buy_qty": buy.quantity, "price": buy.price, "sell_qty": ""})

        return order_rows

    def sum_quantity_by_price(self, stock_symbol: str) -> Tuple[Dict[float, int], Dict[float, int]]:
        """Return aggregated buy and sell depth for market depth charts."""
        if self.db and hasattr(self.db, "session") and self.db.session:
            return self.db.sum_quantity_by_price(stock_symbol)

        # Fallback to in-memory order book aggregation
        buy_data: Dict[float, int] = defaultdict(int)
        sell_data: Dict[float, int] = defaultdict(int)

        for buy in self.buy_orders:
            if buy.stock_symbol == stock_symbol:
                buy_data[buy.price] += buy.quantity

        for sell in self.sell_orders:
            if sell.stock_symbol == stock_symbol:
                sell_data[sell.price] += sell.quantity

        return buy_data, sell_data

    def clear(self) -> None:
        """Reset internal in-memory order queues."""
        self.buy_orders.clear()
        self.sell_orders.clear()


# Default singleton instance (lazily configured, safe for imports)
_default_db = None
try:
    from backend.cassandra_db import CassandraDB
    _default_db = CassandraDB(auto_connect=False)
except Exception:
    pass

order_book = OrderBook(_default_db)
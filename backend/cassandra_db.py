"""Cassandra database access layer for active orders, trade execution history, and completed orders."""

from collections import defaultdict
from datetime import datetime
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid

try:
    from cassandra.cluster import Cluster, Session
    from cassandra.util import ms_timestamp_from_datetime
    HAS_CASSANDRA = True
except ImportError:
    HAS_CASSANDRA = False

from backend.order import Order

logger = logging.getLogger("CassandraDB")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class CassandraDB:
    """Manages persistence of active orders, trade matches, and historical orders in Apache Cassandra."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        keyspace: Optional[str] = None,
        auto_connect: bool = True,
    ) -> None:
        self.host = host or os.getenv("CASSANDRA_HOST", "localhost")
        self.port = port or int(os.getenv("CASSANDRA_PORT", 9042))
        self.keyspace = keyspace or os.getenv("CASSANDRA_KEYSPACE", "stock_orders")
        self.cluster: Optional[Any] = None
        self.session: Optional[Any] = None

        if auto_connect:
            self.connect()

    def connect(self, retries: int = 5, delay: float = 3.0) -> bool:
        """Establish connection to Cassandra cluster with retry logic."""
        if not HAS_CASSANDRA:
            logger.warning("cassandra-driver not installed. CassandraDB operating in offline/mock mode.")
            return False

        for attempt in range(1, retries + 1):
            try:
                logger.info(f"Connecting to Cassandra at {self.host}:{self.port} (attempt {attempt}/{retries})...")
                self.cluster = Cluster([self.host], port=self.port, connect_timeout=10)
                self.session = self.cluster.connect()
                self.create_keyspace()
                self.create_tables()
                logger.info(f"Successfully connected to Cassandra keyspace '{self.keyspace}'.")
                return True
            except Exception as e:
                logger.warning(f"Connection attempt {attempt} failed: {e}")
                if attempt < retries:
                    time.sleep(delay)

        logger.error(f"Could not connect to Cassandra after {retries} attempts.")
        return False

    def create_keyspace(self) -> None:
        """Create the keyspace if it does not already exist."""
        if not self.session:
            return
        query = f"""
            CREATE KEYSPACE IF NOT EXISTS {self.keyspace}
            WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': '1'}};
        """
        self.session.execute(query)
        self.session.set_keyspace(self.keyspace)

    def create_tables(self) -> None:
        """Create orders, order_history, and completed_orders tables."""
        if not self.session:
            return

        self.session.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                stock_symbol TEXT,
                order_type TEXT,
                status TEXT,
                order_id UUID,
                user_id TEXT,
                price DOUBLE,
                original_quantity INT,
                quantity INT,
                timestamp TIMESTAMP,
                PRIMARY KEY ((stock_symbol, order_type, status), order_id)
            );
        """)

        self.session.execute("""
            CREATE TABLE IF NOT EXISTS order_history (
                match_id UUID PRIMARY KEY,
                buy_order_id UUID,
                sell_order_id UUID,
                stock_symbol TEXT,
                price DOUBLE,
                matched_quantity INT,
                match_timestamp TIMESTAMP
            );
        """)

        self.session.execute("""
            CREATE TABLE IF NOT EXISTS completed_orders (
                order_id UUID PRIMARY KEY,
                stock_symbol TEXT,
                order_type TEXT,
                user_id TEXT,
                price DOUBLE,
                original_quantity INT,
                quantity INT,
                completed_timestamp TIMESTAMP
            );
        """)

    def get_current_timestamp(self) -> int:
        """Return the current timestamp in milliseconds."""
        if HAS_CASSANDRA:
            return ms_timestamp_from_datetime(datetime.now())
        return int(time.time() * 1000)

    def get_active_orders(self, stock_symbol: str, order_type: str) -> List[Order]:
        """Fetch active buy or sell orders from Cassandra."""
        if not self.session:
            return []

        orders: List[Order] = []
        try:
            query = """
                SELECT * FROM orders
                WHERE stock_symbol = %s AND order_type = %s AND status = 'active';
            """
            results = self.session.execute(query, (stock_symbol, order_type.lower()))
            for row in results:
                orders.append(Order.from_dict(row))
        except Exception as e:
            logger.error(f"Error fetching active {order_type} orders for {stock_symbol}: {e}")
        return orders

    def insert_order(self, order: Order) -> None:
        """Insert or update an active order in the 'orders' table."""
        if not self.session:
            return

        try:
            order_uuid = uuid.UUID(order.order_id) if isinstance(order.order_id, str) else order.order_id
            query = """
                INSERT INTO orders (
                    order_id, stock_symbol, user_id, order_type, price,
                    original_quantity, quantity, status, timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            self.session.execute(query, (
                order_uuid, order.stock_symbol, order.user_id, order.order_type,
                order.price, order.original_quantity, order.quantity, order.status,
                self.get_current_timestamp()
            ))
        except Exception as e:
            logger.error(f"Error inserting order {order.order_id}: {e}")
            raise

    def update_order(self, order_id: str, stock_symbol: str, order_type: str, status: str, quantity: int) -> None:
        """Update the remaining quantity of an active order."""
        if not self.session:
            return

        try:
            order_uuid = uuid.UUID(order_id) if isinstance(order_id, str) else order_id
            query = """
                UPDATE orders SET quantity = %s
                WHERE stock_symbol = %s AND order_type = %s AND status = %s AND order_id = %s;
            """
            self.session.execute(query, (quantity, stock_symbol, order_type.lower(), status, order_uuid))
        except Exception as e:
            logger.error(f"Error updating order {order_id}: {e}")
            raise

    def move_to_history(self, buy_order: Order, sell_order: Order, matched_quantity: int, matched_price: float) -> uuid.UUID:
        """Record matched execution in 'order_history' and update remaining order quantities."""
        match_id = uuid.uuid4()
        if not self.session:
            return match_id

        try:
            timestamp_in_ms = self.get_current_timestamp()
            buy_uuid = uuid.UUID(buy_order.order_id) if isinstance(buy_order.order_id, str) else buy_order.order_id
            sell_uuid = uuid.UUID(sell_order.order_id) if isinstance(sell_order.order_id, str) else sell_order.order_id

            query = """
                INSERT INTO order_history (
                    match_id, buy_order_id, sell_order_id, stock_symbol,
                    price, matched_quantity, match_timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            self.session.execute(query, (
                match_id, buy_uuid, sell_uuid,
                buy_order.stock_symbol, matched_price, matched_quantity, timestamp_in_ms
            ))

            # Handle Buy order state transition
            if buy_order.quantity - matched_quantity <= 0:
                self.move_to_completed_orders(buy_order)
            else:
                self.update_order(
                    buy_order.order_id, buy_order.stock_symbol, 'buy', 'active',
                    buy_order.quantity - matched_quantity
                )

            # Handle Sell order state transition
            if sell_order.quantity - matched_quantity <= 0:
                self.move_to_completed_orders(sell_order)
            else:
                self.update_order(
                    sell_order.order_id, sell_order.stock_symbol, 'sell', 'active',
                    sell_order.quantity - matched_quantity
                )

            return match_id
        except Exception as e:
            logger.error(f"Error recording match to history: {e}")
            raise

    def move_to_completed_orders(self, order: Order) -> None:
        """Move a fully filled order to 'completed_orders' and delete it from 'orders'."""
        if not self.session:
            return

        try:
            order_uuid = uuid.UUID(order.order_id) if isinstance(order.order_id, str) else order.order_id

            insert_query = """
                INSERT INTO completed_orders (
                    order_id, stock_symbol, order_type, user_id, price,
                    original_quantity, quantity, completed_timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            self.session.execute(insert_query, (
                order_uuid, order.stock_symbol, order.order_type, order.user_id,
                order.price, order.original_quantity, 0, datetime.now()
            ))

            delete_query = """
                DELETE FROM orders
                WHERE stock_symbol = %s AND order_type = %s AND status = 'active' AND order_id = %s
            """
            self.session.execute(delete_query, (order.stock_symbol, order.order_type.lower(), order_uuid))
        except Exception as e:
            logger.error(f"Error moving order {order.order_id} to completed_orders: {e}")
            raise

    def sum_quantity_by_price(self, stock_symbol: str) -> Tuple[Dict[float, int], Dict[float, int]]:
        """Fetch and aggregate the quantities of active buy and sell orders by price for Level 2 depth."""
        buy_data: Dict[float, int] = defaultdict(int)
        sell_data: Dict[float, int] = defaultdict(int)

        if not self.session:
            return buy_data, sell_data

        try:
            buy_query = """
                SELECT price, quantity FROM orders 
                WHERE stock_symbol = %s AND order_type = 'buy' AND status = 'active';
            """
            for row in self.session.execute(buy_query, (stock_symbol,)):
                buy_data[row.price] += row.quantity

            sell_query = """
                SELECT price, quantity FROM orders 
                WHERE stock_symbol = %s AND order_type = 'sell' AND status = 'active';
            """
            for row in self.session.execute(sell_query, (stock_symbol,)):
                sell_data[row.price] += row.quantity

        except Exception as e:
            logger.error(f"Error aggregating depth data from Cassandra for {stock_symbol}: {e}")

        return buy_data, sell_data

    def close(self) -> None:
        """Close Cassandra connection cleanly."""
        try:
            if self.session:
                self.session.shutdown()
            if self.cluster:
                self.cluster.shutdown()
            logger.info("Cassandra session and cluster shutdown successfully.")
        except Exception as e:
            logger.error(f"Error closing Cassandra connection: {e}")

    def truncate_tables(self) -> None:
        """Clear all active and historical orders (useful for test resets)."""
        if not self.session:
            return
        try:
            self.session.execute("TRUNCATE orders;")
            self.session.execute("TRUNCATE order_history;")
            self.session.execute("TRUNCATE completed_orders;")
            logger.info("Truncated orders, order_history, and completed_orders tables.")
        except Exception as e:
            logger.error(f"Error truncating tables: {e}")

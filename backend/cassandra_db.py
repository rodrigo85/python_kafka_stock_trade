from cassandra.cluster import Cluster
from cassandra.util import ms_timestamp_from_datetime
from backend.order import Order
from collections import defaultdict
import uuid
from datetime import datetime

class CassandraDB:
    def __init__(self):
        """
        Initialize the CassandraDB connection and create the keyspace and tables.
        Connects to a Cassandra cluster running on Docker.
        """
        try:
            self.cluster = Cluster(['127.0.0.1'], port=9042)  # Connect to Cassandra running in Docker
            self.session = self.cluster.connect()
            self.create_keyspace()
            self.create_tables()
        except Exception as e:
            print(f"Error initializing CassandraDB: {e}")

    def create_keyspace(self):
        """Create the 'stock_orders' keyspace in Cassandra if it does not already exist."""
        try:
            self.session.execute("""
                CREATE KEYSPACE IF NOT EXISTS stock_orders
                WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'}
            """)
            self.session.set_keyspace('stock_orders')
        except Exception as e:
            print(f"Error creating keyspace: {e}")

    def create_tables(self):
        """Create the 'orders', 'order_history', and 'completed_orders' tables."""
        try:
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
        except Exception as e:
            print(f"Error creating tables: {e}")

    def get_current_timestamp(self):
        """Get the current timestamp in milliseconds."""
        return ms_timestamp_from_datetime(datetime.now())

    def get_active_orders(self, stock_symbol, order_type):
        """Fetch active buy or sell orders from Cassandra."""
        orders = []
        try:
            query = """
                SELECT * FROM orders
                WHERE stock_symbol = %s AND order_type = %s AND status = 'active';
            """
            results = self.session.execute(query, (stock_symbol, order_type))
            for row in results:
                orders.append(Order.from_dict(row))
        except Exception as e:
            raise Exception(f"Error fetching active {order_type} orders from Cassandra: {e}")
        return orders

    def insert_order(self, order):        
        """Insert a new order into the 'orders' table."""
        if any(attr is None for attr in [
            order.stock_symbol, order.order_type, order.status, order.order_id,
            order.user_id, order.price, order.original_quantity, order.quantity, order.timestamp
        ]):
            raise ValueError("All fields must be populated and cannot be None.")

        try:
            query = """
                INSERT INTO orders (order_id, stock_symbol, user_id, order_type, price, original_quantity, quantity, status, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            self.session.execute(query, (
                uuid.UUID(order.order_id), order.stock_symbol, order.user_id, order.order_type,
                order.price, order.original_quantity, order.quantity, order.status, self.get_current_timestamp()
            ))
        except Exception as e:
            raise Exception(f"Error inserting order: {e}")

    def update_order(self, order_id, stock_symbol, order_type, status, quantity):
        """Update the quantity and status of an order."""
        try:
            query = """
                UPDATE orders SET quantity = %s
                WHERE stock_symbol = %s AND order_type = %s AND status = %s AND order_id = %s
            """
            self.session.execute(query, (
                quantity, stock_symbol, order_type, status, uuid.UUID(order_id)
            ))
        except Exception as e:
            raise Exception(f"Error updating order: {e}")

    def move_to_history(self, buy_order, sell_order, matched_quantity, matched_price):
        """Move matched orders to the 'order_history' table."""
        timestamp_in_ms = self.get_current_timestamp()
        try:
            query = """
                INSERT INTO order_history (match_id, buy_order_id, sell_order_id, stock_symbol, price, matched_quantity, match_timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            self.session.execute(query, (
                uuid.uuid4(), uuid.UUID(buy_order.order_id), uuid.UUID(sell_order.order_id),
                buy_order.stock_symbol, matched_price, matched_quantity, timestamp_in_ms
            ))

            # Update orders in 'orders' table based on remaining quantities
            if buy_order.quantity - matched_quantity == 0:
                self.move_to_completed_orders(buy_order)
            else:
                self.update_order(buy_order.order_id, buy_order.stock_symbol, 'buy', 'active', buy_order.quantity - matched_quantity)

            if sell_order.quantity - matched_quantity == 0:
                self.move_to_completed_orders(sell_order)
            else:
                self.update_order(sell_order.order_id, sell_order.stock_symbol, 'sell', 'active', sell_order.quantity - matched_quantity)

        except Exception as e:
            raise Exception(f"Error moving orders to history: {e}")

    def move_to_completed_orders(self, order):
        """Move a completed order to the 'completed_orders' table."""
        try:
            query = """
                INSERT INTO completed_orders (order_id, stock_symbol, order_type, user_id, price, original_quantity, quantity, completed_timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """            
            self.session.execute(query, (
                uuid.UUID(order.order_id), order.stock_symbol, order.order_type, order.user_id,
                order.price, order.original_quantity, 0, datetime.now()
            ))            
            # Remove the order from the 'orders' table
            delete_query = """
                DELETE FROM orders WHERE stock_symbol = %s AND order_type = %s AND status = 'active' AND order_id = %s
            """            
            self.session.execute(delete_query, (order.stock_symbol, order.order_type, uuid.UUID(order.order_id)))            
        except Exception as e:
            raise Exception(f"Error moving order to completed_orders: {e}")

    def sum_quantity_by_price(self, stock_symbol):
        """
        Fetch and aggregate the quantities of buy and sell orders by price for a given stock symbol.
        
        Args:
            stock_symbol (str): The stock symbol to fetch data for.

        Returns:
            tuple: Two defaultdicts containing aggregated buy and sell quantities by price.
        """
        buy_data = defaultdict(int)
        sell_data = defaultdict(int)
        try:
            # Query for buy orders
            buy_query = """
                SELECT price, quantity FROM orders 
                WHERE stock_symbol = %s AND order_type = 'buy' AND status = 'active';
            """
            buy_results = self.session.execute(buy_query, (stock_symbol,))
            for row in buy_results:
                buy_data[row.price] += row.quantity
            
            # Query for sell orders
            sell_query = """
                SELECT price, quantity FROM orders 
                WHERE stock_symbol = %s AND order_type = 'sell' AND status = 'active';
            """
            sell_results = self.session.execute(sell_query, (stock_symbol,))
            for row in sell_results:
                sell_data[row.price] += row.quantity
        
        except Exception as e:
            raise Exception(f"Error fetching data from Cassandra: {e}")

        return buy_data, sell_data

    def close(self):
        """Close the Cassandra session and cluster connection."""
        try:
            self.session.shutdown()
            self.cluster.shutdown()
        except Exception as e:
            print(f"Error closing Cassandra connection: {e}")

    def truncate_tables(self):
        """Truncate orders and order_history tables to clear all data."""
        try:
            self.session.execute("TRUNCATE orders;")
            self.session.execute("TRUNCATE order_history;")
            print("Truncated orders and order_history tables successfully.")
        except Exception as e:
            print(f"Error truncating tables: {e}")

from collections import defaultdict
import heapq as hq
from backend.order import Order
from backend.cassandra_db import CassandraDB
from collections import deque

class OrderBook:
    def __init__(self, db):
        # Buy orders sorted by descending price
        self.buy_orders = deque()
        # Sell orders sorted by ascending price
        self.sell_orders = deque()
        self.db = db
        self.load_active_orders("AAPL")
        
    def get_active_orders(self, stock_symbol):
        """Fetch active buy and sell orders from the database."""
        # Use the CassandraDB instance to get active orders
        buy_orders = self.db.get_active_orders(stock_symbol, 'buy')
        sell_orders = self.db.get_active_orders(stock_symbol, 'sell')
        return buy_orders, sell_orders

    def load_active_orders(self, stock_symbol):
        """Load active buy and sell orders from the database."""
        # Load active buy orders
        buy_orders = self.db.get_active_orders(stock_symbol, 'buy')
        # Load active sell orders
        sell_orders = self.db.get_active_orders(stock_symbol, 'sell')
        
        # Sort buy orders by price descending, and sell orders by price ascending
        self.buy_orders = deque(sorted(buy_orders, key=lambda x: -x.price))        
        self.sell_orders = deque(sorted(sell_orders, key=lambda x: x.price))


    def add_order(self, order: Order):
        """Add a new order to the order book and try to match it."""
        if order.order_type == 'buy':
            self.match_buy_order(order)
        elif order.order_type == 'sell':
            self.match_sell_order(order)

    def match_sell_order(self, sell_order):
        """Try to match a sell order with the highest priced buy orders.""" 
        print(sell_order)       
        while sell_order.quantity > 0 and self.buy_orders:            
            # Get the highest-priced buy order
            buy_order = self.buy_orders[0]
            print(buy_order)
            # If the buy price is lower than the sell price, stop matching
            if buy_order.price < sell_order.price:
                break

            # Determine the quantity that can be matched            
            
            trade_quantity = min(buy_order.quantity, sell_order.quantity)
            
            # Record the match
            self.db.move_to_history(buy_order, sell_order, trade_quantity, buy_order.price)

            # Update quantities
            buy_order.quantity -= trade_quantity
            sell_order.quantity -= trade_quantity

            # If the buy order is fully matched, remove it from the queue
            if buy_order.quantity == 0:
                self.buy_orders.popleft()

        # If there's any remaining quantity, add the sell order back to the queue
        if sell_order.quantity > 0:            
            self.insert_sorted(self.sell_orders, sell_order, ascending=True)
            self.db.insert_order(sell_order)
        else:            
            # Insert into completed orders if fully matched
            self.db.move_to_completed_orders(sell_order)
        

    def match_buy_order(self, buy_order):
        """Try to match a buy order with the lowest priced sell orders."""
        print(buy_order)   
        while buy_order.quantity > 0 and self.sell_orders:
            # Get the lowest-priced sell order
            sell_order = self.sell_orders[0]
            print(sell_order)       
            # If the sell price is higher than the buy price, stop matching
            if sell_order.price > buy_order.price:
                break

            # Determine the quantity that can be matched
            trade_quantity = min(sell_order.quantity, buy_order.quantity)

            # Record the match
            self.db.move_to_history(buy_order, sell_order, trade_quantity, sell_order.price)

            # Update quantities
            sell_order.quantity -= trade_quantity
            buy_order.quantity -= trade_quantity

            # If the sell order is fully matched, remove it from the queue
            if sell_order.quantity == 0:
                self.sell_orders.popleft()

        # If there's any remaining quantity, add the buy order back to the queue
        if buy_order.quantity > 0:
            print('Remaining quantity after matching, inserting back into queue...')            
            self.insert_sorted(self.buy_orders, buy_order, ascending=False)
            # Update the remaining buy order in the database
            self.db.insert_order(buy_order)
        else:
            print('Buy order fully matched, moving to completed orders...')            
            # Insert into completed orders if fully matched
            self.db.move_to_completed_orders(buy_order)
        print('End of matching process')


    def get_order_rows(self):
        """Get the formatted order rows for both buy and sell orders."""
        order_rows = []
        
        # Process sell orders first (ascending)
        for sell_order in self.sell_orders:
            order_rows.append({
                'buy_qty': '',
                'price': sell_order.price,
                'sell_qty': sell_order.quantity
            })

        # Process buy orders (descending)
        for buy_order in self.buy_orders:
            order_rows.append({
                'buy_qty': buy_order.quantity,
                'price': buy_order.price,
                'sell_qty': ''
            })

        return order_rows
    

    def insert_sorted(self, order_queue, order, ascending=True):
        """Insert an order into the queue while maintaining sorted order."""
        try:
            # Ensure the order and its price are valid
            if order is None or order.price is None:
                raise ValueError("Order or order price cannot be None")

            index = 0
            while index < len(order_queue):
                # Ensure the current order in the queue has a valid price
                if not hasattr(order_queue[index], 'price') or order_queue[index].price is None:
                    raise ValueError(f"Invalid price in the queue at index {index}")

                # Insert based on the sorted order
                if (ascending and order.price < order_queue[index].price) or \
                (not ascending and order.price > order_queue[index].price):
                    break
                index += 1

            # Insert the order at the correct position
            order_queue.insert(index, order)

        except ValueError as ve:
            raise Exception(f"ValueError: {ve}")
        except TypeError as te:
            raise Exception(f"TypeError: {te}")
        except Exception as e:
            raise Exception(f"Unexpected error: {e}")


    def sum_quantity_by_price(self, stock_symbol: str):
        """Get quantity by price for both buy and sell orders from Cassandra."""
        return self.db.sum_quantity_by_price(stock_symbol)

    
db = CassandraDB()
order_book = OrderBook(db)
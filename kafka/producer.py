from confluent_kafka import Producer
from dotenv import load_dotenv
import json
import os
import uuid
import time
from backend.cassandra_db import CassandraDB

db = CassandraDB() 

# Load environment variables
load_dotenv()

# Kafka Producer configuration
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'localhost:29092')

# Initialize Kafka Producer
producer = Producer({'bootstrap.servers': KAFKA_BROKER})

def create_order(user_id, order_type, stock_id, price, quantity):
    """
    Creates a dictionary representing a stock order.

    Args:
        user_id (str): The ID of the user placing the order.
        order_type (str): The type of the order, either "buy" or "sell".
        stock_id (str): The stock symbol (e.g., 'AAPL').
        price (float): The price for the order.
        quantity (int): The number of shares in the order.

    Returns:
        dict: A dictionary representing the stock order, containing:
              order_id (str), user_id (str), stock_id (str), order_type (str),
              price (float), quantity (int), market_order (bool), and timestamp (float).
    """
    
    return {
        'order_id': str(uuid.uuid4()),
        'user_id': user_id,
        'stock_id': stock_id,
        'order_type': order_type,
        'price': price,
        'quantity': quantity,
        'market_order': False,
        'timestamp': time.time()
    }

def send_order(order):
    """Send the order to the appropriate Kafka topic."""
    topic = 'buy_orders' if order['order_type'] == 'buy' else 'sell_orders'
    producer.produce(topic, key=order['stock_id'], value=json.dumps(order))
    producer.flush()
    print(f"Order sent by user {order['user_id']}: {order}")
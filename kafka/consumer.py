from confluent_kafka import Consumer, KafkaError
from backend.order import Order
from backend.order_book import OrderBook
from backend.cassandra_db import CassandraDB
from dotenv import load_dotenv
import json
import os

load_dotenv()

KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'localhost:29092')

# Initialize CassandraDB and OrderBook
db = CassandraDB()
order_book = OrderBook(db)

consumer = Consumer({
    'bootstrap.servers': KAFKA_BROKER,
    'group.id': 'order_group',
    'auto.offset.reset': 'earliest'
})

consumer.subscribe(['buy_orders', 'sell_orders'])

def consume_orders():
    """
    Polls messages from Kafka topics 'buy_orders' and 'sell_orders'.
    Each message is processed, converting it into an Order object and adding it to the order book.
    If an order matches with another, it is processed and the match is recorded.
    """
    while True:
        msg = consumer.poll(1.0)

        if msg is None:
            continue
        
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            else:
                print(f"Error: {msg.error()}")
                break

        try:
            order_data = json.loads(msg.value().decode('utf-8'))
            print(f"Consumed message: {order_data}")

            # Create Order instance
            order = Order(
                order_id=order_data['order_id'],
                price=order_data['price'],
                stock_symbol=order_data['stock_id'],
                original_quantity=order_data['quantity'],
                quantity=order_data['quantity'], 
                order_type=order_data['order_type'],
                user_id=order_data['user_id'],
                status="active"
            )
            #order_book.add_order(order)

            if order.order_type == 'sell':
                order_book.match_sell_order(order)
            else:            
                order_book.match_buy_order(order)

        except json.JSONDecodeError as json_err:
            print(f"JSON decoding error: {json_err}")

        except KafkaError as kafka_err:
            print(f"Kafka consumer error: {kafka_err}")

        except KeyError as key_err:
            print(f"Missing expected field: {key_err}")

        except Exception as e:            
            print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':    
    try:
        consume_orders()
    finally:
        consumer.close()
        db.close()

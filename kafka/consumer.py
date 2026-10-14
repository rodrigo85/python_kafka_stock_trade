"""Kafka consumer service that processes incoming orders and executes the matching engine."""

import json
import logging
import os
import signal
import sys
import time
from typing import Any, Optional
from dotenv import load_dotenv

try:
    from confluent_kafka import Consumer, KafkaError
    HAS_KAFKA = True
except ImportError:
    HAS_KAFKA = False

from backend.cassandra_db import CassandraDB
from backend.order import Order
from backend.order_book import OrderBook
from kafka.producer import send_matched_trade

load_dotenv()

logger = logging.getLogger("OrderConsumer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:29092")
CONSUMER_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", "order_matching_engine_group")

running = True


def signal_handler(sig: int, frame: Any) -> None:
    """Handle graceful shutdown signals."""
    global running
    logger.info("Shutdown signal received. Closing consumer...")
    running = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def init_engine() -> tuple[CassandraDB, OrderBook]:
    """Initialize Cassandra connection and OrderBook instance with trade event callback."""
    db = CassandraDB(auto_connect=True)
    order_book = OrderBook(db=db, trade_callback=send_matched_trade)
    return db, order_book


def consume_orders() -> None:
    """Main consumer event loop polling buy and sell orders from Kafka."""
    if not HAS_KAFKA:
        logger.error("confluent-kafka not installed. Consumer cannot run.")
        return

    db, order_book = init_engine()

    conf = {
        "bootstrap.servers": KAFKA_BROKER,
        "group.id": CONSUMER_GROUP,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    }

    consumer = Consumer(conf)
    topics = ["buy_orders", "sell_orders"]

    logger.info(f"Subscribing to topics: {topics} at broker: {KAFKA_BROKER}")
    consumer.subscribe(topics)

    logger.info("Order Matching Engine is ready and polling for orders...")
    try:
        while running:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                logger.error(f"Kafka error encountered: {msg.error()}")
                continue

            try:
                raw_val = msg.value().decode("utf-8")
                order_data = json.loads(raw_val)
                logger.info(f"Received {msg.topic()} message: {order_data}")

                order = Order.from_dict(order_data)
                executed_trades = order_book.add_order(order)

                if executed_trades:
                    logger.info(f"Executed {len(executed_trades)} trade(s) for order {order.order_id}")

            except json.JSONDecodeError as err:
                logger.error(f"Malformed JSON in Kafka message: {err}")
            except Exception as err:
                logger.error(f"Unexpected error processing order: {err}", exc_info=True)

    finally:
        logger.info("Closing Kafka consumer and database connections...")
        consumer.close()
        db.close()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    consume_orders()

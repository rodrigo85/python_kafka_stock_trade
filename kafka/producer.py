"""Kafka producer utility for publishing stock orders and trade execution events."""

import json
import logging
import os
import time
from typing import Any, Dict, Optional
import uuid
from dotenv import load_dotenv

try:
    from confluent_kafka import Producer
    HAS_KAFKA = True
except ImportError:
    HAS_KAFKA = False

load_dotenv()

logger = logging.getLogger("KafkaProducer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:29092")

_producer_instance: Optional[Any] = None


def get_producer() -> Optional[Any]:
    """Return a singleton Kafka Producer instance with lazy initialization."""
    global _producer_instance
    if _producer_instance is None and HAS_KAFKA:
        try:
            conf = {
                "bootstrap.servers": KAFKA_BROKER,
                "client.id": "stock-order-producer",
                "acks": "all",
                "retries": 3,
            }
            _producer_instance = Producer(conf)
            logger.info(f"Connected Kafka Producer to {KAFKA_BROKER}")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka Producer: {e}")
            _producer_instance = None
    return _producer_instance


def delivery_report(err: Any, msg: Any) -> None:
    """Callback invoked by confluent_kafka upon delivery or failure."""
    if err is not None:
        logger.error(f"Message delivery failed to topic {msg.topic()}: {err}")
    else:
        logger.info(f"Delivered order to {msg.topic()} [part {msg.partition()}] at offset {msg.offset()}")


def create_order(
    user_id: str,
    order_type: str,
    stock_id: str,
    price: float,
    quantity: int,
    order_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a standardized order dictionary."""
    return {
        "order_id": order_id or str(uuid.uuid4()),
        "user_id": user_id,
        "stock_id": stock_id.upper(),
        "order_type": order_type.lower(),
        "price": float(price),
        "quantity": int(quantity),
        "market_order": False,
        "timestamp": time.time(),
    }


def send_order(order: Dict[str, Any]) -> bool:
    """Publish an order to the appropriate Kafka topic ('buy_orders' or 'sell_orders')."""
    topic = "buy_orders" if order["order_type"] == "buy" else "sell_orders"
    producer = get_producer()

    payload = json.dumps(order)
    key = str(order.get("stock_id", "DEFAULT"))

    if producer:
        try:
            producer.produce(topic, key=key, value=payload, on_delivery=delivery_report)
            producer.poll(0)
            producer.flush(timeout=2.0)
            logger.info(f"Order queued -> {topic}: user={order['user_id']} {order['order_type'].upper()} {order['quantity']} {key} @ ${order['price']:.2f}")
            return True
        except Exception as e:
            logger.error(f"Error publishing order to Kafka topic {topic}: {e}")
            return False
    else:
        logger.warning(f"Kafka offline. Order simulated: {order}")
        return False


def send_matched_trade(trade_event: Dict[str, Any]) -> bool:
    """Publish an executed trade match to the 'matched_orders' topic for downstream accounting."""
    producer = get_producer()
    payload = json.dumps(trade_event)
    key = str(trade_event.get("stock_symbol", "DEFAULT"))

    if producer:
        try:
            producer.produce("matched_orders", key=key, value=payload, on_delivery=delivery_report)
            producer.poll(0)
            return True
        except Exception as e:
            logger.error(f"Error publishing matched trade to Kafka: {e}")
            return False
    return False
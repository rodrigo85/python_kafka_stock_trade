"""Unit tests for the Kafka order generator and message formatting."""

import pytest
from kafka.producer import create_order


class TestProducerHelpers:
    """Verifies order factory and schema compliance."""

    def test_create_order_schema(self) -> None:
        order = create_order(
            user_id="trader_1",
            order_type="BUY",
            stock_id="aapl",
            price=180.50,
            quantity=100,
        )

        assert order["user_id"] == "trader_1"
        assert order["order_type"] == "buy"
        assert order["stock_id"] == "AAPL"
        assert order["price"] == 180.50
        assert order["quantity"] == 100
        assert order["market_order"] is False
        assert "order_id" in order
        assert "timestamp" in order

"""Unit tests for the Order domain model."""

import pytest
import time
from backend.order import Order


class TestOrderModel:
    """Validations for Order creation and serialization."""

    def test_valid_buy_order(self) -> None:
        order = Order(
            stock_symbol="AAPL",
            user_id="user_123",
            order_type="buy",
            price=150.50,
            original_quantity=100,
            quantity=100,
        )
        assert order.stock_symbol == "AAPL"
        assert order.user_id == "user_123"
        assert order.order_type == "buy"
        assert order.price == 150.50
        assert order.quantity == 100
        assert order.status == "active"
        assert order.order_id is not None

    def test_valid_sell_order(self) -> None:
        order = Order(
            stock_symbol="TSLA",
            user_id="user_456",
            order_type="SELL",
            price=240.00,
            original_quantity=50,
            quantity=50,
        )
        assert order.order_type == "sell"

    def test_invalid_order_type_raises_error(self) -> None:
        with pytest.raises(ValueError, match="Invalid order_type"):
            Order(
                stock_symbol="AAPL",
                user_id="user_1",
                order_type="hold",
                price=100.0,
                original_quantity=10,
                quantity=10,
            )

    def test_zero_or_negative_price_raises_error(self) -> None:
        with pytest.raises(ValueError, match="Invalid price"):
            Order(
                stock_symbol="AAPL",
                user_id="user_1",
                order_type="buy",
                price=0.0,
                original_quantity=10,
                quantity=10,
            )

        with pytest.raises(ValueError, match="Invalid price"):
            Order(
                stock_symbol="AAPL",
                user_id="user_1",
                order_type="buy",
                price=-50.0,
                original_quantity=10,
                quantity=10,
            )

    def test_negative_quantity_raises_error(self) -> None:
        with pytest.raises(ValueError, match="Invalid quantity"):
            Order(
                stock_symbol="AAPL",
                user_id="user_1",
                order_type="buy",
                price=100.0,
                original_quantity=10,
                quantity=-5,
            )

    def test_serialization_to_and_from_dict(self) -> None:
        order_dict = {
            "order_id": "test-uuid-001",
            "user_id": "trader_bob",
            "stock_symbol": "GOOGL",
            "order_type": "buy",
            "price": 175.25,
            "original_quantity": 200,
            "quantity": 150,
            "status": "partially_filled",
            "timestamp": 1700000000.0,
        }

        order = Order.from_dict(order_dict)
        assert order.order_id == "test-uuid-001"
        assert order.user_id == "trader_bob"
        assert order.stock_symbol == "GOOGL"
        assert order.price == 175.25
        assert order.quantity == 150
        assert order.original_quantity == 200
        assert order.status == "partially_filled"

        serialized = order.to_dict()
        assert serialized["order_id"] == "test-uuid-001"
        assert serialized["price"] == 175.25

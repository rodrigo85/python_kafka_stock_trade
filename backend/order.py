"""Order domain model representing individual buy and sell orders in the matching engine."""

from dataclasses import dataclass, field
from datetime import datetime
import time
from typing import Any, Dict, Optional
import uuid


@dataclass(order=True)
class Order:
    """Represents a financial stock limit order with strict validation."""

    stock_symbol: str
    user_id: str
    order_type: str  # 'buy' or 'sell'
    price: float
    original_quantity: int
    quantity: int
    status: str = "active"  # 'active', 'partially_filled', 'completed', 'cancelled'
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        """Validate order attributes upon creation."""
        self.order_type = self.order_type.lower()
        if self.order_type not in ("buy", "sell"):
            raise ValueError(f"Invalid order_type '{self.order_type}'. Must be 'buy' or 'sell'.")
        if self.price <= 0:
            raise ValueError(f"Invalid price {self.price}. Order price must be greater than zero.")
        if self.quantity < 0:
            raise ValueError(f"Invalid quantity {self.quantity}. Order quantity cannot be negative.")
        if self.original_quantity < self.quantity:
            self.original_quantity = self.quantity
        if not self.order_id:
            self.order_id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """Convert Order instance to dictionary for Kafka or JSON serialization."""
        return {
            "order_id": self.order_id,
            "user_id": self.user_id,
            "stock_symbol": self.stock_symbol,
            "order_type": self.order_type,
            "price": self.price,
            "original_quantity": self.original_quantity,
            "quantity": self.quantity,
            "status": self.status,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "Order":
        """Factory method constructing an Order from a dictionary or database row object."""
        # Support both dict and Cassandra Row object attributes
        def get_val(key: str, alt_key: Optional[str] = None, default: Any = None) -> Any:
            if isinstance(data, dict):
                val = data.get(key)
                if val is None and alt_key:
                    val = data.get(alt_key)
                return val if val is not None else default
            # Attribute access for namedtuples or Cassandra Row objects
            if hasattr(data, key):
                return getattr(data, key)
            if alt_key and hasattr(data, alt_key):
                return getattr(data, alt_key)
            return default

        raw_timestamp = get_val("timestamp", default=time.time())
        if isinstance(raw_timestamp, datetime):
            timestamp = raw_timestamp.timestamp()
        else:
            timestamp = float(raw_timestamp)

        order_id = str(get_val("order_id", default=uuid.uuid4()))
        stock_symbol = str(get_val("stock_symbol", "stock_id", "AAPL"))
        user_id = str(get_val("user_id", default="anonymous"))
        order_type = str(get_val("order_type", default="buy")).lower()
        price = float(get_val("price", default=0.0))
        quantity = int(get_val("quantity", default=0))
        original_qty = int(get_val("original_quantity", default=quantity))
        status = str(get_val("status", default="active"))

        return cls(
            stock_symbol=stock_symbol,
            user_id=user_id,
            order_type=order_type,
            price=price,
            original_quantity=original_qty,
            quantity=quantity,
            status=status,
            order_id=order_id,
            timestamp=timestamp,
        )

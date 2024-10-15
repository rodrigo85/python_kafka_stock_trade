from dataclasses import dataclass, field
import uuid
import time
from datetime import datetime

@dataclass(order=True)
class Order:
    stock_symbol: str
    user_id: str
    order_type: str
    price: float
    original_quantity: int
    quantity: int
    status: str
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)

    @classmethod
    def from_dict(cls, data):        
        # If the timestamp is a datetime object, convert it to a float timestamp
        timestamp = data.timestamp.timestamp() if isinstance(data.timestamp, datetime) else data.timestamp
        return cls(
            stock_symbol=data.stock_symbol,
            user_id=data.user_id,
            order_type=data.order_type,
            price=data.price,
            original_quantity=data.quantity,
            quantity=data.quantity,
            status=data.status,
            order_id=str(data.order_id),
            timestamp=timestamp
        )

# 📈 Real-Time Stock Order Matching Engine

This project implements a real-time stock order matching system using Python, Kafka, and Cassandra. The engine processes buy and sell orders, efficiently matching them based on price and quantity. It handles real-time order streams via Kafka, and stores active, completed, and historical data in Cassandra for further analysis.

The project simulates a fully operational order book for stock trading with features to track and log trade matches, ensuring accurate records of completed and historical trades.

#### 🛠️ Tools & Technologies

- ![Python](https://img.shields.io/badge/-Python-3776AB?logo=python&logoColor=white) **Python**: Used for the main logic to match buy and sell stock orders.
- ![Apache Kafka](https://img.shields.io/badge/-Kafka-231F20?logo=apachekafka&logoColor=white) **Kafka**: Handles the real-time flow of stock orders, streaming live buy and sell requests to the system for immediate processing.
- ![Cassandra](https://img.shields.io/badge/-Cassandra-1287B1?logo=apachecassandra&logoColor=white) **Cassandra**: Stores all the active, matched, and completed orders, so the data is organized and ready for later use.


### ➡️ System Flow

This project handles real-time stock orders from the frontend to the backend using the following components:

1. **Frontend**:
    - User submits a buy or sell order through the UI. The frontend logic is located in [`frontend/`](./frontend/), which sends the orders to the backend via Kafka.

2. **Kafka Producer**:
    - The order is sent to a Kafka topic by the producer logic in [`kafka/producer.py`](./kafka/producer.py).
    - The `produce_message` function is responsible for sending the message to the Kafka topic: [`produce_message`](./kafka/producer.py#L10).

3. **Kafka Consumer**:
    - The Kafka consumer listens to the topic and processes matched orders, consuming messages from Kafka. The consumer logic is located in [`kafka/consumer.py`](./kafka/consumer.py).
    - The function that handles this is [`consume_message`](./kafka/consumer.py#L12), which reads messages from Kafka topics.
    - 
4. **Backend (Order Matching Engine)**:
    - The order matching logic is implemented in the [`OrderBook` class](./backend/order_book.py#L9) in [`backend/order_book.py`](./backend/order_book.py).
    - Key functions that handle the order processing include:
        - [`add_order`](./backend/order_book.py#L21): Adds new buy or sell orders to the order book and triggers the matching process.
        - [`match_buy_order`](./backend/order_book.py#L43): Matches incoming buy orders with the lowest priced sell orders.
        - [`match_sell_order`](./backend/order_book.py#L68): Matches incoming sell orders with the highest priced buy orders.
    - The `OrderBook` class fetches active orders from the Cassandra database via the [`CassandraDB` class](./backend/cassandra_db.py#L10).

5. **Cassandra**:
    - Active orders, matched orders, and completed orders are stored in Cassandra. This is managed by the [`CassandraDB` class](./backend/cassandra_db.py#L10) in [`backend/cassandra_db.py`](./backend/cassandra_db.py).
    - Key functions include:
        - [`move_to_history`](./backend/cassandra_db.py#L98): Logs matched orders into the `order_history` table.
        - [`move_to_completed_orders`](./backend/cassandra_db.py#L115): Moves fully processed orders into the `completed_orders` table.


### 🎥 Watch a recorded test of the project in action [here](https://youtu.be/inrQesrC7e4?si=kgktBdoYRYxzMHZv).

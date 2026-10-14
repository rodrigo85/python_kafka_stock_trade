-- =============================================================================
-- Cassandra Schema Initialization for Stock Order Matching Engine
-- =============================================================================

-- 1. Create Keyspace
CREATE KEYSPACE IF NOT EXISTS stock_orders
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'};

USE stock_orders;

-- 2. Active Orders Book Table
-- Partition key: (stock_symbol, order_type, status) ensures fast partition queries for active orders
CREATE TABLE IF NOT EXISTS orders (
    stock_symbol TEXT,
    order_type TEXT,
    status TEXT,
    order_id UUID,
    user_id TEXT,
    price DOUBLE,
    original_quantity INT,
    quantity INT,
    timestamp TIMESTAMP,
    PRIMARY KEY ((stock_symbol, order_type, status), order_id)
);

-- 3. Matched Trades History Table
CREATE TABLE IF NOT EXISTS order_history (
    match_id UUID PRIMARY KEY,
    buy_order_id UUID,
    sell_order_id UUID,
    stock_symbol TEXT,
    price DOUBLE,
    matched_quantity INT,
    match_timestamp TIMESTAMP
);

-- 4. Completed / Filled Orders Archive Table
CREATE TABLE IF NOT EXISTS completed_orders (
    order_id UUID PRIMARY KEY,
    stock_symbol TEXT,
    order_type TEXT,
    user_id TEXT,
    price DOUBLE,
    original_quantity INT,
    quantity INT,
    completed_timestamp TIMESTAMP
);

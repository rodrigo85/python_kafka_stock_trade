#!/bin/bash

# Wait until Kafka is ready
echo "Waiting for Kafka to be ready..."
while ! nc -z localhost 9092; do   
  sleep 0.1
done

echo "Creating Kafka topics..."

# Create the buy_orders topic
/usr/bin/kafka-topics --create --topic buy_orders --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1

# Create the sell_orders topic
/usr/bin/kafka-topics --create --topic sell_orders --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1

# Create the matched_orders topic
/usr/bin/kafka-topics --create --topic matched_orders --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1

echo "Kafka topics created successfully."

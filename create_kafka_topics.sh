#!/bin/bash
set -e

BOOTSTRAP_SERVER="${KAFKA_BOOTSTRAP_SERVER:-kafka:9092}"

echo "Waiting for Kafka at ${BOOTSTRAP_SERVER}..."
until kafka-topics --bootstrap-server "${BOOTSTRAP_SERVER}" --list > /dev/null 2>&1; do
  echo "Kafka is not ready yet. Retrying in 2 seconds..."
  sleep 2
done

echo "Kafka is ready. Creating topics..."

kafka-topics --create --if-not-exists --topic buy_orders --bootstrap-server "${BOOTSTRAP_SERVER}" --partitions 3 --replication-factor 1
kafka-topics --create --if-not-exists --topic sell_orders --bootstrap-server "${BOOTSTRAP_SERVER}" --partitions 3 --replication-factor 1
kafka-topics --create --if-not-exists --topic matched_orders --bootstrap-server "${BOOTSTRAP_SERVER}" --partitions 3 --replication-factor 1

echo "Kafka topics verified successfully:"
kafka-topics --list --bootstrap-server "${BOOTSTRAP_SERVER}"

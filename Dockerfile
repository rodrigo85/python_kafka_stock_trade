# Use an official lightweight Python runtime
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for compiling C extensions (librdkafka, cassandra)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app

# Expose Dash Web UI port
EXPOSE 8050

# Default environment
ENV PYTHONUNBUFFERED=1
ENV KAFKA_BROKER=kafka:9092
ENV CASSANDRA_HOST=cassandra
ENV CASSANDRA_PORT=9042

# Default entrypoint runs the Dash Web UI
CMD ["python", "frontend/app.py"]
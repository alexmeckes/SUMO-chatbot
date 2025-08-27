# Use Python 3.11 to avoid dependency issues
FROM python:3.11-slim

# Cache bust to force fresh build (change this value to force rebuild)
ARG CACHEBUST=13

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better caching
COPY requirements.txt .

# Upgrade pip and install dependencies with no cache
RUN pip install --upgrade pip && \
    pip cache purge && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set up ChromaDB if needed
RUN python setup_chromadb.py || true

# Set environment variable for port
ENV PORT=8080

# Expose port
EXPOSE 8080

# Run the application
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 2 app_multiturn:app"]
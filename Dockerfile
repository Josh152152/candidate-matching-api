# Use official slim Python base
FROM python:3.11-slim

# Set work directory inside container
WORKDIR /app

# Install system-level build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    make \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and setuptools for better build support
RUN pip install --upgrade pip setuptools wheel

# Copy dependencies first for cache efficiency
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY . .

# Ensure spaCy model is downloaded at build time
RUN python -m spacy download en_core_web_sm

# Expose the port expected by Render
EXPOSE 10000

# Start the app with Gunicorn and bind to dynamic $PORT
CMD exec gunicorn app:app --bind 0.0.0.0:$PORT --workers 1

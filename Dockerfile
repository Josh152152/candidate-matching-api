FROM python:3.11-slim

WORKDIR /app

# ✅ Install system dependencies, including make for numpy build
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# ✅ Rebuild numpy from source to fix binary mismatch
RUN pip install --no-binary :all: numpy

# Install the rest of the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the expected port
EXPOSE 10000

# Start the Flask app using Gunicorn
CMD exec gunicorn app:app --bind 0.0.0.0:$PORT --workers 1

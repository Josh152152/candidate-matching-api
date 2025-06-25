FROM python:3.11-slim

WORKDIR /app

# ✅ Install build tools required by numpy, cmake, etc.
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# 🔧 Rebuild numpy from source to fix ABI mismatch
RUN pip install --no-binary :all: numpy

# Install all other Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port expected by Render
EXPOSE 10000

# Launch app via gunicorn
CMD exec gunicorn app:app --bind 0.0.0.0:$PORT --workers 1

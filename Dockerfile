FROM python:3.11-slim

WORKDIR /app

# Install required system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and clean cache
RUN pip install --upgrade pip

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port your app runs on
EXPOSE 10000

# Use Gunicorn to run Flask
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$PORT", "--workers", "1"]

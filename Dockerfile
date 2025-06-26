FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Optional: If you need a shell script to run before startup, ensure it's present and executable
# COPY start.sh .
# RUN chmod +x start.sh

# Expose the app port (Render sets PORT automatically)
EXPOSE 10000

# Start with Gunicorn using Flask (adjust app:app if different)
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$PORT", "--workers", "1"]

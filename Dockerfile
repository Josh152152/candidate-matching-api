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

# Install compatible versions to avoid numpy/thinc binary mismatch
RUN pip install numpy==1.24.4
RUN pip install --no-cache-dir cython

# Copy and install all other dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

# Expose port
EXPOSE 10000

# Start with Gunicorn (PORT will be injected by Render)
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$PORT", "--workers", "1"]

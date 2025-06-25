FROM python:3.11-slim

WORKDIR /app

# Install system-level build tools (for packages that may need compilation)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    cmake \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements file first to leverage Docker cache
COPY requirements.txt .

# ✅ Upgrade pip, use prebuilt wheels
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose the expected port
EXPOSE 10000

# ✅ Run Flask app with gunicorn (Render uses $PORT)
CMD exec gunicorn app:app --bind 0.0.0.0:$PORT --workers 1

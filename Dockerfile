FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Reinstall numpy to fix dtype binary incompatibility with thinc/spaCy
RUN pip install --force-reinstall numpy

# Make start script executable
RUN chmod +x start.sh

# Expose the port (Render will set $PORT)
EXPOSE 10000

# Start the app using your custom start script
CMD ["./start.sh"]

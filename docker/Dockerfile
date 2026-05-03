FROM python:3.11.4-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY tests/ ./tests/

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"]
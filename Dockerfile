# Dockerfile for Voice AI System
#
# Notes:
#   - Frontend standalone output is NOT configured (next.config.ts has no output: 'standalone')
#   - Run frontend separately: cd frontend && npm run dev
#   - Use Edge TTS in Docker (no GPU passthrough)
#   - For CosyVoice, run locally with GPU
#
# Usage:
#   docker build -t voice-ai .
#   docker run -p 8000:8000 --env-file .env voice-ai

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
# python-dotenv is needed by run_server_auto_port.py but not listed in requirements.txt
RUN pip install --no-cache-dir python-dotenv && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY run_server_auto_port.py .
COPY .env* ./

# Default to Edge TTS in Docker
ENV TTS_PROVIDER=edge_tts
ENV SERVER_HOST=0.0.0.0
ENV SERVER_PORT=8000

EXPOSE 8000

CMD ["python", "run_server_auto_port.py"]

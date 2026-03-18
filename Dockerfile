FROM python:3.11-slim

WORKDIR /app

# System dependencies
# - tesseract-ocr: for pytesseract OCR on scanned PDFs
# - libglib2.0-0, libsm6, libxext6: required by some PDF/image libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cached unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories used at runtime
RUN mkdir -p /data/sessions /data/documents /data/reports/agents

# Expose both service ports (actual binding is done by docker-compose command)
EXPOSE 8000 8501

# No default CMD — overridden per-service in docker-compose.yml

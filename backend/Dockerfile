# backend/Dockerfile - build context: ./backend
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PATH="/home/appuser/.local/bin:${PATH}"
ENV DEBIAN_FRONTEND=noninteractive

# Install system deps + netcat (Debian-based slim) + curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ libpq-dev netcat-openbsd curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy wait-for script (expected to be in build context ./backend)
COPY wait-for.sh /wait-for.sh
RUN chmod +x /wait-for.sh

# Copy requirements and install (layer caching)
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --disable-pip-version-check -r /tmp/requirements.txt

# Copy application source into /app
COPY . .

# Create necessary directories (ownership set below)
RUN mkdir -p /app/data/lancedb /app/logs

# Create non-root user, chown files (do this after copying to avoid extra layers)
RUN useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app /wait-for.sh

USER appuser

EXPOSE 8000

# Backend HEALTHCHECK (exec form - runs the Python script)
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD ["python", "/app/backend/healthcheck.py"]


# Use a single worker for memory-limited hosts; ensure module path matches your code.
# Replace "main:app" with "backend.main:app" if that is your actual import path.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

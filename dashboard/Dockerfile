# dashboard/Dockerfile - build context: ./dashboard
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# System deps: curl for healthcheck, netcat for wait-for fallback, small libs Streamlit expects
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    netcat-openbsd \
    libglib2.0-0 \
    libnss3 \
    libx11-6 \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Copy wait-for helper (ensure this file exists in ./dashboard)
COPY wait-for.sh /wait-for.sh
RUN chmod +x /wait-for.sh

# Copy and install Python deps (layer-cached)
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --disable-pip-version-check -r /tmp/requirements.txt

# Copy application
COPY . .

# Create data dir for LanceDB and logs; ensure permissions for non-root user
RUN mkdir -p /app/data/lancedb /app/.streamlit /app/logs \
    && useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app /wait-for.sh

USER appuser

EXPOSE 8501

# Dashboard HEALTHCHECK (shell form via sh -c; falls back to root)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD ["sh", "-c", "curl -fsS http://127.0.0.1:8501/_stcore/health || curl -fsS http://127.0.0.1:8501/ || exit 1"]

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]

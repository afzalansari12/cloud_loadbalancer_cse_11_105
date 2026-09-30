FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing .pyc files & buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV API_HOST="0.0.0.0"
ENV API_PORT="8000"

# Install python dependencies directly without apt-get overhead
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose ports:
# 8501: Streamlit SaaS UI
# 8000: REST API & Prometheus /metrics endpoint
EXPOSE 8501 8000

# Health check using Python's standard library
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/status')" || exit 1

# Start all services (Simulation Engine, REST API, Streamlit Dashboard)
CMD ["python", "run.py", "--all"]

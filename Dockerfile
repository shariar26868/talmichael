FROM python:3.12-slim

WORKDIR /app

# Create non-root user for security
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup --no-create-home appuser

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/    ./app/
COPY main.py ./main.py

# Correct ownership
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Health check — uses the /health endpoint on the correct internal port (8000)
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=8).raise_for_status()"

# Start the app (use app.main:app — avoids any root-level import issues in containers)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
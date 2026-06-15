# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install deps into a prefix so we can copy just the packages
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Stage 2: final runtime image ──────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Create non-root user for security
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup --no-create-home appuser

# Copy installed Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin                /usr/local/bin

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
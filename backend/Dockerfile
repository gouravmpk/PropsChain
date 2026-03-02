# ── Stage 1: builder ──────────────────────────────────────────────────────────
# Use a full Python image to install dependencies (some packages compile C extensions).
# We'll copy only the installed packages to the final image — keeps final image small.
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system libs needed by PyMuPDF (fitz) and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libmupdf-dev libffi-dev libssl-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
# Slim final image — no compiler, no build tools.
FROM python:3.12-slim

# Same system libs needed at RUNTIME by PyMuPDF/Pillow (not the compiler ones)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Non-root user for security — never run as root in containers
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# uvicorn: bind to all interfaces (0.0.0.0) so the ALB can reach the container
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

# Multi-stage build for optimized production image
FROM python:3.11-slim as builder

# Install system dependencies for compilation
RUN apt-get update && apt-get install -y \
    gcc \
    libc6-dev \
    make \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy source files
COPY requirements.txt .
COPY main.c .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Compile the C shell
RUN gcc -o mysh main.c -Wall -Wextra -O2

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    vim \
    nano \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1001 cbash

WORKDIR /app

# Copy built application
COPY --from=builder /app/mysh .
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application files
COPY server.py .
COPY templates/ templates/
COPY static/ static/
COPY requirements.txt .

# Change ownership to non-root user
RUN chown -R cbash:cbash /app
USER cbash

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "server.py"]

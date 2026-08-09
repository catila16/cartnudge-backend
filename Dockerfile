# Stage 1: Build dependencies
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Run application
FROM python:3.11-slim

WORKDIR /app
# Copy installed dependencies
COPY --from=builder /root/.local /root/.local
# Make sure scripts in .local are usable:
ENV PATH=/root/.local/bin:$PATH

# Copy app code
COPY . .

# Expose port (Railway overrides this via $PORT)
EXPOSE 8000

# Ensure python output is sent straight to terminal (unbuffered)
ENV PYTHONUNBUFFERED=1

# Default command if Procfile isn't explicitly used
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

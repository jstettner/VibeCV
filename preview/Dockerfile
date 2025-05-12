# preview/Dockerfile
# ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

# 1. Only one native library is needed so Pillow can read/write JPEGs
RUN apt-get update && \
    apt-get install -y --no-install-recommends libjpeg-turbo-progs && \
    rm -rf /var/lib/apt/lists/*

# 2. Python dependencies
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir \
        fastapi==0.111.* \
        uvicorn[standard]==0.30.* \
        pillow==10.*

# 3. Copy the FastAPI app (server.py sits next to this Dockerfile)
WORKDIR /app
COPY server.py .

# 4. Launch the MJPEG stream on port 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"]


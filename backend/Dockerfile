FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt
COPY backend/ ./backend/
COPY data/ ./data/
WORKDIR /app/backend
ENV VELDORA_DATA_DIR=/app/data
# Reference data is loaded once with `python -m scripts.ingest` (see README); training artifacts are committed.
# PORT is set by hosts such as Render; docker compose falls back to 8000.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

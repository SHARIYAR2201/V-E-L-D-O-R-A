FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY data/ ./data/
WORKDIR /app/backend
ENV VELDORA_DATA_DIR=/app/data
CMD ["sh", "-c", "python -m scripts.ingest && python -m scripts.train && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

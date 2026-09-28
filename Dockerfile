FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY cost_engine.py prompt_analyzer.py models.json ./
COPY server ./server

# Render sets PORT; default 8000 for local docker run
CMD uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8000}

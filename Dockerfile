FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
COPY backend ./backend
COPY frontend ./frontend
RUN pip install --no-cache-dir .
RUN mkdir -p storage/input storage/output storage/zips
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

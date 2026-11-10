FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY . .
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser
CMD ["uvicorn", "ekg.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Dockerfile
FROM python:3.10

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY main.py /app/

# Минимальные зависимости
RUN pip install --no-cache-dir fastapi uvicorn[standard] httpx

EXPOSE 8000

# Uvicorn слушает на 0.0.0.0, чтобы был доступ из контейнера
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

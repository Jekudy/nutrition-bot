# Dockerfile для Nutrition Bot на Railway
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Обновляем систему и устанавливаем необходимые пакеты
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем пользователя для безопасности
RUN useradd -m -s /bin/bash botuser && chown -R botuser:botuser /app
USER botuser

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# Открываем порт
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Команда запуска webhook версии
CMD ["python", "main_webhook.py"]
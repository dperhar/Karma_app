# Используем облегченную версию Python 3.11
FROM python:3.11-slim

# Установка рабочей директории
WORKDIR /app

# Создание непривилегированного пользователя
RUN useradd -m appuser

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Настройка сертификата Selectel
RUN mkdir -p /usr/local/share/ca-certificates/selectel && \
    curl -k https://s3.ru-1.storage.selcloud.ru -o /usr/local/share/ca-certificates/selectel/storage.crt && \
    update-ca-certificates

# Обновление pip перед установкой зависимостей
RUN pip install --upgrade pip

# Копируем файл зависимостей и устанавливаем Python-пакеты
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код приложения
COPY . .

# Создание директории для логов
RUN mkdir -p /app/logs

# Делаем скрипт запуска исполняемым и меняем владельца
RUN chmod +x start.sh && chown -R appuser /app

# Переход на пользователя appuser
USER appuser

# Установка переменных окружения
ENV PYTHONUNBUFFERED=1
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV AWS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV PYTHONPATH=/app

# Экспонируем порт 8000 для взаимодействия с приложением
EXPOSE 8000

# Запуск приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

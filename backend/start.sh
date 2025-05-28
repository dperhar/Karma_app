#!/bin/bash

set -e
set -o pipefail

# Install the package in development mode
# pip install -e .

# Проверка переменных окружения
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL не установлен"
    exit 1
fi

# Установка PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Извлечение параметров подключения к БД
DB_HOST=$(echo $DATABASE_URL | sed -E 's|.*//[^:]+:[^@]+@([^:]+):([0-9]+)/.*|\1|')
DB_PORT=$(echo $DATABASE_URL | sed -E 's|.*//[^:]+:[^@]+@([^:]+):([0-9]+)/.*|\2|')

echo "Подключение к базе данных на $DB_HOST:$DB_PORT"

# Ожидание доступности БД с таймаутом
max_attempts=30
attempt=1
echo "Ожидаем запуск базы данных..."
until nc -z -v -w30 $DB_HOST $DB_PORT; do
    if [ $attempt -gt $max_attempts ]; then
        echo "База данных недоступна после $max_attempts попыток. Выход."
        exit 1
    fi
    echo "База данных недоступна, попытка $attempt из $max_attempts..."
    attempt=$((attempt + 1))
    sleep 1
done
echo "База данных доступна!"

# Применение миграций
echo "Применение миграций..."
if ! python -m alembic upgrade heads; then
    echo "Ошибка при применении миграций"
    exit 1
fi

# Запуск приложения
echo "Запуск приложения с перезапуском..."
exec python main.py

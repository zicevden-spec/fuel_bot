#!/bin/bash

# Скрипт для запуска бота и поддержания его в рабочем состоянии

set -e

echo "🚀 Запуск Telegram-бота для отметки бензина..."

# Проверяем наличие .env файла
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден! Создайте его по примеру .env.example"
    exit 1
fi

# Проверяем наличие docker-compose
if ! command -v docker-compose &> /dev/null && ! command -v docker &> /dev/null; then
    echo "❌ Docker не найден! Установите Docker и docker-compose"
    echo "   Инструкция: https://docs.docker.com/get-docker/"
    exit 1
fi

# Запускаем базы данных через docker-compose
echo "📦 Запуск PostgreSQL и Redis..."
docker-compose up -d postgres redis

# Ждём пока базы данных будут готовы
echo "⏳ Ожидание готовности баз данных..."
sleep 5

# Проверяем готовность PostgreSQL
for i in {1..30}; do
    if pg_isready -h localhost -p 5432 -U fuelbot > /dev/null 2>&1; then
        echo "✅ PostgreSQL готов!"
        break
    fi
    echo "   Ждём PostgreSQL... ($i/30)"
    sleep 1
done

# Проверяем готовность Redis
for i in {1..30}; do
    if redis-cli -h localhost ping > /dev/null 2>&1; then
        echo "✅ Redis готов!"
        break
    fi
    echo "   Ждём Redis... ($i/30)"
    sleep 1
done

# Устанавливаем зависимости Python
echo "📦 Установка зависимостей Python..."
pip install -q -r requirements.txt

# Инициализируем базу данных (создаём таблицы)
echo "🗄 Инициализация базы данных..."
python -c "from app.database.base import init_db; import asyncio; asyncio.run(init_db())"

# Запускаем бота
echo "🤖 Запуск бота..."
echo "   Для остановки нажмите Ctrl+C"
echo "   Бот будет работать в фоновом режиме после настройки systemd"
echo ""

# Запуск бота с перезапуском при ошибках
while true; do
    python -m app
    echo "⚠️ Бот остановился. Перезапуск через 5 секунд..."
    sleep 5
done

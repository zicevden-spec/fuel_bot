# Вариант 1: Если Docker УЖЕ установлен на сервере

# 1. Запуск баз данных
docker-compose up -d postgres redis

# 2. Установка зависимостей
pip install -r requirements.txt

# 3. Инициализация БД
python -c "from app.database.base import init_db; import asyncio; asyncio.run(init_db())"

# 4. Запуск бота (в фоне с логом)
nohup python -m app > bot.log 2>&1 &

# Проверка что бот работает
ps aux | grep "python -m app"

# Просмотр логов
tail -f bot.log


# ============================================
# Вариант 2: Автозапуск через systemd (рекомендуется)

# 1. Копируем сервис файл
sudo cp /workspace/fuel_bot.service /etc/systemd/system/

# 2. Перезагружаем systemd
sudo systemctl daemon-reload

# 3. Включаем автозапуск
sudo systemctl enable fuel_bot

# 4. Запускаем
sudo systemctl start fuel_bot

# 5. Проверяем статус
sudo systemctl status fuel_bot

# 6. Смотрим логи
journalctl -u fuel_bot -f


# ============================================
# Вариант 3: Простой запуск в фоне (без systemd)

cd /workspace
nohup python -m app > /var/log/fuel_bot.log 2>&1 &

# Проверка
ps aux | grep fuel_bot


# ============================================
# Вариант 4: Использование screen/tmux для фона

# Установите screen если нет
# apt-get install screen  # Debian/Ubuntu
# yum install screen      # CentOS/RHEL

# Запуск в screen
screen -S fuel_bot
python -m app
# Нажмите Ctrl+A, затем D чтобы отцепиться от сессии

# Возврат к сессии
screen -r fuel_bot

# ============================================
# Как остановить бота

# Если запущен через systemd:
sudo systemctl stop fuel_bot

# Если запущен в фоне:
pkill -f "python -m app"

# Если в screen:
screen -r fuel_bot
# Затем Ctrl+C

# Telegram-бот для отметки бензина

Бот для отслеживания состояния АЗС: наличие топлива, очереди, цены.

## 📋 Требования

- Python 3.10+
- Docker и docker-compose (для баз данных)
- Telegram Bot Token (получить у @BotFather)

## 🚀 Быстрый старт

### 1. Настройка окружения

Отредактируйте файл `.env`:

```bash
# Ваш токен бота от @BotFather
BOT_TOKEN=your_bot_token_here

# Telegram ID администраторов (список через запятую)
ADMIN_IDS=[123456789, 987654321]

# URL базы данных (оставьте как есть при использовании docker-compose)
DATABASE_URL=postgresql+asyncpg://fuelbot:fuelbot_password@localhost:5432/fuel_bot

# URL Redis (оставьте как есть при использовании docker-compose)
REDIS_URL=redis://localhost:6379/0

# Режим отладки
DEBUG=True
```

### 2. Запуск баз данных

```bash
docker-compose up -d postgres redis
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Инициализация базы данных

```bash
python -c "from app.database.base import init_db; import asyncio; asyncio.run(init_db())"
```

### 5. Запуск бота

```bash
python -m app
```

## 🔁 Автозапуск при загрузке системы

### Вариант A: Использование systemd (рекомендуется для Linux)

1. Скопируйте файл службы:
```bash
sudo cp fuel_bot.service /etc/systemd/system/
```

2. Перезагрузите systemd:
```bash
sudo systemctl daemon-reload
```

3. Включите и запустите сервис:
```bash
sudo systemctl enable fuel_bot
sudo systemctl start fuel_bot
```

4. Проверьте статус:
```bash
sudo systemctl status fuel_bot
```

### Вариант B: Использование скрипта run_bot.sh

```bash
./run_bot.sh
```

Этот скрипт автоматически:
- Запустит базы данных через docker-compose
- Дождётся их готовности
- Установит зависимости
- Запустит бота с автоперезапуском при ошибках

## 📱 Как пользоваться ботом

### Для обычных пользователей:

1. **Заправки по городу** — выбор города → бренд → конкретная АЗС
2. **Лента заправок** — просмотр всех заправок города в режиме "свайпов"
3. **Отчёт о заправке** — отметка наличия топлива, очереди и цены

### Для администраторов:

1. **Добавить город** — создание нового города
2. **Добавить заправку** — добавление АЗС с указанием бренда, адреса и видов топлива
3. **Рассылка** — отправка сообщений всем пользователям бота

## 🛠 Структура проекта

```
/workspace
├── app/
│   ├── __main__.py          # Точка входа
│   ├── config.py            # Настройки
│   ├── database/
│   │   ├── base.py          # Подключение к БД
│   │   └── models.py        # SQLAlchemy модели
│   ├── handlers/
│   │   ├── user.py          # Обработчики пользователя
│   │   ├── user_stations.py # Выбор заправок
│   │   ├── user_report.py   # Создание отчётов
│   │   ├── user_feed.py     # Лента заправок
│   │   ├── admin_city.py    # Управление городами
│   │   ├── admin_station.py # Управление заправками
│   │   └── admin_broadcast.py # Рассылки
│   ├── keyboards/           # Клавиатуры
│   ├── services/            # Бизнес-логика
│   └── states/              # FSM состояния
├── docker-compose.yml       # Контейнеры БД
├── requirements.txt         # Зависимости Python
├── run_bot.sh              # Скрипт запуска
└── fuel_bot.service        # Systemd сервис
```

## 📊 Модели данных

- **User** — пользователи бота
- **City** — города
- **Station** — заправки (АЗС)
- **Report** — отчёты о состоянии заправки
- **Broadcast** — рассылки сообщений
- **BroadcastLog** — логи отправок рассылок

## ⚙️ Особенности

- Отчёты публикуются сразу без модерации (ответственность на пользователе)
- Заправки от администратора активируются сразу
- Асинхронная работа с базой данных (asyncpg)
- Поддержка FSM для диалогов
- Inline-клавиатуры для удобной навигации

## 🔍 Логи

При использовании systemd:
```bash
journalctl -u fuel_bot -f
```

При ручном запуске логи выводятся в консоль.

## 🆘 Troubleshooting

**Бот не отвечает:**
1. Проверьте токен в `.env`
2. Убедитесь, что базы данных запущены: `docker-compose ps`
3. Проверьте логи: `journalctl -u fuel_bot` или консоль

**Ошибка подключения к БД:**
```bash
docker-compose logs postgres
```

**Redis не доступен:**
```bash
docker-compose logs redis
redis-cli -h localhost ping
```

## 📝 Лицензия

MIT

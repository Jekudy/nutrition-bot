# 🍎 Nutrition Bot

Telegram бот для анализа пищевой ценности продуктов по фотографиям с использованием OpenAI Vision API.

## 🚀 Возможности

- 📸 Анализ пищевой ценности по фотографии еды
- 🔍 Определение калорийности, белков, жиров, углеводов
- 📊 Отслеживание ежедневного потребления калорий
- 📅 Ежедневные отчеты и планирование
- 🤖 Интеграция с OpenAI GPT-4 Vision

## 🛠 Технологии

- **Python 3.11+**
- **python-telegram-bot** - Telegram Bot API
- **OpenAI API** - GPT-4 Vision для анализа изображений
- **PostgreSQL** - База данных (SQLite для локальной разработки)
- **Pydantic** - Валидация данных
- **Railway.app** - Хостинг и деплой

## 🏗 Архитектура

```
nutrition-bot/
├── adapters/          # Внешние адаптеры (Telegram, OpenAI, DB)
├── services/          # Бизнес-логика
├── shared/           # Общие модели и утилиты
├── prompts/          # Промпты для OpenAI
└── main_v2.py        # Точка входа
```

## 🔧 Локальная разработка

### Предварительные требования

- Python 3.11+
- Telegram Bot Token (получить у @BotFather)
- OpenAI API Key

### Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/Jekudy/nutrition-bot.git
cd nutrition-bot
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте переменные окружения:
```bash
cp .env.example .env
# Отредактируйте .env файл
```

4. Запустите бота:
```bash
python run_v2.py
```

## 🚀 Деплой на Railway

1. Подключите GitHub репозиторий к Railway
2. Добавьте PostgreSQL сервис
3. Настройте переменные окружения:
   - `TELEGRAM_BOT_TOKEN`
   - `OPENAI_API_KEY`
   - `DATABASE_URL` (автоматически из PostgreSQL)

## 📝 Использование

1. Найдите бота в Telegram: @YourBotName
2. Отправьте команду `/start`
3. Отправьте фотографию еды
4. Получите анализ пищевой ценности
5. Используйте `/daily_report` для просмотра статистики

## 🔒 Безопасность

- Все секретные ключи хранятся в переменных окружения
- База данных защищена SSL соединением
- Логи не содержат чувствительной информации

## 📊 Мониторинг

- Health check endpoint: `/health`
- Логирование всех операций
- Автоматический перезапуск при ошибках

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature ветку
3. Внесите изменения
4. Создайте Pull Request

## 📄 Лицензия

MIT License - см. [LICENSE](LICENSE) файл.

## 📞 Поддержка

Если у вас есть вопросы или проблемы, создайте [Issue](https://github.com/Jekudy/nutrition-bot/issues).
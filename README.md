# TrendRec - Telegram Bot

Бот для контент-мейкеров TikTok. Отслеживает тренды и даёт идеи для видео.

## Быстрый старт

1. Создай бота у @BotFather, получи токен
2. Создай файл .env рядом с этим README:
   `
   BOT_TOKEN=твой_токен_сюда
   `
3. Установи зависимости:
   `ash
   pip install -r requirements.txt
   `
4. Запусти:
   `ash
   python -m bot.main
   `

## Команды

- /start - регистрация и выбор ниш
- /trends - показать текущие тренды
- /idea - идея для видео
- /niches - изменить ниши

## Стек

- Python 3.11+ / aiogram 3.x
- SQLite (без Docker, без сервера)
- Railway (деплой)

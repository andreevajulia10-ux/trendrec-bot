#!/bin/bash
# ============================================================
# Скрипт деплоя TrendRec Bot на VPS (Ubuntu/Debian)
# Запускать на сервере:
#   curl -fsSL https://raw.githubusercontent.com/.../deploy.sh | bash
# или скопировать и запустить вручную:
#   chmod +x deploy.sh && ./deploy.sh
# ============================================================

set -e

echo "============================================"
echo "🚀 Деплой TrendRec Bot"
echo "============================================"

# 1. Обновление системы
echo "📦 Обновление пакетов..."
apt update && apt upgrade -y

# 2. Установка зависимостей
echo "🐍 Установка Python и зависимостей..."
apt install -y python3 python3-pip python3-venv git curl postgresql postgresql-client

# 3. Создание пользователя для бота
if ! id -u trendrec > /dev/null 2>&1; then
    useradd -m -s /bin/bash trendrec
    echo "👤 Создан пользователь trendrec"
fi

# 4. Клонирование репозитория
REPO_DIR="/home/trendrec/tiktok-trends-bot"
if [ ! -d "$REPO_DIR" ]; then
    echo "📥 Клонирование репозитория..."
    # Замените URL на ваш репозиторий
    git clone https://github.com/YOUR_USERNAME/tiktok-trends-bot.git "$REPO_DIR"
else
    echo "📥 Репозиторий уже существует, обновляем..."
    cd "$REPO_DIR" && git pull
fi

cd "$REPO_DIR"

# 5. Настройка виртуального окружения
echo "🐍 Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 6. Создание .env файла
if [ ! -f .env ]; then
    echo "📝 Создание .env (заполните позже!)"
    cat > .env << 'ENVEOF'
# Telegram Bot Token (от @BotFather)
BOT_TOKEN=ВАШ_ТОКЕН_ЗДЕСЬ

# База данных PostgreSQL
DATABASE_URL=postgresql+asyncpg://trendrec:trendrec_pass@localhost:5432/trendrec

# Настройки AI (опционально)
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
YANDEXGPT_API_KEY=
YANDEX_FOLDER_ID=
AI_PROVIDER=

# Прокси для Telegram (не нужен на зарубежном VPS, оставьте пустым)
TELEGRAM_PROXY=

# Время дайджеста
DAILY_DIGEST_TIME=10:00
ENVEOF
    echo "⚠️  Заполните BOT_TOKEN в .env и настройте БД!"
else
    echo "✅ .env уже существует"
fi

# 7. Создание БД и пользователя
echo "🗄️ Настройка PostgreSQL..."
sudo -u postgres psql -c "CREATE USER trendrec WITH PASSWORD 'trendrec_pass';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE trendrec OWNER trendrec;" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE trendrec TO trendrec;" 2>/dev/null || true
echo "✅ База данных настроена"

# 8. Создание systemd сервиса
echo "⚙️ Создание systemd сервиса..."
cat > /etc/systemd/system/trendrec-bot.service << 'SERVICEEOF'
[Unit]
Description=TrendRec Bot - TikTok Trend Analyzer
After=network.target postgresql.service

[Service]
Type=simple
User=trendrec
WorkingDirectory=/home/trendrec/tiktok-trends-bot
Environment=PATH=/home/trendrec/tiktok-trends-bot/venv/bin
ExecStart=/home/trendrec/tiktok-trends-bot/venv/bin/python -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEEOF

systemctl daemon-reload
systemctl enable trendrec-bot.service
echo "✅ systemd сервис создан"

# 9. Запуск бота
echo "🎯 Запуск бота..."
systemctl start trendrec-bot.service
sleep 3
systemctl status trendrec-bot.service --no-pager

echo ""
echo "============================================"
echo "✅ Деплой завершён!"
echo "============================================"
echo ""
echo "📋 Полезные команды:"
echo "  systemctl status trendrec-bot.service  — статус бота"
echo "  journalctl -u trendrec-bot -f         — логи в реальном времени"
echo "  systemctl restart trendrec-bot         — перезапуск"
echo "  nano /home/trendrec/tiktok-trends-bot/.env — редактировать .env"
echo ""
echo "⚠️  НЕ ЗАБУДЬТЕ:"
echo "  1. Заполнить BOT_TOKEN в .env"
echo "  2. Если нужно, настроить DATABASE_URL и AI провайдеров"
echo "  3. Перезапустить бота: systemctl restart trendrec-bot"
echo ""

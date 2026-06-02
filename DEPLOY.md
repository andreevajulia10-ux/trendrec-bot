# 🚀 Деплой TrendRec Bot на VPS

## Быстрый старт

### 1. Подготовка VPS

Вам понадобится VPS за границей (не в РФ). Рекомендую:
- [Hetzner](https://hetzner.cloud) — от €4/мес
- [DigitalOcean](https://digitalocean.com) — от $6/мес
- [VDSina](https://vdsina.ru) — от ₽150/мес

**Минимальные требования:**
- 1 CPU, 1GB RAM, 20GB SSD
- Ubuntu 22.04 / Debian 11
- Доступ по SSH

### 2. Загрузка кода на VPS

**Вариант A: Через Git (рекомендуемый)**

```bash
# На локальной машине создайте репозиторий и запушьте код
cd /путь/к/tiktok-trends-bot
git remote add origin https://github.com/ВАШ_АККАУНТ/tiktok-trends-bot.git
git push -u origin master

# На VPS склонируйте
ssh root@ВАШ_СЕРВЕР
git clone https://github.com/ВАШ_АККАУНТ/tiktok-trends-bot.git /home/trendrec/tiktok-trends-bot
```

**Вариант B: Через SCP (без Git)**

```bash
# На локальной машине
cd business/products/tiktok-trends-bot
tar czf bot.tar.gz --exclude=.git --exclude=venv --exclude=__pycache__ .
scp bot.tar.gz root@ВАШ_СЕРВЕР:/root/
ssh root@ВАШ_СЕРВЕР
mkdir -p /home/trendrec/tiktok-trends-bot
tar xzf /root/bot.tar.gz -C /home/trendrec/tiktok-trends-bot
```

### 3. Настройка на VPS

```bash
# Установка зависимостей
apt update && apt install -y python3 python3-pip python3-venv postgresql

# Создание виртуального окружения
cd /home/trendrec/tiktok-trends-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Настройка БД
sudo -u postgres psql -c "CREATE USER trendrec WITH PASSWORD 'trendrec_pass';"
sudo -u postgres psql -c "CREATE DATABASE trendrec OWNER trendrec;"

# Настройка .env
nano .env
```

### 4. Заполнение .env

```env
BOT_TOKEN=ВАШ_ТОКЕН_ОТ_BOTFATHER

DATABASE_URL=postgresql+asyncpg://trendrec:trendrec_pass@localhost:5432/trendrec

# AI (опционально)
OPENAI_API_KEY=sk-...
AI_PROVIDER=openai
# или
YANDEXGPT_API_KEY=...
YANDEX_FOLDER_ID=...
AI_PROVIDER=yandexgpt

# Прокси не нужен на зарубежном VPS
TELEGRAM_PROXY=

DAILY_DIGEST_TIME=10:00
```

### 5. Запуск

```bash
# Создание systemd сервиса
cat > /etc/systemd/system/trendrec-bot.service << 'EOF'
[Unit]
Description=TrendRec Bot
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/home/trendrec/tiktok-trends-bot
Environment=PATH=/home/trendrec/tiktok-trends-bot/venv/bin
ExecStart=/home/trendrec/tiktok-trends-bot/venv/bin/python -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now trendrec-bot.service

# Проверка логов
journalctl -u trendrec-bot -f
```

### 6. Проверка

```bash
# Статус бота
systemctl status trendrec-bot

# Логи в реальном времени
journalctl -u trendrec-bot -f

# Перезапуск
systemctl restart trendrec-bot
```

## Команды для управления

```bash
systemctl start trendrec-bot      # запуск
systemctl stop trendrec-bot       # остановка
systemctl restart trendrec-bot    # перезапуск
systemctl status trendrec-bot     # статус
journalctl -u trendrec-bot -f     # логи
```

## Обновление кода

```bash
cd /home/trendrec/tiktok-trends-bot
git pull
systemctl restart trendrec-bot
```

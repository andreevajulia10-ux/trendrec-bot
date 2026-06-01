"""Миграция: добавляет колонку video_url в таблицу trends."""

import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'trendrec.db')


def migrate():
    print(f'Подключаюсь к БД: {DB_PATH}')
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Проверяем, есть ли уже колонка
    cols = [c['name'] for c in conn.execute('PRAGMA table_info(trends)')]
    print(f'Колонки в trends: {cols}')
    
    if 'video_url' not in cols:
        print('Добавляю колонку video_url...')
        conn.execute('ALTER TABLE trends ADD COLUMN video_url TEXT')
        conn.commit()
        print('Колонка добавлена!')
    else:
        print('Колонка video_url уже существует')
    
    # Обновляем старые записи: video_url = source_url (если есть)
    updated = conn.execute(
        "UPDATE trends SET video_url = source_url WHERE (video_url IS NULL OR video_url = '') AND source_url IS NOT NULL AND source_url != ''"
    ).rowcount
    conn.commit()
    print(f'Скопировано source_url -> video_url: {updated} записей')
    
    # Для трендов без ссылки — генерируем из хештега
    hashtags = conn.execute("SELECT id, title FROM trends WHERE (video_url IS NULL OR video_url = '')").fetchall()
    for h in hashtags:
        tag = h['title'].lstrip('#')
        url = f'https://www.tiktok.com/tag/{tag}'
        conn.execute("UPDATE trends SET video_url = ? WHERE id = ?", (url, h['id']))
    
    conn.commit()
    print(f'Сгенерировано ссылок из хештегов: {len(hashtags)}')
    
    # Финальная проверка
    no_video = conn.execute("SELECT COUNT(*) FROM trends WHERE video_url IS NULL OR video_url = ''").fetchone()[0]
    total = conn.execute('SELECT COUNT(*) FROM trends').fetchone()[0]
    print(f'\nИтого: {total} трендов, без video_url: {no_video}')
    
    conn.close()
    print('Миграция завершена!')


if __name__ == '__main__':
    migrate()

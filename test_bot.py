"""
Тест: прямой API-запрос к Telegram
"""
import asyncio
import aiohttp

TOKEN = "8700084972:AAG25CnUbt3sRNV3j1HlfbEdKdqw0AHKd2k"

async def main():
    print("Проверка подключения к Telegram API...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.telegram.org/bot{TOKEN}/getMe",
                timeout=30
            ) as resp:
                text = await resp.text()
                print(f"Статус: {resp.status}")
                print(f"Ответ: {text}")
                
                if resp.status == 200:
                    print("✅ Подключение работает!")
                else:
                    print("❌ Ошибка подключения")
    except asyncio.TimeoutError:
        print("❌ Таймаут подключения к Telegram API")
    except aiohttp.ClientConnectorError as e:
        print(f"❌ Ошибка соединения: {e}")
    except Exception as e:
        print(f"❌ Другая ошибка: {type(e).__name__}: {e}")

    print("\nПроверка отправки сообщения...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={
                    "chat_id": 1188904706,
                    "text": "🤖 Привет! Бот перезагружен и снова работает!",
                },
                timeout=30
            ) as resp:
                text = await resp.text()
                print(f"Статус: {resp.status}")
                print(f"Ответ: {text}")
                if resp.status == 200:
                    print("✅ Сообщение отправлено!")
    except Exception as e:
        print(f"❌ Ошибка отправки: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(main())

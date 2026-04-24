import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import CommandStart
from aiogram.types import Message
import asyncpg

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
PROXY_URL = os.getenv("PROXY_URL", "socks5://127.0.0.1:1080")

async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS modules (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            unit TEXT NOT NULL,
            calories FLOAT,
            protein FLOAT,
            fat FLOAT,
            carbs FLOAT
        );
        CREATE TABLE IF NOT EXISTS inventory (
            id SERIAL PRIMARY KEY,
            module_id INTEGER REFERENCES modules(id),
            quantity FLOAT NOT NULL DEFAULT 0,
            location TEXT DEFAULT 'Морозилка 1',
            updated_at TIMESTAMP DEFAULT NOW()
        );
    ''')
    await conn.close()
    print("DB ready")

async def main():
    await init_db()
    session = AiohttpSession(proxy=PROXY_URL)
    bot = Bot(token=BOT_TOKEN, session=session)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start(message: Message):
        await message.answer("Привет! FoodBot готов к работе 🍱")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

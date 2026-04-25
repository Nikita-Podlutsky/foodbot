import asyncio
import os
import json
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import Message
import asyncpg

from database import init_db
from llm import process_user_text_with_llm
from logic import add_raw_product_to_inventory, consume_item,get_inventory

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
PROXY_URL = os.getenv("PROXY_URL", "socks5://127.0.0.1:1080")

router = Router()

@router.message()
async def handle_all_messages(message: Message, db_pool: asyncpg.Pool):
    # Показываем юзеру, что бот думает
    await message.bot.send_chat_action(chat_id=message.chat.id, action='typing')
    
    # 1. Отправляем текст в Ollama
    llm_response = await process_user_text_with_llm(message.text)
    
    func_name = llm_response.get("function_name")
    
    # 2. Если LLM решила, что нужно добавить продукт
    if func_name == "add_raw_product_to_inventory":
        # Парсим аргументы (Ollama может вернуть строку или сразу словарь)
        args = llm_response["arguments"]
        if isinstance(args, str):
            args = json.loads(args)
            
        try:
            # 3. Вызываем бизнес-логику для работы с БД
            result_msg = await add_raw_product_to_inventory(
                pool=db_pool,
                brand=args.get("brand", ""),
                name=args["name"],
                base_unit=args["base_unit"],
                package_type=args["package_type"],
                amount=args["amount"],
                quantity=args["quantity"],
                location=args["location"]
            )
            await message.answer(result_msg)
        except Exception as e:
            await message.answer(f"❌ Ошибка базы данных: {e}")
            
    elif func_name == "consume_item":
        args = llm_response["arguments"]
        if isinstance(args, str):
            args = json.loads(args)
            
        try:
            result_msg = await consume_item(
                pool=db_pool,
                item_name=args["item_name"],
                quantity=args["quantity"],
                user_name=args.get("user_name", "")
            )
            await message.answer(result_msg)
        except Exception as e:
            await message.answer(f"❌ Ошибка списания: {e}")
    
    elif func_name == "get_inventory":
        try:
            inventory_msg = await get_inventory(db_pool)
            await message.answer(inventory_msg)
        except Exception as e:
            await message.answer(f"❌ Ошибка просмотра: {e}")
    else:
        await message.answer(llm_response.get("reply", "Функция не распознана."))

async def main():
    pool = await asyncpg.create_pool(DATABASE_URL)
    await init_db(pool)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    try:
        print("🚀 Бот запущен!")
        await dp.start_polling(bot, db_pool=pool)
    finally:
        await bot.session.close()
        await pool.close()

if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
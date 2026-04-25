import aiohttp
import json
import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434/api/chat")
# Используем модель, которая хорошо понимает JSON и Tools (например, qwen2.5 или llama3.1)
MODEL_NAME = "qwen3.5:4b"

# Описываем для ИИ, какие функции у нас есть
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_raw_product_to_inventory",
            "description": "Добавить купленный в магазине продукт (сырье) в холодильник или морозилку.",
            "parameters": {
                "type": "object",
                "properties": {
                    "brand": {"type": "string", "description": "Бренд (например 'Домик в деревне'). Если нет, передать пустую строку."},
                    "name": {"type": "string", "description": "Название продукта (например 'Молоко 3.2%')"},
                    "base_unit": {"type": "string", "enum": ["ml", "g"], "description": "В чем измеряется тара"},
                    "package_type": {"type": "string", "description": "Тип упаковки (бутылка, пакет, пачка)"},
                    "amount": {"type": "number", "description": "Объем/вес одной упаковки (например 1500 для 1.5л)"},
                    "quantity": {"type": "number", "description": "Количество купленных упаковок (например 2)"},
                    "location": {"type": "string", "description": "Куда положили (Холодильник, Морозилка 1)"}
                },
                "required": ["brand", "name", "base_unit", "package_type", "amount", "quantity", "location"]
            }
        }
    },
{
        "type": "function",
        "function": {
            "name": "consume_item",
            "description": "Списать продукт или блюдо из инвентаря, потому что его съели или использовали для готовки.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string", "description": "Название продукта (например 'Молоко', 'Сувид курица', 'Бульон')"},
                    "quantity": {"type": "number", "description": "Какое количество съели/списали (например 1.5, 3)"},
                    "user_name": {"type": "string", "description": "Имя того, кто съел (Папа, Дочка). Если не указано, передать пустую строку."}
                },
                "required": ["item_name", "quantity"]
            }
        }
    },
{
            "type": "function",
            "function": {
                "name": "get_inventory",
                "description": "Посмотреть всё содержимое инвентаря: холодильник и морозилки с количеством продуктов."
            }
        }
]

async def process_user_text_with_llm(text: str) -> dict:
    """Отправляет текст в Ollama и возвращает вызванную функцию и аргументы."""
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Ты ИИ-ассистент управления складом кухни. Извлекай данные из текста и вызывай функции."},
            {"role": "user", "content": text}
        ],
        "tools": TOOLS,
        "stream": False
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(OLLAMA_URL, json=payload) as resp:
                data = await resp.json()
                msg = data.get("message", {})
                
                # Проверяем, решила ли модель вызвать функцию
                if "tool_calls" in msg and len(msg["tool_calls"]) > 0:
                    tool_call = msg["tool_calls"][0]["function"]
                    return {
                        "function_name": tool_call["name"],
                        "arguments": tool_call["arguments"] # Ollama обычно возвращает словарь или JSON-строку
                    }
                else:
                    return {"function_name": None, "reply": msg.get("content", "Не понял, что нужно сделать.")}
        except Exception as e:
            return {"function_name": None, "reply": f"Ошибка связи с Ollama: {e}"}
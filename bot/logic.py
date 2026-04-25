import asyncpg

async def add_raw_product_to_inventory(
    pool: asyncpg.Pool, brand: str, name: str, base_unit: str, 
    package_type: str, amount: float, quantity: float, location: str
) -> str:
    """Добавляет сырье (и его упаковку) в инвентарь."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Ищем или создаем продукт
            product_id = await conn.fetchval('''
                INSERT INTO products (brand, name, base_unit) 
                VALUES ($1, $2, $3) ON CONFLICT (brand, name) 
                DO UPDATE SET base_unit = EXCLUDED.base_unit RETURNING id;
            ''', brand, name, base_unit)

            # 2. Ищем или создаем упаковку
            pack_id = await conn.fetchval('''
                INSERT INTO product_packaging (product_id, package_type, amount) 
                VALUES ($1, $2, $3) ON CONFLICT (product_id, package_type, amount) 
                DO UPDATE SET amount = EXCLUDED.amount RETURNING id;
            ''', product_id, package_type, amount)

            # 3. Добавляем в инвентарь
            await conn.execute('''
                INSERT INTO inventory (packaging_id, quantity, location) 
                VALUES ($1, $2, $3) 
                ON CONFLICT (packaging_id, module_id, location, expiration_date) 
                DO UPDATE SET quantity = inventory.quantity + $2;
            ''', pack_id, quantity, location)

    return f"✅ Добавлено: {brand} {name} ({amount}{base_unit}) x {quantity} шт. в {location}."



async def consume_item(pool: asyncpg.Pool, item_name: str, quantity: float, user_name: str = "Кто-то") -> str:
    """Умное списание: ищет товар по названию среди сырья и модулей и уменьшает остаток."""
    async with pool.acquire() as conn:
        # Пытаемся найти этот товар в инвентаре (ищем либо по имени сырья, либо по имени модуля)
        record = await conn.fetchrow('''
            SELECT i.id, i.quantity, i.location,
                   COALESCE(p.name, m.name) as name,
                   COALESCE(pp.package_type, m.unit_type) as unit
            FROM inventory i
            LEFT JOIN product_packaging pp ON i.packaging_id = pp.id
            LEFT JOIN products p ON pp.product_id = p.id
            LEFT JOIN modules m ON i.module_id = m.id
            WHERE p.name ILIKE $1 OR m.name ILIKE $1
            ORDER BY i.quantity DESC LIMIT 1;
        ''', f"%{item_name}%") # Ищем частичное совпадение (например "молоко" найдет "Молоко 3.2%")

        if not record:
            return f"❌ Не нашел «{item_name}» в морозилках/холодильнике."

        current_qty = record['quantity']
        new_qty = current_qty - quantity

        if new_qty <= 0:
            # Если съели всё — удаляем строку из инвентаря
            await conn.execute('DELETE FROM inventory WHERE id = $1', record['id'])
            result_text = f"🍽 Списано {current_qty} {record['unit']} «{record['name']}». Запас исчерпан!"
        else:
            # Уменьшаем количество
            await conn.execute('UPDATE inventory SET quantity = $1 WHERE id = $2', new_qty, record['id'])
            result_text = f"🍽 Списано {quantity} {record['unit']} «{record['name']}». Осталось: {new_qty}."

        return result_text


async def get_inventory(pool: asyncpg.Pool) -> str:
    """Возвращает текущее состояние холодильника/морозилок."""
    async with pool.acquire() as conn:
        records = await conn.fetch('''
            SELECT COALESCE(p.name, m.name) as name, 
                   i.quantity, 
                   COALESCE(pp.package_type, m.unit_type) as unit,
                   i.location
            FROM inventory i
            LEFT JOIN product_packaging pp ON i.packaging_id = pp.id
            LEFT JOIN products p ON pp.product_id = p.id
            LEFT JOIN modules m ON i.module_id = m.id
            WHERE i.quantity > 0
        ''')
    
    if not records:
        return "В холодильниках/морозильниках пусто!"
        
    text = "📦 **Текущие запасы:**\n"
    for r in records:
        text += f"- {r['name']}: {r['quantity']} {r['unit']} в {r['location']}\n"
    return text




async def get_daily_macros(pool: asyncpg.Pool, user_id: int) -> dict:
    """Считает, сколько пользователь уже съел сегодня (Автопересчет)."""
    # Этот SQL объединяет калории сырья (пересчитанные из 100г) и калории модулей
    # В рамках MVP возвращаем заглушку, но тут будет мощный SQL JOIN
    return {"kcal": 1200, "protein": 80, "fat": 40, "carbs": 130}
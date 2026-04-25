import asyncpg

async def init_db(pool: asyncpg.Pool):
    async with pool.acquire() as conn:
        
        
        # await conn.execute('''
        #     DROP TABLE IF EXISTS consumption_log CASCADE;
        #     DROP TABLE IF EXISTS inventory CASCADE;
        #     DROP TABLE IF EXISTS module_ingredients CASCADE;
        #     DROP TABLE IF EXISTS modules CASCADE;
        #     DROP TABLE IF EXISTS product_packaging CASCADE;
        #     DROP TABLE IF EXISTS products CASCADE;
        #     DROP TABLE IF EXISTS users CASCADE;
        # ''')
        # print("🧹 Старые таблицы удалены!")
        await conn.execute('''
            -- 1. ПРОФИЛИ ПОЛЬЗОВАТЕЛЕЙ (Семья)
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                tg_id BIGINT UNIQUE,          -- Telegram ID для связи (если у всех свои ТГ)
                name TEXT NOT NULL,           -- 'Папа', 'Дочка'
                target_kcal FLOAT,
                target_protein FLOAT,
                target_fat FLOAT,
                target_carbs FLOAT
            );

            -- 2. СЫРЬЕ
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                brand TEXT,
                name TEXT NOT NULL,
                base_unit TEXT NOT NULL CHECK (base_unit IN ('g', 'ml')),
                tags TEXT[] DEFAULT '{}',
                kcal_per_100 FLOAT, protein_per_100 FLOAT, fat_per_100 FLOAT, carbs_per_100 FLOAT,
                UNIQUE (brand, name)
            );

            -- 3. УПАКОВКИ
            CREATE TABLE IF NOT EXISTS product_packaging (
                id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                package_type TEXT NOT NULL,
                amount FLOAT NOT NULL,
                barcode TEXT UNIQUE,
                UNIQUE (product_id, package_type, amount)
            );

            -- 4. МОДУЛИ (Заготовки)
            CREATE TABLE IF NOT EXISTS modules (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                unit_type TEXT NOT NULL,
                unit_weight_g FLOAT,
                tags TEXT[] DEFAULT '{}',
                kcal_per_unit FLOAT, protein_per_unit FLOAT, fat_per_unit FLOAT, carbs_per_unit FLOAT
            );

            -- 5. ИНВЕНТАРЬ (Остатки)
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY,
                packaging_id INTEGER REFERENCES product_packaging(id) ON DELETE CASCADE,
                module_id INTEGER REFERENCES modules(id) ON DELETE CASCADE,
                quantity FLOAT NOT NULL DEFAULT 0,
                location TEXT DEFAULT 'Холодильник',
                expiration_date DATE,
                CHECK ((packaging_id IS NOT NULL AND module_id IS NULL) OR (packaging_id IS NULL AND module_id IS NOT NULL)),
                UNIQUE NULLS NOT DISTINCT (packaging_id, module_id, location, expiration_date)
            );

            -- 6. ЖУРНАЛ СЪЕДЕННОГО (Для подсчета КБЖУ за день)
            CREATE TABLE IF NOT EXISTS consumption_log (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                inventory_id INTEGER REFERENCES inventory(id),
                quantity FLOAT NOT NULL,
                consumed_at TIMESTAMP DEFAULT NOW()
            );
        ''')
    print("✅ БД: Все таблицы созданы")
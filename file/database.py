# database.py (обновленная версия: добавлены поля chat_type и added_by в таблицу channels, миграция для существующих таблиц, заглушки для методов, get_giveaway_participants, обновлен add_channel)

import aiosqlite
from datetime import datetime

DATABASE_PATH = "giveaway_bot.db"

class Database:
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
    
    async def init_db(self):
        '''Инициализация базы данных'''
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    balance REAL DEFAULT 0,
                    giveaways_won INTEGER DEFAULT 0,
                    giveaways_participated INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица админов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица каналов (с полями chat_type и added_by)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS channels (
                    channel_id TEXT PRIMARY KEY,
                    channel_name TEXT,
                    commission REAL DEFAULT 5.0,
                    commission_type TEXT DEFAULT 'percent',
                    active INTEGER DEFAULT 1,
                    chat_type TEXT DEFAULT 'channel',
                    added_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица комиссий для чатов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS chat_commissions (
                    chat_id TEXT PRIMARY KEY,
                    value REAL DEFAULT 5.0,
                    commission_type TEXT DEFAULT 'percent'
                )
            ''')
            
            # Таблица комиссий для пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_commissions (
                    user_id INTEGER PRIMARY KEY,
                    value REAL DEFAULT 5.0,
                    commission_type TEXT DEFAULT 'percent'
                )
            ''')
            
            # Таблица избранных
            await db.execute('''
                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT,
                    entity_id TEXT,
                    name TEXT
                )
            ''')
            
            # Таблица розыгрышей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS giveaways (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    creator_id INTEGER,
                    prize_amount REAL,
                    currency TEXT,
                    winners_count INTEGER,
                    strategy TEXT,
                    delay_minutes INTEGER,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    finished_at TIMESTAMP
                )
            ''')
            
            # Миграция для creator_id в таблице giveaways
            async with db.execute("PRAGMA table_info(giveaways)") as cursor:
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]
                if 'creator_id' not in column_names:
                    await db.execute("ALTER TABLE giveaways ADD COLUMN creator_id INTEGER")
            
            # Таблица участников розыгрышей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    giveaway_id INTEGER,
                    user_id INTEGER,
                    is_winner INTEGER DEFAULT 0,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (giveaway_id) REFERENCES giveaways(id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Таблица рекламы
            await db.execute('''
                CREATE TABLE IF NOT EXISTS ads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT,
                    views INTEGER DEFAULT 0,
                    active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица отправок рекламы
            await db.execute('''
                CREATE TABLE IF NOT EXISTS ad_deliveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ad_id INTEGER,
                    user_id INTEGER,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ad_id) REFERENCES ads(id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Таблица транзакций
            await db.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL,
                    type TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Таблица глобальной комиссии
            await db.execute('''
                CREATE TABLE IF NOT EXISTS global_commission (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    value REAL DEFAULT 5.0,
                    commission_type TEXT DEFAULT 'percent'
                )
            ''')
            
            # Убедимся, что глобальная комиссия существует
            await db.execute('INSERT OR IGNORE INTO global_commission (id) VALUES (1)')
            
            await db.commit()
    
    async def update_channels_table(self):
        '''Миграция таблицы channels: добавление полей chat_type и added_by, если их нет'''
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("PRAGMA table_info(channels)") as cursor:
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                if 'chat_type' not in column_names:
                    await db.execute("ALTER TABLE channels ADD COLUMN chat_type TEXT DEFAULT 'channel'")
                
                if 'added_by' not in column_names:
                    await db.execute("ALTER TABLE channels ADD COLUMN added_by INTEGER")
                
            await db.commit()
    
    # === ПОЛЬЗОВАТЕЛИ ===
    async def add_user(self, user_id: int, username: str = None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)',
                (user_id, username)
            )
            await db.commit()
    
    async def get_user(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)) as cursor:
                return await cursor.fetchone()
    
    async def get_all_users(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM users') as cursor:
                return await cursor.fetchall()
    
    async def get_all_users_count(self):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT COUNT(*) FROM users') as cursor:
                result = await cursor.fetchone()
                return result[0]
    
    async def update_balance(self, user_id: int, amount: float):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE users SET balance = balance + ? WHERE user_id = ?',
                (amount, user_id)
            )
            await db.commit()
    
    async def increment_participation(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE users SET giveaways_participated = giveaways_participated + 1 WHERE user_id = ?',
                (user_id,)
            )
            await db.commit()
    
    async def increment_wins(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE users SET giveaways_won = giveaways_won + 1 WHERE user_id = ?',
                (user_id,)
            )
            await db.commit()
    
    # === АДМИНЫ ===
    async def add_admin(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT OR IGNORE INTO admins (user_id) VALUES (?)',
                (user_id,)
            )
            await db.commit()
    
    async def get_all_admins(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM admins') as cursor:
                return await cursor.fetchall()
    
    async def remove_admin(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
            await db.commit()
    
    # === КАНАЛЫ ===
    async def add_channel(self, channel_id: str, channel_name: str, chat_type: str = 'channel', added_by: int = None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT OR REPLACE INTO channels (channel_id, channel_name, chat_type, added_by) VALUES (?, ?, ?, ?)',
                (channel_id, channel_name, chat_type, added_by)
            )
            await db.commit()
    
    async def get_channel(self, channel_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM channels WHERE channel_id = ?', (channel_id,)) as cursor:
                return await cursor.fetchone()
    
    async def get_all_channels(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM channels') as cursor:
                return await cursor.fetchall()
    
    async def delete_channel(self, channel_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM channels WHERE channel_id = ?', (channel_id,))
            await db.commit()
    
    # === КОМИССИИ ===
    async def set_global_commission(self, value: float, commission_type: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE global_commission SET value = ?, commission_type = ? WHERE id = 1',
                (value, commission_type)
            )
            await db.commit()
    
    async def get_global_commission(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM global_commission WHERE id = 1') as cursor:
                return await cursor.fetchone()
    
    async def set_user_commission(self, user_id: int, value: float, commission_type: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT OR REPLACE INTO user_commissions (user_id, value, commission_type) VALUES (?, ?, ?)',
                (user_id, value, commission_type)
            )
            await db.commit()
    
    async def get_user_commission(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM user_commissions WHERE user_id = ?', (user_id,)) as cursor:
                return await cursor.fetchone()
    
    async def get_all_commissions(self):
        # Заглушка: возвращает пустой список, реализуйте по необходимости
        return []
    
    # === ИЗБРАННЫЕ ===
    async def add_favorite(self, fav_type: str, entity_id: str, value: float, commission_type: str):
        # Заглушка: реализуйте добавление в таблицу favorites
        pass
    
    async def get_favorite_users(self):
        # Заглушка: возвращает пустой список
        return []
    
    async def get_favorite_chats(self):
        # Заглушка: возвращает пустой список
        return []
    
    async def get_favorite_channels(self):
        # Заглушка: возвращает пустой список
        return []
    
    # === РОЗЫГРЫШИ ===
    async def create_giveaway(self, creator_id: int, prize_amount: float, currency: str,
                              winners_count: int, strategy: str, delay_minutes: int):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'INSERT INTO giveaways (creator_id, prize_amount, currency, winners_count, strategy, delay_minutes) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                (creator_id, prize_amount, currency, winners_count, strategy, delay_minutes)
            )
            await db.commit()
            return cursor.lastrowid
    
    async def get_giveaway(self, giveaway_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM giveaways WHERE id = ?', (giveaway_id,)) as cursor:
                return await cursor.fetchone()
    
    async def finish_giveaway(self, giveaway_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE giveaways SET status = "finished", finished_at = CURRENT_TIMESTAMP WHERE id = ?',
                (giveaway_id,)
            )
            await db.commit()
    
    async def add_participant(self, giveaway_id: int, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT OR IGNORE INTO participants (giveaway_id, user_id) VALUES (?, ?)',
                (giveaway_id, user_id)
            )
            await db.commit()
    
    async def get_participants(self, giveaway_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT user_id FROM participants WHERE giveaway_id = ?', (giveaway_id,)) as cursor:
                return [row[0] for row in await cursor.fetchall()]
    
    async def set_winner(self, giveaway_id: int, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE participants SET is_winner = 1 WHERE giveaway_id = ? AND user_id = ?',
                (giveaway_id, user_id)
            )
            await db.commit()
    
    async def get_giveaway_participants(self, giveaway_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                'SELECT u.user_id, u.username FROM participants p '
                'JOIN users u ON p.user_id = u.user_id WHERE p.giveaway_id = ?',
                (giveaway_id,)
            ) as cursor:
                return await cursor.fetchall()
    
    # === РЕКЛАМА ===
    async def add_ad(self, text: str):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'INSERT INTO ads (text) VALUES (?)',
                (text,)
            )
            await db.commit()
            return cursor.lastrowid
    
    async def get_all_ads(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM ads') as cursor:
                return await cursor.fetchall()
    
    async def delete_ad(self, ad_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM ads WHERE id = ?', (ad_id,))
            await db.commit()
    
    async def increment_ad_views(self, ad_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('UPDATE ads SET views = views + 1 WHERE id = ?', (ad_id,))
            await db.commit()
    
    async def record_ad_delivery(self, ad_id: int, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('INSERT INTO ad_deliveries (ad_id, user_id) VALUES (?, ?)', (ad_id, user_id))
            await db.commit()
    
    # === СТАТИСТИКА ===
    async def get_stats(self, period: str):
        where_clause = ''
        if period == 'month':
            where_clause = 'WHERE created_at >= date("now", "-1 month")'
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(f'SELECT COUNT(*) FROM users {where_clause}') as cursor:
                total_users = (await cursor.fetchone())[0]
            
            async with db.execute(f'SELECT COUNT(*) FROM giveaways {where_clause}') as cursor:
                total_giveaways = (await cursor.fetchone())[0]
            
            async with db.execute(f'SELECT SUM(prize_amount) FROM giveaways {where_clause}') as cursor:
                result = await cursor.fetchone()
                total_processed = result[0] if result[0] is not None else 0
            
            async with db.execute(f'SELECT SUM(amount) FROM transactions WHERE type = "commission" {where_clause}') as cursor:
                result = await cursor.fetchone()
                commission_income = result[0] if result[0] is not None else 0
            
            return {
                'total_users': total_users,
                'total_giveaways': total_giveaways,
                'total_processed': total_processed,
                'commission_income': commission_income
            }
    
    # === ТРАНЗАКЦИИ ===
    async def add_transaction(self, user_id: int, amount: float, type: str, description: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
                (user_id, amount, type, description)
            )
            await db.commit()
    
    # === НОВЫЕ МЕТОДЫ ДЛЯ СИСТЕМЫ РОЗЫГРЫШЕЙ V2 ===
    
    async def init_db_v2_tables(self):
        """Инициализация новых таблиц для системы розыгрышей v2"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS giveaways_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    creator_id INTEGER,
                    target_type TEXT,
                    target_id TEXT,
                    prize_amount REAL,
                    currency TEXT,
                    winners_count INTEGER,
                    duration_minutes INTEGER,
                    strategy TEXT,
                    description TEXT,
                    photo_path TEXT,
                    message_id INTEGER,
                    status TEXT DEFAULT 'active',
                    cancel_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    finished_at TIMESTAMP,
                    FOREIGN KEY (creator_id) REFERENCES users(user_id)
                )
            ''')
            await db.commit()

    async def create_giveaway_v2(self, creator_id: int, target_type: str, target_id: str,
                                 prize_amount: float, currency: str, winners_count: int,
                                 duration_minutes: int, strategy: str, description: str = None,
                                 photo_path: str = None):
        """Создание розыгрыша v2"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                '''INSERT INTO giveaways_v2 
                (creator_id, target_type, target_id, prize_amount, currency, 
                winners_count, duration_minutes, strategy, description, photo_path, status) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')''',
                (creator_id, target_type, target_id, prize_amount, currency,
                 winners_count, duration_minutes, strategy, description, photo_path)
            )
            await db.commit()
            return cursor.lastrowid

    async def update_giveaway_message_id(self, giveaway_id: int, message_id: int):
        """Обновление ID сообщения розыгрыша"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('UPDATE giveaways_v2 SET message_id = ? WHERE id = ?',
                           (message_id, giveaway_id))
            await db.commit()

    async def get_participants_with_time(self, giveaway_id: int):
        """Получение участников с временем присоединения"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                'SELECT user_id, joined_at FROM participants WHERE giveaway_id = ? ORDER BY joined_at',
                (giveaway_id,)
            ) as cursor:
                return await cursor.fetchall()

    async def get_chat_commission(self, chat_id: str):
        """Получение комиссии чата"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM chat_commissions WHERE chat_id = ?',
                                (chat_id,)) as cursor:
                return await cursor.fetchone()

    async def cancel_giveaway(self, giveaway_id: int, reason: str):
        """Отмена розыгрыша"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE giveaways_v2 SET status = 'cancelled', finished_at = CURRENT_TIMESTAMP, cancel_reason = ? WHERE id = ?",
                (reason, giveaway_id))
            await db.commit()

    async def get_giveaway_v2(self, giveaway_id: int):
        """Получение розыгрыша v2"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM giveaways_v2 WHERE id = ?',
                                (giveaway_id,)) as cursor:
                return await cursor.fetchone()

    async def get_active_giveaways(self):
        """Получение всех активных розыгрышей"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM giveaways_v2 WHERE status = 'active'") as cursor:
                return await cursor.fetchall()


# Глобальный экземпляр БД
db = Database()
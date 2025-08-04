"""
PostgreSQL Database Adapter для Railway deployment
"""
import asyncpg
import json
import os
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from shared.logger import get_logger
from shared.models import FoodAnalysisResult, DailyNutritionStats, UserProfile

logger = get_logger(__name__)

class PostgreSQLAdapter:
    """Асинхронный адаптер для PostgreSQL базы данных"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL не найдена в переменных окружения")
        logger.info("Инициализирован PostgreSQL адаптер")
    
    async def init_db(self):
        """Инициализирует структуру базы данных"""
        try:
            conn = await asyncpg.connect(self.database_url)
            
            # Таблица пользователей
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    settings JSONB DEFAULT '{}'::jsonb
                )
            """)
            
            # Таблица приемов пищи
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS food_entries (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    date DATE,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Основные макросы
                    total_calories REAL DEFAULT 0,
                    total_protein REAL DEFAULT 0,
                    total_carbs REAL DEFAULT 0,
                    total_fat REAL DEFAULT 0,
                    total_fiber REAL DEFAULT 0,
                    
                    -- Специфические нутриенты
                    berries_grams REAL DEFAULT 0,
                    red_meat_grams REAL DEFAULT 0,
                    seafood_grams REAL DEFAULT 0,
                    nuts_grams REAL DEFAULT 0,
                    vegetables_grams REAL DEFAULT 0,
                    
                    -- Детали анализа
                    analysis_json JSONB,
                    
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица дневной статистики
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    user_id BIGINT,
                    date DATE,
                    
                    -- Агрегированные значения
                    total_calories REAL DEFAULT 0,
                    total_protein REAL DEFAULT 0,
                    total_carbs REAL DEFAULT 0,
                    total_fat REAL DEFAULT 0,
                    total_fiber REAL DEFAULT 0,
                    
                    berries_grams REAL DEFAULT 0,
                    red_meat_grams REAL DEFAULT 0,
                    seafood_grams REAL DEFAULT 0,
                    nuts_grams REAL DEFAULT 0,
                    vegetables_grams REAL DEFAULT 0,
                    
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    PRIMARY KEY (user_id, date),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Создаем индексы для лучшей производительности
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_food_entries_user_date ON food_entries (user_id, date)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_stats_user_date ON daily_stats (user_id, date)")
            
            await conn.close()
            logger.info("PostgreSQL база данных инициализирована")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации PostgreSQL БД: {e}")
            raise
    
    async def get_or_create_user(self, user_id: int, username: str = None, first_name: str = None) -> Dict[str, Any]:
        """Получает или создает пользователя"""
        try:
            conn = await asyncpg.connect(self.database_url)
            
            # Проверяем существование
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1", 
                user_id
            )
            
            if user:
                user_dict = dict(user)
                logger.info(f"Пользователь {user_id} найден")
                await conn.close()
                return user_dict
            else:
                # Создаем нового пользователя
                await conn.execute(
                    "INSERT INTO users (user_id, username, first_name) VALUES ($1, $2, $3)",
                    user_id, username, first_name
                )
                
                logger.info(f"Создан новый пользователь {user_id}")
                await conn.close()
                
                return {
                    "user_id": user_id,
                    "username": username,
                    "first_name": first_name,
                    "created_at": datetime.now(),
                    "settings": {}
                }
                
        except Exception as e:
            logger.error(f"Ошибка работы с пользователем {user_id}: {e}")
            raise
    
    async def save_food_entry(self, user_id: int, analysis: FoodAnalysisResult) -> bool:
        """Сохраняет анализ еды в базу данных"""
        try:
            today = date.today()
            
            conn = await asyncpg.connect(self.database_url)
            
            # Сохраняем запись о еде
            await conn.execute("""
                INSERT INTO food_entries (
                    user_id, date, 
                    total_calories, total_protein, total_carbs, total_fat, total_fiber,
                    berries_grams, red_meat_grams, seafood_grams, nuts_grams, vegetables_grams,
                    analysis_json
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """, 
                user_id, today,
                analysis.total_calories, analysis.total_protein, 
                analysis.total_carbs, analysis.total_fat, analysis.total_fiber,
                analysis.berries_grams, analysis.red_meat_grams, 
                analysis.seafood_grams, analysis.nuts_grams, analysis.vegetables_grams,
                analysis.model_dump_json()
            )
            
            # Обновляем дневную статистику
            await self._update_daily_stats(conn, user_id, today)
            
            await conn.close()
            logger.info(f"Сохранен анализ еды для пользователя {user_id}: {analysis.total_calories} ккал")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения анализа еды: {e}")
            return False
    
    async def _update_daily_stats(self, conn: asyncpg.Connection, user_id: int, date: date):
        """Обновляет агрегированную статистику за день"""
        try:
            # Вычисляем суммы за день
            stats = await conn.fetchrow("""
                SELECT 
                    COALESCE(SUM(total_calories), 0) as calories,
                    COALESCE(SUM(total_protein), 0) as protein,
                    COALESCE(SUM(total_carbs), 0) as carbs,
                    COALESCE(SUM(total_fat), 0) as fat,
                    COALESCE(SUM(total_fiber), 0) as fiber,
                    COALESCE(SUM(berries_grams), 0) as berries,
                    COALESCE(SUM(red_meat_grams), 0) as red_meat,
                    COALESCE(SUM(seafood_grams), 0) as seafood,
                    COALESCE(SUM(nuts_grams), 0) as nuts,
                    COALESCE(SUM(vegetables_grams), 0) as vegetables
                FROM food_entries 
                WHERE user_id = $1 AND date = $2
            """, user_id, date)
            
            if stats:
                # Upsert в daily_stats
                await conn.execute("""
                    INSERT INTO daily_stats (
                        user_id, date,
                        total_calories, total_protein, total_carbs, total_fat, total_fiber,
                        berries_grams, red_meat_grams, seafood_grams, nuts_grams, vegetables_grams
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ON CONFLICT (user_id, date) DO UPDATE SET
                        total_calories = EXCLUDED.total_calories,
                        total_protein = EXCLUDED.total_protein,
                        total_carbs = EXCLUDED.total_carbs,
                        total_fat = EXCLUDED.total_fat,
                        total_fiber = EXCLUDED.total_fiber,
                        berries_grams = EXCLUDED.berries_grams,
                        red_meat_grams = EXCLUDED.red_meat_grams,
                        seafood_grams = EXCLUDED.seafood_grams,
                        nuts_grams = EXCLUDED.nuts_grams,
                        vegetables_grams = EXCLUDED.vegetables_grams,
                        updated_at = CURRENT_TIMESTAMP
                """, user_id, date, *stats)
                
                logger.info(f"Обновлена дневная статистика для {user_id} на {date}")
                
        except Exception as e:
            logger.error(f"Ошибка обновления дневной статистики: {e}")
    
    async def get_daily_stats(self, user_id: int, date: str = None) -> Optional[DailyNutritionStats]:
        """Получает статистику за день"""
        try:
            if not date:
                date = datetime.now().date()
            elif isinstance(date, str):
                date = datetime.fromisoformat(date).date()
            
            conn = await asyncpg.connect(self.database_url)
            
            row = await conn.fetchrow("""
                SELECT * FROM daily_stats 
                WHERE user_id = $1 AND date = $2
            """, user_id, date)
            
            await conn.close()
            
            if row:
                stats_dict = dict(row)
                return DailyNutritionStats(**stats_dict)
            
            logger.info(f"Статистика за {date} для пользователя {user_id} не найдена")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения дневной статистики: {e}")
            return None
    
    async def get_weekly_stats(self, user_id: int, start_date: str = None) -> Dict[str, float]:
        """Получает статистику за неделю"""
        try:
            if not start_date:
                # Берем последние 7 дней
                today = date.today()
                start_date = date(today.year, today.month, today.day - 6)
            elif isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date).date()
            
            conn = await asyncpg.connect(self.database_url)
            
            row = await conn.fetchrow("""
                SELECT 
                    COALESCE(SUM(total_calories), 0) as weekly_calories,
                    COALESCE(SUM(total_protein), 0) as weekly_protein,
                    COALESCE(SUM(total_fiber), 0) as weekly_fiber,
                    COALESCE(SUM(berries_grams), 0) as weekly_berries,
                    COALESCE(SUM(red_meat_grams), 0) as weekly_red_meat,
                    COALESCE(SUM(seafood_grams), 0) as weekly_seafood,
                    COALESCE(SUM(nuts_grams), 0) as weekly_nuts,
                    COALESCE(SUM(vegetables_grams), 0) as weekly_vegetables
                FROM daily_stats 
                WHERE user_id = $1 AND date >= $2
            """, user_id, start_date)
            
            await conn.close()
            
            if row:
                return dict(row)
            
            return {}
            
        except Exception as e:
            logger.error(f"Ошибка получения недельной статистики: {e}")
            return {}
    
    async def get_food_history(self, user_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """Получает историю приемов пищи"""
        try:
            # Вычисляем дату начала
            start_date = date.today() - timedelta(days=days)
            
            conn = await asyncpg.connect(self.database_url)
            
            rows = await conn.fetch("""
                SELECT * FROM food_entries 
                WHERE user_id = $1 AND date >= $2
                ORDER BY timestamp DESC
            """, user_id, start_date)
            
            await conn.close()
            
            history = [dict(row) for row in rows]
            logger.info(f"Получена история питания для {user_id}: {len(history)} записей")
            return history
            
        except Exception as e:
            logger.error(f"Ошибка получения истории питания: {e}")
            return []
    
    async def update_user_settings(self, user_id: int, settings: Dict[str, Any]) -> bool:
        """
        Обновляет настройки пользователя
        
        Args:
            user_id: ID пользователя
            settings: Словарь с настройками
            
        Returns:
            True при успехе, False при ошибке
        """
        try:
            conn = await asyncpg.connect(self.database_url)
            
            await conn.execute(
                "UPDATE users SET settings = $1 WHERE user_id = $2",
                json.dumps(settings, ensure_ascii=False), user_id
            )
            
            await conn.close()
            logger.info(f"Настройки пользователя {user_id} обновлены")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления настроек пользователя {user_id}: {e}")
            return False
    
    async def get_user_settings(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает настройки пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь с настройками или None
        """
        try:
            conn = await asyncpg.connect(self.database_url)
            
            row = await conn.fetchrow(
                "SELECT settings FROM users WHERE user_id = $1",
                user_id
            )
            
            await conn.close()
            
            if row and row['settings']:
                return dict(row['settings'])
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения настроек пользователя {user_id}: {e}")
            return None
    
    async def close(self):
        """Закрывает соединение с базой данных"""
        logger.info("PostgreSQL адаптер закрыт")
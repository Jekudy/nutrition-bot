"""
Database Adapter: асинхронный SQLite с упрощенной схемой
"""
import aiosqlite
import json
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from shared.logger import get_logger
from shared.models import FoodAnalysisResult, DailyNutritionStats, UserProfile

logger = get_logger(__name__)

class DatabaseAdapter:
    """Асинхронный адаптер для SQLite базы данных"""
    
    def __init__(self, db_path: str = "nutrition_bot.db"):
        self.db_path = db_path
        logger.info(f"Инициализирован адаптер БД: {db_path}")
    
    async def init_db(self):
        """Инициализирует структуру базы данных"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Таблица пользователей
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        settings TEXT DEFAULT '{}'
                    )
                """)
                
                # Таблица приемов пищи (упрощенная - без сессий)
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS food_entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        date TEXT,
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                        
                        -- Основные макросы
                        total_calories REAL DEFAULT 0,
                        total_protein REAL DEFAULT 0,
                        total_carbs REAL DEFAULT 0,
                        total_fat REAL DEFAULT 0,
                        total_fiber REAL DEFAULT 0,
                        
                        -- Специфические нутриенты (для норм)
                        berries_grams REAL DEFAULT 0,
                        red_meat_grams REAL DEFAULT 0,
                        seafood_grams REAL DEFAULT 0,
                        nuts_grams REAL DEFAULT 0,
                        vegetables_grams REAL DEFAULT 0,
                        
                        -- Детали анализа
                        analysis_json TEXT,
                        
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                
                # Таблица дневной статистики (кэш)
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS daily_stats (
                        user_id INTEGER,
                        date TEXT,
                        
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
                        
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        
                        PRIMARY KEY (user_id, date),
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                
                await db.commit()
                logger.info("База данных инициализирована")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise
    
    async def get_or_create_user(self, user_id: int, username: str = None, first_name: str = None) -> Dict[str, Any]:
        """
        Получает или создает пользователя
        
        Args:
            user_id: ID пользователя
            username: Имя пользователя
            first_name: Имя
            
        Returns:
            Данные пользователя
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Проверяем существование
                cursor = await db.execute(
                    "SELECT * FROM users WHERE user_id = ?", 
                    (user_id,)
                )
                user = await cursor.fetchone()
                
                if user:
                    # Пользователь существует
                    columns = [desc[0] for desc in cursor.description]
                    user_dict = dict(zip(columns, user))
                    logger.info(f"Пользователь {user_id} найден")
                    return user_dict
                else:
                    # Создаем нового пользователя
                    await db.execute(
                        "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                        (user_id, username, first_name)
                    )
                    await db.commit()
                    
                    logger.info(f"Создан новый пользователь {user_id}")
                    
                    return {
                        "user_id": user_id,
                        "username": username,
                        "first_name": first_name,
                        "created_at": datetime.now().isoformat(),
                        "settings": "{}"
                    }
                    
        except Exception as e:
            logger.error(f"Ошибка работы с пользователем {user_id}: {e}")
            raise
    
    async def save_food_entry(self, user_id: int, analysis: FoodAnalysisResult) -> bool:
        """
        Сохраняет анализ еды в базу данных
        
        Args:
            user_id: ID пользователя
            analysis: Результат анализа еды
            
        Returns:
            True при успехе, False при ошибке
        """
        try:
            today = date.today().isoformat()
            
            async with aiosqlite.connect(self.db_path) as db:
                # Сохраняем запись о еде
                # Извлекаем данные из анализа (поддерживаем обе структуры)
                food_data = self._extract_food_data(analysis)
                
                await db.execute("""
                    INSERT INTO food_entries (
                        user_id, date, 
                        total_calories, total_protein, total_carbs, total_fat, total_fiber,
                        berries_grams, red_meat_grams, seafood_grams, nuts_grams, vegetables_grams,
                        analysis_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, today,
                    food_data['calories'], food_data['protein'], 
                    food_data['carbs'], food_data['fat'], food_data['fiber'],
                    food_data['berries'], food_data['red_meat'], 
                    food_data['seafood'], food_data['nuts'], food_data['vegetables'],
                    analysis.model_dump_json()
                ))
                
                # Обновляем дневную статистику
                await self._update_daily_stats(db, user_id, today)
                
                await db.commit()
                logger.info(f"Сохранен анализ еды для пользователя {user_id}: {food_data['calories']} ккал")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка сохранения анализа еды: {e}")
            return False
    
    def _extract_food_data(self, analysis) -> dict:
        """
        Извлекает данные из анализа (поддерживает обе структуры)
        
        Args:
            analysis: FoodAnalysisResult или ProfessionalFoodAnalysis
            
        Returns:
            Словарь с унифицированными данными
        """
        if hasattr(analysis, 'totals'):
            # Новая структура ProfessionalFoodAnalysis
            return {
                'calories': float(analysis.totals.kcal),
                'protein': float(analysis.totals.protein_g),
                'carbs': float(analysis.totals.carb_g),
                'fat': float(analysis.totals.fat_g),
                'fiber': float(analysis.totals.fiber_g),
                'berries': 0.0,  # TODO: добавить в новую схему
                'red_meat': 0.0,  # TODO: добавить в новую схему
                'seafood': 0.0,   # TODO: добавить в новую схему
                'nuts': 0.0,      # TODO: добавить в новую схему
                'vegetables': 0.0 # TODO: добавить в новую схему
            }
        else:
            # Старая структура FoodAnalysisResult
            return {
                'calories': float(getattr(analysis, 'total_calories', 0)),
                'protein': float(getattr(analysis, 'total_protein', 0)),
                'carbs': float(getattr(analysis, 'total_carbs', 0)),
                'fat': float(getattr(analysis, 'total_fat', 0)),
                'fiber': float(getattr(analysis, 'total_fiber', 0)),
                'berries': float(getattr(analysis, 'berries_grams', 0)),
                'red_meat': float(getattr(analysis, 'red_meat_grams', 0)),
                'seafood': float(getattr(analysis, 'seafood_grams', 0)),
                'nuts': float(getattr(analysis, 'nuts_grams', 0)),
                'vegetables': float(getattr(analysis, 'vegetables_grams', 0))
            }
    
    async def _update_daily_stats(self, db: aiosqlite.Connection, user_id: int, date: str):
        """Обновляет агрегированную статистику за день"""
        try:
            # Вычисляем суммы за день
            cursor = await db.execute("""
                SELECT 
                    SUM(total_calories) as calories,
                    SUM(total_protein) as protein,
                    SUM(total_carbs) as carbs,
                    SUM(total_fat) as fat,
                    SUM(total_fiber) as fiber,
                    SUM(berries_grams) as berries,
                    SUM(red_meat_grams) as red_meat,
                    SUM(seafood_grams) as seafood,
                    SUM(nuts_grams) as nuts,
                    SUM(vegetables_grams) as vegetables
                FROM food_entries 
                WHERE user_id = ? AND date = ?
            """, (user_id, date))
            
            stats = await cursor.fetchone()
            
            if stats:
                # Upsert в daily_stats
                await db.execute("""
                    INSERT OR REPLACE INTO daily_stats (
                        user_id, date,
                        total_calories, total_protein, total_carbs, total_fat, total_fiber,
                        berries_grams, red_meat_grams, seafood_grams, nuts_grams, vegetables_grams
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, date, *stats))
                
                logger.info(f"Обновлена дневная статистика для {user_id} на {date}")
                
        except Exception as e:
            logger.error(f"Ошибка обновления дневной статистики: {e}")
    
    async def get_daily_stats(self, user_id: int, date: str = None) -> Optional[DailyNutritionStats]:
        """
        Получает статистику за день
        
        Args:
            user_id: ID пользователя
            date: Дата (по умолчанию сегодня)
            
        Returns:
            Статистика за день или None
        """
        try:
            if not date:
                date = datetime.now().date().isoformat()
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT * FROM daily_stats 
                    WHERE user_id = ? AND date = ?
                """, (user_id, date))
                
                row = await cursor.fetchone()
                
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    stats_dict = dict(zip(columns, row))
                    
                    # Преобразуем в Pydantic модель
                    return DailyNutritionStats(**stats_dict)
                
                logger.info(f"Статистика за {date} для пользователя {user_id} не найдена")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка получения дневной статистики: {e}")
            return None
    
    async def get_weekly_stats(self, user_id: int, start_date: str = None) -> Dict[str, float]:
        """
        Получает статистику за неделю
        
        Args:
            user_id: ID пользователя  
            start_date: Начальная дата недели
            
        Returns:
            Агрегированная статистика за неделю
        """
        try:
            if not start_date:
                # Берем последние 7 дней
                today = date.today()
                start_date = (today.replace(day=today.day-6)).isoformat()
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT 
                        SUM(total_calories) as weekly_calories,
                        SUM(total_protein) as weekly_protein,
                        SUM(total_fiber) as weekly_fiber,
                        SUM(berries_grams) as weekly_berries,
                        SUM(red_meat_grams) as weekly_red_meat,
                        SUM(seafood_grams) as weekly_seafood,
                        SUM(nuts_grams) as weekly_nuts,
                        SUM(vegetables_grams) as weekly_vegetables
                    FROM daily_stats 
                    WHERE user_id = ? AND date >= ?
                """, (user_id, start_date))
                
                row = await cursor.fetchone()
                
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    weekly_stats = dict(zip(columns, row))
                    
                    # Заменяем None на 0
                    return {k: (v or 0) for k, v in weekly_stats.items()}
                
                return {}
                
        except Exception as e:
            logger.error(f"Ошибка получения недельной статистики: {e}")
            return {}
    
    async def get_food_history(self, user_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """
        Получает историю приемов пищи
        
        Args:
            user_id: ID пользователя
            days: Количество дней назад
            
        Returns:
            Список записей о еде
        """
        try:
            # Вычисляем дату начала
            start_date = (date.today().replace(day=date.today().day - days)).isoformat()
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT * FROM food_entries 
                    WHERE user_id = ? AND date >= ?
                    ORDER BY timestamp DESC
                """, (user_id, start_date))
                
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                history = []
                for row in rows:
                    entry = dict(zip(columns, row))
                    history.append(entry)
                
                logger.info(f"Получена история питания для {user_id}: {len(history)} записей")
                return history
                
        except Exception as e:
            logger.error(f"Ошибка получения истории питания: {e}")
            return []
    
    async def close(self):
        """Закрывает соединение с базой данных"""
        logger.info("Адаптер БД закрыт")
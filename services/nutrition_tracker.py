"""
Nutrition Tracker Service: записывает анализы в БД без сессий
"""
from typing import Optional, Dict, Any
from datetime import datetime, date
from shared.logger import get_logger
from shared.models import FoodAnalysisResult, DailyNutritionStats
from adapters.database import DatabaseAdapter

logger = get_logger(__name__)

class NutritionTracker:
    """Простое отслеживание питания - записываем всю еду за день"""
    
    def __init__(self, db: DatabaseAdapter):
        self.db = db
    
    async def save_food_analysis(self, user_id: int, analysis: FoodAnalysisResult) -> bool:
        """
        Сохраняет анализ еды в базу данных
        
        Args:
            user_id: ID пользователя
            analysis: Результат анализа фото
            
        Returns:
            True при успехе, False при ошибке
        """
        try:
            # Определяем калории в зависимости от типа анализа
            calories = self._get_calories_from_analysis(analysis)
            logger.info(f"Сохраняем анализ для пользователя {user_id}: {calories} ккал")
            
            # Сохраняем через адаптер БД
            success = await self.db.save_food_entry(user_id, analysis)
            
            if success:
                logger.info(f"Анализ успешно сохранен для пользователя {user_id}")
            else:
                logger.error(f"Ошибка сохранения анализа для пользователя {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка сохранения анализа для пользователя {user_id}: {e}")
            return False
    
    def _get_calories_from_analysis(self, analysis) -> float:
        """Извлекает калории из анализа (поддерживает обе структуры)"""
        if hasattr(analysis, 'totals') and hasattr(analysis.totals, 'kcal'):
            # Новая структура ProfessionalFoodAnalysis
            return float(analysis.totals.kcal)
        elif hasattr(analysis, 'total_calories'):
            # Старая структура FoodAnalysisResult
            return float(analysis.total_calories)
        else:
            return 0.0
    
    async def get_daily_progress(self, user_id: int) -> Optional[DailyNutritionStats]:
        """
        Получает прогресс питания за день
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Статистика за день или None
        """
        try:
            return await self.db.get_daily_stats(user_id)
            
        except Exception as e:
            logger.error(f"Ошибка получения дневного прогресса для пользователя {user_id}: {e}")
            return None
    
    async def get_weekly_progress(self, user_id: int) -> Dict[str, Any]:
        """
        Получает прогресс питания за неделю
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь с недельной статистикой
        """
        try:
            return await self.db.get_weekly_stats(user_id)
            
        except Exception as e:
            logger.error(f"Ошибка получения недельного прогресса для пользователя {user_id}: {e}")
            return {}
    
    async def get_food_history(self, user_id: int, days: int = 7) -> list:
        """
        Получает историю питания за последние дни
        
        Args:
            user_id: ID пользователя
            days: Количество дней назад
            
        Returns:
            Список записей о питании
        """
        try:
            return await self.db.get_food_history(user_id, days)
            
        except Exception as e:
            logger.error(f"Ошибка получения истории питания для пользователя {user_id}: {e}")
            return []
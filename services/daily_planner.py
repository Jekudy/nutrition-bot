"""
Daily Planner Service: собирает данные → OpenAI → план на день
"""
from typing import Optional
from datetime import datetime, date, timedelta
from shared.logger import get_logger
from shared.models import DailyPlan, UserProfile, DailyNutritionStats
from adapters.openai_client import OpenAIClient
from adapters.database import DatabaseAdapter

logger = get_logger(__name__)

class DailyPlanner:
    """Планирование питания на день через OpenAI"""
    
    def __init__(self, openai_client: OpenAIClient, db: DatabaseAdapter):
        self.openai_client = openai_client
        self.db = db
    
    async def create_daily_plan(self, user_id: int) -> Optional[str]:
        """
        Создает план питания на день
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Готовое сообщение с планом или None при ошибке
        """
        try:
            logger.info(f"Создаем план на день для пользователя {user_id}")
            
            # Собираем статистику
            today = date.today()
            yesterday = today - timedelta(days=1)
            
            yesterday_stats = await self.db.get_daily_stats(user_id, yesterday.isoformat())
            weekly_stats = await self.db.get_weekly_stats(user_id)
            
            # Формируем промпт
            prompt = self._build_planning_prompt(yesterday_stats, weekly_stats)
            
            # OpenAI создает план
            plan_message = await self.openai_client.chat_completion(prompt)
            
            if plan_message:
                logger.info(f"План создан для пользователя {user_id}")
                
            return plan_message
            
        except Exception as e:
            logger.error(f"Ошибка создания плана для пользователя {user_id}: {e}")
            return None
    
    def _build_planning_prompt(self, yesterday: Optional[DailyNutritionStats], weekly_stats: dict) -> str:
        """Формирует промпт для планирования дня"""
        
        # Анализ вчерашнего дня
        yesterday_summary = "Данных за вчера нет"
        if yesterday:
            yesterday_summary = f"""
            Вчера съедено:
            - Калории: {yesterday.total_calories:.0f} ккал
            - Белки: {yesterday.total_protein:.1f}г
            - Клетчатка: {yesterday.total_fiber:.1f}г
            - Ягоды: {yesterday.berries_grams:.0f}г
            - Красное мясо: {yesterday.red_meat_grams:.0f}г
            - Овощи: {yesterday.vegetables_grams:.0f}г
            """
        
        # Недельная статистика
        weekly_summary = f"""
        На этой неделе:
        - Ягоды: {weekly_stats.get('weekly_berries', 0):.0f}г из 175г (норма)
        - Красное мясо: {weekly_stats.get('weekly_red_meat', 0):.0f}г из 700г (максимум)
        - Морепродукты: {weekly_stats.get('weekly_seafood', 0):.0f}г
        - Орехи: {weekly_stats.get('weekly_nuts', 0):.0f}г
        - Овощи: {weekly_stats.get('weekly_vegetables', 0):.0f}г
        """
        
        return f"""
        Ты персональный нутрициолог. Создай план питания на сегодня.
        
        РЕКОМЕНДУЕМЫЕ ДНЕВНЫЕ НОРМЫ:
        - Калории: 2200 ккал
        - Белки: 150г
        - Клетчатка: 50г
        - Овощи: 400-500г
        - Орехи: 30-50г в день
        
        АНАЛИЗ ВЧЕРАШНЕГО ДНЯ:
        {yesterday_summary}
        
        НЕДЕЛЬНАЯ СТАТИСТИКА:
        {weekly_summary}
        
        НАУЧНЫЕ НОРМЫ ПИТАНИЯ:
        - Ягоды: 150-200г в неделю (антиоксиданты)
        - Красное мясо: максимум 700г в неделю
        - Морепродукты: 2-3 порции в неделю (омега-3)
        - Клетчатка: 50-55г в день (здоровье кишечника)
        
        ЗАДАЧА:
        Создай мотивирующее сообщение с планом на сегодня:
        1. Поприветствуй и кратко оцени вчерашний день
        2. Дай конкретные цели на сегодня (калории, белки, клетчатка)
        3. Порекомендуй конкретные продукты с учетом недельных норм
        4. Сделай акцент на том, чего не хватает на неделе
        
        Пиши дружелюбно, мотивируй, используй эмодзи. Размер: 150-200 слов.
        """
"""
Daily Reporter Service: собирает статистику → OpenAI → отчет
"""
from typing import Optional
from datetime import datetime, date
from shared.logger import get_logger
from shared.models import DailyReport, UserProfile, DailyNutritionStats
from adapters.openai_client import OpenAIClient
from adapters.database import DatabaseAdapter

logger = get_logger(__name__)

class DailyReporter:
    """Создание отчетов за день через OpenAI"""
    
    def __init__(self, openai_client: OpenAIClient, db: DatabaseAdapter):
        self.openai_client = openai_client
        self.db = db
    
    async def generate_daily_report(self, user_id: int) -> Optional[str]:
        """
        Создает отчет за день
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Готовый отчет или None при ошибке
        """
        try:
            logger.info(f"Создаем отчет за день для пользователя {user_id}")
            
            # Собираем данные дня
            today = date.today()
            today_stats = await self.db.get_daily_stats(user_id, today.isoformat())
            weekly_stats = await self.db.get_weekly_stats(user_id)
            
            if not today_stats:
                return "📈 Сегодня еще нет данных для отчета. Отправьте фото еды для анализа!"
            
            # Формируем промпт для отчета
            prompt = self._build_report_prompt(today_stats, weekly_stats)
            
            # OpenAI создает отчет
            report_message = await self.openai_client.chat_completion(prompt)
            
            if report_message:
                logger.info(f"Отчет создан для пользователя {user_id}")
                
            return report_message
            
        except Exception as e:
            logger.error(f"Ошибка создания отчета для пользователя {user_id}: {e}")
            return None
    
    def _build_report_prompt(self, today: DailyNutritionStats, weekly_stats: dict) -> str:
        """Формирует промпт для отчета за день"""
        
        # Анализ сегодняшнего дня
        daily_calories_target = 2200
        daily_protein_target = 150
        daily_fiber_target = 50
        weekly_berries_target = 175
        weekly_red_meat_max = 700
        
        # Детальный анализ дня
        calories_status = "норма"
        if today.total_calories > daily_calories_target * 1.1:
            calories_status = "превышение"
        elif today.total_calories < daily_calories_target * 0.8:
            calories_status = "недобор"
        
        protein_percent = (today.total_protein / daily_protein_target) * 100
        fiber_percent = (today.total_fiber / daily_fiber_target) * 100
        
        # Анализ недели
        weekly_berries = weekly_stats.get('weekly_berries', 0)
        weekly_red_meat = weekly_stats.get('weekly_red_meat', 0)
        berries_week_percent = (weekly_berries / weekly_berries_target) * 100
        red_meat_week_percent = (weekly_red_meat / weekly_red_meat_max) * 100
        
        return f"""
        Ты персональный нутрициолог. Создай вечерний отчет-анализ дня для пользователя.
        
        РЕКОМЕНДУЕМЫЕ НОРМЫ:
        - Калории: {daily_calories_target} ккал в день
        - Белки: {daily_protein_target}г в день
        - Клетчатка: {daily_fiber_target}г в день
        - Ягоды: {weekly_berries_target}г в неделю
        - Красное мясо: максимум {weekly_red_meat_max}г в неделю
        
        РЕЗУЛЬТАТЫ СЕГОДНЯ:
        - Калории: {today.total_calories:.0f} ккал ({calories_status})
        - Белки: {today.total_protein:.1f}г ({protein_percent:.0f}% от нормы)
        - Углеводы: {today.total_carbs:.1f}г
        - Жиры: {today.total_fat:.1f}г  
        - Клетчатка: {today.total_fiber:.1f}г ({fiber_percent:.0f}% от нормы)
        - Ягоды: {today.berries_grams:.0f}г
        - Красное мясо: {today.red_meat_grams:.0f}г
        - Морепродукты: {today.seafood_grams:.0f}г
        - Овощи: {today.vegetables_grams:.0f}г
        - Орехи: {today.nuts_grams:.0f}г
        
        НЕДЕЛЬНАЯ СТАТИСТИКА:
        - Ягоды: {weekly_berries:.0f}г ({berries_week_percent:.0f}% от недельной нормы)
        - Красное мясо: {weekly_red_meat:.0f}г ({red_meat_week_percent:.0f}% от недельного лимита)
        - Морепродукты: {weekly_stats.get('weekly_seafood', 0):.0f}г
        - Орехи: {weekly_stats.get('weekly_nuts', 0):.0f}г
        - Овощи: {weekly_stats.get('weekly_vegetables', 0):.0f}г
        
        ЗАДАЧА:
        Создай персональный отчет:
        1. Оцени день по 10-балльной шкале и объясни оценку
        2. Отметь достижения (что хорошо получилось)
        3. Укажи области для улучшения
        4. Дай рекомендации на завтра с учетом недельного баланса
        5. Если есть превышение калорий, предложи корректировку на завтра
        
        Тон: дружелюбный, конструктивный, мотивирующий.
        Размер: 200-300 слов. Используй эмодзи для наглядности.
        """
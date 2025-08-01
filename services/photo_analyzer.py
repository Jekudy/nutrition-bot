"""
Photo Analyzer Service: фото + промпт → OpenAI Structured Outputs
"""
from typing import Optional, Dict, Any
from shared.logger import get_logger
from shared.models import FoodAnalysisResult  # Старая модель для совместимости
from shared.new_models import ProfessionalFoodAnalysis, DEFAULT_DAILY_TARGETS, calculate_percent_of_daily
from shared.prompt_manager import prompt_manager
from shared.utils import generate_meal_id, detect_eating_place
from adapters.openai_client import OpenAIClient

logger = get_logger(__name__)

class PhotoAnalyzer:
    """Анализ фотографий еды через OpenAI Structured Outputs"""
    
    def __init__(self, openai_client: OpenAIClient):
        self.openai_client = openai_client
    
    async def analyze_food_photo_professional(self, photo_bytes: bytes, user_id: int) -> Optional[ProfessionalFoodAnalysis]:
        """
        Анализирует фото еды и возвращает профессиональные структурированные данные
        
        Args:
            photo_bytes: Данные изображения
            user_id: ID пользователя для контекста
            
        Returns:
            Профессиональный структурированный результат анализа или None при ошибке
        """
        try:
            logger.info(f"🔍 Начинаем профессиональный анализ фото для пользователя {user_id}")
            
            # Генерируем контекст для анализа
            meal_id = generate_meal_id()
            eating_place = detect_eating_place()
            daily_targets = DEFAULT_DAILY_TARGETS
            
            logger.info(f"📋 Контекст: meal_id={meal_id}, eating_place={eating_place}")
            
            # Формируем профессиональный промпт
            prompt = prompt_manager.build_food_analysis_prompt(
                eating_place=eating_place,
                meal_id=meal_id,
                daily_targets=daily_targets
            )
            
            # Используем новый метод structured output с ProfessionalFoodAnalysis
            result = await self.openai_client.analyze_image_professional(photo_bytes, prompt)
            
            if not result:
                logger.error(f"❌ OpenAI не вернул результат для пользователя {user_id}")
                return None
            
            logger.info(f"✅ Профессиональный анализ завершен для пользователя {user_id}: {result.totals.kcal} ккал")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка профессионального анализа фото для пользователя {user_id}: {e}")
            return None

    async def analyze_food_photo(self, photo_bytes: bytes, user_id: int) -> Optional[FoodAnalysisResult]:
        """
        LEGACY: Анализирует фото еды и возвращает структурированные данные (старая модель)
        
        Args:
            photo_bytes: Данные изображения
            user_id: ID пользователя для контекста
            
        Returns:
            Структурированный результат анализа или None при ошибке
        """
        try:
            logger.info(f"Начинаем legacy анализ фото для пользователя {user_id}")
            
            # Формируем промпт для анализа
            prompt = self._build_analysis_prompt()
            
            # Используем новый метод structured output
            result = await self.openai_client.analyze_image_structured(photo_bytes, prompt)
            
            if not result:
                logger.error(f"OpenAI не вернул результат для пользователя {user_id}")
                return None
            
            logger.info(f"Анализ завершен для пользователя {user_id}: {result.total_calories} ккал")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка анализа фото для пользователя {user_id}: {e}")
            return None
    
    def _build_analysis_prompt(self) -> str:
        """Формирует промпт для анализа фото"""
        return """
        Проанализируй фотографию еды и определи её пищевую ценность.
        
        Твоя задача:
        1. Определи все видимые продукты и блюда
        2. Оцени их вес/объем в граммах  
        3. Рассчитай калории и макронутриенты
        4. Определи специальные категории (ягоды, красное мясо, овощи и т.д.)
        
        Принципы анализа:
        - При неопределенности выбирай БОЛЬШУЮ калорийность для безопасности
        - Учитывай способ приготовления (жарка добавляет калории)
        - Для соусов и заправок добавляй примерные калории
        - Скрытые ингредиенты (масло, сахар) тоже учитывай
        
        Верни структурированный ответ с:
        - Общими калориями и макросами
        - Списком отдельных продуктов
        - Специфичными категориями (ягоды, мясо, овощи)
        - Факторами неопределенности
        - Объяснением анализа
        
        Важно: Лучше переоценить калории, чем недооценить!
        """
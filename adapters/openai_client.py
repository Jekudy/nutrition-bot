"""
OpenAI Client: Реальный клиент для работы с OpenAI API
"""
import os
import base64
import json
from typing import Optional
from openai import AsyncOpenAI
from shared.logger import get_logger
from shared.models import FoodAnalysisResult
from shared.new_models import ProfessionalFoodAnalysis

logger = get_logger(__name__)

class OpenAIClient:
    """Реальный OpenAI клиент с поддержкой Structured Outputs"""
    
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY не найден в переменных окружения")
        
        try:
            self.client = AsyncOpenAI(api_key=api_key)
            self.model = "gpt-4o"  # Модель с поддержкой Structured Outputs
            logger.info("✅ OpenAI клиент успешно инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации OpenAI клиента: {e}")
            raise
    
    async def analyze_image(self, photo_bytes: bytes, prompt: str) -> Optional[str]:
        """
        Анализ изображения с возвратом JSON строки
        
        Args:
            photo_bytes: Данные изображения
            prompt: Промпт для анализа
            
        Returns:
            JSON строка с результатом анализа
        """
        try:
            # Кодируем изображение в base64
            base64_image = base64.b64encode(photo_bytes).decode('utf-8')
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            logger.info(f"✅ Анализ изображения завершен (размер: {len(photo_bytes)} байт)")
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа изображения: {e}")
            return None
    
    async def analyze_image_structured(self, photo_bytes: bytes, prompt: str) -> Optional[FoodAnalysisResult]:
        """
        Анализ изображения с Structured Outputs
        
        Args:
            photo_bytes: Данные изображения
            prompt: Промпт для анализа
            
        Returns:
            Структурированный результат анализа
        """
        try:
            # Кодируем изображение в base64
            base64_image = base64.b64encode(photo_bytes).decode('utf-8')
            
            completion = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                response_format=FoodAnalysisResult
            )
            
            logger.info(f"✅ Structured анализ изображения завершен (размер: {len(photo_bytes)} байт)")
            return completion.choices[0].message.parsed
            
        except Exception as e:
            logger.error(f"❌ Ошибка structured анализа изображения: {e}")
            return None
    
    async def analyze_image_professional(self, photo_bytes: bytes, prompt: str) -> Optional[ProfessionalFoodAnalysis]:
        """
        Профессиональный анализ изображения с новой JSON схемой
        
        Args:
            photo_bytes: Данные изображения 
            prompt: Промпт для анализа
            
        Returns:
            Профессиональный структурированный результат анализа
        """
        try:
            # Кодируем изображение в base64
            base64_image = base64.b64encode(photo_bytes).decode('utf-8')
            
            completion = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                response_format=ProfessionalFoodAnalysis
            )
            
            logger.info(f"✅ Профессиональный анализ изображения завершен (размер: {len(photo_bytes)} байт)")
            return completion.choices[0].message.parsed
            
        except Exception as e:
            logger.error(f"❌ Ошибка профессионального анализа изображения: {e}")
            return None
    
    async def chat_completion(self, prompt: str) -> Optional[str]:
        """
        Обычный chat completion для текстовых запросов
        
        Args:
            prompt: Промпт для обработки
            
        Returns:
            Ответ от модели
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            logger.info("✅ Chat completion запрос выполнен")
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"❌ Ошибка chat completion: {e}")
            return None
    
    async def close(self):
        """Закрытие соединения с OpenAI"""
        try:
            await self.client.close()
            logger.info("✅ OpenAI клиент корректно закрыт")
        except Exception as e:
            logger.error(f"❌ Ошибка закрытия OpenAI клиента: {e}")
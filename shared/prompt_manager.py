"""
Prompt Manager: централизованное управление промптами
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
from shared.logger import get_logger

logger = get_logger(__name__)

class PromptManager:
    """Менеджер для загрузки и форматирования промптов"""
    
    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = Path(prompts_dir)
        self._prompts_cache = {}
    
    def load_prompt(self, prompt_name: str) -> str:
        """
        Загружает промпт из файла
        
        Args:
            prompt_name: Имя файла промпта (без расширения)
            
        Returns:
            Содержимое промпта
        """
        if prompt_name in self._prompts_cache:
            return self._prompts_cache[prompt_name]
        
        prompt_file = self.prompts_dir / f"{prompt_name}.txt"
        
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                self._prompts_cache[prompt_name] = content
                logger.info(f"Загружен промпт: {prompt_name}")
                return content
                
        except FileNotFoundError:
            logger.error(f"Файл промпта не найден: {prompt_file}")
            raise
        except Exception as e:
            logger.error(f"Ошибка загрузки промпта {prompt_name}: {e}")
            raise
    
    def format_prompt(self, prompt_name: str, **kwargs) -> str:
        """
        Загружает и форматирует промпт с переменными
        
        Args:
            prompt_name: Имя промпта
            **kwargs: Переменные для подстановки
            
        Returns:
            Отформатированный промпт
        """
        try:
            template = self.load_prompt(prompt_name)
            return template.format(**kwargs)
            
        except KeyError as e:
            logger.error(f"Не найдена переменная в промпте {prompt_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка форматирования промпта {prompt_name}: {e}")
            raise
    
    def build_food_analysis_prompt(self, 
                                 eating_place: str = "home",
                                 meal_id: str = None,
                                 daily_targets: Dict[str, Any] = None) -> str:
        """
        Создает промпт для анализа фото еды
        
        Args:
            eating_place: "home" или "restaurant"
            meal_id: ID приема пищи
            daily_targets: Дневные нормы нутриентов
            
        Returns:
            Готовый промпт для анализа
        """
        try:
            # Базовый промпт
            base_prompt = self.load_prompt("food_analysis_professional")
            
            # Добавляем параметры
            context_parts = []
            
            if eating_place:
                context_parts.append(f"eating_place: {eating_place}")
            
            if meal_id:
                context_parts.append(f"meal_id: {meal_id}")
            
            if daily_targets:
                import json
                context_parts.append(f"daily_targets: {json.dumps(daily_targets, ensure_ascii=False)}")
            
            # Объединяем промпт с контекстом
            if context_parts:
                context = "\n".join(context_parts)
                return f"{base_prompt}\n\nContext:\n{context}"
            
            return base_prompt
            
        except Exception as e:
            logger.error(f"Ошибка создания промпта для анализа еды: {e}")
            # Fallback на простой промпт
            return self.load_prompt("food_analysis_current")
    
    def reload_prompts(self):
        """Очищает кэш и перезагружает промпты"""
        self._prompts_cache.clear()
        logger.info("Кэш промптов очищен")

# Глобальный экземпляр
prompt_manager = PromptManager()
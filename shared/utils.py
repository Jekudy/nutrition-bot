"""
Утилиты для Nutrition Bot
"""
import random
from datetime import datetime
from typing import Literal, Dict, Any

def generate_meal_id(meal_type: str = None) -> str:
    """
    Генерирует ID приема пищи
    
    Args:
        meal_type: Тип приема пищи (breakfast, lunch, dinner, snack)
        
    Returns:
        ID в формате "2025-08-01-breakfast"
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    
    if not meal_type:
        # Автоопределение по времени
        hour = now.hour
        if 6 <= hour < 11:
            meal_type = "breakfast"
        elif 11 <= hour < 16:
            meal_type = "lunch"
        elif 16 <= hour < 22:
            meal_type = "dinner"
        else:
            meal_type = "snack"
    
    return f"{date_str}-{meal_type}"

def detect_eating_place() -> Literal["home", "restaurant"]:
    """
    Определяет место приема пищи
    
    В будущем можно добавить ML/геолокацию,
    пока просто возвращаем 'home' по умолчанию
    
    Returns:
        "home" или "restaurant"
    """
    # TODO: Добавить детекцию по геолокации, времени, паттернам
    return "home"

def get_restaurant_multiplier(eating_place: str) -> float:
    """
    Возвращает множитель калорийности для ресторанов
    
    Args:
        eating_place: "home" или "restaurant"
        
    Returns:
        Множитель (1.0 для дома, 1.2 для ресторана)
    """
    return 1.2 if eating_place == "restaurant" else 1.0

def format_weight_estimate(weight: float) -> str:
    """
    Форматирует вес с учетом погрешности
    
    Args:
        weight: Вес в граммах
        
    Returns:
        Строка типа "150г (±20%)"
    """
    return f"{weight:.0f}г (±20%)"

def should_ask_clarification(confidence: float, threshold: float = 0.6) -> bool:
    """
    Определяет, нужно ли задавать уточняющие вопросы
    
    Args:
        confidence: Уверенность модели (0-1)
        threshold: Порог для уточнений
        
    Returns:
        True если нужны уточнения
    """
    return confidence < threshold
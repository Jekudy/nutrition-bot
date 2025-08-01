"""
Модели данных для nutrition bot
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class FoodItem(BaseModel):
    """Отдельный продукт в анализе"""
    name: str = Field(description="Название продукта")
    weight_grams: float = Field(description="Вес в граммах")
    calories: float = Field(description="Калории")
    protein: float = Field(description="Белки в граммах")
    carbs: float = Field(description="Углеводы в граммах") 
    fat: float = Field(description="Жиры в граммах")
    fiber: float = Field(description="Клетчатка в граммах")
    
    # Специфичные нутриенты для отслеживания норм
    berries_grams: Optional[float] = Field(default=0, description="Ягоды в граммах")
    red_meat_grams: Optional[float] = Field(default=0, description="Красное мясо в граммах")
    seafood_grams: Optional[float] = Field(default=0, description="Морепродукты в граммах")
    nuts_grams: Optional[float] = Field(default=0, description="Орехи в граммах")
    olive_oil_ml: Optional[float] = Field(default=0, description="Оливковое масло в мл")
    vegetables_grams: Optional[float] = Field(default=0, description="Овощи в граммах")

class AnalysisVariant(BaseModel):
    """Варианты анализа с разной калорийностью"""
    variant: str = Field(description="Тип варианта: conservative/likely/maximum")
    total_calories: float = Field(description="Общие калории")
    confidence: float = Field(description="Уверенность 0-1")

class FoodAnalysisResult(BaseModel):
    """Результат анализа фото еды через Structured Outputs (упрощенная версия)"""
    confidence: float = Field(description="Общая уверенность анализа 0-1")
    
    # Агрегированные значения
    total_calories: float = Field(description="Общие калории блюда")
    total_protein: float = Field(description="Общие белки в граммах")
    total_carbs: float = Field(description="Общие углеводы в граммах")
    total_fat: float = Field(description="Общие жиры в граммах")
    total_fiber: float = Field(description="Общая клетчатка в граммах")
    
    # Специфичные нутриенты для отслеживания норм
    berries_grams: float = Field(description="Ягоды в граммах")
    red_meat_grams: float = Field(description="Красное мясо в граммах")
    seafood_grams: float = Field(description="Морепродукты в граммах")
    nuts_grams: float = Field(description="Орехи в граммах")
    olive_oil_ml: float = Field(description="Оливковое масло в мл")
    vegetables_grams: float = Field(description="Овощи в граммах")
    whole_grains_grams: float = Field(description="Цельнозерновые в граммах")
    
    # Объяснение анализа
    explanation: str = Field(description="Подробное объяснение анализа и состава блюда")

class UserProfile(BaseModel):
    """Профиль пользователя"""
    user_id: int
    daily_calories_target: int = Field(default=2250)
    daily_protein_target: float = Field(default=150)
    daily_carbs_target: float = Field(default=280)
    daily_fat_target: float = Field(default=75)
    daily_fiber_target: float = Field(default=50)
    
    # Недельные цели
    weekly_berries_target: float = Field(default=175)  # граммы
    weekly_red_meat_max: float = Field(default=700)   # граммы
    weekly_seafood_target: float = Field(default=300) # граммы
    
    # Предпочтения
    dietary_preferences: str = Field(default="standard")
    allergies: List[str] = Field(default_factory=list)
    timezone: str = Field(default="UTC")

class DailyNutritionStats(BaseModel):
    """Статистика питания за день"""
    user_id: int
    date: datetime
    total_calories: float = 0
    total_protein: float = 0
    total_carbs: float = 0
    total_fat: float = 0
    total_fiber: float = 0
    
    # Специфичные нутриенты
    berries_grams: float = 0
    red_meat_grams: float = 0
    seafood_grams: float = 0
    nuts_grams: float = 0
    olive_oil_ml: float = 0
    vegetables_grams: float = 0

class NutritionProgress(BaseModel):
    """Прогресс по питанию"""
    calories_consumed: float
    calories_remaining: float
    protein_progress_percent: float
    recommendations: List[str]
    
class DailyPlan(BaseModel):
    """План питания на день"""
    date: datetime
    calorie_target: int
    protein_target: float
    carbs_target: float
    fat_target: float
    fiber_target: float
    recommended_foods: List[str]
    plan_message: str  # Готовое сообщение от OpenAI

class DailyReport(BaseModel):
    """Отчет за день"""
    date: datetime
    achievements: List[str]
    areas_for_improvement: List[str]
    tomorrow_adjustments: Dict[str, float]
    report_message: str  # Готовое сообщение от OpenAI
    overall_score: int = Field(ge=1, le=10)  # 1-10
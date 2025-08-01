"""
Новые модели данных под профессиональную JSON схему
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class FoodItemProfessional(BaseModel):
    """Отдельный продукт в анализе (новая схема)"""
    food: str = Field(description="Название продукта на русском, без заглавных букв")
    weight_g: float = Field(description="Вес в граммах", ge=0)
    kcal: int = Field(description="Калории (целое число)", ge=0) 
    protein_g: float = Field(description="Белки в граммах", ge=0)
    fat_g: float = Field(description="Жиры в граммах", ge=0)
    carb_g: float = Field(description="Углеводы в граммах", ge=0)
    fiber_g: float = Field(description="Клетчатка в граммах", ge=0)
    sugar_g: float = Field(description="Сахар в граммах", ge=0)
    calcium_mg: float = Field(description="Кальций в мг", ge=0)
    iron_mg: float = Field(description="Железо в мг", ge=0)
    vitaminA_mcg: float = Field(description="Витамин A в мкг", ge=0)
    omega3_g: float = Field(description="Омега-3 в граммах", ge=0)
    cholesterol_mg: float = Field(description="Холестерин в мг", ge=0)

class NutrientTotals(BaseModel):
    """Суммарные нутриенты (те же поля что у FoodItemProfessional, но без food и weight_g)"""
    kcal: int = Field(description="Калории (целое число)", ge=0)
    protein_g: float = Field(description="Белки в граммах", ge=0)
    fat_g: float = Field(description="Жиры в граммах", ge=0) 
    carb_g: float = Field(description="Углеводы в граммах", ge=0)
    fiber_g: float = Field(description="Клетчатка в граммах", ge=0)
    sugar_g: float = Field(description="Сахар в граммах", ge=0)
    calcium_mg: float = Field(description="Кальций в мг", ge=0)
    iron_mg: float = Field(description="Железо в мг", ge=0)
    vitaminA_mcg: float = Field(description="Витамин A в мкг", ge=0)
    omega3_g: float = Field(description="Омега-3 в граммах", ge=0)
    cholesterol_mg: float = Field(description="Холестерин в мг", ge=0)

class NutrientPercents(BaseModel):
    """Проценты от дневных норм (те же поля, округлённые до 1 знака)"""
    kcal: float = Field(description="% калорий от дневной нормы", ge=0)
    protein_g: float = Field(description="% белков от дневной нормы", ge=0)
    fat_g: float = Field(description="% жиров от дневной нормы", ge=0)
    carb_g: float = Field(description="% углеводов от дневной нормы", ge=0)
    fiber_g: float = Field(description="% клетчатки от дневной нормы", ge=0)
    sugar_g: float = Field(description="% сахара от дневной нормы", ge=0)
    calcium_mg: float = Field(description="% кальция от дневной нормы", ge=0)
    iron_mg: float = Field(description="% железа от дневной нормы", ge=0)
    vitaminA_mcg: float = Field(description="% витамина A от дневной нормы", ge=0)
    omega3_g: float = Field(description="% омега-3 от дневной нормы", ge=0)
    cholesterol_mg: float = Field(description="% холестерина от дневной нормы", ge=0)

class ProfessionalFoodAnalysis(BaseModel):
    """Профессиональный результат анализа фото еды"""
    meal_id: str = Field(description="ID приема пищи (например: 2025-08-01-breakfast)")
    items: List[FoodItemProfessional] = Field(description="Список продуктов, отсортированный по убыванию калорий")
    totals: NutrientTotals = Field(description="Суммарные значения всех нутриентов")
    percent_of_daily: NutrientPercents = Field(description="Проценты от дневных целей без знака '%'")

# Дневные нормы для расчета процентов
DEFAULT_DAILY_TARGETS = {
    "kcal": 2200,
    "protein_g": 150.0,
    "fat_g": 80.0,
    "carb_g": 275.0,
    "fiber_g": 50.0,
    "sugar_g": 50.0,  # максимум
    "calcium_mg": 1000.0,
    "iron_mg": 18.0,
    "vitaminA_mcg": 900.0,
    "omega3_g": 2.0,
    "cholesterol_mg": 300.0  # максимум
}

def calculate_percent_of_daily(totals: NutrientTotals, daily_targets: Dict[str, float] = None) -> NutrientPercents:
    """
    Рассчитывает проценты от дневных норм
    
    Args:
        totals: Суммарные нутриенты
        daily_targets: Дневные нормы (если None, используются DEFAULT_DAILY_TARGETS)
        
    Returns:
        Проценты от дневных норм
    """
    if daily_targets is None:
        daily_targets = DEFAULT_DAILY_TARGETS
        
    percents = {}
    for field, value in totals.model_dump().items():
        target = daily_targets.get(field, 100.0)  # fallback
        percent = round((value / target) * 100, 1) if target > 0 else 0.0
        percents[field] = percent
    
    return NutrientPercents(**percents)
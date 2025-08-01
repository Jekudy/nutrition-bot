"""
Модуль логирования с автоочисткой через 72 часа
"""
import logging
import logging.handlers
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import asyncio
import glob

# Константы
LOG_DIR = Path("logs")
LOG_RETENTION_HOURS = 72
MAX_LOG_SIZE_MB = 50
BACKUP_COUNT = 5

class LogCleaner:
    """Автоочистка старых логов"""
    
    @staticmethod
    async def cleanup_old_logs():
        """Удаляет логи старше 72 часов"""
        if not LOG_DIR.exists():
            return
            
        cutoff_time = datetime.now() - timedelta(hours=LOG_RETENTION_HOURS)
        
        for log_file in LOG_DIR.glob("*.log*"):
            try:
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_time:
                    log_file.unlink()
                    print(f"Удален старый лог: {log_file}")
            except Exception as e:
                print(f"Ошибка при удалении {log_file}: {e}")
    
    @staticmethod
    async def schedule_cleanup():
        """Запускает очистку каждые 6 часов"""
        while True:
            await LogCleaner.cleanup_old_logs()
            await asyncio.sleep(6 * 3600)  # 6 часов

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Настраивает логгер с ротацией и автоочисткой
    
    Args:
        name: Имя логгера (обычно __name__)
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Настроенный логгер
    """
    # Создаем директорию для логов
    LOG_DIR.mkdir(exist_ok=True)
    
    # Настраиваем логгер
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Избегаем дублирования хендлеров
    if logger.handlers:
        return logger
    
    # Форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Ротирующий файловый хендлер
    log_file = LOG_DIR / f"{name.replace('.', '_')}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=MAX_LOG_SIZE_MB * 1024 * 1024,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Консольный хендлер для разработки
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)  # В консоль только важное
    logger.addHandler(console_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """Получить логгер для модуля"""
    return setup_logger(name)

# Глобальные логгеры для основных компонентов
main_logger = get_logger("nutrition_bot.main")
openai_logger = get_logger("nutrition_bot.openai")
telegram_logger = get_logger("nutrition_bot.telegram")
database_logger = get_logger("nutrition_bot.database")
analyzer_logger = get_logger("nutrition_bot.analyzer")
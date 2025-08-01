"""
Cloud Logger: логирование для облачных сред (Railway, Docker)
"""
import os
import sys
import logging
from typing import Optional

def get_cloud_logger(name: str) -> logging.Logger:
    """
    Создает логгер для облачной среды
    
    В облачной среде логи выводятся в stdout/stderr для системы мониторинга
    В локальной среде работает как обычно с файлами
    
    Args:
        name: Имя логгера
        
    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    
    # Проверяем, настроен ли уже логгер
    if logger.handlers:
        return logger
    
    # Определяем уровень логирования
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Определяем окружение
    environment = os.getenv('ENVIRONMENT', 'development')
    is_production = environment in ['production', 'staging']
    
    if is_production:
        # Продакшен: логи в stdout для Railway/Docker
        handler = logging.StreamHandler(sys.stdout)
        
        # Простой формат для облачных логов
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # Локальная разработка: логи в файлы (как было)
        from .logger import get_logger as get_file_logger
        return get_file_logger(name)
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Предотвращаем дублирование в родительские логгеры
    logger.propagate = False
    
    return logger

def setup_flask_logging():
    """Настройка логирования для Flask в облачной среде"""
    environment = os.getenv('ENVIRONMENT', 'development')
    
    if environment in ['production', 'staging']:
        # Отключаем стандартные логи Flask в продакшене
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
        
        # Настраиваем уровень для основного Flask логгера
        flask_logger = logging.getLogger('flask.app')
        flask_logger.setLevel(logging.INFO)

def get_logger(name: str) -> logging.Logger:
    """
    Универсальная функция получения логгера
    
    Автоматически выбирает облачный или файловый логгер
    в зависимости от окружения
    """
    environment = os.getenv('ENVIRONMENT', 'development')
    
    if environment in ['production', 'staging']:
        return get_cloud_logger(name)
    else:
        # Импортируем локальный логгер только в dev среде
        from .logger import get_logger as get_file_logger
        return get_file_logger(name)
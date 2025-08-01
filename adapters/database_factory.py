"""
Database Factory: выбирает адаптер в зависимости от окружения
"""
import os
from .database import DatabaseAdapter
from .postgres_database import PostgreSQLAdapter
from shared.logger import get_logger

logger = get_logger(__name__)

def get_database_adapter():
    """
    Возвращает подходящий адаптер базы данных в зависимости от окружения
    
    Returns:
        DatabaseAdapter или PostgreSQLAdapter
    """
    database_url = os.getenv('DATABASE_URL')
    environment = os.getenv('ENVIRONMENT', 'development')
    
    if database_url and database_url.startswith('postgresql'):
        # Production: используем PostgreSQL
        logger.info("Используем PostgreSQL адаптер для продакшена")
        return PostgreSQLAdapter(database_url)
    else:
        # Development: используем SQLite
        logger.info("Используем SQLite адаптер для разработки")
        return DatabaseAdapter()
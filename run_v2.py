"""
Run V2: Современный запуск Nutrition Bot с новой архитектурой
"""
import os
import sys
import asyncio
import signal
from dotenv import load_dotenv
from main_v2 import NutritionBotV2
from shared.logger import get_logger

# Загружаем переменные окружения
load_dotenv()

logger = get_logger(__name__)

class BotRunner:
    """Класс для управления жизненным циклом бота"""
    
    def __init__(self):
        self.bot = None
        self.shutdown_requested = False
    
    def signal_handler(self, signum, frame):
        """Обработчик сигналов для корректного завершения"""
        logger.info(f"Получен сигнал {signum}, завершаем работу...")
        self.shutdown_requested = True
    
    def run(self):
        """Основной цикл запуска бота"""
        try:
            # Проверяем переменные окружения
            if not self._check_environment():
                return 1
            
            # Настраиваем обработчики сигналов
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            # Создаем и запускаем бота
            logger.info("🚀 Запуск Nutrition Bot V2...")
            self.bot = NutritionBotV2()
            
            # Запускаем бота (синхронно)
            self.bot.start()
            
            return 0
            
        except KeyboardInterrupt:
            logger.info("⌨️ Прерывание с клавиатуры")
            return 0
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
            return 1
    
    def _check_environment(self) -> bool:
        """Проверяет наличие необходимых переменных окружения"""
        required_vars = [
            'TELEGRAM_BOT_TOKEN',
            'OPENAI_API_KEY'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"❌ Отсутствуют переменные окружения: {', '.join(missing_vars)}")
            logger.error("Создайте файл .env с необходимыми токенами")
            return False
        
        logger.info("✅ Переменные окружения найдены")
        return True

def main():
    """Точка входа в приложение"""
    try:
        # Создаем и запускаем runner (синхронно)
        runner = BotRunner()
        exit_code = runner.run()
        
        if exit_code == 0:
            logger.info("👋 Бот завершил работу успешно")
        else:
            logger.error(f"💥 Бот завершился с ошибкой (код: {exit_code})")
        
        return exit_code
        
    except Exception as e:
        logger.error(f"💥 Необработанная ошибка в main: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
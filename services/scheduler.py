"""
Scheduler Service: управляет всеми уведомлениями по времени
"""
import asyncio
from datetime import datetime, time
from typing import Callable, Dict, List
from shared.logger import get_logger

logger = get_logger(__name__)

class NotificationScheduler:
    """Планировщик уведомлений с автоочисткой логов"""
    
    def __init__(self):
        self.scheduled_tasks: Dict[str, asyncio.Task] = {}
        self.running = False
        
        # Временные интервалы
        self.morning_time = time(8, 0)    # 8:00 утра
        self.evening_time = time(23, 59)  # 23:59 вечера
        
    async def start(self, daily_planner_callback: Callable, daily_reporter_callback: Callable):
        """
        Запускает планировщик
        
        Args:
            daily_planner_callback: Функция для утренних планов
            daily_reporter_callback: Функция для вечерних отчетов
        """
        logger.info("Запускаем планировщик уведомлений")
        self.running = True
        
        # Запускаем основные задачи
        self.scheduled_tasks['morning_plans'] = asyncio.create_task(
            self._schedule_morning_plans(daily_planner_callback)
        )
        
        self.scheduled_tasks['evening_reports'] = asyncio.create_task(
            self._schedule_evening_reports(daily_reporter_callback)
        )
        
        # Запускаем автоочистку логов
        from shared.logger import LogCleaner
        self.scheduled_tasks['log_cleanup'] = asyncio.create_task(
            LogCleaner.schedule_cleanup()
        )
        
        logger.info("Планировщик запущен")
    
    async def stop(self):
        """Останавливает планировщик"""
        logger.info("Останавливаем планировщик")
        self.running = False
        
        for task_name, task in self.scheduled_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"Задача {task_name} отменена")
        
        self.scheduled_tasks.clear()
        logger.info("Планировщик остановлен")
    
    async def _schedule_morning_plans(self, callback: Callable):
        """Отправляет утренние планы в 8:00"""
        while self.running:
            try:
                await self._wait_until_time(self.morning_time)
                
                if self.running:
                    logger.info("Время утренних планов - запускаем рассылку")
                    await callback()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в утренних планах: {e}")
                await asyncio.sleep(60)  # Ждем минуту перед повтором
    
    async def _schedule_evening_reports(self, callback: Callable):
        """Отправляет вечерние отчеты в 23:59"""
        while self.running:
            try:
                await self._wait_until_time(self.evening_time)
                
                if self.running:
                    logger.info("Время вечерних отчетов - запускаем рассылку")
                    await callback()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в вечерних отчетах: {e}")
                await asyncio.sleep(60)
    
    async def _wait_until_time(self, target_time: time):
        """Ждет до указанного времени"""
        now = datetime.now()
        target_datetime = datetime.combine(now.date(), target_time)
        
        # Если время уже прошло сегодня, ждем до завтра
        if target_datetime <= now:
            target_datetime = target_datetime.replace(day=target_datetime.day + 1)
        
        wait_seconds = (target_datetime - now).total_seconds()
        
        logger.info(f"Ждем до {target_datetime} ({wait_seconds/3600:.1f} часов)")
        await asyncio.sleep(wait_seconds)
    
    def schedule_one_time_notification(self, delay_seconds: int, callback: Callable, *args):
        """
        Планирует одноразовое уведомление
        
        Args:
            delay_seconds: Задержка в секундах
            callback: Функция для вызова
            *args: Аргументы для функции
        """
        async def delayed_call():
            await asyncio.sleep(delay_seconds)
            await callback(*args)
        
        task = asyncio.create_task(delayed_call())
        task_id = f"one_time_{datetime.now().timestamp()}"
        self.scheduled_tasks[task_id] = task
        
        logger.info(f"Запланировано одноразовое уведомление через {delay_seconds} секунд")
        return task_id
"""
Telegram Bot: современный адаптер с Application.builder() паттерном
"""
import os
from typing import Optional, Callable, Dict, Any, List
from telegram import Update, Message, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ContextTypes, 
    filters
)
from shared.logger import get_logger

logger = get_logger(__name__)

class TelegramBot:
    """Современный Telegram бот с Application архитектурой"""
    
    def __init__(self):
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        
        # Создаем Application через builder pattern
        self.application = Application.builder().token(token).build()
        
        # Хранилище для callback'ов
        self._command_handlers: Dict[str, Callable] = {}
        self._message_handler: Optional[Callable] = None
        self._photo_handler: Optional[Callable] = None
        self._callback_handler: Optional[Callable] = None
        
        logger.info("Telegram бот инициализирован с Application.builder()")
    
    def add_command_handler(self, command: str, callback: Callable):
        """
        Добавляет обработчик команды
        
        Args:
            command: Название команды (без /)
            callback: Async функция для обработки
        """
        self._command_handlers[command] = callback
        handler = CommandHandler(command, callback)
        self.application.add_handler(handler)
        logger.info(f"Добавлен обработчик команды /{command}")
    
    def add_message_handler(self, callback: Callable):
        """
        Добавляет обработчик текстовых сообщений
        
        Args:
            callback: Async функция для обработки
        """
        self._message_handler = callback
        handler = MessageHandler(filters.TEXT & ~filters.COMMAND, callback)
        self.application.add_handler(handler)
        logger.info("Добавлен обработчик текстовых сообщений")
    
    def add_photo_handler(self, callback: Callable):
        """
        Добавляет обработчик фотографий
        
        Args:
            callback: Async функция для обработки
        """
        self._photo_handler = callback
        handler = MessageHandler(filters.PHOTO, callback)
        self.application.add_handler(handler)
        logger.info("Добавлен обработчик фотографий")
    
    def add_callback_handler(self, callback: Callable):
        """
        Добавляет обработчик inline кнопок
        
        Args:
            callback: Async функция для обработки
        """
        self._callback_handler = callback
        handler = CallbackQueryHandler(callback)
        self.application.add_handler(handler)
        logger.info("Добавлен обработчик callback кнопок")
    
    async def send_message(
        self, 
        chat_id: int, 
        text: str, 
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        parse_mode: Optional[str] = None
    ) -> Optional[Message]:
        """
        Отправляет сообщение
        
        Args:
            chat_id: ID чата
            text: Текст сообщения
            reply_markup: Клавиатура (опционально)
            parse_mode: Режим парсинга (HTML, Markdown)
            
        Returns:
            Объект отправленного сообщения или None при ошибке
        """
        try:
            message = await self.application.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            logger.info(f"Сообщение отправлено в чат {chat_id}")
            return message
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            return None
    
    async def edit_message(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        parse_mode: Optional[str] = None
    ) -> bool:
        """
        Редактирует сообщение
        
        Args:
            chat_id: ID чата
            message_id: ID сообщения
            text: Новый текст
            reply_markup: Новая клавиатура
            parse_mode: Режим парсинга
            
        Returns:
            True при успехе, False при ошибке
        """
        try:
            await self.application.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            logger.info(f"Сообщение {message_id} отредактировано")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка редактирования сообщения: {e}")
            return False
    
    async def answer_callback_query(self, callback_query_id: str, text: str = None) -> bool:
        """
        Отвечает на callback query
        
        Args:
            callback_query_id: ID callback query
            text: Текст уведомления
            
        Returns:
            True при успехе, False при ошибке
        """
        try:
            await self.application.bot.answer_callback_query(
                callback_query_id=callback_query_id,
                text=text
            )
            logger.info("Callback query обработан")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обработки callback query: {e}")
            return False
    
    def create_inline_keyboard(self, buttons: List[List[Dict[str, str]]]) -> InlineKeyboardMarkup:
        """
        Создает inline клавиатуру
        
        Args:
            buttons: Список рядов кнопок, каждая кнопка - {"text": "Текст", "callback_data": "data"}
            
        Returns:
            InlineKeyboardMarkup объект
        """
        keyboard = []
        for row in buttons:
            keyboard_row = []
            for button in row:
                keyboard_row.append(
                    InlineKeyboardButton(
                        text=button["text"],
                        callback_data=button["callback_data"]
                    )
                )
            keyboard.append(keyboard_row)
        
        return InlineKeyboardMarkup(keyboard)
    
    async def get_file_bytes(self, file_id: str) -> Optional[bytes]:
        """
        Скачивает файл как bytes
        
        Args:
            file_id: ID файла
            
        Returns:
            Содержимое файла как bytes или None при ошибке
        """
        try:
            file = await self.application.bot.get_file(file_id)
            file_bytes = await file.download_as_bytearray()
            logger.info(f"Файл {file_id} скачан ({len(file_bytes)} байт)")
            return bytes(file_bytes)
            
        except Exception as e:
            logger.error(f"Ошибка скачивания файла: {e}")
            return None
    
    async def start_polling(self):
        """Запускает бота в режиме polling"""
        try:
            logger.info("Запускаем бота в режиме polling...")
            
            # Инициализируем приложение
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("Бот успешно запущен и работает!")
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            raise
    
    async def stop_polling(self):
        """Останавливает бота"""
        try:
            logger.info("Останавливаем бота...")
            
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            
            logger.info("Бот остановлен")
            
        except Exception as e:
            logger.error(f"Ошибка остановки бота: {e}")
    
    def run_polling(self):
        """Запускает бота синхронно"""
        try:
            logger.info("Запускаем бота через run_polling...")
            # run_polling() сам управляет event loop
            self.application.run_polling()
            
        except Exception as e:
            logger.error(f"Ошибка run_polling: {e}")
            raise
    
    def get_user_info(self, update: Update) -> Dict[str, Any]:
        """
        Извлекает информацию о пользователе из Update
        
        Args:
            update: Telegram Update объект
            
        Returns:
            Словарь с информацией о пользователе
        """
        user = update.effective_user
        chat = update.effective_chat
        
        return {
            "user_id": user.id if user else None,
            "username": user.username if user else None,
            "first_name": user.first_name if user else None,
            "last_name": user.last_name if user else None,
            "chat_id": chat.id if chat else None,
            "chat_type": chat.type if chat else None,
        }
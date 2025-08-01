"""
Nutrition Bot V2 - Webhook версия для Railway deployment
"""
import os
import asyncio
from typing import Dict, Any
from datetime import datetime, date
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request
import threading

# Импорты модулей бота
from adapters.database_factory import get_database_adapter
from adapters.openai_client import OpenAIClient
from services.photo_analyzer import PhotoAnalyzer
from services.nutrition_tracker import NutritionTracker
from services.daily_planner import DailyPlanner
from services.daily_reporter import DailyReporter
from services.scheduler import Scheduler
from shared.cloud_logger import get_logger, setup_flask_logging
from shared.models import UserProfile

logger = get_logger(__name__)

class NutritionBotWebhook:
    """Webhook версия Nutrition Bot для облачного деплоя"""
    
    def __init__(self):
        """Инициализация бота"""
        self._check_environment()
        
        # Инициализация адаптеров
        self.db = get_database_adapter()
        self.openai = OpenAIClient()
        
        # Инициализация сервисов
        self.photo_analyzer = PhotoAnalyzer(self.openai, self.db)
        self.nutrition_tracker = NutritionTracker(self.db)
        self.daily_planner = DailyPlanner(self.openai, self.db)
        self.daily_reporter = DailyReporter(self.openai, self.db)
        self.scheduler = Scheduler()
        
        # Настройка Telegram бота
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.webhook_url = os.getenv('WEBHOOK_URL', 'https://your-app.railway.app')
        self.port = int(os.getenv('PORT', 8000))
        
        # Создаем Telegram Application
        self.application = Application.builder().token(self.token).build()
        self._setup_handlers()
        
        # Flask приложение для webhook
        self.app = Flask(__name__)
        setup_flask_logging()  # Настраиваем логирование Flask
        self._setup_flask_routes()
        
        logger.info("✅ Nutrition Bot V2 (Webhook) инициализирован")
    
    def _check_environment(self):
        """Проверяет переменные окружения"""
        required_vars = ['TELEGRAM_BOT_TOKEN', 'OPENAI_API_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Отсутствуют переменные окружения: {', '.join(missing_vars)}")
        
        logger.info("✅ Переменные окружения найдены")
    
    def _setup_handlers(self):
        """Настройка обработчиков команд"""
        # Команды
        self.application.add_handler(CommandHandler("start", self.handle_start))
        self.application.add_handler(CommandHandler("daily_report", self.handle_daily_report))
        self.application.add_handler(CommandHandler("daily_plan", self.handle_daily_plan))
        self.application.add_handler(CommandHandler("stats", self.handle_stats))
        self.application.add_handler(CommandHandler("help", self.handle_help))
        
        # Обработка фотографий
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        
        # Обработка текстовых сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
    
    def _setup_flask_routes(self):
        """Настройка Flask маршрутов"""
        
        @self.app.route("/", methods=['GET'])
        def health_check():
            """Health check endpoint для Railway"""
            return {
                "status": "healthy",
                "service": "nutrition-bot-webhook",
                "timestamp": datetime.now().isoformat(),
                "version": "2.0"
            }
        
        @self.app.route("/webhook", methods=['POST'])
        def webhook():
            """Обработка webhook от Telegram"""
            try:
                json_data = request.get_json()
                if json_data:
                    update = Update.de_json(json_data, self.application.bot)
                    asyncio.run(self.application.process_update(update))
                return "OK"
            except Exception as e:
                logger.error(f"Ошибка обработки webhook: {e}")
                return "ERROR", 500
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        user = update.effective_user
        logger.info(f"Пользователь {user.id} начал работу с ботом")
        
        # Создаем или получаем пользователя
        await self.db.get_or_create_user(user.id, user.username, user.first_name)
        
        welcome_message = """
🍎 <b>Добро пожаловать в Nutrition Bot!</b>

Я помогу отслеживать вашу пищевую ценность:

📸 <b>Отправьте фото еды</b> - получите анализ калорий и макросов
📊 <b>/stats</b> - статистика за день и неделю  
📅 <b>/daily_plan</b> - план питания на сегодня
📋 <b>/daily_report</b> - отчет за день
❓ <b>/help</b> - помощь

<i>Просто отправьте фото вашей еды, и я проанализирую её пищевую ценность!</i>
"""
        
        await update.message.reply_text(welcome_message, parse_mode='HTML')
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка фотографий еды"""
        user_id = update.effective_user.id
        logger.info(f"Получена фотография от пользователя {user_id}")
        
        # Уведомляем о начале анализа
        processing_message = await update.message.reply_text(
            "🔍 <b>Анализирую фотографию...</b>\n\n"
            "⏳ Это может занять несколько секунд",
            parse_mode='HTML'
        )
        
        try:
            # Получаем файл
            photo = update.message.photo[-1]  # Берем фото лучшего качества
            file = await context.bot.get_file(photo.file_id)
            
            # Скачиваем в байты
            photo_bytes = await file.download_as_bytearray()
            
            # Анализируем фото
            analysis = await self.photo_analyzer.analyze_food_photo(user_id, photo_bytes)
            
            if analysis:
                # Форматируем результат
                result_message = self._format_analysis_result(analysis)
                
                # Обновляем сообщение
                await processing_message.edit_text(result_message, parse_mode='HTML')
                
                logger.info(f"Фотография пользователя {user_id} успешно проанализирована")
                
            else:
                await processing_message.edit_text(
                    "❌ <b>Не удалось проанализировать фотографию</b>\n\n"
                    "Попробуйте:\n"
                    "• Сделать фото при лучшем освещении\n"
                    "• Убедиться, что еда хорошо видна\n"
                    "• Отправить другое фото",
                    parse_mode='HTML'
                )
                
        except Exception as e:
            logger.error(f"Ошибка обработки фото: {e}")
            await processing_message.edit_text(
                "❌ <b>Произошла ошибка при анализе</b>\n\n"
                "Попробуйте отправить фото еще раз",
                parse_mode='HTML'
            )
    
    async def handle_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /stats"""
        user_id = update.effective_user.id
        
        # Получаем статистику
        daily_stats = await self.nutrition_tracker.get_daily_progress(user_id)
        weekly_stats = await self.nutrition_tracker.get_weekly_progress(user_id)
        
        message_parts = [
            "📊 <b>Ваша статистика питания</b>\n",
            "📅 <b>Сегодня:</b>",
            self._format_daily_stats(daily_stats),
            "\n📈 <b>За неделю:</b>",
            self._format_weekly_stats(weekly_stats)
        ]
        
        message = "\n".join(message_parts)
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def handle_daily_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /daily_report"""
        user_id = update.effective_user.id
        
        report = await self.daily_reporter.generate_daily_report(user_id)
        
        if report:
            message = f"📋 <b>Отчет за {report.date.strftime('%d.%m.%Y')}</b>\n\n{report.report_message}"
        else:
            message = "📋 <b>Отчет за сегодня</b>\n\nДанных для отчета пока недостаточно. Добавьте записи о приемах пищи!"
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def handle_daily_plan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /daily_plan"""
        user_id = update.effective_user.id
        
        plan = await self.daily_planner.generate_daily_plan(user_id)
        
        if plan:
            message = f"📅 <b>План на {plan.date.strftime('%d.%m.%Y')}</b>\n\n{plan.plan_message}"
        else:
            message = "📅 <b>План питания</b>\n\nНе удалось создать план. Попробуйте позже!"
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /help"""
        help_message = """
🍎 <b>Nutrition Bot - Помощь</b>

<b>Основные команды:</b>
📸 Отправьте фото еды - получите анализ калорий и макросов
📊 /stats - статистика за день и неделю
📅 /daily_plan - план питания на сегодня  
📋 /daily_report - отчет за день
❓ /help - эта помощь

<b>Как пользоваться:</b>
1. Сфотографируйте вашу еду
2. Отправьте фото боту
3. Получите детальный анализ пищевой ценности
4. Отслеживайте прогресс через /stats

<b>Советы для лучших результатов:</b>
• Фотографируйте при хорошем освещении
• Убедитесь, что еда хорошо видна
• Включайте в кадр всю порцию

<i>Бот использует ИИ для анализа, поэтому результаты могут незначительно отличаться от реальных значений.</i>
"""
        
        await update.message.reply_text(help_message, parse_mode='HTML')
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        await update.message.reply_text(
            "📸 Отправьте фото еды для анализа или используйте команды:\n"
            "/stats - статистика\n"
            "/help - помощь",
            parse_mode='HTML'
        )
    
    def _format_analysis_result(self, analysis):
        """Форматирует результат анализа"""
        confidence_emoji = "🎯" if analysis.confidence > 0.8 else "🎲" if analysis.confidence > 0.6 else "❓"
        
        message_lines = [
            f"{confidence_emoji} <b>Анализ завершен!</b>",
            "",
            f"🍽️ <b>Калории:</b> {analysis.total_calories:.0f} ккал",
            f"🥩 <b>Белки:</b> {analysis.total_protein:.1f} г", 
            f"🍞 <b>Углеводы:</b> {analysis.total_carbs:.1f} г",
            f"🧈 <b>Жиры:</b> {analysis.total_fat:.1f} г",
            f"🌾 <b>Клетчатка:</b> {analysis.total_fiber:.1f} г",
            ""
        ]
        
        # Добавляем специфичные нутриенты если есть
        if analysis.berries_grams > 0:
            message_lines.append(f"🫐 <b>Ягоды:</b> {analysis.berries_grams:.0f} г")
        if analysis.vegetables_grams > 0:
            message_lines.append(f"🥬 <b>Овощи:</b> {analysis.vegetables_grams:.0f} г")
        if analysis.nuts_grams > 0:
            message_lines.append(f"🥜 <b>Орехи:</b> {analysis.nuts_grams:.0f} г")
        
        if any([analysis.berries_grams, analysis.vegetables_grams, analysis.nuts_grams]):
            message_lines.append("")
        
        message_lines.extend([
            f"<i>{analysis.explanation}</i>",
            "",
            f"🎯 <b>Уверенность:</b> {analysis.confidence*100:.0f}%"
        ])
        
        return "\n".join(message_lines)
    
    def _format_daily_stats(self, stats):
        """Форматирует дневную статистику"""
        if not stats:
            return "📊 Данных за сегодня пока нет"
        
        return f"""🍽️ <b>Калории:</b> {stats.total_calories:.0f} ккал
🥩 <b>Белки:</b> {stats.total_protein:.1f} г  
🍞 <b>Углеводы:</b> {stats.total_carbs:.1f} г
🧈 <b>Жиры:</b> {stats.total_fat:.1f} г
🌾 <b>Клетчатка:</b> {stats.total_fiber:.1f} г"""
    
    def _format_weekly_stats(self, stats):
        """Форматирует недельную статистику"""
        if not stats:
            return "📈 Данных за неделю пока нет"
        
        return f"""📊 <b>Средние за день:</b> {stats.get('weekly_calories', 0)/7:.0f} ккал
🥬 <b>Овощи:</b> {stats.get('weekly_vegetables', 0):.0f} г
🫐 <b>Ягоды:</b> {stats.get('weekly_berries', 0):.0f} г
🥜 <b>Орехи:</b> {stats.get('weekly_nuts', 0):.0f} г"""

    async def init_database(self):
        """Инициализация базы данных"""
        await self.db.init_db()
    
    async def set_webhook(self):
        """Устанавливает webhook для Telegram"""
        webhook_url = f"{self.webhook_url}/webhook"
        
        try:
            await self.application.bot.set_webhook(webhook_url)
            logger.info(f"✅ Webhook установлен: {webhook_url}")
        except Exception as e:
            logger.error(f"❌ Ошибка установки webhook: {e}")
            raise
    
    def run(self):
        """Запуск webhook сервера"""
        try:
            # Инициализируем базу данных
            asyncio.run(self.init_database())
            
            # Устанавливаем webhook
            asyncio.run(self.set_webhook())
            
            logger.info(f"🚀 Запуск webhook сервера на порту {self.port}...")
            
            # Запускаем Flask сервер
            self.app.run(host='0.0.0.0', port=self.port, debug=False)
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска webhook сервера: {e}")
            raise

# Точка входа для Railway
def main():
    """Главная функция для webhook версии"""
    bot = NutritionBotWebhook()
    bot.run()

if __name__ == "__main__":
    main()
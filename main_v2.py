"""
Main V2: Современный Telegram бот с модульной архитектурой
"""
import asyncio
import os
from telegram import Update
from telegram.ext import ContextTypes

# Импорты адаптеров
from adapters.telegram_bot import TelegramBot
from adapters.openai_client import OpenAIClient  
from adapters.database import DatabaseAdapter

# Импорты сервисов
from services.photo_analyzer import PhotoAnalyzer
from services.nutrition_tracker import NutritionTracker
from services.daily_planner import DailyPlanner
from services.daily_reporter import DailyReporter
from services.scheduler import NotificationScheduler

# Логирование
from shared.logger import get_logger, LogCleaner

logger = get_logger(__name__)

class NutritionBotV2:
    """Современный бот с модульной архитектурой"""
    
    def __init__(self):
        logger.info("🚀 Инициализация Nutrition Bot V2...")
        
        # Инициализируем адаптеры
        self.telegram = TelegramBot()
        self.openai = OpenAIClient()
        self.db = DatabaseAdapter()
        
        # Инициализируем сервисы
        self.photo_analyzer = PhotoAnalyzer(self.openai)
        self.nutrition_tracker = NutritionTracker(self.db)
        self.daily_planner = DailyPlanner(self.openai, self.db)
        self.daily_reporter = DailyReporter(self.openai, self.db)
        self.scheduler = NotificationScheduler()
        
        # Настраиваем обработчики
        self._setup_handlers()
        
        logger.info("✅ Nutrition Bot V2 инициализирован")
    
    def _setup_handlers(self):
        """Настраивает обработчики команд и сообщений"""
        
        # Команды
        self.telegram.add_command_handler("start", self.handle_start)
        self.telegram.add_command_handler("stats", self.handle_stats)
        self.telegram.add_command_handler("plan", self.handle_plan)
        self.telegram.add_command_handler("report", self.handle_report)
        self.telegram.add_command_handler("help", self.handle_help)
        
        # Фотографии
        self.telegram.add_photo_handler(self.handle_photo)
        
        # Текстовые сообщения
        self.telegram.add_message_handler(self.handle_message)
        
        # Callback кнопки
        self.telegram.add_callback_handler(self.handle_callback)
        
        logger.info("Обработчики настроены")
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        try:
            user_info = self.telegram.get_user_info(update)
            user_id = user_info["user_id"]
            
            # Регистрируем пользователя
            await self.db.get_or_create_user(
                user_id=user_id,
                username=user_info["username"],
                first_name=user_info["first_name"]
            )
            
            welcome_text = f"""
🍎 Добро пожаловать в Nutrition Bot V2!

Привет, {user_info['first_name']}! 

Я помогу тебе:
🔍 Анализировать еду по фотографиям  
📊 Отслеживать калории и нутриенты
📈 Следить за выполнением норм питания
📅 Планировать рацион на день

📸 Просто отправь фото своей еды для анализа!

Команды:
/plan - План питания на сегодня
/stats - Статистика за день  
/report - Отчет за день
/help - Помощь
"""
            
            await self.telegram.send_message(
                chat_id=user_info["chat_id"],
                text=welcome_text
            )
            
            logger.info(f"Пользователь {user_id} начал работу с ботом")
            
        except Exception as e:
            logger.error(f"Ошибка в handle_start: {e}")
            await self._send_error_message(update, "Ошибка при запуске бота")
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик фотографий еды"""
        try:
            user_info = self.telegram.get_user_info(update)
            user_id = user_info["user_id"]
            chat_id = user_info["chat_id"]
            
            logger.info(f"Получена фотография от пользователя {user_id}")
            
            # Отправляем сообщение о начале анализа
            processing_msg = await self.telegram.send_message(
                chat_id=chat_id,
                text="🔄 Анализирую фотографию еды..."
            )
            
            # Получаем файл фотографии
            photo = update.message.photo[-1]  # Берем самое большое разрешение
            photo_bytes = await self.telegram.get_file_bytes(photo.file_id)
            
            if not photo_bytes:
                await self.telegram.edit_message(
                    chat_id=chat_id,
                    message_id=processing_msg.message_id,
                    text="❌ Ошибка при загрузке фотографии"
                )
                return
            
            # Анализируем фотографию (профессиональный метод)
            analysis_result = await self.photo_analyzer.analyze_food_photo_professional(photo_bytes, user_id)
            
            if not analysis_result:
                await self.telegram.edit_message(
                    chat_id=chat_id,
                    message_id=processing_msg.message_id,
                    text="❌ Не удалось проанализировать фотографию"
                )
                return
            
            # Сохраняем результат в БД
            saved = await self.nutrition_tracker.save_food_analysis(user_id, analysis_result)
            
            if not saved:
                await self.telegram.edit_message(
                    chat_id=chat_id,
                    message_id=processing_msg.message_id,
                    text="❌ Ошибка при сохранении данных"
                )
                return
            
            # Получаем прогресс по питанию
            progress = await self.nutrition_tracker.get_daily_progress(user_id)
            
            # Формируем ответ
            response_text = self._format_analysis_result(analysis_result, progress)
            
            # Создаем кнопки для дополнительных действий
            buttons = [
                [
                    {"text": "📊 Статистика дня", "callback_data": "stats_day"},
                    {"text": "📈 Прогресс недели", "callback_data": "stats_week"}
                ],
                [{"text": "📅 План на завтра", "callback_data": "plan_tomorrow"}]
            ]
            keyboard = self.telegram.create_inline_keyboard(buttons)
            
            # Обновляем сообщение с результатом
            await self.telegram.edit_message(
                chat_id=chat_id,
                message_id=processing_msg.message_id,
                text=response_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            
            logger.info(f"Фотография пользователя {user_id} успешно проанализирована")
            
        except Exception as e:
            logger.error(f"Ошибка в handle_photo: {e}")
            await self._send_error_message(update, "Ошибка при анализе фотографии")
    
    async def handle_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stats"""
        try:
            user_info = self.telegram.get_user_info(update)
            user_id = user_info["user_id"]
            
            progress = await self.nutrition_tracker.get_daily_progress(user_id)
            
            if not progress:
                await self.telegram.send_message(
                    chat_id=user_info["chat_id"],
                    text="📊 Данных за сегодня пока нет. Отправьте фото еды для анализа!"
                )
                return
            
            stats_text = self._format_daily_stats(progress)
            
            await self.telegram.send_message(
                chat_id=user_info["chat_id"],
                text=stats_text,
                parse_mode="HTML"
            )
            
        except Exception as e:
            logger.error(f"Ошибка в handle_stats: {e}")
            await self._send_error_message(update, "Ошибка при получении статистики")
    
    async def handle_plan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /plan"""
        try:
            user_info = self.telegram.get_user_info(update)
            user_id = user_info["user_id"]
            
            plan_message = await self.daily_planner.create_daily_plan(user_id)
            
            if not plan_message:
                plan_message = "📅 Не удалось создать план на сегодня. Попробуйте позже."
            
            await self.telegram.send_message(
                chat_id=user_info["chat_id"],
                text=plan_message,
                parse_mode="HTML"
            )
            
        except Exception as e:
            logger.error(f"Ошибка в handle_plan: {e}")
            await self._send_error_message(update, "Ошибка при создании плана")
    
    async def handle_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /report"""
        try:
            user_info = self.telegram.get_user_info(update)
            user_id = user_info["user_id"]
            
            report_message = await self.daily_reporter.generate_daily_report(user_id)
            
            if not report_message:
                report_message = "📈 Данных для отчета пока недостаточно."
            
            await self.telegram.send_message(
                chat_id=user_info["chat_id"],
                text=report_message,
                parse_mode="HTML"
            )
            
        except Exception as e:
            logger.error(f"Ошибка в handle_report: {e}")
            await self._send_error_message(update, "Ошибка при создании отчета")
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
🆘 <b>Помощь по Nutrition Bot V2</b>

<b>Основные команды:</b>
/start - Начать работу с ботом
/plan - Получить план питания на день
/stats - Статистика питания за день
/report - Подробный отчет за день
/help - Показать эту справку

<b>Как пользоваться:</b>
📸 Отправьте фото еды для анализа калорий и нутриентов
📊 Бот автоматически отслеживает ваш прогресс
📅 Каждое утро получайте персональный план питания
📈 Вечером - подробный отчет за день

<b>Что анализирует бот:</b>
• Калории и макронутриенты (белки, жиры, углеводы)
• Клетчатку и микронутриенты
• Соответствие недельным нормам питания
• Рекомендации по улучшению рациона

💡 <b>Совет:</b> Фотографируйте всю еду для точной статистики!
"""
        
        await self.telegram.send_message(
            chat_id=self.telegram.get_user_info(update)["chat_id"],
            text=help_text,
            parse_mode="HTML"
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        text = update.message.text.lower().strip()
        
        if any(word in text for word in ["привет", "hello", "hi", "здравствуй"]):
            await update.message.reply_text(
                "Привет! 👋 Отправьте фото еды для анализа или используйте /help для справки."
            )
        elif any(word in text for word in ["спасибо", "благодарю", "thanks"]):
            await update.message.reply_text("Пожалуйста! 😊 Рад помочь с питанием!")
        else:
            await update.message.reply_text(
                "📸 Отправьте фото еды для анализа или используйте команды /plan, /stats, /report"
            )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback кнопок"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_info = self.telegram.get_user_info(update)
            user_id = user_info["user_id"]
            
            if query.data == "stats_day":
                progress = await self.nutrition_tracker.get_daily_progress(user_id)
                if progress:
                    response = self._format_daily_stats(progress)
                else:
                    response = "📊 Данных за сегодня пока нет"
                    
                await query.edit_message_text(text=response, parse_mode="HTML")
                
            elif query.data == "stats_week":
                weekly_stats = await self.nutrition_tracker.get_weekly_progress(user_id)
                response = self._format_weekly_stats(weekly_stats)
                await query.edit_message_text(text=response, parse_mode="HTML")
                
            elif query.data == "plan_tomorrow":
                plan = await self.daily_planner.create_daily_plan(user_id)
                if plan:
                    await query.edit_message_text(text=plan, parse_mode="HTML")
                else:
                    await query.edit_message_text(text="❌ Не удалось создать план")
            
        except Exception as e:
            logger.error(f"Ошибка в handle_callback: {e}")
    
    def _format_analysis_result(self, analysis, progress):
        """Форматирует результат анализа еды (auto-detect format)"""
        # Проверяем, какой тип результата получили
        if hasattr(analysis, 'totals') and hasattr(analysis, 'items'):
            # Это ProfessionalFoodAnalysis - используем новый формат
            return self._format_professional_analysis(analysis, progress)
        else:
            # Это старый FoodAnalysisResult - используем legacy формат
            return self._format_legacy_analysis(analysis, progress)
    
    def _format_professional_analysis(self, analysis, progress):
        """Форматирует профессиональный результат анализа еды"""
        result_lines = [
            "✅ <b>Анализ завершен!</b>",
            f"🆔 <code>{analysis.meal_id}</code>",
            "",
        ]
        
        # Основные продукты (топ-3 по калориям)
        top_items = analysis.items[:3]
        if top_items:
            result_lines.append("🍽️ <b>Основные продукты:</b>")
            for item in top_items:
                result_lines.append(f"• {item.food} ({item.weight_g:.0f}г) - {item.kcal} ккал")
            result_lines.append("")
        
        # Общие нутриенты с процентами
        result_lines.extend([
            "📊 <b>Нутриенты:</b>",
            f"🔥 <b>Калории:</b> {analysis.totals.kcal} ккал ({analysis.percent_of_daily.kcal:.1f}%)",
            f"🥩 <b>Белки:</b> {analysis.totals.protein_g:.1f} г ({analysis.percent_of_daily.protein_g:.1f}%)",
            f"🍞 <b>Углеводы:</b> {analysis.totals.carb_g:.1f} г ({analysis.percent_of_daily.carb_g:.1f}%)",
            f"🧈 <b>Жиры:</b> {analysis.totals.fat_g:.1f} г ({analysis.percent_of_daily.fat_g:.1f}%)",
            f"🌾 <b>Клетчатка:</b> {analysis.totals.fiber_g:.1f} г ({analysis.percent_of_daily.fiber_g:.1f}%)",
        ])
        
        # Микронутриенты (если есть значительные количества)
        micronutrients = []
        if analysis.totals.calcium_mg > 50:
            micronutrients.append(f"🦴 Кальций: {analysis.totals.calcium_mg:.0f} мг ({analysis.percent_of_daily.calcium_mg:.1f}%)")
        if analysis.totals.iron_mg > 2:
            micronutrients.append(f"🩸 Железо: {analysis.totals.iron_mg:.1f} мг ({analysis.percent_of_daily.iron_mg:.1f}%)")
        if analysis.totals.omega3_g > 0.1:
            micronutrients.append(f"🐟 Омега-3: {analysis.totals.omega3_g:.1f} г ({analysis.percent_of_daily.omega3_g:.1f}%)")
        
        if micronutrients:
            result_lines.append("")
            result_lines.append("🧪 <b>Микронутриенты:</b>")
            result_lines.extend(micronutrients)
        
        # Прогресс за день (если есть)
        if progress:
            result_lines.extend([
                "",
                "📈 <b>Сегодня съедено:</b>",
                f"Всего калорий: {progress.total_calories:.0f} ккал",
                f"Всего клетчатки: {progress.total_fiber:.0f} г"
            ])
        
        return "\n".join(result_lines)
    
    def _format_legacy_analysis(self, analysis, progress):
        """Форматирует результат анализа еды (legacy format)"""
        result_lines = [
            "✅ <b>Анализ завершен!</b>",
            "",
            f"🍽️ <b>Калории:</b> {analysis.total_calories:.0f} ккал",
            f"🥩 <b>Белки:</b> {analysis.total_protein:.1f} г",
            f"🍞 <b>Углеводы:</b> {analysis.total_carbs:.1f} г", 
            f"🧈 <b>Жиры:</b> {analysis.total_fat:.1f} г",
            f"🌾 <b>Клетчатка:</b> {analysis.total_fiber:.1f} г",
        ]
        
        if analysis.berries_grams > 0:
            result_lines.append(f"🫐 <b>Ягоды:</b> {analysis.berries_grams:.0f} г")
        if analysis.vegetables_grams > 0:
            result_lines.append(f"🥬 <b>Овощи:</b> {analysis.vegetables_grams:.0f} г")
        if analysis.nuts_grams > 0:
            result_lines.append(f"🥜 <b>Орехи:</b> {analysis.nuts_grams:.0f} г")
        
        if progress:
            result_lines.extend([
                "",
                "📊 <b>Прогресс за день:</b>",
                f"Калории: {progress.total_calories:.0f} / 2200 ккал",
                f"Клетчатка: {progress.total_fiber:.0f} / 50 г"
            ])
        
        return "\n".join(result_lines)
    
    def _format_daily_stats(self, progress):
        """Форматирует дневную статистику"""
        if not progress:
            return "📊 Данных за сегодня пока нет"
        
        lines = [
            "📊 <b>Статистика за день</b>",
            "",
            f"🍽️ <b>Калории:</b> {progress.total_calories:.0f} ккал",
            f"🥩 <b>Белки:</b> {progress.total_protein:.1f} г",
            f"🍞 <b>Углеводы:</b> {progress.total_carbs:.1f} г",
            f"🧈 <b>Жиры:</b> {progress.total_fat:.1f} г",
            f"🌾 <b>Клетчатка:</b> {progress.total_fiber:.1f} г",
            "",
            f"🫐 <b>Ягоды:</b> {progress.berries_grams:.0f} г",
            f"🥬 <b>Овощи:</b> {progress.vegetables_grams:.0f} г",
            f"🥜 <b>Орехи:</b> {progress.nuts_grams:.0f} г"
        ]
        
        return "\n".join(lines)
    
    def _format_weekly_stats(self, stats):
        """Форматирует недельную статистику"""
        if not stats:
            return "📈 Данных за неделю пока нет"
        
        lines = [
            "📈 <b>Статистика за неделю</b>",
            "",
            f"🫐 <b>Ягоды:</b> {stats.get('weekly_berries', 0):.0f} / 175 г",
            f"🥩 <b>Красное мясо:</b> {stats.get('weekly_red_meat', 0):.0f} / 700 г",
            f"🐟 <b>Морепродукты:</b> {stats.get('weekly_seafood', 0):.0f} г",
            f"🥜 <b>Орехи:</b> {stats.get('weekly_nuts', 0):.0f} г",
            f"🥬 <b>Овощи:</b> {stats.get('weekly_vegetables', 0):.0f} г"
        ]
        
        return "\n".join(lines)
    
    async def _send_error_message(self, update: Update, error_text: str):
        """Отправляет сообщение об ошибке пользователю"""
        try:
            user_info = self.telegram.get_user_info(update)
            await self.telegram.send_message(
                chat_id=user_info["chat_id"],
                text=f"❌ {error_text}"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения об ошибке: {e}")
    
    async def initialize(self):
        """Инициализация всех компонентов"""
        try:
            logger.info("Инициализация компонентов...")
            
            # Инициализируем базу данных
            await self.db.init_db()
            
            # Запускаем автоочистку логов
            await LogCleaner.cleanup_old_logs()
            
            logger.info("✅ Все компоненты инициализированы")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации: {e}")
            raise
    
    def start(self):
        """Запуск бота"""
        try:
            logger.info("🚀 Запуск Nutrition Bot V2...")
            
            # Запускаем бота (синхронно) - он сам создаст event loop
            self.telegram.run_polling()
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            raise
    
    async def shutdown(self):
        """Корректное завершение работы"""
        try:
            logger.info("🛑 Завершение работы бота...")
            
            # Закрываем соединения
            await self.openai.close()
            await self.db.close()
            
            logger.info("✅ Бот корректно завершил работу")
            
        except Exception as e:
            logger.error(f"Ошибка при завершении работы: {e}")

# Точка входа
def main():
    """Главная функция запуска"""
    bot = NutritionBotV2()
    bot.start()

if __name__ == "__main__":
    main()
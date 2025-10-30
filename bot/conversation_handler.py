"""Обробник природних повідомлень через Gemini AI"""
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, date

from core.logger_settings import create_logger
from services.gemini_service import GeminiService
from core.analytics import AnalyticsService

logger = create_logger(__name__)


class ConversationHandler:
    """Обробник природної розмови з користувачами"""
    
    def __init__(self, gemini_service: GeminiService, analytics_service: AnalyticsService):
        """
        Ініціалізація обробника
        
        Args:
            gemini_service: Сервіс Gemini для AI відповідей
            analytics_service: Сервіс аналітики для контексту
        """
        self.gemini = gemini_service
        self.analytics = analytics_service
        logger.info("ConversationHandler ініціалізовано")
    
    def _is_report_message(self, text: str) -> bool:
        """
        Перевірити чи є повідомлення звітом
        
        Args:
            text: Текст повідомлення
            
        Returns:
            True якщо схоже на звіт
        """
        # Ключові слова що вказують на звіт
        report_keywords = [
            'звіт', 'статистика', 'результат', 'підсумок',
            'сьогодні', 'за день', 'за тиждень',
            'створено', 'оновлено', 'кандидат', 'дзвінк',
            'вакансія', 'інтервʼю', 'співбесіда'
        ]
        
        text_lower = text.lower()
        
        # Перевіряємо наявність ключових слів
        has_keywords = any(keyword in text_lower for keyword in report_keywords)
        
        # Перевіряємо наявність цифр (звіти зазвичай містять числа)
        has_numbers = any(char.isdigit() for char in text)
        
        # Перевіряємо чи є структура звіту (списки, статистика)
        has_structure = ('•' in text or '-' in text or '\n' in text) and has_numbers
        
        return has_keywords or has_structure
    
    async def _detect_command_intent(self, text: str) -> tuple[str, dict]:
        """
        Розпізнати намір команди з природного тексту через AI
        
        Args:
            text: Текст повідомлення
            
        Returns:
            Tuple (command_name, params) або (None, {})
        """
        try:
            # Використовуємо AI для розпізнавання команди
            ai_result = await self.gemini.detect_command_intent(text)
            
            # Перевіряємо впевненість AI
            if ai_result['command'] and ai_result['confidence'] >= 0.6:
                logger.info(
                    f"AI розпізнав команду '{ai_result['command']}' "
                    f"з впевненістю {ai_result['confidence']:.2f}: {ai_result['reasoning']}"
                )
                return (ai_result['command'], ai_result.get('params', {}))
            else:
                if ai_result['confidence'] > 0:
                    logger.debug(
                        f"AI впевненість занадто низька ({ai_result['confidence']:.2f}) "
                        f"для команди '{ai_result['command']}'"
                    )
                return (None, {})
                
        except Exception as e:
            logger.error(f"Помилка AI розпізнавання команди: {e}", exc_info=True)
            # Fallback до старого pattern matching при помилці AI
            return self._detect_command_intent_fallback(text)
    
    def _detect_command_intent_fallback(self, text: str) -> tuple[str, dict]:
        """
        Резервний метод розпізнавання команд (pattern matching)
        Використовується якщо AI не доступний
        
        Args:
            text: Текст повідомлення
            
        Returns:
            Tuple (command_name, params) або (None, {})
        """
        text_lower = text.lower().strip()
        
        # Звіт за сьогодні
        today_patterns = [
            'дай звіт за сьогодні',
            'дай звіт за день',
            'звіт за сьогодні',
            'покажи звіт за сьогодні',
            'статистика за сьогодні',
            'що сьогодні',
            'результати сьогодні',
            'дай статистику за сьогодні',
            'покажи статистику сьогодні'
        ]
        if any(pattern in text_lower for pattern in today_patterns):
            return ('today', {})
        
        # Звіт за вчора
        yesterday_patterns = [
            'дай звіт за вчора',
            'звіт за вчора',
            'покажи звіт за вчора',
            'статистика за вчора',
            'що вчора',
            'результати вчора'
        ]
        if any(pattern in text_lower for pattern in yesterday_patterns):
            return ('yesterday', {})
        
        # Аналітика по вакансіях
        vacancy_patterns = [
            'аналітика по вакансі',
            'статистика вакансі',
            'покажи вакансі',
            'дай аналітику',
            'аналіз вакансі',
            'вакансії статистика'
        ]
        if any(pattern in text_lower for pattern in vacancy_patterns):
            return ('vacancy_analytics', {})
        
        # Список вакансій
        list_patterns = [
            'список вакансій',
            'які вакансії',
            'покажи вакансії',
            'вакансії список'
        ]
        if any(pattern in text_lower for pattern in list_patterns):
            return ('vacancies', {})
        
        # Допомога
        help_patterns = [
            'допомога',
            'що ти вмієш',
            'які команди',
            'покажи команди',
            'як користуватись',
            'інструкція'
        ]
        if any(pattern in text_lower for pattern in help_patterns):
            return ('help', {})
        
        # Кеш інформація
        cache_patterns = [
            'стан кеш',
            'інформація про кеш',
            'кеш інфо'
        ]
        if any(pattern in text_lower for pattern in cache_patterns):
            return ('cache_info', {})
        
        # Очистити кеш
        clear_patterns = [
            'очисти кеш',
            'оновити дані',
            'перезавантажити',
            'скинь кеш'
        ]
        if any(pattern in text_lower for pattern in clear_patterns):
            return ('clear_cache', {})
        
        return (None, {})
    
    def _extract_context_from_message(self, text: str) -> dict:
        """
        Витягнути контекстну інформацію з повідомлення
        
        Args:
            text: Текст повідомлення
            
        Returns:
            Словник з контекстною інформацією
        """
        context = {
            'is_report': self._is_report_message(text),
            'has_numbers': any(char.isdigit() for char in text),
            'message_length': len(text),
            'current_date': date.today().strftime('%d.%m.%Y')
        }
        
        # Витягуємо згадки про вакансії
        text_lower = text.lower()
        if 'вакансі' in text_lower or 'позиці' in text_lower:
            context['mentions_vacancy'] = True
        
        # Витягуємо згадки про кандидатів
        if 'кандидат' in text_lower:
            context['mentions_candidates'] = True
        
        # Витягуємо згадки про дзвінки
        if 'дзвінк' in text_lower or 'телефон' in text_lower or 'зв\'яз' in text_lower:
            context['mentions_calls'] = True
        
        # Витягуємо згадки про етапи
        if any(stage in text_lower for stage in ['новий', 'інтервʼю', 'співбесіда', 'оффер', 'відмова']):
            context['mentions_stages'] = True
        
        return context
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обробити вхідне повідомлення
        
        Args:
            update: Telegram update
            context: Telegram context
        """
        try:
            message = update.message
            if not message or not message.text:
                return
            
            # Ігноруємо команди (вони обробляються окремо)
            if message.text.startswith('/'):
                return
            
            user = update.effective_user
            user_name = user.first_name or user.username or "Користувач"
            user_id = user.id
            text = message.text
            
            logger.info(f"Отримано повідомлення від {user_name} (ID: {user_id}): {text[:100]}...")
            
            # Перевіряємо чи це природна команда (await для асинхронного методу)
            command_name, params = await self._detect_command_intent(text)
            
            if command_name:
                logger.info(f"Розпізнано команду: {command_name} з повідомлення: '{text}'")
                
                # Виконуємо відповідну команду
                from bot.commands import (
                    today_command, 
                    yesterday_command, 
                    help_command,
                    cache_info_command,
                    clear_cache_command,
                    list_vacancies_command,
                    vacancy_analytics_command
                )
                
                command_map = {
                    'today': today_command,
                    'yesterday': yesterday_command,
                    'vacancy_analytics': vacancy_analytics_command,
                    'vacancies': list_vacancies_command,
                    'help': help_command,
                    'cache_info': cache_info_command,
                    'clear_cache': clear_cache_command,
                }
                
                command_func = command_map.get(command_name)
                if command_func:
                    await command_func(update, context)
                    return
            
            # Показуємо що бот друкує
            await message.chat.send_action(action="typing")
            
            # Витягуємо контекст з повідомлення
            msg_context = self._extract_context_from_message(text)
            
            # Визначаємо тип повідомлення та відповідаємо
            if msg_context['is_report']:
                # Це звіт - аналізуємо його
                logger.info(f"Повідомлення розпізнано як звіт від {user_name}")
                
                response = await self.gemini.analyze_report(
                    report_text=text,
                    user_name=user_name,
                    context_info=msg_context
                )
            else:
                # Звичайна розмова
                logger.info(f"Повідомлення розпізнано як розмова від {user_name}")
                
                response = await self.gemini.chat(
                    user_id=user_id,
                    user_name=user_name,
                    message=text,
                    context_info=msg_context
                )
            
            # Відправляємо відповідь
            await message.reply_text(response, parse_mode='Markdown')
            
            logger.info(f"Відправлено відповідь користувачу {user_name}")
            
        except Exception as e:
            logger.error(f"Помилка обробки повідомлення: {e}", exc_info=True)
            
            # Відправляємо дружню помилку
            try:
                await update.message.reply_text(
                    "Вибач, щось пішло не так 😅 Спробуй ще раз або звернись до адміністратора."
                )
            except Exception as send_error:
                logger.error(f"Не вдалося відправити повідомлення про помилку: {send_error}")
    
    async def handle_statistics_with_ai(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        stats_data: dict,
        period: str = "today"
    ):
        """
        Обробити статистику з AI коментарем
        
        Args:
            update: Telegram update
            context: Telegram context
            stats_data: Дані статистики
            period: Період статистики
        """
        try:
            user = update.effective_user
            user_name = user.first_name or user.username or "Користувач"
            
            # Показуємо що бот друкує
            await update.message.chat.send_action(action="typing")
            
            # Отримуємо AI аналіз
            ai_comment = await self.gemini.analyze_statistics(
                stats_data=stats_data,
                user_name=user_name,
                period=period
            )
            
            # Формуємо відповідь
            response = f"📊 <b>Аналіз статистики</b>\n\n{ai_comment}"
            
            await update.message.reply_html(response)
            
        except Exception as e:
            logger.error(f"Помилка обробки статистики з AI: {e}", exc_info=True)
    
    async def handle_greeting(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обробити привітання
        
        Args:
            update: Telegram update
            context: Telegram context
        """
        try:
            user = update.effective_user
            user_name = user.first_name or user.username or "Користувач"
            user_id = user.id
            
            # Очищаємо історію для свіжого початку
            self.gemini.clear_history(user_id)
            
            greeting_message = f"Привіт, {user_name}!"
            
            response = await self.gemini.chat(
                user_id=user_id,
                user_name=user_name,
                message=greeting_message,
                context_info={'is_greeting': True}
            )
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Помилка обробки привітання: {e}", exc_info=True)
            await update.message.reply_text(
                f"Привіт, {user.first_name}! 👋\n\n"
                "Я головний рекрутер. Можу допомогти з аналізом роботи, "
                "обговоренням кандидатів або відповісти на запитання про процеси найму."
            )

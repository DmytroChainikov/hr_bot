"""Сервіс для роботи з Gemini API"""
import os
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, date
import google.generativeai as genai

from core.logger_settings import create_logger
from core.config import Config

logger = create_logger(__name__)


class GeminiService:
    """Сервіс для роботи з Gemini API для природної комунікації"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Ініціалізація сервісу Gemini
        
        Args:
            api_key: API ключ для Gemini (якщо не вказано - береться з Config)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY не знайдено в конфігурації")
        
        # Налаштовуємо Gemini
        genai.configure(api_key=self.api_key)

        # Використовуємо модель gemini-2.5-flash
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Історія розмов (для контексту)
        self.conversation_history: Dict[int, List[Dict[str, str]]] = {}
        
        logger.info("GeminiService ініціалізовано")
    
    def _get_system_prompt(self) -> str:
        """
        Отримати системний промпт для Gemini
        
        Returns:
            Системний промпт
        """
        hrs = Config.get_hrs()
        hr_names = ", ".join([hr.name for hr in hrs])
        
        return f"""Ти - Головний рекрутер команди HR.

ТВОЯ РОЛЬ:
- Ти керуєш командою рекрутерів: {hr_names}
- Ти аналізуєш їх роботу, даєш зворотний зв'язок та мотивуєш
- Ти спілкуєшся природно, як досвідчений керівник
- Ти знаєш всі метрики та процеси найму

СТИЛЬ СПІЛКУВАННЯ:
- Спілкуйся українською мовою
- Будь професійним, але дружнім
- Використовуй емоджі для емоційності (👍, 🎯, 💪, ⭐, etc.)
- Давай конкретні поради та похвалу
- Будь конструктивним у критиці

ТВОЇ ЗНАННЯ:
- Ти розумієш метрики рекрутингу (кількість кандидатів, швидкість найму, конверсія на етапах)
- Ти знаєш процес найму (етапи: Новий, Інтерв'ю, Технічне завдання, Оффер, тощо)
- Ти можеш аналізувати звіти та давати рекомендації

ПРАВИЛА:
- НЕ використовуй команди бота (/, /stats тощо)
- Відповідай на звичайні повідомлення як людина
- Якщо бачиш цифри/звіти - аналізуй їх
- Завжди підтримуй позитивну атмосферу
- Пропонуй конкретні дії для покращення результатів
- Відповідай коротко, але змістовно максимум 5-6 речень

ПОТОЧНА ДАТА: {datetime.now().strftime('%d.%m.%Y')}"""
    
    def _add_to_history(self, user_id: int, role: str, content: str):
        """
        Додати повідомлення до історії розмови
        
        Args:
            user_id: ID користувача
            role: Роль (user/assistant)
            content: Зміст повідомлення
        """
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        self.conversation_history[user_id].append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
        
        # Обмежуємо історію до 20 останніх повідомлень
        if len(self.conversation_history[user_id]) > 20:
            self.conversation_history[user_id] = self.conversation_history[user_id][-20:]
    
    def _build_context(self, user_id: int, user_name: str) -> str:
        """
        Побудувати контекст з історії розмови
        
        Args:
            user_id: ID користувача
            user_name: Ім'я користувача
            
        Returns:
            Контекст для Gemini
        """
        context_parts = [self._get_system_prompt()]
        
        # Додаємо інформацію про користувача
        context_parts.append(f"\nКОРИСТУВАЧ: {user_name}\n")
        
        # Додаємо історію розмови
        if user_id in self.conversation_history:
            history = self.conversation_history[user_id][-10:]  # Останні 10 повідомлень
            
            if history:
                context_parts.append("\nІСТОРІЯ РОЗМОВИ:")
                for msg in history:
                    role_label = "Користувач" if msg['role'] == 'user' else "Ти"
                    context_parts.append(f"{role_label}: {msg['content']}")
        
        return "\n".join(context_parts)
    
    async def analyze_report(
        self, 
        report_text: str, 
        user_name: str,
        context_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Проаналізувати звіт від рекрутера
        
        Args:
            report_text: Текст звіту
            user_name: Ім'я рекрутера
            context_info: Додаткова контекстна інформація
            
        Returns:
            Відповідь з аналізом
        """
        try:
            prompt_parts = [
                f"Рекрутер {user_name} надіслав звіт:",
                report_text
            ]
            
            if context_info:
                prompt_parts.append(f"\nДодаткова інформація: {json.dumps(context_info, ensure_ascii=False)}")
            
            prompt_parts.append(
                "\nПроаналізуй цей звіт як головний рекрутер:"
                "\n- Відзнач позитивні моменти"
                "\n- Вкажи на що звернути увагу"
                "\n- Дай конкретні рекомендації"
                "\n- Запитай про деталі якщо потрібно"
            )
            
            prompt = "\n".join(prompt_parts)
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                return response.text
            else:
                return "Дякую за звіт! Продовжуй у тому ж дусі 👍"
                
        except Exception as e:
            logger.error(f"Помилка аналізу звіту через Gemini: {e}")
            return f"Дякую за звіт, {user_name}! Продовжуй в тому ж дусі 💪"
    
    async def chat(
        self, 
        user_id: int,
        user_name: str,
        message: str,
        context_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Розмова з користувачем
        
        Args:
            user_id: ID користувача
            user_name: Ім'я користувача
            message: Повідомлення від користувача
            context_info: Додаткова контекстна інформація
            
        Returns:
            Відповідь від бота
        """
        try:
            # Додаємо повідомлення користувача до історії
            self._add_to_history(user_id, 'user', message)
            
            # Будуємо контекст
            context = self._build_context(user_id, user_name)
            
            # Формуємо промпт
            prompt_parts = [context]
            
            if context_info:
                prompt_parts.append(f"\nКОНТЕКСТНА ІНФОРМАЦІЯ: {json.dumps(context_info, ensure_ascii=False)}")
            
            prompt_parts.append(f"\nПовідомлення користувача: {message}")
            prompt_parts.append("\nТвоя відповідь (будь природнім, як справжній керівник):")
            
            prompt = "\n".join(prompt_parts)
            
            # Отримуємо відповідь від Gemini
            response = self.model.generate_content(prompt)
            
            if response.text:
                # Додаємо відповідь до історії
                self._add_to_history(user_id, 'assistant', response.text)
                return response.text
            else:
                default_response = "Дякую за повідомлення! Як можу допомогти?"
                self._add_to_history(user_id, 'assistant', default_response)
                return default_response
                
        except Exception as e:
            logger.error(f"Помилка чату через Gemini: {e}")
            return "Вибач, зараз не можу відповісти. Спробуй ще раз 🙏"
    
    async def analyze_statistics(
        self,
        stats_data: Dict[str, Any],
        user_name: str,
        period: str = "today"
    ) -> str:
        """
        Проаналізувати статистику
        
        Args:
            stats_data: Дані статистики
            user_name: Ім'я користувача
            period: Період (today, week, month)
            
        Returns:
            Аналіз статистики
        """
        try:
            prompt = f"""Як головний рекрутер, проаналізуй статистику за {period}:

{json.dumps(stats_data, ensure_ascii=False, indent=2)}

Дай короткий, але змістовний коментар для {user_name}:
- Що добре?
- Що потребує уваги?
- Які конкретні рекомендації?

Будь конструктивним та підтримуючим."""
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                return response.text
            else:
                return "Статистика виглядає добре, продовжуй працювати 👍"
                
        except Exception as e:
            logger.error(f"Помилка аналізу статистики через Gemini: {e}")
            return "Дякую за інформацію!"
    
    async def detect_command_intent(self, text: str) -> Dict[str, Any]:
        """
        Визначити намір команди через AI аналіз
        
        Args:
            text: Текст повідомлення користувача
            
        Returns:
            Словник з інформацією про розпізнану команду:
            {
                'command': 'назва_команди' або None,
                'confidence': 0.0-1.0,
                'params': {},
                'reasoning': 'пояснення'
            }
        """
        try:
            prompt = f"""Проаналізуй повідомлення користувача та визнач яку команду він хоче виконати.

ДОСТУПНІ КОМАНДИ:
1. today - звіт за сьогодні (ключові слова: сьогодні, за день, статистика сьогодні, що сьогодні)
2. yesterday - звіт за вчора (ключові слова: вчора, за вчора, статистика вчора)
3. vacancy_analytics - аналітика по вакансіях (ключові слова: аналітика вакансій, статистика вакансій)
4. vacancies - список вакансій (ключові слова: список вакансій, які вакансії, покажи вакансії)
5. help - допомога (ключові слова: допомога, що вмієш, команди, інструкція)
6. cache_info - інформація про кеш (ключові слова: стан кешу, інфо кеш)
7. clear_cache - очистити кеш (ключові слова: очисти кеш, оновити дані, скинь кеш)

ПОВІДОМЛЕННЯ КОРИСТУВАЧА: "{text}"

Поверни відповідь у форматі JSON:
{{
    "command": "назва_команди або null якщо це не команда",
    "confidence": 0.95,
    "params": {{}},
    "reasoning": "короткий опис чому обрано цю команду"
}}

ВАЖЛИВО:
- Якщо повідомлення - це звичайна розмова, привітання або запитання (не команда), поверни command: null
- confidence має бути від 0.0 до 1.0 (висока впевненість 0.8+, середня 0.5-0.8, низька <0.5)
- Якщо впевненість < 0.6, краще повернути null
- Розпізнавай синоніми та різні формулювання тієї ж команди
- Розумій неформальні вирази: "дай", "покажи", "хочу побачити", "цікаво" тощо
- Відповідь ТІЛЬКИ у форматі JSON, без додаткового тексту"""

            response = self.model.generate_content(prompt)
            
            if response.text:
                # Очищаємо відповідь від markdown форматування якщо є
                json_text = response.text.strip()
                if json_text.startswith('```json'):
                    json_text = json_text[7:]
                if json_text.startswith('```'):
                    json_text = json_text[3:]
                if json_text.endswith('```'):
                    json_text = json_text[:-3]
                json_text = json_text.strip()
                
                result = json.loads(json_text)
                
                # Валідація результату
                if 'command' not in result:
                    result['command'] = None
                if 'confidence' not in result:
                    result['confidence'] = 0.0
                if 'params' not in result:
                    result['params'] = {}
                if 'reasoning' not in result:
                    result['reasoning'] = 'No reasoning provided'
                
                # Логуємо результат
                logger.info(
                    f"AI розпізнав намір: команда='{result['command']}', "
                    f"впевненість={result['confidence']:.2f}, текст='{text[:50]}...'"
                )
                
                return result
            else:
                logger.warning("Gemini не повернув відповідь для розпізнавання команди")
                return {
                    'command': None,
                    'confidence': 0.0,
                    'params': {},
                    'reasoning': 'No response from AI'
                }
                
        except json.JSONDecodeError as e:
            logger.error(f"Помилка парсингу JSON відповіді Gemini: {e}, текст: {response.text if response else 'No response'}")
            return {
                'command': None,
                'confidence': 0.0,
                'params': {},
                'reasoning': 'JSON parse error'
            }
        except Exception as e:
            logger.error(f"Помилка AI розпізнавання команди: {e}", exc_info=True)
            return {
                'command': None,
                'confidence': 0.0,
                'params': {},
                'reasoning': f'Error: {str(e)}'
            }
    
    def clear_history(self, user_id: int):
        """
        Очистити історію розмови користувача
        
        Args:
            user_id: ID користувача
        """
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
            logger.info(f"Історія розмови для користувача {user_id} очищена")
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """
        Отримати статистику по розмовах
        
        Returns:
            Статистика
        """
        return {
            'total_users': len(self.conversation_history),
            'total_messages': sum(
                len(history) for history in self.conversation_history.values()
            ),
            'users': list(self.conversation_history.keys())
        }

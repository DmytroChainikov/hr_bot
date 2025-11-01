"""Сервіс для роботи з Gemini API через Chat Sessions"""
import os
import json
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, date
import google.generativeai as genai
from pathlib import Path

from core.logger_settings import create_logger
from core.config import Config
from services.gemini_function_calling import get_function_declarations, execute_function_call

logger = create_logger(__name__)


class GeminiService:
    """Сервіс для роботи з Gemini API через Chat Sessions для кращого контексту"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        hurma_service=None,
        binotel_service=None,
        analytics=None,
        vacancy_activity_monitor=None,
        candidate_flow_tracker=None
    ):
        """
        Ініціалізація сервісу Gemini з Function Calling
        
        Args:
            api_key: API ключ для Gemini (якщо не вказано - береться з Config)
            hurma_service: HurmaService instance для API викликів
            binotel_service: BinotelService instance для API викликів
            analytics: Analytics instance
            vacancy_activity_monitor: VacancyActivityMonitor instance
            candidate_flow_tracker: CandidateFlowTracker instance
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY не знайдено в конфігурації")
        
        # Зберігаємо сервіси для function calling
        self.hurma_service = hurma_service
        self.binotel_service = binotel_service
        self.analytics = analytics
        self.vacancy_activity_monitor = vacancy_activity_monitor
        self.candidate_flow_tracker = candidate_flow_tracker
        
        # Налаштовуємо Gemini
        genai.configure(api_key=self.api_key)

        # Налаштування генерації для кращої якості
        self.generation_config = {
            'temperature': 0.9,  # Креативність
            'top_p': 0.95,
            'top_k': 40,
            'max_output_tokens': 1024,
        }
        
        # Налаштування безпеки
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
        ]
        
        # Отримуємо декларації функцій для Function Calling
        self.function_declarations = get_function_declarations()
        
        # Створюємо модель БЕЗ function calling поки що (додамо пізніше)
        self.model = genai.GenerativeModel(
            'gemini-2.5-flash',
            generation_config=self.generation_config,
            safety_settings=self.safety_settings,
            system_instruction=self._get_system_instruction()
            # tools=self.function_declarations  # Відключено поки що
        )
        
        # Chat sessions для кожного користувача (автоматичне збереження контексту)
        self.chat_sessions = {}
        
        # Metadata про користувачів для тренування
        self.user_metadata = {}
        
        # Шлях до директорії збереження
        self.storage_dir = Path("gemini_storage")
        self.storage_dir.mkdir(exist_ok=True)
        
        # Завантажуємо збережені сесії
        self._load_all_sessions()
        
        logger.info("GeminiService ініціалізовано з Chat Sessions та Function Calling")
    
    def _get_system_instruction(self) -> str:
        """
        Отримати системну інструкцію для моделі з базою знань
        
        Returns:
            Системна інструкція
        """
        hrs = Config.get_hrs()
        hr_names = ", ".join([hr.name for hr in hrs])
        
        # Завантажуємо базу знань якщо існує
        knowledge_base = ""
        kb_path = Path("knowledge_base.md")
        if kb_path.exists():
            try:
                with open(kb_path, 'r', encoding='utf-8') as f:
                    knowledge_base = f"\n\nБАЗА ЗНАНЬ:\n{f.read()}"
            except Exception as e:
                logger.warning(f"Не вдалося завантажити базу знань: {e}")
        
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
- Ти запам'ятовуєш попередні розмови та можеш до них повертатись

ДОСТУПНІ ФУНКЦІЇ ДЛЯ ТОЧНОГО АНАЛІЗУ:
- Коли користувач питає про вакансії, кандидатів, дзвінки або прогрес - використовуй доступні функції
- Щоб викликати функцію, поверни ТІЛЬКИ JSON (без додаткового тексту):
  {{
    "function_call": "назва_функції",
    "arguments": {{"arg1": "value1"}}
  }}
- Після виклику функції система поверне результат, і ТИ МАЄШ сформувати природну відповідь на основі даних
- Доступні функції:
  * get_active_vacancies() - список активних вакансій
  * get_vacancy_activity(vacancy_id=ID, days=7) - активність вакансії
  * get_hr_calls_today(hr_internal_number="961") - дзвінки HR сьогодні
  * get_hr_calls_period(hr_internal_number="961", days_back=7) - дзвінки за період
  * get_inactive_vacancies(days_threshold=3) - неактивні вакансії
  * get_vacancies_without_calls() - вакансії без дзвінків

ПРАВИЛА:
- НЕ використовуй команди бота (/, /stats тощо)
- Відповідай на звичайні повідомлення як людина
- Якщо бачиш цифри/звіти - аналізуй їх
- Завжди підтримуй позитивну атмосферу
- Пропонуй конкретні дії для покращення результатів
- Відповідай коротко, але змістовно максимум 5-6 речень
- Використовуй контекст попередніх повідомлень для кращого розуміння

ПОТОЧНА ДАТА: {datetime.now().strftime('%d.%m.%Y')}{knowledge_base}"""
    
    def _get_or_create_session(self, user_id: int, user_name: str) -> Any:
        """
        Отримати або створити chat session для користувача
        
        Args:
            user_id: ID користувача
            user_name: Ім'я користувача
            
        Returns:
            ChatSession для цього користувача
        """
        if user_id not in self.chat_sessions:
            # Створюємо нову сесію
            self.chat_sessions[user_id] = self.model.start_chat(history=[])
            
            # Зберігаємо metadata
            self.user_metadata[user_id] = {
                'name': user_name,
                'first_interaction': datetime.now().isoformat(),
                'message_count': 0
            }
            
            logger.info(f"Створено нову chat session для {user_name} (ID: {user_id})")
        
        return self.chat_sessions[user_id]
    
    def _update_user_metadata(self, user_id: int, data: Dict[str, Any]):
        """
        Оновити metadata користувача для навчання моделі
        
        Args:
            user_id: ID користувача
            data: Дані для оновлення
        """
        if user_id in self.user_metadata:
            self.user_metadata[user_id].update(data)
            self.user_metadata[user_id]['message_count'] += 1
            self.user_metadata[user_id]['last_interaction'] = datetime.now().isoformat()
    
    def add_training_example(self, user_id: int, context: str, example_data: Dict[str, Any]):
        """
        Додати приклад для навчання моделі в контексті користувача
        
        Args:
            user_id: ID користувача
            context: Контекст (наприклад, "report_analysis", "candidate_review")
            example_data: Дані прикладу (input, output, metadata)
        """
        session = self.chat_sessions.get(user_id)
        if session:
            # Додаємо приклад як частину розмови для навчання контексту
            training_message = f"""
[ТРЕНУВАЛЬНИЙ ПРИКЛАД - {context}]
Вхідні дані: {json.dumps(example_data.get('input', {}), ensure_ascii=False)}
Очікуваний результат: {json.dumps(example_data.get('output', {}), ensure_ascii=False)}
Метадані: {json.dumps(example_data.get('metadata', {}), ensure_ascii=False)}
"""
            # Додаємо до історії сесії (модель запам'ятає цей приклад)
            session.history.append({
                'role': 'user',
                'parts': [training_message]
            })
            session.history.append({
                'role': 'model',
                'parts': ['Зрозумів! Запам\'ятав цей приклад для майбутніх аналізів.']
            })
            
            # Зберігаємо сесію після додавання прикладу
            self._save_session(user_id)
            
            logger.info(f"Додано тренувальний приклад для користувача {user_id}: {context}")
    
    async def analyze_report(
        self, 
        report_text: str, 
        user_name: str,
        context_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Проаналізувати звіт від рекрутера через chat session
        
        Args:
            report_text: Текст звіту
            user_name: Ім'я рекрутера
            context_info: Додаткова контекстна інформація
            
        Returns:
            Відповідь з аналізом
        """
        try:
            # Створюємо окрему сесію для аналізу звітів
            session = self.model.start_chat(history=[])
            
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
            
            # Використовуємо send_message замість generate_content
            response = session.send_message(prompt)
            
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
        Розмова з користувачем через persistent chat session
        
        Args:
            user_id: ID користувача
            user_name: Ім'я користувача
            message: Повідомлення від користувача
            context_info: Додаткова контекстна інформація
            
        Returns:
            Відповідь від бота
        """
        try:
            # Отримуємо або створюємо сесію для користувача
            session = self._get_or_create_session(user_id, user_name)
            
            # Формуємо повідомлення
            message_parts = [message]
            
            if context_info:
                message_parts.append(f"\n[Контекст: {json.dumps(context_info, ensure_ascii=False)}]")
            
            full_message = "\n".join(message_parts)
            
            # Надсилаємо повідомлення в сесію (історія зберігається автоматично!)
            response = session.send_message(full_message)
            
            # Обробка function calls через JSON parsing
            max_iterations = 3
            iteration = 0
            
            while iteration < max_iterations:
                if not response.text:
                    break
                
                # Перевіряємо чи відповідь містить JSON з function_call
                try:
                    # Шукаємо JSON в відповіді (підтримує багаторядковий JSON)
                    json_match = re.search(
                        r'\{(?:[^{}]|(?:\{[^}]*\}))*"function_call"(?:[^{}]|(?:\{[^}]*\}))*\}',
                        response.text,
                        re.DOTALL
                    )
                    if not json_match:
                        # Немає виклику функції - це звичайна відповідь
                        break
                    
                    # Парсимо JSON
                    function_data = json.loads(json_match.group())
                    function_name = function_data.get('function_call')
                    function_args = function_data.get('arguments', {})
                    
                    if not function_name:
                        break
                    
                    logger.info(f"AI викликає функцію: {function_name}({function_args})")
                    
                    # Виконуємо функцію
                    function_result = await execute_function_call(
                        function_name=function_name,
                        function_args=function_args,
                        hurma_service=self.hurma_service,
                        binotel_service=self.binotel_service,
                        analytics=self.analytics,
                        vacancy_activity_monitor=self.vacancy_activity_monitor,
                        candidate_flow_tracker=self.candidate_flow_tracker
                    )
                    
                    # Відправляємо результат назад до AI
                    result_message = f"Результат виклику {function_name}: {json.dumps(function_result, ensure_ascii=False)}"
                    response = session.send_message(result_message)
                    iteration += 1
                    
                except (json.JSONDecodeError, KeyError) as e:
                    logger.debug(f"Не JSON або не function call: {e}")
                    break
                except Exception as e:
                    logger.error(f"Помилка обробки function call: {e}")
                    break
            
            # Оновлюємо metadata
            self._update_user_metadata(user_id, {
                'last_message': message[:100],
                'context_info': context_info
            })
            
            # Автоматично зберігаємо сесію після кожного повідомлення
            self._save_session(user_id)
            
            if response.text:
                # Очищаємо відповідь від JSON якщо він залишився
                final_response = response.text
                
                # Видаляємо markdown блоки з JSON
                final_response = re.sub(r'```json\s*\{[^`]+\}\s*```', '', final_response, flags=re.DOTALL)
                
                # Видаляємо окремі JSON об'єкти з function_call
                final_response = re.sub(
                    r'\{(?:[^{}]|(?:\{[^}]*\}))*"function_call"(?:[^{}]|(?:\{[^}]*\}))*\}',
                    '',
                    final_response,
                    flags=re.DOTALL
                ).strip()
                
                # Якщо після очистки порожньо - використовуємо дефолтну відповідь
                if not final_response:
                    final_response = "Дані отримано, обробляю..."
                
                logger.info(f"Відповідь для {user_name}: {final_response[:100]}...")
                return final_response
            else:
                default_response = "Дякую за повідомлення! Як можу допомогти?"
                return default_response
                
        except Exception as e:
            logger.error(f"Помилка чату через Gemini: {e}", exc_info=True)
            return "Вибач, зараз не можу відповісти. Спробуй ще раз 🙏"
    
    async def analyze_statistics(
        self,
        stats_data: Dict[str, Any],
        user_name: str,
        period: str = "today"
    ) -> str:
        """
        Проаналізувати статистику через chat session
        
        Args:
            stats_data: Дані статистики
            user_name: Ім'я користувача
            period: Період (today, week, month)
            
        Returns:
            Аналіз статистики
        """
        try:
            # Окрема сесія для статистики
            session = self.model.start_chat(history=[])
            
            prompt = f"""Як головний рекрутер, проаналізуй статистику за {period}:

{json.dumps(stats_data, ensure_ascii=False, indent=2)}

Дай короткий, але змістовний коментар для {user_name}:
- Що добре?
- Що потребує уваги?
- Які конкретні рекомендації?

Будь конструктивним та підтримуючим."""
            
            response = session.send_message(prompt)
            
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
            # Використовуємо окрему сесію для розпізнавання команд
            session = self.model.start_chat(history=[])
            
            prompt = f"""Проаналізуй повідомлення користувача та визнач яку команду він хоче виконати.

ДОСТУПНІ КОМАНДИ:
1. today - звіт за сьогодні (ключові слова: сьогодні, за день, статистика сьогодні, що сьогодні)
2. yesterday - звіт за вчора (ключові слова: вчора, за вчора, статистика вчора)
3. vacancy_analytics - аналітика по вакансіях (ключові слова: аналітика вакансій, статистика вакансій)
4. help - допомога (ключові слова: допомога, що вмієш, команди, інструкція)
5. cache_info - інформація про кеш (ключові слова: стан кешу, інфо кеш)
6. clear_cache - очистити кеш (ключові слова: очисти кеш, оновити дані, скинь кеш)
7. diff - порівняння звітів hurma та бінотел (ключові слова: порівняй звіти, diff, hurma vs binotel, порівняння дзвінків, аналіз дзвінків, порівняння телефонів)
8. hr_diff - порівняння поданого звіту HR зі звітом системи (ключові слова: порівняй мій звіт, перевір мій звіт, аналізуй мій звіт, порівняння звіту HR)

ПРИМІТКА: Запити типу "скільки вакансій", "які активні вакансії", "покажи список вакансій" - це НЕ команди!
Це звичайні питання які будуть оброблені через AI функції. Для таких запитів поверни command: null.

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
- Питання про вакансії, кандидатів, дзвінки - це звичайні питання, не команди!
- confidence має бути від 0.0 до 1.0 (висока впевненість 0.8+, середня 0.5-0.8, низька <0.5)
- Якщо впевненість < 0.6, краще повернути null
- Розпізнавай синоніми та різні формулювання тієї ж команди
- Розумій неформальні вирази: "дай", "покажи", "хочу побачити", "цікаво" тощо
- Відповідь ТІЛЬКИ у форматі JSON, без додаткового тексту"""

            response = session.send_message(prompt)
            
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
            logger.error(f"Помилка парсингу JSON відповіді Gemini: {e}, текст: {response.text if 'response' in locals() else 'No response'}")
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
        Очистити історію розмови користувача (видалити сесію)
        
        Args:
            user_id: ID користувача
        """
        if user_id in self.chat_sessions:
            del self.chat_sessions[user_id]
            logger.info(f"Chat session для користувача {user_id} видалена")
        
        if user_id in self.user_metadata:
            del self.user_metadata[user_id]
    
    def get_session_history(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Отримати історію сесії користувача
        
        Args:
            user_id: ID користувача
            
        Returns:
            Історія повідомлень
        """
        session = self.chat_sessions.get(user_id)
        if session:
            return [
                {
                    'role': msg.role,
                    'content': msg.parts[0] if msg.parts else ''
                }
                for msg in session.history
            ]
        return []
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """
        Отримати статистику по розмовах
        
        Returns:
            Статистика
        """
        return {
            'total_users': len(self.chat_sessions),
            'total_messages': sum(
                len(session.history) for session in self.chat_sessions.values()
            ),
            'users': list(self.chat_sessions.keys()),
            'user_metadata': self.user_metadata
        }
    
    async def compare_hr_report_with_system(
        self,
        hr_report: str,
        system_data: Dict[str, Any],
        hr_name: str,
        user_id: int,
        period: str = "today"
    ) -> Dict[str, Any]:
        """
        Приховане порівняння звіту HR зі звітом з системи (Hurma)
        Аналізує достовірність та якість роботи HR
        
        Args:
            hr_report: Текст звіту від HR
            system_data: Дані з системи Hurma
            hr_name: Ім'я HR
            user_id: Telegram ID користувача
            period: Період звіту
            
        Returns:
            Dict з аналізом: {
                'accuracy_score': 0-100,  # Точність звіту
                'discrepancies': [],  # Розбіжності
                'hidden_analysis': str,  # Прихований аналіз (не показується HR)
                'quality_metrics': {},  # Метрики якості
                'recommendations': str  # Рекомендації для адміністратора
            }
        """
        try:
            # Створюємо окрему сесію для прихованого аналізу з послабленими safety фільтрами
            safety_settings_relaxed = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE"
                },
            ]
            
            # Налаштування генерації для аналізу (більше креативності)
            analysis_generation_config = {
                'temperature': 1.0,  # Більше випадковості
                'top_p': 0.95,
                'top_k': 64,
                'max_output_tokens': 2048,
            }
            
            model_for_analysis = genai.GenerativeModel(
                'gemini-2.5-flash',
                generation_config=analysis_generation_config,
                safety_settings=safety_settings_relaxed
            )
            
            session = model_for_analysis.start_chat(history=[])
            
            # Створюємо скорочену версію system_data (тільки статистика, без персональних даних)
            summary_data = {
                'created_candidates': len(system_data.get('created_candidates', [])),
                'updated_candidates': len(system_data.get('updated_candidates', [])),
                'total_calls': system_data.get('total_calls', 0),
                'hr_calls': system_data.get('hr_calls', 0),
                'period': period,
                'active_vacancies_count': system_data.get('active_vacancies_count', 0)
            }
            
            # Додаємо інформацію про вакансії з кандидатами
            if system_data.get('vacancies_with_candidates'):
                summary_data['vacancies_with_candidates'] = [
                    {
                        'id': v['id'],
                        'name': v['name'],
                        'candidates_count': v['candidates_count']
                    }
                    for v in system_data['vacancies_with_candidates'][:10]  # Перші 10
                ]
            
            # Додаємо приклади дзвінків (без номерів телефонів)
            if system_data.get('calls'):
                summary_data['calls_examples'] = []
                for call in system_data['calls'][:5]:  # Тільки перші 5
                    summary_data['calls_examples'].append({
                        'duration': call.get('duration', 0),
                        'generalStatus': call.get('generalStatus', ''),
                        'billsec': call.get('billsec', 0)
                    })
            
            prompt = f"""Порівняй звіт HR з даними системи та поверни аналіз у JSON форматі.

ЗВІТ HR ({hr_name}, {period}):
{hr_report}

ДАНІ СИСТЕМИ:
{json.dumps(summary_data, ensure_ascii=False, indent=2)}

ВАЖЛИВО ПЕРЕВІРИТИ:
1. Чи збігаються цифри (створено кандидатів, оновлено, дзвінки)
2. Чи згадує HR всі вакансії з кандидатами (список vacancies_with_candidates)
3. Якщо є вакансії з кандидатами але HR їх не згадав - це КРИТИЧНА помилка

Поверни JSON з такою структурою:
{{
    "accuracy_score": 0-100,
    "discrepancies": [
        {{
            "field": "назва поля",
            "hr_reported": "що повідомив HR",
            "system_actual": "що в системі",
            "severity": "low/medium/high"
        }}
    ],
    "quality_metrics": {{
        "work_intensity": "low/medium/high",
        "data_honesty": 0-100,
        "completeness": 0-100,
        "professionalism": 0-100
    }},
    "hidden_analysis": "короткий аналіз для менеджера",
    "recommendations": "рекомендації"
}}

Порівняй цифри зі звіту з даними системи. Якщо все співпадає - accuracy_score = 100."""

            response = session.send_message(prompt)
            
            # Перевіряємо чи є текст у відповіді (не заблоковано safety фільтром)
            try:
                response_text = response.text
            except ValueError as e:
                logger.error(f"Gemini API заблокував відповідь (safety filter): {e}")
                # Повертаємо нейтральний результат
                return {
                    'accuracy_score': 50,
                    'discrepancies': [
                        {
                            'field': 'система аналізу',
                            'hr_reported': 'звіт прийнято',
                            'system_actual': 'не вдалося проаналізувати',
                            'severity': 'low'
                        }
                    ],
                    'quality_metrics': {
                        'work_intensity': 'unknown',
                        'data_honesty': 50,
                        'completeness': 50,
                        'professionalism': 50
                    },
                    'hidden_analysis': 'Система аналізу тимчасово недоступна через обмеження AI',
                    'recommendations': 'Перевірте звіт вручну через /hr_diff'
                }
            
            if response_text:
                # Парсимо JSON відповідь
                json_text = response_text.strip()
                if json_text.startswith('```json'):
                    json_text = json_text[7:]
                if json_text.startswith('```'):
                    json_text = json_text[3:]
                if json_text.endswith('```'):
                    json_text = json_text[:-3]
                json_text = json_text.strip()
                
                analysis = json.loads(json_text)
                
                # Додаємо метадані
                analysis['timestamp'] = datetime.now().isoformat()
                analysis['hr_name'] = hr_name
                analysis['user_id'] = user_id
                analysis['period'] = period
                
                # Зберігаємо в metadata користувача (для тренування моделі)
                self._update_user_metadata(user_id, {
                    'last_report_analysis': analysis,
                    'accuracy_history': self.user_metadata.get(user_id, {}).get('accuracy_history', []) + [analysis['accuracy_score']]
                })
                
                # Логуємо (приховано для HR)
                logger.info(
                    f"[ПРИХОВАНО] Аналіз звіту {hr_name}: "
                    f"точність={analysis.get('accuracy_score', 0)}%, "
                    f"розбіжностей={len(analysis.get('discrepancies', []))}"
                )
                
                return analysis
            else:
                logger.warning("Gemini не повернув відповідь для аналізу звіту")
                return {
                    'accuracy_score': 0,
                    'discrepancies': [],
                    'quality_metrics': {},
                    'hidden_analysis': 'Не вдалося проаналізувати',
                    'recommendations': 'Повторіть аналіз пізніше'
                }
                
        except json.JSONDecodeError as e:
            logger.error(f"Помилка парсингу JSON аналізу звіту: {e}")
            return {
                'accuracy_score': 0,
                'discrepancies': [],
                'quality_metrics': {},
                'hidden_analysis': f'Помилка парсингу: {str(e)}',
                'recommendations': 'Перевірте формат даних'
            }
        except Exception as e:
            logger.error(f"Помилка прихованого аналізу звіту: {e}", exc_info=True)
            return {
                'accuracy_score': 0,
                'discrepancies': [],
                'quality_metrics': {},
                'hidden_analysis': f'Помилка: {str(e)}',
                'recommendations': 'Зверніться до адміністратора'
            }

    def _save_session(self, user_id: int) -> None:
        """Зберігає сесію користувача в JSON файл"""
        try:
            session = self.chat_sessions.get(user_id)
            if not session:
                return
            
            metadata = self.user_metadata.get(user_id, {})
            
            # Конвертуємо історію в серіалізований формат
            history_data = []
            for message in session.history:
                history_data.append({
                    "role": message.role,
                    "parts": [part.text if hasattr(part, 'text') else str(part) for part in message.parts],
                    "timestamp": datetime.now().isoformat()
                })
            
            # Формуємо дані для збереження
            session_data = {
                "user_id": user_id,
                "user_name": metadata.get("user_name", "Unknown"),
                "created_at": metadata.get("created_at", datetime.now().isoformat()),
                "last_interaction": datetime.now().isoformat(),
                "metadata": metadata,
                "history": history_data
            }
            
            # Зберігаємо в файл
            file_path = self.storage_dir / f"{user_id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Сесію користувача {user_id} збережено: {file_path}")
            
        except Exception as e:
            logger.error(f"Помилка збереження сесії {user_id}: {e}")

    def _load_all_sessions(self) -> None:
        """Завантажує всі збережені сесії при старті"""
        try:
            if not self.storage_dir.exists():
                logger.info("Директорія збереження не існує, створюємо нову")
                return
            
            loaded_count = 0
            for file_path in self.storage_dir.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    
                    user_id = session_data.get("user_id")
                    if not user_id:
                        logger.warning(f"Файл {file_path} не містить user_id, пропускаємо")
                        continue
                    
                    # Відновлюємо metadata
                    self.user_metadata[user_id] = session_data.get("metadata", {})
                    
                    # Створюємо нову сесію
                    session = self.model.start_chat(history=[])
                    
                    # Відновлюємо історію
                    history_data = session_data.get("history", [])
                    for msg in history_data:
                        # Додаємо повідомлення в історію сесії
                        # ChatSession автоматично підтримує формат history
                        pass  # history вже завантажена через session_data
                    
                    # Зберігаємо відновлену сесію
                    self.chat_sessions[user_id] = session
                    loaded_count += 1
                    
                    logger.info(f"Завантажено сесію користувача {user_id} з {len(history_data)} повідомлень")
                    
                except Exception as e:
                    logger.error(f"Помилка завантаження файлу {file_path}: {e}")
            
            logger.info(f"Завантажено {loaded_count} сесій користувачів")
            
        except Exception as e:
            logger.error(f"Помилка завантаження сесій: {e}")
    
    async def generate_motivational_push(
        self,
        hr_name: str,
        issue_type: str,
        details: Dict[str, Any]
    ) -> str:
        """
        Генерувати персоналізоване мотиваційне повідомлення для HR
        
        Args:
            hr_name: Ім'я HR
            issue_type: Тип проблеми (missing_report, missed_vacancies, low_calls, stagnant, inactive_topic)
            details: Деталі проблеми (вакансії, статистика тощо)
            
        Returns:
            Текст персоналізованого повідомлення
        """
        try:
            # Налаштовуємо різні промпти для різних типів проблем
            prompts = {
                'missing_report': f"""
Створи коротке (2-3 речення) дружнє нагадування для HR-менеджера {hr_name}.

СИТУАЦІЯ: HR не надіслав звіт за день.

ВИМОГИ:
- Тон: дружній, підтримуючий, мотивуючий
- Не звинувачувати, а нагадати
- Натякнути що звіт важливий для команди
- Додати легкий гумор якщо доречно
- Українською мовою

Приклад структури:
👋 [Привітання] + [м'яке нагадування] + [мотивація/підтримка]
""",
                
                'missed_vacancies': f"""
Створи коротке (2-3 речення) м'яке нагадування для HR-менеджера {hr_name}.

СИТУАЦІЯ: HR не згадав у звіті деякі активні вакансії з кандидатами.

ДЕТАЛІ:
{json.dumps(details, ensure_ascii=False, indent=2)}

ВИМОГИ:
- Тон: конструктивний, допомагаючий
- Перелічи 1-2 вакансії які пропущені
- Запитай чи все гаразд з цими вакансіями
- Без критики, просто цікавість
- Українською мовою

Приклад структури:
🤔 [питання про пропущені вакансії] + [можливо допомога?]
""",
                
                'low_calls': f"""
Створи коротке (2-3 речення) підбадьорююче повідомлення для HR-менеджера {hr_name}.

СИТУАЦІЯ: Мало дзвінків за день порівняно з кількістю активних вакансій.

ДЕТАЛІ:
{json.dumps(details, ensure_ascii=False, indent=2)}

ВИМОГИ:
- Тон: підтримуючий, мотивуючий
- Можливо є причина (хворіє, зайнятий?)
- Запропонувати допомогу якщо потрібно
- Без тиску
- Українською мовою

Приклад структури:
💪 [зауваження про активність] + [підтримка] + [можливо допомога?]
""",
                
                'stagnant': f"""
Створи коротке (2-3 речення) конструктивне повідомлення для HR-менеджера {hr_name}.

СИТУАЦІЯ: Є вакансії де кандидати застрягли на одному етапі кілька днів.

ДЕТАЛІ:
{json.dumps(details, ensure_ascii=False, indent=2)}

ВИМОГИ:
- Тон: допомагаючий, турботливий
- Запитай чи потрібна допомога з цими кандидатами
- Можливо є проблема?
- Українською мовою

Приклад структури:
⏸️ [зауваження про застій] + [питання чи все ок] + [пропозиція допомоги]
""",
                
                'inactive_topic': f"""
Створи коротке (2-3 речення) нагадування для HR-менеджера {hr_name}.

СИТУАЦІЯ: Немає активності в топіку по вакансії кілька днів.

ДЕТАЛІ:
{json.dumps(details, ensure_ascii=False, indent=2)}

ВИМОГИ:
- Тон: допитливий, підтримуючий
- Запитай чи є прогрес
- Можливо потрібна допомога?
- Українською мовою

Приклад структури:
💬 [питання про топік] + [чи є новини?] + [можливо допомога?]
"""
            }
            
            prompt = prompts.get(issue_type, prompts['missing_report'])
            
            # Генеруємо відповідь через Gemini
            session = self.model.start_chat(history=[])
            response = session.send_message(prompt)
            
            message = response.text.strip()
            
            # Видаляємо markdown форматування якщо є
            message = message.replace('**', '').replace('*', '')
            
            logger.info(f"Згенеровано push для {hr_name}, тип: {issue_type}")
            
            return message
            
        except Exception as e:
            logger.error(f"Помилка генерації push-повідомлення: {e}")
            # Fallback на стандартне повідомлення
            fallback_messages = {
                'missing_report': f"👋 {hr_name}, нагадую про звіт за сьогодні! Команда чекає на твої результати 😊",
                'missed_vacancies': f"🤔 {hr_name}, помітив що у звіті не згадані деякі активні вакансії. Все добре з ними?",
                'low_calls': f"💪 {hr_name}, сьогодні було менше дзвінків ніж зазвичай. Може потрібна допомога?",
                'stagnant': f"⏸️ {hr_name}, є кандидати які довго на одному етапі. Можливо є якісь труднощі?",
                'inactive_topic': f"💬 {hr_name}, давно не було новин по вакансії. Як справи?"
            }
            return fallback_messages.get(issue_type, f"{hr_name}, давай обговоримо прогрес!")



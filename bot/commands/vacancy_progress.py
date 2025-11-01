"""Команди для роботи з вакансіями та їх аналітикою"""
from telegram import Update
from telegram.ext import ContextTypes

from core.vacancy_analytics import VacancyAnalytics
from services.hurma_service import HurmaService
from services.binotel_service import BinotelService
from core.config import Config
from core.logger_settings import create_logger
from bot.commands.decorators import require_admin

logger = create_logger(__name__)


@require_admin
async def vacancy_progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /vacancy_progress - показує прогрес по всіх активних вакансіях
    
    Використання:
        /vacancy_progress - всі вакансії
        /vacancy_progress problems - тільки проблемні вакансії
    """
    await update.message.reply_text("⏳ Аналізую активні вакансії...")
    
    try:
        # Ініціалізуємо сервіси
        config = Config()
        hurma = HurmaService(
            client_id=config.HURMA_CLIENT_ID,
            client_secret=config.HURMA_CLIENT_SECRET,
            username=config.HURMA_USERNAME,
            password=config.HURMA_PASSWORD,
            company=config.HURMA_COMPANY
        )
        binotel = BinotelService(
            key=config.BINOTEL_KEY,
            secret=config.BINOTEL_SECRET
        )
        
        analytics = VacancyAnalytics(hurma, binotel)
        
        # Визначаємо режим роботи
        args = context.args or []
        show_only_problems = 'problems' in args or 'проблеми' in args
        
        # Отримуємо всі активні вакансії
        vacancies = analytics.get_active_vacancies()
        
        if not vacancies:
            await update.message.reply_text(
                "✅ Активних вакансій не знайдено",
                parse_mode='Markdown'
            )
            return
        
        # Формуємо звіт
        message = f"📊 **Аналіз активних вакансій**\n"
        message += f"Всього активних: {len(vacancies)}\n"
        message += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        problems_count = 0
        
        for vacancy in vacancies:
            vacancy_id = vacancy['id']
            vacancy_name = vacancy.get('name', 'Unknown')
            
            # Отримуємо кількість кандидатів
            candidates = analytics.get_vacancy_candidates_count(vacancy_id)
            total = candidates.get('__total__', 0)
            
            # Визначаємо чи є проблема
            has_problem = False
            problem_icon = "✅"
            problem_text = ""
            
            if total == 0:
                has_problem = True
                problem_icon = "⚠️"
                problem_text = " (немає кандидатів)"
            elif total > 0:
                # Перевіряємо чи є кандидати тільки на початкових етапах
                first_stage_candidates = 0
                total_stages = len([k for k in candidates.keys() if k != '__total__'])
                
                if total_stages > 0:
                    # Беремо перший етап (зазвичай "Нові" або подібне)
                    stage_counts = [v for k, v in candidates.items() if k != '__total__']
                    if stage_counts:
                        first_stage_candidates = stage_counts[0]
                    
                    # Якщо всі кандидати на першому етапі - можливий застій
                    if first_stage_candidates == total and total > 3:
                        has_problem = True
                        problem_icon = "⏸️"
                        problem_text = " (всі на першому етапі - можливий застій)"
            
            # Якщо режим "тільки проблеми" - пропускаємо нормальні
            if show_only_problems and not has_problem:
                continue
            
            if has_problem:
                problems_count += 1
            
            # Формуємо рядок для вакансії
            message += f"{problem_icon} **{vacancy_name}**{problem_text}\n"
            message += f"   ID: {vacancy_id} | Кандидатів: {total}\n"
            
            # Показуємо розподіл по етапах якщо є кандидати
            if total > 0:
                message += "   По етапах:\n"
                for stage_name, count in candidates.items():
                    if stage_name != '__total__' and count > 0:
                        message += f"     • {stage_name}: {count}\n"
            
            message += "\n"
        
        # Підсумок
        message += "━━━━━━━━━━━━━━━━━━━━\n"
        if show_only_problems:
            message += f"⚠️ Виявлено проблем: {problems_count}\n"
        else:
            message += f"✅ Нормальних: {len(vacancies) - problems_count}\n"
            message += f"⚠️ З проблемами: {problems_count}\n"
        
        message += f"\n💡 Для перегляду тільки проблемних: /vacancy_progress problems"
        
        # Telegram обмежує довжину повідомлення до 4096 символів
        if len(message) > 4000:
            # Розбиваємо на частини
            parts = []
            current_part = ""
            
            for line in message.split('\n'):
                if len(current_part) + len(line) + 1 > 4000:
                    parts.append(current_part)
                    current_part = line + '\n'
                else:
                    current_part += line + '\n'
            
            if current_part:
                parts.append(current_part)
            
            # Надсилаємо по частинах
            for i, part in enumerate(parts):
                await update.message.reply_text(
                    part,
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )
        
    except Exception as e:
        logger.error(f"Помилка при аналізі вакансій: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Помилка при аналізі вакансій:\n{str(e)}",
            parse_mode='Markdown'
        )


@require_admin
async def vacancy_stagnant_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /vacancy_stagnant - показує вакансії з застоєм
    
    Застій = є кандидати але немає руху по воронці
    """
    await update.message.reply_text("⏳ Шукаю вакансії з застоєм...")
    
    try:
        # Ініціалізуємо сервіси
        config = Config()
        hurma = HurmaService(
            client_id=config.HURMA_CLIENT_ID,
            client_secret=config.HURMA_CLIENT_SECRET,
            username=config.HURMA_USERNAME,
            password=config.HURMA_PASSWORD,
            company=config.HURMA_COMPANY
        )
        binotel = BinotelService(
            key=config.BINOTEL_KEY,
            secret=config.BINOTEL_SECRET
        )
        
        analytics = VacancyAnalytics(hurma, binotel)
        
        # Знаходимо вакансії з застоєм
        stagnant = analytics.find_stagnant_vacancies(min_candidates=1, days_threshold=3)
        
        if not stagnant:
            await update.message.reply_text(
                "✅ Вакансій з застоєм не виявлено!\n\n"
                "Всі активні вакансії мають рух або немає кандидатів.",
                parse_mode='Markdown'
            )
            return
        
        # Формуємо звіт
        message = f"⏸️ **Вакансії з можливим застоєм**\n"
        message += f"Знайдено: {len(stagnant)}\n"
        message += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for vac in stagnant:
            message += f"📋 **{vac['name']}** (ID: {vac['id']})\n"
            message += f"👥 Кандидатів: {vac['candidates_count']}\n"
            message += f"⚠️ {vac['warning']}\n"
            
            if vac.get('candidates_by_stage'):
                message += "По етапах:\n"
                for stage, count in vac['candidates_by_stage'].items():
                    if count > 0:
                        message += f"  • {stage}: {count}\n"
            
            message += "\n"
        
        message += "━━━━━━━━━━━━━━━━━━━━\n"
        message += "💡 Рекомендується перевірити активність HR по цих вакансіях"
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Помилка при пошуку застійних вакансій: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Помилка:\n{str(e)}",
            parse_mode='Markdown'
        )

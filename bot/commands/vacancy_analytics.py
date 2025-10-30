"""Команди для аналітики вакансій"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from core.logger_settings import create_logger
from core.analytics import AnalyticsService
from bot.commands.decorators import require_group_topic

logger = create_logger(__name__)


@require_group_topic
async def vacancy_analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /vacancy_analytics - вибір вакансії для аналітики"""
    try:
        await update.message.reply_text("⏳ Завантажую список вакансій...")
        
        analytics: AnalyticsService = context.bot_data.get('analytics')
        if not analytics:
            await update.message.reply_text("❌ Сервіс аналітики недоступний")
            return
        
        # Отримуємо список активних вакансій
        vacancies = analytics.get_all_active_vacancies()
        
        if not vacancies:
            await update.message.reply_text(
                "❌ Немає активних вакансій\n\n"
                "Додайте вакансії через: /add_vacancy [ID] [Назва]"
            )
            return
        
        # Створюємо клавіатуру з вакансіями
        keyboard = []
        
        for vacancy in vacancies:
            # Обмежуємо довжину назви для кнопки
            button_text = vacancy['name']
            if len(button_text) > 60:
                button_text = button_text[:57] + "..."
            
            keyboard.append([
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"vacancy_stats:{vacancy['id']}"
                )
            ])
        
        # Додаємо кнопку "Оновити список"
        keyboard.append([
            InlineKeyboardButton(
                text="🔄 Оновити список",
                callback_data="vacancy_stats:refresh"
            )
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📊 <b>Виберіть вакансію для аналітики</b>\n\n"
            f"Знайдено {len(vacancies)} активних вакансій:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Помилка у vacancy_analytics_command: {e}")
        await update.message.reply_text(f"❌ Помилка: {str(e)}")


async def vacancy_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник callback для показу статистики вакансії"""
    query = update.callback_query
    await query.answer()
    
    try:
        from datetime import date, timedelta
        
        callback_data = query.data
        
        # Якщо натиснули "Оновити"
        if callback_data == "vacancy_stats:refresh":
            analytics: AnalyticsService = context.bot_data.get('analytics')
            if analytics:
                analytics.clear_cache()
            
            await query.edit_message_text("🔄 Кеш очищено. Використайте /vacancy_analytics для оновленого списку")
            return
        
        # Якщо натиснули "Назад"
        if callback_data == "vacancy_stats:back":
            # Повторно показуємо список вакансій
            analytics: AnalyticsService = context.bot_data.get('analytics')
            if not analytics:
                await query.edit_message_text("❌ Сервіс аналітики недоступний")
                return
            
            vacancies = analytics.get_all_active_vacancies()
            
            if not vacancies:
                await query.edit_message_text("❌ Немає активних вакансій")
                return
            
            keyboard = []
            for vacancy in vacancies:
                button_text = vacancy['name']
                if len(button_text) > 60:
                    button_text = button_text[:57] + "..."
                
                keyboard.append([
                    InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"vacancy_stats:{vacancy['id']}"
                    )
                ])
            
            keyboard.append([
                InlineKeyboardButton(
                    text="🔄 Оновити список",
                    callback_data="vacancy_stats:refresh"
                )
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"📊 <b>Виберіть вакансію для аналітики</b>\n\n"
                f"Знайдено {len(vacancies)} активних вакансій:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            return
        
        # Парсимо callback_data
        parts = callback_data.split(':')
        
        # Якщо формат vacancy_stats:ID:DATE
        if len(parts) == 3:
            vacancy_id = int(parts[1])
            date_str = parts[2]
            
            if date_str == 'today':
                report_date = date.today()
            elif date_str == 'yesterday':
                report_date = date.today() - timedelta(days=1)
            else:
                # Формат YYYY-MM-DD
                report_date = date.fromisoformat(date_str)
        else:
            # Формат vacancy_stats:ID - використовуємо сьогодні
            vacancy_id = int(parts[1])
            report_date = date.today()
        
        await query.edit_message_text("⏳ Формую статистику...")
        
        analytics: AnalyticsService = context.bot_data.get('analytics')
        if not analytics:
            await query.edit_message_text("❌ Сервіс аналітики недоступний")
            return
        
        # Отримуємо статистику
        stats = analytics.get_vacancy_statistics(vacancy_id, report_date)
        
        if not stats:
            await query.edit_message_text(f"❌ Вакансію з ID {vacancy_id} не знайдено")
            return
        
        # Формуємо повідомлення
        message = _format_vacancy_statistics(stats)
        
        # Створюємо кнопки для вибору дати та назад
        keyboard = [
            [
                InlineKeyboardButton(
                    text="📅 Сьогодні",
                    callback_data=f"vacancy_stats:{vacancy_id}:today"
                ),
                InlineKeyboardButton(
                    text="📅 Вчора",
                    callback_data=f"vacancy_stats:{vacancy_id}:yesterday"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад до списку",
                    callback_data="vacancy_stats:back"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        import traceback
        logger.error(f"Помилка у vacancy_stats_callback: {e}\n{traceback.format_exc()}")
        await query.edit_message_text(f"❌ Помилка: {str(e)}")


def _format_vacancy_statistics(stats: dict) -> str:
    """
    Форматування статистики вакансії (звіт за весь час + за день)
    
    Args:
        stats: Словник зі статистикою
        
    Returns:
        Форматований текст
    """
    from datetime import datetime
    
    vacancy_name = stats['vacancy_name']
    vacancy_id = stats['vacancy_id']
    report_date = stats['report_date']
    
    # Дані за весь час
    all_time = stats['all_time']
    total = all_time['total_candidates']
    all_time_stages = all_time['stages']
    
    # Дані за день
    daily = stats['daily']
    created_count = daily['created_count']
    updated_count = daily['updated_count']
    created_stages = daily['created_stages']
    updated_stages = daily['updated_stages']
    
    message = (
        f"📊 <b>Аналітика вакансії</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>🎯 {vacancy_name}</b>\n"
        f"ID: <code>{vacancy_id}</code>\n\n"
    )
    
    # ========== ЗВІТ ЗА ДЕНЬ ==========
    message += (
        f"� <b>Звіт за {report_date.strftime('%d.%m.%Y')}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    if created_count == 0 and updated_count == 0:
        message += "ℹ️ За сьогодні немає нових або оновлених кандидатів\n\n"
    else:
        # Створені кандидати
        if created_count > 0:
            message += f"✨ <b>Створено:</b> {created_count}\n"
            
            for stage_name, stage_data in sorted(
                created_stages.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            ):
                print(stage_data, stage_name)
                count = stage_data['count']
                message += f"  • {stage_name}: {count}\n"
                
                # Показуємо кандидатів
                for candidate in stage_data['candidates'][:3]:
                    name = candidate.get('name', 'Без імені')
                    recruiter = candidate.get('recruiter', 'Не вказано')
                    message += f"    - {name} (HR: {recruiter})\n"
                
                if len(stage_data['candidates']) > 3:
                    message += f"    ... та ще {len(stage_data['candidates']) - 3}\n"
            
            message += "\n"
        
        # Оновлені кандидати
        if updated_count > 0:
            message += f"🔄 <b>Оновлено:</b> {updated_count}\n"
            
            for stage_name, stage_data in sorted(
                updated_stages.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            ):
                count = stage_data['count']
                message += f"  • {stage_name}: {count}\n"
                
                # Показуємо кандидатів
                for candidate in stage_data['candidates'][:3]:
                    name = candidate.get('name', 'Без імені')
                    recruiter = candidate.get('recruiter', 'Не вказано')
                    message += f"    - {name} (HR: {recruiter})\n"
                
                if len(stage_data['candidates']) > 3:
                    message += f"    ... та ще {len(stage_data['candidates']) - 3}\n"
            
            message += "\n"
    
    # ========== ЗВІТ ЗА ВЕСЬ ЧАС ==========
    message += (
        f"📈 <b>Статистика за весь час</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Всього кандидатів:</b> {total}\n\n"
    )
    
    if not all_time_stages:
        message += "ℹ️ Немає кандидатів на вакансії"
        return message
    
    message += "<b>📌 Розподіл по етапах:</b>\n\n"
    # Сортуємо етапи по кількості кандидатів
    sorted_stages = sorted(
        all_time_stages.items(),
        key=lambda x: x[1]['count'],
        reverse=True
    )
    print(sorted_stages)
    
    for stage_name, stage_data in sorted_stages:
        count = stage_data['count']
        percentage = (count / total * 100) if total > 0 else 0
        
        # Візуальна шкала
        bar_length = int(percentage / 5)  # Макс 20 символів
        bar = "█" * bar_length + "░" * (20 - bar_length)
        
        message += f"  <b>{stage_name}</b>\n"
        message += f"  {bar} {count} ({percentage:.1f}%)\n\n"
    
    # Останні оновлення (топ-5)
    all_candidates = []
    for stage_data in all_time_stages.values():
        all_candidates.extend(stage_data.get('candidates', []))
    
    if all_candidates:
        message += "<b>🆕 Останні 5 оновлень:</b>\n"
        
        # Сортуємо по даті оновлення
        candidates_with_date = [
            c for c in all_candidates 
            if c.get('updated_at')
        ]
        
        if candidates_with_date:
            candidates_with_date.sort(
                key=lambda x: x.get('updated_at', ''),
                reverse=True
            )
            
            for candidate in candidates_with_date[:5]:
                name = candidate.get('name', 'Без імені')
                recruiter = candidate.get('recruiter', 'Не вказано')
                
                # Парсимо дату для красивого відображення
                updated_at = candidate.get('updated_at', '')
                try:
                    dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                    date_str = dt.strftime('%d.%m.%Y %H:%M')
                except:
                    date_str = 'невідомо'
                
                message += f"  • <b>{name}</b>\n"
                message += f"    HR: {recruiter} | {date_str}\n"
        else:
            message += "  <i>Немає даних про оновлення</i>\n"
    
    return message
"""
Тест нової аналітики вакансій
"""
from datetime import date, datetime, timedelta

def test_date_logic():
    """Тестуємо логіку розділення кандидатів за датами"""
    
    # Симуляція даних
    report_date = date(2025, 10, 30)
    
    candidates = [
        {
            'id': 1,
            'name': 'Іван Петренко',
            'created_at': '2025-10-30T10:00:00Z',
            'updated_at': '2025-10-30T10:00:00Z',
            'stage': {'name': 'Нові кандидати'}
        },
        {
            'id': 2,
            'name': 'Марія Коваль',
            'created_at': '2025-10-29T15:00:00Z',
            'updated_at': '2025-10-30T14:00:00Z',
            'stage': {'name': 'Первинна співбесіда'}
        },
        {
            'id': 3,
            'name': 'Петро Сидоренко',
            'created_at': '2025-10-28T09:00:00Z',
            'updated_at': '2025-10-28T09:00:00Z',
            'stage': {'name': 'Технічна співбесіда'}
        },
        {
            'id': 4,
            'name': 'Олег Іваненко',
            'created_at': '2025-10-30T16:30:00Z',
            'updated_at': '2025-10-30T16:30:00Z',
            'stage': {'name': 'Нові кандидати'}
        },
    ]
    
    created_today = []
    updated_today = []
    
    for candidate in candidates:
        created_at = candidate.get('created_at')
        updated_at = candidate.get('updated_at')
        
        # Перевіряємо чи створений сьогодні
        if created_at:
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            if created_date.date() == report_date:
                created_today.append(candidate)
                continue  # Якщо створений сьогодні - не рахуємо як оновлений
        
        # Перевіряємо чи оновлений сьогодні
        if updated_at:
            updated_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            if updated_date.date() == report_date:
                updated_today.append(candidate)
    
    print("=" * 50)
    print("ТЕСТ РОЗДІЛЕННЯ КАНДИДАТІВ ЗА ДАТАМИ")
    print("=" * 50)
    print(f"\n📅 Дата звіту: {report_date.strftime('%d.%m.%Y')}\n")
    
    print(f"✨ Створено сьогодні: {len(created_today)}")
    for c in created_today:
        print(f"   - {c['name']} ({c['stage']['name']})")
    
    print(f"\n🔄 Оновлено сьогодні: {len(updated_today)}")
    for c in updated_today:
        print(f"   - {c['name']} ({c['stage']['name']})")
    
    print(f"\n👥 Всього кандидатів: {len(candidates)}")
    
    # Перевірка
    assert len(created_today) == 2, "Має бути 2 створених (ID 1 та 4)"
    assert len(updated_today) == 1, "Має бути 1 оновлений (ID 2)"
    
    print("\n✅ Тест пройдено успішно!")
    print("=" * 50)


def test_stage_distribution():
    """Тестуємо розподіл по етапах"""
    from collections import defaultdict
    
    candidates = [
        {'name': 'Кандидат 1', 'stage': {'name': 'Нові кандидати'}},
        {'name': 'Кандидат 2', 'stage': {'name': 'Нові кандидати'}},
        {'name': 'Кандидат 3', 'stage': {'name': 'Первинна співбесіда'}},
        {'name': 'Кандидат 4', 'stage': {'name': 'Нові кандидати'}},
        {'name': 'Кандидат 5', 'stage': {'name': 'Технічна співбесіда'}},
    ]
    
    stage_stats = defaultdict(lambda: {'count': 0, 'candidates': []})
    
    for candidate in candidates:
        stage_name = candidate['stage']['name']
        stage_stats[stage_name]['count'] += 1
        stage_stats[stage_name]['candidates'].append(candidate)
    
    print("\n" + "=" * 50)
    print("ТЕСТ РОЗПОДІЛУ ПО ЕТАПАХ")
    print("=" * 50)
    
    total = len(candidates)
    print(f"\n👥 Всього: {total}\n")
    
    for stage_name, data in sorted(stage_stats.items(), key=lambda x: x[1]['count'], reverse=True):
        count = data['count']
        percentage = (count / total * 100) if total > 0 else 0
        
        # Візуальна шкала
        bar_length = int(percentage / 5)
        bar = '█' * bar_length + '░' * (20 - bar_length)
        
        print(f"{stage_name}")
        print(f"{bar} {count} ({percentage:.1f}%)")
        print()
    
    assert stage_stats['Нові кандидати']['count'] == 3
    assert stage_stats['Первинна співбесіда']['count'] == 1
    assert stage_stats['Технічна співбесіда']['count'] == 1
    
    print("✅ Тест пройдено успішно!")
    print("=" * 50)


if __name__ == '__main__':
    test_date_logic()
    test_stage_distribution()
    
    print("\n🎉 ВСІ ТЕСТИ ПРОЙДЕНО!")

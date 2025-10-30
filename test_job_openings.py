"""
Тест роботи з job_openings
"""

def test_job_openings_parsing():
    """Тестуємо парсинг job_openings"""
    
    # Симуляція кандидата з реальною структурою
    candidate = {
        'id': 123,
        'name': 'Тестовий Кандидат',
        'job_openings': [
            {
                'jobopening_id': 84,
                'stage_id': 1
            }
        ],
        'responsible_recruiter': {
            'id': 456,
            'name': 'Олена Іваненко'
        }
    }
    
    # Симуляція вакансій з етапами
    vacancies_with_stages = {
        84: {
            'info': {
                'id': 84,
                'name': 'Python Developer (Middle)',
                'status': 1
            },
            'stages': [
                {'id': 1, 'name': 'Нові кандидати'},
                {'id': 2, 'name': 'Первинна співбесіда'},
                {'id': 3, 'name': 'Технічна співбесіда'},
                {'id': 4, 'name': 'Оффер'},
            ]
        }
    }
    
    print("=" * 60)
    print("ТЕСТ ПАРСИНГУ JOB_OPENINGS")
    print("=" * 60)
    
    print(f"\n📋 Кандидат: {candidate['name']}")
    print(f"ID: {candidate['id']}")
    print(f"HR: {candidate['responsible_recruiter']['name']}")
    
    print(f"\n🎯 Job Openings:")
    for job in candidate['job_openings']:
        job_id = job['jobopening_id']
        stage_id = job['stage_id']
        
        # Знаходимо назву вакансії
        vacancy_name = 'Не знайдено'
        stage_name = 'Не знайдено'
        
        if job_id in vacancies_with_stages:
            vacancy_data = vacancies_with_stages[job_id]
            vacancy_name = vacancy_data['info']['name']
            
            # Знаходимо назву етапу
            for stage in vacancy_data['stages']:
                if stage['id'] == stage_id:
                    stage_name = stage['name']
                    break
        
        print(f"  • Вакансія ID {job_id}: {vacancy_name}")
        print(f"    Етап ID {stage_id}: {stage_name}")
    
    print("\n" + "=" * 60)
    
    # Перевірки
    assert len(candidate['job_openings']) == 1
    assert candidate['job_openings'][0]['jobopening_id'] == 84
    assert candidate['job_openings'][0]['stage_id'] == 1
    
    print("✅ Тест пройдено!")
    print("=" * 60)


def test_multiple_vacancies():
    """Тестуємо кандидата з кількома вакансіями"""
    
    candidate = {
        'id': 456,
        'name': 'Марія Коваль',
        'job_openings': [
            {'jobopening_id': 84, 'stage_id': 2},
            {'jobopening_id': 91, 'stage_id': 1},
        ]
    }
    
    vacancies = {
        84: {'info': {'name': 'Python Developer'}, 'stages': [
            {'id': 1, 'name': 'Новий'},
            {'id': 2, 'name': 'Співбесіда'},
        ]},
        91: {'info': {'name': 'Frontend Developer'}, 'stages': [
            {'id': 1, 'name': 'Новий'},
            {'id': 2, 'name': 'Тестове завдання'},
        ]}
    }
    
    print("\n" + "=" * 60)
    print("ТЕСТ МНОЖИННИХ ВАКАНСІЙ")
    print("=" * 60)
    
    print(f"\n📋 Кандидат: {candidate['name']}")
    print(f"Кількість вакансій: {len(candidate['job_openings'])}")
    
    for job in candidate['job_openings']:
        job_id = job['jobopening_id']
        stage_id = job['stage_id']
        
        vacancy_name = vacancies[job_id]['info']['name']
        stage_name = next(
            (s['name'] for s in vacancies[job_id]['stages'] if s['id'] == stage_id),
            'Не знайдено'
        )
        
        print(f"\n  🎯 {vacancy_name}")
        print(f"     Етап: {stage_name}")
    
    print("\n" + "=" * 60)
    print("✅ Тест пройдено!")
    print("=" * 60)


def test_filter_by_vacancy():
    """Тестуємо фільтрацію кандидатів по вакансії"""
    
    candidates = [
        {
            'id': 1,
            'name': 'Кандидат 1',
            'job_openings': [
                {'jobopening_id': 84, 'stage_id': 1}
            ]
        },
        {
            'id': 2,
            'name': 'Кандидат 2',
            'job_openings': [
                {'jobopening_id': 84, 'stage_id': 2},
                {'jobopening_id': 91, 'stage_id': 1}
            ]
        },
        {
            'id': 3,
            'name': 'Кандидат 3',
            'job_openings': [
                {'jobopening_id': 91, 'stage_id': 1}
            ]
        },
        {
            'id': 4,
            'name': 'Кандидат 4',
            'job_openings': []  # Без вакансій
        }
    ]
    
    print("\n" + "=" * 60)
    print("ТЕСТ ФІЛЬТРАЦІЇ ПО ВАКАНСІЇ")
    print("=" * 60)
    
    target_vacancy_id = 84
    
    print(f"\n🔍 Шукаємо кандидатів для вакансії ID {target_vacancy_id}\n")
    
    filtered = []
    for candidate in candidates:
        job_openings = candidate.get('job_openings', [])
        
        for job in job_openings:
            if job.get('jobopening_id') == target_vacancy_id:
                filtered.append(candidate)
                break
    
    print(f"Знайдено кандидатів: {len(filtered)}")
    for c in filtered:
        print(f"  • {c['name']} (ID: {c['id']})")
    
    print("\n" + "=" * 60)
    
    # Перевірка
    assert len(filtered) == 2
    assert filtered[0]['id'] == 1
    assert filtered[1]['id'] == 2
    
    print("✅ Тест пройдено!")
    print("=" * 60)


if __name__ == '__main__':
    test_job_openings_parsing()
    test_multiple_vacancies()
    test_filter_by_vacancy()
    
    print("\n" + "=" * 60)
    print("🎉 ВСІ ТЕСТИ ПРОЙДЕНО!")
    print("=" * 60)

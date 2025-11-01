"""Тест regex для парсингу JSON з function_call"""
import re
import json

# Тестові відповіді від AI
test_responses = [
    # Формат 1: чистий JSON
    '{"function_call": "get_active_vacancies", "arguments": {}}',
    
    # Формат 2: JSON з пробілами
    '''{
  "function_call": "get_active_vacancies",
  "arguments": {}
}''',
    
    # Формат 3: JSON у markdown блоці
    '''```json
{
  "function_call": "get_active_vacancies",
  "arguments": {}
}
```''',
    
    # Формат 4: JSON з текстом навколо
    '''Щоб відповісти на ваше питання, мені потрібно викликати функцію:
{
  "function_call": "get_active_vacancies",
  "arguments": {}
}
Зараз отримаю дані...''',
]

# Поточний pattern (не підтримує багаторядковий JSON)
pattern1 = r'\{[^{}]*"function_call"[^{}]*\}'

# Покращений pattern (підтримує вкладені структури)
pattern2 = r'\{[^}]*"function_call"[^}]*"arguments"[^}]*\{[^}]*\}[^}]*\}'

# Найкращий pattern (з прапором DOTALL)
pattern3 = r'\{(?:[^{}]|(?:\{[^}]*\}))*"function_call"(?:[^{}]|(?:\{[^}]*\}))*\}'

print("=" * 60)
print("ТЕСТ REGEX PATTERNS")
print("=" * 60)

for i, response in enumerate(test_responses, 1):
    print(f"\n📝 Тест {i}: {response[:50]}...")
    print("-" * 60)
    
    # Pattern 1 (поточний)
    match1 = re.search(pattern1, response)
    if match1:
        try:
            data = json.loads(match1.group())
            print(f"✅ Pattern 1: {data}")
        except json.JSONDecodeError as e:
            print(f"❌ Pattern 1: Знайдено, але не valid JSON - {e}")
    else:
        print("❌ Pattern 1: Не знайдено")
    
    # Pattern 2
    match2 = re.search(pattern2, response)
    if match2:
        try:
            data = json.loads(match2.group())
            print(f"✅ Pattern 2: {data}")
        except json.JSONDecodeError as e:
            print(f"❌ Pattern 2: Знайдено, але не valid JSON - {e}")
    else:
        print("❌ Pattern 2: Не знайдено")
    
    # Pattern 3 (з DOTALL)
    match3 = re.search(pattern3, response, re.DOTALL)
    if match3:
        try:
            data = json.loads(match3.group())
            print(f"✅ Pattern 3: {data}")
        except json.JSONDecodeError as e:
            print(f"❌ Pattern 3: Знайдено, але не valid JSON - {e}")
    else:
        print("❌ Pattern 3: Не знайдено")

print("\n" + "=" * 60)
print("РЕКОМЕНДАЦІЯ: Pattern 3 з re.DOTALL")
print("=" * 60)

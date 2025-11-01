"""
Тест Function Calling для Gemini
"""
import asyncio
import sys
import io

# Windows console encoding fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from services.hurma_service import HurmaService
from services.binotel_service import BinotelService
from services.gemini_service import GeminiService
from core.analytics import AnalyticsService
from core.candidate_flow_tracker import CandidateFlowTracker
from core.vacancy_activity_monitor import VacancyActivityMonitor
from core.config import Config


async def test_function_calling():
    """Тест Function Calling"""
    
    print("="*80)
    print("ТЕСТ GEMINI FUNCTION CALLING")
    print("="*80)
    
    # Ініціалізація сервісів
    print("\n1. Ініціалізація сервісів...")
    
    hurma = HurmaService(
        client_id=Config.HURMA_CLIENT_ID,
        client_secret=Config.HURMA_CLIENT_SECRET,
        username=Config.HURMA_USERNAME,
        password=Config.HURMA_PASSWORD,
        company=Config.HURMA_COMPANY
    )
    
    binotel = BinotelService(
        key=Config.BINOTEL_KEY,
        secret=Config.BINOTEL_SECRET
    )
    
    analytics = AnalyticsService(hurma, binotel)
    candidate_flow_tracker = CandidateFlowTracker(hurma)
    vacancy_activity_monitor = VacancyActivityMonitor(hurma, binotel)
    
    print("✓ Сервіси ініціалізовано")
    
    # Ініціалізація Gemini з Function Calling
    print("\n2. Ініціалізація Gemini AI з Function Calling...")
    
    gemini = GeminiService(
        hurma_service=hurma,
        binotel_service=binotel,
        analytics=analytics,
        vacancy_activity_monitor=vacancy_activity_monitor,
        candidate_flow_tracker=candidate_flow_tracker
    )
    
    print(f"✓ Gemini ініціалізовано з {len(gemini.function_declarations)} функціями")
    print("\nДоступні функції:")
    for func in gemini.function_declarations:
        print(f"  - {func['name']}: {func['description']}")
    
    # Тестові запити
    test_user_id = 123456789
    test_user_name = "TestUser"
    
    print("\n" + "="*80)
    print("ТЕСТОВІ ЗАПИТИ")
    print("="*80)
    
    # Тест 1: Запит про вакансії
    print("\n[ТЕСТ 1] Запит: 'Скільки у нас зараз активних вакансій?'")
    response1 = await gemini.chat(
        user_id=test_user_id,
        user_name=test_user_name,
        message="Скільки у нас зараз активних вакансій?"
    )
    print(f"\nВідповідь AI:\n{response1}")
    
    # Тест 2: Запит про дзвінки
    print("\n" + "-"*80)
    print("\n[ТЕСТ 2] Запит: 'Скільки дзвінків було сьогодні на номері 961?'")
    response2 = await gemini.chat(
        user_id=test_user_id,
        user_name=test_user_name,
        message="Скільки дзвінків було сьогодні на номері 961?"
    )
    print(f"\nВідповідь AI:\n{response2}")
    
    # Тест 3: Запит про неактивні вакансії
    print("\n" + "-"*80)
    print("\n[ТЕСТ 3] Запит: 'Є вакансії які застояли без активності?'")
    response3 = await gemini.chat(
        user_id=test_user_id,
        user_name=test_user_name,
        message="Є вакансії які застояли без активності?"
    )
    print(f"\nВідповідь AI:\n{response3}")
    
    # Тест 4: Запит про конкретну вакансію
    print("\n" + "-"*80)
    print("\n[ТЕСТ 4] Запит: 'Як справи з вакансією номер 84?'")
    response4 = await gemini.chat(
        user_id=test_user_id,
        user_name=test_user_name,
        message="Як справи з вакансією номер 84?"
    )
    print(f"\nВідповідь AI:\n{response4}")
    
    print("\n" + "="*80)
    print("ТЕСТУВАННЯ ЗАВЕРШЕНО")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_function_calling())

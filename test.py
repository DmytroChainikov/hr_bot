from services.hurma_service import HurmaService
import os
from dotenv import load_dotenv
from datetime import datetime
load_dotenv()
# новий - 1
# без відповіді - 46
# резерв - 6
# інтерв'ю - 2
# співбесіда з керівником - 48
# відправлено на філіал - 39
# на стажуванні - 40
# прийнято офер - 20
# відмова кандидату - 43

# Перевіряємо чи є OAuth credentials, якщо так - використовуємо їх
if all([os.getenv('HURMA_CLIENT_ID'), os.getenv('HURMA_CLIENT_SECRET'), 
        os.getenv('HURMA_USERNAME'), os.getenv('HURMA_PASSWORD')]):
    hurma_service = HurmaService(
        client_id=os.getenv('HURMA_CLIENT_ID'),
        client_secret=os.getenv('HURMA_CLIENT_SECRET'),
        username=os.getenv('HURMA_USERNAME'),
        password=os.getenv('HURMA_PASSWORD'),
        company=os.getenv('HURMA_COMPANY', 'yourcompany'),
    )
else:
    hurma_service = HurmaService(api_key=os.getenv('HURMA_API_KEY'))

import pprint
data = hurma_service.get_job_stages(vacancy_id=82)
with open('test.json', 'w', encoding='utf-8') as f:
    import json
    json.dump(data, f, ensure_ascii=False, indent=4)
pprint.pprint(data)

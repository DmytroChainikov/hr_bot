from services.hurma_service import HurmaService
from services.binotel_service import BinotelService
import os
from dotenv import load_dotenv
from datetime import datetime
load_dotenv()

binotel_service = BinotelService(os.getenv('BINOTEL_KEY'), os.getenv('BINOTEL_SECRET'))

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
data = hurma_service.get_job_stages(vacancy_id=29)
with open('users_hurma.json', 'w', encoding='utf-8') as f:
    import json
    json.dump(data, f, ensure_ascii=False, indent=4)
# pprint.pprint(data)
# отримання даних з Бінотел за внутрішнім номером, за сьогоднішній день
# def get_calls_by_internal_number(
#         self, 
#         internal_number: str, 
#         date_from: datetime.datetime, 
#         date_to: datetime.datetime
#     )
# binotel_data = binotel_service.get_calls_by_internal_number(internal_number=961,
#                                                             date_from=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
#                                                             date_to=datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)) 

# with open('users_binotel.json', 'w', encoding='utf-8') as f:
#     import json
#     json.dump(binotel_data, f, ensure_ascii=False, indent=4)
# pprint.pprint(binotel_data)

import json
# with open('users_hurma.json', 'r', encoding='utf-8') as f:
#     hurma_data = json.load(f)

#analize hurma changes for week
from datetime import datetime, timedelta, timezone
# 2025-03-19T14:14:13+02:00
# now = datetime.now(timezone(timedelta(hours=2)))
# week_ago = now - timedelta(days=7)
# new_candidates = []
# for candidate in hurma_data['data']:
#     # print(candidate['updated_at'])
#     # 2025-03-19T14:14:13+02:00
#     updated_at = datetime.fromisoformat(candidate['updated_at'])
#     # print(created_at)
#     if updated_at >= week_ago:
#         new_candidates.append(candidate)
# print(f"New candidates in the last week: {len(new_candidates)}")
# print("List of new candidates:")
# for candidate in new_candidates:
#     print(f"- {candidate['name']} (Created at: {candidate['updated_at']})")
# print(len( hurma_data['data']))
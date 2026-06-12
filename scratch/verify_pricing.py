import os
import sys
import django
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chipscan.settings')
django.setup()

from django.test import RequestFactory
from scanner.views import api_prices, api_check_chip, seed_database_if_empty
from scanner.models import Price, NonCodePrice, Chip

# First ensure database is seeded
seed_database_if_empty()

print("--- TESTING SEEDED CHIPS GRADES AND CAPACITIES ---")
for code in ["KM8V7001JM-B809", "KM8U8001JM-B907", "KM8V8001JM-B810", "KMQX1000SM-B419", "KMQ7X000SA-B315"]:
    chip = Chip.objects.filter(code=code).first()
    if chip:
        print(f"Chip: {chip.code} | Size: {chip.size} | Grade: {chip.grade} | Status: {chip.status}")
    else:
        print(f"Chip {code} not found")

print("\n--- TESTING API GET /api/prices/ ---")
factory = RequestFactory()
request = factory.get('/api/prices/')
response = api_prices(request)
prices_data = json.loads(response.content)
print("Seeded Coded Prices (by Grade):", prices_data.get('coded'))
print("Seeded Non-Code Prices (by Capacity):", prices_data.get('noncode'))

print("\n--- TESTING API POST /api/prices/ ---")
updated_coded = prices_data.get('coded', {})
updated_noncode = prices_data.get('noncode', {})
# Let's set some dummy changes
updated_coded['A1'] = 150
updated_noncode['16GB'] = 99

post_request = factory.post('/api/prices/', 
                            data=json.dumps({'coded': updated_coded, 'noncode': updated_noncode}),
                            content_type='application/json')
post_response = api_prices(post_request)
print("POST Response status:", post_response.status_code)
print("POST Response content:", post_response.content.decode('utf-8'))

# Verify they saved
response2 = api_prices(factory.get('/api/prices/'))
prices_data2 = json.loads(response2.content)
print("Coded Price A1 updated to:", prices_data2.get('coded', {}).get('A1'))
print("Non-Code Price 16GB updated to:", prices_data2.get('noncode', {}).get('16GB'))

print("\n--- TESTING API GET /api/chips/<code>/check/ ---")
# Test a coded chip: KMQX1000SM-B419 (16GB, Grade A1, coded status)
# Expected coded price: 150 (updated from 120), non-coded price: 99
req_check1 = factory.get('/api/chips/KMQX1000SM-B419/check/')
res_check1 = api_check_chip(req_check1, 'KMQX1000SM-B419')
data_check1 = json.loads(res_check1.content)
print("Coded chip check data:", data_check1)

# Test an ungraded/N/A chip: KM8V8001JM-B810 (512GB, Grade N/A, coded status)
# Expected coded price: 0, non-coded price: 800 (or seeded default)
req_check2 = factory.get('/api/chips/KM8V8001JM-B810/check/')
res_check2 = api_check_chip(req_check2, 'KM8V8001JM-B810')
data_check2 = json.loads(res_check2.content)
print("Ungraded chip check data:", data_check2)

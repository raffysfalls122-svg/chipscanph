import os
import sys
import django

# Add workspace directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chipscan.settings')
django.setup()

from scanner.models import Chip, NonCodePrice

print("=== SEEDING NONCODEPRICE TABLE ===")
default_noncode_prices = {
    '8GB': 50,
    '16GB': 80,
    '32GB': 200,
    '64GB': 300,
    '128GB': 450,
    '256GB': 600,
    '512GB': 800
}

for size, price in default_noncode_prices.items():
    obj, created = NonCodePrice.objects.get_or_create(size=size, defaults={'price': price})
    if created:
        print(f"  Created NonCodePrice for {size}: PHP {price}")
    else:
        print(f"  NonCodePrice for {size} already exists: PHP {obj.price}")

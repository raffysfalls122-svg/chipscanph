import os
import sys
import django

# Add root folder to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chipscan.settings')
django.setup()

from scanner.models import ScanHistory, Chip

print("--- ScanHistory image field values (first 5): ---")
for s in ScanHistory.objects.exclude(image='').order_by('-timestamp')[:5]:
    if s.image:
        print(f"ID {s.id}: image.name='{s.image.name}', image.url='{s.image.url}'")

print("\n--- Chip reference_image field values (first 5): ---")
for c in Chip.objects.all():
    if c.reference_image:
        print(f"Code {c.code}: reference_image.name='{c.reference_image.name}', reference_image.url='{c.reference_image.url}'")

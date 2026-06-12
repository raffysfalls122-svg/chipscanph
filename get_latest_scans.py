import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chipscan.settings')
django.setup()

from scanner.models import ScanHistory

print("=== RECENT SCANS ===")
for s in ScanHistory.objects.order_by('-id')[:5]:
    print(f"ID: {s.id}")
    print(f"  Code: {s.code}")
    print(f"  OCR Text: {repr(s.ocr_text)}")
    print(f"  Image: {s.image.url if s.image else 'None'}")
    print("-" * 50)


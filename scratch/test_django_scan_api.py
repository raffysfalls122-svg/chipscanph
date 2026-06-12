import os
import sys
import django
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chipscan.settings')
django.setup()

# Create a small dummy image in memory
from PIL import Image
import io

img = Image.new('RGB', (100, 100), color = 'red')
img_byte_arr = io.BytesIO()
img.save(img_byte_arr, format='PNG')
img_byte_arr.seek(0)

# Mock file upload
uploaded_file = SimpleUploadedFile("cropped_chip.png", img_byte_arr.read(), content_type="image/png")

client = Client()

print("Testing POST api_scan_image...")
try:
    response = client.post('/api/scan/image/', {'image': uploaded_file})
    print("Status Code:", response.status_code)
    import json
    data = json.loads(response.content)
    print("Response JSON:")
    for k, v in data.items():
        if k != 'result':
            print(f"  {k}: {v}")
        else:
            print("  result:")
            for rk, rv in v.items():
                print(f"    {rk}: {rv}")
except Exception as e:
    import traceback
    print("Error occurred:")
    traceback.print_exc()

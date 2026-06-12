import os
from PIL import Image, ImageOps, ImageFilter
import pytesseract
import numpy as np

TESSERACT_WINDOWS_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_WINDOWS_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_WINDOWS_PATH

img_path = r"C:\Users\Windows 11\Desktop\chipscanph\media\scans\cropped_chip_8WHzgeU.png"
if not os.path.exists(img_path):
    print("File not found")
    exit()

img = Image.open(img_path)
print("Image size:", img.size)

# Execute new views.py preprocessing pipeline steps:
img_gray = img.convert('L')
w, h = img_gray.size
img_scaled = img_gray.resize((w * 4, h * 4), Image.Resampling.LANCZOS)
img_blur = img_scaled.filter(ImageFilter.GaussianBlur(radius=1.0))
img_contrast = ImageOps.autocontrast(img_blur)

mean_val = np.mean(np.array(img_contrast))
if mean_val < 127:
    img_final = ImageOps.invert(img_contrast)
else:
    img_final = img_contrast

# Multi-pass OCR
chip_whitelist = r'--oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'

ocr_results = []
try:
    r1 = pytesseract.image_to_string(img_final, config=f'--psm 6 {chip_whitelist}').strip()
    if r1: ocr_results.append(r1)
except Exception as e:
    print("Pass 1 error:", e)

try:
    r2 = pytesseract.image_to_string(img_final, config=f'--psm 4 {chip_whitelist}').strip()
    if r2: ocr_results.append(r2)
except Exception as e:
    print("Pass 2 error:", e)

try:
    r3 = pytesseract.image_to_string(img_final, config='--psm 6').strip()
    if r3: ocr_results.append(r3)
except Exception as e:
    print("Pass 3 error:", e)

print("\n=== OCR Multi-pass Results ===")
for i, res in enumerate(ocr_results):
    print(f"Pass {i+1}:")
    for line in res.split('\n'):
        if line.strip():
            print(f"  {line.strip()}")

# Cleanup helpers
def clean_for_matching(text):
    import re
    return re.sub(r'[^A-Z0-9-]', '', text.upper())

all_ocr_text = ' '.join(ocr_results)
print("\nCleaned OCR tokens:")
import re
ocr_tokens = [t for t in re.split(r'[^A-Z0-9]+', all_ocr_text.upper()) if len(t) >= 4]
print(ocr_tokens)


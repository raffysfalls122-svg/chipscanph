import os
from PIL import Image, ImageOps, ImageFilter
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

img_path = r"c:\Users\Windows 11\Desktop\chipscanph\media\scans\cropped_chip_Pb85uGR.png"
if not os.path.exists(img_path):
    print("Not found")
    exit()

img = Image.open(img_path)

print("--- RAW OCR (no preprocessing) ---")
for psm in [3, 4, 6, 11, 12]:
    try:
        text = pytesseract.image_to_string(img, config=f'--psm {psm}').strip()
        print(f"PSM {psm}: {repr(text)}")
    except Exception as e:
        print(f"PSM {psm} Error: {e}")

print("--- RESIZED 4x ONLY ---")
w, h = img.size
img_resized = img.resize((w * 4, h * 4), Image.Resampling.LANCZOS)
for psm in [3, 4, 6]:
    try:
        text = pytesseract.image_to_string(img_resized, config=f'--psm {psm}').strip()
        print(f"PSM {psm}: {repr(text)}")
    except Exception as e:
        print(f"PSM {psm} Error: {e}")

print("--- GRAYSCALE + RESIZED 4x ---")
img_gray = img.convert('L').resize((w * 4, h * 4), Image.Resampling.LANCZOS)
for psm in [3, 4, 6]:
    try:
        text = pytesseract.image_to_string(img_gray, config=f'--psm {psm}').strip()
        print(f"PSM {psm}: {repr(text)}")
    except Exception as e:
        print(f"PSM {psm} Error: {e}")

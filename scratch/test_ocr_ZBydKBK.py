import os
from PIL import Image, ImageOps, ImageFilter
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

img_path = r"c:\Users\Windows 11\Desktop\chipscanph\media\scans\cropped_chip_ZBydKBK.png"
if not os.path.exists(img_path):
    print("Not found")
    exit()

img = Image.open(img_path)
print("Image size:", img.size)

print("--- RAW OCR (no preprocessing) ---")
for psm in [3, 4, 6]:
    try:
        text = pytesseract.image_to_string(img, config=f'--psm {psm}').strip()
        print(f"PSM {psm}: {repr(text)}")
    except Exception as e:
        print(f"Error PSM {psm}: {e}")

import os
from PIL import Image
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

img_path = r"c:\Users\Windows 11\Desktop\chipscanph\media\scans\cropped_chip_lvx5rXx.png"
if os.path.exists(img_path):
    img = Image.open(img_path)
    print("Format:", img.format)
    print("Size:", img.size)
    print("Mode:", img.mode)
    
    # Run a quick OCR to see what's on it
    text = pytesseract.image_to_string(img)
    print("=== Raw OCR ===")
    print(repr(text))
else:
    print("Image not found at:", img_path)

import os
from PIL import Image, ImageOps, ImageFilter
import pytesseract
import numpy as np

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

img_path = r"c:\Users\Windows 11\Desktop\chipscanph\media\scans\cropped_chip_ZBydKBK.png"
if not os.path.exists(img_path):
    print("Not found")
    exit()

img = Image.open(img_path)
img_gray = img.convert('L')
w, h = img_gray.size
img_scaled = img_gray.resize((w * 4, h * 4), Image.Resampling.LANCZOS)
img_blur = img_scaled.filter(ImageFilter.GaussianBlur(radius=1.0))
img_contrast = ImageOps.autocontrast(img_blur)

img_arr = np.array(img_contrast)
mean_val = np.mean(img_arr)
if mean_val < 127:
    img_final = ImageOps.invert(img_contrast)
else:
    img_final = img_contrast

print("Pass 4 (denoised, PSM 6, no whitelist):")
try:
    print(repr(pytesseract.image_to_string(img_final, config='--psm 6').strip()))
except Exception as e:
    print("Error:", e)

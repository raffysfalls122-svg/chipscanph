import os
from PIL import Image, ImageOps, ImageFilter
import pytesseract
import numpy as np

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

img_path = r"c:\Users\Windows 11\Desktop\chipscanph\media\scans\cropped_chip_Pb85uGR.png"
if not os.path.exists(img_path):
    print("Not found")
    exit()

img = Image.open(img_path)
img_gray = img.convert('L')
w, h = img_gray.size
img_scaled = img_gray.resize((w * 4, h * 4), Image.Resampling.LANCZOS)

# Test different blur values
for radius in [0.0, 0.3, 0.5, 0.8, 1.0]:
    if radius > 0:
        img_blur = img_scaled.filter(ImageFilter.GaussianBlur(radius=radius))
    else:
        img_blur = img_scaled
        
    img_contrast = ImageOps.autocontrast(img_blur)
    
    # Check mean and invert if necessary
    img_arr = np.array(img_contrast)
    mean_val = np.mean(img_arr)
    if mean_val < 127:
        img_final = ImageOps.invert(img_contrast)
    else:
        img_final = img_contrast
        
    # Test OCR with PSM 6 and PSM 4
    for psm in [6, 4]:
        try:
            txt = pytesseract.image_to_string(img_final, config=f'--psm {psm}').strip()
            print(f"Radius={radius} | PSM={psm} | OCR: {repr(txt)}")
        except Exception as e:
            print("Error:", e)

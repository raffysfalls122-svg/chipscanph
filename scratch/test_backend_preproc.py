import os
import sys
import re
import cv2
from PIL import Image, ImageOps, ImageFilter
import pytesseract
import numpy as np

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def run_tests():
    scans_dir = "scans"
    files = ["cropped_chip.png", "cropped_chip_GJwz6hC.png"]
    
    for f in files:
        path = os.path.join(scans_dir, f)
        if not os.path.exists(path):
            continue
        print(f"\n=================== FILE: {f} ===================")
        
        # Load image with cv2
        img_cv = cv2.imread(path)
        if img_cv is None:
            print("Failed to load image via cv2")
            continue
            
        # Convert to grayscale
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # Test combinations of scaling and thresholding
        h, w = gray.shape
        tests = []
        for scale in [2, 3, 4]:
            resized = cv2.resize(gray, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
            
            # Simple contrast
            contrast = cv2.convertScaleAbs(resized, alpha=1.8, beta=-30)
            tests.append((f"Scale {scale}x + Contrast", contrast))
            
            # Otsu
            blur = cv2.GaussianBlur(resized, (5, 5), 0)
            _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            tests.append((f"Scale {scale}x + Otsu", otsu))
            
            # Adaptive Thresholding (block sizes 11, 25, 51)
            for bs in [11, 25, 51]:
                thresh_adaptive = cv2.adaptiveThreshold(resized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, bs, 10)
                tests.append((f"Scale {scale}x + Adaptive (BS={bs})", thresh_adaptive))
        
        chip_whitelist = r'--oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'
        
        for desc, test_img in tests:
            for psm in [6, 11]:
                try:
                    txt = pytesseract.image_to_string(test_img, config=f'--psm {psm} {chip_whitelist}').strip()
                    if "KMQE" in txt or "B318" in txt or "00600" in txt or "60013" in txt:
                        txt_clean = re.sub(r'\n+', '\n', txt)
                        print(f"[{desc}] PSM {psm}:")
                        print(repr(txt_clean))
                except Exception as e:
                    pass

if __name__ == '__main__':
    run_tests()

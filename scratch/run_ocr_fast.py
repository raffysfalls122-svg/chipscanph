import os
import re
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import pytesseract
import numpy as np
import cv2

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def run_fast_ocr():
    files = ["cropped_chip.png", "cropped_chip_GJwz6hC.png"]
    scans_dir = "scans"
    
    for f in files:
        path = os.path.join(scans_dir, f)
        if not os.path.exists(path):
            print(f"File {path} not found.")
            continue
        print(f"\n=================== FILE: {f} ===================")
        
        # Load image via cv2
        img_cv = cv2.imread(path)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        resized = cv2.resize(gray, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)
        
        # Prep 1: Otsu inverted
        blur = cv2.GaussianBlur(resized, (3, 3), 0)
        _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        otsu_inv = cv2.bitwise_not(otsu)
        
        # Prep 2: Adaptive threshold inverted
        thresh_ad = cv2.adaptiveThreshold(resized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 25, 10)
        ad_inv = cv2.bitwise_not(thresh_ad)
        
        # Prep 3: Contrast + Sharpen
        pil_resized = Image.fromarray(resized)
        pil_ac = ImageOps.autocontrast(pil_resized)
        pil_contrast = ImageEnhance.Contrast(pil_ac).enhance(2.0)
        pil_sharp = pil_contrast.filter(ImageFilter.SHARPEN)
        img_sharp = np.array(pil_sharp)
        
        preps = [
            ("Otsu Inverted", otsu_inv),
            ("Adaptive Inverted", ad_inv),
            ("Contrast + Sharpen", img_sharp)
        ]
        
        for name, img_arr in preps:
            print(f"--- Prep: {name} ---")
            for psm in [6, 11]:
                try:
                    txt = pytesseract.image_to_string(img_arr, config=f'--psm {psm}').strip()
                    txt_clean = re.sub(r'\s+', ' ', txt)
                    if txt_clean:
                        print(f"  PSM {psm}: {repr(txt_clean)}")
                except Exception as e:
                    print(f"  PSM {psm} Error: {e}")

if __name__ == '__main__':
    run_fast_ocr()

import os
import re
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import pytesseract
import numpy as np
import cv2

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def preprocess_options(img_path):
    img = Image.open(img_path)
    # Convert PIL to CV2 grayscale
    img_cv = cv2.imread(img_path)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    results = {}
    
    # Base scale
    scale = 3
    h, w = gray.shape
    resized = cv2.resize(gray, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
    
    # Option 1: Adaptive Thresholding (C=10, block=25)
    thresh_ad = cv2.adaptiveThreshold(resized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 25, 10)
    results["Adaptive Threshold"] = Image.fromarray(thresh_ad)
    
    # Option 2: Otsu thresholding
    blur = cv2.GaussianBlur(resized, (3, 3), 0)
    _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results["Otsu Threshold"] = Image.fromarray(otsu)
    
    # Option 3: Otsu Threshold Inverted (Tesseract works better with black text on white background)
    results["Otsu Threshold Inverted"] = Image.fromarray(cv2.bitwise_not(otsu))
    
    # Option 4: Grayscale + Autocontrast + Sharpen
    pil_gray = Image.fromarray(resized)
    pil_ac = ImageOps.autocontrast(pil_gray)
    pil_sharp = pil_ac.filter(ImageFilter.SHARPEN)
    results["Autocontrast + Sharpen"] = pil_sharp
    
    # Option 5: Adaptive Threshold Inverted
    results["Adaptive Threshold Inverted"] = Image.fromarray(cv2.bitwise_not(thresh_ad))
    
    return results

def test_ocr():
    files = ["cropped_chip.png", "cropped_chip_GJwz6hC.png"]
    scans_dir = "scans"
    
    chip_whitelist = r'--oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'
    
    for f in files:
        path = os.path.join(scans_dir, f)
        if not os.path.exists(path):
            print(f"File {path} does not exist.")
            continue
        print(f"\n=================== FILE: {f} ===================")
        
        preprocessed = preprocess_options(path)
        for name, img in preprocessed.items():
            print(f"\n--- Preprocessing: {name} ---")
            for psm in [3, 4, 6, 11, 12]:
                try:
                    txt = pytesseract.image_to_string(img, config=f'--psm {psm} {chip_whitelist}').strip()
                    txt_no_wl = pytesseract.image_to_string(img, config=f'--psm {psm}').strip()
                    
                    for wl_desc, t in [("With Whitelist", txt), ("No Whitelist", txt_no_wl)]:
                        t_clean = re.sub(r'\s+', ' ', t).strip()
                        if t_clean:
                            # Print result if it looks like a chip code
                            # e.g., contains KM, SEC, H9, UFS, eMMC, or length > 4
                            if any(x in t_clean.upper() for x in ["KM", "SEC", "H9", "00600", "B318", "GD6", "THG"]):
                                print(f"  [PSM {psm} - {wl_desc}]: {repr(t_clean)}")
                except Exception as e:
                    print(f"Error {psm}: {e}")

if __name__ == '__main__':
    test_ocr()

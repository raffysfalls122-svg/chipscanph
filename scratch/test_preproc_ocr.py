import os
import sys
import re
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import pytesseract
import numpy as np

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def current_ocr_logic(img):
    # Resize to 400 max dim
    max_ocr_dim = 400
    img_ocr = img.copy()
    if img_ocr.width > max_ocr_dim or img_ocr.height > max_ocr_dim:
        img_ocr.thumbnail((max_ocr_dim, max_ocr_dim), Image.Resampling.LANCZOS)
    img_gray = img_ocr.convert('L')
    enhancer = ImageEnhance.Contrast(img_gray)
    img_contrast = enhancer.enhance(2.0)
    img_sharp = img_contrast.filter(ImageFilter.SHARPEN)
    
    chip_whitelist = r'--oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'
    res6 = pytesseract.image_to_string(img_sharp, config=f'--psm 6 {chip_whitelist}').strip()
    res11 = pytesseract.image_to_string(img_sharp, config=f'--psm 11 {chip_whitelist}').strip()
    return f"PSM6: {repr(res6)} | PSM11: {repr(res11)}"

def optimized_ocr_logic(img):
    # Upscale or keep high resolution (e.g. max dim 1500)
    max_ocr_dim = 1500
    img_ocr = img.copy()
    if img_ocr.width < 800 and img_ocr.height < 800:
        # Scale up small crops
        scale = 3
        img_ocr = img_ocr.resize((img_ocr.width * scale, img_ocr.height * scale), Image.Resampling.LANCZOS)
    elif img_ocr.width > max_ocr_dim or img_ocr.height > max_ocr_dim:
        img_ocr.thumbnail((max_ocr_dim, max_ocr_dim), Image.Resampling.LANCZOS)
        
    img_gray = img_ocr.convert('L')
    
    # Run multiple preprocessed versions to catch all variations
    # 1. Autocontrast + Sharpen
    img_ac = ImageOps.autocontrast(img_gray)
    img_sharp = img_ac.filter(ImageFilter.SHARPEN)
    
    # 2. High Contrast + Sharpen
    img_contrast = ImageEnhance.Contrast(img_gray).enhance(2.5)
    img_sharp_c = img_contrast.filter(ImageFilter.SHARPEN)
    
    chip_whitelist = r'--oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'
    
    results = []
    
    # Check both images with different PSMs
    for name, test_img in [("Sharp_AutoContrast", img_sharp), ("Sharp_HighContrast", img_sharp_c)]:
        for psm in [6, 11, 3]:
            try:
                res = pytesseract.image_to_string(test_img, config=f'--psm {psm} {chip_whitelist}').strip()
                if res:
                    results.append((name, psm, res))
            except Exception:
                pass
                
    output = []
    for name, psm, text in results[:6]:
        output.append(f"{name}_PSM{psm}: {repr(text)}")
    return " | ".join(output)

def run_tests():
    scans_dir = "scans"
    files = [f for f in os.listdir(scans_dir) if f.startswith('cropped_chip')]
    print(f"Found {len(files)} cropped chip files in scans/")
    
    for f in files:
        path = os.path.join(scans_dir, f)
        print(f"\n=================== FILE: {f} ===================")
        try:
            img = Image.open(path)
            print("CURRENT LOGIC:")
            print("  ", current_ocr_logic(img))
            print("OPTIMIZED LOGIC:")
            print("  ", optimized_ocr_logic(img))
        except Exception as e:
            print("Error:", e)

if __name__ == '__main__':
    run_tests()

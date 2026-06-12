import os
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import pytesseract
import numpy as np

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

img_path = r"c:\Users\Windows 11\Desktop\chipscanph\media\scans\cropped_chip_Pb85uGR.png"
if not os.path.exists(img_path):
    print("Not found")
    exit()

img = Image.open(img_path).convert('L')
w, h = img.size

# Preprocessing combinations
enhancers = [
    ("Raw", img),
    ("Resized 4x", img.resize((w * 4, h * 4), Image.Resampling.LANCZOS)),
]

results = []

for name, im in enhancers:
    # Try different contrast factors
    for contrast in [1.0, 1.5, 2.0, 2.5]:
        im_contrast = ImageEnhance.Contrast(im).enhance(contrast)
        # Try different brightness factors
        for brightness in [0.8, 1.0, 1.2]:
            im_bright = ImageEnhance.Brightness(im_contrast).enhance(brightness)
            # Try blur/sharp
            for filter_name, filter_obj in [("None", None), ("Blur 0.5", ImageFilter.GaussianBlur(0.5)), ("Blur 1.0", ImageFilter.GaussianBlur(1.0)), ("Sharpen", ImageFilter.SHARPEN)]:
                im_filtered = im_bright.filter(filter_obj) if filter_obj else im_bright
                
                # Invert versions
                for inv in [False, True]:
                    im_final = ImageOps.invert(im_filtered) if inv else im_filtered
                    
                    # Convert to numpy array for threshold testing
                    arr = np.array(im_final)
                    
                    for thresh_type in ["None", "Otsu", "Adaptive"]:
                        if thresh_type == "None":
                            # Standard grayscale
                            test_imgs = [im_final]
                        elif thresh_type == "Otsu":
                            # Otsu thresholding
                            try:
                                import cv2
                                _, thresh = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                                test_imgs = [Image.fromarray(thresh)]
                            except ImportError:
                                # Fallback if cv2 not installed
                                test_imgs = []
                        elif thresh_type == "Adaptive":
                            try:
                                import cv2
                                thresh = cv2.adaptiveThreshold(arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
                                test_imgs = [Image.fromarray(thresh)]
                            except ImportError:
                                test_imgs = []
                        
                        for test_img in test_imgs:
                            for psm in [4, 6, 11, 12]:
                                try:
                                    txt = pytesseract.image_to_string(test_img, config=f'--psm {psm}').strip()
                                    if txt:
                                        # Score based on whether it contains KM2 or 7001 or standard chip characters
                                        score = 0
                                        if "KM2" in txt: score += 10
                                        if "7001" in txt: score += 10
                                        if "CM" in txt: score += 5
                                        if "SEC" in txt: score += 5
                                        results.append((score, txt, f"{name} | C={contrast} | B={brightness} | F={filter_name} | Inv={inv} | Thresh={thresh_type} | PSM={psm}"))
                                except Exception:
                                    pass

# Sort results by score, then show top 10
results.sort(key=lambda x: x[0], reverse=True)
print(f"Total combinations tested: {len(results)}")
print("=== TOP RESULTS ===")
for score, txt, desc in results[:20]:
    print(f"Score: {score} | Config: {desc}")
    print(repr(txt))
    print("-" * 50)

import os
from PIL import Image

img_path = r"c:\Users\Windows 11\Desktop\chipscanph\media\scans\cropped_chip_Pb85uGR.png"
if os.path.exists(img_path):
    img = Image.open(img_path).convert('L')
    # Resize slightly so it fits in terminal width (say 80 columns)
    w, h = img.size
    scale = 80.0 / w
    img_small = img.resize((80, int(h * scale)), Image.Resampling.NEAREST)
    
    # Print as ASCII
    chars = " .:-=+*#%@"
    for y in range(img_small.height):
        line = ""
        for x in range(img_small.width):
            val = img_small.getpixel((x, y))
            idx = int((val / 255.0) * (len(chars) - 1))
            line += chars[idx]
        print(line)
else:
    print("Not found")

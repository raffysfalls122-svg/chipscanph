import os
from PIL import Image
import numpy as np

img_path = r"c:\Users\Windows 11\Desktop\chipscanph\media\scans\cropped_chip_lvx5rXx.png"
if os.path.exists(img_path):
    img = Image.open(img_path)
    arr = np.array(img)
    print("Dimensions:", arr.shape)
    
    # Calculate average color
    avg_color = np.mean(arr, axis=(0, 1))
    print("Average color (RGBA):", avg_color)
    
    # Check if there are colorful pixels or if it's mostly dark background code theme
    # Dark themes usually have dark grey background (e.g., #0a0a12 or #1e1e1e)
    # Let's count some color distributions
    flat_arr = arr.reshape(-1, arr.shape[-1])
    unique_colors, counts = np.unique(flat_arr[:, :3], axis=0, return_counts=True)
    sorted_idx = np.argsort(-counts)
    print("Top 5 dominant colors:")
    for idx in sorted_idx[:5]:
        print(f"  Color {unique_colors[idx]}: {counts[idx]} pixels ({counts[idx]/len(flat_arr)*100:.2f}%)")
else:
    print("Not found")

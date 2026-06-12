import os
from PIL import Image
import numpy as np

def check_image(path):
    if not os.path.exists(path):
        print(f"File {path} not found.")
        return
    img = Image.open(path)
    arr = np.array(img)
    flat_arr = arr.reshape(-1, arr.shape[-1])
    unique_colors, counts = np.unique(flat_arr[:, :3], axis=0, return_counts=True)
    sorted_idx = np.argsort(-counts)
    print(f"=== {path} ===")
    print("Dimensions:", arr.shape)
    print("Unique colors count:", len(unique_colors))
    print("Top 3 dominant colors:")
    for idx in sorted_idx[:3]:
        print(f"  Color {unique_colors[idx]}: {counts[idx]} pixels ({counts[idx]/len(flat_arr)*100:.2f}%)")

check_image("scratch/scan_tab.png")
check_image("scratch/grades_tab.png")
check_image("scratch/history_tab.png")

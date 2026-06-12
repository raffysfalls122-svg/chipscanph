import sys

sys.stdout.reconfigure(encoding='utf-8')
index_path = r"c:\Users\Windows 11\Desktop\chipscanph\scanner\templates\scanner\index.html"

try:
    with open(index_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    print("Searching for OCR list rendering loop in index.html:")
    for idx, line in enumerate(lines):
        if 'extracted.forEach((item, index)' in line:
            print(f"Line {idx+1}: {line.strip()}")
            for j in range(max(0, idx-2), min(len(lines), idx+50)):
                print(f"  {j+1}: {lines[j].strip()}")
            break
except Exception as e:
    print(f"Error: {e}")

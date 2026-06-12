import sys

sys.stdout.reconfigure(encoding='utf-8')
views_path = r"c:\Users\Windows 11\Desktop\chipscanph\scanner\views.py"

try:
    with open(views_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    print("Printing views.py from line 920 to 945:")
    for j in range(919, min(len(lines), 945)):
        print(f"{j+1}: {lines[j].strip()}")
except Exception as e:
    print(f"Error: {e}")

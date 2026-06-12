with open('scanner/views.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if 'def ' in line and ('ocr' in line.lower() or 'matching' in line.lower() or 'task' in line.lower() or 'scan' in line.lower()):
            print(f"{i}: {line.strip()}")

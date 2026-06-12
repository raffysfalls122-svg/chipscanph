with open('scanner/views.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if line.startswith('def '):
            print(f"{i}: {line.strip()}")

with open('scanner/views.py', 'r', encoding='utf-8') as f:
    for i in range(100):
        line = f.readline()
        if not line:
            break
        safe_line = line.strip().encode('ascii', 'ignore').decode('ascii')
        print(f"{i+1}: {repr(safe_line)}")

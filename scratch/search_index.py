with open('scanner/templates/scanner/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    for i, line in enumerate(f, 1):
        if "method: 'PUT'" in line or "method: 'DELETE'" in line or 'api/chips' in line or 'delete' in line:
            if 'fetch' in line or 'method' in line:
                safe_line = line.strip().encode('ascii', 'ignore').decode('ascii')
                print(f'{i}: {safe_line}')

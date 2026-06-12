with open('scanner/templates/scanner/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '.nav {' in line or '.nb {' in line or '.ni {' in line:
        print(f"Line {i+1}: {line.strip()}")
        # print next 15 lines
        for j in range(1, 15):
            print(f"  {lines[i+j].strip()}")

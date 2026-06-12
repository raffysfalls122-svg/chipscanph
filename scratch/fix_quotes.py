with open('scanner/views.py', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('\\"\\"\\"', '"""')

with open('scanner/views.py', 'w', encoding='utf-8') as f:
    f.write(c)

print("Quotes replaced successfully.")

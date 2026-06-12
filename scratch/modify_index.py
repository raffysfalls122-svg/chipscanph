import os

path = r'c:\Users\Windows 11\Desktop\chipscanph\scanner\templates\scanner\index.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Insert {% csrf_token %} after <body>
body_tag = '<body>'
if body_tag in content and '{% csrf_token %}' not in content:
    content = content.replace(body_tag, body_tag + '\n  {% csrf_token %}')
    print('Inserted {% csrf_token %} tag.')

# Normalize spaces/newlines to LF for uniform replacement
content = content.replace('\r\n', '\n')

# 2. Insert getCsrfToken() definition below the return inside getCookie
insert_marker = 'return cookieValue;\n    }'
token_func = '''

    function getCsrfToken() {
      let token = getCookie('csrftoken');
      if (!token) {
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        if (input) {
          token = input.value;
        }
      }
      return token;
    }'''

if insert_marker in content:
    content = content.replace(insert_marker, insert_marker + token_func, 1)
    print('Inserted getCsrfToken() function definition.')
else:
    print('Error: Could not find insert_marker in index.html')

# 3. Replace all occurrences of getCookie('csrftoken')
count_replaced = content.count("getCookie('csrftoken')")
content = content.replace("getCookie('csrftoken')", 'getCsrfToken()')
print(f"Replaced {count_replaced} occurrences of getCookie('csrftoken') with getCsrfToken().")

with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(content)
print('File saved successfully.')

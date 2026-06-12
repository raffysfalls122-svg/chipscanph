import os

html_path = 'scanner/templates/scanner/index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    text = f.read()

start = text.find('    async function doLogin() {')
if start == -1:
    print('Failed to find start marker!')
    exit(1)

# Find the end of doLogin
end_marker = "      } catch (err) {\n        errEl.classList.add('s');\n      }\n    }"
end = text.find(end_marker, start)
if end == -1:
    print('Failed to find end marker!')
    exit(1)

end += len(end_marker)

replacement = """    let isSubmittingLogin = false;

    async function doLogin() {
      if (isSubmittingLogin) return;
      
      const btn = document.querySelector('.login-btn');
      const u = document.getElementById('lU').value.trim();
      const p = document.getElementById('lP').value.trim();
      const errEl = document.getElementById('lE');

      if (!u || !p) {
        errEl.textContent = '❌ Username and password are required';
        errEl.classList.add('s');
        return;
      }

      isSubmittingLogin = true;
      if (btn) {
        btn.disabled = true;
        btn.textContent = 'Signing In...';
      }
      errEl.classList.remove('s');

      try {
        const res = await fetch('/api/login/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
          },
          body: JSON.stringify({ username: u, password: p })
        });

        const data = await res.json();
        if (data.success) {
          loginSuccess(data.user);
          document.getElementById('lU').value = '';
          document.getElementById('lP').value = '';
        } else {
          errEl.textContent = '❌ ' + (data.message || 'Invalid username or password');
          errEl.classList.add('s');
        }
      } catch (err) {
        errEl.textContent = '❌ Connection failed. Try again.';
        errEl.classList.add('s');
      } finally {
        isSubmittingLogin = false;
        if (btn) {
          btn.disabled = false;
          btn.textContent = 'Sign In →';
        }
      }
    }"""

text = text[:start] + replacement + text[end:]

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(text)

print('SUCCESS: index.html login updated successfully.')

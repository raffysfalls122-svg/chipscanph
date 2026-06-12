import os

html_path = 'scanner/templates/scanner/index.html'

with open(html_path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Fix getCsrfToken recursion
bad_csrf_func = """    function getCsrfToken() {
      let token = getCsrfToken();"""

good_csrf_func = """    function getCsrfToken() {
      let token = getCookie('csrftoken');"""

if bad_csrf_func in text:
    text = text.replace(bad_csrf_func, good_csrf_func)
    print("Fixed getCsrfToken recursion.")
else:
    print("WARNING: bad_csrf_func not found. Checking general pattern...")
    # fallback check
    idx = text.find('function getCsrfToken() {\n      let token = getCsrfToken();')
    if idx != -1:
        text = text[:idx] + 'function getCsrfToken() {\n      let token = getCookie(\'csrftoken\');' + text[idx + len('function getCsrfToken() {\n      let token = getCsrfToken();'):]
        print("Fixed getCsrfToken recursion via fallback.")

# 2. Fix doLogin catch block
bad_catch = """      } catch (err) {
        errEl.textContent = '❌ Connection failed. Try again.';
        errEl.classList.add('s');
      }"""

good_catch = """      } catch (err) {
        console.error('[LOGIN ERROR]', err);
        errEl.textContent = '❌ Connection failed: ' + err.message;
        errEl.classList.add('s');
      }"""

if bad_catch in text:
    text = text.replace(bad_catch, good_catch)
    print("Updated doLogin catch block error message.")
else:
    print("WARNING: bad_catch not found.")

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("HTML modifications complete.")

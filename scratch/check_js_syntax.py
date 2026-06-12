import re
import subprocess
import os

html_path = "scanner/templates/scanner/index.html"
temp_js_path = "scratch/temp_index.js"

with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# Find the script block
# Note: There might be multiple <script> tags. We find all and check them.
script_blocks = re.findall(r"<script[^>]*>(.*?)</script>", content, re.DOTALL)

print(f"Found {len(script_blocks)} script blocks.")

for i, block in enumerate(script_blocks):
    # Node does not support browser APIs like document, window, localStorage, etc.
    # To check syntax only, we can run "node --check" on the script block, which only parses the code
    # and checks for syntax errors (it does not execute any browser APIs).
    with open(temp_js_path, "w", encoding="utf-8") as f:
        f.write(block)
    
    print(f"Checking script block {i+1}...")
    res = subprocess.run(["node", "--check", temp_js_path], capture_output=True)
    if res.returncode != 0:
        print(f"Error: Syntax Error found in script block {i+1}:")
        import sys
        sys.stdout.buffer.write(res.stderr)
    else:
        print(f"OK: Script block {i+1} has no syntax errors.")

if os.path.exists(temp_js_path):
    os.remove(temp_js_path)
